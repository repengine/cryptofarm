"""
Airdrop Predictive Analytics Module.

This module provides foundational predictive analytics capabilities for airdrop timing
predictions. It includes data ingestion stubs, basic heuristic models, and prediction
output structures for future machine learning integration.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from airdrops.analytics.tracker import AirdropTracker

# Configure logging
logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Enumeration of data source types for prediction models."""
    HISTORICAL_AIRDROPS = "historical_airdrops"
    MARKET_DATA = "market_data"
    ONCHAIN_ACTIVITY = "onchain_activity"
    SOCIAL_SENTIMENT = "social_sentiment"


class PredictionConfidence(Enum):
    """Enumeration of prediction confidence levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PredictionWindow(BaseModel):
    """Model representing a predicted time window for airdrop events."""
    start_date: datetime = Field(..., description="Start of prediction window")
    end_date: datetime = Field(..., description="End of prediction window")
    probability: Decimal = Field(..., ge=0, le=1, description="Probability score")

    @field_validator('end_date')
    def validate_end_after_start(cls, v: datetime, info: Any) -> datetime:
        """Validate that end_date is after start_date."""
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v


class PredictionResult(BaseModel):
    """Model representing a complete airdrop timing prediction."""
    protocol_name: str = Field(..., min_length=1, max_length=100)
    prediction_windows: List[PredictionWindow] = Field(..., description="Prediction windows", min_length=1)
    confidence_level: PredictionConfidence
    model_version: str = Field(..., description="Version of prediction model used")
    data_sources_used: List[DataSourceType]
    prediction_date: datetime = Field(default_factory=datetime.now)
    next_review_date: datetime
    metadata: Optional[Dict[str, Union[str, int, float]]] = Field(default=None)

    @field_validator('protocol_name')
    def validate_protocol_name(cls, v: str) -> str:
        """Validate and normalize protocol name."""
        if not v.strip():
            raise ValueError("Protocol name cannot be empty")
        return v.strip().title()


class MarketDataStub:
    """Stub interface for market data ingestion."""

    def get_token_price_history(
        self,
        token_symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical token price data (stub implementation).

        Args:
            token_symbol: Token symbol to fetch data for
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            DataFrame with price history (empty in stub)

        Example:
            >>> market_data = MarketDataStub()
            >>> df = market_data.get_token_price_history("ETH", start, end)
        """
        logger.info(f"Market data stub called for {token_symbol}")
        return pd.DataFrame(columns=['timestamp', 'price', 'volume'])


class OnChainActivityStub:
    """Stub interface for on-chain activity data ingestion."""

    def get_protocol_activity_metrics(
        self,
        protocol_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get on-chain activity metrics for a protocol (stub implementation).

        Args:
            protocol_name: Protocol to fetch metrics for
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            DataFrame with activity metrics (empty in stub)

        Example:
            >>> activity_data = OnChainActivityStub()
            >>> df = activity_data.get_protocol_activity_metrics("Uniswap", start, end)
        """
        logger.info(f"On-chain activity stub called for {protocol_name}")
        return pd.DataFrame(columns=['timestamp', 'tx_count', 'active_addresses'])


class SocialSentimentStub:
    """Stub interface for social sentiment data ingestion."""

    def get_sentiment_score(
        self,
        protocol_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get social sentiment scores for a protocol (stub implementation).

        Args:
            protocol_name: Protocol to analyze sentiment for
            start_date: Start date for sentiment analysis
            end_date: End date for sentiment analysis

        Returns:
            DataFrame with sentiment scores (empty in stub)

        Example:
            >>> sentiment_data = SocialSentimentStub()
            >>> df = sentiment_data.get_sentiment_score("Arbitrum", start, end)
        """
        logger.info(f"Social sentiment stub called for {protocol_name}")
        return pd.DataFrame(columns=['timestamp', 'sentiment_score', 'mention_count'])


class AirdropPredictor:
    """
    Airdrop timing prediction engine with foundational analytics capabilities.

    This class provides the foundation for predictive analytics on airdrop timing,
    including data ingestion interfaces, basic heuristic models, and structured
    prediction outputs. It serves as the groundwork for future machine learning
    model integration.

    Example:
        >>> tracker = AirdropTracker()
        >>> predictor = AirdropPredictor(tracker)
        >>> prediction = predictor.predict_airdrop_timing("Uniswap")
        >>> print(f"Next window: {prediction.prediction_windows[0].start_date}")
    """

    def __init__(
        self,
        tracker: AirdropTracker,
        market_data: Optional[MarketDataStub] = None,
        onchain_data: Optional[OnChainActivityStub] = None,
        sentiment_data: Optional[SocialSentimentStub] = None
    ) -> None:
        """
        Initialize the airdrop predictor.

        Args:
            tracker: AirdropTracker instance for historical data
            market_data: Market data source (optional, uses stub if None)
            onchain_data: On-chain activity data source (optional, uses stub if None)
            sentiment_data: Social sentiment data source (optional, uses stub if None)
        """
        self.tracker = tracker
        self.market_data = market_data or MarketDataStub()
        self.onchain_data = onchain_data or OnChainActivityStub()
        self.sentiment_data = sentiment_data or SocialSentimentStub()
        self.model_version = "1.0.0-heuristic"

        logger.info("AirdropPredictor initialized with heuristic model")

    def predict_airdrop_timing(
        self,
        protocol_name: str,
        lookback_days: int = 365
    ) -> PredictionResult:
        """
        Predict airdrop timing for a given protocol using historical patterns.

        Args:
            protocol_name: Name of the protocol to predict for
            lookback_days: Number of days to look back for historical data

        Returns:
            PredictionResult with timing predictions

        Raises:
            ValueError: If protocol_name is invalid
            RuntimeError: If prediction generation fails

        Example:
            >>> predictor = AirdropPredictor(tracker)
            >>> result = predictor.predict_airdrop_timing("Arbitrum")
            >>> print(f"Confidence: {result.confidence_level}")
        """
        # Validate input parameters first (let ValueError propagate)
        if not protocol_name or not protocol_name.strip():
            raise ValueError("Protocol name cannot be empty")

        try:
            protocol_name = protocol_name.strip().title()
            logger.info(f"Generating prediction for protocol: {protocol_name}")

            # Get historical airdrop data
            historical_events = self.tracker.get_airdrops_by_protocol(protocol_name)

            # Apply basic heuristic model
            prediction_windows = self._apply_heuristic_model(
                protocol_name, historical_events, lookback_days
            )

            # Determine confidence level based on data availability
            confidence = self._calculate_confidence_level(historical_events)

            # Set next review date (30 days from now)
            next_review = datetime.now() + timedelta(days=30)

            return PredictionResult(
                protocol_name=protocol_name,
                prediction_windows=prediction_windows,
                confidence_level=confidence,
                model_version=self.model_version,
                data_sources_used=[DataSourceType.HISTORICAL_AIRDROPS],
                next_review_date=next_review,
                metadata={
                    "historical_events_count": len(historical_events),
                    "lookback_days": lookback_days,
                    "model_type": "heuristic"
                }
            )

        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to generate prediction for {protocol_name}: {e}")
            raise RuntimeError(f"Prediction generation failed: {e}") from e

    def _apply_heuristic_model(
        self,
        protocol_name: str,
        historical_events: List[Any],
        lookback_days: int
    ) -> List[PredictionWindow]:
        """
        Apply basic heuristic model for airdrop timing prediction.

        This is a simple placeholder model that analyzes historical patterns
        to suggest potential future airdrop windows.

        Args:
            protocol_name: Protocol name
            historical_events: List of historical airdrop events
            lookback_days: Days to look back for analysis

        Returns:
            List of predicted time windows
        """
        if not historical_events:
            # No historical data - predict based on typical patterns
            return self._generate_default_prediction_windows()

        # Analyze historical patterns
        event_dates = [event.event_date for event in historical_events]

        if len(event_dates) >= 2:
            # Calculate average interval between airdrops
            intervals = []
            sorted_dates = sorted(event_dates)

            for i in range(1, len(sorted_dates)):
                interval = (sorted_dates[i] - sorted_dates[i-1]).days
                intervals.append(interval)

            avg_interval = sum(intervals) / len(intervals)

            # Predict next window based on average interval
            last_event_date = max(event_dates)
            predicted_start = last_event_date + timedelta(days=int(avg_interval * 0.8))
            predicted_end = last_event_date + timedelta(days=int(avg_interval * 1.2))

            return [PredictionWindow(
                start_date=predicted_start,
                end_date=predicted_end,
                probability=Decimal("0.6")
            )]
        else:
            # Single historical event - use default pattern
            last_event_date = event_dates[0]
            predicted_start = last_event_date + timedelta(days=180)
            predicted_end = last_event_date + timedelta(days=365)

            return [PredictionWindow(
                start_date=predicted_start,
                end_date=predicted_end,
                probability=Decimal("0.4")
            )]

    def _generate_default_prediction_windows(self) -> List[PredictionWindow]:
        """
        Generate default prediction windows when no historical data is available.

        Returns:
            List of default prediction windows
        """
        now = datetime.now()

        # Default pattern: suggest windows at 3, 6, and 12 months
        windows = []

        for months, prob in [(3, "0.3"), (6, "0.5"), (12, "0.4")]:
            start_date = now + timedelta(days=months * 30 - 15)
            end_date = now + timedelta(days=months * 30 + 15)

            windows.append(PredictionWindow(
                start_date=start_date,
                end_date=end_date,
                probability=Decimal(prob)
            ))

        return windows

    def _calculate_confidence_level(
        self, historical_events: List[Any]
    ) -> PredictionConfidence:
        """
        Calculate confidence level based on available historical data.

        Args:
            historical_events: List of historical airdrop events

        Returns:
            Confidence level for the prediction
        """
        event_count = len(historical_events)

        if event_count >= 3:
            return PredictionConfidence.HIGH
        elif event_count >= 1:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def get_data_source_status(self) -> Dict[str, bool]:
        """
        Get status of all data sources.

        Returns:
            Dictionary mapping data source names to availability status

        Example:
            >>> predictor = AirdropPredictor(tracker)
            >>> status = predictor.get_data_source_status()
            >>> print(f"Market data available: {status['market_data']}")
        """
        return {
            "historical_airdrops": True,  # Always available via tracker
            "market_data": False,  # Stub implementation
            "onchain_activity": False,  # Stub implementation
            "social_sentiment": False  # Stub implementation
        }

    def update_prediction_model(self, model_version: str) -> None:
        """
        Update the prediction model version.

        Args:
            model_version: New model version identifier

        Example:
            >>> predictor = AirdropPredictor(tracker)
            >>> predictor.update_prediction_model("2.0.0-ml")
        """
        self.model_version = model_version
        logger.info(f"Updated prediction model to version: {model_version}")
