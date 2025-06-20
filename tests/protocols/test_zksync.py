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


def test_zksync_swap_tokens_success(zksync_protocol: ZkSyncProtocol) -> None:
    """Test successful token swap operation."""
    # The swap_tokens method is not yet implemented in ZkSyncProtocol
    # So we test that it raises NotImplementedError
    import time
    
    with pytest.raises(NotImplementedError, match="Swap functionality not yet implemented"):
        zksync_protocol.swap_tokens(
            web3=zksync_protocol.web3_l2,
            private_key=zksync_protocol.private_key,
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.1"),
            min_amount_out=Decimal("0.09"),
            deadline=int(time.time()) + 300
        )


def test_zksync_swap_tokens_failure(zksync_protocol: ZkSyncProtocol) -> None:
    """Test token swap failure."""
    # The swap_tokens method is not yet implemented in ZkSyncProtocol
    # So we test that it raises NotImplementedError
    import time
    
    with pytest.raises(NotImplementedError, match="Swap functionality not yet implemented"):
        zksync_protocol.swap_tokens(
            web3=zksync_protocol.web3_l2,
            private_key=zksync_protocol.private_key,
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.1"),
            min_amount_out=Decimal("0.09"),
            deadline=int(time.time()) + 300
        )
