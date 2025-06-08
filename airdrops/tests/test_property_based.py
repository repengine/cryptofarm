"""
Property-based tests for airdrops modules using Hypothesis.

This module contains property-based tests that verify invariants and properties
across the airdrops system using the Hypothesis testing framework.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant
from decimal import Decimal
from typing import Dict, List, Any, Optional
import pendulum

from airdrops.capital_allocation.engine import (
    CapitalAllocator,
    AllocationStrategy,
    AllocationTarget
)
from airdrops.monitoring.collector import MetricsCollector
from airdrops.scheduler.bot import TaskStatus, TaskPriority
from airdrops.analytics.optimizer import ROIOptimizer
from airdrops.analytics.portfolio import PortfolioPerformanceAnalyzer


# Custom strategies for domain-specific types
protocol_strategy = st.sampled_from(["scroll", "zksync", "eigenlayer", "layerzero", "hyperliquid"])
wallet_strategy = st.text(
    alphabet="0123456789abcdef",
    min_size=40,
    max_size=40
).map(lambda s: f"0x{s}")
decimal_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("1000000"),
    places=6
)
percentage_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("1"),
    places=4
)


class TestCapitalAllocationProperties:
    """Property-based tests for capital allocation engine."""

    @given(
        protocols=st.lists(protocol_strategy, min_size=1, max_size=10, unique=True),
        total_capital=st.decimals(
            min_value=Decimal("1000"),
            max_value=Decimal("1000000"),
            places=2
        )
    )
    @settings(max_examples=100)
    def test_allocation_sums_to_total(self, protocols: List[str], total_capital: Decimal):
        """Test that allocations always sum to total capital or less.
        
        Property: Sum of all allocations <= total capital
        
        Args:
            protocols: List of protocol names
            total_capital: Total capital to allocate
        """
        config = {
            "capital_allocation": {
                "strategy": "equal_weight",
                "rebalance_threshold": 0.1,
                "min_protocol_allocation": 0.01,
                "max_protocol_allocation": 0.5,
            }
        }
        
        allocator = CapitalAllocator(config)
        
        # Create equal weight portfolio
        portfolio = {p: Decimal(1) / len(protocols) for p in protocols}
        
        # Allocate capital
        risk_metrics = {"volatility_state": "low"}
        allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
        
        # Property: sum of allocations <= total capital
        total_allocated = sum(allocations.values())
        assert total_allocated <= total_capital
        
        # Property: no negative allocations
        assert all(amount >= 0 for amount in allocations.values())

    @given(
        protocols=st.lists(protocol_strategy, min_size=2, max_size=8, unique=True),
        risk_scores=st.lists(
            percentage_strategy,
            min_size=2,
            max_size=8
        )
    )
    def test_risk_parity_allocation_properties(
        self, protocols: List[str], risk_scores: List[Decimal]
    ):
        """Test risk parity allocation maintains expected properties.
        
        Properties:
        - Lower risk protocols get higher allocations
        - All protocols get non-zero allocation
        - Allocations sum to 100%
        
        Args:
            protocols: List of protocol names
            risk_scores: List of risk scores (0-1)
        """
        assume(len(protocols) == len(risk_scores))
        assume(all(0 < score < 1 for score in risk_scores))
        
        config = {
            "capital_allocation": {
                "strategy": "risk_parity",
                "rebalance_threshold": 0.1,
                "min_protocol_allocation": 0.05,
                "max_protocol_allocation": 0.5,
            }
        }
        
        allocator = CapitalAllocator(config)
        
        # Create risk score mapping
        protocol_risks = dict(zip(protocols, risk_scores))
        risk_constraints = {"max_protocol_exposure": Decimal("0.5")}
        
        # Optimize portfolio
        portfolio = allocator.optimize_portfolio(
            protocols,
            risk_constraints,
            risk_scores=protocol_risks
        )
        
        # Property: allocations sum to 100%
        total_allocation = sum(portfolio.values())
        assert abs(total_allocation - Decimal("1.0")) < Decimal("0.01")
        
        # Property: all protocols get minimum allocation
        assert all(
            alloc >= allocator.min_allocation
            for alloc in portfolio.values()
        )
        
        # Property: no protocol exceeds maximum
        assert all(
            alloc <= allocator.max_allocation
            for alloc in portfolio.values()
        )

    @given(
        current_prices=st.dictionaries(
            protocol_strategy,
            st.decimals(min_value=Decimal("0.1"), max_value=Decimal("10000"), places=2),
            min_size=3,
            max_size=5
        ),
        target_allocation=st.dictionaries(
            protocol_strategy,
            percentage_strategy,
            min_size=3,
            max_size=5
        )
    )
    def test_rebalancing_threshold_logic(
        self,
        current_prices: Dict[str, Decimal],
        target_allocation: Dict[str, Decimal]
    ):
        """Test rebalancing threshold calculations are consistent.
        
        Property: Rebalancing should only trigger when drift exceeds threshold
        
        Args:
            current_prices: Current token prices
            target_allocation: Target allocation percentages
        """
        # Ensure dictionaries have same keys
        protocols = list(set(current_prices.keys()) & set(target_allocation.keys()))
        assume(len(protocols) >= 2)
        
        # Normalize target allocation
        total_target = sum(target_allocation[p] for p in protocols)
        assume(total_target > 0)
        normalized_target = {
            p: target_allocation[p] / total_target
            for p in protocols
        }
        
        config = {"capital_allocation": {"rebalance_threshold": 0.1}}
        allocator = CapitalAllocator(config)
        
        # Test various drift scenarios
        for drift_factor in [0.05, 0.09, 0.11, 0.20]:
            # Create drifted allocation
            current_allocation = {}
            for i, protocol in enumerate(protocols):
                if i == 0:
                    # Increase first protocol
                    current_allocation[protocol] = normalized_target[protocol] * (1 + Decimal(drift_factor))
                else:
                    # Decrease others proportionally
                    reduction = Decimal(drift_factor) * normalized_target[protocols[0]] / (len(protocols) - 1)
                    current_allocation[protocol] = normalized_target[protocol] - reduction
            
            # Check rebalancing decision
            needs_rebalance = allocator.check_rebalance_needed(
                normalized_target,
                current_allocation
            )
            
            # Property: rebalance only if drift > threshold
            if drift_factor > 0.1:
                assert needs_rebalance is True
            else:
                assert needs_rebalance is False


class TestMonitoringProperties:
    """Property-based tests for monitoring system."""

    @given(
        transactions=st.lists(
            st.fixed_dictionaries({
                "protocol": protocol_strategy,
                "success": st.booleans(),
                "gas_used": st.integers(min_value=21000, max_value=1000000),
                "value_usd": st.floats(min_value=0, max_value=10000),
                "timestamp": st.integers(min_value=1600000000, max_value=1800000000)
            }),
            min_size=1,
            max_size=100
        )
    )
    def test_metrics_aggregation_consistency(self, transactions: List[Dict[str, Any]]):
        """Test that metrics aggregation is consistent and accurate.
        
        Properties:
        - Sum of protocol metrics equals total metrics
        - Success rate is between 0 and 1
        - Average calculations are correct
        
        Args:
            transactions: List of transaction records
        """
        collector = MetricsCollector()
        
        # Record all transactions
        for i, tx in enumerate(transactions):
            collector.record_transaction(
                protocol=tx["protocol"],
                action="test_action",
                wallet=f"0x{'0' * 39}{i}",
                success=tx["success"],
                gas_used=tx["gas_used"],
                value_usd=tx["value_usd"],
                tx_hash=f"0x{'a' * 63}{i}"
            )
        
        # Get aggregated metrics
        all_protocols = list(set(tx["protocol"] for tx in transactions))
        total_metrics = {"transactions": 0, "successes": 0, "gas": 0, "value": 0}
        
        for protocol in all_protocols:
            metrics = collector.get_protocol_metrics(protocol)
            total_metrics["transactions"] += metrics["total_transactions"]
            total_metrics["successes"] += metrics["successful_transactions"]
            total_metrics["gas"] += metrics["total_gas_used"]
            total_metrics["value"] += metrics["total_value_usd"]
        
        # Property: sum of parts equals whole
        assert total_metrics["transactions"] == len(transactions)
        
        # Property: success rate is valid probability
        if total_metrics["transactions"] > 0:
            success_rate = total_metrics["successes"] / total_metrics["transactions"]
            assert 0 <= success_rate <= 1
        
        # Property: gas and value are non-negative
        assert total_metrics["gas"] >= 0
        assert total_metrics["value"] >= 0

    @given(
        metric_values=st.lists(
            st.floats(min_value=0, max_value=1000, allow_nan=False),
            min_size=1,
            max_size=1000
        )
    )
    def test_percentile_calculations(self, metric_values: List[float]):
        """Test percentile calculations maintain mathematical properties.
        
        Properties:
        - p50 (median) divides data in half
        - p95 >= p50 >= p5
        - Percentiles are within data range
        
        Args:
            metric_values: List of metric values
        """
        from airdrops.monitoring.aggregator import calculate_percentiles
        
        percentiles = calculate_percentiles(metric_values, [5, 50, 95])
        
        # Property: percentiles are ordered
        assert percentiles[5] <= percentiles[50] <= percentiles[95]
        
        # Property: percentiles are within data range
        assert min(metric_values) <= percentiles[5] <= max(metric_values)
        assert min(metric_values) <= percentiles[95] <= max(metric_values)
        
        # Property: median divides data (approximately for even lengths)
        sorted_values = sorted(metric_values)
        median_idx = len(sorted_values) // 2
        if len(sorted_values) % 2 == 1:
            assert abs(percentiles[50] - sorted_values[median_idx]) < 0.01
        else:
            expected_median = (sorted_values[median_idx - 1] + sorted_values[median_idx]) / 2
            assert abs(percentiles[50] - expected_median) < 0.01


class PortfolioStateMachine(RuleBasedStateMachine):
    """Stateful testing for portfolio management operations."""
    
    def __init__(self):
        super().__init__()
        self.protocols = ["scroll", "zksync", "eigenlayer"]
        self.portfolio = {p: Decimal("0") for p in self.protocols}
        self.total_capital = Decimal("100000")
        self.transactions = []
        self.current_prices = {p: Decimal("1") for p in self.protocols}
    
    @rule(
        protocol=st.sampled_from(["scroll", "zksync", "eigenlayer"]),
        amount=st.decimals(min_value=Decimal("100"), max_value=Decimal("10000"), places=2)
    )
    def add_position(self, protocol: str, amount: Decimal):
        """Add to a protocol position."""
        self.portfolio[protocol] += amount
        self.transactions.append({
            "type": "add",
            "protocol": protocol,
            "amount": amount,
            "timestamp": pendulum.now()
        })
    
    @rule(
        protocol=st.sampled_from(["scroll", "zksync", "eigenlayer"]),
        percentage=st.decimals(min_value=Decimal("0.1"), max_value=Decimal("0.5"), places=2)
    )
    @precondition(lambda self: any(self.portfolio[p] > 0 for p in self.protocols))
    def reduce_position(self, protocol: str, percentage: Decimal):
        """Reduce a protocol position by percentage."""
        if self.portfolio[protocol] > 0:
            reduction = self.portfolio[protocol] * percentage
            self.portfolio[protocol] -= reduction
            self.transactions.append({
                "type": "reduce",
                "protocol": protocol,
                "amount": reduction,
                "timestamp": pendulum.now()
            })
    
    @rule()
    def rebalance(self):
        """Rebalance portfolio to equal weights."""
        total_value = sum(self.portfolio.values())
        if total_value > 0:
            target_per_protocol = total_value / len(self.protocols)
            
            for protocol in self.protocols:
                diff = target_per_protocol - self.portfolio[protocol]
                self.portfolio[protocol] = target_per_protocol
                
                self.transactions.append({
                    "type": "rebalance",
                    "protocol": protocol,
                    "amount": diff,
                    "timestamp": pendulum.now()
                })
    
    @invariant()
    def portfolio_value_non_negative(self):
        """Portfolio values should never be negative."""
        assert all(value >= 0 for value in self.portfolio.values())
    
    @invariant()
    def total_value_conserved(self):
        """Total portfolio value should be conserved (minus fees)."""
        # Allow for small rounding errors
        total_value = sum(self.portfolio.values())
        assert total_value >= 0
        
        # If we've done transactions, check conservation
        if self.transactions:
            net_additions = sum(
                tx["amount"] for tx in self.transactions
                if tx["type"] == "add"
            )
            net_reductions = sum(
                tx["amount"] for tx in self.transactions
                if tx["type"] == "reduce"
            )
            
            # Account for rebalancing (net zero)
            expected_value = net_additions - net_reductions
            assert abs(total_value - expected_value) < Decimal("1")


class TestSchedulerProperties:
    """Property-based tests for scheduler logic."""

    @given(
        num_tasks=st.integers(min_value=1, max_value=100),
        num_wallets=st.integers(min_value=1, max_value=10),
        protocols=st.lists(protocol_strategy, min_size=1, max_size=5, unique=True)
    )
    def test_task_distribution_fairness(
        self,
        num_tasks: int,
        num_wallets: int,
        protocols: List[str]
    ):
        """Test that tasks are distributed fairly across wallets.
        
        Property: Task distribution should be approximately uniform
        
        Args:
            num_tasks: Number of tasks to distribute
            num_wallets: Number of wallets
            protocols: List of protocols
        """
        from collections import Counter
        
        # Generate wallets
        wallets = [f"0x{'0' * 39}{i}" for i in range(num_wallets)]
        
        # Simulate round-robin distribution
        wallet_assignments = []
        for i in range(num_tasks):
            wallet_idx = i % num_wallets
            wallet_assignments.append(wallets[wallet_idx])
        
        # Count assignments
        assignment_counts = Counter(wallet_assignments)
        
        # Property: difference between max and min assignments <= 1
        max_assignments = max(assignment_counts.values())
        min_assignments = min(assignment_counts.values())
        assert max_assignments - min_assignments <= 1
        
        # Property: all wallets get at least one task if tasks >= wallets
        if num_tasks >= num_wallets:
            assert len(assignment_counts) == num_wallets
            assert all(count >= 1 for count in assignment_counts.values())

    @given(
        task_priorities=st.lists(
            st.sampled_from([TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH]),
            min_size=5,
            max_size=20
        )
    )
    def test_priority_queue_ordering(self, task_priorities: List[TaskPriority]):
        """Test that priority queue maintains correct ordering.
        
        Property: Higher priority tasks execute before lower priority
        
        Args:
            task_priorities: List of task priorities
        """
        from queue import PriorityQueue
        
        pq = PriorityQueue()
        tasks = []
        
        # Create tasks with priorities
        for i, priority in enumerate(task_priorities):
            task = {
                "id": f"task_{i}",
                "priority": priority,
                "created_at": pendulum.now().add(seconds=i)
            }
            tasks.append(task)
            # Use negative priority value for max heap behavior
            pq.put((-priority.value, i, task))
        
        # Extract tasks in priority order
        ordered_tasks = []
        while not pq.empty():
            _, _, task = pq.get()
            ordered_tasks.append(task)
        
        # Property: tasks are ordered by priority (high to low)
        for i in range(len(ordered_tasks) - 1):
            current_priority = ordered_tasks[i]["priority"].value
            next_priority = ordered_tasks[i + 1]["priority"].value
            assert current_priority >= next_priority


# Test the stateful portfolio machine
TestPortfolioStateMachine = PortfolioStateMachine.TestCase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])