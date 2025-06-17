# Mock Wallet Validation Plan

## 1. Objective

To validate the `MockWallet` testing framework against live public testnets to ensure it accurately reflects real-world blockchain conditions and behaviors for all supported protocols.

## 2. Scope

This plan covers the validation of the `MockWallet` framework for the following protocols:
- Ethereum (as a baseline)
- zkSync
- Scroll
- LayerZero
- EigenLayer
- Hyperliquid

The validation will compare the results of identical operations executed with both a real wallet on a public testnet and a `MockWallet` instance.

## 3. Testnet Selection and Justification

| Protocol | Testnet | Justification |
|---|---|---|
| **Ethereum** | Sepolia | Official, stable, well-supported, and has readily available faucets. Serves as the baseline for L1 interactions. |
| **zkSync** | zkSync Sepolia Testnet | The official testnet for zkSync, providing the most accurate environment for zkSync-specific features. |
| **Scroll** | Scroll Sepolia Testnet | The official testnet for Scroll, ensuring compatibility with its ZK-rollup architecture. |
| **LayerZero** | Sepolia (for Ethereum) & other protocol testnets | LayerZero is a messaging protocol, so tests will be run between supported testnets (e.g., Sepolia and Arbitrum Sepolia). |
| **EigenLayer** | Holesky | The primary testnet for EigenLayer, offering the best support for restaking features. |
| **Hyperliquid** | Hyperliquid Testnet | The official testnet for Hyperliquid, necessary for testing its specific exchange functionalities. |

## 4. Testnet Funding Strategy

A dedicated test wallet will be used for each testnet to isolate activities and simplify funding.

| Testnet | Faucet URL(s) | Instructions |
|---|---|---|
| **Sepolia (ETH)** | - `https://sepoliafaucet.com/` <br> - `https://www.infura.io/faucet/sepolia` | Use a wallet address to request testnet ETH. Some faucets may require a social media account or a minimum mainnet balance. |
| **zkSync Sepolia** | - `https://faucet.zksync.io/` | Bridge ETH from Sepolia to zkSync Sepolia using the official bridge. |
| **Scroll Sepolia** | - `https://scroll.io/sepia` | Bridge ETH from Sepolia to Scroll Sepolia using the official bridge. |
| **Arbitrum Sepolia** | - `https://faucet.triangleplatform.com/arbitrum/sepolia` | Request testnet ETH directly on Arbitrum Sepolia. |
| **Holesky (ETH)** | - `https://holeskyfaucet.io/` | Request testnet ETH for the Holesky testnet. |
| **Hyperliquid** | - Faucet is integrated into the testnet UI. | Connect a wallet to the Hyperliquid testnet and use the UI to request testnet funds. |

## 5. Validation Test Suite

The following tests will be executed on both the live testnets and with the corresponding `MockWallet` implementation.

### 5.1. `NormalMockWallet` Validation

| Test Case | Description | Expected Outcome |
|---|---|---|
| **Successful Transaction** | Send a standard ETH transfer or token transfer. | Transaction succeeds. `receipt.status == 1`. Balances are updated correctly. |
| **Contract Interaction** | Call a simple function on a deployed contract (e.g., `approve` on an ERC20). | Transaction succeeds. `receipt.status == 1`. Correct logs are emitted. |

### 5.2. `InsufficientFundsMockWallet` Validation

| Test Case | Description | Expected Outcome |
|---|---|---|
| **Transfer Exceeding Balance** | Attempt to send more ETH or tokens than the wallet holds. | Transaction fails before being sent. The mock should raise an `InsufficientFundsError`. The real wallet should prevent the transaction. |
| **Transfer with Insufficient Gas** | Attempt a transaction where `value + gas_cost > balance`. | Transaction fails. The mock should raise an `InsufficientFundsError`. The real wallet should prevent the transaction. |

### 5.3. `SecurityBreachMockWallet` Validation

| Test Case | Description | Expected Outcome |
|---|---|---|
| **Simulated Compromise** | This is a mock-only scenario. | The mock should raise a `SecurityBreachError` or similar exception when a transaction is attempted. |

### 5.4. `NetworkFailureMockWallet` Validation

| Test Case | Description | Expected Outcome |
|---|---|---|
| **Simulated Network Failure** | This is a mock-only scenario. | The mock should raise a `NetworkError` or `ConnectionError` when a transaction is attempted. |

## 6. Comparison and Validation Methodology

### 6.1. Comparison Criteria

| Criteria | `MockWallet` | Real Wallet (Testnet) |
|---|---|---|
| **Transaction Receipt** | - `status`: `1` for success, `0` for failure. <br> - `gasUsed`: Estimated or pre-defined. <br> - `logs`: Mocked log entries. | - `status`: `1` for success, `0` for failure. <br> - `gasUsed`: Actual gas consumed. <br> - `logs`: Actual logs emitted by the contract. |
| **State Changes** | - `balance`: Updated based on the transaction value and gas cost. | - `balance`: Updated based on the transaction value and gas cost. |
| **Error Handling** | - Raises specific exceptions (e.g., `InsufficientFundsError`). | - The underlying library (`web3.py`) raises exceptions for issues like insufficient funds before sending. |

### 6.2. Success and Discrepancy Definitions

- **Successful Validation**: The mock wallet's behavior and state changes are consistent with the real wallet's behavior and state changes for the same operation. Minor differences in `gasUsed` are acceptable.
- **Discrepancy**: Any significant deviation in transaction outcome (`status`), state changes, or error handling between the mock and real wallet.

## 7. Task Blocks

| ID | Description | Owner Mode | Deliverable | Acceptance Test |
|---|---|---|---|---|
| **TB-1** | Fund all testnet wallets. | Code | Wallets funded with sufficient testnet ETH and tokens. | Balances are confirmed on-chain. |
| **TB-2** | Implement the validation test suite. | Code | A new `pytest` suite that runs the tests defined in section 5. | Tests run against both mock and real wallets. |
| **TB-3** | Execute the validation tests. | Code | Test results are collected and analyzed. | A report of the test results is generated. |
| **TB-4** | Identify and document discrepancies. | Architect | A list of discrepancies between the mock and real wallets. | Discrepancies are documented in a new issue. |
| **TB-5** | Fix discrepancies in the `MockWallet` framework. | Code | Pull requests that fix the identified discrepancies. | The validation tests pass with no discrepancies. |

## 8. PCRM Analysis

- **Pros**:
  - Increased confidence in our testing framework.
  - Early detection of inconsistencies between mock and real environments.
  - Improved reliability of the entire application.
- **Cons**:
  - Time-consuming to set up and execute.
  - Dependent on the stability of public testnets and faucets.
- **Risks**:
  - Testnet instability could block or delay validation.
  - Faucets may be unreliable or have rate limits.
- **Mitigations**:
  - Select stable, well-supported testnets.
  - Fund wallets in advance and maintain a buffer of testnet funds.
  - Document alternative faucets where available.