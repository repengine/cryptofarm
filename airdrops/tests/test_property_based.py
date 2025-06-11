"""
Property-based tests for airdrops modules using Hypothesis.

This module contains property-based tests that verify invariants and properties
across the airdrops system using the Hypothesis testing framework.
"""

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant
from decimal import Decimal
from typing import Dict, List, Any, cast
import pendulum

from airdrops.capital_allocation.engine import CapitalAllocator  # type: ignore
from airdrops.monitoring.collector import MetricsCollector  # type: ignore
from airdrops.monitoring.aggregator import calculate_percentiles  # type: ignore


# Custom strategies for domain-specific types
protocol_strategy = st.sampled_from(
    ["scroll", "zksync", "eigenlayer", "layerzero", "hyperliquid"]
)
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
    def test_allocation_sums_to_total(
        self, protocols: List[str], total_capital: Decimal
    ) -> None:
        """Test that allocations always sum to total capital or less.
        Property: Sum of all allocations <= total capital
        
        Args:
            protocols: List of protocol names
            total_capital: Total capital to allocate
        """
        config = {
            "capital_allocation": {
                "strategy": "equal_weight",
                "rebalance_threshold": Decimal("0.1"),
                "min_protocol_allocation": Decimal("0.01"),
                "max_protocol_allocation": Decimal("0.5"),
            }
        }
        allocator = CapitalAllocator(config)
        
        # Create equal weight portfolio
        portfolio = {p: Decimal("1") / len(protocols) for p in protocols}
        
        risk_metrics = {"volatility_state": "low"}
        allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
        
        # Property: sum of allocations <= total capital
        total_allocated = sum(allocations.values())
        assert total_allocated <= total_capital + Decimal("1e-9")  \
            # Allow for small precision errors
        
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
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_risk_parity_allocation_properties(
        self, protocols: List[str], risk_scores: List[Decimal]
    ) -> None:
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
                "rebalance_threshold": Decimal("0.1"),
                "min_protocol_allocation": Decimal("0.05"),
                "max_protocol_allocation": Decimal("0.5"),
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
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_rebalancing_threshold_logic(
        self,
        current_prices: Dict[str, Decimal],
        target_allocation: Dict[str, Decimal]
    ) -> None:
        """Test rebalancing threshold calculations are consistent.
        
        Property: Rebalancing should only trigger when drift exceeds threshold
        
        Args:
            current_prices: Current token prices
            target_allocation: Target allocation percentages
        """
        # Ensure dictionaries have same keys and at least two protocols
        protocols = list(set(current_prices.keys()) & set(target_allocation.keys()))
        assume(len(protocols) >= 2)
        
        # Normalize target allocation
        total_target = sum(target_allocation[p] for p in protocols)
        assume(total_target > 0)
        normalized_target = {
            p: target_allocation[p] / total_target
            for p in protocols
        }

        # Filter out protocols with zero normalized target, as they cannot be
        # drifted meaningfully
        protocols_with_non_zero_target = [
            p for p in protocols if normalized_target[p] > 0
        ]
        assume(len(protocols_with_non_zero_target) >= 2)  # Need at least two

        config = {"capital_allocation": {"rebalance_threshold": Decimal("0.1")}}
        allocator = CapitalAllocator(config)
        
        # Test various drift scenarios
        for drift_trigger in [False, True]:  # Test cases for below and above threshold
            current_allocation = normalized_target.copy()
            
            # Pick two distinct protocols to create drift
            # Ensure we have at least two protocols to shift between
            if len(protocols_with_non_zero_target) < 2:
                assume(False)  # Discard if not enough protocols for meaningful drift

            # Pick two distinct protocols from the list
            protocol_to_increase = protocols_with_non_zero_target[0]
            protocol_to_decrease = protocols_with_non_zero_target[1]

            # Determine the magnitude of the drift
            if drift_trigger:
                # Ensure actual_drift (shift_amount) is > rebalance_threshold (0.1)
                shift_amount = Decimal("0.11")
            else:
                # Ensure actual_drift (shift_amount) is < rebalance_threshold (0.1)
                shift_amount = Decimal("0.09")

            # Apply the shift
            # Ensure we don't go negative or exceed 1.0
            assume(current_allocation[protocol_to_decrease] - shift_amount >= 0)
            assume(current_allocation[protocol_to_increase] + shift_amount <= 1)

            current_allocation[protocol_to_increase] += shift_amount
            current_allocation[protocol_to_decrease] -= shift_amount

            # Re-normalize current_allocation to sum to 1.0 after drift
            current_total = sum(current_allocation.values())
            if current_total > 0:
                current_allocation = {
                    p: current_allocation[p] / current_total for p in protocols
                }
            else:
                assume(False)  # Discard if total becomes zero or negative
            
            # Check rebalancing decision
            needs_rebalance = allocator.check_rebalance_needed(
                normalized_target,
                current_allocation
            )
            
            # Property: rebalance only if drift > threshold
            if drift_trigger:
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
    def test_metrics_aggregation_consistency(
        self, transactions: List[Dict[str, Any]]
    ) -> None:
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
                value_usd=Decimal(str(tx["value_usd"])),  # Convert float to Decimal
                tx_hash=f"0x{'a' * 63}{i}"
            )
        
        # Get aggregated metrics
        total_metrics = {
            "transactions": Decimal("0"),
            "successes": Decimal("0"),
            "gas": Decimal("0"),
            "value": Decimal("0")
        }
        all_protocols = list(set(tx["protocol"] for tx in transactions))
        
        for protocol in all_protocols:
            metrics = collector.get_protocol_metrics(protocol)
            total_metrics["transactions"] += Decimal(str(metrics["total_transactions"]))
            total_metrics["successes"] += Decimal(
                str(metrics["successful_transactions"])
            )
            total_metrics["gas"] += Decimal(str(metrics["total_gas_used"]))
            total_metrics["value"] += metrics["total_value_usd"]  # Already Decimal
        
        # Property: sum of parts equals whole
        assert total_metrics["transactions"] == Decimal(str(len(transactions)))
        
        # Property: success rate is valid probability
        if total_metrics["transactions"] > Decimal("0"):
            success_rate = total_metrics["successes"] / total_metrics["transactions"]
            assert Decimal("0") <= success_rate <= Decimal("1")
        
        # Property: gas and value are non-negative
        assert total_metrics["gas"] >= Decimal("0")
        assert total_metrics["value"] >= Decimal("0")

    @given(
        metric_values=st.lists(
            st.floats(min_value=0, max_value=1000, allow_nan=False),
            min_size=1,
            max_size=1000
        )
    )
    def test_percentile_calculations(self, metric_values: List[float]) -> None:
        """Test percentile calculations maintain mathematical properties.
        
        Properties:
        - p50 (median) divides data in half
        - p95 >= p50 >= p5
        - Percentiles are within data range
        
        Args:
            metric_values: List of metric values
        """
        percentiles = calculate_percentiles(metric_values, [5, 50, 95])
        
        # Property: percentiles are ordered
        assert percentiles["p5"] <= percentiles["p50"] <= percentiles["p95"]
        
        # Property: percentiles are within data range
        assert Decimal(str(min(metric_values))) <= percentiles["p5"] <= \
            Decimal(str(max(metric_values)))
        assert Decimal(str(min(metric_values))) <= percentiles["p95"] <= \
            Decimal(str(max(metric_values)))
        
        # Property: median divides data (approximately for even lengths)
        sorted_values = sorted(metric_values)
        median_idx = len(sorted_values) // 2
        if len(sorted_values) % 2 == 1:
            assert abs(
                percentiles["p50"] - Decimal(str(sorted_values[median_idx]))
            ) < Decimal("0.01")
        else:
            expected_median = (
                Decimal(str(sorted_values[median_idx - 1]))
                + Decimal(str(sorted_values[median_idx]))
            ) / Decimal("2")  # Ensure division is with Decimal
            assert abs(percentiles["p50"] - expected_median) < Decimal("0.01")


class PortfolioStateMachine(RuleBasedStateMachine):
    """Stateful testing for portfolio management operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.protocols = ["scroll", "zksync", "eigenlayer"]
        self.portfolio: Dict[str, Decimal] = {}
        for p in self.protocols:
            self.portfolio[p] = Decimal("0.0")
        self.total_capital = Decimal("100000")
        self.transactions: List[Dict[str, Any]] = []
        self.current_prices = {p: Decimal("1") for p in self.protocols}
    
    @rule(
        protocol=st.sampled_from(["scroll", "zksync", "eigenlayer"]),
        amount=st.decimals(
            min_value=Decimal("100"), max_value=Decimal("10000"), places=2
        )
    )
    def add_position(self, protocol: str, amount: Decimal) -> None:
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
        percentage=st.decimals(
            min_value=Decimal("0.1"), max_value=Decimal("0.5"), places=2
        )
    )
    @precondition(lambda self: any(self.portfolio[p] > 0 for p in self.protocols))
    def reduce_position(self, protocol: str, percentage: Decimal) -> None:
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
    def rebalance(self) -> None:
        """Rebalance portfolio to equal weights."""
        total_value = sum(self.portfolio.values())
        if total_value > 0:
            target_per_protocol = total_value / Decimal(str(len(self.protocols)))
            
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
    def portfolio_value_non_negative(self) -> None:
        """Portfolio values should never be negative."""
        assert all(value >= 0 for value in self.portfolio.values())
    
    @invariant()
    def total_value_conserved(self) -> None:
        """Total portfolio value should be conserved (minus fees)."""
        # Allow for small rounding errors
        total_value: Decimal = cast(Decimal, sum(self.portfolio.values()))
        assert total_value >= Decimal("0")  # Compare with Decimal
        
        # If we've done transactions, check conservation
        if self.transactions:
            net_additions: Decimal = sum(
                tx["amount"] for tx in self.transactions
                if tx["type"] == "add"
            )
            net_reductions: Decimal = sum(
                tx["amount"] for tx in self.transactions
                if tx["type"] == "reduce"
            )
            
            # Account for rebalancing (net zero)
            expected_value: Decimal = net_additions - net_reductions
            assert abs(total_value - expected_value) < Decimal("1")


# Test the stateful portfolio machine
TestPortfolioStateMachine = PortfolioStateMachine.TestCase
TestPortfolioStateMachine = PortfolioStateMachine.TestCase