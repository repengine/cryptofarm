"""
Protocol interfaces for Cross Chain components.

This module defines typing.Protocol interfaces for the cross-chain management system,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Dict, Any, Optional
from decimal import Decimal

__all__ = [
    "ICrossChainManager",
]


class ICrossChainManager(Protocol):
    """Protocol interface for cross-chain management operations.
    
    This protocol defines the interface for cross-chain rebalancing,
    liquidity management, and chain coordination operations.
    
    Example:
        >>> def process_cross_chain_operations(manager: ICrossChainManager) -> None:
        ...     # Type-safe usage of any cross-chain manager implementation
        ...     manager.add_chain("ethereum", "https://eth.llamarpc.com")
        ...     rebalance_needed = manager.check_liquidity_thresholds()
        ...     if rebalance_needed:
        ...         manager.initiate_rebalancing()
        ...     print("Cross-chain operations completed")
    """
    
    def __init__(
        self,
        config: Dict[str, Any]
    ) -> None:
        """Initialize the cross-chain manager.
        
        Args:
            config: Configuration dictionary containing chain and bridge settings.
        """
        ...
    
    def initiate_rebalancing(
        self,
        source_chain: Optional[str] = None,
        target_chain: Optional[str] = None,
        asset: Optional[str] = None,
        amount: Optional[Decimal] = None
    ) -> str:
        """Initiate cross-chain rebalancing operation.
        
        Args:
            source_chain: Source chain identifier (optional for auto-selection).
            target_chain: Target chain identifier (optional for auto-selection).
            asset: Asset to rebalance (optional for auto-selection).
            amount: Amount to rebalance (optional for auto-calculation).
            
        Returns:
            Transaction hash or operation ID for tracking.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If rebalancing initiation fails.
        """
        ...
    
    def check_liquidity_thresholds(self) -> bool:
        """Check if any chains have liquidity below configured thresholds.
        
        Returns:
            True if rebalancing is needed due to liquidity thresholds.
            
        Raises:
            RuntimeError: If liquidity check fails.
        """
        ...
    
    def add_chain(
        self,
        chain_id: str,
        rpc_url: str,
        bridge_adapter: Any = None
    ) -> bool:
        """Add a new blockchain to the cross-chain manager.
        
        Args:
            chain_id: Unique identifier for the blockchain.
            rpc_url: RPC endpoint URL for the blockchain.
            bridge_adapter: Optional bridge adapter for cross-chain operations.
            
        Returns:
            True if chain was successfully added.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If chain addition fails.
        """
        ...
    
    def get_chain_balances(
        self,
        chain_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Decimal]]:
        """Get asset balances across chains.
        
        Args:
            chain_id: Specific chain to query (None for all chains).
            
        Returns:
            Dictionary mapping chain IDs to asset balances.
            
        Raises:
            ValueError: If chain_id is invalid.
            RuntimeError: If balance query fails.
        """
        ...
    
    def estimate_bridge_time(
        self,
        source_chain: str,
        target_chain: str,
        asset: str
    ) -> int:
        """Estimate bridge completion time in seconds.
        
        Args:
            source_chain: Source chain identifier.
            target_chain: Target chain identifier.
            asset: Asset to bridge.
            
        Returns:
            Estimated completion time in seconds.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If estimation fails.
        """
        ...
    
    def get_optimal_bridge_route(
        self,
        source_chain: str,
        target_chain: str,
        asset: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Find the optimal bridge route for an asset transfer.
        
        Args:
            source_chain: Source chain identifier.
            target_chain: Target chain identifier.
            asset: Asset to bridge.
            amount: Amount to bridge.
            
        Returns:
            Dictionary containing route information, fees, and timing.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If route calculation fails.
        """
        ...