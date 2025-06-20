"""
Protocol interfaces for Risk Management components.

This module defines typing.Protocol interfaces for the risk management system,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Dict, Any
from decimal import Decimal

__all__ = [
    "IRiskManager",
]


class IRiskManager(Protocol):
    """Protocol interface for risk management operations.
    
    This protocol defines the interface for risk assessment, monitoring,
    and circuit breaker functionality in the airdrop system.
    
    Example:
        >>> def process_risk_management(manager: IRiskManager) -> None:
        ...     # Type-safe usage of any risk manager implementation
        ...     risk_score = manager.assess_current_risk()
        ...     if risk_score > Decimal("0.8"):
        ...         manager.trigger_circuit_breaker("High risk detected")
        ...     print(f"Current risk score: {risk_score}")
    """
    
    def __init__(
        self,
        config: Dict[str, Any]
    ) -> None:
        """Initialize the risk manager.
        
        Args:
            config: Configuration dictionary containing risk parameters.
        """
        ...
    
    def assess_current_risk(self) -> Decimal:
        """Assess the current risk level of the system.
        
        Returns:
            Risk score as a Decimal between 0.0 (no risk) and 1.0 (maximum risk).
            
        Raises:
            RuntimeError: If risk assessment fails.
        """
        ...
    
    def monitor_positions(
        self,
        positions: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """Monitor current positions for risk exposure.
        
        Args:
            positions: Dictionary mapping asset symbols to position sizes.
            
        Returns:
            Dictionary containing risk metrics and alerts.
            
        Raises:
            ValueError: If positions data is invalid.
            RuntimeError: If monitoring fails.
        """
        ...
    
    def trigger_circuit_breaker(
        self,
        reason: str
    ) -> bool:
        """Trigger the circuit breaker to halt operations.
        
        Args:
            reason: Reason for triggering the circuit breaker.
            
        Returns:
            True if circuit breaker was successfully triggered.
            
        Raises:
            RuntimeError: If circuit breaker activation fails.
        """
        ...
    
    def check_position_limits(
        self,
        asset: str,
        proposed_amount: Decimal
    ) -> bool:
        """Check if a proposed position change violates risk limits.
        
        Args:
            asset: Asset symbol to check.
            proposed_amount: Proposed position change amount.
            
        Returns:
            True if the position change is within risk limits.
            
        Raises:
            ValueError: If parameters are invalid.
        """
        ...
    
    def calculate_var(
        self,
        positions: Dict[str, Decimal],
        confidence_level: Decimal = Decimal("0.95")
    ) -> Decimal:
        """Calculate Value at Risk (VaR) for current positions.
        
        Args:
            positions: Dictionary mapping asset symbols to position sizes.
            confidence_level: Confidence level for VaR calculation (default 95%).
            
        Returns:
            VaR value as a Decimal.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If VaR calculation fails.
        """
        ...