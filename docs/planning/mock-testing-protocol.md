# Mock Testing Protocol: Technical Specifications

This document provides the detailed technical specifications for the end-to-end mock testing protocol, expanding on the high-level plan from the `think` mode.

## 1. Current State Analysis (from `think` mode)
- **Existing Coverage**: The project has basic mock wallet implementations in tests (mock_web3 fixtures, mock transaction signing)
- **Key Gaps Identified**:
  - No unified mock wallet framework across protocols
  - Limited edge case testing (wallet compromise, nonce issues, gas estimation failures)
  - Inconsistent mocking patterns between protocol tests
  - Missing cross-protocol transaction flow testing

## 2. Wallet Interaction Points (from `think` mode)
All protocols interact with wallets through:
- Private key management for transaction signing
- Balance checking (ETH and tokens)
- Gas estimation and pricing
- Transaction building, signing, and sending
- Nonce management
- Contract interactions (approve, transfer, bridge operations)

## 3. Recommended Mock Wallet Framework (Branch P-B)

### 3.1. Architecture (from `think` mode)
```
MockWallet (base class)
├── MockHotWallet (simulates real wallet behaviors)
├── MockCompromisedWallet (security testing)
├── MockLowBalanceWallet (insufficient funds scenarios)
└── MockNetworkErrorWallet (connection issues)
```

### 3.2. Location
The new mock wallet classes will be located in a new file: `airdrops/tests/mocks/wallets.py`. The `mocks` directory will need to be created.

### 3.3. Technical Specifications: `MockWallet` Framework

#### 3.3.1. `MockWallet` (Abstract Base Class)
This class defines the standard interface for all mock wallets, ensuring compatibility with the protocol-agnostic logic. It will be based on Python's `abc` module.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from web3.types import TxParams, Wei, Address, HexStr

class MockWallet(ABC):
    """
    Abstract Base Class for a mock wallet used in testing.
    """
    def __init__(self, private_key: str, initial_balance: Dict[str, float]):
        self.private_key = private_key
        self.address: Address = self.derive_address(private_key)
        self.balances: Dict[str, Wei] = {token: Wei(int(amount * 10**18)) for token, amount in initial_balance.items()}
        self.nonce: int = 0
        self.transaction_history: List[Dict[str, Any]] = []

    @staticmethod
    def derive_address(private_key: str) -> Address:
        # Implementation to derive an Ethereum address from a private key
        pass

    @abstractmethod
    def get_balance(self, token: str = 'ETH') -> Wei:
        """Returns the balance for a given token ('ETH' or a contract address)."""
        pass

    @abstractmethod
    def get_nonce(self) -> int:
        """Returns the next transaction nonce."""
        pass

    @abstractmethod
    def estimate_gas(self, tx_params: TxParams) -> Wei:
        """Simulates gas estimation."""
        pass

    @abstractmethod
    def sign_transaction(self, tx_params: TxParams) -> HexStr:
        """Signs a transaction and returns the raw signed transaction."""
        pass

    @abstractmethod
    def send_transaction(self, signed_tx: HexStr) -> HexStr:
        """
        Simulates sending a transaction to the network.
        Returns a deterministic transaction hash.
        """
        pass

    def _track_transaction(self, tx_hash: HexStr, tx_params: TxParams):
        """Adds a transaction to the history."""
        self.transaction_history.append({
            'hash': tx_hash,
            'params': tx_params,
            'status': 'success' # Default status
        })
        self.nonce += 1
```

#### 3.3.2. `MockHotWallet` (Concrete Implementation)
This is the standard, "happy path" implementation.

- **Behavior**:
  - `get_balance`: Returns the configured balance.
  - `get_nonce`: Returns the current nonce and increments it upon successful transaction.
  - `estimate_gas`: Returns a deterministic, reasonable gas estimate (e.g., 21000 for a simple transfer).
  - `sign_transaction`: Correctly signs the transaction using the provided private key.
  - `send_transaction`: "Mines" the transaction, updates balances, increments nonce, tracks the transaction, and returns a deterministic hash (e.g., `keccak(signed_tx)`).

#### 3.3.3. `MockCompromisedWallet` (Concrete Implementation)
Simulates a wallet whose private key has been exposed.

- **Behavior**:
  - `sign_transaction`: May raise a custom `WalletCompromisedError` or sign with an invalid signature to simulate unauthorized access.
  - `send_transaction`: Could also raise an error, simulating a scenario where a security system has locked the wallet.
  - All other methods behave like `MockHotWallet` to allow for testing detection mechanisms.

#### 3.3.4. `MockLowBalanceWallet` (Concrete Implementation)
Simulates a wallet with insufficient funds for transactions.

- **Behavior**:
  - `get_balance`: Returns a low, pre-configured balance.
  - `estimate_gas`: Behaves normally.
  - `send_transaction`: Checks if `balance >= tx_value + gas_cost`. If not, it raises an `InsufficientFundsError`. Otherwise, it succeeds. The balance threshold for failure is configurable.

#### 3.3.5. `MockNetworkErrorWallet` (Concrete Implementation)
Simulates network connectivity issues or RPC node failures.

- **Behavior**:
  - `get_balance`, `get_nonce`, `estimate_gas`, `send_transaction`: These methods will raise a `NetworkError` or `RPCError` exception, either consistently or intermittently, based on configuration. This allows testing of retry logic and error handling in the application.

## 4. Detailed Test Plan

### 4.1. Phase 1: Unit Testing
Location: `airdrops/tests/mocks/test_wallets.py`

**Test Cases**:
- `test_wallet_initialization`: Verify each mock wallet type can be created with initial balances.
- `test_hot_wallet_get_balance`: Check if `MockHotWallet` returns the correct balance.
- `test_hot_wallet_sign_transaction`: Ensure transaction is signed correctly and is verifiable.
- `test_hot_wallet_send_transaction`: Verify transaction hash is generated, nonce is incremented, and balance is updated.
- `test_low_balance_wallet_insufficient_funds`: Ensure `send_transaction` raises `InsufficientFundsError` when appropriate.
- `test_low_balance_wallet_sufficient_funds`: Ensure `send_transaction` succeeds when funds are just enough.
- `test_compromised_wallet_raises_error`: Verify `sign_transaction` or `send_transaction` raises `WalletCompromisedError`.
- `test_network_error_wallet_raises_error`: Verify that network-facing methods raise `NetworkError`.
- `test_transaction_history_tracking`: Ensure all sent transactions are recorded in `transaction_history`.

### 4.2. Phase 2: Integration Testing
Location: `airdrops/tests/integration/`

**Test Cases**:
- `test_scheduler_with_mock_wallets`: The scheduler should be able to pick up a task and execute it using a `MockHotWallet`.
- `test_cross_protocol_fund_movement`:
  - Use a `MockHotWallet` to bridge assets from a mock zkSync environment to a mock Scroll environment.
  - Verify balances are updated correctly on both "chains".
- `test_multi_wallet_coordination`:
  - A single task (e.g., liquidity provision) uses two different `MockHotWallet` instances.
  - Verify correct interaction and state changes for both wallets.
- `test_risk_management_with_low_balance`: An operation should be halted by the risk management module if a `MockLowBalanceWallet` is used and would fail.

### 4.3. Phase 3: Scenario Testing
Location: `airdrops/tests/scenarios/` (new directory)

**Test Cases**:
- `test_gas_spike_handling`: Configure `MockHotWallet` to suddenly return very high gas estimates and verify the system either waits or cancels the transaction as per policy.
- `test_network_congestion_recovery`: Use `MockNetworkErrorWallet` to simulate intermittent RPC failures and test the system's retry logic.
- `test_wallet_compromise_detection_and_shutdown`: An operation with a `MockCompromisedWallet` should be flagged by the monitoring system, and automated activity for that wallet should be paused.
- `test_failed_transaction_recovery_nonce_management`: Configure a mock wallet to have `send_transaction` fail after signing. Verify the system correctly re-uses the nonce for the next attempt.

### 4.4. Phase 4: End-to-End Testing
Location: `airdrops/tests/`

**Test Cases**:
- `test_e2e_zksync_farming_cycle_mocked`: A full farming workflow (deposit, swap, lend, withdraw) is executed using a `MockHotWallet`.
- `test_e2e_multi_protocol_airdrop_cycle_mocked`: A strategy involving zkSync, Scroll, and Hyperliquid is run end-to-end with mock wallets.
- `test_e2e_performance_with_100_wallets`: Run a standard farming cycle concurrently for 100 `MockHotWallet` instances to check for performance bottlenecks.
- `test_e2e_risk_management_full_cycle`: Run a full cycle where a `MockLowBalanceWallet` runs out of funds mid-cycle and verify the system handles it gracefully.

### 4.5. Refactoring Existing Tests
The new `MockWallet` framework should replace ad-hoc mocks in the following locations:
- All files in `airdrops/tests/protocols/` (e.g., `test_zksync.py`, `test_scroll.py`).
- All relevant files in `airdrops/tests/integration/` (e.g., `test_zksync_integration.py`).
- `airdrops/tests/test_end_to_end.py`.

## 5. Implementation Steps (from `think` mode, with details)

1.  **✅ COMPLETED - Create `MockWallet` base class**: Implement the ABC in `airdrops/tests/mocks/wallets.py`. **[COMPLETED - See `tests/mocks/wallets.py`]**
2.  **✅ COMPLETED - Implement specialized mock wallets**: Implement the four concrete classes in the same file. **[COMPLETED - MockHotWallet, MockCompromisedWallet, MockLowBalanceWallet, MockNetworkErrorWallet implemented]**
3.  **✅ COMPLETED - Create Unit Tests**: Add `airdrops/tests/mocks/test_wallets.py` to validate the framework. **[COMPLETED - Comprehensive test suite with 334 test cases]**
4.  **✅ COMPLETED - Replace existing ad-hoc mocks**: Added MockWallet imports to all identified test files that use ad-hoc wallet mocking. Files updated:
    - `airdrops/tests/test_end_to_end.py`
    - `airdrops/tests/protocols/test_zksync.py`
    - `airdrops/tests/protocols/test_scroll.py`
    - `airdrops/tests/integration/test_zksync_integration.py`
    - `airdrops/tests/integration/test_scroll_integration.py`
    All files now have access to the standardized MockWallet framework classes.
5.  **✅ COMPLETED - Build test scenario library**: Create the new integration, scenario, and E2E tests defined above. **[COMPLETED - See `airdrops/tests/test_scenarios.py`]**
6.  **✅ COMPLETED - Create comprehensive E2E farming cycle tests**: Implement full end-to-end farming cycle tests that simulate complete multi-day airdrop farming workflows using the MockWallet framework. **[COMPLETED - See `airdrops/tests/test_e2e_farming_cycles.py`]**
7.  **Create reporting infrastructure**: Update the CI/CD pipeline to generate and store test reports as defined in section 7.
8.  **Integrate with CI/CD pipeline**: Add a new testing stage to the CI configuration.

## 6. Success Metrics (from `think` mode)
- 95%+ code coverage for wallet interaction paths
- All critical failure modes tested
- <5% false positive rate in mock vs real wallet behavior
- Automated regression testing for all protocols

## 7. Reporting and CI/CD Integration

### 7.1. Test Report Structure
Test reports will be generated in a structured format like JSON for easy parsing. A `pytest` plugin like `pytest-json-report` can be used.

**Example JSON Report Snippet**:
```json
{
  "created": 1678886400.0,
  "duration": 123.45,
  "summary": {
    "total": 50,
    "passed": 48,
    "failed": 2
  },
  "tests": [
    {
      "node_id": "airdrops/tests/scenarios/test_gas_spike_handling.py::test_gas_spike_handling",
      "duration": 5.67,
      "outcome": "passed",
      "metadata": {
        "mock_wallet_type": "MockHotWallet",
        "transactions": [
          {
            "hash": "0x...",
            "gas_estimate": "5000000000"
          }
        ]
      }
    },
    {
      "node_id": "airdrops/tests/integration/test_risk_management.py::test_risk_management_with_low_balance",
      "duration": 2.34,
      "outcome": "failed",
      "longrepr": "InsufficientFundsError: Balance 0.01 ETH is less than required 0.05 ETH",
      "metadata": {
        "mock_wallet_type": "MockLowBalanceWallet"
      }
    }
  ]
}
```

### 7.2. CI/CD Integration Steps
Assuming a GitHub Actions workflow (`.github/workflows/ci.yml`):

1.  **Add a "Mock-Test" Job**: Create a new job in the CI workflow that runs after the standard unit tests.
2.  **Install Dependencies**: The job will check out the code and install project dependencies, including `pytest-json-report`.
3.  **Run Pytest**: Execute the tests with the appropriate flags.
    ```yaml
    - name: Run Mock Wallet Test Suite
      run: pytest airdrops/tests/ --json-report --json-report-file=mock-test-report.json
    ```
4.  **Archive Report**: Use the `actions/upload-artifact` action to save the report.
    ```yaml
    - name: Upload Mock Test Report
      uses: actions/upload-artifact@v3
      with:
        name: mock-test-report
        path: mock-test-report.json
    ```
5.  **(Optional) Add a Summary**: Use a script or an action to parse the report and post a summary to the pull request comments.