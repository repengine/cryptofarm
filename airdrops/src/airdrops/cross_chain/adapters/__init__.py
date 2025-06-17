"""
Cross-chain bridge adapters package.

This package contains concrete implementations of the BridgeAdapter interface
for various cross-chain bridging protocols.
"""

from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
from airdrops.cross_chain.adapters.scroll_adapter import ScrollBridgeAdapter
from airdrops.cross_chain.adapters.zksync_adapter import ZkSyncBridgeAdapter

__all__ = [
    "LayerZeroBridgeAdapter",
    "ScrollBridgeAdapter",
    "ZkSyncBridgeAdapter",
]