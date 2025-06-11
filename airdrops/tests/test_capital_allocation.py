"""
Tests for the Capital Allocation Engine.

This module contains comprehensive tests for the CapitalAllocator class,
covering portfolio optimization, risk-adjusted allocation, rebalancing,
and efficiency metrics calculation.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch
from typing import Dict, List

from airdrops.capital_allocation.engine import (
    CapitalAllocator,
    AllocationStrategy,
    AllocationTarget,
    PortfolioMetrics,
    RebalanceOrder
)


class TestCapitalAllocator:
    """Test suite for CapitalAllocator class."""

    @pytest.fixture(params=[
        {"capital_allocation": {"strategy": "equal_weight", "max_protocols": 5}},
        {"capital_allocation": {"strategy": "risk_parity", "max_protocols": 5}},
        {"capital_allocation": {"strategy": "mean_variance", "max_protocols": 5}}
    ])
    def allocator(self, request) -> CapitalAllocator:
        """Create a CapitalAllocator instance for testing with parameterized config."""
        return CapitalAllocator(request.param)

    @pytest.fixture
    def sample_protocols(self) -> List[str]:
        """Sample protocol list for testing."""
        return ["scroll", "zksync", "eigenlayer"]

    @pytest.fixture
    def sample_risk_constraints(self) -> Dict[str, Decimal]:
        """Sample risk constraints for testing."""
        return {
            "max_protocol_exposure_pct": Decimal("50"),  # Higher limit for testing
            "max_transaction_size_pct": Decimal("5"),
            "max_daily_loss_pct": Decimal("10")
        }

    def test_init_default_config(self):
        """Test CapitalAllocator initialization with default config."""
        allocator = CapitalAllocator()

        assert allocator.config == {}
        assert allocator.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT
        assert allocator.risk_free_rate == Decimal("0.02")
        assert allocator.rebalance_threshold == Decimal("0.10")
        assert allocator.max_protocols == 10
        assert allocator.portfolio_history == []

    def test_init_custom_config(self):
        """Test CapitalAllocator initialization with custom config."""
        config = {"capital_allocation": {"strategy": "risk_parity", "max_protocols": 3}}
        allocator = CapitalAllocator(config)

        assert allocator.config == config
        assert allocator.allocation_strategy == AllocationStrategy.RISK_PARITY

    def test_optimize_portfolio_equal_weight(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test portfolio optimization with equal weight strategy."""
        allocation = allocator.optimize_portfolio(
            sample_protocols, sample_risk_constraints
        )

        expected_allocation = Decimal("1") / Decimal("3")  # 1/3 for each protocol

        assert len(allocation) == 3
        for protocol in sample_protocols:
            assert allocation[protocol] == pytest.approx(expected_allocation, rel=Decimal("1e-5"))

    @pytest.mark.parametrize(
        "allocator",
        [{"capital_allocation": {"strategy": "risk_parity"}}],
        indirect=True
    )
    def test_optimize_portfolio_risk_parity(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test portfolio optimization with risk parity strategy."""

        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.5"),
            "eigenlayer": Decimal("0.2")
        }

        expected_allocation = allocator._risk_parity_allocation(
            sample_protocols, risk_scores, sample_risk_constraints
        )
        allocation = allocator.optimize_portfolio(
            sample_protocols, sample_risk_constraints, risk_scores=risk_scores
        )

        # Risk parity should allocate more to lower risk protocols
        # Using pytest.approx for Decimal comparisons due to potential
        # precision differences
        assert allocation["eigenlayer"] == pytest.approx(
            expected_allocation["eigenlayer"], rel=Decimal("1e-4")
        )
        assert allocation["scroll"] == pytest.approx(
            expected_allocation["scroll"], rel=Decimal("1e-4")
        )
        assert allocation["zksync"] == pytest.approx(
            expected_allocation["zksync"], rel=Decimal("1e-4")
        )

    @pytest.mark.parametrize(
        "allocator",
        [{"capital_allocation": {"strategy": "mean_variance"}}],
        indirect=True
    )
    def test_optimize_portfolio_mean_variance(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test portfolio optimization with mean variance strategy."""

        expected_returns = {
            "scroll": Decimal("0.08"),
            "zksync": Decimal("0.06"),
            "eigenlayer": Decimal("0.10")
        }
        risk_scores = {
            "scroll": Decimal("0.4"),
            "zksync": Decimal("0.6"),
            "eigenlayer": Decimal("0.3")
        }

        expected_allocation = allocator._mean_variance_allocation(
            sample_protocols, expected_returns, risk_scores, sample_risk_constraints
        )
        allocation = allocator.optimize_portfolio(
            sample_protocols, sample_risk_constraints,
            expected_returns=expected_returns, risk_scores=risk_scores
        )

        # Should allocate more to higher risk-adjusted return protocols
        assert allocation["zksync"] == pytest.approx(
            expected_allocation["zksync"], rel=Decimal("1e-4")
        )
        assert allocation["scroll"] == pytest.approx(
            expected_allocation["scroll"], rel=Decimal("1e-4")
        )
        assert allocation["eigenlayer"] == pytest.approx(
            expected_allocation["eigenlayer"], rel=Decimal("1e-4")
        )

    def test_optimize_portfolio_empty_protocols(
        self, allocator, sample_risk_constraints
    ):
        """Test portfolio optimization with empty protocols list."""
        allocation = allocator.optimize_portfolio([], sample_risk_constraints)

        assert allocation == {}

    def test_optimize_portfolio_too_many_protocols(
        self, allocator, sample_risk_constraints
    ):
        """Test portfolio optimization with too many protocols."""
        many_protocols = [f"protocol_{i}" for i in range(15)]

        allocation = allocator.optimize_portfolio(
            many_protocols, sample_risk_constraints
        )

        # Should limit to max_protocols (10 by default, 5 in fixture)
        assert len(allocation) <= allocator.max_protocols

    def test_optimize_portfolio_max_exposure_constraint(
        self, allocator, sample_protocols
    ):
        """Test portfolio optimization respects maximum exposure constraints."""
        risk_constraints = {"max_protocol_exposure_pct": Decimal("10")}  # 10% max

        allocation = allocator.optimize_portfolio(sample_protocols, risk_constraints)

        for protocol in sample_protocols:
            assert allocation[protocol] <= Decimal("0.10")

    def test_allocate_risk_adjusted_capital_normal_conditions(self, allocator):
        """Test risk-adjusted capital allocation under normal conditions."""
        total_capital = Decimal("100000")
        portfolio_allocation = {
            "scroll": Decimal("0.4"),
            "zksync": Decimal("0.6")
        }
        risk_metrics = {
            "volatility_state": "low",
            "gas_price_gwei": Decimal("30"),
            "circuit_breaker_triggered": False
        }

        capital_allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio_allocation, risk_metrics
        )

        # Under low volatility, should allocate close to target
        assert capital_allocations["scroll"] == Decimal("40000")  # 40% of 100k
        assert capital_allocations["zksync"] == Decimal("60000")  # 60% of 100k

    def test_allocate_risk_adjusted_capital_high_volatility(self, allocator):
        """Test risk-adjusted capital allocation under high volatility."""
        total_capital = Decimal("100000")
        portfolio_allocation = {
            "scroll": Decimal("0.5"),
            "zksync": Decimal("0.5")
        }
        risk_metrics = {
            "volatility_state": "high",
            "gas_price_gwei": Decimal("40"),
            "circuit_breaker_triggered": False
        }

        capital_allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio_allocation, risk_metrics
        )

        # Under high volatility, should allocate less than target
        total_allocated = sum(capital_allocations.values())
        assert total_allocated < total_capital

    def test_allocate_risk_adjusted_capital_circuit_breaker(self, allocator):
        """Test risk-adjusted capital allocation with circuit breaker active."""
        total_capital = Decimal("100000")
        portfolio_allocation = {"scroll": Decimal("1.0")}
        risk_metrics = {
            "volatility_state": "medium",
            "gas_price_gwei": Decimal("50"),
            "circuit_breaker_triggered": True
        }

        capital_allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio_allocation, risk_metrics
        )

        # Circuit breaker should result in zero allocation
        assert capital_allocations["scroll"] == Decimal("0")

    def test_allocate_risk_adjusted_capital_high_gas_prices(self, allocator):
        """Test risk-adjusted capital allocation with high gas prices."""
        total_capital = Decimal("100000")
        portfolio_allocation = {"scroll": Decimal("1.0")}
        risk_metrics = {
            "volatility_state": "low",
            "gas_price_gwei": Decimal("150"),  # High gas price
            "circuit_breaker_triggered": False
        }

        capital_allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio_allocation, risk_metrics
        )

        # High gas prices should reduce allocation
        assert capital_allocations["scroll"] < Decimal("100000")

    def test_allocate_risk_adjusted_capital_invalid_capital(self, allocator):
        """Test risk-adjusted capital allocation with invalid capital amount."""
        with pytest.raises(ValueError, match="Total capital must be positive"):
            allocator.allocate_risk_adjusted_capital(
                Decimal("0"), {}, {}
            )

    def test_rebalance_portfolio_no_rebalancing_needed(self, allocator):
        """Test portfolio rebalancing when no rebalancing is needed."""
        current_allocations = {
            "scroll": Decimal("0.30"),
            "zksync": Decimal("0.70")
        }
        target_allocations = {
            "scroll": Decimal("0.32"),  # Small deviation < threshold
            "zksync": Decimal("0.68")
        }
        total_value = Decimal("100000")

        orders = allocator.rebalance_portfolio(
            current_allocations, target_allocations, total_value
        )

        # No orders should be generated for small deviations
        assert len(orders) == 0

    def test_rebalance_portfolio_rebalancing_needed(self, allocator):
        """Test portfolio rebalancing when rebalancing is needed."""
        current_allocations = {
            "scroll": Decimal("0.20"),
            "zksync": Decimal("0.80")
        }
        target_allocations = {
            "scroll": Decimal("0.40"),  # Large deviation > threshold
            "zksync": Decimal("0.60")
        }
        total_value = Decimal("100000")

        orders = allocator.rebalance_portfolio(
            current_allocations, target_allocations, total_value
        )

        assert len(orders) == 2

        # Check scroll increase order
        scroll_order = next(o for o in orders if o.protocol == "scroll")
        assert scroll_order.action == "increase"
        assert scroll_order.amount == Decimal("20000")  # 20% of 100k

        # Check zksync decrease order
        zksync_order = next(o for o in orders if o.protocol == "zksync")
        assert zksync_order.action == "decrease"
        assert zksync_order.amount == Decimal("20000")  # 20% of 100k

    def test_rebalance_portfolio_new_protocol(self, allocator):
        """Test portfolio rebalancing with new protocol addition."""
        current_allocations = {
            "scroll": Decimal("0.50"),
            "zksync": Decimal("0.50")
        }
        target_allocations = {
            "scroll": Decimal("0.30"),
            "zksync": Decimal("0.30"),
            "eigenlayer": Decimal("0.40")  # New protocol
        }
        total_value = Decimal("100000")

        orders = allocator.rebalance_portfolio(
            current_allocations, target_allocations, total_value
        )

        # Should generate orders for all protocols with significant changes
        assert len(orders) == 3

        # New protocol should have increase order
        eigenlayer_order = next(o for o in orders if o.protocol == "eigenlayer")
        assert eigenlayer_order.action == "increase"
        assert eigenlayer_order.amount == Decimal("40000")

    def test_rebalance_portfolio_priority_ordering(self, allocator):
        """Test that rebalancing orders are prioritized correctly."""
        current_allocations = {
            "scroll": Decimal("0.10"),
            "zksync": Decimal("0.90")
        }
        target_allocations = {
            "scroll": Decimal("0.60"),  # Large deviation (50%)
            "zksync": Decimal("0.40")   # Large deviation (50%)
        }
        total_value = Decimal("100000")

        orders = allocator.rebalance_portfolio(
            current_allocations, target_allocations, total_value
        )

        # Orders should be sorted by priority (deviation magnitude)
        assert orders[0].priority >= orders[1].priority

    def test_calculate_efficiency_metrics_empty_returns(self, allocator):
        """Test efficiency metrics calculation with empty returns."""
        metrics = allocator.calculate_efficiency_metrics([])

        assert metrics.total_return == Decimal("0")
        assert metrics.sharpe_ratio == Decimal("0")
        assert metrics.max_drawdown == Decimal("0")

    def test_calculate_efficiency_metrics_positive_returns(self, allocator):
        """Test efficiency metrics calculation with positive returns."""
        returns = [
            Decimal("0.05"), Decimal("0.03"), Decimal("0.04")
        ]  # Mean = 0.04 > risk_free_rate = 0.02 # noqa: E501

        metrics = allocator.calculate_efficiency_metrics(returns)

        assert metrics.total_return > Decimal("0")
        assert metrics.sharpe_ratio > Decimal("0")
        assert len(allocator.portfolio_history) == 1

    def test_calculate_efficiency_metrics_mixed_returns(self, allocator):
        """Test efficiency metrics calculation with mixed returns."""
        returns = [Decimal("0.05"), Decimal("-0.02"), Decimal("0.01")]

        metrics = allocator.calculate_efficiency_metrics(returns)

        assert metrics.max_drawdown > Decimal("0")
        assert isinstance(metrics.total_return, Decimal)

    def test_calculate_efficiency_metrics_zero_volatility(self, allocator):
        """Test efficiency metrics calculation with zero volatility."""
        returns = [Decimal("0.02"), Decimal("0.02"), Decimal("0.02")]

        metrics = allocator.calculate_efficiency_metrics(returns)

        # Zero volatility should result in zero Sharpe ratio
        assert metrics.sharpe_ratio == Decimal("0")

    def test_equal_weight_allocation_method(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test the _equal_weight_allocation private method."""
        allocation = allocator._equal_weight_allocation(
            sample_protocols, sample_risk_constraints
        )

        expected_weight = Decimal("1") / Decimal("3")
        for protocol in sample_protocols:
            assert allocation[protocol] == expected_weight

    def test_risk_parity_allocation_method(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test the _risk_parity_allocation private method."""
        risk_scores = {
            "scroll": Decimal("0.2"),
            "zksync": Decimal("0.4"),
            "eigenlayer": Decimal("0.1")
        }

        allocation = allocator._risk_parity_allocation(
            sample_protocols, risk_scores, sample_risk_constraints
        )

        # Lower risk should get higher allocation
        assert allocation["eigenlayer"] > allocation["scroll"]
        assert allocation["scroll"] > allocation["zksync"]

    def test_mean_variance_allocation_method(
        self, allocator, sample_protocols, sample_risk_constraints
    ):
        """Test the _mean_variance_allocation private method."""
        expected_returns = {
            "scroll": Decimal("0.06"),
            "zksync": Decimal("0.04"),
            "eigenlayer": Decimal("0.08")
        }
        risk_scores = {
            "scroll": Decimal("0.3"),
            "zksync": Decimal("0.4"),
            "eigenlayer": Decimal("0.2")
        }

        allocation = allocator._mean_variance_allocation(
            sample_protocols, expected_returns, risk_scores, sample_risk_constraints
        )

        # Higher risk-adjusted return should get higher allocation
        assert allocation["eigenlayer"] > allocation["scroll"]
        assert allocation["scroll"] > allocation["zksync"]

    def test_calculate_risk_multiplier_normal_conditions(self, allocator):
        """Test risk multiplier calculation under normal conditions."""
        multiplier = allocator._calculate_risk_multiplier(
            "low", Decimal("30"), False
        )

        assert multiplier == Decimal("1.0")

    def test_calculate_risk_multiplier_high_volatility(self, allocator):
        """Test risk multiplier calculation with high volatility."""
        multiplier = allocator._calculate_risk_multiplier(
            "high", Decimal("30"), False
        )

        assert multiplier < Decimal("1.0")

    def test_calculate_risk_multiplier_circuit_breaker(self, allocator):
        """Test risk multiplier calculation with circuit breaker active."""
        multiplier = allocator._calculate_risk_multiplier(
            "low", Decimal("30"), True
        )

        assert multiplier == Decimal("0")

    def test_calculate_risk_multiplier_high_gas_prices(self, allocator):
        """Test risk multiplier calculation with high gas prices."""
        multiplier = allocator._calculate_risk_multiplier(
            "low", Decimal("150"), False
        )

        assert multiplier < Decimal("1.0")

    def test_optimize_portfolio_exception_handling(self, allocator):
        """Test portfolio optimization exception handling."""
        # Determine which allocation method to patch based on the current strategy
        if allocator.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT:
            method_to_patch = '_equal_weight_allocation'
        elif allocator.allocation_strategy == AllocationStrategy.RISK_PARITY:
            method_to_patch = '_risk_parity_allocation'
        elif allocator.allocation_strategy == AllocationStrategy.MEAN_VARIANCE:
            method_to_patch = '_mean_variance_allocation'
        else:
            pytest.fail(f"Unknown allocation strategy: {allocator.allocation_strategy}")

        with patch.object(
            allocator, method_to_patch, side_effect=Exception("Test error")
        ):
            with pytest.raises(RuntimeError, match="Failed to optimize portfolio"):
                # Provide dummy data that would trigger the patched method
                protocols = ["test_protocol"]
                risk_constraints = {"max_protocol_exposure_pct": Decimal("100")}
                expected_returns = {"test_protocol": Decimal("0.1")}
                risk_scores = {"test_protocol": Decimal("0.5")}

                allocator.optimize_portfolio(
                    protocols,
                    risk_constraints,
                    expected_returns=expected_returns,
                    risk_scores=risk_scores
                )

    def test_allocate_risk_adjusted_capital_exception_handling(self, allocator):
        """Test risk-adjusted capital allocation exception handling."""
        with patch.object(
            allocator, '_calculate_risk_multiplier', side_effect=Exception("Test error")
        ):
            with pytest.raises(
                RuntimeError, match="Failed to allocate risk-adjusted capital"
            ):
                allocator.allocate_risk_adjusted_capital(
                    Decimal("1000"), {"test": Decimal("1")}, {}
                )

    def test_rebalance_portfolio_exception_handling(self, allocator):
        """Test portfolio rebalancing exception handling."""
        with patch(
            'airdrops.capital_allocation.engine.RebalanceOrder',
            side_effect=Exception("Test error")
        ):
            with pytest.raises(
                RuntimeError, match="Failed to generate rebalancing orders"
            ):
                allocator.rebalance_portfolio(
                    {"test": Decimal("1")}, {"test": Decimal("0.5")}, Decimal("1000")
                )

    def test_calculate_efficiency_metrics_exception_handling(self, allocator):
        """Test efficiency metrics calculation exception handling."""
        with patch('numpy.array', side_effect=Exception("Test error")):
            with pytest.raises(
                RuntimeError, match="Failed to calculate efficiency metrics"
            ):
                allocator.calculate_efficiency_metrics([Decimal("0.01")])


class TestDataClasses:
    """Test suite for data classes."""

    def test_allocation_target_creation(self):
        """Test AllocationTarget data class creation."""
        target = AllocationTarget(
            protocol="scroll",
            target_percentage=Decimal("0.30"),
            current_percentage=Decimal("0.25"),
            risk_score=Decimal("0.4"),
            expected_return=Decimal("0.06")
        )

        assert target.protocol == "scroll"
        assert target.target_percentage == Decimal("0.30")
        assert target.current_percentage == Decimal("0.25")
        assert target.risk_score == Decimal("0.4")
        assert target.expected_return == Decimal("0.06")

    def test_portfolio_metrics_creation(self):
        """Test PortfolioMetrics data class creation."""
        metrics = PortfolioMetrics(
            total_value=Decimal("100000"),
            total_return=Decimal("0.05"),
            sharpe_ratio=Decimal("1.2"),
            max_drawdown=Decimal("0.03"),
            capital_utilization=Decimal("0.85"),
            protocol_allocations={"scroll": Decimal("0.5"), "zksync": Decimal("0.5")}
        )

        assert metrics.total_value == Decimal("100000")
        assert metrics.total_return == Decimal("0.05")
        assert metrics.sharpe_ratio == Decimal("1.2")
        assert metrics.max_drawdown == Decimal("0.03")
        assert metrics.capital_utilization == Decimal("0.85")
        assert len(metrics.protocol_allocations) == 2

    def test_rebalance_order_creation(self):
        """Test RebalanceOrder data class creation."""
        order = RebalanceOrder(
            protocol="scroll",
            action="increase",
            amount=Decimal("5000"),
            priority=75
        )

        assert order.protocol == "scroll"
        assert order.action == "increase"
        assert order.amount == Decimal("5000")
        assert order.priority == 75


class TestAllocationStrategy:
    """Test suite for AllocationStrategy enum."""

    def test_allocation_strategy_values(self):
        """Test AllocationStrategy enum values."""
        assert AllocationStrategy.EQUAL_WEIGHT.value == "equal_weight"
        assert AllocationStrategy.RISK_PARITY.value == "risk_parity"
        assert AllocationStrategy.MEAN_VARIANCE.value == "mean_variance"
        assert AllocationStrategy.KELLY_CRITERION.value == "kelly_criterion"
