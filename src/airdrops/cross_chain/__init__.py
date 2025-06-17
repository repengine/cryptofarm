"""
Cross-Chain Capital Management Module.

This module provides automated cross-chain capital management and rebalancing
capabilities for the airdrop farming system.
"""

from airdrops.cross_chain.models import Chain, Wallet, RebalancingJob, JobStatus
from airdrops.cross_chain.manager import CrossChainManager
from airdrops.cross_chain.bridge_adapter import BridgeAdapter

__all__ = [
    "Chain",
    "Wallet",
    "RebalancingJob",
    "JobStatus",
    "CrossChainManager",
    "BridgeAdapter",
]