"""
Tests for ScrollBridgeAdapter

This module contains comprehensive tests for the ScrollBridgeAdapter class,
covering initialization, supported chains/assets, fee estimation, and bridge operations.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from airdrops.cross_chain.adapters.scroll_adapter import ScrollBridgeAdapter
from airdrops.cross_chain.types import BridgeRequest, BridgeResult


class TestScrollBridgeAdapter:
    """Test suite for ScrollBridgeAdapter class."""
    
    @pytest.fixture
    def mock_protocol(self):
        """Create a mock Scroll protocol instance."""
        return Mock()
    
    @pytest.fixture
    def adapter(self, mock_protocol):
        """Create a ScrollBridgeAdapter instance with mock protocol."""
        return ScrollBridgeAdapter(mock_protocol)
    
    def test_initialization(self, mock_protocol):
        """Test adapter initialization."""
        adapter = ScrollBridgeAdapter(mock_protocol)
        assert adapter.protocol == mock_protocol
    
    def test_get_supported_chains(self, adapter):
        """Test getting supported blockchain networks."""
        chains = adapter.get_supported_chains()
        assert chains == {"ethereum", "scroll"}
        assert len(chains) == 2
    
    def test_get_supported_assets_ethereum(self, adapter):
        """Test getting supported assets for Ethereum chain."""
        assets = adapter.get_supported_assets("ethereum")
        
        # Should include ETH and tokens from SCROLL_TOKEN_ADDRESSES
        assert "ETH" in assets
        assert isinstance(assets, set)
        assert len(assets) >= 1  # At least ETH
    
    def test_get_supported_assets_scroll(self, adapter):
        """Test getting supported assets for Scroll chain."""
        assets = adapter.get_supported_assets("scroll")
        
        # Should include ETH and tokens from SCROLL_TOKEN_ADDRESSES
        assert "ETH" in assets
        assert isinstance(assets, set)
        assert len(assets) >= 1  # At least ETH
    
    def test_get_supported_assets_unsupported_chain(self, adapter):
        """Test getting supported assets for unsupported chain."""
        with pytest.raises(ValueError, match="Chain 'polygon' is not supported"):
            adapter.get_supported_assets("polygon")
    
    def test_estimate_bridge_fee_ethereum_to_scroll_eth(self, adapter):
        """Test fee estimation for ETH deposit (L1 to L2)."""
        fee = adapter.estimate_bridge_fee("ethereum", "scroll", "ETH", Decimal("1.0"))
        assert fee == Decimal("0.001")
        assert isinstance(fee, Decimal)
    
    def test_estimate_bridge_fee_ethereum_to_scroll_erc20(self, adapter):
        """Test fee estimation for ERC20 deposit (L1 to L2)."""
        fee = adapter.estimate_bridge_fee("ethereum", "scroll", "USDC", Decimal("100.0"))
        assert fee == Decimal("0.0015")
        assert isinstance(fee, Decimal)
    
    def test_estimate_bridge_fee_scroll_to_ethereum_eth(self, adapter):
        """Test fee estimation for ETH withdrawal (L2 to L1)."""
        fee = adapter.estimate_bridge_fee("scroll", "ethereum", "ETH", Decimal("1.0"))
        assert fee == Decimal("0.005")
        assert isinstance(fee, Decimal)
    
    def test_estimate_bridge_fee_scroll_to_ethereum_erc20(self, adapter):
        """Test fee estimation for ERC20 withdrawal (L2 to L1)."""
        fee = adapter.estimate_bridge_fee("scroll", "ethereum", "USDC", Decimal("100.0"))
        assert fee == Decimal("0.007")
        assert isinstance(fee, Decimal)
    
    def test_estimate_bridge_fee_unsupported_source_chain(self, adapter):
        """Test fee estimation with unsupported source chain."""
        with pytest.raises(ValueError, match="Source chain 'polygon' is not supported"):
            adapter.estimate_bridge_fee("polygon", "scroll", "ETH", Decimal("1.0"))
    
    def test_estimate_bridge_fee_unsupported_destination_chain(self, adapter):
        """Test fee estimation with unsupported destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'polygon' is not supported"):
            adapter.estimate_bridge_fee("ethereum", "polygon", "ETH", Decimal("1.0"))
    
    def test_estimate_bridge_fee_unsupported_asset(self, adapter):
        """Test fee estimation with unsupported asset."""
        with pytest.raises(ValueError, match="Asset 'BTC' is not supported"):
            adapter.estimate_bridge_fee("ethereum", "scroll", "BTC", Decimal("1.0"))
    
    def test_estimate_bridge_fee_invalid_route(self, adapter):
        """Test fee estimation with invalid bridge route."""
        with pytest.raises(ValueError, match="Invalid bridge route"):
            adapter.estimate_bridge_fee("scroll", "scroll", "ETH", Decimal("1.0"))
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_successful_deposit(self, mock_bridge_assets, adapter):
        """Test successful bridge operation for deposit (L1 to L2)."""
        # Setup mock response
        mock_bridge_assets.return_value = {
            "transaction_hash": "0xabc123",
            "estimated_completion_time": 300
        }
        
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is True
        assert result.transaction_hash == "0xabc123"
        assert result.bridge_fee == Decimal("0.001")
        assert result.estimated_completion_time == 300
        assert result.error_message is None
        
        # Verify bridge_assets was called with correct parameters
        mock_bridge_assets.assert_called_once_with(
            protocol=adapter.protocol,
            asset="ETH",
            amount=1000000000000000000,  # 1 ETH in Wei
            recipient="0x1234567890123456789012345678901234567890",
            direction="deposit"
        )
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_successful_withdrawal(self, mock_bridge_assets, adapter):
        """Test successful bridge operation for withdrawal (L2 to L1)."""
        # Setup mock response
        mock_bridge_assets.return_value = {
            "transaction_hash": "0xdef456",
            "estimated_completion_time": 1800
        }
        
        request = BridgeRequest(
            source_chain="scroll",
            destination_chain="ethereum",
            asset="ETH",
            amount=Decimal("0.5"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is True
        assert result.transaction_hash == "0xdef456"
        assert result.bridge_fee == Decimal("0.005")
        assert result.estimated_completion_time == 1800
        
        # Verify bridge_assets was called with correct parameters
        mock_bridge_assets.assert_called_once_with(
            protocol=adapter.protocol,
            asset="ETH",
            amount=500000000000000000,  # 0.5 ETH in Wei
            recipient="0x1234567890123456789012345678901234567890",
            direction="withdraw"
        )
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_usdc_deposit(self, mock_bridge_assets, adapter):
        """Test bridge operation for USDC deposit with 6 decimals."""
        # Setup mock response
        mock_bridge_assets.return_value = {
            "transaction_hash": "0xghi789"
        }
        
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="USDC",
            amount=Decimal("100.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is True
        assert result.bridge_fee == Decimal("0.0015")
        
        # Verify USDC amount conversion (6 decimals)
        mock_bridge_assets.assert_called_once_with(
            protocol=adapter.protocol,
            asset="USDC",
            amount=100000000,  # 100 USDC with 6 decimals
            recipient="0x1234567890123456789012345678901234567890",
            direction="deposit"
        )
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_weth_deposit(self, mock_bridge_assets, adapter):
        """Test bridge operation for WETH deposit with 18 decimals."""
        # Setup mock response
        mock_bridge_assets.return_value = {
            "transaction_hash": "0xjkl012"
        }
        
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="WETH",
            amount=Decimal("2.5"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is True
        
        # Verify WETH amount conversion (18 decimals)
        mock_bridge_assets.assert_called_once_with(
            protocol=adapter.protocol,
            asset="WETH",
            amount=2500000000000000000,  # 2.5 WETH with 18 decimals
            recipient="0x1234567890123456789012345678901234567890",
            direction="deposit"
        )
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_protocol_exception(self, mock_bridge_assets, adapter):
        """Test bridge operation when protocol raises exception."""
        # Setup mock to raise exception
        mock_bridge_assets.side_effect = Exception("Protocol error")
        
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is False
        assert "Bridge operation failed: Protocol error" in result.error_message
        assert result.transaction_hash is None
        assert result.bridge_fee is None
    
    def test_bridge_assets_invalid_source_chain(self, adapter):
        """Test bridge operation with invalid source chain."""
        request = BridgeRequest(
            source_chain="polygon",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Source chain 'polygon' is not supported"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_invalid_destination_chain(self, adapter):
        """Test bridge operation with invalid destination chain."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="polygon",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Destination chain 'polygon' is not supported"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_invalid_asset(self, adapter):
        """Test bridge operation with invalid asset."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="BTC",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Asset 'BTC' is not supported"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_invalid_route(self, adapter):
        """Test bridge operation with invalid route."""
        request = BridgeRequest(
            source_chain="scroll",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Invalid bridge route"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_zero_amount(self, adapter):
        """Test bridge operation with zero amount."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Bridge amount must be positive"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_negative_amount(self, adapter):
        """Test bridge operation with negative amount."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("-1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Bridge amount must be positive"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_invalid_recipient_address_format(self, adapter):
        """Test bridge operation with invalid recipient address format."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="invalid_address"
        )
        
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_invalid_recipient_address_prefix(self, adapter):
        """Test bridge operation with invalid recipient address prefix."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="1234567890123456789012345678901234567890"
        )
        
        with pytest.raises(ValueError, match="Recipient address must start with '0x'"):
            adapter.bridge_assets(request)
    
    def test_bridge_assets_empty_recipient_address(self, adapter):
        """Test bridge operation with empty recipient address."""
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address=""
        )
        
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(request)
    
    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_default_completion_time(self, mock_bridge_assets, adapter):
        """Test bridge operation with default completion time when not provided."""
        # Setup mock response without estimated_completion_time
        mock_bridge_assets.return_value = {
            "transaction_hash": "0xmno345"
        }
        
        request = BridgeRequest(
            source_chain="ethereum",
            destination_chain="scroll",
            asset="ETH",
            amount=Decimal("1.0"),
            recipient_address="0x1234567890123456789012345678901234567890"
        )
        
        result = adapter.bridge_assets(request)
        
        assert result.success is True
        assert result.estimated_completion_time == 600  # Default 10 minutes