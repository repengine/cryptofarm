"""
Tests for LayerZero Bridge Adapter.

This module contains comprehensive unit tests for the LayerZeroBridgeAdapter
implementation, including positive cases, edge cases, and error conditions.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock

from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol


class TestLayerZeroBridgeAdapter:
    """Test suite for LayerZeroBridgeAdapter."""
    
    @pytest.fixture
    def mock_protocol(self):
        """Create a mock LayerZeroProtocol instance."""
        mock = Mock(spec=LayerZeroProtocol)
        mock.send_message.return_value = "0x123abc456def789"
        return mock
    
    @pytest.fixture
    def adapter(self, mock_protocol):
        """Create a LayerZeroBridgeAdapter instance with mocked protocol."""
        return LayerZeroBridgeAdapter(mock_protocol)
    
    def test_adapter_initialization_success(self, mock_protocol):
        """Test successful adapter initialization."""
        adapter = LayerZeroBridgeAdapter(mock_protocol)
        assert adapter._protocol is mock_protocol
    
    def test_adapter_initialization_none_protocol(self):
        """Test adapter initialization with None protocol raises ValueError."""
        with pytest.raises(ValueError, match="LayerZeroProtocol instance cannot be None"):
            LayerZeroBridgeAdapter(None)
    
    def test_get_supported_chains(self, adapter):
        """Test getting supported chains returns expected list."""
        chains = adapter.get_supported_chains()
        expected_chains = ["ethereum", "arbitrum", "optimism"]
        assert chains == expected_chains
        assert len(chains) == 3
    
    def test_get_supported_assets_valid_chain(self, adapter):
        """Test getting supported assets for valid chain."""
        assets = adapter.get_supported_assets("ethereum")
        expected_assets = ["USDC", "USDT", "WETH"]
        assert assets == expected_assets
        assert len(assets) == 3
    
    def test_get_supported_assets_invalid_chain(self, adapter):
        """Test getting supported assets for invalid chain raises ValueError."""
        with pytest.raises(ValueError, match="Chain 'invalid_chain' is not supported by LayerZero"):
            adapter.get_supported_assets("invalid_chain")
    
    def test_estimate_bridge_fee_valid_params(self, adapter):
        """Test fee estimation with valid parameters."""
        fee = adapter.estimate_bridge_fee(
            "ethereum", "arbitrum", "USDC", Decimal("100")
        )
        assert isinstance(fee, Decimal)
        assert fee > 0
        # Base fee (0.001) + amount factor (100/1000 * 0.0001) = 0.001 + 0.00001 = 0.00101
        expected_fee = Decimal("0.00101")
        assert fee == expected_fee
    
    def test_estimate_bridge_fee_large_amount(self, adapter):
        """Test fee estimation scales with larger amounts."""
        small_fee = adapter.estimate_bridge_fee(
            "ethereum", "arbitrum", "USDC", Decimal("100")
        )
        large_fee = adapter.estimate_bridge_fee(
            "ethereum", "arbitrum", "USDC", Decimal("10000")
        )
        assert large_fee > small_fee
    
    def test_estimate_bridge_fee_invalid_source_chain(self, adapter):
        """Test fee estimation with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by LayerZero"):
            adapter.estimate_bridge_fee("invalid", "arbitrum", "USDC", Decimal("100"))
    
    def test_estimate_bridge_fee_invalid_destination_chain(self, adapter):
        """Test fee estimation with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by LayerZero"):
            adapter.estimate_bridge_fee("ethereum", "invalid", "USDC", Decimal("100"))
    
    def test_estimate_bridge_fee_invalid_asset(self, adapter):
        """Test fee estimation with invalid asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported by LayerZero"):
            adapter.estimate_bridge_fee("ethereum", "arbitrum", "INVALID", Decimal("100"))
    
    def test_estimate_bridge_fee_negative_amount(self, adapter):
        """Test fee estimation with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "arbitrum", "USDC", Decimal("-100"))
    
    def test_estimate_bridge_fee_zero_amount(self, adapter):
        """Test fee estimation with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "arbitrum", "USDC", Decimal("0"))
    
    def test_estimate_bridge_fee_same_chains(self, adapter):
        """Test fee estimation with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.estimate_bridge_fee("ethereum", "ethereum", "USDC", Decimal("100"))
    
    def test_bridge_assets_success(self, adapter, mock_protocol):
        """Test successful bridge assets operation."""
        tx_hash = adapter.bridge_assets(
            "ethereum", "arbitrum", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_protocol.send_message.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_protocol.send_message.call_args
        assert call_args[1]["destination_chain_id"] == 42161  # Arbitrum chain ID
        assert call_args[1]["recipient_address"] == "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        assert call_args[1]["value"] == int(100 * 10**18)  # Amount in Wei
    
    def test_bridge_assets_invalid_source_chain(self, adapter):
        """Test bridge assets with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by LayerZero"):
            adapter.bridge_assets(
                "invalid", "arbitrum", "USDC", Decimal("100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_destination_chain(self, adapter):
        """Test bridge assets with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by LayerZero"):
            adapter.bridge_assets(
                "ethereum", "invalid", "USDC", Decimal("100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_asset(self, adapter):
        """Test bridge assets with invalid asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported by LayerZero"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "INVALID", Decimal("100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_negative_amount(self, adapter):
        """Test bridge assets with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "USDC", Decimal("-100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_zero_amount(self, adapter):
        """Test bridge assets with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "USDC", Decimal("0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_same_chains(self, adapter):
        """Test bridge assets with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.bridge_assets(
                "ethereum", "ethereum", "USDC", Decimal("100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_invalid_recipient_address_empty(self, adapter):
        """Test bridge assets with empty recipient address."""
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "USDC", Decimal("100"), ""
            )
    
    def test_bridge_assets_invalid_recipient_address_format(self, adapter):
        """Test bridge assets with invalid recipient address format."""
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "USDC", Decimal("100"), "invalid_address"
            )
    
    def test_bridge_assets_protocol_exception(self, adapter, mock_protocol):
        """Test bridge assets when protocol raises exception."""
        mock_protocol.send_message.side_effect = Exception("Protocol error")
        
        with pytest.raises(RuntimeError, match="Bridge transaction failed: Protocol error"):
            adapter.bridge_assets(
                "ethereum", "arbitrum", "USDC", Decimal("100"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
    
    def test_bridge_assets_unsupported_destination_chain_id(self, adapter):
        """Test bridge assets with destination chain that has no ID mapping."""
        # This test would require modifying the chain_id_map in the adapter
        # For now, all supported chains have mappings, so this is a future consideration
        pass
    
    def test_bridge_assets_optimism_chain_id(self, adapter, mock_protocol):
        """Test bridge assets to Optimism uses correct chain ID."""
        adapter.bridge_assets(
            "ethereum", "optimism", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        call_args = mock_protocol.send_message.call_args
        assert call_args[1]["destination_chain_id"] == 10  # Optimism chain ID
    
    def test_bridge_assets_ethereum_chain_id(self, adapter, mock_protocol):
        """Test bridge assets to Ethereum uses correct chain ID."""
        adapter.bridge_assets(
            "arbitrum", "ethereum", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        call_args = mock_protocol.send_message.call_args
        assert call_args[1]["destination_chain_id"] == 1  # Ethereum chain ID
    
    def test_bridge_assets_payload_format(self, adapter, mock_protocol):
        """Test bridge assets creates correct payload format."""
        adapter.bridge_assets(
            "ethereum", "arbitrum", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        call_args = mock_protocol.send_message.call_args
        payload = call_args[1]["payload"]
        expected_message = "Bridge 100 USDC to 0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        assert payload == expected_message.encode('utf-8')
    
    def test_all_supported_chains_have_assets(self, adapter):
        """Test that all supported chains return assets."""
        chains = adapter.get_supported_chains()
        for chain in chains:
            assets = adapter.get_supported_assets(chain)
            assert len(assets) > 0
            assert all(isinstance(asset, str) for asset in assets)
    
    def test_fee_estimation_consistency(self, adapter):
        """Test that fee estimation is consistent for same parameters."""
        fee1 = adapter.estimate_bridge_fee("ethereum", "arbitrum", "USDC", Decimal("100"))
        fee2 = adapter.estimate_bridge_fee("ethereum", "arbitrum", "USDC", Decimal("100"))
        assert fee1 == fee2
    
    def test_adapter_interface_compliance(self, adapter):
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