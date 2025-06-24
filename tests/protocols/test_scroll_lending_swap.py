"""
Comprehensive unit tests for Scroll LayerBank lending and SyncSwap functionality.

This module tests the lending/borrowing operations on LayerBank V2 and
detailed SyncSwap swap functionality including path construction and routing.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from web3.exceptions import ContractLogicError
from hexbytes import HexBytes

from src.airdrops.protocols.scroll.scroll import (
    _handle_lend_action_scroll,
    _handle_withdraw_action_scroll,
    _handle_borrow_action_scroll,
    _handle_repay_action_scroll,
    _get_expected_amount_out_syncswap_scroll,
    _construct_syncswap_paths_scroll,
    swap_tokens,
)
from src.airdrops.protocols.scroll.exceptions import (
    InsufficientBalanceError,
    InsufficientCollateralError,
    RepayAmountExceedsDebtError,
    InsufficientLiquidityError,
)


class TestLayerBankLendActions:
    """Test suite for LayerBank lending action handlers."""

    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_lend_action_scroll_eth_success(self, mock_build_send: MagicMock) -> None:
        """Test successful ETH lending action."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_web3.eth.gas_price = 10**9
        mock_contract.functions.mint.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 5 * 10**17, "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_lend_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("500000000000000000"),  # 0.5 ETH
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_contract,
            lbtoken_address="0x789"
        )
        
        assert result == "0xabc123"
        mock_contract.functions.mint.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._approve_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_lend_action_scroll_usdc_success(
        self,
        mock_build_send: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
    ) -> None:
        """Test successful USDC lending action."""
        mock_web3 = MagicMock()
        mock_lbtoken_contract = MagicMock()
        mock_usdc_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.gas_price = 10**9
        mock_get_contract.return_value = mock_usdc_contract
        mock_usdc_contract.functions.balanceOf.return_value.call.return_value = 10**6  # 1 USDC
        mock_approve.return_value = "0xapproval"
        mock_lbtoken_contract.functions.mint.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 0, "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_lend_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=Decimal("500000"),  # 0.5 USDC
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_lbtoken_contract,
            lbtoken_address="0x789"
        )
        
        assert result == "0xabc123"
        mock_approve.assert_called_once()
        mock_lbtoken_contract.functions.mint.assert_called_once_with(Decimal("500000"))
        mock_build_send.assert_called_once()

    def test_handle_lend_action_scroll_insufficient_eth_balance(self) -> None:
        """Test ETH lending with insufficient balance."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        mock_web3.eth.get_balance.return_value = 10**17  # 0.1 ETH
        mock_web3.eth.gas_price = 10**9
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient ETH balance"):
            _handle_lend_action_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("500000000000000000"),  # 0.5 ETH (more than balance)
                user_address="0x4567890123456789012345678901234567890123",
                lbtoken_contract=mock_contract,
                lbtoken_address="0x789"
            )

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    def test_handle_lend_action_scroll_insufficient_usdc_balance(self, mock_get_contract: MagicMock) -> None:
        """Test USDC lending with insufficient balance."""
        mock_web3 = MagicMock()
        mock_lbtoken_contract = MagicMock()
        mock_usdc_contract = MagicMock()
        
        mock_web3.eth.gas_price = 10**9
        mock_get_contract.return_value = mock_usdc_contract
        mock_usdc_contract.functions.balanceOf.return_value.call.return_value = 100000  # 0.1 USDC
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient USDC balance"):
            _handle_lend_action_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_symbol="USDC",
                amount=Decimal("500000"),  # 0.5 USDC (more than balance)
                user_address="0x4567890123456789012345678901234567890123",
                lbtoken_contract=mock_lbtoken_contract,
                lbtoken_address="0x789"
            )


class TestLayerBankWithdrawActions:
    """Test suite for LayerBank withdraw action handlers."""

    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_withdraw_action_scroll_success(self, mock_build_send: MagicMock) -> None:
        """Test successful withdraw action."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.gas_price = 10**9
        mock_contract.functions.balanceOf.return_value.call.return_value = 10**18  # 1 lbToken
        mock_contract.functions.redeemUnderlying.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_withdraw_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("500000000000000000"),  # 0.5 ETH
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_contract
        )
        
        assert result == "0xabc123"
        mock_contract.functions.redeemUnderlying.assert_called_once_with(Decimal("500000000000000000"))
        mock_build_send.assert_called_once()

    def test_handle_withdraw_action_scroll_insufficient_balance(self) -> None:
        """Test withdraw with insufficient lbToken balance."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        mock_web3.eth.gas_price = 10**9
        mock_contract.functions.balanceOf.return_value.call.return_value = 10**17  # 0.1 lbToken
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient lbToken balance"):
            _handle_withdraw_action_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("500000000000000000"),  # 0.5 ETH (more than balance)
                user_address="0x4567890123456789012345678901234567890123",
                lbtoken_contract=mock_contract
            )


class TestLayerBankBorrowActions:
    """Test suite for LayerBank borrow action handlers."""

    @patch("src.airdrops.protocols.scroll.scroll._check_and_enter_layerbank_market_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_layerbank_account_liquidity_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_borrow_action_scroll_success(
        self,
        mock_build_send: MagicMock,
        mock_get_liquidity: MagicMock,
        mock_enter_market: MagicMock,
    ) -> None:
        """Test successful borrow action."""
        mock_web3 = MagicMock()
        mock_lbtoken_contract = MagicMock()
        mock_comptroller_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.gas_price = 10**9
        mock_get_liquidity.return_value = (0, 1000, 0)  # No error, sufficient liquidity, no shortfall
        mock_lbtoken_contract.functions.borrow.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_borrow_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("100000000000000000"),  # 0.1 ETH
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_lbtoken_contract,
            comptroller_contract=mock_comptroller_contract,
            lbtoken_address="0x789"
        )
        
        assert result == "0xabc123"
        mock_enter_market.assert_called_once()
        mock_get_liquidity.assert_called_once()
        mock_lbtoken_contract.functions.borrow.assert_called_once_with(Decimal("100000000000000000"))
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._check_and_enter_layerbank_market_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_layerbank_account_liquidity_scroll")
    def test_handle_borrow_action_scroll_insufficient_collateral(
        self,
        mock_get_liquidity: MagicMock,
        mock_enter_market: MagicMock,
    ) -> None:
        """Test borrow with insufficient collateral."""
        mock_web3 = MagicMock()
        mock_lbtoken_contract = MagicMock()
        mock_comptroller_contract = MagicMock()
        
        mock_web3.eth.gas_price = 10**9
        mock_get_liquidity.return_value = (0, 0, 500)  # No error, no liquidity, shortfall exists
        
        with pytest.raises(InsufficientCollateralError, match="Account is in shortfall"):
            _handle_borrow_action_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("100000000000000000"),  # 0.1 ETH
                user_address="0x4567890123456789012345678901234567890123",
                lbtoken_contract=mock_lbtoken_contract,
                comptroller_contract=mock_comptroller_contract,
                lbtoken_address="0x789"
            )


class TestLayerBankRepayActions:
    """Test suite for LayerBank repay action handlers."""

    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_repay_action_scroll_eth_success(self, mock_build_send: MagicMock) -> None:
        """Test successful ETH repay action."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_web3.eth.gas_price = 10**9
        mock_contract.functions.borrowBalanceCurrent.return_value.call.return_value = 5 * 10**17  # 0.5 ETH debt
        mock_contract.functions.repayBorrow.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "value": 10**17, "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_repay_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("100000000000000000"),  # 0.1 ETH
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_contract
        )
        
        assert result == "0xabc123"
        mock_contract.functions.repayBorrow.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._approve_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_handle_repay_action_scroll_usdc_success(
        self,
        mock_build_send: MagicMock,
        mock_approve: MagicMock,
        mock_get_contract: MagicMock,
    ) -> None:
        """Test successful USDC repay action."""
        mock_web3 = MagicMock()
        mock_lbtoken_contract = MagicMock()
        mock_usdc_contract = MagicMock()
        
        # Setup mocks
        mock_web3.eth.gas_price = 10**9
        mock_get_contract.return_value = mock_usdc_contract
        mock_usdc_contract.functions.balanceOf.return_value.call.return_value = 10**6  # 1 USDC
        mock_lbtoken_contract.functions.borrowBalanceCurrent.return_value.call.return_value = 5 * 10**5  # 0.5 USDC debt
        mock_lbtoken_contract.address = "0x789"
        mock_approve.return_value = "0xapproval"
        mock_lbtoken_contract.functions.repayBorrow.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890", "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        
        result = _handle_repay_action_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=Decimal("100000"),  # 0.1 USDC
            user_address="0x4567890123456789012345678901234567890123",
            lbtoken_contract=mock_lbtoken_contract
        )
        
        assert result == "0xabc123"
        mock_approve.assert_called_once()
        mock_lbtoken_contract.functions.repayBorrow.assert_called_once_with(Decimal("100000"))
        mock_build_send.assert_called_once()

    def test_handle_repay_action_scroll_amount_exceeds_debt(self) -> None:
        """Test repay with amount exceeding current debt."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        
        mock_web3.eth.gas_price = 10**9
        mock_contract.functions.borrowBalanceCurrent.return_value.call.return_value = 5 * 10**16  # 0.05 ETH debt
        
        with pytest.raises(RepayAmountExceedsDebtError, match="Repay amount .* exceeds current borrow debt"):
            _handle_repay_action_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("100000000000000000"),  # 0.1 ETH (more than debt)
                user_address="0x4567890123456789012345678901234567890123",
                lbtoken_contract=mock_contract
            )


class TestSyncSwapAmountCalculation:
    """Test suite for SyncSwap amount calculation functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_classic_pool_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_expected_amount_out_syncswap_scroll_direct_pool(
        self,
        mock_web3_class: MagicMock,
        mock_get_pool_contract: MagicMock,
        mock_get_pool_address: MagicMock,
    ) -> None:
        """Test expected amount calculation with direct pool."""
        mock_web3 = MagicMock()
        mock_pool_contract = MagicMock()
        
        # Setup mocks
        mock_get_pool_address.return_value = "0xpool123"
        mock_get_pool_contract.return_value = mock_pool_contract
        mock_pool_contract.functions.getAmountOut.return_value.call.return_value = 2000 * 10**6  # 2000 USDC
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        result = _get_expected_amount_out_syncswap_scroll(
            web3_scroll=mock_web3,
            token_in_address="0xWETH",
            token_out_address="0xUSDC",
            amount_in=10**17,  # 0.1 ETH
            sender_address="0x4567890123456789012345678901234567890123",
            weth_address="0xWETH"
        )
        
        assert result == 2000 * 10**6
        mock_pool_contract.functions.getAmountOut.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_classic_pool_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_expected_amount_out_syncswap_scroll_via_weth(
        self,
        mock_web3_class: MagicMock,
        mock_get_pool_contract: MagicMock,
        mock_get_pool_address: MagicMock,
    ) -> None:
        """Test expected amount calculation via WETH hop."""
        mock_web3 = MagicMock()
        mock_pool1_contract = MagicMock()
        mock_pool2_contract = MagicMock()
        
        # Setup mocks - no direct pool, but pools via WETH exist
        mock_get_pool_address.side_effect = [None, "0xpool1", "0xpool2"]
        mock_get_pool_contract.side_effect = [mock_pool1_contract, mock_pool2_contract]
        mock_pool1_contract.functions.getAmountOut.return_value.call.return_value = 5 * 10**16  # 0.05 WETH
        mock_pool2_contract.functions.getAmountOut.return_value.call.return_value = 100 * 10**6  # 100 USDC
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        result = _get_expected_amount_out_syncswap_scroll(
            web3_scroll=mock_web3,
            token_in_address="0xUSDT",
            token_out_address="0xUSDC",
            amount_in=100 * 10**6,  # 100 USDT
            sender_address="0x4567890123456789012345678901234567890123",
            weth_address="0xWETH"
        )
        
        assert result == 100 * 10**6
        assert mock_pool1_contract.functions.getAmountOut.call_count == 1
        assert mock_pool2_contract.functions.getAmountOut.call_count == 1

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    def test_get_expected_amount_out_syncswap_scroll_no_path(self, mock_get_pool_address: MagicMock) -> None:
        """Test expected amount calculation when no path exists."""
        mock_web3 = MagicMock()
        
        # No pools found
        mock_get_pool_address.return_value = None
        
        with pytest.raises(InsufficientLiquidityError, match="No liquidity or path found"):
            _get_expected_amount_out_syncswap_scroll(
                web3_scroll=mock_web3,
                token_in_address="0xTOKEN1",
                token_out_address="0xTOKEN2",
                amount_in=10**18,
                sender_address="0x4567890123456789012345678901234567890123",
                weth_address="0xWETH"
            )


class TestSyncSwapPathConstruction:
    """Test suite for SyncSwap path construction functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._encode_swap_step_data_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_construct_syncswap_paths_scroll_direct_path(
        self,
        mock_web3_class: MagicMock,
        mock_encode_data: MagicMock,
        mock_get_pool_address: MagicMock,
    ) -> None:
        """Test path construction for direct swap."""
        mock_web3 = MagicMock()
        mock_router = MagicMock()
        
        # Setup mocks
        mock_get_pool_address.return_value = "0xpool123"
        mock_router.functions.vault.return_value.call.return_value = "0xvault"
        mock_encode_data.return_value = HexBytes("0x12345678901234567890123456789012345678904")
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        result = _construct_syncswap_paths_scroll(
            web3_scroll=mock_web3,
            token_in_start_address="0xWETH",
            token_out_final_address="0xUSDC",
            amount_in_start=10**17,  # 0.1 ETH
            final_recipient_address="0x4567890123456789012345678901234567890123",
            weth_address="0xWETH",
            router_contract=mock_router,
            actual_token_out_symbol="USDC"
        )
        
        assert len(result) == 1
        assert len(result[0]["steps"]) == 1
        assert result[0]["tokenIn"] == "0xWETH"
        assert result[0]["amountIn"] == 10**17

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._encode_swap_step_data_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_construct_syncswap_paths_scroll_via_weth(
        self,
        mock_web3_class: MagicMock,
        mock_encode_data: MagicMock,
        mock_get_pool_address: MagicMock,
    ) -> None:
        """Test path construction for swap via WETH."""
        mock_web3 = MagicMock()
        mock_router = MagicMock()
        
        # Setup mocks - no direct pool, but pools via WETH exist
        mock_get_pool_address.side_effect = [None, "0xpool1", "0xpool2"]
        mock_router.functions.vault.return_value.call.return_value = "0xvault"
        mock_encode_data.side_effect = [HexBytes("0x12345678901234567890123456789012345678904"), HexBytes("0x5678")]
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        result = _construct_syncswap_paths_scroll(
            web3_scroll=mock_web3,
            token_in_start_address="0xUSDT",
            token_out_final_address="0xUSDC",
            amount_in_start=100 * 10**6,  # 100 USDT
            final_recipient_address="0x4567890123456789012345678901234567890123",
            weth_address="0xWETH",
            router_contract=mock_router,
            actual_token_out_symbol="USDC"
        )
        
        assert len(result) == 1
        assert len(result[0]["steps"]) == 2
        assert result[0]["tokenIn"] == "0xUSDT"
        assert result[0]["amountIn"] == 100 * 10**6

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
    def test_construct_syncswap_paths_scroll_no_path(self, mock_get_pool_address: MagicMock) -> None:
        """Test path construction when no path exists."""
        mock_web3 = MagicMock()
        mock_router = MagicMock()
        
        # No pools found
        mock_get_pool_address.return_value = None
        mock_router.functions.vault.return_value.call.return_value = "0xvault"
        
        with pytest.raises(InsufficientLiquidityError, match="No swap path found"):
            _construct_syncswap_paths_scroll(
                web3_scroll=mock_web3,
                token_in_start_address="0xTOKEN1",
                token_out_final_address="0xTOKEN2",
                amount_in_start=10**18,
                final_recipient_address="0x4567890123456789012345678901234567890123",
                weth_address="0xWETH",
                router_contract=mock_router,
                actual_token_out_symbol="TOKEN2"
            )


class TestSwapTokensErrorHandling:
    """Test suite for swap_tokens error handling scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_expected_amount_out_syncswap_scroll")
    def test_swap_tokens_zero_expected_output(
        self,
        mock_get_expected_out: MagicMock,
        mock_get_token_address: MagicMock,
        mock_get_account: MagicMock,
    ) -> None:
        """Test swap with zero expected output."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_get_token_address.side_effect = ["0xWETH", "0xUSDC"]
        mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_web3.eth.get_block.return_value = {"timestamp": 1000000}
        mock_get_expected_out.return_value = 0  # Zero output
        
        with pytest.raises(InsufficientLiquidityError, match="Expected output .* is 0"):
            swap_tokens(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=10**17,  # 0.1 ETH
                slippage_percent=0.5,
                deadline_seconds=1800
            )

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_expected_amount_out_syncswap_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._construct_syncswap_paths_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
    def test_swap_tokens_contract_logic_error(
        self,
        mock_get_router: MagicMock,
        mock_construct_paths: MagicMock,
        mock_get_expected_out: MagicMock,
        mock_get_token_address: MagicMock,
        mock_get_account: MagicMock,
    ) -> None:
        """Test swap with contract logic error (slippage too high)."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_router = MagicMock()
        
        mock_get_account.return_value = mock_account
        mock_get_token_address.side_effect = ["0xWETH", "0xUSDC"]
        mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_web3.eth.get_block.return_value = {"timestamp": 1000000}
        mock_get_expected_out.return_value = 2000 * 10**6  # 2000 USDC
        mock_construct_paths.return_value = [{"steps": [], "tokenIn": "0xWETH", "amountIn": 10**17}]
        mock_get_router.return_value = mock_router
        
        # Mock contract logic error for slippage
        contract_error = ContractLogicError("TooLittleReceived")
        contract_error.message = "TooLittleReceived"
        contract_error.data = "0x087229a4"
        mock_router.functions.swap.return_value.build_transaction.side_effect = contract_error
        
        with pytest.raises(InsufficientLiquidityError, match="Swap likely to result in too little received"):
            swap_tokens(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=10**17,  # 0.1 ETH
                slippage_percent=0.1,  # Very low slippage
                deadline_seconds=1800
            )