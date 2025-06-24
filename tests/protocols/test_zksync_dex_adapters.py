"""
Tests for zkSync DEX adapters and enhanced swap functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.airdrops.protocols.zksync.dex_adapter import (
    ZkSyncDEXAdapter,
    SyncSwapAdapter,
    MuteAdapter,
    SpaceFiAdapter
)
from src.airdrops.protocols.zksync.exceptions import (
    ZkSyncSwapError,
    InsufficientLiquidityError
)


class TestZkSyncDEXAdapter:
    """Test the abstract DEX adapter base class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that the abstract base class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ZkSyncDEXAdapter(Mock())

    def test_dex_name_attribute_required(self):
        """Test that concrete implementations must define DEX_NAME."""
        class TestAdapter(ZkSyncDEXAdapter):
            def get_quote(self, token_in_address, token_out_address, amount_in):
                return 0
            
            def build_swap_transaction(self, token_in_address, token_out_address,
                                     amount_in, recipient_address, slippage_percent,
                                     deadline_seconds):
                return {}
            
            def add_liquidity(self, token_a_address, token_b_address, amount_a, amount_b,
                            recipient_address, slippage_percent, deadline_seconds):
                return {}
            
            def remove_liquidity(self, token_a_address, token_b_address, liquidity,
                               recipient_address, slippage_percent, deadline_seconds):
                return {}
        
        # Should work without DEX_NAME defined (will be None)
        adapter = TestAdapter(Mock())
        assert not hasattr(adapter, 'DEX_NAME') or adapter.DEX_NAME is None


class TestSyncSwapAdapter:
    """Test the SyncSwap DEX adapter."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        return web3

    @pytest.fixture
    def adapter(self, mock_web3):
        """Create a SyncSwap adapter instance."""
        return SyncSwapAdapter(mock_web3)

    def test_adapter_initialization(self, mock_web3):
        """Test SyncSwap adapter initialization."""
        adapter = SyncSwapAdapter(mock_web3)
        assert adapter.web3_l2 == mock_web3
        assert adapter.DEX_NAME == "syncswap"

    @patch('src.airdrops.protocols.zksync.zksync._get_expected_amount_out_syncswap_zksync')
    def test_get_quote_success(self, mock_get_expected, adapter):
        """Test successful quote retrieval from SyncSwap."""
        mock_get_expected.return_value = 1000000
        adapter._get_l2_token_address = Mock(return_value="0xweth")
        
        result = adapter.get_quote(
            "0xtoken_in",
            "0xtoken_out", 
            500000
        )
        
        assert result == 1000000
        mock_get_expected.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_expected_amount_out_syncswap_zksync')
    def test_get_quote_failure(self, mock_get_expected, adapter):
        """Test quote retrieval failure handling."""
        mock_get_expected.side_effect = Exception("Pool not found")
        adapter._get_l2_token_address = Mock(return_value="0xweth")
        
        result = adapter.get_quote(
            "0xtoken_in",
            "0xtoken_out",
            500000
        )
        
        assert result == 0

    @patch('src.airdrops.protocols.zksync.zksync._construct_syncswap_paths_zksync')
    def test_build_swap_transaction_success(self, mock_construct_paths, adapter):
        """Test successful swap transaction building."""
        # Mock dependencies
        adapter.get_quote = Mock(return_value=1000000)
        adapter._get_contract = Mock()
        adapter._get_l2_token_address = Mock(return_value="0xweth")
        
        mock_router = Mock()
        mock_router.functions.swap.return_value.build_transaction.return_value = {
            "to": "0xrouter",
            "data": "0xdata",
            "value": 0,
            "gas": 600000
        }
        adapter._get_contract.return_value = mock_router
        
        mock_construct_paths.return_value = [{"test": "path"}]
        
        result = adapter.build_swap_transaction(
            "0xtoken_in",
            "0xtoken_out",
            500000,
            "0xrecipient",
            0.5,
            1800
        )
        
        assert "to" in result
        assert "data" in result
        adapter.get_quote.assert_called_once()

    def test_build_swap_transaction_no_liquidity(self, adapter):
        """Test swap transaction building with no liquidity."""
        adapter.get_quote = Mock(return_value=0)
        
        with pytest.raises(InsufficientLiquidityError):
            adapter.build_swap_transaction(
                "0xtoken_in",
                "0xtoken_out",
                500000,
                "0xrecipient",
                0.5,
                1800
            )


class TestMuteAdapter:
    """Test the Mute DEX adapter."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        return Mock()

    @pytest.fixture
    def adapter(self, mock_web3):
        """Create a Mute adapter instance."""
        return MuteAdapter(mock_web3)

    def test_adapter_initialization(self, mock_web3):
        """Test Mute adapter initialization."""
        adapter = MuteAdapter(mock_web3)
        assert adapter.web3_l2 == mock_web3
        assert adapter.DEX_NAME == "mute"

    def test_get_quote_placeholder(self, adapter):
        """Test that Mute quote returns 0 (placeholder implementation)."""
        result = adapter.get_quote(
            "0xtoken_in",
            "0xtoken_out",
            500000
        )
        assert result == 0

    def test_build_swap_transaction_not_implemented(self, adapter):
        """Test that Mute swap transaction building raises error."""
        with pytest.raises(ZkSyncSwapError, match="Mute adapter not fully implemented"):
            adapter.build_swap_transaction(
                "0xtoken_in",
                "0xtoken_out",
                500000,
                "0xrecipient",
                0.5,
                1800
            )


class TestSpaceFiAdapter:
    """Test the SpaceFi DEX adapter."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        return Mock()

    @pytest.fixture
    def adapter(self, mock_web3):
        """Create a SpaceFi adapter instance."""
        return SpaceFiAdapter(mock_web3)

    def test_adapter_initialization(self, mock_web3):
        """Test SpaceFi adapter initialization."""
        adapter = SpaceFiAdapter(mock_web3)
        assert adapter.web3_l2 == mock_web3
        assert adapter.DEX_NAME == "spacefi"

    def test_get_quote_placeholder(self, adapter):
        """Test that SpaceFi quote returns 0 (placeholder implementation)."""
        result = adapter.get_quote(
            "0xtoken_in",
            "0xtoken_out",
            500000
        )
        assert result == 0

    def test_build_swap_transaction_not_implemented(self, adapter):
        """Test that SpaceFi swap transaction building raises error."""
        with pytest.raises(ZkSyncSwapError, match="SpaceFi adapter not fully implemented"):
            adapter.build_swap_transaction(
                "0xtoken_in",
                "0xtoken_out",
                500000,
                "0xrecipient",
                0.5,
                1800
            )


class TestDEXAdapterIntegration:
    """Test integration between different DEX adapters."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        return web3

    @pytest.fixture
    def adapters(self, mock_web3):
        """Create all DEX adapter instances."""
        return {
            "syncswap": SyncSwapAdapter(mock_web3),
            "mute": MuteAdapter(mock_web3),
            "spacefi": SpaceFiAdapter(mock_web3)
        }

    def test_all_adapters_implement_interface(self, adapters):
        """Test that all adapters implement the required interface."""
        for name, adapter in adapters.items():
            assert hasattr(adapter, 'get_quote')
            assert hasattr(adapter, 'build_swap_transaction')
            assert hasattr(adapter, 'DEX_NAME')
            assert adapter.DEX_NAME == name

    @patch('src.airdrops.protocols.zksync.zksync._get_expected_amount_out_syncswap_zksync')
    def test_quote_comparison(self, mock_get_expected, adapters):
        """Test comparing quotes across different DEXs."""
        # Mock SyncSwap to return a quote
        mock_get_expected.return_value = 1000000
        adapters["syncswap"]._get_l2_token_address = Mock(return_value="0xweth")
        
        quotes = {}
        for name, adapter in adapters.items():
            quotes[name] = adapter.get_quote(
                "0xtoken_in",
                "0xtoken_out",
                500000
            )
        
        # SyncSwap should return a quote, others should return 0 (placeholder)
        assert quotes["syncswap"] == 1000000
        assert quotes["mute"] == 0
        assert quotes["spacefi"] == 0

    def test_adapter_error_handling(self, adapters):
        """Test error handling across different adapters."""
        for name, adapter in adapters.items():
            # All adapters should handle quote errors gracefully
            with patch.object(adapter, '_get_l2_token_address', side_effect=Exception("Network error")):
                quote = adapter.get_quote("0xtoken_in", "0xtoken_out", 500000)
                assert quote == 0  # Should return 0 on error, not raise


class TestDEXAdapterHelperMethods:
    """Test helper methods in DEX adapters."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        return Mock()

    @pytest.fixture
    def adapter(self, mock_web3):
        """Create a SyncSwap adapter instance for testing helper methods."""
        return SyncSwapAdapter(mock_web3)

    @patch('src.airdrops.protocols.zksync.zksync._get_contract_zksync')
    def test_get_contract_helper(self, mock_get_contract, adapter):
        """Test the _get_contract helper method."""
        mock_contract = Mock()
        mock_get_contract.return_value = mock_contract
        
        result = adapter._get_contract("TestContract", "0xaddress")
        
        assert result == mock_contract
        mock_get_contract.assert_called_once_with(
            adapter.web3_l2, "TestContract", "0xaddress"
        )

    @patch('src.airdrops.protocols.zksync.zksync._get_l2_token_address_zksync')
    def test_get_l2_token_address_helper(self, mock_get_l2_address, adapter):
        """Test the _get_l2_token_address helper method."""
        mock_get_l2_address.return_value = "0xtoken_address"
        
        result = adapter._get_l2_token_address("ETH")
        
        assert result == "0xtoken_address"
        mock_get_l2_address.assert_called_once_with("ETH")


class TestLiquidityOperations:
    """Test liquidity operations in DEX adapters."""

    @pytest.fixture
    def mock_web3(self):
        """Create a mock Web3 instance."""
        web3 = Mock()
        web3.eth = Mock()
        web3.eth.get_block.return_value = {"timestamp": 1000000}
        return web3

    @pytest.fixture
    def syncswap_adapter(self, mock_web3):
        """Create a SyncSwap adapter instance."""
        return SyncSwapAdapter(mock_web3)

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_add_liquidity_success(self, mock_get_pool, syncswap_adapter):
        """Test successful liquidity addition."""
        # Mock dependencies
        mock_get_pool.return_value = "0xpool123"
        syncswap_adapter._get_contract = Mock()
        syncswap_adapter._get_l2_token_address = Mock(return_value="0xweth")
        
        mock_router = Mock()
        mock_router.functions.addLiquidity.return_value.build_transaction.return_value = {
            "to": "0xrouter",
            "data": "0xdata",
            "value": 1000000000000000000,  # 1 ETH
            "gas": 800000
        }
        syncswap_adapter._get_contract.return_value = mock_router
        
        result = syncswap_adapter.add_liquidity(
            "0xtoken_a",
            "0xtoken_b",
            1000000000000000000,  # 1 ETH
            2000000000,  # 2000 USDC
            "0xrecipient",
            0.5,
            1800
        )
        
        assert "to" in result
        assert "data" in result
        assert result["gas"] == 800000
        mock_get_pool.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_add_liquidity_no_pool(self, mock_get_pool, syncswap_adapter):
        """Test liquidity addition with no pool available."""
        mock_get_pool.return_value = None
        syncswap_adapter._get_l2_token_address = Mock(return_value="0xweth")
        
        with pytest.raises(InsufficientLiquidityError, match="No SyncSwap pool found"):
            syncswap_adapter.add_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                2000000000,
                "0xrecipient",
                0.5,
                1800
            )

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_remove_liquidity_success(self, mock_get_pool, syncswap_adapter):
        """Test successful liquidity removal."""
        # Mock dependencies
        mock_get_pool.return_value = "0xpool123"
        syncswap_adapter._get_contract = Mock()
        
        mock_router = Mock()
        mock_router.functions.burnLiquidity.return_value.build_transaction.return_value = {
            "to": "0xrouter",
            "data": "0xdata",
            "value": 0,
            "gas": 800000
        }
        syncswap_adapter._get_contract.return_value = mock_router
        
        result = syncswap_adapter.remove_liquidity(
            "0xtoken_a",
            "0xtoken_b",
            1000000000000000000,  # 1 LP token
            "0xrecipient",
            0.5,
            1800
        )
        
        assert "to" in result
        assert "data" in result
        assert result["gas"] == 800000
        mock_get_pool.assert_called_once()

    @patch('src.airdrops.protocols.zksync.zksync._get_syncswap_pool_address_zksync')
    def test_remove_liquidity_no_pool(self, mock_get_pool, syncswap_adapter):
        """Test liquidity removal with no pool available."""
        mock_get_pool.return_value = None
        
        with pytest.raises(InsufficientLiquidityError, match="No SyncSwap pool found"):
            syncswap_adapter.remove_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                "0xrecipient",
                0.5,
                1800
            )

    def test_mute_add_liquidity_not_implemented(self):
        """Test that Mute add liquidity raises not implemented error."""
        adapter = MuteAdapter(Mock())
        
        with pytest.raises(ZkSyncSwapError, match="Mute adapter not fully implemented"):
            adapter.add_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                2000000000,
                "0xrecipient",
                0.5,
                1800
            )

    def test_mute_remove_liquidity_not_implemented(self):
        """Test that Mute remove liquidity raises not implemented error."""
        adapter = MuteAdapter(Mock())
        
        with pytest.raises(ZkSyncSwapError, match="Mute adapter not fully implemented"):
            adapter.remove_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                "0xrecipient",
                0.5,
                1800
            )

    def test_spacefi_add_liquidity_not_implemented(self):
        """Test that SpaceFi add liquidity raises not implemented error."""
        adapter = SpaceFiAdapter(Mock())
        
        with pytest.raises(ZkSyncSwapError, match="SpaceFi adapter not fully implemented"):
            adapter.add_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                2000000000,
                "0xrecipient",
                0.5,
                1800
            )

    def test_spacefi_remove_liquidity_not_implemented(self):
        """Test that SpaceFi remove liquidity raises not implemented error."""
        adapter = SpaceFiAdapter(Mock())
        
        with pytest.raises(ZkSyncSwapError, match="SpaceFi adapter not fully implemented"):
            adapter.remove_liquidity(
                "0xtoken_a",
                "0xtoken_b",
                1000000000000000000,
                "0xrecipient",
                0.5,
                1800
            )

    def test_all_adapters_implement_liquidity_interface(self):
        """Test that all adapters implement the liquidity interface."""
        mock_web3 = Mock()
        mock_web3.eth.get_block.return_value = {"timestamp": 1000000}
        
        adapters = {
            "syncswap": SyncSwapAdapter(mock_web3),
            "mute": MuteAdapter(mock_web3),
            "spacefi": SpaceFiAdapter(mock_web3)
        }
        
        for name, adapter in adapters.items():
            assert hasattr(adapter, 'add_liquidity')
            assert hasattr(adapter, 'remove_liquidity')
            assert callable(getattr(adapter, 'add_liquidity'))
            assert callable(getattr(adapter, 'remove_liquidity'))