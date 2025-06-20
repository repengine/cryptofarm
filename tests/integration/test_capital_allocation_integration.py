"""
Integration tests for the capital allocation module.
"""

import pytest
from decimal import Decimal

from airdrops.capital_allocation.engine import (
    CapitalAllocator,
    AllocationStrategy,
)


@pytest.fixture
def capital_allocator():
    """Fixture for a CapitalAllocator instance with default config."""
    config = {
        "capital_allocation": {
            "strategy": "equal_weight",
            "rebalance_threshold": Decimal("0.1"),
            "min_protocol_allocation": Decimal("0.01"),
            "max_protocol_allocation": Decimal("0.5"),
        }
    }
    return CapitalAllocator(config)


def test_equal_weight_allocation_integration(capital_allocator):
    """
    Test equal weight allocation strategy with a simple scenario.
    """
    total_capital = Decimal("10000")
    protocols = ["protocol_a", "protocol_b", "protocol_c"]
    risk_constraints = {"max_protocol_exposure_pct": Decimal("100")}

    # 1. Get the allocation percentages from the optimizer
    portfolio_allocations = capital_allocator.optimize_portfolio(
        protocols, risk_constraints
    )

    # 2. Allocate capital based on the optimized percentages
    risk_metrics = {"volatility_state": "low"}
    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio_allocations, risk_metrics
    )

    # Assertions
    assert isinstance(allocations, dict)
    assert len(allocations) == len(protocols)
    expected_allocation = total_capital / Decimal(str(len(protocols)))
    for protocol in protocols:
        assert protocol in allocations
        # Each should get roughly 1/3 of total capital
        assert allocations[protocol] == pytest.approx(expected_allocation)

    # Sum of allocations should be close to total capital
    assert sum(allocations.values()) == pytest.approx(total_capital)


def test_risk_parity_allocation_integration(capital_allocator):
    """
    Test risk parity allocation strategy with varying risk scores.
    """
    capital_allocator.allocation_strategy = AllocationStrategy.RISK_PARITY
    total_capital = Decimal("10000")
    protocols = ["protocol_x", "protocol_y", "protocol_z"]
    risk_constraints = {"max_protocol_exposure_pct": Decimal("100")}

    # Protocol X is lowest risk, Protocol Z is highest risk
    risk_scores = {
        "protocol_x": Decimal("0.1"),
        "protocol_y": Decimal("0.5"),
        "protocol_z": Decimal("0.9"),
    }

    portfolio_allocations = capital_allocator.optimize_portfolio(
        protocols, risk_constraints, risk_scores=risk_scores
    )

    risk_metrics = {"volatility_state": "low"}  # Use low vol to not affect amounts
    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio_allocations, risk_metrics
    )

    # Assertions
    assert isinstance(allocations, dict)
    assert len(allocations) == len(protocols)

    # Lower risk protocol (X) should get higher allocation
    assert allocations["protocol_x"] > allocations["protocol_y"]
    assert allocations["protocol_y"] > allocations["protocol_z"]

    # All allocations should be positive
    assert all(alloc > Decimal("0") for alloc in allocations.values())

    # Sum of allocations should be close to total capital
    assert sum(allocations.values()) == pytest.approx(total_capital)


def test_rebalancing_logic_integration(capital_allocator):
    """
    Test rebalancing logic with a scenario where rebalance is needed.
    """
    # Set up a scenario where current portfolio is drifted from target
    capital_allocator.current_portfolio = {
        "protocol_a": Decimal("0.8"),
        "protocol_b": Decimal("0.2"),
    }
    capital_allocator.target_portfolio = {
        "protocol_a": Decimal("0.5"),
        "protocol_b": Decimal("0.5"),
    }

    # Check if rebalance is needed
    needs_rebalance = capital_allocator.check_rebalance_needed(
        capital_allocator.target_portfolio, capital_allocator.current_portfolio
    )
    assert needs_rebalance is True

    # Simulate rebalancing (this is usually done by an external process
    # or a scheduler, but we can call the internal method for testing)
    # In a real scenario, allocate_risk_adjusted_capital would be called
    # with updated portfolio weights after rebalancing.
    # For this test, we'll just confirm the check_rebalance_needed logic.


def test_min_max_allocation_constraints_integration(capital_allocator):
    """
    Test that min/max allocation constraints are respected.
    """
    capital_allocator.min_allocation = Decimal("0.2")
    capital_allocator.max_allocation = Decimal("0.4")
    capital_allocator.allocation_strategy = AllocationStrategy.RISK_PARITY

    total_capital = Decimal("10000")
    protocols = ["p1", "p2", "p3", "p4", "p5"]  # Use more protocols to see constraints
    risk_constraints = {"max_protocol_exposure_pct": Decimal("40")}
    risk_scores = {p: Decimal(str(i * 0.1 + 0.1)) for i, p in enumerate(protocols)}

    portfolio_allocations = capital_allocator.optimize_portfolio(
        protocols, risk_constraints, risk_scores=risk_scores
    )

    risk_metrics = {"volatility_state": "low"}
    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio_allocations, risk_metrics
    )

    # Assertions: all allocations should be within min/max bounds
    for alloc_pct in portfolio_allocations.values():
        assert alloc_pct >= capital_allocator.min_allocation
        assert alloc_pct <= capital_allocator.max_allocation

    assert sum(allocations.values()) == pytest.approx(total_capital)


def test_edge_case_single_protocol(capital_allocator):
    """
    Test allocation with only a single protocol.
    """
    total_capital = Decimal("5000")
    portfolio = {"single_protocol": Decimal("1")}

    risk_metrics = {"volatility_state": "low"}

    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio, risk_metrics
    )

    assert len(allocations) == 1
    assert "single_protocol" in allocations
    assert allocations["single_protocol"] == total_capital


def test_edge_case_zero_total_capital(capital_allocator):
    """
    Test allocation with zero total capital.
    """
    total_capital = Decimal("0")
    protocols = ["p1", "p2"]
    portfolio = {p: Decimal("1") for p in protocols}

    risk_metrics = {"volatility_state": "low"}

    with pytest.raises(ValueError, match="Total capital must be positive"):
        capital_allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
