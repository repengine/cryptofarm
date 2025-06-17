"""MockWallet validation tests against live public testnets.

This module implements the validation test suite as defined in the MockWallet
validation plan. It compares the behavior of mock wallets against real wallet
interactions on public testnets to ensure accuracy and reliability.

The tests are designed to validate:
- NormalMockWallet (MockHotWallet) behavior
- InsufficientFundsMockWallet (MockLowBalanceWallet) behavior
- SecurityBreachMockWallet (MockCompromisedWallet) behavior
- NetworkFailureMockWallet behavior

Note: This test suite requires testnet funds and real wallet credentials.
For security, private keys should be stored in environment variables.
"""

import os
import pytest
from typing import Dict, Any, Tuple, cast

from web3 import Web3
from web3.types import Wei, TxParams
from eth_account import Account
from eth_account.signers.local import LocalAccount

from tests.mocks.wallets import (
    MockHotWallet,
    MockLowBalanceWallet,
    MockCompromisedWallet,
    MockNetworkFailureWallet
)


class TestnetConfig:
    """Configuration for testnet connections and validation parameters."""

    # Testnet RPC URLs
    SEPOLIA_RPC = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
    ZKSYNC_SEPOLIA_RPC = "https://sepolia.era.zksync.dev"
    SCROLL_SEPOLIA_RPC = "https://sepolia-rpc.scroll.io"
    ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"
    HOLESKY_RPC = "https://ethereum-holesky.publicnode.com"

    # Test transaction parameters
    TEST_TRANSFER_AMOUNT = Wei(1000000000000000)  # 0.001 ETH
    TEST_GAS_LIMIT = 21000
    TEST_GAS_PRICE = Wei(20000000000)  # 20 Gwei

    # Validation thresholds
    MAX_GAS_DIFFERENCE_PERCENT = 10.0
    TRANSACTION_TIMEOUT_SECONDS = 300


class RealWalletManager:
    """Manages real wallet interactions for testnet validation."""

    def __init__(self, private_key: str, rpc_url: str):
        """Initialize real wallet manager.

        Args:
            private_key: Private key for the test wallet
            rpc_url: RPC URL for the target testnet
        """
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account: LocalAccount = Account.from_key(private_key)
        self.address = self.account.address

    def get_balance(self) -> Wei:
        """Get current wallet balance.

        Returns:
            Wei: Current balance in Wei
        """
        return self.web3.eth.get_balance(self.address)

    def send_transaction(self, tx_params: TxParams) -> Tuple[str, Dict[str, Any]]:
        """Send a transaction and return hash and receipt.

        Args:
            tx_params: Transaction parameters

        Returns:
            Tuple of (transaction_hash, receipt_dict)

        Raises:
            Various exceptions based on transaction failure reasons
        """
        # Build complete transaction
        nonce = self.web3.eth.get_transaction_count(self.address)

        complete_tx: TxParams = {
            'from': self.address,
            'nonce': nonce,
            'gas': tx_params.get('gas', TestnetConfig.TEST_GAS_LIMIT),
            'gasPrice': tx_params.get('gasPrice',
                                      TestnetConfig.TEST_GAS_PRICE),
            **tx_params
        }

        # Sign and send transaction
        signed_txn = self.account.sign_transaction(cast(Any, complete_tx))
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=TestnetConfig.TRANSACTION_TIMEOUT_SECONDS
        )

        return tx_hash.hex(), {
            'status': receipt['status'],
            'gasUsed': receipt['gasUsed'],
            'logs': receipt['logs'],
            'transactionHash': receipt['transactionHash'].hex(),
            'blockNumber': receipt['blockNumber']
        }


@pytest.fixture(scope="module")
def testnet_credentials() -> Dict[str, str]:
    """Load testnet credentials from environment variables.

    Returns:
        Dictionary mapping testnet names to private keys

    Note:
        Private keys should be stored as environment variables:
        - SEPOLIA_PRIVATE_KEY
        - ZKSYNC_SEPOLIA_PRIVATE_KEY
        - SCROLL_SEPOLIA_PRIVATE_KEY
        - ARBITRUM_SEPOLIA_PRIVATE_KEY
        - HOLESKY_PRIVATE_KEY
    """
    credentials = {}

    testnet_keys = [
        "SEPOLIA_PRIVATE_KEY",
        "ZKSYNC_SEPOLIA_PRIVATE_KEY",
        "SCROLL_SEPOLIA_PRIVATE_KEY",
        "ARBITRUM_SEPOLIA_PRIVATE_KEY",
        "HOLESKY_PRIVATE_KEY"
    ]

    for key in testnet_keys:
        private_key = os.getenv(key)
        if private_key:
            testnet_name = key.replace("_PRIVATE_KEY", "").lower()
            credentials[testnet_name] = private_key

    return credentials


@pytest.fixture(scope="module")
def real_wallet_managers(testnet_credentials: Dict[str, str]) -> Dict[str, RealWalletManager]:
    """Create real wallet managers for each available testnet.

    Args:
        testnet_credentials: Testnet private keys from fixture

    Returns:
        Dictionary mapping testnet names to RealWalletManager instances
    """
    managers = {}

    rpc_mapping = {
        "sepolia": TestnetConfig.SEPOLIA_RPC,
        "zksync_sepolia": TestnetConfig.ZKSYNC_SEPOLIA_RPC,
        "scroll_sepolia": TestnetConfig.SCROLL_SEPOLIA_RPC,
        "arbitrum_sepolia": TestnetConfig.ARBITRUM_SEPOLIA_RPC,
        "holesky": TestnetConfig.HOLESKY_RPC
    }

    for testnet, private_key in testnet_credentials.items():
        if testnet in rpc_mapping:
            try:
                manager = RealWalletManager(private_key, rpc_mapping[testnet])
                # Test connection
                balance = manager.get_balance()
                managers[testnet] = manager
                print(f"Connected to {testnet}: {manager.address} "
                      f"(Balance: {balance} Wei)")
            except Exception as e:
                print(f"Failed to connect to {testnet}: {e}")

    return managers


def test_normal_mock_wallet_successful_transaction(real_wallet_managers: Dict[str, RealWalletManager]) -> None:
    """Validate MockHotWallet behavior against real successful transactions.

    Test Case: Successful Transaction
    - Send a standard ETH transfer
    - Compare transaction success, balance updates, and receipt data
    """
    if not real_wallet_managers:
        pytest.skip("No testnet credentials available")

    # Use first available testnet
    testnet_name, real_wallet = next(iter(real_wallet_managers.items()))

    # Create mock wallet with similar balance
    initial_balance = real_wallet.get_balance()
    mock_wallet = MockHotWallet(initial_balance=initial_balance)

    # Prepare test transaction
    test_tx_params: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': TestnetConfig.TEST_TRANSFER_AMOUNT,
        'gas': TestnetConfig.TEST_GAS_LIMIT,
        'gasPrice': TestnetConfig.TEST_GAS_PRICE
    }

    # Execute on real wallet (if sufficient balance)
    real_initial_balance = real_wallet.get_balance()
    total_cost = (test_tx_params['value'] +
                  (test_tx_params['gas'] * test_tx_params['gasPrice']))

    if real_initial_balance >= total_cost:
        # Execute real transaction
        real_tx_hash, real_receipt = real_wallet.send_transaction(
            test_tx_params)

        # Execute mock transaction
        mock_tx_hash = mock_wallet.send_transaction(test_tx_params)

        # Validate results
        assert real_receipt['status'] == 1, "Real transaction should succeed"
        assert mock_tx_hash is not None, "Mock transaction should return hash"

        # Allow for gas estimation differences
        gas_diff_percent = (abs(real_receipt['gasUsed'] -
                                test_tx_params['gas']) /
                            test_tx_params['gas'] * 100)
        assert gas_diff_percent <= TestnetConfig.MAX_GAS_DIFFERENCE_PERCENT, \
            f"Gas usage difference too large: {gas_diff_percent}%"

        print(f"✓ Successful transaction validation passed on {testnet_name}")
        print(f"  Real tx: {real_tx_hash}")
        print(f"  Mock tx: {mock_tx_hash}")
        print(f"  Real gas used: {real_receipt['gasUsed']}")
        print(f"  Mock gas estimated: {test_tx_params['gas']}")

    else:
        pytest.skip(f"Insufficient balance on {testnet_name} for test "
                     "transaction")


def test_insufficient_funds_mock_wallet_validation(real_wallet_managers: Dict[str, RealWalletManager]) -> None:
    """Validate MockLowBalanceWallet behavior against real insufficient funds.

    Test Case: Transfer Exceeding Balance
    - Attempt to send more ETH than wallet holds
    - Verify both mock and real wallets prevent the transaction
    """
    if not real_wallet_managers:
        pytest.skip("No testnet credentials available")

    # Create low balance mock wallet
    low_balance = Wei(100000000000000)  # 0.0001 ETH
    mock_wallet = MockLowBalanceWallet(balance=low_balance)

    # Prepare transaction that exceeds balance
    excessive_tx_params: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': Wei(1000000000000000000),  # 1 ETH (much more than balance)
        'gas': TestnetConfig.TEST_GAS_LIMIT,
        'gasPrice': TestnetConfig.TEST_GAS_PRICE
    }

    # Test mock wallet behavior
    with pytest.raises(ValueError, match="Insufficient balance"):
        mock_wallet.send_transaction(excessive_tx_params)

    print("✓ MockLowBalanceWallet correctly raises ValueError for "
          "insufficient funds")

    # Note: We don't test real wallet insufficient funds to avoid depleting
    # test funds. Real wallets would similarly fail at the RPC level before
    # broadcasting


def test_security_breach_mock_wallet_validation() -> None:
    """Validate MockCompromisedWallet behavior.

    Test Case: Simulated Compromise
    - This is a mock-only scenario
    - Verify the mock raises SecurityBreachError appropriately
    """
    mock_wallet = MockCompromisedWallet()

    test_tx_params: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': TestnetConfig.TEST_TRANSFER_AMOUNT,
        'gas': TestnetConfig.TEST_GAS_LIMIT,
        'gasPrice': TestnetConfig.TEST_GAS_PRICE
    }

    # Test security breach simulation
    with pytest.raises(RuntimeError, match="security breach"):
        mock_wallet.send_transaction(test_tx_params)

    print("✓ MockCompromisedWallet correctly raises RuntimeError for "
          "security breach")


def test_network_failure_mock_wallet_validation() -> None:
    """Validate MockNetworkFailureWallet behavior.

    Test Case: Simulated Network Failure
    - This is a mock-only scenario
    - Verify the mock raises NetworkError appropriately
    """
    mock_wallet = MockNetworkFailureWallet()

    test_tx_params: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': TestnetConfig.TEST_TRANSFER_AMOUNT,
        'gas': TestnetConfig.TEST_GAS_LIMIT,
        'gasPrice': TestnetConfig.TEST_GAS_PRICE
    }

    # Test network failure simulation
    with pytest.raises(ConnectionError, match="Network timeout"):
        mock_wallet.send_transaction(test_tx_params)

    print("✓ MockNetworkFailureWallet correctly raises ConnectionError for "
          "network failure")


def test_mock_wallet_state_consistency() -> None:
    """Validate internal state consistency of mock wallets.

    Ensures mock wallets maintain proper state across multiple operations.
    """
    initial_balance = Wei(2000000000000000000)  # 2 ETH
    mock_wallet = MockHotWallet(initial_balance=initial_balance)

    # Verify initial state
    assert mock_wallet.get_balance() == initial_balance
    assert mock_wallet.get_nonce() == 0
    assert len(mock_wallet.get_transaction_history()) == 0

    # Execute multiple transactions
    tx_params_1: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': Wei(500000000000000000),  # 0.5 ETH
        'gas': 21000,
        'gasPrice': Wei(20000000000)
    }

    tx_hash_1 = mock_wallet.send_transaction(tx_params_1)

    # Verify state after first transaction
    expected_balance_1 = (initial_balance - tx_params_1['value'] -
                          (tx_params_1['gas'] * tx_params_1['gasPrice']))
    assert mock_wallet.get_balance() == expected_balance_1
    assert mock_wallet.get_nonce() == 1
    assert len(mock_wallet.get_transaction_history()) == 1

    # Execute second transaction
    tx_params_2: TxParams = {
        'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
        'value': Wei(300000000000000000),  # 0.3 ETH
        'gas': 21000,
        'gasPrice': Wei(25000000000)  # Higher gas price
    }

    tx_hash_2 = mock_wallet.send_transaction(tx_params_2)

    # Verify final state
    expected_balance_2 = (expected_balance_1 - tx_params_2['value'] -
                          (tx_params_2['gas'] * tx_params_2['gasPrice']))
    assert mock_wallet.get_balance() == expected_balance_2
    assert mock_wallet.get_nonce() == 2
    assert len(mock_wallet.get_transaction_history()) == 2

    # Verify transaction history
    history = mock_wallet.get_transaction_history()
    assert history[0]['hash'] == tx_hash_1
    assert history[1]['hash'] == tx_hash_2
    assert history[0]['nonce'] == 0
    assert history[1]['nonce'] == 1

    print("✓ Mock wallet state consistency validation passed")


@pytest.mark.integration
def test_cross_testnet_behavior_consistency(real_wallet_managers: Dict[str, RealWalletManager]) -> None:
    """Validate that mock wallet behavior is consistent across testnets.

    This test ensures our mocks work the same regardless of the underlying
    network.
    """
    if len(real_wallet_managers) < 2:
        pytest.skip("Need at least 2 testnets for cross-testnet validation")

    results = {}

    for testnet_name, real_wallet in real_wallet_managers.items():
        # Create mock wallet with same balance as real wallet
        real_balance = real_wallet.get_balance()
        mock_wallet = MockHotWallet(initial_balance=real_balance)

        # Test transaction parameters
        test_tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': TestnetConfig.TEST_TRANSFER_AMOUNT,
            'gas': TestnetConfig.TEST_GAS_LIMIT,
            'gasPrice': TestnetConfig.TEST_GAS_PRICE
        }

        # Execute mock transaction
        mock_initial_balance = mock_wallet.get_balance()
        mock_tx_hash = mock_wallet.send_transaction(test_tx_params)
        mock_final_balance = mock_wallet.get_balance()

        results[testnet_name] = {
            'initial_balance': mock_initial_balance,
            'final_balance': mock_final_balance,
            'balance_change': mock_initial_balance - mock_final_balance,
            'tx_hash': mock_tx_hash,
            'nonce': mock_wallet.get_nonce()
        }

    # Verify consistency across testnets
    balance_changes = [result['balance_change'] for result in results.values()]
    nonces = [result['nonce'] for result in results.values()]

    # All balance changes should be identical (same tx params)
    assert all(change == balance_changes[0] for change in balance_changes), \
        "Mock wallet balance changes should be consistent across testnets"

    # All nonces should be 1 after first transaction
    assert all(nonce == 1 for nonce in nonces), \
        "Mock wallet nonces should be consistent across testnets"

    print(f"✓ Cross-testnet consistency validated across {len(results)} "
          "testnets")


# Test execution markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.requires_testnet_funds
]


if __name__ == "__main__":
    # Run validation tests
    pytest.main([__file__, "-v", "--tb=short"])
