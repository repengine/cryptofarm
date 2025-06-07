"""
Airdrop Tracking Module.

This module provides functionality to track airdrop events, store them in a database,
and retrieve historical data for analysis.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine import Engine

# Configure logging
logger = logging.getLogger(__name__)


# SQLAlchemy Base
class Base(DeclarativeBase):
    __abstract__ = True


# Database configuration
DEFAULT_DB_PATH = "analytics.db"


class AirdropEventModel(Base):
    """SQLAlchemy model for airdrop events."""
    __tablename__ = "airdrop_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol_name = Column(String(100), nullable=False, index=True)
    token_symbol = Column(String(20), nullable=False)
    amount_received = Column(Numeric(precision=36, scale=18), nullable=False)
    estimated_value_usd = Column(Numeric(precision=20, scale=8), nullable=True)
    wallet_address = Column(String(42), nullable=False, index=True)
    transaction_hash = Column(String(66), nullable=True, unique=True)
    block_number = Column(Integer, nullable=True)
    event_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)


class AirdropEvent(BaseModel):
    """Pydantic model for airdrop event validation."""
    protocol_name: str = Field(..., min_length=1, max_length=100)
    token_symbol: str = Field(..., min_length=1, max_length=20)
    amount_received: Decimal = Field(..., gt=0)
    estimated_value_usd: Optional[Decimal] = Field(None, ge=0)
    wallet_address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    transaction_hash: Optional[str] = Field(None, pattern=r"^0x[a-fA-F0-9]{64}$")
    block_number: Optional[int] = Field(None, ge=0)
    event_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('protocol_name')
    def validate_protocol_name(cls, v: str) -> str:
        """Validate protocol name format."""
        if not v.strip():
            raise ValueError("Protocol name cannot be empty")
        return v.strip().title()

    @field_validator('token_symbol')
    def validate_token_symbol(cls, v: str) -> str:
        """Validate token symbol format."""
        return v.strip().upper()

    class ConfigDict:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class AirdropTracker:
    """
    Airdrop tracking and storage system.

    Provides functionality to record airdrop events, store them in SQLite database,
    and retrieve historical data for analysis and reporting.

    Example:
        >>> tracker = AirdropTracker()
        >>> event = AirdropEvent(
        ...     protocol_name="Uniswap",
        ...     token_symbol="UNI",
        ...     amount_received=Decimal("400"),
        ...     estimated_value_usd=Decimal("1200.50"),
        ...     wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        ...     event_date=datetime.now()
        ... )
        >>> tracker.record_airdrop(event)
        >>> events = tracker.get_airdrops_by_protocol("Uniswap")
    """
    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize the airdrop tracker.

        Args:
            db_path: Path to SQLite database file. If None, uses default path.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._create_tables()
        logger.info(f"AirdropTracker initialized with database: {self.db_path}")

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine for SQLite database."""
        # Create engine
        engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            pool_pre_ping=True
        )
        # Ensure directory exists for file-based databases
        if self.db_path != ":memory:":
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
        return engine

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.debug("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def record_airdrop(self, event: AirdropEvent) -> int:
        """
        Record a new airdrop event in the database.

        Args:
            event: AirdropEvent instance to record

        Returns:
            ID of the created record

        Raises:
            ValueError: If event data is invalid
            RuntimeError: If database operation fails
        """
        try:
            with self.SessionLocal() as session:
                db_event = AirdropEventModel(
                    protocol_name=event.protocol_name,
                    token_symbol=event.token_symbol,
                    amount_received=event.amount_received,
                    estimated_value_usd=event.estimated_value_usd,
                    wallet_address=event.wallet_address.lower(),
                    transaction_hash=event.transaction_hash,
                    block_number=event.block_number,
                    event_date=event.event_date,
                    notes=event.notes
                )

                session.add(db_event)
                session.commit()
                session.refresh(db_event)
                # Removed: Rely on 'with' block for session management

                logger.info(
                    f"Recorded airdrop: {event.protocol_name} - "
                    f"{event.amount_received} {event.token_symbol}"
                )
                return int(db_event.id)

        except Exception as e:
            logger.error(f"Failed to record airdrop event: {e}")
            raise RuntimeError(f"Database operation failed: {e}") from e

    def get_airdrops_by_protocol(self, protocol_name: str) -> List[AirdropEvent]:
        """
        Retrieve all airdrop events for a specific protocol.

        Args:
            protocol_name: Name of the protocol to filter by

        Returns:
            List of AirdropEvent instances
        """
        try:
            with self.SessionLocal() as session:
                db_events = session.query(AirdropEventModel).filter(
                    AirdropEventModel.protocol_name == protocol_name.strip().title()
                ).order_by(AirdropEventModel.event_date.desc()).all()

                return [self._db_event_to_pydantic(event) for event in db_events]

        except Exception as e:
            logger.error(f"Failed to retrieve airdrops for protocol {protocol_name}: {e}")
            raise RuntimeError(f"Database query failed: {e}") from e

    def get_airdrops_by_wallet(self, wallet_address: str) -> List[AirdropEvent]:
        """
        Retrieve all airdrop events for a specific wallet.

        Args:
            wallet_address: Ethereum wallet address

        Returns:
            List of AirdropEvent instances
        """
        try:
            with self.SessionLocal() as session:
                db_events = session.query(AirdropEventModel).filter(
                    AirdropEventModel.wallet_address == wallet_address.lower()
                ).order_by(AirdropEventModel.event_date.desc()).all()

                return [self._db_event_to_pydantic(event) for event in db_events]

        except Exception as e:
            logger.error(f"Failed to retrieve airdrops for wallet {wallet_address}: {e}")
            raise RuntimeError(f"Database query failed: {e}") from e

    def get_airdrops_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[AirdropEvent]:
        """
        Retrieve airdrop events within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of AirdropEvent instances
        """
        try:
            with self.SessionLocal() as session:
                db_events = session.query(AirdropEventModel).filter(
                    AirdropEventModel.event_date >= start_date,
                    AirdropEventModel.event_date <= end_date
                ).order_by(AirdropEventModel.event_date.desc()).all()

                return [self._db_event_to_pydantic(event) for event in db_events]

        except Exception as e:
            logger.error(f"Failed to retrieve airdrops for date range: {e}")
            raise RuntimeError(f"Database query failed: {e}") from e

    def _db_event_to_pydantic(self, db_event: AirdropEventModel) -> AirdropEvent:
        """Convert SQLAlchemy model to Pydantic model."""
        return AirdropEvent(
            protocol_name=str(db_event.protocol_name),
            token_symbol=str(db_event.token_symbol),
            amount_received=Decimal(str(db_event.amount_received)),
            estimated_value_usd=(
                Decimal(str(db_event.estimated_value_usd))
                if db_event.estimated_value_usd is not None
                else None
            ),
            wallet_address=str(db_event.wallet_address),
            transaction_hash=(
                str(db_event.transaction_hash)
                if db_event.transaction_hash is not None
                else None
            ),
            block_number=(
                int(db_event.block_number)
                if db_event.block_number is not None
                else None
            ),
            event_date=datetime(
                db_event.event_date.year,
                db_event.event_date.month,
                db_event.event_date.day,
                db_event.event_date.hour,
                db_event.event_date.minute,
                db_event.event_date.second,
                db_event.event_date.microsecond,
                tzinfo=db_event.event_date.tzinfo,
            ),
            notes=str(db_event.notes) if db_event.notes is not None else None,
        )
