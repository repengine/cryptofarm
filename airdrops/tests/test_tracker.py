"""
Tests for the airdrop tracker module.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from unittest.mock import patch, MagicMock
from typing import Any, Generator, List, Optional

import pytest

from airdrops.analytics.tracker import AirdropTracker, AirdropEvent, AirdropEventModel


class TestAirdropEvent:
    """Test cases for AirdropEvent Pydantic model."""
    def test_valid_airdrop_event(self) -> None:
        """Test creating a valid airdrop event."""
        event = AirdropEvent(
            protocol_name="Uniswap",
            token_symbol="UNI",
            amount_received=Decimal("400"),
            estimated_value_usd=Decimal("1200.50"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            transaction_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            block_number=12345678,
            event_date=datetime.now(),
            notes="Test airdrop event"
        )
        assert event.protocol_name == "Uniswap"
        assert event.token_symbol == "UNI"
        assert event.amount_received == Decimal("400")
        assert event.estimated_value_usd == Decimal("1200.50")
        assert event.wallet_address == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"

    def test_protocol_name_validation(self) -> None:
        """Test protocol name validation and formatting."""
        event = AirdropEvent(
            protocol_name="  uniswap  ",
            token_symbol="UNI",
            amount_received=Decimal("400"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime.now(),
            estimated_value_usd=None,
            transaction_hash=None,
            block_number=None,
            notes=None,
        )
        assert event.protocol_name == "Uniswap"

    def test_token_symbol_validation(self) -> None:
        """Test token symbol validation and formatting."""
        event = AirdropEvent(
            protocol_name="Uniswap",
            token_symbol="  uni  ",
            amount_received=Decimal("400"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime.now(),
            estimated_value_usd=None,
            transaction_hash=None,
            block_number=None,
            notes=None,
        )
        assert event.token_symbol == "UNI"

    def test_invalid_wallet_address(self) -> None:
        """Test validation of invalid wallet address."""
        with pytest.raises(ValueError):
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("400"),
                wallet_address="invalid_address",
                event_date=datetime.now(),
                estimated_value_usd=None,
                transaction_hash=None,
                block_number=None,
                notes=None,
            )

    def test_invalid_transaction_hash(self) -> None:
        """Test validation of invalid transaction hash."""
        with pytest.raises(ValueError):
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("400"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                transaction_hash="invalid_hash",
                event_date=datetime.now(),
                estimated_value_usd=None,
                block_number=None,
                notes=None,
            )

    def test_negative_amount(self) -> None:
        """Test validation of negative amount."""
        with pytest.raises(ValueError):
            AirdropEvent(
                protocol_name="Uniswap",
                token_symbol="UNI",
                amount_received=Decimal("-400"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime.now(),
                estimated_value_usd=None,
                transaction_hash=None,
                block_number=None,
                notes=None,
            )

    def test_empty_protocol_name(self) -> None:
        """Test validation of empty protocol name."""
        with pytest.raises(ValueError):
            AirdropEvent(
                protocol_name="",
                token_symbol="UNI",
                amount_received=Decimal("400"),
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                event_date=datetime.now(),
                estimated_value_usd=None,
                transaction_hash=None,
                block_number=None,
                notes=None,
            )


class TestAirdropTracker:
    """Test cases for AirdropTracker class."""
    @pytest.fixture
    def temp_db_path(self) -> Generator[str, Any, None]:
        """Create a temporary database path for testing."""
        yield ":memory:"

    @pytest.fixture
    def tracker(self, temp_db_path: str) -> AirdropTracker:
        """Create a tracker instance with temporary database."""
        return AirdropTracker(db_path=temp_db_path)

    @pytest.fixture
    def sample_event(self) -> AirdropEvent:
        """Create a sample airdrop event for testing with a unique transaction hash."""
        return AirdropEvent(
            protocol_name="Uniswap",
            token_symbol="UNI",
            amount_received=Decimal("400"),
            estimated_value_usd=Decimal("1200.50"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            transaction_hash=(
                f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"
            ),  # Generate a 64-char hex string
            block_number=12345678,
            event_date=datetime.now(),
            notes="Test airdrop event"
        )

    def test_tracker_initialization(self, temp_db_path: str) -> None:
        """Test tracker initialization."""
        tracker = AirdropTracker(db_path=temp_db_path)
        assert tracker.db_path == temp_db_path
        assert tracker.engine is not None
        assert tracker.SessionLocal is not None
        # For in-memory databases, Path.exists() will be False, so remove this assertion
        # if temp_db_path != ":memory__": # This check is no longer needed as we are always using :memory: for tests
        #     assert Path(temp_db_path).exists()

    def test_record_airdrop_success(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test successful airdrop recording."""
        event_id = tracker.record_airdrop(sample_event)
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_record_airdrop_database_error(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test airdrop recording with database error."""
        # Mock the session to raise an exception
        with patch.object(tracker, 'SessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session.__enter__.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_session
            with pytest.raises(RuntimeError, match="Database operation failed"):
                tracker.record_airdrop(sample_event)

    def test_get_airdrops_by_protocol_success(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test retrieving airdrops by protocol."""
        # Record an event first
        tracker.record_airdrop(sample_event)
        # Retrieve events
        events = tracker.get_airdrops_by_protocol("Uniswap")
        assert len(events) == 1
        assert events[0].protocol_name == "Uniswap"
        assert events[0].token_symbol == "UNI"
        assert events[0].amount_received == Decimal("400")

    def test_get_airdrops_by_protocol_not_found(self, tracker: AirdropTracker) -> None:
        """Test retrieving airdrops for non-existent protocol."""
        events = tracker.get_airdrops_by_protocol("NonExistent")
        assert len(events) == 0

    def test_get_airdrops_by_wallet_success(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test retrieving airdrops by wallet address."""
        # Record an event first
        tracker.record_airdrop(sample_event)
        # Retrieve events
        events = tracker.get_airdrops_by_wallet("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
        assert len(events) == 1
        assert events[0].wallet_address == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6".lower()

    def test_get_airdrops_by_date_range_success(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test retrieving airdrops by date range."""
        # Record an event first
        tracker.record_airdrop(sample_event)
        # Retrieve events within date range
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        events = tracker.get_airdrops_by_date_range(start_date, end_date)
        assert len(events) == 1
        assert events[0].protocol_name == "Uniswap"

    def test_get_airdrops_by_date_range_outside_range(self, tracker: AirdropTracker, sample_event: AirdropEvent) -> None:
        """Test retrieving airdrops outside date range."""
        # Record an event first
        tracker.record_airdrop(sample_event)
        # Retrieve events outside date range
        start_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now() - timedelta(days=5)
        events = tracker.get_airdrops_by_date_range(start_date, end_date)
        assert len(events) == 0

    def test_get_airdrops_database_error(self, tracker: AirdropTracker) -> None:
        """Test database error during retrieval."""
        with patch.object(tracker, 'SessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session.__enter__.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_session
            with pytest.raises(RuntimeError, match="Database query failed"):
                tracker.get_airdrops_by_protocol("Uniswap")

    def test_db_event_to_pydantic_conversion(self, tracker: AirdropTracker) -> None:
        """Test conversion from SQLAlchemy model to Pydantic model."""
        # Create a mock database event
        db_event = AirdropEventModel(
            protocol_name="Uniswap",
            token_symbol="UNI",
            amount_received=Decimal("400"),
            estimated_value_usd=Decimal("1200.50"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            transaction_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            block_number=12345678,
            event_date=datetime.now(),
            notes="Test event"
        )
        # Convert to Pydantic model
        pydantic_event = tracker._db_event_to_pydantic(db_event)
        assert isinstance(pydantic_event, AirdropEvent)
        assert pydantic_event.protocol_name == "Uniswap"
        assert pydantic_event.token_symbol == "UNI"
        assert pydantic_event.amount_received == Decimal("400")

    def test_multiple_events_ordering(self, tracker: AirdropTracker) -> None:
        """Test that events are returned in descending date order."""
        # Create events with different dates
        event1 = AirdropEvent(
            protocol_name="Uniswap",
            token_symbol="UNI",
            amount_received=Decimal("400"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime.now() - timedelta(days=2),
            estimated_value_usd=None,
            transaction_hash=None,
            block_number=None,
            notes=None,
        )
        event2 = AirdropEvent(
            protocol_name="Uniswap",
            token_symbol="UNI",
            amount_received=Decimal("500"),
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            event_date=datetime.now() - timedelta(days=1),
            estimated_value_usd=None,
            transaction_hash=None,
            block_number=None,
            notes=None,
        )
        # Record events
        tracker.record_airdrop(event1)
        tracker.record_airdrop(event2)
        # Retrieve events
        events = tracker.get_airdrops_by_protocol("Uniswap")
        assert len(events) == 2
        # Should be in descending order (newest first)
        assert events[0].amount_received == Decimal("500")
        assert events[1].amount_received == Decimal("400")