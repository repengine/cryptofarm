"""
Tests for the ZkSync lending functionality.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, Mock
from web3 import Web3

from airdrops.protocols.zksync.zksync import ZkSyncProtocol, lend_borrow
from airdrops.protocols.zksync.lending_adapter import ZkSyncLendingAdapter, ZerolendAdapter
from airdrops.protocols.zksync.exceptions import (
    ZkSyncLendingError,
    InsufficientBalanceError
)


@pytest.fixture
def mock_web3_l2():
    """Mock Web3 instance for L2."""
    web3 = Mock()
    web3.to_wei.return_value = 1000000000000000000  # 1 ETH in wei
    web3.eth = Mock()
    web3.eth.get_balance.return_value = 2000000000000000000  # 2 ETH
    web3.eth.gas_price = 20000000000  # 20 gwei
    return web3


@pytest.fixture
def zksync_protocol_lending():
    """Fixture for a ZkSyncProtocol instance with mocked web3."""
    with patch('airdrops.protocols.zksync.zksync.Web3') as mock_web3_class:
        mock_web3_l1 = Mock(spec=Web3)
        mock_web3_l2 = Mock(spec=Web3)
        mock_web3_class.return_value = mock_web3_l2
        
        protocol = ZkSyncProtocol(
            l1_rpc_url="http://mock-l1-rpc.com",
            l2_rpc_url="http://mock-l2-rpc.com",
            private_key="0x" + "1" * 64,
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2
        )
        return protocol


class TestZerolendAdapter:
    """Test cases for the ZerolendAdapter class."""

    def test_adapter_initialization(self, mock_web3_l2):
        """Test that the ZerolendAdapter initializes correctly."""
        adapter = ZerolendAdapter(mock_web3_l2)
        assert adapter.web3_l2 == mock_web3_l2
        assert adapter.PROTOCOL_NAME == "zerolend"

    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_contract')
    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_l2_token_address')
    def test_lend_eth_transaction(self, mock_get_token_address, mock_get_contract, mock_web3_l2):
        """Test building a lend transaction for ETH."""
        # Setup mocks
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_contract = Mock()
        mock_contract.functions.depositETH.return_value.build_transaction.return_value = {
            "to": "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319",
            "value": 1000000000000000000,
            "gas": 300000
        }
        mock_get_contract.return_value = mock_contract
        
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Test ETH lending
        tx_params = adapter.lend(
            token_address="0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",  # WETH address
            amount=1000000000000000000,  # 1 ETH
            from_address="0x1234567890123456789012345678901234567890"
        )
        
        assert tx_params["to"] == "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319"
        assert tx_params["value"] == 1000000000000000000
        mock_contract.functions.depositETH.assert_called_once()

    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_contract')
    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_l2_token_address')
    def test_lend_erc20_transaction(self, mock_get_token_address, mock_get_contract, mock_web3_l2):
        """Test building a lend transaction for ERC20 tokens."""
        # Setup mocks
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_contract = Mock()
        mock_contract.functions.supply.return_value.build_transaction.return_value = {
            "to": "0x4d9429246EA989C9CeE203B43F6d1C7D83e3B8F8",
            "gas": 300000
        }
        mock_get_contract.return_value = mock_contract
        
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Test USDC lending (not ETH)
        tx_params = adapter.lend(
            token_address="0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",  # USDC address
            amount=1000000000,  # 1000 USDC
            from_address="0x1234567890123456789012345678901234567890"
        )
        
        assert tx_params["to"] == "0x4d9429246EA989C9CeE203B43F6d1C7D83e3B8F8"
        mock_contract.functions.supply.assert_called_once()

    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_contract')
    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_l2_token_address')
    def test_withdraw_eth_transaction(self, mock_get_token_address, mock_get_contract, mock_web3_l2):
        """Test building a withdraw transaction for ETH."""
        # Setup mocks
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_contract = Mock()
        mock_contract.functions.withdrawETH.return_value.build_transaction.return_value = {
            "to": "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319",
            "gas": 300000
        }
        mock_get_contract.return_value = mock_contract
        
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Test ETH withdrawal
        tx_params = adapter.withdraw(
            token_address="0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",  # WETH address
            amount=500000000000000000,  # 0.5 ETH
            from_address="0x1234567890123456789012345678901234567890"
        )
        
        assert tx_params["to"] == "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319"
        mock_contract.functions.withdrawETH.assert_called_once()

    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_contract')
    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_l2_token_address')
    def test_borrow_transaction(self, mock_get_token_address, mock_get_contract, mock_web3_l2):
        """Test building a borrow transaction."""
        # Setup mocks
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_contract = Mock()
        mock_contract.functions.borrowETH.return_value.build_transaction.return_value = {
            "to": "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319",
            "gas": 400000
        }
        mock_get_contract.return_value = mock_contract
        
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Test ETH borrowing
        tx_params = adapter.borrow(
            token_address="0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",  # WETH address
            amount=200000000000000000,  # 0.2 ETH
            from_address="0x1234567890123456789012345678901234567890"
        )
        
        assert tx_params["to"] == "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319"
        assert tx_params["gas"] == 400000
        mock_contract.functions.borrowETH.assert_called_once()

    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_contract')
    @patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter._get_l2_token_address')
    def test_repay_transaction(self, mock_get_token_address, mock_get_contract, mock_web3_l2):
        """Test building a repay transaction."""
        # Setup mocks
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_contract = Mock()
        mock_contract.functions.repayETH.return_value.build_transaction.return_value = {
            "to": "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319",
            "value": 200000000000000000,
            "gas": 300000
        }
        mock_get_contract.return_value = mock_contract
        
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Test ETH repayment
        tx_params = adapter.repay(
            token_address="0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",  # WETH address
            amount=200000000000000000,  # 0.2 ETH
            from_address="0x1234567890123456789012345678901234567890"
        )
        
        assert tx_params["to"] == "0x1908e2BF4a88F91E4eF0DC72f02b8Ea36BEa2319"
        assert tx_params["value"] == 200000000000000000
        mock_contract.functions.repayETH.assert_called_once()


class TestZkSyncProtocolLending:
    """Test cases for the ZkSyncProtocol lending methods."""

    @patch('airdrops.protocols.zksync.zksync.lend_borrow')
    def test_lend_method(self, mock_lend_borrow, zksync_protocol_lending):
        """Test the lend method of ZkSyncProtocol."""
        mock_lend_borrow.return_value = "0x" + "a" * 64
        
        tx_hash = zksync_protocol_lending.lend(
            token="ETH",
            amount=Decimal("1.0"),
            protocol="zerolend"
        )
        
        assert tx_hash == "0x" + "a" * 64
        mock_lend_borrow.assert_called_once_with(
            web3_zksync=zksync_protocol_lending.web3_l2,
            private_key=zksync_protocol_lending.private_key,
            action="lend",
            token_symbol="ETH",
            amount=Decimal("1.0"),
            protocol="zerolend"
        )

    @patch('airdrops.protocols.zksync.zksync.lend_borrow')
    def test_withdraw_method(self, mock_lend_borrow, zksync_protocol_lending):
        """Test the withdraw method of ZkSyncProtocol."""
        mock_lend_borrow.return_value = "0x" + "b" * 64
        
        tx_hash = zksync_protocol_lending.withdraw(
            token="USDC",
            amount=Decimal("500.0"),
            protocol="zerolend"
        )
        
        assert tx_hash == "0x" + "b" * 64
        mock_lend_borrow.assert_called_once_with(
            web3_zksync=zksync_protocol_lending.web3_l2,
            private_key=zksync_protocol_lending.private_key,
            action="withdraw",
            token_symbol="USDC",
            amount=Decimal("500.0"),
            protocol="zerolend"
        )

    @patch('airdrops.protocols.zksync.zksync.lend_borrow')
    def test_borrow_method(self, mock_lend_borrow, zksync_protocol_lending):
        """Test the borrow method of ZkSyncProtocol."""
        mock_lend_borrow.return_value = "0x" + "c" * 64
        
        tx_hash = zksync_protocol_lending.borrow(
            token="ETH",
            amount=Decimal("0.5"),
            protocol="zerolend"
        )
        
        assert tx_hash == "0x" + "c" * 64
        mock_lend_borrow.assert_called_once_with(
            web3_zksync=zksync_protocol_lending.web3_l2,
            private_key=zksync_protocol_lending.private_key,
            action="borrow",
            token_symbol="ETH",
            amount=Decimal("0.5"),
            protocol="zerolend"
        )

    @patch('airdrops.protocols.zksync.zksync.lend_borrow')
    def test_repay_method(self, mock_lend_borrow, zksync_protocol_lending):
        """Test the repay method of ZkSyncProtocol."""
        mock_lend_borrow.return_value = "0x" + "d" * 64
        
        tx_hash = zksync_protocol_lending.repay(
            token="ETH",
            amount=Decimal("0.3"),
            protocol="zerolend"
        )
        
        assert tx_hash == "0x" + "d" * 64
        mock_lend_borrow.assert_called_once_with(
            web3_zksync=zksync_protocol_lending.web3_l2,
            private_key=zksync_protocol_lending.private_key,
            action="repay",
            token_symbol="ETH",
            amount=Decimal("0.3"),
            protocol="zerolend"
        )


class TestLendBorrowFunction:
    """Test cases for the lend_borrow module-level function."""

    @patch('airdrops.protocols.zksync.zksync._build_and_send_tx_zksync')
    @patch('airdrops.protocols.zksync.zksync._approve_erc20_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_eth_success(self, mock_get_account, mock_get_token_address, 
                                   mock_approve, mock_build_send, mock_web3_l2):
        """Test successful ETH lending operation."""
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        mock_build_send.return_value = "0x" + "a" * 64
        
        mock_web3_l2.to_wei.return_value = 1000000000000000000  # 1 ETH
        mock_web3_l2.eth.get_balance.return_value = 2000000000000000000  # 2 ETH
        
        with patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.lend.return_value = {"to": "0x123", "value": 1000000000000000000}
            mock_adapter_class.return_value = mock_adapter
            
            tx_hash = lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="lend",
                token_symbol="ETH",
                amount=Decimal("1.0"),
                protocol="zerolend"
            )
            
            assert tx_hash == "0x" + "a" * 64
            mock_adapter.lend.assert_called_once()
            mock_build_send.assert_called_once()

    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_invalid_action(self, mock_get_account, mock_web3_l2):
        """Test lend_borrow with invalid action."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        with pytest.raises(ValueError, match="Invalid action"):
            lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="invalid_action",
                token_symbol="ETH",
                amount=Decimal("1.0"),
                protocol="zerolend"
            )

    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_invalid_protocol(self, mock_get_account, mock_web3_l2):
        """Test lend_borrow with unsupported protocol."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        with pytest.raises(ValueError, match="Unsupported protocol"):
            lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="lend",
                token_symbol="ETH",
                amount=Decimal("1.0"),
                protocol="unsupported_protocol"
            )

    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_negative_amount(self, mock_get_account, mock_web3_l2):
        """Test lend_borrow with negative amount."""
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="lend",
                token_symbol="ETH",
                amount=Decimal("-1.0"),
                protocol="zerolend"
            )

    @patch('airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_insufficient_balance(self, mock_get_account, mock_get_token_address, mock_web3_l2):
        """Test lend_borrow with insufficient balance."""
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        
        mock_web3_l2.to_wei.return_value = 2000000000000000000  # 2 ETH
        mock_web3_l2.eth.get_balance.return_value = 1000000000000000000  # 1 ETH (insufficient)
        
        with pytest.raises(InsufficientBalanceError):
            lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="lend",
                token_symbol="ETH",
                amount=Decimal("2.0"),  # Trying to lend more than balance
                protocol="zerolend"
            )

    @patch('airdrops.protocols.zksync.zksync._build_and_send_tx_zksync')
    @patch('airdrops.protocols.zksync.zksync._approve_erc20_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_contract_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_erc20_success(self, mock_get_account, mock_get_token_address, 
                                     mock_get_contract, mock_approve, mock_build_send, mock_web3_l2):
        """Test successful ERC20 lending operation."""
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        mock_get_token_address.return_value = "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"  # USDC
        mock_build_send.return_value = "0x" + "b" * 64
        
        # Mock ERC20 contract
        mock_contract = Mock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 2000000000000000000000  # 2000 USDC (18 decimals)
        mock_get_contract.return_value = mock_contract
        
        with patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.lend.return_value = {"to": "0x123", "gas": 300000}
            mock_adapter_class.return_value = mock_adapter
            
            tx_hash = lend_borrow(
                web3_zksync=mock_web3_l2,
                private_key="0x" + "1" * 64,
                action="lend",
                token_symbol="USDC",
                amount=Decimal("1000.0"),
                protocol="zerolend"
            )
            
            assert tx_hash == "0x" + "b" * 64
            mock_adapter.lend.assert_called_once()
            mock_approve.assert_called_once()  # Should approve ERC20
            mock_build_send.assert_called_once()

    @patch('airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    @patch('airdrops.protocols.zksync.zksync._get_account_zksync')
    def test_lend_borrow_contract_logic_error(self, mock_get_account, mock_get_token_address, mock_web3_l2):
        """Test lend_borrow handling ContractLogicError."""
        from web3.exceptions import ContractLogicError
        
        # Setup mocks
        mock_account = Mock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        mock_get_token_address.return_value = "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91"  # WETH
        
        mock_web3_l2.to_wei.return_value = 1000000000000000000  # 1 ETH
        mock_web3_l2.eth.get_balance.return_value = 2000000000000000000  # 2 ETH
        
        with patch('airdrops.protocols.zksync.lending_adapter.ZerolendAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.lend.side_effect = ContractLogicError("Insufficient collateral")
            mock_adapter_class.return_value = mock_adapter
            
            with pytest.raises(ZkSyncLendingError, match="reverted with logic error"):
                lend_borrow(
                    web3_zksync=mock_web3_l2,
                    private_key="0x" + "1" * 64,
                    action="lend",
                    token_symbol="ETH",
                    amount=Decimal("1.0"),
                    protocol="zerolend"
                )


class TestLendingAdapterInterface:
    """Test cases for the abstract lending adapter interface."""

    def test_abstract_interface_cannot_be_instantiated(self, mock_web3_l2):
        """Test that the abstract interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ZkSyncLendingAdapter(mock_web3_l2)

    def test_concrete_adapter_implements_interface(self, mock_web3_l2):
        """Test that concrete adapters implement the required interface."""
        adapter = ZerolendAdapter(mock_web3_l2)
        
        # Check that all required methods are implemented
        assert hasattr(adapter, 'lend')
        assert hasattr(adapter, 'withdraw')
        assert hasattr(adapter, 'borrow')
        assert hasattr(adapter, 'repay')
        assert hasattr(adapter, 'PROTOCOL_NAME')
        
        # Check that methods are callable
        assert callable(adapter.lend)
        assert callable(adapter.withdraw)
        assert callable(adapter.borrow)
        assert callable(adapter.repay)