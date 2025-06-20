"""
Protocol interfaces for LayerZero protocol components.

This module defines typing.Protocol interfaces for the LayerZero protocol,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Any, Optional
from decimal import Decimal

__all__ = [
    "ILayerZeroProtocol",
]


class ILayerZeroProtocol(Protocol):
    """Protocol interface for LayerZero protocol operations.
    
    This protocol defines the interface for LayerZero-specific operations
    including cross-chain message passing and airdrop execution.
    
    Example:
        >>> def process_layerzero_operations(protocol: ILayerZeroProtocol) -> None:
        ...     # Type-safe usage of any LayerZero protocol implementation
        ...     tx_hash = protocol.perform_airdrop(
        ...         web3=web3,
        ...         private_key="0x...",
        ...         amount=Decimal("100"),
        ...         recipient="0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        ...     )
        ...     print(f"Airdrop transaction: {tx_hash}")
    """
    
    def __init__(
        self,
        web3: Any,
        private_key: str,
        endpoint_address: str
    ) -> None:
        """Initialize the LayerZero protocol instance.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            endpoint_address: Address of the LayerZero endpoint contract.
        """
        ...
    
    def perform_airdrop(
        self,
        web3: Any,
        private_key: str,
        amount: Decimal,
        recipient: str
    ) -> str:
        """Perform an airdrop operation using LayerZero.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            amount: Amount to airdrop as a Decimal.
            recipient: Address of the airdrop recipient.
            
        Returns:
            Transaction hash of the airdrop operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the airdrop transaction fails.
        """
        ...
    
    def send_message(
        self,
        web3: Any,
        private_key: str,
        destination_chain_id: int,
        destination_address: str,
        payload: bytes,
        adapter_params: bytes = b""
    ) -> str:
        """Send a cross-chain message via LayerZero.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            destination_chain_id: LayerZero chain ID of the destination.
            destination_address: Address on the destination chain.
            payload: Message payload to send.
            adapter_params: Optional adapter parameters for gas configuration.
            
        Returns:
            Transaction hash of the message sending operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the message sending fails.
        """
        ...
    
    def get_balance(
        self,
        web3: Any,
        address: str,
        token_address: Optional[str] = None
    ) -> Decimal:
        """Get the balance of an address for a specific token.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            address: Address to check balance for.
            token_address: Token contract address (None for native token).
            
        Returns:
            Balance as a Decimal.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If balance query fails.
        """
        ...