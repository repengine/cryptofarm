"""
Tests for the ZkSync protocol.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from airdrops.protocols.zksync import ZkSyncProtocol


@pytest.fixture
def zksync_protocol() -> ZkSyncProtocol:
    """Fixture for a ZkSyncProtocol instance."""
    # In a real integration test, this would connect to a testnet or mock RPC
    # For now, we'll mock the internal web3 calls if necessary.
    return ZkSyncProtocol(
        l1_rpc_url="http://mock-zksync-l1-rpc.com",
        l2_rpc_url="http://mock-zksync-l2-rpc.com",
        private_key="0x" + "2" * 64,
    )


def test_zksync_protocol_initialization(zksync_protocol: ZkSyncProtocol) -> None:
    """Test that the ZkSyncProtocol initializes correctly."""
    assert zksync_protocol.l1_rpc_url == "http://mock-zksync-l1-rpc.com"
    assert zksync_protocol.l2_rpc_url == "http://mock-zksync-l2-rpc.com"
    assert zksync_protocol.web3_l1 is not None
    assert zksync_protocol.web3_l2 is not None


def test_zksync_bridge_assets_success(zksync_protocol: ZkSyncProtocol) -> None:
    """Test successful bridge assets operation."""
    # Mock the underlying bridge_assets function that's called internally
    with patch("airdrops.protocols.zksync.zksync.bridge_assets") as mock_bridge_assets:
        mock_bridge_assets.return_value = "0x" + "a" * 64
        
        tx_hash = zksync_protocol.bridge_assets(
            web3_l1=zksync_protocol.web3_l1,
            web3_l2=zksync_protocol.web3_l2,
            private_key=zksync_protocol.private_key,
            token_symbol="ETH",
            amount=Decimal("0.1"),
            direction="deposit"
        )
        
        assert tx_hash == "0x" + "a" * 64
        mock_bridge_assets.assert_called_once()


def test_zksync_bridge_assets_failure(zksync_protocol: ZkSyncProtocol) -> None:
    """Test bridge assets failure."""
    with patch("airdrops.protocols.zksync.zksync.bridge_assets") as mock_bridge_assets:
        mock_bridge_assets.side_effect = Exception("Bridge failed")
        
        with pytest.raises(Exception, match="Bridge failed"):
            zksync_protocol.bridge_assets(
                web3_l1=zksync_protocol.web3_l1,
                web3_l2=zksync_protocol.web3_l2,
                private_key=zksync_protocol.private_key,
                token_symbol="ETH",
                amount=Decimal("0.1"),
                direction="deposit"
            )


@patch('airdrops.protocols.zksync.zksync.swap_tokens')
def test_zksync_swap_tokens_success(mock_swap_tokens, zksync_protocol: ZkSyncProtocol) -> None:
    """Test successful token swap operation."""
    # Mock the swap_tokens function to return a transaction hash
    mock_swap_tokens.return_value = "0x123456789abcdef"
    
    result = zksync_protocol.swap_tokens(
        token_in="ETH",
        token_out="USDC",
        amount_in=Decimal("0.1"),
        slippage_percent=0.5,
        deadline_seconds=300
    )
    
    assert result == "0x123456789abcdef"
    mock_swap_tokens.assert_called_once()


@patch('airdrops.protocols.zksync.zksync.swap_tokens')
def test_zksync_swap_tokens_failure(mock_swap_tokens, zksync_protocol: ZkSyncProtocol) -> None:
    """Test token swap failure."""
    # Mock the swap_tokens function to raise an exception
    mock_swap_tokens.side_effect = ValueError("Insufficient balance")
    
    with pytest.raises(ValueError, match="Insufficient balance"):
        zksync_protocol.swap_tokens(
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.1"),
            slippage_percent=0.5,
            deadline_seconds=300
        )


@patch('airdrops.protocols.zksync.zksync.provide_liquidity')
def test_zksync_provide_liquidity_success(mock_provide_liquidity, zksync_protocol: ZkSyncProtocol) -> None:
    """Test successful liquidity provision operation."""
    # Mock the provide_liquidity function to return a transaction hash
    mock_provide_liquidity.return_value = "0x123456789abcdef"

    result = zksync_protocol.provide_liquidity(
        token_a="ETH",
        token_b="USDC",
        amount_a=Decimal("1.0"),
        amount_b=Decimal("2000.0"),
        dex="syncswap"
    )

    assert result == "0x123456789abcdef"
    mock_provide_liquidity.assert_called_once()


@patch('airdrops.protocols.zksync.zksync.provide_liquidity')
def test_zksync_provide_liquidity_failure(mock_provide_liquidity, zksync_protocol: ZkSyncProtocol) -> None:
    """Test liquidity provision failure."""
    # Mock the provide_liquidity function to raise an exception
    mock_provide_liquidity.side_effect = ValueError("Insufficient balance")

    with pytest.raises(ValueError, match="Insufficient balance"):
        zksync_protocol.provide_liquidity(
            token_a="ETH",
            token_b="USDC",
            amount_a=Decimal("1.0"),
            amount_b=Decimal("2000.0"),
            dex="syncswap"
        )


@patch('airdrops.protocols.zksync.zksync.remove_liquidity')
def test_zksync_remove_liquidity_success(mock_remove_liquidity, zksync_protocol: ZkSyncProtocol) -> None:
    """Test successful liquidity removal operation."""
    # Mock the remove_liquidity function to return a transaction hash
    mock_remove_liquidity.return_value = "0x987654321fedcba"

    result = zksync_protocol.remove_liquidity(
        token_a="ETH",
        token_b="USDC",
        liquidity_percent=50.0,
        dex="syncswap"
    )

    assert result == "0x987654321fedcba"
    mock_remove_liquidity.assert_called_once()


@patch('airdrops.protocols.zksync.zksync.remove_liquidity')
def test_zksync_remove_liquidity_failure(mock_remove_liquidity, zksync_protocol: ZkSyncProtocol) -> None:
    """Test liquidity removal failure."""
    # Mock the remove_liquidity function to raise an exception
    mock_remove_liquidity.side_effect = ValueError("No LP tokens found")

    with pytest.raises(ValueError, match="No LP tokens found"):
        zksync_protocol.remove_liquidity(
            token_a="ETH",
            token_b="USDC",
            liquidity_percent=50.0,
            dex="syncswap"
        )


def test_zksync_provide_liquidity_parameter_validation(zksync_protocol: ZkSyncProtocol) -> None:
    """Test parameter validation for provide_liquidity."""
    with patch('airdrops.protocols.zksync.zksync.provide_liquidity') as mock_provide:
        mock_provide.return_value = "0x123"
        
        # Test with valid parameters
        result = zksync_protocol.provide_liquidity(
            token_a="ETH",
            token_b="USDC",
            amount_a=Decimal("1.0"),
            amount_b=Decimal("2000.0")
        )
        
        assert result == "0x123"
        
        # Verify the function was called with correct wei amounts
        call_args = mock_provide.call_args
        assert call_args[1]['amount_a'] == 1000000000000000000  # 1 ETH in wei
        assert call_args[1]['amount_b'] == 2000000000000000000000  # 2000 * 10^18


def test_zksync_remove_liquidity_parameter_validation(zksync_protocol: ZkSyncProtocol) -> None:
    """Test parameter validation for remove_liquidity."""
    with patch('airdrops.protocols.zksync.zksync.remove_liquidity') as mock_remove:
        mock_remove.return_value = "0x456"
        
        # Test with valid parameters
        result = zksync_protocol.remove_liquidity(
            token_a="ETH",
            token_b="USDC",
            liquidity_percent=25.5
        )
        
        assert result == "0x456"
        
        # Verify the function was called with correct parameters
        call_args = mock_remove.call_args
        assert call_args[1]['liquidity_percent'] == 25.5
