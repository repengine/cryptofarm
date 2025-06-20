"""
Protocol interfaces for EigenLayer protocol components.

This module defines typing.Protocol interfaces for the EigenLayer protocol,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Any
from decimal import Decimal

__all__ = [
    "IEigenLayerProtocol",
]


class IEigenLayerProtocol(Protocol):
    """Protocol interface for EigenLayer protocol operations.
    
    This protocol defines the interface for EigenLayer-specific operations
    including liquid staking token (LST) restaking and withdrawal operations.
    
    Example:
        >>> def process_eigenlayer_operations(protocol: IEigenLayerProtocol) -> None:
        ...     # Type-safe usage of any EigenLayer protocol implementation
        ...     tx_hash = protocol.perform_airdrop(
        ...         web3=web3,
        ...         private_key="0x...",
        ...         amount=Decimal("1.0"),
        ...         recipient="0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
        ...     )
        ...     print(f"Airdrop transaction: {tx_hash}")
    """
    
    def __init__(
        self,
        web3: Any,
        private_key: str,
        strategy_manager_address: str
    ) -> None:
        """Initialize the EigenLayer protocol instance.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            strategy_manager_address: Address of the EigenLayer StrategyManager contract.
        """
        ...
    
    def perform_airdrop(
        self,
        web3: Any,
        private_key: str,
        amount: Decimal,
        recipient: str
    ) -> str:
        """Perform an airdrop operation using EigenLayer.
        
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
    
    def restake_lst(
        self,
        web3: Any,
        private_key: str,
        lst_token: str,
        amount: Decimal,
        strategy_address: str
    ) -> str:
        """Restake liquid staking tokens (LST) into EigenLayer.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            lst_token: Address of the LST token contract.
            amount: Amount of LST to restake.
            strategy_address: Address of the EigenLayer strategy contract.
            
        Returns:
            Transaction hash of the restaking operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the restaking transaction fails.
        """
        ...
    
    def withdraw_lst(
        self,
        web3: Any,
        private_key: str,
        strategy_address: str,
        shares: Decimal,
        withdrawer: str
    ) -> str:
        """Withdraw LST from EigenLayer restaking.
        
        Args:
            web3: Web3 instance for blockchain interaction.
            private_key: Private key for signing transactions.
            strategy_address: Address of the EigenLayer strategy contract.
            shares: Amount of strategy shares to withdraw.
            withdrawer: Address that will receive the withdrawn tokens.
            
        Returns:
            Transaction hash of the withdrawal operation.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If the withdrawal transaction fails.
        """
        ...