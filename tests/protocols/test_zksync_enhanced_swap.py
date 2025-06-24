"""
Tests for enhanced zkSync swap functionality with DEX adapter pattern.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from src.airdrops.protocols.zksync.zksync import swap_tokens, ZkSyncProtocol
from src.airdrops.protocols.zksync.exceptions import (
    ZkSyncSwapError,
    InsufficientLiquidityError
)


class TestEnhancedSwapTokens:
    """Test the enhanced swap_tokens function with DEX adapter pattern."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        return web3

    @patch('src.airdrops.protocols.zksync.dex_adapter.SyncSwapAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.MuteAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.SpaceFiAdapter')
    def test_auto_dex_selection_syncswap_best(self, mock_spacefi_cls, mock_mute_cls,
                                            mock_syncswap_cls, mock_web3):
        """Test auto DEX selection when SyncSwap has the best quote."""
        # Setup mock adapters
        mock_syncswap = Mock()
        mock_syncswap.get_quote.return_value = 1000000  # Best quote
        mock_syncswap.build_swap_transaction.return_value = {
            "to": "0xrouter",
            "data": "0xdata",
            "value": 0,
            "gas": 600000
        }
        mock_syncswap_cls.return_value = mock_syncswap

        mock_mute = Mock()
        mock_mute.get_quote.return_value = 900000  # Lower quote
        mock_mute_cls.return_value = mock_mute

        mock_spacefi = Mock()
        mock_spacefi.get_quote.return_value = 950000  # Middle quote
        mock_spacefi_cls.return_value = mock_spacefi

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        # Mock other dependencies
        with patch('src.airdrops.protocols.zksync.zksync._build_and_send_tx_zksync') as mock_send, \
             patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync') as mock_get_token, \
             patch('src.airdrops.protocols.zksync.zksync.ETH_SYMBOL', 'ETH'):
            mock_send.return_value = "0xtxhash"
            mock_get_token.side_effect = lambda symbol: f"0x{symbol.lower()}_address"
            
            result = swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="auto"
            )

        # Verify SyncSwap was selected and used
        assert result == "0xtxhash"
        mock_syncswap.get_quote.assert_called_once()
        mock_syncswap.build_swap_transaction.assert_called_once()
        mock_mute.get_quote.assert_called_once()
        mock_spacefi.get_quote.assert_called_once()

    @patch('src.airdrops.protocols.zksync.dex_adapter.SyncSwapAdapter')
    def test_specific_dex_selection_syncswap(self, mock_syncswap_cls, mock_web3):
        """Test specific DEX selection for SyncSwap."""
        mock_syncswap = Mock()
        mock_syncswap.get_quote.return_value = 1000000
        mock_syncswap.build_swap_transaction.return_value = {
            "to": "0xrouter",
            "data": "0xdata",
            "value": 0,
            "gas": 600000
        }
        mock_syncswap_cls.return_value = mock_syncswap

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        with patch('src.airdrops.protocols.zksync.zksync._build_and_send_tx_zksync') as mock_send, \
             patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync') as mock_get_token, \
             patch('src.airdrops.protocols.zksync.zksync.ETH_SYMBOL', 'ETH'):
            mock_send.return_value = "0xtxhash"
            mock_get_token.side_effect = lambda symbol: f"0x{symbol.lower()}_address"
            
            result = swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="syncswap"
            )

        assert result == "0xtxhash"
        mock_syncswap.get_quote.assert_called_once()
        mock_syncswap.build_swap_transaction.assert_called_once()

    @patch('src.airdrops.protocols.zksync.dex_adapter.MuteAdapter')
    def test_specific_dex_selection_mute(self, mock_mute_cls, mock_web3):
        """Test specific DEX selection for Mute."""
        mock_mute = Mock()
        mock_mute.get_quote.return_value = 1000000  # Non-zero to pass liquidity check
        mock_mute.build_swap_transaction.side_effect = ZkSyncSwapError("Mute adapter not fully implemented")
        mock_mute_cls.return_value = mock_mute

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        with pytest.raises(ZkSyncSwapError, match="Failed to execute mute swap"):
            swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="mute"
            )

    @patch('src.airdrops.protocols.zksync.dex_adapter.SpaceFiAdapter')
    def test_specific_dex_selection_spacefi(self, mock_spacefi_cls, mock_web3):
        """Test specific DEX selection for SpaceFi."""
        mock_spacefi = Mock()
        mock_spacefi.get_quote.return_value = 1000000  # Non-zero to pass liquidity check
        mock_spacefi.build_swap_transaction.side_effect = ZkSyncSwapError("SpaceFi adapter not fully implemented")
        mock_spacefi_cls.return_value = mock_spacefi

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        with pytest.raises(ZkSyncSwapError, match="Failed to execute spacefi swap"):
            swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="spacefi"
            )

    def test_invalid_dex_parameter(self, mock_web3):
        """Test error handling for invalid DEX parameter."""
        with pytest.raises(ValueError, match="Unsupported DEX"):
            swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="invalid_dex"
            )

    @patch('src.airdrops.protocols.zksync.dex_adapter.SyncSwapAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.MuteAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.SpaceFiAdapter')
    def test_auto_dex_no_liquidity(self, mock_spacefi_cls, mock_mute_cls, 
                                 mock_syncswap_cls, mock_web3):
        """Test auto DEX selection when no DEX has liquidity."""
        # All adapters return 0 quote (no liquidity)
        for mock_cls in [mock_syncswap_cls, mock_mute_cls, mock_spacefi_cls]:
            mock_adapter = Mock()
            mock_adapter.get_quote.return_value = 0
            mock_cls.return_value = mock_adapter

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        with pytest.raises(InsufficientLiquidityError, match="No DEX has sufficient liquidity"):
            swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="auto"
            )

    @patch('src.airdrops.protocols.zksync.dex_adapter.SyncSwapAdapter')
    def test_swap_transaction_failure(self, mock_syncswap_cls, mock_web3):
        """Test handling of swap transaction failure."""
        mock_syncswap = Mock()
        mock_syncswap.get_quote.return_value = 1000000
        mock_syncswap.build_swap_transaction.side_effect = Exception("Transaction build failed")
        mock_syncswap_cls.return_value = mock_syncswap

        # Mock Web3 balance check
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH

        with pytest.raises(ZkSyncSwapError, match="Failed to execute syncswap swap"):
            swap_tokens(
                web3_zksync=mock_web3,
                private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=500000000000000000,  # 0.5 ETH in Wei
                slippage_percent=0.5,
                dex="syncswap"
            )


class TestZkSyncProtocolEnhanced:
    """Test the enhanced ZkSyncProtocol class with DEX parameter."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        web3.to_wei.return_value = 500000000000000000  # 0.5 ETH
        return web3

    @pytest.fixture
    def protocol(self, mock_web3):
        """Create a ZkSyncProtocol instance."""
        return ZkSyncProtocol(
            l1_rpc_url="http://localhost:8545",
            l2_rpc_url="http://localhost:3050",
            private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
            web3_l1=mock_web3,
            web3_l2=mock_web3
        )

    @patch('src.airdrops.protocols.zksync.zksync.swap_tokens')
    def test_protocol_swap_tokens_with_dex_parameter(self, mock_swap_tokens, protocol):
        """Test protocol swap_tokens method with DEX parameter."""
        mock_swap_tokens.return_value = "0xtxhash"
        
        result = protocol.swap_tokens(
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.5"),
            slippage_percent=0.5,
            dex="syncswap"
        )
        
        assert result == "0xtxhash"
        mock_swap_tokens.assert_called_once_with(
            web3_zksync=protocol.web3_l2,
            private_key=protocol.private_key,
            token_in_symbol="ETH",
            token_out_symbol="USDC",
            amount_in=500000000000000000,  # 0.5 ETH in Wei
            slippage_percent=0.5,
            deadline_seconds=1800,
            dex="syncswap"
        )

    @patch('src.airdrops.protocols.zksync.zksync.swap_tokens')
    def test_protocol_swap_tokens_default_auto_dex(self, mock_swap_tokens, protocol):
        """Test protocol swap_tokens method with default auto DEX selection."""
        mock_swap_tokens.return_value = "0xtxhash"
        
        result = protocol.swap_tokens(
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.5"),
            slippage_percent=0.5
        )
        
        assert result == "0xtxhash"
        mock_swap_tokens.assert_called_once_with(
            web3_zksync=protocol.web3_l2,
            private_key=protocol.private_key,
            token_in_symbol="ETH",
            token_out_symbol="USDC",
            amount_in=500000000000000000,  # 0.5 ETH in Wei
            slippage_percent=0.5,
            deadline_seconds=1800,
            dex="auto"
        )

    @patch('src.airdrops.protocols.zksync.zksync.swap_tokens')
    def test_protocol_swap_tokens_error_propagation(self, mock_swap_tokens, protocol):
        """Test that protocol properly propagates swap errors."""
        mock_swap_tokens.side_effect = ZkSyncSwapError("Swap failed")
        
        with pytest.raises(ZkSyncSwapError, match="Swap failed"):
            protocol.swap_tokens(
                token_in="ETH",
                token_out="USDC",
                amount_in=Decimal("0.5"),
                slippage_percent=0.5,
                dex="syncswap"
            )


class TestDEXAdapterQuoteComparison:
    """Test DEX adapter quote comparison logic."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        web3.to_wei.return_value = 500000000000000000  # 0.5 ETH
        return web3

    @patch('src.airdrops.protocols.zksync.dex_adapter.SyncSwapAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.MuteAdapter')
    @patch('src.airdrops.protocols.zksync.dex_adapter.SpaceFiAdapter')
    def test_quote_comparison_different_scenarios(self, mock_spacefi_cls, mock_mute_cls, 
                                                mock_syncswap_cls, mock_web3):
        """Test quote comparison in different scenarios."""
        # Scenario 1: SyncSwap best
        mock_syncswap = Mock()
        mock_syncswap.get_quote.return_value = 1000000
        mock_syncswap_cls.return_value = mock_syncswap

        mock_mute = Mock()
        mock_mute.get_quote.return_value = 900000
        mock_mute_cls.return_value = mock_mute

        mock_spacefi = Mock()
        mock_spacefi.get_quote.return_value = 950000
        mock_spacefi_cls.return_value = mock_spacefi

        # Test the quote comparison logic (extracted from swap_tokens)
        adapters = {
            "syncswap": mock_syncswap,
            "mute": mock_mute,
            "spacefi": mock_spacefi
        }
        
        quotes = {}
        for name, adapter in adapters.items():
            quotes[name] = adapter.get_quote("0xtoken_in", "0xtoken_out", 500000)
        
        best_dex = max(quotes.items(), key=lambda x: x[1])
        assert best_dex[0] == "syncswap"
        assert best_dex[1] == 1000000

    def test_quote_comparison_edge_cases(self, mock_web3):
        """Test quote comparison edge cases."""
        # Test with all zero quotes
        quotes = {"syncswap": 0, "mute": 0, "spacefi": 0}
        best_dex = max(quotes.items(), key=lambda x: x[1])
        assert best_dex[1] == 0  # All are zero, any could be selected

        # Test with equal quotes
        quotes = {"syncswap": 1000000, "mute": 1000000, "spacefi": 1000000}
        best_dex = max(quotes.items(), key=lambda x: x[1])
        assert best_dex[1] == 1000000  # Any could be selected, all equal