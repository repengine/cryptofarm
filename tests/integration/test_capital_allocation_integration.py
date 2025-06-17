"""
Integration tests for the capital allocation module.
"""

import pytest
from decimal import Decimal

from airdrops.capital_allocation.engine import CapitalAllocator  # type: ignore


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
    portfolio = {p: Decimal("1") for p in protocols}  # Initial equal weights

    risk_metrics = {"volatility_state": "low"}

    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio, risk_metrics
    )

    # Assertions
    assert isinstance(allocations, dict)
    assert len(allocations) == len(protocols)
    for protocol in protocols:
        assert protocol in allocations
        # Each should get roughly 1/3 of total capital
        expected_allocation = total_capital / Decimal(str(len(protocols)))
        assert abs(allocations[protocol] - expected_allocation) < Decimal("0.01")
        assert allocations[protocol] >= capital_allocator.min_allocation * total_capital
        assert allocations[protocol] <= capital_allocator.max_allocation * total_capital

    # Sum of allocations should be close to total capital
    assert abs(sum(allocations.values()) - total_capital) < Decimal("0.01")


def test_risk_parity_allocation_integration(capital_allocator):
    """
    Test risk parity allocation strategy with varying risk scores.
    """
    capital_allocator.config["capital_allocation"]["strategy"] = "risk_parity"
    total_capital = Decimal("10000")
    protocols = ["protocol_x", "protocol_y", "protocol_z"]

    # Protocol X is lowest risk, Protocol Z is highest risk
    risk_scores = {
        "protocol_x": Decimal("0.1"),
        "protocol_y": Decimal("0.5"),
        "protocol_z": Decimal("0.9"),
    }
    portfolio = {p: Decimal("1") for p in protocols}  # Initial equal weights

    risk_metrics = {"volatility_state": "high", "protocol_risks": risk_scores}

    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio, risk_metrics
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
    assert abs(sum(allocations.values()) - total_capital) < Decimal("0.01")


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
    capital_allocator.config["capital_allocation"]["min_protocol_allocation"] = Decimal("0.2")
    capital_allocator.config["capital_allocation"]["max_protocol_allocation"] = Decimal("0.4")

    total_capital = Decimal("10000")
    protocols = ["p1", "p2", "p3"]
    portfolio = {p: Decimal("1") for p in protocols}

    risk_metrics = {"volatility_state": "low"}

    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio, risk_metrics
    )

    # Assertions: all allocations should be within min/max bounds
    for protocol, alloc_amount in allocations.items():
        assert alloc_amount >= capital_allocator.min_allocation * total_capital
        assert alloc_amount <= capital_allocator.max_allocation * total_capital

    assert abs(sum(allocations.values()) - total_capital) < Decimal("0.01")


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

    allocations = capital_allocator.allocate_risk_adjusted_capital(
        total_capital, portfolio, risk_metrics
    )

    assert len(allocations) == 2
    assert all(alloc == Decimal("0") for alloc in allocations.values())
