"""
Protocol interfaces for Scroll protocol components.

This module defines typing.Protocol interfaces for the Scroll protocol,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Any

__all__ = [
    "IScrollProtocol",
]


class IScrollProtocol(Protocol):
    """Protocol interface for Scroll protocol operations.
    
    This protocol defines the interface for Scroll-specific operations
    including token swapping and asset bridging between L1 and L2.
    
    Example:
        >>> def process_scroll_operations(protocol: IScrollProtocol) -> None:
        ...     # Type-safe usage of any Scroll protocol implementation
        ...     tx_hash = protocol.bridge_assets(
        ...         web3_l1=web3_l1,
        ...         web3_l2=web3_l2,
        ...         private_key="0x...",
        ...         token_symbol="ETH",
        ...         amount=1000000000000000000,  # 1 ETH in wei
        ...         direction="deposit"
        ...     )
        ...     print(f"Bridge transaction: {tx_hash}")
    """
    
    def swap_tokens(
        self,
        web3: Any,
        private_key: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        deadline: int
    ) -> str:
        """Swap tokens on Scroll network.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            token_in: Address or symbol of input token.
            token_out: Address or symbol of output token.
            amount_in: Amount of input token to swap (in smallest units).
            min_amount_out: Minimum acceptable output amount (slippage protection).
            deadline: Transaction deadline timestamp.
            
        Returns:
            Transaction hash of the swap operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the swap transaction fails.
        """
        ...
    
    def bridge_assets(
        self,
        web3_l1: Any,
        web3_l2: Any,
        private_key: str,
        token_symbol: str,
        amount: int,
        direction: str
    ) -> str:
        """Bridge assets between Ethereum L1 and Scroll L2.
        
        Args:
            web3_l1: Web3 instance for Ethereum L1.
            web3_l2: Web3 instance for Scroll L2.
            private_key: Private key for signing transactions.
            token_symbol: Symbol of the token to bridge (e.g., "ETH", "USDC").
            amount: Amount to bridge in smallest token units (wei for ETH).
            direction: Bridge direction ("deposit" for L1->L2, "withdraw" for L2->L1).
            
        Returns:
            Transaction hash of the bridge operation.
            
        Raises:
            ValueError: If parameters are invalid or unsupported.
            RuntimeError: If the bridge transaction fails.
        """
        ...