"""
Tests for Scroll Bridge Adapter.

This module contains comprehensive unit tests for the ScrollBridgeAdapter
implementation, including positive cases, edge cases, and error conditions.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import Mock, patch

from airdrops.cross_chain.adapters.scroll_adapter import ScrollBridgeAdapter


class TestScrollBridgeAdapter:
    """Test suite for ScrollBridgeAdapter."""

    @pytest.fixture
    def mock_web3_l1(self) -> Mock:
        """Create a mock Web3 instance for L1."""
        mock = Mock()
        mock.eth.gas_price = 20000000000  # 20 gwei
        return mock

    @pytest.fixture
    def mock_web3_l2(self) -> Mock:
        """Create a mock Web3 instance for L2."""
        mock = Mock()
        mock.eth.gas_price = 1000000000  # 1 gwei
        return mock

    @pytest.fixture
    def private_key(self) -> str:
        """Return a test private key."""
        return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    @pytest.fixture
    def adapter(self, mock_web3_l1: Mock, mock_web3_l2: Mock, private_key: str) -> ScrollBridgeAdapter:
        """Create a ScrollBridgeAdapter instance with mocked dependencies."""
        return ScrollBridgeAdapter(mock_web3_l1, mock_web3_l2, private_key)

    def test_adapter_initialization_success(self, mock_web3_l1: Mock, mock_web3_l2: Mock, private_key: str) -> None:
        """Test successful adapter initialization."""
        adapter = ScrollBridgeAdapter(mock_web3_l1, mock_web3_l2, private_key)
        assert adapter.web3_l1 is mock_web3_l1
        assert adapter.web3_l2 is mock_web3_l2
        assert adapter.private_key == private_key

    def test_get_supported_chains(self, adapter: ScrollBridgeAdapter) -> None:
        """Test getting supported chains returns expected list."""
        chains = adapter.get_supported_chains()
        expected_chains = ["ethereum", "scroll"]
        assert chains == expected_chains
        assert len(chains) == 2

    def test_get_supported_assets_valid_chain_ethereum(self, adapter: ScrollBridgeAdapter) -> None:
        """Test getting supported assets for ethereum chain."""
        assets = adapter.get_supported_assets("ethereum")
        expected_assets = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        assert assets == expected_assets
        assert len(assets) == 5
        assert "ETH" in assets  # Native ETH should be supported

    def test_get_supported_assets_valid_chain_scroll(self, adapter: ScrollBridgeAdapter) -> None:
        """Test getting supported assets for scroll chain."""
        assets = adapter.get_supported_assets("scroll")
        expected_assets = ["ETH", "USDC", "USDT", "WETH", "DAI"]
        assert assets == expected_assets
        assert len(assets) == 5
        assert "ETH" in assets  # Native ETH should be supported

    def test_get_supported_assets_invalid_chain(self, adapter: ScrollBridgeAdapter) -> None:
        """Test getting supported assets for invalid chain raises ValueError."""
        with pytest.raises(ValueError, match="Chain 'invalid_chain' is not supported by Scroll"):
            adapter.get_supported_assets("invalid_chain")

    def test_estimate_bridge_fee_l1_to_l2_eth(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation for L1 to L2 ETH bridge."""
        fee = adapter.estimate_bridge_fee(
            "ethereum", "scroll", "ETH", Decimal("1.0")
        )
        assert isinstance(fee, Decimal)
        assert fee == Decimal("0.001")  # L1 to L2 ETH fee

    def test_estimate_bridge_fee_l1_to_l2_erc20(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation for L1 to L2 ERC20 bridge."""
        fee = adapter.estimate_bridge_fee(
            "ethereum", "scroll", "USDC", Decimal("100")
        )
        assert isinstance(fee, Decimal)
        assert fee == Decimal("0.0015")  # L1 to L2 ERC20 fee

    def test_estimate_bridge_fee_l2_to_l1_eth(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation for L2 to L1 ETH bridge."""
        fee = adapter.estimate_bridge_fee(
            "scroll", "ethereum", "ETH", Decimal("1.0")
        )
        assert isinstance(fee, Decimal)
        assert fee == Decimal("0.005")  # L2 to L1 ETH fee

    def test_estimate_bridge_fee_l2_to_l1_erc20(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation for L2 to L1 ERC20 bridge."""
        fee = adapter.estimate_bridge_fee(
            "scroll", "ethereum", "USDC", Decimal("100")
        )
        assert isinstance(fee, Decimal)
        assert fee == Decimal("0.007")  # L2 to L1 ERC20 fee

    def test_estimate_bridge_fee_same_chains(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.estimate_bridge_fee("ethereum", "ethereum", "ETH", Decimal("1.0"))

    def test_estimate_bridge_fee_invalid_source_chain(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by Scroll"):
            adapter.estimate_bridge_fee("invalid", "scroll", "ETH", Decimal("1.0"))

    def test_estimate_bridge_fee_invalid_destination_chain(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by Scroll"):
            adapter.estimate_bridge_fee("ethereum", "invalid", "ETH", Decimal("1.0"))

    def test_estimate_bridge_fee_unsupported_asset(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with unsupported asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported on ethereum"):
            adapter.estimate_bridge_fee("ethereum", "scroll", "INVALID", Decimal("1.0"))

    def test_estimate_bridge_fee_negative_amount(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "scroll", "ETH", Decimal("-1.0"))

    def test_estimate_bridge_fee_zero_amount(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.estimate_bridge_fee("ethereum", "scroll", "ETH", Decimal("0"))

    def test_estimate_bridge_fee_invalid_direction(self, adapter: ScrollBridgeAdapter) -> None:
        """Test fee estimation with invalid bridge direction."""
        # This should not happen with current supported chains, but test edge case
        with patch.object(adapter, 'get_supported_chains', return_value=['ethereum', 'scroll', 'polygon']):
            with pytest.raises(ValueError, match="Invalid bridge direction"):
                adapter.estimate_bridge_fee("ethereum", "polygon", "ETH", Decimal("1.0"))

    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_success_l1_to_l2_eth(self, mock_bridge_assets: Mock, adapter: ScrollBridgeAdapter) -> None:
        """Test successful bridge assets operation from L1 to L2 with ETH."""
        mock_bridge_assets.return_value = "0x123abc456def789"
        
        tx_hash = adapter.bridge_assets(
            "ethereum", "scroll", "ETH", Decimal("1.0"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_bridge_assets.assert_called_once_with(
            web3_l1=adapter.web3_l1,
            web3_l2=adapter.web3_l2,
            private_key=adapter.private_key,
            token_symbol="ETH",
            amount=1000000000000000000,  # 1 ETH in Wei
            direction="deposit"
        )

    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_success_l2_to_l1_eth(self, mock_bridge_assets: Mock, adapter: ScrollBridgeAdapter) -> None:
        """Test successful bridge assets operation from L2 to L1 with ETH."""
        mock_bridge_assets.return_value = "0x123abc456def789"
        
        tx_hash = adapter.bridge_assets(
            "scroll", "ethereum", "ETH", Decimal("0.5"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_bridge_assets.assert_called_once_with(
            web3_l1=adapter.web3_l1,
            web3_l2=adapter.web3_l2,
            private_key=adapter.private_key,
            token_symbol="ETH",
            amount=500000000000000000,  # 0.5 ETH in Wei
            direction="withdraw"
        )

    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_success_usdc(self, mock_bridge_assets: Mock, adapter: ScrollBridgeAdapter) -> None:
        """Test successful bridge assets operation with USDC."""
        mock_bridge_assets.return_value = "0x123abc456def789"
        
        tx_hash = adapter.bridge_assets(
            "ethereum", "scroll", "USDC", Decimal("100"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_bridge_assets.assert_called_once_with(
            web3_l1=adapter.web3_l1,
            web3_l2=adapter.web3_l2,
            private_key=adapter.private_key,
            token_symbol="USDC",
            amount=100000000,  # 100 USDC with 6 decimals
            direction="deposit"
        )

    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_success_weth(self, mock_bridge_assets: Mock, adapter: ScrollBridgeAdapter) -> None:
        """Test successful bridge assets operation with WETH."""
        mock_bridge_assets.return_value = "0x123abc456def789"
        
        tx_hash = adapter.bridge_assets(
            "ethereum", "scroll", "WETH", Decimal("2.5"),
            "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        )
        
        assert tx_hash == "0x123abc456def789"
        mock_bridge_assets.assert_called_once_with(
            web3_l1=adapter.web3_l1,
            web3_l2=adapter.web3_l2,
            private_key=adapter.private_key,
            token_symbol="WETH",
            amount=2500000000000000000,  # 2.5 WETH with 18 decimals
            direction="deposit"
        )

    def test_bridge_assets_same_chains(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with same source and destination chains."""
        with pytest.raises(ValueError, match="Source and destination chains must be different"):
            adapter.bridge_assets(
                "ethereum", "ethereum", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_invalid_source_chain(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with invalid source chain."""
        with pytest.raises(ValueError, match="Source chain 'invalid' is not supported by Scroll"):
            adapter.bridge_assets(
                "invalid", "scroll", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_invalid_destination_chain(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with invalid destination chain."""
        with pytest.raises(ValueError, match="Destination chain 'invalid' is not supported by Scroll"):
            adapter.bridge_assets(
                "ethereum", "invalid", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_unsupported_asset(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with unsupported asset."""
        with pytest.raises(ValueError, match="Asset 'INVALID' is not supported on ethereum"):
            adapter.bridge_assets(
                "ethereum", "scroll", "INVALID", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_negative_amount(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with negative amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("-1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_zero_amount(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_invalid_recipient_address_format(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with invalid recipient address format."""
        with pytest.raises(ValueError, match="Recipient address must start with '0x'"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("1.0"),
                "invalid_address"
            )

    def test_bridge_assets_invalid_recipient_address_prefix(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with invalid recipient address prefix."""
        with pytest.raises(ValueError, match="Recipient address must start with '0x'"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("1.0"),
                "742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_bridge_assets_empty_recipient_address(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with empty recipient address."""
        with pytest.raises(ValueError, match="Invalid recipient address format"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("1.0"),
                ""
            )

    def test_bridge_assets_invalid_direction(self, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets with invalid chain combination."""
        # This should not happen with current supported chains, but test edge case
        with patch.object(adapter, 'get_supported_chains', return_value=['ethereum', 'scroll', 'polygon']):
            with pytest.raises(ValueError, match="Invalid bridge direction"):
                adapter.bridge_assets(
                    "ethereum", "polygon", "ETH", Decimal("1.0"),
                    "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
                )

    @patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets')
    def test_bridge_assets_protocol_error(self, mock_bridge_assets: Mock, adapter: ScrollBridgeAdapter) -> None:
        """Test bridge assets when protocol raises an exception."""
        mock_bridge_assets.side_effect = Exception("Protocol error")
        
        with pytest.raises(RuntimeError, match="Bridge transaction failed: Protocol error"):
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )

    def test_adapter_interface_compliance(self, adapter: ScrollBridgeAdapter) -> None:
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

    def test_adapter_logging_integration(self, adapter: ScrollBridgeAdapter, caplog: Any) -> None:
        """Test that adapter properly logs bridge operations."""
        with patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets') as mock_bridge:
            mock_bridge.return_value = "0x123abc456def789"
            
            adapter.bridge_assets(
                "ethereum", "scroll", "ETH", Decimal("1.0"),
                "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            )
            
            # Check that info log was created for successful transaction
            assert "Scroll bridge transaction initiated: 0x123abc456def789" in caplog.text

    def test_adapter_logging_error(self, adapter: ScrollBridgeAdapter, caplog: Any) -> None:
        """Test that adapter properly logs bridge operation errors."""
        with patch('airdrops.cross_chain.adapters.scroll_adapter.bridge_assets') as mock_bridge:
            mock_bridge.side_effect = Exception("Test error")
            
            with pytest.raises(RuntimeError):
                adapter.bridge_assets(
                    "ethereum", "scroll", "ETH", Decimal("1.0"),
                    "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
                )
            
            # Check that error log was created
            assert "Scroll bridge transaction failed: Test error" in caplog.text