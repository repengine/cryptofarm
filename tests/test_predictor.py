"""
Tests for the Airdrop Predictor module.

This module contains comprehensive tests for the predictive analytics functionality,
including data ingestion stubs, heuristic models, and prediction output validation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from airdrops.analytics.predictor import (
    AirdropPredictor,
    PredictionResult,
    PredictionWindow,
    PredictionConfidence,
    DataSourceType,
    MarketDataStub,
    OnChainActivityStub,
    SocialSentimentStub
)
from airdrops.analytics.tracker import AirdropTracker, AirdropEvent


class TestPredictionWindow:
    """Test cases for PredictionWindow model."""

    def test_valid_prediction_window(self):
        """Test creating a valid prediction window."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        window = PredictionWindow(
            start_date=start,
            end_date=end,
            probability=Decimal("0.7")
        )

        assert window.start_date == start
        assert window.end_date == end
        assert window.probability == Decimal("0.7")

    def test_invalid_end_date_before_start(self):
        """Test validation error when end_date is before start_date."""
        start = datetime(2024, 1, 31)
        end = datetime(2024, 1, 1)

        with pytest.raises(ValueError, match="end_date must be after start_date"):
            PredictionWindow(
                start_date=start,
                end_date=end,
                probability=Decimal("0.5")
            )

    def test_probability_bounds_validation(self):
        """Test probability validation bounds."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        # Test valid probabilities
        for prob in ["0.0", "0.5", "1.0"]:
            window = PredictionWindow(
                start_date=start,
                end_date=end,
                probability=Decimal(prob)
            )
            assert window.probability == Decimal(prob)

        # Test invalid probabilities
        with pytest.raises(ValueError):
            PredictionWindow(
                start_date=start,
                end_date=end,
                probability=Decimal("-0.1")
            )

        with pytest.raises(ValueError):
            PredictionWindow(
                start_date=start,
                end_date=end,
                probability=Decimal("1.1")
            )


class TestPredictionResult:
    """Test cases for PredictionResult model."""

    def test_valid_prediction_result(self):
        """Test creating a valid prediction result."""
        window = PredictionWindow(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            probability=Decimal("0.6")
        )

        result = PredictionResult(
            protocol_name="Uniswap",
            prediction_windows=[window],
            confidence_level=PredictionConfidence.MEDIUM,
            model_version="1.0.0",
            data_sources_used=[DataSourceType.HISTORICAL_AIRDROPS],
            next_review_date=datetime(2024, 2, 1)
        )

        assert result.protocol_name == "Uniswap"
        assert len(result.prediction_windows) == 1
        assert result.confidence_level == PredictionConfidence.MEDIUM
        assert result.model_version == "1.0.0"
        assert DataSourceType.HISTORICAL_AIRDROPS in result.data_sources_used

    def test_protocol_name_validation(self):
        """Test protocol name validation and normalization."""
        window = PredictionWindow(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            probability=Decimal("0.6")
        )

        # Test normalization
        result = PredictionResult(
            protocol_name="  uniswap  ",
            prediction_windows=[window],
            confidence_level=PredictionConfidence.MEDIUM,
            model_version="1.0.0",
            data_sources_used=[DataSourceType.HISTORICAL_AIRDROPS],
            next_review_date=datetime(2024, 2, 1)
        )
        assert result.protocol_name == "Uniswap"

        # Test empty protocol name
        with pytest.raises(ValueError, match="Protocol name cannot be empty"):
            PredictionResult(
                protocol_name="   ",
                prediction_windows=[window],
                confidence_level=PredictionConfidence.MEDIUM,
                model_version="1.0.0",
                data_sources_used=[DataSourceType.HISTORICAL_AIRDROPS],
                next_review_date=datetime(2024, 2, 1)
            )


class TestDataStubs:
    """Test cases for data source stub implementations."""

    def test_market_data_stub(self):
        """Test MarketDataStub functionality."""
        stub = MarketDataStub()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        df = stub.get_token_price_history("ETH", start_date, end_date)

        assert df.empty
        assert list(df.columns) == ['timestamp', 'price', 'volume']

    def test_onchain_activity_stub(self):
        """Test OnChainActivityStub functionality."""
        stub = OnChainActivityStub()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        df = stub.get_protocol_activity_metrics("Uniswap", start_date, end_date)

        assert df.empty
        assert list(df.columns) == ['timestamp', 'tx_count', 'active_addresses']

    def test_social_sentiment_stub(self):
        """Test SocialSentimentStub functionality."""
        stub = SocialSentimentStub()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        df = stub.get_sentiment_score("Arbitrum", start_date, end_date)

        assert df.empty
        assert list(df.columns) == ['timestamp', 'sentiment_score', 'mention_count']


class TestAirdropPredictor:
    """Test cases for AirdropPredictor class."""

    @pytest.fixture
    def mock_tracker(self):
        """Create a mock AirdropTracker for testing."""
        return Mock(spec=AirdropTracker)

    @pytest.fixture
    def predictor(self, mock_tracker):
        """Create an AirdropPredictor instance for testing."""
        return AirdropPredictor(mock_tracker)

    def test_predictor_initialization(self, mock_tracker):
        """Test predictor initialization with default stubs."""
        predictor = AirdropPredictor(mock_tracker)

        assert predictor.tracker == mock_tracker
        assert isinstance(predictor.market_data, MarketDataStub)
        assert isinstance(predictor.onchain_data, OnChainActivityStub)
        assert isinstance(predictor.sentiment_data, SocialSentimentStub)
        assert predictor.model_version == "1.0.0-heuristic"

    def test_predictor_initialization_with_custom_stubs(self, mock_tracker):
        """Test predictor initialization with custom data sources."""
        market_stub = MarketDataStub()
        onchain_stub = OnChainActivityStub()
        sentiment_stub = SocialSentimentStub()

        predictor = AirdropPredictor(
            mock_tracker,
            market_data=market_stub,
            onchain_data=onchain_stub,
            sentiment_data=sentiment_stub
        )

        assert predictor.market_data == market_stub
        assert predictor.onchain_data == onchain_stub
        assert predictor.sentiment_data == sentiment_stub

    def test_predict_airdrop_timing_no_historical_data(self, predictor, mock_tracker):
        """Test prediction with no historical data."""
        mock_tracker.get_airdrops_by_protocol.return_value = []

        result = predictor.predict_airdrop_timing("NewProtocol")

        assert result.protocol_name == "Newprotocol"
        assert len(result.prediction_windows) == 3  # Default windows
        assert result.confidence_level == PredictionConfidence.LOW
        assert result.model_version == "1.0.0-heuristic"
        assert DataSourceType.HISTORICAL_AIRDROPS in result.data_sources_used
        assert result.metadata["historical_events_count"] == 0

    def test_predict_airdrop_timing_single_historical_event(
        self, predictor, mock_tracker
    ):
        """Test prediction with single historical event."""
        historical_event = Mock()
        historical_event.event_date = datetime(2023, 6, 1)
        mock_tracker.get_airdrops_by_protocol.return_value = [historical_event]

        result = predictor.predict_airdrop_timing("SingleEventProtocol")

        assert result.protocol_name == "Singleeventprotocol"
        assert len(result.prediction_windows) == 1
        assert result.confidence_level == PredictionConfidence.MEDIUM
        assert result.prediction_windows[0].probability == Decimal("0.4")
        assert result.metadata["historical_events_count"] == 1

    def test_predict_airdrop_timing_multiple_historical_events(
        self, predictor, mock_tracker
    ):
        """Test prediction with multiple historical events."""
        event1 = Mock()
        event1.event_date = datetime(2023, 1, 1)
        event2 = Mock()
        event2.event_date = datetime(2023, 7, 1)  # 6 months later

        mock_tracker.get_airdrops_by_protocol.return_value = [event1, event2]

        result = predictor.predict_airdrop_timing("MultiEventProtocol")

        assert result.protocol_name == "Multieventprotocol"
        assert len(result.prediction_windows) == 1
        assert result.confidence_level == PredictionConfidence.MEDIUM
        assert result.prediction_windows[0].probability == Decimal("0.6")
        assert result.metadata["historical_events_count"] == 2

    def test_predict_airdrop_timing_high_confidence(self, predictor, mock_tracker):
        """Test prediction with high confidence (3+ events)."""
        events = []
        for i in range(3):
            event = Mock()
            event.event_date = datetime(2023, 1 + i * 4, 1)  # Every 4 months
            events.append(event)

        mock_tracker.get_airdrops_by_protocol.return_value = events

        result = predictor.predict_airdrop_timing("HighConfidenceProtocol")

        assert result.confidence_level == PredictionConfidence.HIGH
        assert result.metadata["historical_events_count"] == 3

    def test_predict_airdrop_timing_invalid_protocol_name(self, predictor):
        """Test prediction with invalid protocol name."""
        with pytest.raises(ValueError, match="Protocol name cannot be empty"):
            predictor.predict_airdrop_timing("")

        with pytest.raises(ValueError, match="Protocol name cannot be empty"):
            predictor.predict_airdrop_timing("   ")

    def test_predict_airdrop_timing_tracker_exception(self, predictor, mock_tracker):
        """Test prediction when tracker raises exception."""
        mock_tracker.get_airdrops_by_protocol.side_effect = Exception("Database error")

        with pytest.raises(RuntimeError, match="Prediction generation failed"):
            predictor.predict_airdrop_timing("ErrorProtocol")

    def test_get_data_source_status(self, predictor):
        """Test data source status reporting."""
        status = predictor.get_data_source_status()

        expected_status = {
            "historical_airdrops": True,
            "market_data": False,
            "onchain_activity": False,
            "social_sentiment": False
        }

        assert status == expected_status

    def test_update_prediction_model(self, predictor):
        """Test updating prediction model version."""
        new_version = "2.0.0-ml"
        predictor.update_prediction_model(new_version)

        assert predictor.model_version == new_version

    def test_generate_default_prediction_windows(self, predictor):
        """Test default prediction window generation."""
        windows = predictor._generate_default_prediction_windows()

        assert len(windows) == 3
        assert all(isinstance(w, PredictionWindow) for w in windows)
        assert all(w.probability > 0 for w in windows)

        # Check that windows are in chronological order
        for i in range(1, len(windows)):
            assert windows[i].start_date > windows[i-1].start_date

    def test_calculate_confidence_level(self, predictor):
        """Test confidence level calculation."""
        # No events - LOW confidence
        confidence = predictor._calculate_confidence_level([])
        assert confidence == PredictionConfidence.LOW

        # 1-2 events - MEDIUM confidence
        events = [Mock() for _ in range(2)]
        confidence = predictor._calculate_confidence_level(events)
        assert confidence == PredictionConfidence.MEDIUM

        # 3+ events - HIGH confidence
        events = [Mock() for _ in range(3)]
        confidence = predictor._calculate_confidence_level(events)
        assert confidence == PredictionConfidence.HIGH

    def test_apply_heuristic_model_no_events(self, predictor):
        """Test heuristic model with no historical events."""
        windows = predictor._apply_heuristic_model("TestProtocol", [], 365)

        assert len(windows) == 3  # Default windows
        assert all(isinstance(w, PredictionWindow) for w in windows)

    def test_apply_heuristic_model_single_event(self, predictor):
        """Test heuristic model with single historical event."""
        event = Mock()
        event.event_date = datetime(2023, 1, 1)

        windows = predictor._apply_heuristic_model("TestProtocol", [event], 365)

        assert len(windows) == 1
        assert windows[0].probability == Decimal("0.4")
        # Should predict 6-12 months after last event
        expected_date = event.event_date + timedelta(days=150)
        assert windows[0].start_date > expected_date

    def test_apply_heuristic_model_multiple_events(self, predictor):
        """Test heuristic model with multiple historical events."""
        event1 = Mock()
        event1.event_date = datetime(2023, 1, 1)
        event2 = Mock()
        event2.event_date = datetime(2023, 7, 1)  # 6 months later

        events = [event1, event2]
        windows = predictor._apply_heuristic_model("TestProtocol", events, 365)

        assert len(windows) == 1
        assert windows[0].probability == Decimal("0.6")
        # Should predict based on average interval (6 months)
        expected_start = event2.event_date + timedelta(days=int(180 * 0.8))
        expected_end = event2.event_date + timedelta(days=int(180 * 1.2))

        # Allow some tolerance for calculation differences
        assert abs((windows[0].start_date - expected_start).days) <= 1
        assert abs((windows[0].end_date - expected_end).days) <= 1


class TestEnums:
    """Test cases for enum classes."""

    def test_data_source_type_values(self):
        """Test DataSourceType enum values."""
        assert DataSourceType.HISTORICAL_AIRDROPS.value == "historical_airdrops"
        assert DataSourceType.MARKET_DATA.value == "market_data"
        assert DataSourceType.ONCHAIN_ACTIVITY.value == "onchain_activity"
        assert DataSourceType.SOCIAL_SENTIMENT.value == "social_sentiment"

    def test_prediction_confidence_values(self):
        """Test PredictionConfidence enum values."""
        assert PredictionConfidence.LOW.value == "low"
        assert PredictionConfidence.MEDIUM.value == "medium"
        assert PredictionConfidence.HIGH.value == "high"


class TestIntegration:
    """Integration tests for the predictor module."""

    def test_end_to_end_prediction_workflow(self):
        """Test complete prediction workflow with real tracker."""
        # Create real tracker with in-memory database
        tracker = AirdropTracker(":memory:")

        # Add some historical events
        event1 = AirdropEvent(
            protocol_name="TestProtocol",
            token_symbol="TEST",
            amount_received=Decimal("100"),
            estimated_value_usd=Decimal("500"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime(2023, 1, 1)
        )

        event2 = AirdropEvent(
            protocol_name="TestProtocol",
            token_symbol="TEST",
            amount_received=Decimal("200"),
            estimated_value_usd=Decimal("1000"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime(2023, 7, 1)
        )

        tracker.record_airdrop(event1)
        tracker.record_airdrop(event2)

        # Create predictor and generate prediction
        predictor = AirdropPredictor(tracker)
        result = predictor.predict_airdrop_timing("TestProtocol")

        # Verify prediction result
        assert result.protocol_name == "Testprotocol"
        assert len(result.prediction_windows) == 1
        assert result.confidence_level == PredictionConfidence.MEDIUM
        assert result.metadata["historical_events_count"] == 2

        # Verify prediction window is reasonable
        window = result.prediction_windows[0]
        assert window.start_date > datetime(2023, 7, 1)
        assert window.end_date > window.start_date
        assert 0 < window.probability <= 1

    def test_prediction_with_custom_lookback_days(self):
        """Test prediction with custom lookback period."""
        tracker = AirdropTracker(":memory:")
        predictor = AirdropPredictor(tracker)

        result = predictor.predict_airdrop_timing("NewProtocol", lookback_days=180)

        assert result.metadata["lookback_days"] == 180
        assert result.confidence_level == PredictionConfidence.LOW  # No historical data
