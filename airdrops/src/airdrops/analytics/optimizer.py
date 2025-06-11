"""
ROI Analysis and Optimization Module.

This module provides functionality to calculate Return on Investment (ROI) for airdrop
activities and generate optimization suggestions based on performance analysis.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from airdrops.analytics.tracker import AirdropTracker

# Configure logging
logger = logging.getLogger(__name__)


class CostModel(Enum):
    """Supported cost calculation models."""
    SIMPLE_GAS = "simple_gas"
    MANUAL_INPUT = "manual_input"
    ESTIMATED = "estimated"


class OptimizationStrategy(Enum):
    """Optimization strategy types."""
    ROI_MAXIMIZATION = "roi_maximization"
    RISK_ADJUSTED = "risk_adjusted"
    DIVERSIFIED = "diversified"


class CostData(BaseModel):
    """Cost data for ROI calculations."""
    protocol_name: str = Field(..., min_length=1, max_length=100)
    total_gas_cost_usd: Optional[Decimal] = Field(None, ge=0)
    transaction_count: int = Field(0, ge=0)
    average_gas_cost_usd: Optional[Decimal] = Field(None, ge=0)
    manual_cost_usd: Optional[Decimal] = Field(None, ge=0)
    time_investment_hours: Optional[Decimal] = Field(None, ge=0)


class ROIMetrics(BaseModel):
    """ROI calculation results for a protocol."""
    protocol_name: str
    total_revenue_usd: Decimal
    total_cost_usd: Decimal
    roi_percentage: Decimal
    profit_usd: Decimal
    transaction_count: int
    revenue_per_transaction: Decimal
    cost_per_transaction: Decimal
    calculation_date: datetime


class OptimizationSuggestion(BaseModel):
    """Optimization suggestion for improving ROI."""
    protocol_name: str
    suggestion_type: str
    priority: str  # "high", "medium", "low"
    description: str
    expected_impact: str
    current_roi: Decimal
    potential_roi: Optional[Decimal] = None


class ROIOptimizer:
    """
    ROI analysis and optimization system for airdrop activities.

    Calculates Return on Investment metrics and provides optimization suggestions
    based on historical performance data and cost analysis.

    Example:
        >>> tracker = AirdropTracker()
        >>> optimizer = ROIOptimizer(tracker)
        >>> roi_metrics = optimizer.calculate_protocol_roi("Uniswap")
        >>> suggestions = optimizer.generate_optimization_suggestions()
    """

    def __init__(
        self,
        tracker: AirdropTracker,
        default_gas_cost_usd: Decimal = Decimal("5.0"),
        cost_model: CostModel = CostModel.SIMPLE_GAS
    ) -> None:
        """
        Initialize the ROI optimizer.

        Args:
            tracker: AirdropTracker instance for data access
            default_gas_cost_usd: Default gas cost per transaction in USD
            cost_model: Cost calculation model to use
        """
        self.tracker = tracker
        self.default_gas_cost_usd = default_gas_cost_usd
        self.cost_model = cost_model
        self._cost_data_cache: Dict[str, CostData] = {}
        logger.info(f"ROIOptimizer initialized with cost model: {cost_model.value}")

    def set_protocol_cost_data(self, cost_data: CostData) -> None:
        """
        Set cost data for a specific protocol.

        Args:
            cost_data: Cost data for the protocol

        Example:
            >>> cost_data = CostData(
            ...     protocol_name="Uniswap",
            ...     total_gas_cost_usd=Decimal("150.0"),
            ...     transaction_count=30
            ... )
            >>> optimizer.set_protocol_cost_data(cost_data)
        """
        self._cost_data_cache[cost_data.protocol_name] = cost_data
        logger.debug(f"Set cost data for protocol: {cost_data.protocol_name}")

    def calculate_protocol_roi(
        self,
        protocol_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ROIMetrics:
        """
        Calculate ROI metrics for a specific protocol.

        Args:
            protocol_name: Name of the protocol to analyze
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            ROI metrics for the protocol

        Raises:
            ValueError: If no airdrop events found for the protocol
            RuntimeError: If ROI calculation fails

        Example:
            >>> roi = optimizer.calculate_protocol_roi("Uniswap")
            >>> print(f"ROI: {roi.roi_percentage}%")
        """
        try:
            # Get airdrop events for the protocol
            if start_date and end_date:
                all_events = self.tracker.get_airdrops_by_date_range(start_date,
                                                                     end_date)
                events = [e for e in all_events if e.protocol_name == protocol_name]
            else:
                events = self.tracker.get_airdrops_by_protocol(protocol_name)

            if not events:
                raise ValueError(f"No airdrop events found for protocol: "
                                 f"{protocol_name}")

            # Calculate total revenue
            total_revenue = (
                sum(event.estimated_value_usd or Decimal('0') for event in events)
                if events
                else Decimal('0')
            )

            # Calculate total costs
            total_cost = self._calculate_protocol_costs(protocol_name, len(events))

            # Calculate ROI metrics
            profit = total_revenue - total_cost
            roi_percentage = (
                (profit / total_cost * 100) if total_cost > 0 else Decimal('0')
            )

            revenue_per_tx = (
                total_revenue / len(events) if events else Decimal('0')
            )
            cost_per_tx = (
                total_cost / len(events) if events else Decimal('0')
            )

            roi_metrics = ROIMetrics(
                protocol_name=protocol_name,
                total_revenue_usd=Decimal(str(total_revenue)),
                total_cost_usd=total_cost,
                roi_percentage=roi_percentage,
                profit_usd=profit,
                transaction_count=len(events),
                revenue_per_transaction=Decimal(str(revenue_per_tx)),
                cost_per_transaction=cost_per_tx,
                calculation_date=datetime.now()
            )

            logger.info(
                f"Calculated ROI for {protocol_name}: {roi_percentage:.2f}% "
                f"(Revenue: ${total_revenue}, Cost: ${total_cost})"
            )
            return roi_metrics

        except Exception as e:
            logger.error(f"Failed to calculate ROI for protocol {protocol_name}: {e}")
            raise RuntimeError(f"ROI calculation failed: {e}") from e

    def calculate_portfolio_roi(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ROIMetrics]:
        """
        Calculate ROI metrics for all protocols in the portfolio.

        Args:
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of ROI metrics for all protocols

        Example:
            >>> portfolio_roi = optimizer.calculate_portfolio_roi()
            >>> for roi in portfolio_roi:
            ...     print(f"{roi.protocol_name}: {roi.roi_percentage}%")
        """
        try:
            # Get all events in date range
            if start_date and end_date:
                events = self.tracker.get_airdrops_by_date_range(start_date, end_date)
            else:
                # Get all events by querying a wide date range
                start_date = datetime(2020, 1, 1)
                end_date = datetime.now()
                events = self.tracker.get_airdrops_by_date_range(start_date, end_date)

            # Group events by protocol
            protocols = set(event.protocol_name for event in events)

            # Calculate ROI for each protocol
            portfolio_roi = []
            for protocol in protocols:
                try:
                    roi_metrics = self.calculate_protocol_roi(
                        protocol, start_date, end_date
                    )
                    portfolio_roi.append(roi_metrics)
                except ValueError:
                    # Skip protocols with no events
                    continue

            # Sort by ROI percentage (descending)
            portfolio_roi.sort(key=lambda x: x.roi_percentage, reverse=True)

            logger.info(f"Calculated portfolio ROI for {len(portfolio_roi)} protocols")
            return portfolio_roi

        except Exception as e:
            logger.error(f"Failed to calculate portfolio ROI: {e}")
            raise RuntimeError(f"Portfolio ROI calculation failed: {e}") from e

    def generate_optimization_suggestions(
        self,
        strategy: OptimizationStrategy = OptimizationStrategy.ROI_MAXIMIZATION,
        min_roi_threshold: Decimal = Decimal("50.0")
    ) -> List[OptimizationSuggestion]:
        """
        Generate optimization suggestions based on ROI analysis.

        Args:
            strategy: Optimization strategy to use
            min_roi_threshold: Minimum ROI threshold for recommendations

        Returns:
            List of optimization suggestions

        Example:
            >>> suggestions = optimizer.generate_optimization_suggestions()
            >>> for suggestion in suggestions:
            ...     print(f"{suggestion.protocol_name}: {suggestion.description}")
        """
        try:
            portfolio_roi = self.calculate_portfolio_roi()
            suggestions = []

            if strategy == OptimizationStrategy.ROI_MAXIMIZATION:
                suggestions.extend(
                    self._generate_roi_maximization_suggestions(
                        portfolio_roi, min_roi_threshold
                    ) or []
                )
            elif strategy == OptimizationStrategy.RISK_ADJUSTED:
                suggestions.extend(
                    self._generate_risk_adjusted_suggestions(portfolio_roi) or []
                )
            elif strategy == OptimizationStrategy.DIVERSIFIED:
                suggestions.extend(
                    self._generate_diversification_suggestions(portfolio_roi) or []
                )

            # Sort by priority and potential impact
            priority_order = {"high": 0, "medium": 1, "low": 2}
            suggestions.sort(key=lambda x: priority_order.get(x.priority, 3))

            logger.info(f"Generated {len(suggestions)} optimization suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate optimization suggestions: {e}")
            raise RuntimeError(f"Optimization suggestion generation failed: {e}") from e

    def _calculate_protocol_costs(
        self, protocol_name: str, transaction_count: int
    ) -> Decimal:
        """Calculate total costs for a protocol based on the cost model."""
        if protocol_name in self._cost_data_cache:
            cost_data = self._cost_data_cache[protocol_name]

            if (self.cost_model == CostModel.MANUAL_INPUT and
                    cost_data.manual_cost_usd):
                return cost_data.manual_cost_usd
            elif cost_data.total_gas_cost_usd:
                return cost_data.total_gas_cost_usd
            elif cost_data.average_gas_cost_usd:
                return cost_data.average_gas_cost_usd * transaction_count

        # Fallback to default gas cost estimation
        return self.default_gas_cost_usd * transaction_count

    def _generate_roi_maximization_suggestions(
        self, portfolio_roi: List[ROIMetrics], min_threshold: Decimal
    ) -> List[OptimizationSuggestion]:
        """Generate suggestions focused on maximizing ROI."""
        suggestions = []

        # Identify high-performing protocols
        high_performers = [roi for roi in portfolio_roi
                           if roi.roi_percentage > min_threshold]
        low_performers = [roi for roi in portfolio_roi
                          if roi.roi_percentage < min_threshold]

        # Suggest focusing on high-performing protocols
        if high_performers:
            top_performer = high_performers[0]
            suggestions.append(
                OptimizationSuggestion(
                    protocol_name=top_performer.protocol_name,
                    suggestion_type="focus_allocation",
                    priority="high",
                    description=(f"Increase allocation to {top_performer.protocol_name} "  # noqa: E501
                                 f"(current ROI: {top_performer.roi_percentage:.1f}%)"),  # noqa: E501
                    expected_impact="High potential for increased returns",
                    current_roi=top_performer.roi_percentage,
                )
            )

        # Suggest reducing or eliminating low-performing protocols
        for roi in low_performers[:3]:  # Top 3 worst performers
            suggestions.append(
                OptimizationSuggestion(
                    protocol_name=roi.protocol_name,
                    suggestion_type="reduce_allocation",
                    priority="medium",
                    description=(f"Consider reducing allocation to {roi.protocol_name} "  # noqa: E501
                                 f"(current ROI: {roi.roi_percentage:.1f}%)"),  # noqa: E501
                    expected_impact="Reduce capital exposure to underperforming assets",
                    current_roi=roi.roi_percentage,
                )
            )

        return suggestions

    def _generate_risk_adjusted_suggestions(
        self, portfolio_roi: List[ROIMetrics]
    ) -> List[OptimizationSuggestion]:
        """Generate suggestions focused on risk-adjusted returns."""
        suggestions: List[OptimizationSuggestion] = []

        # Calculate portfolio metrics
        if not portfolio_roi:
            return suggestions

        avg_roi = (sum(roi.roi_percentage for roi in portfolio_roi) /
                   len(portfolio_roi))

        # Suggest protocols with consistent performance
        consistent_performers = [
            roi for roi in portfolio_roi
            if roi.roi_percentage > avg_roi and roi.transaction_count >= 5
        ]

        for roi in consistent_performers[:2]:
            suggestions.append(
                OptimizationSuggestion(
                    protocol_name=roi.protocol_name,
                    suggestion_type="stable_allocation",
                    priority="medium",
                    description=(f"Maintain or increase allocation to {roi.protocol_name} "  # noqa: E501
                                 f"for consistent returns ({roi.roi_percentage:.1f}% ROI, "  # noqa: E501
                                 f"{roi.transaction_count} transactions)"),  # noqa: E501
                    expected_impact="Stable returns with proven track record",
                    current_roi=roi.roi_percentage,
                )
            )

        return suggestions

    def _generate_diversification_suggestions(
        self, portfolio_roi: List[ROIMetrics]
    ) -> List[OptimizationSuggestion]:
        """Generate suggestions focused on portfolio diversification."""
        suggestions = []

        if len(portfolio_roi) < 3:
            suggestions.append(
                OptimizationSuggestion(
                    protocol_name="Portfolio",
                    suggestion_type="diversification",
                    priority="high",
                    description=("Consider diversifying across more protocols to reduce risk"),  # noqa: E501
                    expected_impact="Reduced portfolio volatility and risk",
                    current_roi=Decimal('0'),
                )
            )

        # Check for over-concentration
        if portfolio_roi:
            total_transactions = sum(roi.transaction_count for roi in portfolio_roi)
            if total_transactions > 0:
                for roi in portfolio_roi:
                    concentration = (roi.transaction_count / total_transactions) * 100
                    if concentration > 50:  # More than 50% concentration
                        suggestions.append(
                            OptimizationSuggestion(
                                protocol_name=roi.protocol_name,
                                suggestion_type="reduce_concentration",
                                priority="medium",
                                description=(
                                    f"Reduce concentration in "
                                    f"{roi.protocol_name} "
                                    f"({concentration:.1f}% of transactions)"
                                ),
                                expected_impact="Better risk distribution",
                                current_roi=roi.roi_percentage,
                            )
                        )

        return suggestions

    def optimize_protocol_strategy(
        self, protocol_name: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize the strategy for a specific protocol based on its performance metrics.
        This is a placeholder for a more sophisticated optimization algorithm.
        """
        logger.info(f"Optimizing strategy for protocol: {protocol_name}")
        
        # Dummy optimization logic
        if metrics.get("success_rate", 0) < 0.8:
            return {
                "recommended_actions": ["review_gas_settings", "check_slippage"],
                "expected_improvement": Decimal("0.10"),
                "reason": "Low success rate",
            }
        elif metrics.get("average_gas_used", 0) > 200000:
            return {
                "recommended_actions": [
                    "optimize_gas_limits", "explore_alternative_routes"
                ],
                "expected_improvement": Decimal("0.05"),
                "reason": "High gas usage",
            }
        else:
            return {
                "recommended_actions": ["continue_monitoring"],
                "expected_improvement": Decimal("0.00"),
                "reason": "Performance is satisfactory",
            }

    def optimize_gas_usage(self, metrics_collector: Any) -> Dict[str, Any]:
        """
        Optimize gas usage based on historical transaction data.
        This is a placeholder for a more advanced gas optimization logic.
        """
        logger.info("Optimizing gas usage...")
        
        # Dummy gas optimization
        return {
            "optimal_gas_price": 30,  # gwei
            "best_times": ["02:00 UTC", "14:00 UTC"],
            "estimated_savings": Decimal("50.0"),  # USD per day
        }

    def optimize_swap_routes(self, swap_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize swap routes for better execution prices or lower slippage.
        This is a placeholder for a more complex routing algorithm.
        """
        logger.info(
            f"Optimizing swap routes for {swap_params.get('token_in')} to "
            f"{swap_params.get('token_out')}"
        )
        
        # Dummy route optimization
        return {
            "best_route": ["protocol_A", "protocol_B"],
            "expected_output": Decimal("0.99"),  # e.g., 0.99 WETH for 1 USDC
            "price_impact": Decimal("0.001"),  # 0.1% price impact
        }
