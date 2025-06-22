"""
Protocol interfaces for Capital Allocation components.

This module defines typing.Protocol interfaces for the capital allocation system,
enabling type-safe mocking and dependency injection in tests and production code.
"""

from typing import Protocol, Dict, Any, List, Tuple, Optional, TYPE_CHECKING
from decimal import Decimal

# Import RebalanceOrder for return type annotation
if TYPE_CHECKING:
    from airdrops.capital_allocation.engine import RebalanceOrder

__all__ = [
    "ICapitalAllocator",
]


class ICapitalAllocator(Protocol):
    """Protocol interface for capital allocation operations.
    
    This protocol defines the interface for portfolio optimization,
    capital allocation, and rebalancing operations.
    
    Example:
        >>> def process_capital_allocation(allocator: ICapitalAllocator) -> None:
        ...     # Type-safe usage of any capital allocator implementation
        ...     portfolio = allocator.optimize_portfolio(
        ...         available_capital=Decimal("10000"),
        ...         risk_tolerance=Decimal("0.5")
        ...     )
        ...     print(f"Optimized portfolio: {portfolio}")
    """
    
    def __init__(
        self,
        config: Dict[str, Any]
    ) -> None:
        """Initialize the capital allocator.
        
        Args:
            config: Configuration dictionary containing allocation parameters.
        """
        ...
    
    def optimize_portfolio(
        self,
        protocols: List[str],
        risk_constraints: Dict[str, Any],
        risk_scores: Optional[Dict[str, Decimal]] = None,
        expected_returns: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Decimal]:
        """Optimize portfolio allocation based on protocols and risk constraints.
        
        Args:
            protocols: List of protocol names to allocate capital across.
            risk_constraints: Risk constraints and parameters for optimization.
            risk_scores: Optional risk scores for each protocol (0.0-1.0).
            expected_returns: Optional expected returns for each protocol.
            
        Returns:
            Dictionary mapping protocol names to allocation amounts.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If optimization fails.
        """
        ...
    
    def allocate_risk_adjusted_capital(
        self,
        total_capital: Decimal,
        risk_scores: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Allocate capital with risk adjustments.
        
        Args:
            total_capital: Total capital to allocate.
            risk_scores: Dictionary mapping assets to risk scores (0.0-1.0).
            target_allocations: Target allocation percentages for each asset.
            
        Returns:
            Dictionary mapping asset symbols to risk-adjusted allocation amounts.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If allocation calculation fails.
        """
        ...
    
    def rebalance_portfolio(
        self,
        current_allocations: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal],
        total_portfolio_value: Decimal
    ) -> List["RebalanceOrder"]:
        """Generate rebalancing orders to align portfolio with target allocations.
        
        Args:
            current_allocations: Current allocation percentages by protocol.
            target_allocations: Target allocation percentages.
            total_portfolio_value: Total portfolio value for calculating amounts.
            
        Returns:
            List of RebalanceOrder objects sorted by priority.
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If rebalancing calculation fails.
        """
        ...
    
    def calculate_sharpe_ratio(
        self,
        returns: List[Decimal],
        risk_free_rate: Decimal = Decimal("0.02")
    ) -> Decimal:
        """Calculate Sharpe ratio for a series of returns.
        
        Args:
            returns: List of historical returns.
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
            
        Returns:
            Sharpe ratio as a Decimal.
            
        Raises:
            ValueError: If returns data is invalid.
            RuntimeError: If calculation fails.
        """
        ...
    
    def estimate_portfolio_risk(
        self,
        allocations: Dict[str, Decimal],
        correlation_matrix: Dict[Tuple[str, str], Decimal]
    ) -> Decimal:
        """Estimate portfolio risk based on allocations and correlations.
        
        Args:
            allocations: Portfolio allocations by asset.
            correlation_matrix: Correlation matrix between assets.
            
        Returns:
            Estimated portfolio risk (standard deviation).
            
        Raises:
            ValueError: If parameters are invalid.
            RuntimeError: If risk estimation fails.
        """
        ...