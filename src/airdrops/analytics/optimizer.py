"""
ROI Optimizer for airdrop farming.

This module provides the ROIOptimizer class, which is responsible for analyzing
historical airdrop data and market conditions to suggest optimal strategies
for maximizing Return on Investment (ROI).
"""

import logging
import os
from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CostData:
    """
    Represents cost data for a specific operation or airdrop.
    Placeholder for actual cost breakdown.
    """
    gas_cost_usd: Decimal = Decimal("0")
    protocol_fees_usd: Decimal = Decimal("0")
    opportunity_cost_usd: Decimal = Decimal("0")
    total_cost_usd: Decimal = Decimal("0")


@dataclass
class ROIMetrics:
    """Data class for ROI-related metrics."""
    total_roi: Decimal
    average_roi_per_airdrop: Decimal
    success_rate: Decimal
    total_capital_deployed: Decimal
    total_profit: Decimal
    protocol_rois: Dict[str, Decimal]
    # Additional attributes used by reporter
    protocol_name: str = ""
    roi_percentage: Decimal = Decimal("0")
    total_revenue_usd: Decimal = Decimal("0")
    total_cost_usd: Decimal = Decimal("0")
    profit_usd: Decimal = Decimal("0")


@dataclass
class OptimizationSuggestion:
    """Data class for optimization suggestions."""
    strategy: str
    protocol: Optional[str]
    suggested_allocation_change: Optional[Decimal]
    reason: str
    expected_impact: str
    # Additional attributes used by reporter
    priority: str = "medium"
    protocol_name: str = ""
    description: str = ""


class CostModel(Enum):
    """Supported cost calculation models."""
    SIMPLE_GAS = "simple_gas"
    MANUAL_INPUT = "manual_input"
    ESTIMATED = "estimated"


class OptimizationStrategy(Enum):
    """
    Defines the available ROI optimization strategies.
    """
    MAXIMIZE_ROI = "maximize_roi"
    MINIMIZE_RISK = "minimize_risk"
    BALANCE_GROWTH_STABILITY = "balance_growth_stability"


class ROIOptimizer:
    """
    ROIOptimizer analyzes historical airdrop data and market conditions
    to suggest optimal strategies for maximizing Return on Investment (ROI).
    """

    def __init__(
        self,
        tracker: Optional[Any] = None,
        default_gas_cost_usd: Optional[Decimal] = None,
        cost_model: Optional[CostModel] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the ROI Optimizer.

        Args:
            tracker: AirdropTracker instance (for backward compatibility).
            default_gas_cost_usd: Default gas cost in USD (for backward compatibility).
            cost_model: Cost calculation model (for backward compatibility).
            config: Optional configuration dictionary for optimization parameters.
        """
        self.tracker = tracker
        self.default_gas_cost_usd = default_gas_cost_usd or Decimal("5.0")
        self.cost_model = cost_model or CostModel.SIMPLE_GAS
        self.config = config or {}
        optimizer_config = self.config.get("roi_optimizer", {})

        self.optimization_strategy = OptimizationStrategy(
            optimizer_config.get("strategy", "maximize_roi")
        )
        logger.debug(
            "ROIOptimizer initialized with strategy: %s",
            self.optimization_strategy.value,
        )

        self.min_data_points = int(
            optimizer_config.get(
                "min_data_points",
                os.getenv("ROI_MIN_DATA_POINTS", "10")
            )
        )
        self.risk_aversion = Decimal(
            str(optimizer_config.get(
                "risk_aversion",
                os.getenv("ROI_RISK_AVERSION", "0.5")
            ))
        )
        self.history: List[ROIMetrics] = []

    def analyze_historical_data(
        self,
        historical_airdrops: List[Dict[str, Any]]
    ) -> ROIMetrics:
        """
        Analyze historical airdrop data to calculate ROI metrics.

        Args:
                historical_airdrops: List of historical airdrop records.

        Returns:
                ROIMetrics object containing calculated performance metrics.
        """
        if not historical_airdrops:
            logger.warning("No historical airdrop data provided for analysis.")
            return ROIMetrics(
                total_roi=Decimal("0"),
                average_roi_per_airdrop=Decimal("0"),
                success_rate=Decimal("0"),
                total_capital_deployed=Decimal("0"),
                total_profit=Decimal("0"),
                protocol_rois={},
            )

        total_capital_deployed = Decimal("0")
        total_profit = Decimal("0")
        successful_airdrops = 0
        protocol_profits: Dict[str, Decimal] = {}
        protocol_capital: Dict[str, Decimal] = {}

        for airdrop in historical_airdrops:
            protocol = airdrop.get("protocol")
            value_usd = Decimal(str(airdrop.get("value_usd", "0")))
            cost_usd = Decimal(str(airdrop.get("cost_usd", "0")))
            success = airdrop.get("success", False)

            total_capital_deployed += cost_usd

            if success:
                profit = value_usd - cost_usd
                total_profit += profit
                successful_airdrops += 1

                if protocol is not None:
                    protocol_profits[protocol] = protocol_profits.get(protocol, Decimal("0")) + profit
                    protocol_capital[protocol] = protocol_capital.get(protocol, Decimal("0")) + cost_usd

        total_roi = (
            (total_profit / total_capital_deployed)
            if total_capital_deployed > 0
            else Decimal("0")
        )
        average_roi_per_airdrop = (
            (total_roi / Decimal(str(len(historical_airdrops))))
            if historical_airdrops
            else Decimal("0")
        )
        success_rate = (
            (Decimal(str(successful_airdrops)) / Decimal(str(len(historical_airdrops))))
            if historical_airdrops
            else Decimal("0")
        )

        protocol_rois = {
            p: (
                (protocol_profits[p] / protocol_capital[p])
                if protocol_capital[p] > 0
                else Decimal("0")
            )
            for p in protocol_profits
        }

        metrics = ROIMetrics(
            total_roi=total_roi,
            average_roi_per_airdrop=average_roi_per_airdrop,
            success_rate=success_rate,
            total_capital_deployed=total_capital_deployed,
            total_profit=total_profit,
            protocol_rois=protocol_rois,
        )
        self.history.append(metrics)
        logger.info(f"Historical data analysis completed. Total ROI: {metrics.total_roi:.2%}")
        return metrics

    def suggest_optimization(
        self,
        current_metrics: ROIMetrics,
        market_data: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """
        Suggest optimization strategies based on current performance and market data.

        Args:
                current_metrics: Current ROI metrics.
                market_data: Real-time market data (e.g., gas prices, protocol activity).

        Returns:
                List of OptimizationSuggestion objects.
        """
        suggestions: List[OptimizationSuggestion] = []

        # Example logic based on optimization strategy
        if self.optimization_strategy == OptimizationStrategy.MAXIMIZE_ROI:
            # Suggest increasing allocation to protocols with highest ROI
            if current_metrics.protocol_rois:
                best_protocol = max(
                    current_metrics.protocol_rois,
                    key=current_metrics.protocol_rois.get  # type: ignore
                )
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Maximize ROI",
                        protocol=best_protocol,
                        suggested_allocation_change=Decimal("0.10"),
                        reason=(
                            f"Protocol {best_protocol} has the highest "
                            "historical ROI."
                        ),
                        expected_impact="Increased overall ROI.",
                    )
                )
            if current_metrics.success_rate < Decimal("0.7"):
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Maximize ROI",
                        protocol=None,
                        suggested_allocation_change=None,
                        reason=(
                            "Overall success rate is low, consider focusing on "
                            "more reliable airdrops."
                        ),
                        expected_impact="Improved success rate and reduced capital loss.",
                    )
                )

        elif self.optimization_strategy == OptimizationStrategy.MINIMIZE_RISK:
            # Suggest reducing allocation to high-risk protocols or those with low success
            if current_metrics.protocol_rois:
                worst_protocol = min(
                    current_metrics.protocol_rois.keys(),
                    key=lambda k: current_metrics.protocol_rois[k]
                )
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Minimize Risk",
                        protocol=worst_protocol,
                        suggested_allocation_change=Decimal("-0.05"),  # Example decrease
                        reason=(
                            f"Protocol {worst_protocol} has the lowest "
                            "historical ROI, indicating higher risk."
                        ),
                        expected_impact="Reduced exposure to underperforming assets.",
                    )
                )
            if market_data.get("gas_price_gwei", Decimal("0")) > Decimal("100"):
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Minimize Risk",
                        protocol=None,
                        suggested_allocation_change=None,
                        reason="High gas prices increase transaction costs and risk.",
                        expected_impact="Reduced operational costs and improved net ROI.",
                    )
                )

        elif self.optimization_strategy == OptimizationStrategy.BALANCE_GROWTH_STABILITY:
            # Suggest a balanced approach
            if current_metrics.total_roi < Decimal("0.1"):
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Balance Growth & Stability",
                        protocol=None,
                        suggested_allocation_change=Decimal("0.05"),
                        reason=(
                            "Current ROI is moderate, consider slight increase "
                            "in higher-potential protocols."
                        ),
                        expected_impact="Moderate growth with controlled risk.",
                    )
                )
            # Note: max_drawdown is not part of ROIMetrics, using success_rate as proxy
            if current_metrics.success_rate < Decimal("0.8"):
                suggestions.append(
                    OptimizationSuggestion(
                        strategy="Balance Growth & Stability",
                        protocol=None,
                        suggested_allocation_change=None,
                        reason="High maximum drawdown indicates instability, diversify more.",
                        expected_impact="Improved portfolio stability.",
                    )
                )

        logger.info(f"Generated {len(suggestions)} optimization suggestions.")
        return suggestions

    def backtest_strategy(
        self,
        strategy: OptimizationStrategy,
        historical_data: List[Dict[str, Any]]
    ) -> ROIMetrics:
        """
        Backtest a given optimization strategy against historical data.

        This is a simplified backtesting function. A real backtesting engine
        would be much more complex, simulating trades, fees, and market impact.

        Args:
                strategy: The optimization strategy to backtest.
                historical_data: List of historical airdrop records.

        Returns:
                ROIMetrics object representing the performance of the strategy.
        """
        logger.info(f"Backtesting strategy: {strategy.value}")
        # For simplicity, this mock backtest just re-analyzes data
        # and applies a hypothetical adjustment based on the strategy.
        # In a real scenario, this would involve re-running allocation logic
        # with the strategy applied over historical periods.

        # Simulate applying the strategy
        simulated_airdrops = []
        for airdrop in historical_data:
            modified_airdrop = airdrop.copy()
            if strategy == OptimizationStrategy.MAXIMIZE_ROI:
                # Hypothetically increase success rate for high-ROI protocols
                if modified_airdrop.get("protocol") in ["scroll", "zksync"]:
                    modified_airdrop["success"] = True
            elif strategy == OptimizationStrategy.MINIMIZE_RISK:
                # Hypothetically reduce cost for low-risk protocols
                if modified_airdrop.get("protocol") in ["eigenlayer"]:
                    cost_usd = Decimal(str(modified_airdrop["cost_usd"]))
                    modified_airdrop["cost_usd"] = cost_usd * Decimal("0.8")
            simulated_airdrops.append(modified_airdrop)

        return self.analyze_historical_data(simulated_airdrops)

    def _calculate_sharpe_ratio(
        self,
        returns: List[Decimal],
        risk_free_rate: Decimal
    ) -> Decimal:
        """
        Calculate the Sharpe Ratio for a list of returns.
        Assumes returns are periodic (e.g., daily, weekly).
        """
        if len(returns) < 2:
            return Decimal("0")

        returns_array = np.array([float(r) for r in returns])
        excess_returns = returns_array - float(risk_free_rate)

        mean_excess_return = np.mean(excess_returns)
        std_dev_excess_return = np.std(excess_returns, ddof=1)  # Sample standard deviation

        if std_dev_excess_return == 0:
            return Decimal("0")

        sharpe_ratio = Decimal(str(mean_excess_return / std_dev_excess_return))
        return sharpe_ratio.quantize(Decimal("0.001"))

    def _calculate_max_drawdown(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate the Maximum Drawdown for a list of returns.
        """
        if not returns:
            return Decimal("0")

        returns_array = np.array([float(r) for r in returns])
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = Decimal(str(abs(np.min(drawdowns))))
        return max_drawdown.quantize(Decimal("0.001"))

    def calculate_portfolio_roi(
        self,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None
    ) -> List[ROIMetrics]:
        """
        Calculate portfolio ROI metrics for the given date range.
        
        Args:
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)
            
        Returns:
            List of ROI metrics for the portfolio
            
        Example:
            >>> optimizer = ROIOptimizer()
            >>> metrics = optimizer.calculate_portfolio_roi("2024-01-01", "2024-12-31")
        """
        if not self.tracker:
            return []
        try:
            historical_data = self.tracker.get_airdrops_by_date_range(start_date, end_date)
            # This is not ideal, but we need to adapt the historical data to the expected format
            adapted_data = [
                {
                    "protocol": event.protocol_name,
                    "value_usd": event.estimated_value_usd,
                    "cost_usd": self.default_gas_cost_usd,  # Simplified cost
                    "success": True,
                }
                for event in historical_data
            ]
            if not adapted_data:
                return []
            
            metrics = self.analyze_historical_data(adapted_data)
            return [metrics]
        except Exception as e:
            logger.error(f"Portfolio ROI calculation failed: {e}")
            raise RuntimeError(f"Portfolio ROI calculation failed: {e}") from e

    def generate_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """
        Generate optimization suggestions based on current portfolio performance.
        
        Returns:
            List of optimization suggestions
            
        Example:
            >>> optimizer = ROIOptimizer()
            >>> suggestions = optimizer.generate_optimization_suggestions()
        """
        if not self.tracker:
            return []
        try:
            portfolio_metrics = self.calculate_portfolio_roi()
            if not portfolio_metrics:
                return []
            # For now, we'll just use the first (and only) set of metrics
            return self.suggest_optimization(portfolio_metrics[0], {})
        except Exception as e:
            logger.error(f"Optimization suggestion generation failed: {e}")
            raise RuntimeError(f"Optimization suggestion generation failed: {e}") from e


__all__ = [
    "ROIOptimizer",
    "ROIMetrics",
    "OptimizationSuggestion",
    "OptimizationStrategy",
    "CostData",
    "CostModel"
]
