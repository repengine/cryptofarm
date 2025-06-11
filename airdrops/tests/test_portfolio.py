"""
Tests for the portfolio performance analytics module.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Generator
from unittest.mock import patch

from airdrops.analytics.tracker import AirdropTracker, AirdropEvent
from airdrops.analytics.optimizer import ROIOptimizer
from airdrops.analytics.portfolio import (
    PortfolioPerformanceAnalyzer,
    PortfolioMetrics,
    PortfolioSnapshot,
    BenchmarkComparison,
    BenchmarkType
)


class TestPortfolioPerformanceAnalyzer:
    """Test cases for PortfolioPerformanceAnalyzer class."""

    @pytest.fixture
    def temp_db_path(self) -> Generator[str, Any, None]:
        """Create a temporary database path for testing."""
        yield ":memory:"

    @pytest.fixture
    def tracker(self, temp_db_path: str) -> AirdropTracker:
        """Create a tracker instance with temporary database."""
        return AirdropTracker(db_path=temp_db_path)

    @pytest.fixture
    def roi_optimizer(self, tracker: AirdropTracker) -> ROIOptimizer:
        """Create an ROI optimizer instance."""
        return ROIOptimizer(tracker)

    @pytest.fixture
    def analyzer(
        self, tracker: AirdropTracker, roi_optimizer: ROIOptimizer
    ) -> PortfolioPerformanceAnalyzer:
        """Create a portfolio analyzer instance."""
        return PortfolioPerformanceAnalyzer(tracker, roi_optimizer)

    @pytest.fixture
    def sample_events(self) -> list[AirdropEvent]:
        """Create sample airdrop events for testing."""
        base_date = datetime.now()
        return [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("100"),
                estimated_value_usd=Decimal("500.50"),
                transaction_hash=(
                    "0x1234567890abcdef1234567890abcdef"
                    "1234567890abcdef1234567890abcdef"
                ),
                block_number=12345,
                event_date=base_date,
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                notes=None
            ),
            AirdropEvent(
                protocol_name="Arbitrum",
                token_symbol="ARB",
                amount_received=Decimal("200"),
                estimated_value_usd=Decimal("800.00"),
                transaction_hash=(
                    "0xabcdef1234567890abcdef1234567890"
                    "abcdef1234567890abcdef1234567890"
                ),
                block_number=12346,
                event_date=base_date + timedelta(days=1),
                wallet_address="0x8ba1f109551bD432803012645aac136c22C57592",
                notes=None
            ),
            AirdropEvent(
                protocol_name="Optimism",
                token_symbol="OP",
                amount_received=Decimal("150"),
                estimated_value_usd=Decimal("1301.00"),
                transaction_hash=(
                    "0x567890abcdef1234567890abcdef1234"
                    "567890abcdef1234567890abcdef1234"
                ),
                block_number=12347,
                event_date=base_date + timedelta(days=2),
                wallet_address="0x1234567890123456789012345678901234567890",
                notes=None
            )
        ]

    def test_analyzer_initialization(self, tracker: AirdropTracker) -> None:
        """Test portfolio analyzer initialization."""
        analyzer = PortfolioPerformanceAnalyzer(tracker)
        assert analyzer.tracker == tracker
        assert analyzer.roi_optimizer is None
        assert analyzer._price_cache == {}

    def test_analyzer_initialization_with_roi_optimizer(
        self, tracker: AirdropTracker, roi_optimizer: ROIOptimizer
    ) -> None:
        """Test portfolio analyzer initialization with ROI optimizer."""
        analyzer = PortfolioPerformanceAnalyzer(tracker, roi_optimizer)
        assert analyzer.tracker == tracker
        assert analyzer.roi_optimizer == roi_optimizer

    def test_calculate_portfolio_metrics_empty(
        self, analyzer: PortfolioPerformanceAnalyzer
    ) -> None:
        """Test portfolio metrics calculation with no data."""
        metrics = analyzer.calculate_portfolio_metrics(
            capital_allocation={},
            current_prices={}
        )

        assert metrics.total_portfolio_value_usd == Decimal('0')
        assert metrics.total_profit_loss_usd == Decimal('0')
        assert metrics.portfolio_roi_percentage == Decimal('0')
        assert metrics.token_count == 0
        assert metrics.diversification_index == Decimal('0')
        assert metrics.largest_position_percentage == Decimal('0')

    def test_calculate_portfolio_metrics_with_data(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test portfolio metrics calculation with sample data."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        metrics = analyzer.calculate_portfolio_metrics(
            capital_allocation={"Uniswap": Decimal("500.50")},
            current_prices={"Uniswap": Decimal("1.0")}
        )

        # Check basic calculations - only first event is recorded due to constraints
        expected_total_value = Decimal("500.50")  # First event value
        assert metrics.total_portfolio_value_usd == expected_total_value

        assert metrics.token_count == 3
        assert metrics.diversification_index == Decimal('0')  # Single position

    def test_calculate_portfolio_value_over_time(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test portfolio value calculation over time."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        # Calculate value over time with daily intervals
        snapshots = analyzer.calculate_portfolio_value_over_time(
            start_date=datetime.now() - timedelta(days=5),
            end_date=datetime.now(),
            interval_days=1
        )

        assert len(snapshots) > 0
        assert all(
            isinstance(snapshot, PortfolioSnapshot)
            for snapshot in snapshots
        )

        # Check that snapshots are ordered by timestamp
        timestamps = [s.snapshot_date for s in snapshots]
        assert timestamps == sorted(timestamps)

    def test_calculate_portfolio_value_over_time_no_events(
        self, analyzer: PortfolioPerformanceAnalyzer
    ) -> None:
        """Test portfolio value calculation with no events."""
        snapshots = analyzer.calculate_portfolio_value_over_time(
            start_date=datetime.now() - timedelta(days=5),
            end_date=datetime.now(),
            interval_days=1
        )

        # With no events, no snapshots are generated
        assert len(snapshots) == 0

    def test_compare_to_benchmark_eth(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test benchmark comparison with ETH."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        comparison = analyzer.compare_to_benchmark(BenchmarkType.ETH)

        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.benchmark_type == BenchmarkType.ETH
        assert comparison.portfolio_return_percentage is not None
        assert comparison.benchmark_return_percentage is not None

    def test_compare_to_benchmark_btc(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test benchmark comparison with BTC."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        comparison = analyzer.compare_to_benchmark(BenchmarkType.BTC)

        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.benchmark_type == BenchmarkType.BTC

    def test_compare_to_benchmark_market_index(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test benchmark comparison with market index."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        comparison = analyzer.compare_to_benchmark(
            BenchmarkType.MARKET_INDEX
        )

        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.benchmark_type == BenchmarkType.MARKET_INDEX

    def test_calculate_diversification_index(
        self, analyzer: PortfolioPerformanceAnalyzer
    ) -> None:
        """Test diversification index calculation."""
        # Test with empty portfolio
        index = analyzer._calculate_diversification_index({})
        assert index == Decimal('0')

        # Test with single position
        positions = {"UNI": Decimal("100")}
        index = analyzer._calculate_diversification_index(positions)
        assert index == Decimal('0')  # Single position = no diversification

        # Test with multiple equal positions
        positions = {
            "UNI": Decimal("100"),
            "ARB": Decimal("100"),
            "OP": Decimal("100")
        }
        index = analyzer._calculate_diversification_index(positions)
        # HHI = 3 * (1/3)^2 = 1/3, so diversification = 1 - 1/3 = 2/3
        expected = Decimal('1') - Decimal('1') / Decimal('3')
        assert abs(index - expected) < Decimal("0.01")

    def test_calculate_value_at_risk(
        self, analyzer: PortfolioPerformanceAnalyzer
    ) -> None:
        """Test Value at Risk calculation."""
        # Test with zero diversification
        var = analyzer._calculate_value_at_risk(
            Decimal("1000"), Decimal("0")
        )
        expected_var = Decimal("1000") * Decimal("0.20")  # 20% base risk
        assert var == expected_var

        # Test with full diversification
        var = analyzer._calculate_value_at_risk(
            Decimal("1000"), Decimal("1")
        )
        expected_var = Decimal("1000") * Decimal("0.10")  # 10% reduced risk
        assert var == expected_var

    def test_roi_optimizer_integration(
        self, analyzer: PortfolioPerformanceAnalyzer,
        sample_events: list[AirdropEvent]
    ) -> None:
        """Test integration with ROI optimizer for cost calculations."""
        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        # Mock ROI optimizer response - should return list of ROI objects
        mock_roi_data = [
            type('ROI', (), {'total_cost_usd': Decimal('50.0')})(),
            type('ROI', (), {'total_cost_usd': Decimal('50.0')})()
        ]

        with patch.object(
            analyzer.roi_optimizer,
            'calculate_portfolio_roi',
            return_value=mock_roi_data
        ):
            metrics = analyzer.calculate_portfolio_metrics(
                capital_allocation={
                    "Uniswap": Decimal("500.50"),
                    "Arbitrum": Decimal("800.00")
                },
                current_prices={"Uniswap": Decimal("1.0"), "Arbitrum": Decimal("1.0")}
            )

            # Should use ROI optimizer's cost calculation (sum of all ROI costs)
            assert metrics.total_cost_usd == Decimal("100.00")

    def test_fallback_cost_calculation(
        self, tracker: AirdropTracker, sample_events: list[AirdropEvent]
    ) -> None:
        """Test fallback cost calculation when ROI optimizer fails."""
        analyzer = PortfolioPerformanceAnalyzer(tracker)  # No ROI optimizer

        # Add events to tracker
        for event in sample_events:
            analyzer.tracker.record_airdrop(event)

        metrics = analyzer.calculate_portfolio_metrics(
            capital_allocation={"Uniswap": Decimal("500.50")},
            current_prices={"Uniswap": Decimal("1.0")}
        )

        # Should use fallback cost calculation
        # (number of events * default gas cost)
        # Note: The sample_events fixture provides 3 events,
        # so the expected cost is 3 * $5.
        expected_cost = Decimal("15.0")  # 3 events * $5
        assert metrics.total_cost_usd == expected_cost


class TestPortfolioMetrics:
    """Test cases for PortfolioMetrics model."""

    def test_portfolio_metrics_creation(self) -> None:
        """Test PortfolioMetrics model creation."""
        metrics = PortfolioMetrics(
            calculation_date=datetime.now(),
            total_portfolio_value_usd=Decimal("1000.00"),
            total_profit_loss_usd=Decimal("200.00"),
            total_cost_usd=Decimal("800.00"),
            portfolio_roi_percentage=Decimal("25.00"),
            protocol_count=3,
            token_count=5,
            diversification_index=Decimal("0.75"),
            largest_position_percentage=Decimal("30.00"),
            value_at_risk_usd=Decimal("150.00")
        )

        assert metrics.total_portfolio_value_usd == Decimal("1000.00")
        assert metrics.total_profit_loss_usd == Decimal("200.00")
        assert metrics.portfolio_roi_percentage == Decimal("25.00")
        assert metrics.token_count == 5
        assert metrics.diversification_index == Decimal("0.75")
        assert metrics.largest_position_percentage == Decimal("30.00")
        assert metrics.value_at_risk_usd == Decimal("150.00")


class TestPortfolioSnapshot:
    """Test cases for PortfolioSnapshot model."""

    def test_portfolio_snapshot_creation(self) -> None:
        """Test PortfolioSnapshot model creation."""
        snapshot_date = datetime.now()
        snapshot = PortfolioSnapshot(
            snapshot_date=snapshot_date,
            total_value_usd=Decimal("1500.00"),
            protocol_allocations={
                "Uniswap": Decimal("500.00"),
                "Arbitrum": Decimal("400.00")
            },
            token_allocations={
                "UNI": Decimal("500.00"),
                "ARB": Decimal("400.00")
            },
            diversification_score=Decimal("0.75")
        )

        assert snapshot.snapshot_date == snapshot_date
        assert snapshot.total_value_usd == Decimal("1500.00")
        assert len(snapshot.protocol_allocations) == 2
        assert len(snapshot.token_allocations) == 2


class TestBenchmarkComparison:
    """Test cases for BenchmarkComparison model."""

    def test_benchmark_comparison_creation(self) -> None:
        """Test BenchmarkComparison model creation."""
        comparison = BenchmarkComparison(
            benchmark_type=BenchmarkType.ETH,
            portfolio_return_percentage=Decimal("15.50"),
            benchmark_return_percentage=Decimal("12.00"),
            alpha_percentage=Decimal("3.50"),
            comparison_period_days=30,
            calculation_date=datetime.now()
        )

        assert comparison.benchmark_type == BenchmarkType.ETH
        assert comparison.portfolio_return_percentage == Decimal("15.50")
        assert comparison.benchmark_return_percentage == Decimal("12.00")
        assert comparison.alpha_percentage == Decimal("3.50")
        assert comparison.comparison_period_days == 30
