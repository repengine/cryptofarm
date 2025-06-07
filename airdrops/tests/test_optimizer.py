"""
Tests for the ROI optimizer module.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Generator, List
from unittest.mock import patch

from airdrops.analytics.tracker import AirdropTracker, AirdropEvent
from airdrops.analytics.optimizer import (
    ROIOptimizer,
    ROIMetrics,
    OptimizationSuggestion,
    CostData,
    CostModel,
    OptimizationStrategy
)


class TestROIOptimizer:
    """Test cases for ROIOptimizer class."""

    @pytest.fixture
    def temp_db_path(self) -> Generator[str, Any, None]:
        """Create a temporary database path for testing."""
        yield ":memory:"

    @pytest.fixture
    def tracker(self, temp_db_path: str) -> AirdropTracker:
        """Create a tracker instance with temporary database."""
        return AirdropTracker(db_path=temp_db_path)

    @pytest.fixture
    def optimizer(self, tracker: AirdropTracker) -> ROIOptimizer:
        """Create an optimizer instance."""
        return ROIOptimizer(tracker, default_gas_cost_usd=Decimal("5.0"))

    @pytest.fixture
    def sample_events(self) -> List[AirdropEvent]:
        """Create sample airdrop events for testing."""
        base_date = datetime.now()
        return [
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("400"),
                estimated_value_usd=Decimal("1200.50"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=base_date - timedelta(days=30),
                transaction_hash=None,
                block_number=None,
                notes=None,
            ),
            AirdropEvent(
                protocol_name="Arbitrum",
                token_symbol="ARB",
                amount_received=Decimal("1000"),
                estimated_value_usd=Decimal("800.00"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=base_date - timedelta(days=15),
                transaction_hash=None,
                block_number=None,
                notes=None,
            ),
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("200"),
                estimated_value_usd=Decimal("600.25"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=base_date - timedelta(days=10),
                transaction_hash=None,
                block_number=None,
                notes=None,
            )
        ]

    def test_optimizer_initialization(self, tracker: AirdropTracker) -> None:
        """Test optimizer initialization."""
        optimizer = ROIOptimizer(
            tracker,
            default_gas_cost_usd=Decimal("10.0"),
            cost_model=CostModel.MANUAL_INPUT
        )

        assert optimizer.tracker == tracker
        assert optimizer.default_gas_cost_usd == Decimal("10.0")
        assert optimizer.cost_model == CostModel.MANUAL_INPUT
        assert len(optimizer._cost_data_cache) == 0

    def test_set_protocol_cost_data(self, optimizer: ROIOptimizer) -> None:
        """Test setting protocol cost data."""
        cost_data = CostData(
            protocol_name="Uniswap",
            total_gas_cost_usd=Decimal("150.0"),
            transaction_count=30,
            average_gas_cost_usd=Decimal("5.0"),
            manual_cost_usd=None,
            time_investment_hours=None
        )

        optimizer.set_protocol_cost_data(cost_data)

        assert "Uniswap" in optimizer._cost_data_cache
        assert optimizer._cost_data_cache["Uniswap"] == cost_data

    def test_calculate_protocol_roi_success(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test successful protocol ROI calculation."""
        # Record sample events
        for event in sample_events:
            optimizer.tracker.record_airdrop(event)

        # Set cost data for Uniswap
        cost_data = CostData(
            protocol_name="Uniswap",
            total_gas_cost_usd=Decimal("50.0"),
            transaction_count=2,
            average_gas_cost_usd=None,
            manual_cost_usd=None,
            time_investment_hours=None
        )
        optimizer.set_protocol_cost_data(cost_data)

        roi_metrics = optimizer.calculate_protocol_roi("Uniswap")

        assert isinstance(roi_metrics, ROIMetrics)
        assert roi_metrics.protocol_name == "Uniswap"
        assert roi_metrics.total_revenue_usd == Decimal("1800.75")  # 1200.50 + 600.25
        assert roi_metrics.total_cost_usd == Decimal("50.0")
        assert roi_metrics.profit_usd == Decimal("1750.75")
        assert roi_metrics.roi_percentage == Decimal("3501.5")  # (1750.75 / 50) * 100
        assert roi_metrics.transaction_count == 2

    def test_calculate_protocol_roi_no_events(self, optimizer: ROIOptimizer) -> None:
        """Test ROI calculation for protocol with no events."""
        with pytest.raises(RuntimeError, match="ROI calculation failed"):
            optimizer.calculate_protocol_roi("NonExistent")

    def test_calculate_protocol_roi_date_range(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test ROI calculation with date range filter."""
        # Record sample events
        for event in sample_events:
            optimizer.tracker.record_airdrop(event)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=20)

        roi_metrics = optimizer.calculate_protocol_roi("Uniswap", start_date, end_date)

        # Should only include the recent Uniswap event
        assert roi_metrics.transaction_count == 1
        assert roi_metrics.total_revenue_usd == Decimal("600.25")

    def test_calculate_portfolio_roi_success(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test successful portfolio ROI calculation."""
        # Record sample events
        for event in sample_events:
            optimizer.tracker.record_airdrop(event)

        portfolio_roi = optimizer.calculate_portfolio_roi()

        assert len(portfolio_roi) == 2  # Uniswap and Arbitrum
        assert all(isinstance(roi, ROIMetrics) for roi in portfolio_roi)

        # Should be sorted by ROI percentage (descending)
        assert portfolio_roi[0].roi_percentage >= portfolio_roi[1].roi_percentage

        # Check protocol names
        protocol_names = {roi.protocol_name for roi in portfolio_roi}
        assert protocol_names == {"Uniswap", "Arbitrum"}

    def test_calculate_portfolio_roi_empty(self, optimizer: ROIOptimizer) -> None:
        """Test portfolio ROI calculation with no events."""
        portfolio_roi = optimizer.calculate_portfolio_roi()
        assert len(portfolio_roi) == 0

    def test_generate_optimization_suggestions_roi_maximization(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test optimization suggestions for ROI maximization strategy."""
        # Record sample events
        for event in sample_events:
            optimizer.tracker.record_airdrop(event)

        suggestions = optimizer.generate_optimization_suggestions(
            strategy=OptimizationStrategy.ROI_MAXIMIZATION,
            min_roi_threshold=Decimal("100.0")
        )

        assert len(suggestions) > 0
        assert all(isinstance(s, OptimizationSuggestion) for s in suggestions)

        # Should have suggestions for both high and low performers
        suggestion_types = {s.suggestion_type for s in suggestions}
        assert "focus_allocation" in suggestion_types or "reduce_allocation" in suggestion_types  # noqa: E501

    def test_generate_optimization_suggestions_risk_adjusted(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test optimization suggestions for risk-adjusted strategy."""
        # Record sample events
        for event in sample_events:
            optimizer.tracker.record_airdrop(event)

        suggestions = optimizer.generate_optimization_suggestions(
            strategy=OptimizationStrategy.RISK_ADJUSTED
        )

        assert isinstance(suggestions, list)
        # Risk-adjusted strategy may have fewer suggestions
        assert all(isinstance(s, OptimizationSuggestion) for s in suggestions)

    def test_generate_optimization_suggestions_diversified(
        self, optimizer: ROIOptimizer, sample_events: List[AirdropEvent]
    ) -> None:
        """Test optimization suggestions for diversified strategy."""
        # Record only one protocol to trigger diversification suggestions
        optimizer.tracker.record_airdrop(sample_events[0])

        suggestions = optimizer.generate_optimization_suggestions(
            strategy=OptimizationStrategy.DIVERSIFIED
        )

        assert len(suggestions) > 0
        # Should suggest diversification
        diversification_suggestions = [
            s for s in suggestions if s.suggestion_type == "diversification"
        ]
        assert len(diversification_suggestions) > 0

    def test_calculate_protocol_costs_with_cache(self, optimizer: ROIOptimizer) -> None:
        """Test cost calculation with cached cost data."""
        cost_data = CostData(
            protocol_name="Uniswap",
            total_gas_cost_usd=Decimal("100.0"),
            transaction_count=20,
            average_gas_cost_usd=None,
            manual_cost_usd=None,
            time_investment_hours=None
        )
        optimizer.set_protocol_cost_data(cost_data)

        cost = optimizer._calculate_protocol_costs("Uniswap", 20)
        assert cost == Decimal("100.0")

    def test_calculate_protocol_costs_manual_input(self, optimizer: ROIOptimizer) -> None:  # noqa: E501
        """Test cost calculation with manual input model."""
        optimizer.cost_model = CostModel.MANUAL_INPUT
        cost_data = CostData(
            protocol_name="Uniswap",
            manual_cost_usd=Decimal("200.0"),
            total_gas_cost_usd=Decimal("100.0"),  # Should be ignored
            transaction_count=0,  # Add missing required argument
            average_gas_cost_usd=None,
            time_investment_hours=None
        )
        optimizer.set_protocol_cost_data(cost_data)

        cost = optimizer._calculate_protocol_costs("Uniswap", 20)
        assert cost == Decimal("200.0")

    def test_calculate_protocol_costs_average_gas(self, optimizer: ROIOptimizer) -> None:  # noqa: E501
        """Test cost calculation with average gas cost."""
        cost_data = CostData(
            protocol_name="Uniswap",
            average_gas_cost_usd=Decimal("7.5"),
            transaction_count=10,
            total_gas_cost_usd=None,
            manual_cost_usd=None,
            time_investment_hours=None
        )
        optimizer.set_protocol_cost_data(cost_data)

        cost = optimizer._calculate_protocol_costs("Uniswap", 20)
        assert cost == Decimal("150.0")  # 7.5 * 20

    def test_calculate_protocol_costs_default(self, optimizer: ROIOptimizer) -> None:
        """Test cost calculation with default gas cost."""
        cost = optimizer._calculate_protocol_costs("UnknownProtocol", 10)
        assert cost == Decimal("50.0")  # 5.0 * 10

    def test_roi_calculation_error_handling(self, optimizer: ROIOptimizer) -> None:
        """Test error handling during ROI calculation."""
        with patch.object(optimizer.tracker, 'get_airdrops_by_protocol') as mock_get:
            mock_get.side_effect = Exception("Database error")

            with pytest.raises(RuntimeError, match="ROI calculation failed"):
                optimizer.calculate_protocol_roi("Uniswap")

    def test_portfolio_roi_calculation_error_handling(self, optimizer: ROIOptimizer) -> None:  # noqa: E501
        """Test error handling during portfolio ROI calculation."""
        with patch.object(optimizer.tracker, 'get_airdrops_by_date_range') as mock_get:
            mock_get.side_effect = Exception("Database error")

            with pytest.raises(RuntimeError, match="Portfolio ROI calculation failed"):
                optimizer.calculate_portfolio_roi()

    def test_optimization_suggestions_error_handling(self, optimizer: ROIOptimizer) -> None:  # noqa: E501
        """Test error handling during optimization suggestion generation."""
        with patch.object(optimizer, 'calculate_portfolio_roi') as mock_calc:
            mock_calc.side_effect = Exception("Calculation error")

            with pytest.raises(RuntimeError, match="Optimization suggestion generation failed"):  # noqa: E501
                optimizer.generate_optimization_suggestions()

    def test_roi_maximization_suggestions_logic(self, optimizer: ROIOptimizer) -> None:
        """Test the logic of ROI maximization suggestions."""
        # Create mock ROI metrics
        high_roi = ROIMetrics(
            protocol_name="HighROI",
            total_revenue_usd=Decimal("1000"),
            total_cost_usd=Decimal("100"),
            roi_percentage=Decimal("900"),
            profit_usd=Decimal("900"),
            transaction_count=10,
            revenue_per_transaction=Decimal("100"),
            cost_per_transaction=Decimal("10"),
            calculation_date=datetime.now()
        )

        low_roi = ROIMetrics(
            protocol_name="LowROI",
            total_revenue_usd=Decimal("100"),
            total_cost_usd=Decimal("200"),
            roi_percentage=Decimal("-50"),
            profit_usd=Decimal("-100"),
            transaction_count=5,
            revenue_per_transaction=Decimal("20"),
            cost_per_transaction=Decimal("40"),
            calculation_date=datetime.now()
        )

        suggestions = optimizer._generate_roi_maximization_suggestions(
            [high_roi, low_roi], Decimal("100")
        )

        assert len(suggestions) >= 2

        # Should suggest focusing on high performer
        focus_suggestions = [s for s in suggestions if s.suggestion_type == "focus_allocation"]  # noqa: E501
        assert len(focus_suggestions) == 1
        assert focus_suggestions[0].protocol_name == "HighROI"

        # Should suggest reducing low performer
        reduce_suggestions = [s for s in suggestions if s.suggestion_type == "reduce_allocation"]  # noqa: E501
        assert len(reduce_suggestions) == 1
        assert reduce_suggestions[0].protocol_name == "LowROI"

    def test_diversification_suggestions_logic(self, optimizer: ROIOptimizer) -> None:
        """Test the logic of diversification suggestions."""
        # Test with insufficient protocols
        roi_metrics = [
            ROIMetrics(
                protocol_name="OnlyProtocol",
                total_revenue_usd=Decimal("1000"),
                total_cost_usd=Decimal("100"),
                roi_percentage=Decimal("900"),
                profit_usd=Decimal("900"),
                transaction_count=100,  # High concentration
                revenue_per_transaction=Decimal("10"),
                cost_per_transaction=Decimal("1"),
                calculation_date=datetime.now()
            )
        ]

        suggestions = optimizer._generate_diversification_suggestions(roi_metrics)

        # Should suggest diversification
        diversification_suggestions = [
            s for s in suggestions if s.suggestion_type == "diversification"
        ]
        assert len(diversification_suggestions) == 1

        # Test with over-concentration
        roi_metrics = [
            ROIMetrics(
                protocol_name="Concentrated",
                total_revenue_usd=Decimal("1000"),
                total_cost_usd=Decimal("100"),
                roi_percentage=Decimal("900"),
                profit_usd=Decimal("900"),
                transaction_count=60,  # 60% of total
                revenue_per_transaction=Decimal("16.67"),
                cost_per_transaction=Decimal("1.67"),
                calculation_date=datetime.now()
            ),
            ROIMetrics(
                protocol_name="Other",
                total_revenue_usd=Decimal("500"),
                total_cost_usd=Decimal("50"),
                roi_percentage=Decimal("900"),
                profit_usd=Decimal("450"),
                transaction_count=40,  # 40% of total
                revenue_per_transaction=Decimal("12.5"),
                cost_per_transaction=Decimal("1.25"),
                calculation_date=datetime.now()
            )
        ]

        suggestions = optimizer._generate_diversification_suggestions(roi_metrics)

        # Should suggest reducing concentration
        concentration_suggestions = [
            s for s in suggestions if s.suggestion_type == "reduce_concentration"
        ]
        assert len(concentration_suggestions) == 1
        assert concentration_suggestions[0].protocol_name == "Concentrated"
