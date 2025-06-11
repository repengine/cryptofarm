"""
Capital Allocation Engine implementation.

This module provides the main CapitalAllocator class that handles portfolio
optimization, risk-adjusted capital allocation, and rebalancing for automated
airdrop farming activities.
"""

import logging
import os
from decimal import Decimal
import pendulum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import numpy as np


# Configure logging
logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    """Allocation strategy enumeration."""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"
    KELLY_CRITERION = "kelly_criterion"


@dataclass
class AllocationTarget:
    """Data class for allocation targets."""
    protocol: str
    target_percentage: Decimal
    current_percentage: Decimal
    risk_score: Decimal
    expected_return: Decimal


@dataclass
class PortfolioMetrics:
    """Data class for portfolio performance metrics."""
    total_value: Decimal
    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    capital_utilization: Decimal
    protocol_allocations: Dict[str, Decimal]


@dataclass
class RebalanceOrder:
    """Data class for rebalancing orders."""
    protocol: str
    action: str  # "increase" or "decrease"
    amount: Decimal
    priority: int


class CapitalAllocator:
    """
    Capital Allocation Engine for automated airdrop farming.

    Provides portfolio optimization, risk-adjusted capital allocation, and
    rebalancing capabilities that integrate with the Risk Management System
    to ensure safe and efficient capital deployment.

    Example:
        >>> allocator = CapitalAllocator()
        >>> allocator.initialize()
        >>> portfolio = allocator.optimize_portfolio(protocols, risk_constraints)
        >>> metrics = allocator.calculate_efficiency_metrics()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Capital Allocation Engine.

        Args:
            config: Optional configuration dictionary for allocation parameters.
        """
        from decimal import getcontext
        getcontext().prec = 28

        self.config = config or {}
        capital_config = self.config.get("capital_allocation", {})
        
        self.allocation_strategy = AllocationStrategy(
            capital_config.get("strategy", "equal_weight")
        )
        logger.debug(
            "CapitalAllocator initialized with strategy: %s",
            self.allocation_strategy.value,
        )
        self.risk_free_rate = Decimal(
            str(capital_config.get("risk_free_rate",
                                   os.getenv("CAPITAL_RISK_FREE_RATE", "0.02")))
        )
        self.rebalance_threshold = Decimal(
            str(capital_config.get("rebalance_threshold",
                                   os.getenv("CAPITAL_REBALANCE_THRESHOLD", "0.10")))
        )
        min_alloc_env = "CAPITAL_MIN_PROTOCOL_ALLOCATION"
        self.min_allocation = Decimal(
            str(
                capital_config.get(
                    "min_protocol_allocation", os.getenv(min_alloc_env, "0.01")
                )
            )
        )
        max_alloc_env = "CAPITAL_MAX_PROTOCOL_ALLOCATION"
        self.max_allocation = Decimal(
            str(
                capital_config.get(
                    "max_protocol_allocation", os.getenv(max_alloc_env, "0.50")
                )
            )
        )
        self.max_protocols = int(
            os.getenv("CAPITAL_MAX_PROTOCOLS", "10")
        )
        self.portfolio_history: List[PortfolioMetrics] = []

    def allocate_capital(self, wallets: List[str]) -> Dict[str, Dict[str, Decimal]]:
        """
        Allocate capital across protocols and wallets.
        This is a simplified placeholder.
        """
        logger.info(f"Allocating capital for wallets: {wallets}")
        
        # Dummy allocation for demonstration
        allocations = {}
        for wallet in wallets:
            allocations[wallet] = {
                "scroll": Decimal("0.5"),
                "zksync": Decimal("0.5"),
            }
        return allocations

    def optimize_portfolio(
        self,
        protocols: List[str],
        risk_constraints: Dict[str, Decimal],
        expected_returns: Optional[Dict[str, Decimal]] = None,
        risk_scores: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Decimal]:
        """
        Optimize portfolio allocation across available protocols.

        This method implements portfolio optimization algorithms to determine
        optimal capital allocation based on risk constraints and expected returns.

        Args:
            protocols: List of available protocol names.
            risk_constraints: Dictionary of risk limits per protocol.
            expected_returns: Optional expected returns per protocol.
            risk_scores: Optional risk scores per protocol.

        Returns:
            Dictionary mapping protocol names to allocation percentages.

        Example:
            >>> protocols = ["scroll", "zksync", "eigenlayer"]
            >>> constraints = {"max_protocol_exposure": Decimal("0.20")}
            >>> allocation = allocator.optimize_portfolio(protocols, constraints)
            >>> print(f"Scroll allocation: {allocation['scroll']}%")
        """
        try:
            if not protocols:
                logger.warning("No protocols provided for optimization")
                return {}

            # Validate inputs
            if len(protocols) > self.max_protocols:
                logger.warning(
                    f"Too many protocols ({len(protocols)}), "
                    f"limiting to {self.max_protocols}"
                )
                protocols = protocols[:self.max_protocols]

            # Initialize default values if not provided
            if expected_returns is None:
                expected_returns = {p: Decimal("0.05") for p in protocols}
            if risk_scores is None:
                risk_scores = {p: Decimal("0.5") for p in protocols}

            # Apply allocation strategy
            if self.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT:
                allocation = self._equal_weight_allocation(protocols, risk_constraints)
            elif self.allocation_strategy == AllocationStrategy.RISK_PARITY:
                allocation = self._risk_parity_allocation(
                    protocols, risk_scores, risk_constraints
                )
            elif self.allocation_strategy == AllocationStrategy.MEAN_VARIANCE:
                allocation = self._mean_variance_allocation(
                    protocols, expected_returns, risk_scores, risk_constraints
                )
            else:
                # Default to equal weight
                allocation = self._equal_weight_allocation(protocols, risk_constraints)

            logger.info(f"Portfolio optimization completed: {allocation}")
            return allocation

        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
            raise RuntimeError(f"Failed to optimize portfolio: {e}")

    def allocate_risk_adjusted_capital(
        self,
        total_capital: Decimal,
        portfolio_allocation: Dict[str, Decimal],
        risk_metrics: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """
        Allocate capital with risk adjustments from the Risk Management System.

        This method takes portfolio allocation percentages and adjusts them
        based on real-time risk assessments to ensure compliance with risk limits.

        Args:
            total_capital: Total available capital for allocation.
            portfolio_allocation: Target allocation percentages per protocol.
            risk_metrics: Current risk metrics from Risk Management System.

        Returns:
            Dictionary mapping protocol names to allocated capital amounts.

        Example:
            >>> capital = Decimal("100000")  # $100k
            >>> allocation = {"scroll": Decimal("0.30"), "zksync": Decimal("0.70")}
            >>> risk_data = {"volatility_state": "medium", "gas_price": 50}
            >>> amounts = allocator.allocate_risk_adjusted_capital(
            ...     capital, allocation, risk_data
            ... )
        """
        if total_capital <= 0:
            raise ValueError("Total capital must be positive")

        try:

            # Get risk adjustment factors
            volatility_state = risk_metrics.get("volatility_state", "medium")
            gas_price = risk_metrics.get("gas_price_gwei", Decimal("50"))
            circuit_breaker = risk_metrics.get("circuit_breaker_triggered", False)

            # Calculate risk adjustment multiplier
            risk_multiplier = self._calculate_risk_multiplier(
                volatility_state, gas_price, circuit_breaker
            )

            # Apply risk adjustments to allocations
            adjusted_capital = total_capital * risk_multiplier
            capital_allocations = {}

            for protocol, percentage in portfolio_allocation.items():
                allocated_amount = adjusted_capital * percentage
                capital_allocations[protocol] = allocated_amount

                logger.debug(
                    f"Protocol {protocol}: {percentage:.2%} = "
                    f"${allocated_amount:,.2f}"
                )

            logger.info(
                f"Risk-adjusted capital allocation completed. "
                f"Total allocated: ${sum(capital_allocations.values()):,.2f} "
                f"(Risk multiplier: {risk_multiplier:.2f})"
            )

            return capital_allocations

        except Exception as e:
            logger.error(f"Risk-adjusted capital allocation failed: {e}")
            raise RuntimeError(f"Failed to allocate risk-adjusted capital: {e}")

    def rebalance_portfolio(
        self,
        current_allocations: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal],
        total_portfolio_value: Decimal
    ) -> List[RebalanceOrder]:
        """
        Generate rebalancing orders to align portfolio with target allocations.

        This method compares current and target allocations to determine
        necessary rebalancing actions, considering transaction costs and
        minimum rebalancing thresholds.

        Args:
            current_allocations: Current allocation percentages per protocol.
            target_allocations: Target allocation percentages per protocol.
            total_portfolio_value: Current total portfolio value.

        Returns:
            List of RebalanceOrder objects prioritized by importance.

        Example:
            >>> current = {"scroll": Decimal("0.40"), "zksync": Decimal("0.60")}
            >>> target = {"scroll": Decimal("0.30"), "zksync": Decimal("0.70")}
            >>> orders = allocator.rebalance_portfolio(current, target, 100000)
            >>> for order in orders:
            ...     print(f"{order.action} {order.protocol} by ${order.amount}")
        """
        try:
            rebalance_orders = []
 
            # Calculate deviations and determine rebalancing needs
            all_protocols = (
                set(current_allocations.keys()) | set(target_allocations.keys())
            )
 
            for protocol in all_protocols:
                current_pct = current_allocations.get(protocol, Decimal("0"))
                target_pct = target_allocations.get(protocol, Decimal("0"))
                deviation = target_pct - current_pct
 
                # Check if rebalancing is needed
                if abs(deviation) >= self.rebalance_threshold:
                    action = "increase" if deviation > 0 else "decrease"
                    amount = abs(deviation) * total_portfolio_value
                    priority = int(
                        abs(deviation) * 100
                    )  # Higher deviation = higher priority
 
                    order = RebalanceOrder(
                        protocol=protocol,
                        action=action,
                        amount=amount,
                        priority=priority
                    )
                    rebalance_orders.append(order)
 
                    logger.debug(
                        f"Rebalance needed for {protocol}: {action} by "
                        f"{deviation:.2%} (${amount:,.2f})"
                    )
 
            # Sort by priority (highest first)
            rebalance_orders.sort(key=lambda x: x.priority, reverse=True)
 
            logger.info(f"Generated {len(rebalance_orders)} rebalancing orders")
            return rebalance_orders
 
        except Exception as e:
            logger.error(f"Portfolio rebalancing failed: {e}")
            raise RuntimeError(f"Failed to generate rebalancing orders: {e}")
 
    def check_rebalance_needed(
        self,
        target_allocation: Dict[str, Decimal],
        current_allocation: Dict[str, Decimal],
    ) -> bool:
        """
        Check if rebalancing is needed based on current and target allocations.

        Args:
            target_allocation: Target allocation percentages per protocol.
            current_allocation: Current allocation percentages per protocol.

        Returns:
            True if rebalancing is needed, False otherwise.
        """
        # Get all protocols from both allocations
        all_protocols = set(current_allocation.keys()) | set(target_allocation.keys())
        
        # Calculate the sum of absolute deviations
        total_deviation = Decimal("0")
        
        for protocol in all_protocols:
            current_pct = current_allocation.get(protocol, Decimal("0"))
            target_pct = target_allocation.get(protocol, Decimal("0"))
            deviation = abs(current_pct - target_pct)
            total_deviation += deviation
        
        # The sum of absolute deviations represents twice the actual drift
        # because if one asset increases by X%, others must decrease by X% in total
        actual_drift = total_deviation / 2
        
        # Check if drift exceeds threshold
        return actual_drift > self.rebalance_threshold
 
    def distribute_capital_to_wallets(
        self,
        total_capital: Decimal,
        portfolio_allocation: Dict[str, Decimal],
        wallets: List[str]
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        Distribute total capital across multiple wallets based on portfolio allocation.
 
        Args:
            total_capital: Total capital to distribute.
            portfolio_allocation: Target allocation percentages per protocol.
            wallets: List of wallet addresses.
 
        Returns:
            A dictionary where keys are wallet addresses and values are dictionaries
            of protocol allocations for that wallet.
        """
        if not wallets:
            raise ValueError("No wallets provided for distribution.")
 
        capital_per_wallet = total_capital / Decimal(str(len(wallets)))
        distribution = {}
 
        for wallet in wallets:
            wallet_allocations = {}
            for protocol, percentage in portfolio_allocation.items():
                wallet_allocations[protocol] = capital_per_wallet * percentage
            distribution[wallet] = wallet_allocations
 
        logger.info(f"Distributed ${total_capital:,.2f} across {len(wallets)} wallets.")
        return distribution
 
    def track_allocation_metrics(
        self,
        allocation: Dict[str, Decimal],
        portfolio: Dict[str, Decimal]
    ) -> None:
        """
        Track and record allocation-related metrics.
 
        This is a placeholder for integration with a metrics collection system.
 
        Args:
            allocation: The actual allocated capital amounts.
            portfolio: The target portfolio allocation percentages.
        """
        # In a real system, this would send data to MetricsCollector
        # For now, just log the action
        total_allocated = sum(allocation.values())
        logger.info(
            f"Tracking allocation metrics. Total allocated: ${total_allocated:,.2f}"
        )
        # Example of what might be recorded:
        # self.metrics_collector.record_allocation(
        #     timestamp=time.time(),
        #     total_capital=total_allocated,
        #     allocations=allocation,
        #     target_portfolio=portfolio
        # )
 
    def handle_emergency_withdrawal(
        self,
        current_allocation: Dict[str, Decimal],
        risk_event: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """
        Handle emergency capital withdrawal from affected protocols during a risk event.
 
        Args:
            current_allocation: Current capital allocation across protocols.
            risk_event: (
                "Details of the risk event (e.g., type, affected protocol, severity)."
            )
 
        Returns:
            Adjusted capital allocation after emergency withdrawal.
        """
        affected_protocol = risk_event.get("affected_protocol")
        severity = risk_event.get("severity", "medium")
 
        if not affected_protocol or affected_protocol not in current_allocation:
            logger.warning(
                "Emergency withdrawal requested for unknown or unaffected protocol: "
                f"{affected_protocol}"
            )
            return current_allocation
 
        adjusted_allocation = current_allocation.copy()
        withdrawal_factor = Decimal("0.0")
 
        if severity == "critical":
            withdrawal_factor = Decimal("0.9")  # Withdraw 90%
        elif severity == "high":
            withdrawal_factor = Decimal("0.7")  # Withdraw 70%
        elif severity == "medium":
            withdrawal_factor = Decimal("0.5")  # Withdraw 50%
 
        amount_to_withdraw = adjusted_allocation[affected_protocol] * withdrawal_factor
        adjusted_allocation[affected_protocol] -= amount_to_withdraw
 
        # Redistribute withdrawn capital to other protocols
        # (e.g., equally or to safer ones)
        remaining_protocols = [
            p for p in adjusted_allocation if p != affected_protocol
        ]
        if remaining_protocols and amount_to_withdraw > 0:
            redistribution_amount_per_protocol = amount_to_withdraw / Decimal(
                str(len(remaining_protocols))
            )
            for p in remaining_protocols:
                adjusted_allocation[p] += redistribution_amount_per_protocol
 
        logger.warning(
            f"Emergency withdrawal: {amount_to_withdraw:,.2f} from {affected_protocol} "
            f"due to {risk_event.get('type', 'unknown')} event (Severity: {severity})"
        )
        return adjusted_allocation
 
    def optimize_with_correlations(
        self,
        protocols: List[str],
        correlation_matrix: Dict[tuple, Decimal],
        max_portfolio_correlation: Decimal
    ) -> Dict[str, Decimal]:
        """
        Optimize portfolio allocation considering protocol correlations.
 
        This is a simplified placeholder. A real implementation would involve
        complex quadratic programming or similar optimization techniques.
 
        Args:
            protocols: List of protocols to consider.
            correlation_matrix: Dictionary of (protocol1, protocol2) -> correlation.
            max_portfolio_correlation: Maximum allowed average portfolio correlation.
 
        Returns:
            Optimized allocation percentages per protocol.
        """
        # For simplicity, this mock implementation will try to penalize
        # highly correlated assets and favor less correlated ones,
        # without actual complex optimization.

        # Start with equal weight
        if not protocols:
            return {}

        initial_allocation = {
            p: Decimal("1") / Decimal(str(len(protocols))) for p in protocols
        }
        
        # Adjust based on correlations
        adjusted_allocation = initial_allocation.copy()
        
        for (p1, p2), correlation in correlation_matrix.items():
            if correlation > max_portfolio_correlation:
                # Reduce allocation for highly correlated pairs
                reduction_factor = (
                    Decimal("0.1")
                    * (correlation - max_portfolio_correlation)
                    / (Decimal("1") - max_portfolio_correlation)
                )
                if p1 in adjusted_allocation:
                    adjusted_allocation[p1] -= (
                        adjusted_allocation[p1] * reduction_factor
                    )
                if p2 in adjusted_allocation:
                    adjusted_allocation[p2] -= (
                        adjusted_allocation[p2] * reduction_factor
                    )
        
        # Re-normalize to ensure sum is 1 (or close to it)
        total_adjusted = sum(adjusted_allocation.values())
        if total_adjusted > 0:
            adjusted_allocation = {
                p: alloc / total_adjusted for p, alloc in adjusted_allocation.items()
            }
 
        logger.info(
            f"Portfolio optimized with correlation constraints: {adjusted_allocation}"
        )
        return adjusted_allocation
 
    def _get_time_based_multiplier(self) -> Decimal:
        """
        Calculate a time-based multiplier for capital allocation.
 
        This is a placeholder for dynamic adjustments based on time of day/week.
        For example, lower allocation during weekends or off-peak hours.
 
        Returns:
            A Decimal multiplier (e.g., 1.0 for normal, 0.8 for off-peak).
        """
        now = pendulum.now()
        
        # Example logic: lower multiplier on weekends
        if now.day_of_week in [pendulum.SATURDAY, pendulum.SUNDAY]:
            return Decimal("0.7")
        
        # Example logic: lower multiplier during late night/early morning
        if now.hour < 8 or now.hour > 22:
            return Decimal("0.9")
            
        return Decimal("1.0")

    def calculate_efficiency_metrics(
        self,
        portfolio_returns: List[Decimal],
        benchmark_returns: Optional[List[Decimal]] = None
    ) -> PortfolioMetrics:
        """
        Calculate portfolio efficiency and performance metrics.

        This method computes various performance metrics including ROI,
        Sharpe ratio, maximum drawdown, and capital utilization rates.

        Args:
            portfolio_returns: List of portfolio returns over time.
            benchmark_returns: Optional benchmark returns for comparison.

        Returns:
            PortfolioMetrics object with calculated performance metrics.

        Example:
            >>> returns = [Decimal("0.02"), Decimal("0.01"), Decimal("-0.005")]
            >>> metrics = allocator.calculate_efficiency_metrics(returns)
            >>> print(f"Sharpe ratio: {metrics.sharpe_ratio:.3f}")
            >>> print(f"Max drawdown: {metrics.max_drawdown:.2%}")
        """
        try:
            if not portfolio_returns:
                logger.warning("No portfolio returns provided")
                return PortfolioMetrics(
                    total_value=Decimal("0"),
                    total_return=Decimal("0"),
                    sharpe_ratio=Decimal("0"),
                    max_drawdown=Decimal("0"),
                    capital_utilization=Decimal("0"),
                    protocol_allocations={}
                )

            # Convert to numpy arrays for calculations
            returns_array = np.array([float(r) for r in portfolio_returns])

            # Calculate total return
            total_return = Decimal(str(np.prod(1 + returns_array) - 1))

            # Calculate Sharpe ratio
            mean_return = Decimal(str(np.mean(returns_array)))
            std_return = Decimal(
                str(np.std(returns_array, ddof=1))
            )  # Use sample std dev

            if std_return > Decimal("0.0001"):  # Avoid division by very small numbers
                excess_return = mean_return - self.risk_free_rate
                sharpe_ratio = excess_return / std_return
                # Round to avoid precision issues
                sharpe_ratio = sharpe_ratio.quantize(Decimal("0.001"))
            else:
                sharpe_ratio = Decimal("0")

            # Calculate maximum drawdown
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = Decimal(str(abs(np.min(drawdowns))))

            # Mock values for other metrics (would be calculated from real data)
            total_value = Decimal("100000")  # Placeholder
            capital_utilization = Decimal("0.85")  # 85% utilization
            protocol_allocations = {
                "scroll": Decimal("0.30"), "zksync": Decimal("0.70")
            }

            metrics = PortfolioMetrics(
                total_value=total_value,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                capital_utilization=capital_utilization,
                protocol_allocations=protocol_allocations
            )

            # Store in history
            self.portfolio_history.append(metrics)

            logger.info(
                f"Portfolio metrics calculated - Return: {total_return:.2%}, "
                f"Sharpe: {sharpe_ratio:.3f}, Max DD: {max_drawdown:.2%}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Efficiency metrics calculation failed: {e}")
            raise RuntimeError(f"Failed to calculate efficiency metrics: {e}")

    def _equal_weight_allocation(
        self,
        protocols: List[str],
        risk_constraints: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Calculate equal weight allocation across protocols."""
        max_exposure = risk_constraints.get("max_protocol_exposure_pct", Decimal("100"))
        equal_weight = Decimal("1") / Decimal(str(len(protocols)))

        # Ensure no protocol exceeds maximum exposure
        allocation_pct = min(equal_weight, max_exposure / Decimal("100"))

        return {protocol: allocation_pct for protocol in protocols}

    def _risk_parity_allocation(
        self,
        protocols: List[str],
        risk_scores: Dict[str, Decimal],
        risk_constraints: Dict[str, Decimal],
    ) -> Dict[str, Decimal]:
        """Calculate risk parity allocation based on inverse risk scores."""
        if not protocols:
            return {}

        max_exposure = risk_constraints.get(
            "max_protocol_exposure_pct", self.max_allocation * 100
        ) / Decimal("100")

        # Calculate inverse risk weights
        inverse_risks = {
            p: Decimal("1") / risk_scores.get(p, Decimal("1")) for p in protocols
        }

        # Initialize allocations
        final_allocations = {}
        constrained_min = set()  # Protocols at min allocation
        constrained_max = set()  # Protocols at max allocation

        # First pass: identify which protocols will hit constraints
        total_inverse = sum(inverse_risks.values())
        for p in protocols:
            natural_alloc = inverse_risks[p] / total_inverse
            if natural_alloc < self.min_allocation:
                final_allocations[p] = self.min_allocation
                constrained_min.add(p)
            elif natural_alloc > max_exposure:
                final_allocations[p] = max_exposure
                constrained_max.add(p)

        # Calculate remaining allocation and unconstrained protocols
        remaining_alloc = Decimal("1") - sum(final_allocations.values())
        unconstrained = set(protocols) - constrained_min - constrained_max

        # Redistribute remaining allocation among unconstrained protocols
        max_iterations = 10
        for _ in range(max_iterations):
            if not unconstrained or remaining_alloc <= Decimal("0.0001"):
                break

            # Calculate weights for unconstrained protocols
            unconstrained_sum = sum(inverse_risks[p] for p in unconstrained)
            if unconstrained_sum <= 0:
                # Equal distribution
                if unconstrained:
                    for p in unconstrained:
                        final_allocations[p] = remaining_alloc / len(unconstrained)
                break

            # Allocate to unconstrained protocols
            newly_constrained = set()
            tentative = {}

            for p in unconstrained:
                alloc = remaining_alloc * inverse_risks[p] / unconstrained_sum

                if alloc < self.min_allocation:
                    final_allocations[p] = self.min_allocation
                    newly_constrained.add(p)
                    constrained_min.add(p)
                elif alloc > max_exposure:
                    final_allocations[p] = max_exposure
                    newly_constrained.add(p)
                    constrained_max.add(p)
                else:
                    tentative[p] = alloc

            if not newly_constrained:
                # No new constraints, finalize allocations
                for p, alloc in tentative.items():
                    final_allocations[p] = alloc
                break

            # Update for next iteration
            unconstrained -= newly_constrained
            remaining_alloc = Decimal("1") - sum(final_allocations.values())

        # Final adjustment: if there's still unallocated capital,
        # distribute it among protocols that can accept more
        remaining = Decimal("1") - sum(final_allocations.values())
        if remaining > Decimal("0.0001"):
            # Try to add to protocols not at max
            eligible = [p for p in protocols if p not in constrained_max]
            if eligible:
                # Distribute proportionally to current allocations
                current_total = sum(final_allocations.get(p, 0) for p in eligible)
                if current_total > 0:
                    for p in eligible:
                        share = final_allocations.get(p, 0) / current_total
                        additional = remaining * share
                        new_alloc = final_allocations.get(p, 0) + additional
                        if new_alloc <= max_exposure:
                            final_allocations[p] = new_alloc
                        else:
                            final_allocations[p] = max_exposure
                else:
                    # Equal distribution
                    per_protocol = remaining / len(eligible)
                    for p in eligible:
                        final_allocations[p] = min(
                            final_allocations.get(p, Decimal("0")) + per_protocol,
                            max_exposure,
                        )

        return final_allocations

    def _mean_variance_allocation(
        self,
        protocols: List[str],
        expected_returns: Dict[str, Decimal],
        risk_scores: Dict[str, Decimal],
        risk_constraints: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Calculate mean-variance optimal allocation."""
        # Simplified mean-variance optimization
        # In practice, this would use more sophisticated optimization

        allocations = {}
        max_exposure = (
            risk_constraints.get("max_protocol_exposure_pct", Decimal("100"))
            / Decimal("100")
        )

        # Set a higher precision for Decimal operations within this method
        from decimal import getcontext
        getcontext().prec = 28

        # Calculate risk-adjusted returns
        risk_adjusted_returns = {}
        for protocol in protocols:
            # Ensure values are Decimal before division
            exp_ret = Decimal(str(expected_returns[protocol]))
            r_score = Decimal(str(risk_scores[protocol]))
            
            if r_score == Decimal("0"):  # Avoid division by zero
                risk_adjusted_return = Decimal("0")
                logger.warning(
                    f"Risk score for protocol {protocol} is zero, "
                    "setting risk-adjusted return to 0."
                )
            else:
                risk_adjusted_return = exp_ret / r_score
            
            risk_adjusted_returns[protocol] = risk_adjusted_return

        # Normalize to get allocations
        total_risk_adjusted = sum(risk_adjusted_returns.values())
        
        if total_risk_adjusted == Decimal("0"):  # Avoid division by zero
            logger.warning(
                "Total risk-adjusted returns sum to zero, distributing equally."
            )
            # Fallback to equal weight if all risk-adjusted returns are zero
            return {p: Decimal("1") / Decimal(str(len(protocols))) for p in protocols}

        for protocol in protocols:
            allocation = (
                risk_adjusted_returns[protocol] / total_risk_adjusted
            ).quantize(Decimal("1e-5"))
            allocations[protocol] = min(allocation, max_exposure)

        return allocations

    def _calculate_risk_multiplier(
        self,
        volatility_state: str,
        gas_price: Decimal,
        circuit_breaker: bool
    ) -> Decimal:
        """Calculate risk adjustment multiplier based on market conditions."""
        if circuit_breaker:
            return Decimal("0")  # No allocation if circuit breaker is active

        # Base multiplier
        multiplier = Decimal("1.0")

        # Adjust for volatility
        volatility_adjustments = {
            "low": Decimal("1.0"),
            "medium": Decimal("0.8"),
            "high": Decimal("0.6"),
            "extreme": Decimal("0.3")
        }
        multiplier *= volatility_adjustments.get(volatility_state, Decimal("0.8"))

        # Adjust for gas prices (reduce allocation if gas is too high)
        if gas_price > Decimal("100"):
            multiplier *= Decimal("0.7")
        elif gas_price > Decimal("50"):
            multiplier *= Decimal("0.9")

        return multiplier


__all__ = [
    "CapitalAllocator",
    "AllocationStrategy",
    "AllocationTarget",
    "PortfolioMetrics",
    "RebalanceOrder"
]
