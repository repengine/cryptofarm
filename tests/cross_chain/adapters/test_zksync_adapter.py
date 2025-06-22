"""
Tests for ZkSync Bridge Adapter.

This module contains comprehensive unit tests for the ZkSyncBridgeAdapter
implementation, including positive cases, edge cases, and error conditions.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from airdrops.cross_chain.adapters.zksync_adapter import ZkSyncBridgeAdapter
from airdrops.protocols.zksync.zksync import ZkSyncProtocol


class TestZkSyncBridgeAdapter:
    """Test suite for ZkSyncBridgeAdapter."""
    
    @pytest.fixture
    def mock_protocol(self) -> Mock:
        """Create a mock ZkSyncProtocol instance."""
        mock = Mock(spec=ZkSyncProtocol)
        mock.bridge_assets.return_value = "0x123abc456def789"
        # Mock the attributes that the adapter accesses
        mock.web3_l1 = Mock()
        mock.web3_l2 = Mock()
        mock.private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        return mock
    
    @pytest.fixture
    def adapter(self, mock_protocol: Mock) -> ZkSyncBridgeAdapter:
        """Create a ZkSyncBridgeAdapter instance with mocked protocol."""
        return ZkSyncBridgeAdapter(mock_protocol)
    
    def test_adapter_initialization_success(self, mock_protocol: Mock) -> None:
        """Test successful adapter initialization."""
        adapter = ZkSyncBridgeAdapter(mock_protocol)
        assert adapter._protocol is mock_protocol
    
    def test_adapter_initialization_none_protocol(self) -> None:
        """Test adapter initialization with None protocol raises ValueError."""
        with pytest.raises(ValueError, match="ZkSyncProtocol instance cannot be None"):
            ZkSyncBridgeAdapter(None)  # type: ignore
    
    def test_get_supported_chains(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test getting supported chains returns expected list."""
        chains = adapter.get_supported_chains()
        expected_chains = ["ethereum", "zksync"]
        assert chains == expected_chains
        assert len(chains) == 2
    
    def test_get_supported_assets_valid_chain_ethereum(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test getting supported assets for ethereum chain."""
        assets = adapter.get_supported_assets("ethereum")
        expected_assets = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        assert assets == expected_assets
        assert len(assets) == 5
        assert "ETH" in assets  # Native ETH should be supported
    
    def test_get_supported_assets_valid_chain_zksync(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test getting supported assets for zksync chain."""
        assets = adapter.get_supported_assets("zksync")
        expected_assets = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        assert assets == expected_assets
        assert len(assets) == 5
        assert "ETH" in assets  # Native ETH should be supported
    
    def test_get_supported_assets_invalid_chain(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test getting supported assets for invalid chain raises ValueError."""
        with pytest.raises(ValueError, match="Chain 'invalid_chain' is not supported by ZkSync"):
            adapter.get_supported_assets("invalid_chain")
    
    def test_estimate_bridge_fee_l1_to_l2_eth(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation for L1 to L2 ETH bridge."""
        fee = adapter.estimate_bridge_fee(
            "ethereum", "zksync", "ETH", Decimal("1.0")
        )
        assert isinstance(fee, Decimal)
        assert fee > 0
        # L1 to L2 should have higher base fee (0.002) + amount factor
        expected_fee = Decimal("0.002") + (Decimal("1.0") / Decimal("10") * Decimal("0.0001"))
        assert fee == expected_fee
    
    def test_estimate_bridge_fee_l2_to_l1_eth(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation for L2 to L1 ETH bridge."""
        fee = adapter.estimate_bridge_fee(
            "zksync", "ethereum", "ETH", Decimal("1.0")
        )
        assert isinstance(fee, Decimal)
        assert fee > 0
        # L2 to L1 should have lower base fee (0.001) + amount factor
        expected_fee = Decimal("0.001") + (Decimal("1.0") / Decimal("10") * Decimal("0.0001"))
        assert fee == expected_fee
    
    def test_estimate_bridge_fee_erc20_token(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation for ERC20 token bridge."""
        fee = adapter.estimate_bridge_fee(
            "ethereum", "zksync", "USDC", Decimal("100")
        )
        assert isinstance(fee, Decimal)
        assert fee > 0
        # Should use L1 to L2 fee structure for USDC
        expected_fee = Decimal("0.002") + (Decimal("100") / Decimal("10") * Decimal("0.0001"))
        assert fee == expected_fee
    
    def test_estimate_bridge_fee_large_amount(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation scales with larger amounts."""
        small_fee = adapter.estimate_bridge_fee(
            "ethereum", "zksync", "ETH", Decimal("0.1")
        )
        large_fee = adapter.estimate_bridge_fee(
            "ethereum", "zksync", "ETH", Decimal("10.0")
        )
        assert large_fee > small_fee
    
    def test_estimate_bridge_fee_invalid_source_chain(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by ZkSync"):
            adapter.estimate_bridge_fee("invalid", "zksync", "ETH", Decimal("1.0"))
    
    def test_estimate_bridge_fee_invalid_destination_chain(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by ZkSync"):
            adapter.estimate_bridge_fee("ethereum", "invalid", "ETH", Decimal("1.0"))
    
    def test_estimate_bridge_fee_invalid_asset(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with invalid asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported by ZkSync"):
            adapter.estimate_bridge_fee("ethereum", "zksync", "INVALID", Decimal("1.0"))
    
    def test_estimate_bridge_fee_negative_amount(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "zksync", "ETH", Decimal("-1.0"))
    
    def test_estimate_bridge_fee_zero_amount(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "zksync", "ETH", Decimal("0"))
    
    def test_estimate_bridge_fee_same_chains(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test fee estimation with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.estimate_bridge_fee("ethereum", "ethereum", "ETH", Decimal("1.0"))
    
    def test_bridge_assets_l1_to_l2_success(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test successful L1 to L2 bridge assets operation."""
        tx_hash = adapter.bridge_assets(
            "ethereum", "zksync", "ETH", Decimal("1.0"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_protocol.bridge_assets.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["token_symbol"] == "ETH"
        assert call_args[1]["amount"] == Decimal("1.0")
        assert call_args[1]["direction"] == "deposit"
    
    def test_bridge_assets_l2_to_l1_success(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test successful L2 to L1 bridge assets operation."""
        tx_hash = adapter.bridge_assets(
            "zksync", "ethereum", "ETH", Decimal("1.0"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_protocol.bridge_assets.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["token_symbol"] == "ETH"
        assert call_args[1]["amount"] == Decimal("1.0")
        assert call_args[1]["direction"] == "withdraw"
    
    def test_bridge_assets_erc20_token_success(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test successful ERC20 token bridge operation."""
        tx_hash = adapter.bridge_assets(
            "ethereum", "zksync", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_protocol.bridge_assets.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["token_symbol"] == "USDC"
        assert call_args[1]["amount"] == Decimal("100")
        assert call_args[1]["direction"] == "deposit"
    
    def test_bridge_assets_invalid_source_chain(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by ZkSync"):
            adapter.bridge_assets(
                "invalid", "zksync", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_destination_chain(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by ZkSync"):
            adapter.bridge_assets(
                "ethereum", "invalid", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_asset(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with invalid asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported by ZkSync"):
            adapter.bridge_assets(
                "ethereum", "zksync", "INVALID", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_negative_amount(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "zksync", "ETH", Decimal("-1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_zero_amount(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "zksync", "ETH", Decimal("0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_same_chains(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.bridge_assets(
                "ethereum", "ethereum", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_recipient_address_empty(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with empty recipient address."""
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(
                "ethereum", "zksync", "ETH", Decimal("1.0"), ""
            )
    
    def test_bridge_assets_invalid_recipient_address_format(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with invalid recipient address format."""
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(
                "ethereum", "zksync", "ETH", Decimal("1.0"), "invalid_address"
            )
    
    def test_bridge_assets_invalid_direction(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test bridge assets with invalid chain combination."""
        # This should not happen with current supported chains, but test edge case
        with patch.object(adapter, 'get_supported_chains', return_value=['ethereum', 'zksync', 'polygon']):
            with pytest.raises(RuntimeError, match="Bridge transaction failed: Invalid bridge direction"):
                adapter.bridge_assets(
                    "ethereum", "polygon", "ETH", Decimal("1.0"),
                    "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
                )
    
    def test_bridge_assets_protocol_exception(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test bridge assets when protocol raises exception."""
        mock_protocol.bridge_assets.side_effect = Exception("Protocol error")
        
        with pytest.raises(RuntimeError, match="Bridge transaction failed: Protocol error"):
            adapter.bridge_assets(
                "ethereum", "zksync", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_all_supported_chains_have_assets(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that all supported chains return assets."""
        chains = adapter.get_supported_chains()
        for chain in chains:
            assets = adapter.get_supported_assets(chain)
            assert len(assets) > 0
            assert all(isinstance(asset, str) for asset in assets)
            assert "ETH" in assets  # ETH should be supported on all chains
    
    def test_fee_estimation_consistency(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that fee estimation is consistent for same parameters."""
        fee1 = adapter.estimate_bridge_fee("ethereum", "zksync", "ETH", Decimal("1.0"))
        fee2 = adapter.estimate_bridge_fee("ethereum", "zksync", "ETH", Decimal("1.0"))
        assert fee1 == fee2
    
    def test_fee_estimation_direction_difference(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that L1->L2 fees are higher than L2->L1 fees."""
        l1_to_l2_fee = adapter.estimate_bridge_fee("ethereum", "zksync", "ETH", Decimal("1.0"))
        l2_to_l1_fee = adapter.estimate_bridge_fee("zksync", "ethereum", "ETH", Decimal("1.0"))
        assert l1_to_l2_fee > l2_to_l1_fee
    
    def test_adapter_interface_compliance(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that adapter implements all required BridgeAdapter methods."""
        # Test that all abstract methods are implemented
        assert hasattr(adapter, 'get_supported_chains')
        assert hasattr(adapter, 'get_supported_assets')
        assert hasattr(adapter, 'estimate_bridge_fee')
        assert hasattr(adapter, 'bridge_assets')
        
        # Test that methods are callable
        assert callable(adapter.get_supported_chains)
        assert callable(adapter.get_supported_assets)
        assert callable(adapter.estimate_bridge_fee)
        assert callable(adapter.bridge_assets)
    
    def test_supported_assets_include_native_eth(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that ETH is included in supported assets for all chains."""
        chains = adapter.get_supported_chains()
        for chain in chains:
            assets = adapter.get_supported_assets(chain)
            assert "ETH" in assets
    
    def test_supported_assets_include_erc20_tokens(self, adapter: ZkSyncBridgeAdapter) -> None:
        """Test that common ERC20 tokens are supported."""
        assets = adapter.get_supported_assets("ethereum")
        expected_tokens = ["USDC", "USDT", "WETH", "DAI"]
        for token in expected_tokens:
            assert token in assets
    
    def test_bridge_direction_mapping(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test that bridge directions are correctly mapped."""
        # Test L1 to L2 (deposit)
        adapter.bridge_assets(
            "ethereum", "zksync", "ETH", Decimal("1.0"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["direction"] == "deposit"
        
        # Reset mock
        mock_protocol.reset_mock()
        
        # Test L2 to L1 (withdraw)
        adapter.bridge_assets(
            "zksync", "ethereum", "ETH", Decimal("1.0"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["direction"] == "withdraw"
    
    def test_decimal_amount_preservation(self, adapter: ZkSyncBridgeAdapter, mock_protocol: Mock) -> None:
        """Test that Decimal amounts are preserved in protocol calls."""
        amount = Decimal("1.23456789")
        adapter.bridge_assets(
            "ethereum", "zksync", "ETH", amount,
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        call_args = mock_protocol.bridge_assets.call_args
        assert call_args[1]["amount"] == amount
        assert isinstance(call_args[1]["amount"], Decimal)