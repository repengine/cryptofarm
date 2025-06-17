"""
Scroll Bridge Adapter

This module provides the ScrollBridgeAdapter class that implements the BridgeAdapter
interface for cross-chain bridging operations using the Scroll protocol.

The adapter supports bridging between Ethereum (L1) and Scroll (L2) networks,
handling both ETH and ERC20 token transfers with proper fee estimation.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Set

from airdrops.cross_chain.adapters.base import BridgeAdapter
from airdrops.cross_chain.types import BridgeRequest, BridgeResult
from airdrops.protocols.scroll.scroll import bridge_assets
from airdrops.shared.constants import SCROLL_TOKEN_ADDRESSES


class ScrollBridgeAdapter(BridgeAdapter):
    """
    Bridge adapter for Scroll protocol operations.
    
    Provides a standardized interface for cross-chain bridging between
    Ethereum and Scroll networks using the Scroll protocol.
    
    Attributes:
        protocol: The Scroll protocol instance for bridge operations
        
    Example:
        >>> from airdrops.protocols.scroll.scroll import ScrollProtocol
        >>> protocol = ScrollProtocol()
        >>> adapter = ScrollBridgeAdapter(protocol)
        >>> chains = adapter.get_supported_chains()
        >>> print(chains)  # {'ethereum', 'scroll'}
    """
    
    def __init__(self, protocol):
        """
        Initialize the Scroll bridge adapter.
        
        Args:
            protocol: Scroll protocol instance for bridge operations
        """
        super().__init__(protocol)
    
    def get_supported_chains(self) -> Set[str]:
        """
        Get the set of blockchain networks supported by Scroll.
        
        Returns:
            Set of supported chain identifiers
            
        Example:
            >>> adapter = ScrollBridgeAdapter(protocol)
            >>> chains = adapter.get_supported_chains()
            >>> print(chains)  # {'ethereum', 'scroll'}
        """
        return {"ethereum", "scroll"}
    
    def get_supported_assets(self, chain: str) -> Set[str]:
        """
        Get the set of assets supported for bridging on a specific chain.
        
        Args:
            chain: The blockchain network identifier
            
        Returns:
            Set of supported asset symbols
            
        Raises:
            ValueError: If the chain is not supported
            
        Example:
            >>> adapter = ScrollBridgeAdapter(protocol)
            >>> assets = adapter.get_supported_assets("ethereum")
            >>> print(assets)  # {'ETH', 'USDC', 'USDT', 'WETH', 'DAI'}
        """
        if chain not in self.get_supported_chains():
            raise ValueError(f"Chain '{chain}' is not supported by Scroll")
        
        # ETH is natively supported, plus configured ERC20 tokens
        supported_assets = {"ETH"}
        supported_assets.update(SCROLL_TOKEN_ADDRESSES.keys())
        
        return supported_assets
    
    def estimate_bridge_fee(
        self,
        source_chain: str,
        destination_chain: str,
        asset: str,
        amount: Decimal
    ) -> Decimal:
        """
        Estimate the fee for a cross-chain bridge operation.
        
        Args:
            source_chain: Source blockchain network
            destination_chain: Destination blockchain network  
            asset: Asset symbol to bridge
            amount: Amount to bridge
            
        Returns:
            Estimated bridge fee in the same units as amount
            
        Raises:
            ValueError: If chains or asset are not supported
            
        Example:
            >>> adapter = ScrollBridgeAdapter(protocol)
            >>> fee = adapter.estimate_bridge_fee("ethereum", "scroll", "ETH", Decimal("1.0"))
            >>> print(f"Bridge fee: {fee} ETH")
        """
        # Validate chains
        supported_chains = self.get_supported_chains()
        if source_chain not in supported_chains:
            raise ValueError(f"Source chain '{source_chain}' is not supported")
        if destination_chain not in supported_chains:
            raise ValueError(f"Destination chain '{destination_chain}' is not supported")
        
        # Validate asset
        if asset not in self.get_supported_assets(source_chain):
            raise ValueError(f"Asset '{asset}' is not supported on {source_chain}")
        
        # Determine bridge direction
        if source_chain == "ethereum" and destination_chain == "scroll":
            # L1 to L2 (deposit) - lower fees
            if asset == "ETH":
                return Decimal("0.001")  # ~$3-4 at current ETH prices
            else:
                return Decimal("0.0015")  # Slightly higher for ERC20
        elif source_chain == "scroll" and destination_chain == "ethereum":
            # L2 to L1 (withdrawal) - higher fees due to proof generation
            if asset == "ETH":
                return Decimal("0.005")  # ~$15-20 at current ETH prices
            else:
                return Decimal("0.007")  # Higher for ERC20 withdrawals
        else:
            raise ValueError(f"Invalid bridge route: {source_chain} -> {destination_chain}")
    
    def bridge_assets(self, request: BridgeRequest) -> BridgeResult:
        """
        Execute a cross-chain bridge operation.
        
        Args:
            request: Bridge operation request details
            
        Returns:
            Result of the bridge operation
            
        Raises:
            ValueError: If request parameters are invalid
            
        Example:
            >>> from airdrops.cross_chain.types import BridgeRequest
            >>> request = BridgeRequest(
            ...     source_chain="ethereum",
            ...     destination_chain="scroll", 
            ...     asset="ETH",
            ...     amount=Decimal("1.0"),
            ...     recipient_address="0x123..."
            ... )
            >>> result = adapter.bridge_assets(request)
            >>> print(f"Transaction hash: {result.transaction_hash}")
        """
        # Validate request
        self._validate_bridge_request(request)
        
        # Determine bridge direction for Scroll protocol
        if request.source_chain == "ethereum" and request.destination_chain == "scroll":
            direction = "deposit"
        elif request.source_chain == "scroll" and request.destination_chain == "ethereum":
            direction = "withdraw"
        else:
            raise ValueError(
                f"Invalid bridge route: {request.source_chain} -> {request.destination_chain}"
            )
        
        # Convert amount to appropriate units
        if request.asset == "ETH":
            # Convert ETH to Wei (10^18)
            amount_in_units = int(request.amount * Decimal("10") ** 18)
        else:
            # For ERC20 tokens, convert to smallest units
            # Most tokens use 6 decimals (USDC, USDT) or 18 decimals (WETH, DAI)
            if request.asset in ["USDC", "USDT"]:
                decimals = 6
            else:
                decimals = 18
            amount_in_units = int(request.amount * Decimal("10") ** decimals)
        
        # Execute bridge operation using the protocol
        try:
            result = bridge_assets(
                protocol=self.protocol,
                asset=request.asset,
                amount=amount_in_units,
                recipient=request.recipient_address,
                direction=direction
            )
            
            return BridgeResult(
                success=True,
                transaction_hash=result.get("transaction_hash"),
                bridge_fee=self.estimate_bridge_fee(
                    request.source_chain,
                    request.destination_chain,
                    request.asset,
                    request.amount
                ),
                estimated_completion_time=result.get("estimated_completion_time", 600)  # 10 minutes default
            )
            
        except Exception as e:
            return BridgeResult(
                success=False,
                error_message=f"Bridge operation failed: {str(e)}"
            )
    
    def _validate_bridge_request(self, request: BridgeRequest) -> None:
        """
        Validate a bridge request for Scroll protocol requirements.
        
        Args:
            request: Bridge request to validate
            
        Raises:
            ValueError: If request is invalid
        """
        # Validate chains
        supported_chains = self.get_supported_chains()
        if request.source_chain not in supported_chains:
            raise ValueError(f"Source chain '{request.source_chain}' is not supported")
        if request.destination_chain not in supported_chains:
            raise ValueError(f"Destination chain '{request.destination_chain}' is not supported")
        
        # Validate asset
        if request.asset not in self.get_supported_assets(request.source_chain):
            raise ValueError(f"Asset '{request.asset}' is not supported on {request.source_chain}")
        
        # Validate amount
        if request.amount <= 0:
            raise ValueError("Bridge amount must be positive")
        
        # Validate recipient address
        if not request.recipient_address or len(request.recipient_address) != 42:
            raise ValueError("Invalid recipient address format")
        if not request.recipient_address.startswith("0x"):
            raise ValueError("Recipient address must start with '0x'")


__all__ = ["ScrollBridgeAdapter"]