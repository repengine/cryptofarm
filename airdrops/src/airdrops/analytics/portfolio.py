"""
Portfolio Performance Analytics Module.

This module provides comprehensive portfolio performance analysis for airdrop
activities, including value tracking, diversification metrics, and
    benchmark comparisons.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from airdrops.analytics.tracker import AirdropTracker
from airdrops.analytics.optimizer import ROIOptimizer

# Configure logging
logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Supported benchmark types for performance comparison."""
    ETH = "eth"
    BTC = "btc"
    MARKET_INDEX = "market_index"


class PortfolioSnapshot(BaseModel):
    """Portfolio state at a specific point in time."""
    snapshot_date: datetime
    total_value_usd: Decimal
    protocol_allocations: Dict[str, Decimal]  # protocol_name -> value_usd
    token_allocations: Dict[str, Decimal]     # token_symbol -> value_usd
    diversification_score: Decimal = Field(..., ge=0, le=1)


class PortfolioMetrics(BaseModel):
    """Comprehensive portfolio performance metrics."""
    calculation_date: datetime
    total_portfolio_value_usd: Decimal
    total_profit_loss_usd: Decimal
    total_cost_usd: Decimal
    portfolio_roi_percentage: Decimal
    protocol_count: int
    token_count: int
    diversification_index: Decimal = Field(..., ge=0, le=1)
    largest_position_percentage: Decimal = Field(..., ge=0, le=100)
    value_at_risk_usd: Optional[Decimal] = None


class BenchmarkComparison(BaseModel):
    """Portfolio performance compared to benchmark."""
    benchmark_type: BenchmarkType
    portfolio_return_percentage: Decimal
    benchmark_return_percentage: Decimal
    alpha_percentage: Decimal  # Portfolio return - Benchmark return
    comparison_period_days: int
    calculation_date: datetime


class PortfolioPerformanceAnalyzer:
    """
    Portfolio performance analytics engine.

    Provides comprehensive analysis of airdrop portfolio performance including
    value tracking, diversification metrics, and benchmark comparisons.

    Example:
        >>> tracker = AirdropTracker()
        >>> analyzer = PortfolioPerformanceAnalyzer(tracker)
        >>> metrics = analyzer.calculate_portfolio_metrics()
        >>> print(f"Portfolio ROI: {metrics.portfolio_roi_percentage}%")
    """

    def __init__(
        self,
        tracker: AirdropTracker,
        roi_optimizer: Optional[ROIOptimizer] = None
    ) -> None:
        """
        Initialize the portfolio performance analyzer.

        Args:
            tracker: AirdropTracker instance for data access
            roi_optimizer: Optional ROIOptimizer for cost calculations
        """
        self.tracker = tracker
        self.roi_optimizer = roi_optimizer
        self._price_cache: Dict[str, Decimal] = {}
        logger.info("PortfolioPerformanceAnalyzer initialized")

    def calculate_portfolio_metrics(
        self,
        as_of_date: Optional[datetime] = None
    ) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio performance metrics.

        Args:
            as_of_date: Date for calculation (defaults to now)

        Returns:
            PortfolioMetrics with complete performance analysis

        Example:
            >>> analyzer = PortfolioPerformanceAnalyzer(tracker)
            >>> metrics = analyzer.calculate_portfolio_metrics()
            >>> print(f"Total value: ${metrics.total_portfolio_value_usd}")
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.now()

            # Get all airdrop events up to the specified date
            start_date = datetime(2020, 1, 1)  # Far back start date
            events = self.tracker.get_airdrops_by_date_range(start_date, as_of_date)

            if not events:
                logger.warning("No airdrop events found for portfolio analysis")
                return self._create_empty_metrics(as_of_date)

            # Calculate total portfolio value
            total_value = self._calculate_total_portfolio_value(events)

            # Calculate costs using ROI optimizer if available
            total_cost = self._calculate_total_costs(events)

            # Calculate profit/loss and ROI
            profit_loss = total_value - total_cost
            roi_percentage = (
                (profit_loss / total_cost * 100) if total_cost > 0 else Decimal('0')
            )

            # Calculate diversification metrics
            protocol_allocations = self._calculate_protocol_allocations(events)
            token_allocations = self._calculate_token_allocations(events)

            diversification_index = self._calculate_diversification_index(
                protocol_allocations
            )
            largest_position_pct = self._calculate_largest_position_percentage(
                protocol_allocations, total_value
            )

            # Calculate Value at Risk (simplified)
            var_usd = self._calculate_value_at_risk(total_value, diversification_index)

            metrics = PortfolioMetrics(
                calculation_date=as_of_date,
                total_portfolio_value_usd=total_value,
                total_profit_loss_usd=profit_loss,
                total_cost_usd=total_cost,
                portfolio_roi_percentage=roi_percentage,
                protocol_count=len(protocol_allocations),
                token_count=len(token_allocations),
                diversification_index=diversification_index,
                largest_position_percentage=largest_position_pct,
                value_at_risk_usd=var_usd
            )

            logger.info(
                f"Portfolio metrics calculated: ${total_value} value, "
                f"{roi_percentage:.1f}% ROI"
            )
            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            raise RuntimeError(f"Portfolio metrics calculation failed: {e}") from e

    def calculate_portfolio_value_over_time(
        self,
        start_date: datetime,
        end_date: datetime,
        interval_days: int = 30
    ) -> List[PortfolioSnapshot]:
        """
        Calculate portfolio value progression over time.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            interval_days: Days between snapshots

        Returns:
            List of PortfolioSnapshot instances showing value over time

        Example:
            >>> start = datetime(2024, 1, 1)
            >>> end = datetime(2024, 12, 31)
            >>> snapshots = analyzer.calculate_portfolio_value_over_time(start, end)
        """
        try:
            snapshots = []
            current_date = start_date

            while current_date <= end_date:
                # Get events up to current date
                events = self.tracker.get_airdrops_by_date_range(
                    datetime(2020, 1, 1), current_date
                )

                if events:
                    total_value = self._calculate_total_portfolio_value(events)
                    protocol_allocations = self._calculate_protocol_allocations(events)
                    token_allocations = self._calculate_token_allocations(events)
                    diversification_score = self._calculate_diversification_index(
                        protocol_allocations
                    )

                    snapshot = PortfolioSnapshot(
                        snapshot_date=current_date,
                        total_value_usd=total_value,
                        protocol_allocations=protocol_allocations,
                        token_allocations=token_allocations,
                        diversification_score=diversification_score
                    )
                    snapshots.append(snapshot)

                current_date += timedelta(days=interval_days)

            logger.info(f"Generated {len(snapshots)} portfolio snapshots")
            return snapshots

        except Exception as e:
            logger.error(f"Failed to calculate portfolio value over time: {e}")
            raise RuntimeError(
                f"Portfolio value over time calculation failed: {e}"
            ) from e

    def compare_to_benchmark(
        self,
        benchmark_type: BenchmarkType,
        comparison_period_days: int = 365
    ) -> BenchmarkComparison:
        """
        Compare portfolio performance to a benchmark.

        Args:
            benchmark_type: Type of benchmark for comparison
            comparison_period_days: Period for comparison in days

        Returns:
            BenchmarkComparison with performance analysis

        Example:
            >>> comparison = analyzer.compare_to_benchmark(BenchmarkType.ETH, 365)
            >>> print(f"Alpha: {comparison.alpha_percentage}%")
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=comparison_period_days)

            # Calculate portfolio return
            portfolio_return = self._calculate_portfolio_return(start_date, end_date)

            # Get benchmark return (stub implementation)
            benchmark_return = self._get_benchmark_return(
                benchmark_type, start_date, end_date
            )

            # Calculate alpha (excess return)
            alpha = portfolio_return - benchmark_return

            comparison = BenchmarkComparison(
                benchmark_type=benchmark_type,
                portfolio_return_percentage=portfolio_return,
                benchmark_return_percentage=benchmark_return,
                alpha_percentage=alpha,
                comparison_period_days=comparison_period_days,
                calculation_date=end_date
            )

            logger.info(
                f"Benchmark comparison: Portfolio {portfolio_return:.1f}% vs "
                f"{benchmark_type.value} {benchmark_return:.1f}% "
                f"(Alpha: {alpha:.1f}%)"
            )
            return comparison

        except Exception as e:
            logger.error(f"Failed to compare to benchmark: {e}")
            raise RuntimeError(f"Benchmark comparison failed: {e}") from e

    def _calculate_total_portfolio_value(self, events: List[Any]) -> Decimal:
        """Calculate total current portfolio value from events."""
        total_value = Decimal('0')
        for event in events:
            if event.estimated_value_usd:
                # Use current estimated value (in real implementation,
                # this would use current market prices)
                total_value += event.estimated_value_usd
        return total_value

    def _calculate_total_costs(self, events: List[Any]) -> Decimal:
        """Calculate total costs using ROI optimizer or default estimates."""
        if self.roi_optimizer:
            try:
                # Use ROI optimizer for accurate cost calculation
                portfolio_roi = self.roi_optimizer.calculate_portfolio_roi()
                return Decimal(str(sum(roi.total_cost_usd for roi in portfolio_roi)))
            except Exception as e:
                logger.warning(f"ROI optimizer cost calculation failed: {e}")

        # Fallback: estimate costs based on transaction count
        default_gas_cost = Decimal('5.0')  # $5 per transaction estimate
        return Decimal(str(len(events))) * default_gas_cost

    def _calculate_protocol_allocations(self, events: List[Any]) -> Dict[str, Decimal]:
        """Calculate value allocation by protocol."""
        allocations: Dict[str, Decimal] = {}
        for event in events:
            protocol = event.protocol_name
            value = event.estimated_value_usd or Decimal('0')
            allocations[protocol] = allocations.get(protocol, Decimal('0')) + value
        return allocations

    def _calculate_token_allocations(self, events: List[Any]) -> Dict[str, Decimal]:
        """Calculate value allocation by token."""
        allocations: Dict[str, Decimal] = {}
        for event in events:
            token = event.token_symbol
            value = event.estimated_value_usd or Decimal('0')
            allocations[token] = allocations.get(token, Decimal('0')) + value
        return allocations

    def _calculate_diversification_index(
        self, allocations: Dict[str, Decimal]
    ) -> Decimal:
        """Calculate Herfindahl-Hirschman Index for diversification."""
        if not allocations:
            return Decimal('0')

        total_value = sum(allocations.values())
        if total_value == 0:
            return Decimal('0')

        # Calculate HHI (sum of squared market shares)
        hhi = sum(
            (value / total_value) ** 2 for value in allocations.values()
        )

        # Convert to diversification index (1 - HHI, normalized)
        # Higher values indicate better diversification
        diversification_index = Decimal('1') - hhi
        return max(Decimal('0'), min(Decimal('1'), diversification_index))

    def _calculate_largest_position_percentage(
        self, allocations: Dict[str, Decimal], total_value: Decimal
    ) -> Decimal:
        """Calculate percentage of largest single position."""
        if not allocations or total_value == 0:
            return Decimal('0')

        largest_position = max(allocations.values())
        return (largest_position / total_value) * 100

    def _calculate_value_at_risk(
        self, total_value: Decimal, diversification_index: Decimal
    ) -> Decimal:
        """Calculate simplified Value at Risk estimate."""
        # Simplified VaR calculation based on diversification
        # In practice, this would use historical volatility and correlations
        base_risk_percentage = Decimal('0.20')  # 20% base risk
        # Up to 10% reduction based on diversification
        diversification_adjustment = diversification_index * Decimal('0.10')
        risk_percentage = base_risk_percentage - diversification_adjustment

        return total_value * risk_percentage

    def _calculate_portfolio_return(
        self, start_date: datetime, end_date: datetime
    ) -> Decimal:
        """Calculate portfolio return over specified period."""
        # Get portfolio values at start and end dates
        start_events = self.tracker.get_airdrops_by_date_range(
            datetime(2020, 1, 1), start_date
        )
        end_events = self.tracker.get_airdrops_by_date_range(
            datetime(2020, 1, 1), end_date
        )

        start_value = self._calculate_total_portfolio_value(start_events)
        end_value = self._calculate_total_portfolio_value(end_events)

        if start_value == 0:
            return Decimal('0')

        return ((end_value - start_value) / start_value) * 100

    def _get_benchmark_return(
        self,
        benchmark_type: BenchmarkType,
        start_date: datetime,
        end_date: datetime
    ) -> Decimal:
        """Get benchmark return for comparison (stub implementation)."""
        # Stub implementation - in practice, this would fetch real market data
        benchmark_returns = {
            BenchmarkType.ETH: Decimal('15.0'),      # 15% annual return
            BenchmarkType.BTC: Decimal('25.0'),      # 25% annual return
            BenchmarkType.MARKET_INDEX: Decimal('10.0')  # 10% annual return
        }

        # Adjust for actual time period
        days = (end_date - start_date).days
        annual_return = benchmark_returns.get(benchmark_type, Decimal('10.0'))
        return annual_return * (Decimal(str(days)) / Decimal('365'))

    def _create_empty_metrics(self, as_of_date: datetime) -> PortfolioMetrics:
        """Create empty metrics when no data is available."""
        return PortfolioMetrics(
            calculation_date=as_of_date,
            total_portfolio_value_usd=Decimal('0'),
            total_profit_loss_usd=Decimal('0'),
            total_cost_usd=Decimal('0'),
            portfolio_roi_percentage=Decimal('0'),
            protocol_count=0,
            token_count=0,
            diversification_index=Decimal('0'),
            largest_position_percentage=Decimal('0'),
            value_at_risk_usd=Decimal('0')
        )
