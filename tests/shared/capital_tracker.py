"""
Test utility for tracking capital allocation state.

This module provides the TestCapitalTracker wrapper class that adds stateful
tracking capabilities to the stateless CapitalAllocator for testing purposes.
"""

from decimal import Decimal
from typing import Dict, Any

from airdrops.capital_allocation.engine import CapitalAllocator


class TestCapitalTracker:
    """
    Test wrapper for CapitalAllocator that maintains capital state.
    
    This class wraps a CapitalAllocator instance and tracks the total capital
    state across multiple allocation calls, enabling stateful testing scenarios
    while preserving the stateless nature of the underlying allocator.
    
    Example:
        >>> from airdrops.capital_allocation.engine import CapitalAllocator
        >>> from decimal import Decimal
        >>> allocator = CapitalAllocator()
        >>> tracker = TestCapitalTracker(allocator, Decimal("100000"))
        >>> portfolio = {"scroll": Decimal("0.6"), "zksync": Decimal("0.4")}
        >>> risk_metrics = {"volatility_state": "medium", "gas_price_gwei": 50}
        >>> allocation = tracker.allocate_risk_adjusted_capital(
        ...     portfolio, risk_metrics
        ... )
        >>> print(f"Remaining capital: {tracker.total_capital}")
    """
    
    def __init__(self, allocator: CapitalAllocator, total_capital: Decimal) -> None:
        """
        Initialize the TestCapitalTracker.
        
        Args:
            allocator: The CapitalAllocator instance to wrap.
            total_capital: Initial total capital amount.
            
        Raises:
            ValueError: If total_capital is not positive.
            TypeError: If allocator is not a CapitalAllocator instance.
            
        Example:
            >>> allocator = CapitalAllocator()
            >>> tracker = TestCapitalTracker(allocator, Decimal("50000"))
        """
        if not isinstance(allocator, CapitalAllocator):
            raise TypeError("allocator must be a CapitalAllocator instance")
        
        if total_capital <= 0:
            raise ValueError("total_capital must be positive")
            
        self._allocator = allocator
        self.total_capital = total_capital
    
    def allocate_risk_adjusted_capital(
        self,
        portfolio_allocation: Dict[str, Decimal],
        risk_metrics: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """
        Allocate capital with risk adjustments and update internal state.
        
        This method delegates to the wrapped CapitalAllocator's 
        allocate_risk_adjusted_capital method using the current total_capital,
        then updates the internal capital state based on the allocation results.
        
        Args:
            portfolio_allocation: Target allocation percentages per protocol.
            risk_metrics: Current risk metrics from Risk Management System.
            
        Returns:
            Dictionary mapping protocol names to allocated capital amounts.
            
        Raises:
            ValueError: If portfolio_allocation is invalid.
            RuntimeError: If allocation fails.
            
        Example:
            >>> portfolio = {"scroll": Decimal("0.7"), "zksync": Decimal("0.3")}
            >>> risk_data = {"volatility_state": "low", "gas_price_gwei": 30}
            >>> allocation = tracker.allocate_risk_adjusted_capital(
            ...     portfolio, risk_data
            ... )
            >>> # tracker.total_capital is now updated based on allocation
        """
        if not portfolio_allocation:
            raise ValueError("portfolio_allocation cannot be empty")
            
        # Delegate to the wrapped allocator
        allocation_result = self._allocator.allocate_risk_adjusted_capital(
            self.total_capital,
            portfolio_allocation,
            risk_metrics
        )
        
        # Update internal capital state based on allocation results
        total_allocated = sum(allocation_result.values())
        self.total_capital -= total_allocated
        
        return allocation_result


__all__ = ["TestCapitalTracker"]