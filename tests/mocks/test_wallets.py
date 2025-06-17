"""Tests for mock wallet implementations."""

import pytest
from web3.types import Wei, TxParams
from .wallets import (
    MockHotWallet,
    MockLowBalanceWallet,
    MockCompromisedWallet,
    MockNetworkFailureWallet
)


class TestMockHotWallet:
    """Test cases for MockHotWallet functionality."""

    def test_initialization(self) -> None:
        """Test wallet initialization with default balance."""
        wallet = MockHotWallet()
        assert wallet.get_balance() == Wei(1000000000000000000)  # 1 ETH
        assert wallet.get_nonce() == 0
        assert len(wallet.get_transaction_history()) == 0

    def test_custom_initial_balance(self) -> None:
        """Test wallet initialization with custom balance."""
        custom_balance = Wei(500000000000000000)  # 0.5 ETH
        wallet = MockHotWallet(initial_balance=custom_balance)
        assert wallet.get_balance() == custom_balance

    def test_get_address(self) -> None:
        """Test address generation and retrieval."""
        wallet = MockHotWallet()
        address = wallet.get_address()
        assert isinstance(address, str)
        assert address.startswith('0x')
        assert len(address) == 42

    def test_successful_transaction(self) -> None:
        """Test successful transaction execution."""
        wallet = MockHotWallet()
        initial_balance = wallet.get_balance()

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),  # 0.1 ETH
            'gas': 21000,
            'gasPrice': Wei(20000000000)  # 20 Gwei
        }

        tx_hash = wallet.send_transaction(tx_params)

        # Check transaction hash format
        assert isinstance(tx_hash, str)
        assert tx_hash.startswith('0x')
        assert len(tx_hash) == 66

        # Check balance was deducted
        expected_cost = Wei(100000000000000000 + (21000 * 20000000000))
        assert wallet.get_balance() == initial_balance - expected_cost

        # Check nonce incremented
        assert wallet.get_nonce() == 1

        # Check transaction history
        history = wallet.get_transaction_history()
        assert len(history) == 1
        assert history[0]['hash'] == tx_hash
        assert history[0]['value'] == Wei(100000000000000000)

    def test_insufficient_balance_transaction(self) -> None:
        """Test transaction failure due to insufficient balance."""
        wallet = MockHotWallet(initial_balance=Wei(1000000000000000))  # 0.001 ETH

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(1000000000000000000),  # 1 ETH (more than balance)
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        }

        with pytest.raises(ValueError, match="Insufficient balance"):
            wallet.send_transaction(tx_params)

        # Balance should remain unchanged
        assert wallet.get_balance() == Wei(1000000000000000)
        assert wallet.get_nonce() == 0

    def test_multiple_transactions(self) -> None:
        """Test multiple sequential transactions."""
        wallet = MockHotWallet()
        initial_nonce = wallet.get_nonce()

        # Send first transaction
        wallet.send_transaction({
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        })

        # Send second transaction
        wallet.send_transaction({
            'to': '0x8ba1f109551bD432803012645Hac136c',
            'value': Wei(200000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        })

        # Check nonce incremented correctly
        assert wallet.get_nonce() == initial_nonce + 2

        # Check transaction history
        history = wallet.get_transaction_history()
        assert len(history) == 2
        assert history[0]['nonce'] == 0
        assert history[1]['nonce'] == 1

    def test_transaction_deterministic_hash(self) -> None:
        """Test that transaction hashes are deterministic."""
        wallet1 = MockHotWallet()
        wallet2 = MockHotWallet()

        # Same transaction parameters
        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        }

        # Different wallets should produce different hashes
        hash1 = wallet1.send_transaction(tx_params.copy())
        hash2 = wallet2.send_transaction(tx_params.copy())
        assert hash1 != hash2  # Different addresses = different hashes


class TestMockLowBalanceWallet:
    """Test cases for MockLowBalanceWallet functionality."""

    def test_initialization(self) -> None:
        """Test low balance wallet initialization."""
        wallet = MockLowBalanceWallet()
        assert wallet.get_balance() == Wei(100000000000000)  # 0.0001 ETH
        assert wallet.get_nonce() == 0

    def test_custom_low_balance(self) -> None:
        """Test initialization with custom low balance."""
        custom_balance = Wei(50000000000000)  # 0.00005 ETH
        wallet = MockLowBalanceWallet(balance=custom_balance)
        assert wallet.get_balance() == custom_balance

    def test_insufficient_funds_error(self) -> None:
        """Test that most transactions fail due to insufficient funds."""
        wallet = MockLowBalanceWallet()

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),  # 0.1 ETH
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        }

        with pytest.raises(ValueError, match="Insufficient balance"):
            wallet.send_transaction(tx_params)

    def test_successful_micro_transaction(self) -> None:
        """Test that very small transactions can succeed."""
        wallet = MockLowBalanceWallet(balance=Wei(1000000000000000))  # 0.001 ETH

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(1000000000000),  # 0.000001 ETH
            'gas': 21000,
            'gasPrice': Wei(1000000000)  # 1 Gwei (low gas price)
        }

        # This should succeed as total cost is within balance
        tx_hash = wallet.send_transaction(tx_params)
        assert isinstance(tx_hash, str)
        assert tx_hash.startswith('0x')


class TestMockCompromisedWallet:
    """Test cases for MockCompromisedWallet functionality."""

    def test_initialization(self) -> None:
        """Test compromised wallet initialization."""
        wallet = MockCompromisedWallet()
        assert wallet.get_balance() == Wei(500000000000000000)  # 0.5 ETH
        assert wallet.is_compromised is True

    def test_balance_accessible(self) -> None:
        """Test that balance can still be checked."""
        wallet = MockCompromisedWallet()
        balance = wallet.get_balance()
        assert isinstance(balance, int)
        assert balance > 0

    def test_transaction_security_error(self) -> None:
        """Test that transactions fail with security error."""
        wallet = MockCompromisedWallet()

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        }

        with pytest.raises(RuntimeError, match="security breach"):
            wallet.send_transaction(tx_params)

    def test_address_still_accessible(self) -> None:
        """Test that address is still accessible despite compromise."""
        wallet = MockCompromisedWallet()
        address = wallet.get_address()
        assert isinstance(address, str)
        assert address.startswith('0x')


class TestMockNetworkFailureWallet:
    """Test cases for MockNetworkFailureWallet functionality."""

    def test_initialization(self) -> None:
        """Test network failure wallet initialization."""
        wallet = MockNetworkFailureWallet()
        assert wallet.get_balance() == Wei(2000000000000000000)  # 2 ETH

    def test_balance_accessible(self) -> None:
        """Test that balance queries work despite network issues."""
        wallet = MockNetworkFailureWallet()
        balance = wallet.get_balance()
        assert isinstance(balance, int)
        assert balance > 0

    def test_transaction_network_error(self) -> None:
        """Test that transactions fail with network error."""
        wallet = MockNetworkFailureWallet()

        tx_params: TxParams = {
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        }

        with pytest.raises(ConnectionError, match="Network timeout"):
            wallet.send_transaction(tx_params)

    def test_address_accessible(self) -> None:
        """Test that address is accessible despite network issues."""
        wallet = MockNetworkFailureWallet()
        address = wallet.get_address()
        assert isinstance(address, str)
        assert address.startswith('0x')


class TestWalletIntegration:
    """Integration tests across different wallet types."""

    def test_all_wallets_have_unique_addresses(self) -> None:
        """Test that different wallet instances have unique addresses."""
        wallets = [
            MockHotWallet(),
            MockLowBalanceWallet(),
            MockCompromisedWallet(),
            MockNetworkFailureWallet()
        ]

        addresses = [wallet.get_address() for wallet in wallets]
        assert len(set(addresses)) == len(addresses)  # All unique

    def test_wallet_interface_consistency(self) -> None:
        """Test that all wallets implement the same interface."""
        wallets = [
            MockHotWallet(),
            MockLowBalanceWallet(),
            MockCompromisedWallet(),
            MockNetworkFailureWallet()
        ]

        for wallet in wallets:
            # All should have these methods
            assert hasattr(wallet, 'get_balance')
            assert hasattr(wallet, 'send_transaction')
            assert hasattr(wallet, 'get_address')
            assert hasattr(wallet, 'get_nonce')
            assert hasattr(wallet, 'get_transaction_history')

            # All should return proper types
            assert isinstance(wallet.get_balance(), int)
            assert isinstance(wallet.get_address(), str)
            assert isinstance(wallet.get_nonce(), int)
            assert isinstance(wallet.get_transaction_history(), list)

    def test_transaction_history_isolation(self) -> None:
        """Test that transaction histories are isolated between wallets."""
        wallet1 = MockHotWallet()
        wallet2 = MockHotWallet()

        # Send transaction from wallet1
        wallet1.send_transaction({
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        })

        # Check histories are separate
        assert len(wallet1.get_transaction_history()) == 1
        assert len(wallet2.get_transaction_history()) == 0

    def test_nonce_isolation(self) -> None:
        """Test that nonces are isolated between wallets."""
        wallet1 = MockHotWallet()
        wallet2 = MockHotWallet()

        # Send transaction from wallet1
        wallet1.send_transaction({
            'to': '0x742d35Cc6634C0532925a3b8D4C9db96DfE55Af6',
            'value': Wei(100000000000000000),
            'gas': 21000,
            'gasPrice': Wei(20000000000)
        })

        # Check nonces are separate
        assert wallet1.get_nonce() == 1
        assert wallet2.get_nonce() == 0
