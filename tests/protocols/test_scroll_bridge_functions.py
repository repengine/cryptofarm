"""
Comprehensive unit tests for Scroll bridge functions.

This module tests the bridge-specific functionality including ETH and ERC20
bridging between L1 and L2, gas estimation, and error handling.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.airdrops.protocols.scroll.scroll import (
    _bridge_eth_scroll,
    _bridge_erc20_scroll,
    _estimate_l1_to_l2_message_fee_scroll,
    bridge_assets,
)
from src.airdrops.protocols.scroll.exceptions import (
    InsufficientBalanceError,
    ApprovalError,
    GasEstimationError,
)


class TestETHBridging:
    """Test suite for ETH bridging functionality."""

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._estimate_l1_to_l2_message_fee_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_eth_scroll_deposit_success(
        self,
        mock_web3_class: MagicMock,
        mock_estimate_fee: MagicMock,
        mock_build_send: MagicMock,
        mock_get_contract: MagicMock,
    ) -> None:
        """Test successful ETH deposit from L1 to L2."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3_l1.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_estimate_fee.return_value = 10**15  # 0.001 ETH fee
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.depositETH.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 10**17 + 10**15, "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _bridge_eth_scroll(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            amount=10**17,  # 0.1 ETH
            direction="deposit",
            l1_address="0x456",
            l2_address="0x789",
            l2_gas_limit=200000,
            l2_gas_price=None
        )
        
        assert result == "0xabc123"
        mock_estimate_fee.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_eth_scroll_withdraw_success(
        self,
        mock_web3_class: MagicMock,
        mock_build_send: MagicMock,
        mock_get_contract: MagicMock,
    ) -> None:
        """Test successful ETH withdrawal from L2 to L1."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3_l2.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.withdrawETH.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 10**17, "data": "0x"
        }
        mock_build_send.return_value = "0xdef456"
        mock_web3_l2.eth.gas_price = 10**9
        
        result = _bridge_eth_scroll(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            amount=10**17,  # 0.1 ETH
            direction="withdraw",
            l1_address="0x456",
            l2_address="0x789",
            l2_gas_limit=200000,
            l2_gas_price=None
        )
        
        assert result == "0xdef456"
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_eth_scroll_insufficient_balance_deposit(self, mock_web3_class: MagicMock) -> None:
        """Test ETH deposit with insufficient balance."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3_l1.eth.get_balance.return_value = 10**16  # 0.01 ETH
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L1 ETH balance for deposit"):
            _bridge_eth_scroll(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                amount=10**17,  # 0.1 ETH (more than balance)
                direction="deposit",
                l1_address="0x456",
                l2_address="0x789",
                l2_gas_limit=200000,
                l2_gas_price=None
            )

    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_eth_scroll_insufficient_balance_withdraw(self, mock_web3_class: MagicMock) -> None:
        """Test ETH withdrawal with insufficient balance."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3_l2.eth.get_balance.return_value = 10**16  # 0.01 ETH
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L2 ETH balance for withdrawal"):
            _bridge_eth_scroll(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                amount=10**17,  # 0.1 ETH (more than balance)
                direction="withdraw",
                l1_address="0x456",
                l2_address="0x789",
                l2_gas_limit=200000,
                l2_gas_price=None
            )


class TestERC20Bridging:
    """Test suite for ERC20 bridging functionality."""

    @patch("src.airdrops.protocols.scroll.scroll._get_l1_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._approve_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._estimate_l1_to_l2_message_fee_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_erc20_scroll_deposit_success(
        self,
        mock_web3_class: MagicMock,
        mock_estimate_fee: MagicMock,
        mock_build_send: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_l1_token: MagicMock,
    ) -> None:
        """Test successful ERC20 deposit from L1 to L2."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_token_contract = MagicMock()
        mock_gateway_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_get_l1_token.return_value = "0xUSDC_L1"
        mock_get_contract.side_effect = [mock_token_contract, mock_gateway_contract]
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 10**6  # 1 USDC
        mock_estimate_fee.return_value = 10**15  # 0.001 ETH fee
        mock_approve.return_value = "0xapproval"
        mock_gateway_contract.functions.depositERC20.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 10**15, "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"

        # Patch both contract mocks to return int for balance check
        def get_contract_side_effect(*args, **kwargs):
            contract = MagicMock()
            contract.functions.balanceOf.return_value.call.return_value = 10**6
            return contract
        # Patch both contract mocks to return int for balance check, not MagicMock
        mock_get_contract.side_effect = [get_contract_side_effect(), get_contract_side_effect()]

        result = _bridge_erc20_scroll(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=500000,  # 0.5 USDC
            direction="deposit",
            l1_address="0x456",
            l2_address="0x789",
            l2_gas_limit=200000,
            l2_gas_price=None
        )

        assert result == "0xabc123"
        mock_approve.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_erc20_scroll_withdraw_success(
        self,
        mock_web3_class: MagicMock,
        mock_build_send: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_l2_token: MagicMock,
    ) -> None:
        """Test successful ERC20 withdrawal from L2 to L1."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_token_contract = MagicMock()
        mock_gateway_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_get_l2_token.return_value = "0xUSDC_L2"
        mock_get_contract.side_effect = [mock_token_contract, mock_gateway_contract]
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 10**6  # 1 USDC
        mock_gateway_contract.functions.withdrawERC20.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 0, "data": "0x"
        }
        mock_build_send.return_value = "0xdef456"
        mock_web3_l2.eth.gas_price = 10**9

        # Patch both contract mocks to return int for balance check
        def get_contract_side_effect(*args, **kwargs):
            contract = MagicMock()
            contract.functions.balanceOf.return_value.call.return_value = 10**6
            return contract
        # Patch both contract mocks to return int for balance check, not MagicMock
        mock_get_contract.side_effect = [get_contract_side_effect(), get_contract_side_effect(), get_contract_side_effect()]

        result = _bridge_erc20_scroll(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=500000,  # 0.5 USDC
            direction="withdraw",
            l1_address="0x456",
            l2_address="0x789",
            l2_gas_limit=200000,
            l2_gas_price=None
        )

        assert result == "0xdef456"
        # Called for both approve and withdraw, so should be called twice
        assert mock_build_send.call_count == 2

    @patch("src.airdrops.protocols.scroll.scroll._get_l1_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_erc20_scroll_insufficient_balance(
        self,
        mock_web3_class: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_l1_token: MagicMock,
    ) -> None:
        """Test ERC20 deposit with insufficient balance."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_token_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_get_l1_token.return_value = "0xUSDC_L1"
        mock_get_contract.return_value = mock_token_contract
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 100000  # 0.1 USDC
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient L1 USDC balance for deposit"):
            _bridge_erc20_scroll(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="USDC",
                amount=500000,  # 0.5 USDC (more than balance)
                direction="deposit",
                l1_address="0x456",
                l2_address="0x789",
                l2_gas_limit=200000,
                l2_gas_price=None
            )


class TestGasEstimation:
    """Test suite for gas estimation functionality."""

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    def test_estimate_l1_to_l2_message_fee_scroll_success(self, mock_get_contract: MagicMock) -> None:
        """Test successful L1 to L2 message fee estimation."""
        mock_web3 = MagicMock()
        mock_oracle = MagicMock()
        
        mock_get_contract.return_value = mock_oracle
        mock_oracle.functions.estimateCrossDomainMessageFee.return_value.call.return_value = 10**15
        
        result = _estimate_l1_to_l2_message_fee_scroll(mock_web3, 200000)
        
        assert result == 10**15
        mock_oracle.functions.estimateCrossDomainMessageFee.assert_called_once_with(200000)

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    def test_estimate_l1_to_l2_message_fee_scroll_failure(self, mock_get_contract: MagicMock) -> None:
        """Test L1 to L2 message fee estimation failure."""
        mock_web3 = MagicMock()
        mock_oracle = MagicMock()
        
        mock_get_contract.return_value = mock_oracle
        mock_oracle.functions.estimateCrossDomainMessageFee.return_value.call.side_effect = Exception("Oracle error")
        
        with pytest.raises(GasEstimationError, match="Failed to estimate L1->L2 message fee"):
            _estimate_l1_to_l2_message_fee_scroll(mock_web3, 200000)


class TestBridgeIntegration:
    """Test suite for bridge integration scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._bridge_eth_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_bridge_assets_eth_success(
        self,
        mock_get_account: MagicMock,
        mock_bridge_eth: MagicMock,
    ) -> None:
        """Test successful ETH bridging through main bridge_assets function."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_bridge_eth.return_value = "0xabc123"
        
        result = bridge_assets(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("100000000000000000"),  # 0.1 ETH
            direction="deposit",
            l2_gas_limit=200000,
            l2_gas_price=None
        )
        
        assert result == "0xabc123"
        mock_bridge_eth.assert_called_once_with(
            mock_web3_l1,
            mock_web3_l2,
            "0x" + "a" * 64,
            100000000000000000,
            "deposit",
            "0x1234567890123456789012345678901234567890",
            "0x1234567890123456789012345678901234567890",
            200000,
            None
        )

    @patch("src.airdrops.protocols.scroll.scroll._bridge_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_bridge_assets_erc20_success(
        self,
        mock_get_account: MagicMock,
        mock_bridge_erc20: MagicMock,
    ) -> None:
        """Test successful ERC20 bridging through main bridge_assets function."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_bridge_erc20.return_value = "0xdef456"
        
        result = bridge_assets(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=Decimal("1000000"),  # 1 USDC
            direction="withdraw",
            l2_gas_limit=200000,
            l2_gas_price=None
        )
        
        assert result == "0xdef456"
        mock_bridge_erc20.assert_called_once_with(
            mock_web3_l1,
            mock_web3_l2,
            "0x" + "a" * 64,
            "USDC",
            1000000,
            "withdraw",
            "0x1234567890123456789012345678901234567890",
            "0x1234567890123456789012345678901234567890",
            200000,
            None
        )

    def test_bridge_assets_invalid_direction(self) -> None:
        """Test bridge_assets with invalid direction parameter."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        with pytest.raises(ValueError, match="Direction must be 'deposit' or 'withdraw'"):
            bridge_assets(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("100000000000000000"),
                direction="invalid_direction",
                l2_gas_limit=200000,
                l2_gas_price=None
            )

    def test_bridge_assets_zero_amount(self) -> None:
        """Test bridge_assets with zero amount."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            bridge_assets(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("0"),
                direction="deposit",
                l2_gas_limit=200000,
                l2_gas_price=None
            )

    def test_bridge_assets_negative_amount(self) -> None:
        """Test bridge_assets with negative amount."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            bridge_assets(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("-100000000000000000"),
                direction="deposit",
                l2_gas_limit=200000,
                l2_gas_price=None
            )


class TestBridgeErrorScenarios:
    """Test suite for bridge error scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._get_l1_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._approve_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_erc20_approval_failure(
        self,
        mock_web3_class: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_l1_token: MagicMock,
    ) -> None:
        """Test ERC20 bridging with approval failure."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_token_contract = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_get_l1_token.return_value = "0xUSDC_L1"
        mock_get_contract.return_value = mock_token_contract
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 10**6  # 1 USDC
        mock_approve.side_effect = ApprovalError("Approval failed")
        
        with pytest.raises(ApprovalError, match="Approval failed"):
            _bridge_erc20_scroll(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="USDC",
                amount=500000,  # 0.5 USDC
                direction="deposit",
                l1_address="0x456",
                l2_address="0x789",
                l2_gas_limit=200000,
                l2_gas_price=None
            )

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._estimate_l1_to_l2_message_fee_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_bridge_eth_fee_estimation_failure(
        self,
        mock_web3_class: MagicMock,
        mock_estimate_fee: MagicMock,
        mock_get_contract: MagicMock,
    ) -> None:
        """Test ETH bridging with fee estimation failure."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        # Setup mocks
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3_l1.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_estimate_fee.side_effect = GasEstimationError("Fee estimation failed")
        
        with pytest.raises(GasEstimationError, match="Fee estimation failed"):
            _bridge_eth_scroll(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                amount=10**17,  # 0.1 ETH
                direction="deposit",
                l1_address="0x456",
                l2_address="0x789",
                l2_gas_limit=200000,
                l2_gas_price=None
            )