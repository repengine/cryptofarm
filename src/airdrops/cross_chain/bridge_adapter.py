"""
Bridge Adapter Abstract Base Class.

This module provides the abstract base class for all bridge protocol adapters,
defining a unified interface for cross-chain bridging operations.
"""

import abc
from decimal import Decimal
from typing import List

__all__ = [
    "BridgeAdapter",
]


class BridgeAdapter(abc.ABC):
    """Abstract base class for all bridge protocol adapters.
    
    This class defines the common interface that all bridge adapters must implement
    to provide standardized cross-chain bridging functionality. It enables the
    CrossChainManager to interact with different bridging protocols through a
    unified interface.
    
    Example:
        >>> # Concrete implementation would look like:
        >>> class LayerZeroBridgeAdapter(BridgeAdapter):
        ...     def get_supported_chains(self) -> List[str]:
        ...         return ["ethereum", "arbitrum", "polygon"]
        ...     
        ...     def get_supported_assets(self, chain: str) -> List[str]:
        ...         return ["USDC", "USDT", "ETH"]
        ...     
        ...     def estimate_bridge_fee(self, source_chain: str, 
        ...                           destination_chain: str, asset: str, 
        ...                           amount: Decimal) -> Decimal:
        ...         return Decimal("0.01")  # Example fee
        ...     
        ...     def bridge_assets(self, source_chain: str, destination_chain: str,
        ...                      asset: str, amount: Decimal, 
        ...                      recipient_address: str) -> str:
        ...         return "0x123...abc"  # Transaction hash
    """
    
    @abc.abstractmethod
    def get_supported_chains(self) -> List[str]:
        """Returns a list of chain names supported by the bridge.
        
        This method should return the canonical names of all blockchain networks
        that this bridge adapter can facilitate transfers between.
        
        Returns:
            List[str]: A list of supported chain names (e.g., ["ethereum", "arbitrum"]).
            
        Example:
            >>> adapter = SomeBridgeAdapter()
            >>> chains = adapter.get_supported_chains()
            >>> print(chains)
            ['ethereum', 'arbitrum', 'polygon']
        """
        raise NotImplementedError("Subclasses must implement get_supported_chains")
    
    @abc.abstractmethod
    def get_supported_assets(self, chain: str) -> List[str]:
        """Returns a list of asset symbols supported on a given chain.
        
        This method should return the asset symbols that can be bridged
        from or to the specified chain using this bridge adapter.
        
        Args:
            chain: The name of the blockchain network to query.
            
        Returns:
            List[str]: A list of supported asset symbols (e.g., ["USDC", "ETH"]).
            
        Raises:
            ValueError: If the chain is not supported by this bridge.
            
        Example:
            >>> adapter = SomeBridgeAdapter()
            >>> assets = adapter.get_supported_assets("ethereum")
            >>> print(assets)
            ['USDC', 'USDT', 'ETH', 'WBTC']
        """
        raise NotImplementedError("Subclasses must implement get_supported_assets")
    
    @abc.abstractmethod
    def estimate_bridge_fee(
        self, 
        source_chain: str, 
        destination_chain: str, 
        asset: str, 
        amount: Decimal
    ) -> Decimal:
        """Estimates the fee for a bridge transaction.
        
        This method should calculate and return the estimated fee for bridging
        the specified amount of an asset from the source chain to the destination chain.
        
        Args:
            source_chain: The name of the source blockchain network.
            destination_chain: The name of the destination blockchain network.
            asset: The symbol of the asset to bridge.
            amount: The amount of the asset to bridge.
            
        Returns:
            Decimal: The estimated bridge fee in the same units as the asset.
            
        Raises:
            ValueError: If any of the parameters are invalid or unsupported.
            
        Example:
            >>> adapter = SomeBridgeAdapter()
            >>> fee = adapter.estimate_bridge_fee(
            ...     "ethereum", "arbitrum", "USDC", Decimal("100")
            ... )
            >>> print(f"Bridge fee: {fee} USDC")
            Bridge fee: 0.50 USDC
        """
        raise NotImplementedError("Subclasses must implement estimate_bridge_fee")
    
    @abc.abstractmethod
    def bridge_assets(
        self, 
        source_chain: str, 
        destination_chain: str, 
        asset: str, 
        amount: Decimal, 
        recipient_address: str
    ) -> str:
        """Initiates a bridge transaction.
        
        This method should execute the actual bridge transaction, transferring
        the specified amount of an asset from the source chain to the destination
        chain for the given recipient address.
        
        Args:
            source_chain: The name of the source blockchain network.
            destination_chain: The name of the destination blockchain network.
            asset: The symbol of the asset to bridge.
            amount: The amount of the asset to bridge.
            recipient_address: The address to receive the bridged assets.
            
        Returns:
            str: A transaction hash or unique job ID for tracking the bridge operation.
            
        Raises:
            ValueError: If any of the parameters are invalid or unsupported.
            RuntimeError: If the bridge transaction fails to initiate.
            
        Example:
            >>> adapter = SomeBridgeAdapter()
            >>> tx_hash = adapter.bridge_assets(
            ...     "ethereum", "arbitrum", "USDC", Decimal("100"),
            ...     "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
            ... )
            >>> print(f"Bridge transaction: {tx_hash}")
            Bridge transaction: 0x123abc...def789
        """
        raise NotImplementedError("Subclasses must implement bridge_assets")