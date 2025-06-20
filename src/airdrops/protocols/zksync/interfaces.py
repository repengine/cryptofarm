"""
Protocol interfaces for ZkSync protocol components.

This module defines typing.Protocol interfaces for the ZkSync protocol,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Any
from decimal import Decimal

__all__ = [
    "IZkSyncProtocol",
]


class IZkSyncProtocol(Protocol):
    """Protocol interface for ZkSync protocol operations.
    
    This protocol defines the interface for ZkSync-specific operations
    including asset bridging and token swapping on ZkSync Era.
    
    Example:
        >>> def process_zksync_operations(protocol: IZkSyncProtocol) -> None:
        ...     # Type-safe usage of any ZkSync protocol implementation
        ...     tx_hash = protocol.bridge_assets(
        ...         web3_l1=web3_l1,
        ...         web3_l2=web3_l2,
        ...         private_key="0x...",
        ...         token_symbol="ETH",
        ...         amount=Decimal("0.1"),
        ...         direction="deposit"
        ...     )
        ...     print(f"Bridge transaction: {tx_hash}")
    """
    
    def __init__(
        self,
        web3_l1: Any,
        web3_l2: Any,
        private_key: str
    ) -> None:
        """Initialize the ZkSync protocol instance.
        
        Args:
            web3_l1: Web3 instance for Ethereum L1.
            web3_l2: Web3 instance for ZkSync L2.
            private_key: Private key for signing transactions.
        """
        ...
    
    def bridge_assets(
        self,
        web3_l1: Any,
        web3_l2: Any,
        private_key: str,
        token_symbol: str,
        amount: Decimal,
        direction: str
    ) -> str:
        """Bridge assets between Ethereum L1 and ZkSync L2.
        
        Args:
            web3_l1: Web3 instance for Ethereum L1.
            web3_l2: Web3 instance for ZkSync L2.
            private_key: Private key for signing transactions.
            token_symbol: Symbol of the token to bridge (e.g., "ETH", "USDC").
            amount: Amount to bridge as a Decimal.
            direction: Bridge direction ("deposit" for L1->L2, "withdraw" for L2->L1).
            
        Returns:
            Transaction hash of the bridge operation.
            
        Raises:
            ValueError: If parameters are invalid or unsupported.
            RuntimeError: If the bridge transaction fails.
        """
        ...
    
    def swap_tokens(
        self,
        web3: Any,
        private_key: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> str:
        """Swap tokens on ZkSync network.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            token_in: Address or symbol of input token.
            token_out: Address or symbol of output token.
            amount_in: Amount of input token to swap.
            min_amount_out: Minimum acceptable output amount (slippage protection).
            deadline: Transaction deadline timestamp.
            
        Returns:
            Transaction hash of the swap operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the swap transaction fails.
        """
        ...