"""
Additional coverage tests for the ZkSync protocol, focusing on edge cases and specific functionalities.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from airdrops.protocols.zksync import ZkSyncProtocol


@pytest.fixture
def zksync_protocol_coverage() -> ZkSyncProtocol:
    """Fixture for a ZkSyncProtocol instance for coverage tests."""
    return ZkSyncProtocol(
        l1_rpc_url="http://mock-zksync-coverage-l1-rpc.com",
        l2_rpc_url="http://mock-zksync-coverage-l2-rpc.com",
        private_key="0x" + "5" * 64,
    )


def test_zksync_protocol_invalid_private_key(zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test initialization with an invalid private key format."""
    with pytest.raises(ValueError, match="Private key must be a 64-character hex string"):
        ZkSyncProtocol(
            l1_rpc_url="http://mock-l1-rpc.com",
            l2_rpc_url="http://mock-l2-rpc.com",
            private_key="invalid_key",
        )


def test_zksync_protocol_empty_rpc_url(zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test initialization with an empty RPC URL."""
    with pytest.raises(ValueError, match="L1 RPC URL cannot be empty"):
        ZkSyncProtocol(
            l1_rpc_url="",
            l2_rpc_url="http://mock-l2-rpc.com",
            private_key="0x" + "6" * 64,
        )


def test_zksync_bridge_assets_success(zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test successful bridge assets operation."""
    with patch("airdrops.protocols.zksync.zksync.bridge_assets") as mock_bridge_assets:
        mock_bridge_assets.return_value = "0x" + "a" * 64
        
        tx_hash = zksync_protocol_coverage.bridge_assets(
            web3_l1=zksync_protocol_coverage.web3_l1,
            web3_l2=zksync_protocol_coverage.web3_l2,
            private_key=zksync_protocol_coverage.private_key,
            token_symbol="ETH",
            amount=Decimal("0.1"),
            direction="deposit"
        )
        
        assert tx_hash == "0x" + "a" * 64
        mock_bridge_assets.assert_called_once()


def test_zksync_bridge_assets_failure(zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test bridge assets failure."""
    with patch("airdrops.protocols.zksync.zksync.bridge_assets") as mock_bridge_assets:
        mock_bridge_assets.side_effect = Exception("Bridge failed")
        
        with pytest.raises(Exception, match="Bridge failed"):
            zksync_protocol_coverage.bridge_assets(
                web3_l1=zksync_protocol_coverage.web3_l1,
                web3_l2=zksync_protocol_coverage.web3_l2,
                private_key=zksync_protocol_coverage.private_key,
                token_symbol="ETH",
                amount=Decimal("0.1"),
                direction="deposit"
            )


@patch('airdrops.protocols.zksync.zksync.swap_tokens')
def test_zksync_swap_tokens_success(mock_swap_tokens, zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test successful token swap operation."""
    # Mock the swap_tokens function to return a transaction hash
    mock_swap_tokens.return_value = "0x123456789abcdef"
    
    result = zksync_protocol_coverage.swap_tokens(
        token_in="ETH",
        token_out="USDC",
        amount_in=Decimal("0.1"),
        slippage_percent=0.5,
        deadline_seconds=300
    )
    
    assert result == "0x123456789abcdef"
    mock_swap_tokens.assert_called_once()


@patch('airdrops.protocols.zksync.zksync.swap_tokens')
def test_zksync_swap_tokens_failure(mock_swap_tokens, zksync_protocol_coverage: ZkSyncProtocol) -> None:
    """Test token swap failure."""
    # Mock the swap_tokens function to raise an exception
    mock_swap_tokens.side_effect = ValueError("Insufficient balance")
    
    with pytest.raises(ValueError, match="Insufficient balance"):
        zksync_protocol_coverage.swap_tokens(
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.1"),
            slippage_percent=0.5,
            deadline_seconds=300
        )
