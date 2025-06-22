"""
Tests for the airdrops.analytics.reporter module.
"""

import json
import pytest
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import List, Any
from unittest.mock import MagicMock

from airdrops.analytics.reporter import AirdropReporter, ReportFormat, AirdropReport, ProtocolSummary
from airdrops.analytics.tracker import AirdropTracker, AirdropEvent


@pytest.fixture
def sample_events() -> List[AirdropEvent]:
    """Sample airdrop events for testing."""
    return [
        AirdropEvent(
            protocol_name="Scroll",
            token_symbol="ETH",
            amount_received=Decimal("0.1"),
            estimated_value_usd=Decimal("200"),
            wallet_address="0x1000000000000000000000000000000000000001",
            event_date=datetime(2023, 1, 1),
            transaction_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            block_number=12345,
            notes="Test airdrop event"
        ),
        AirdropEvent(
            protocol_name="Zksync",
            token_symbol="USDC",
            amount_received=Decimal("100"),
            estimated_value_usd=Decimal("100"),
            wallet_address="0x1000000000000000000000000000000000000001",
            event_date=datetime(2023, 1, 15),
            transaction_hash="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            block_number=12346,
            notes="Test airdrop event"
        ),
        AirdropEvent(
            protocol_name="Scroll",
            token_symbol="USDT",
            amount_received=Decimal("50"),
            estimated_value_usd=Decimal("50"),
            wallet_address="0x2000000000000000000000000000000000000002",
            event_date=datetime(2023, 2, 1),
            transaction_hash="0x567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234",
            block_number=12347,
            notes="Test airdrop event"
        ),
    ]


@pytest.fixture
def mock_tracker(sample_events: List[AirdropEvent]) -> MagicMock:
    """Fixture for a mock AirdropTracker instance."""
    tracker = MagicMock(spec=AirdropTracker)

    def get_by_date_range(start_date: datetime, end_date: datetime) -> List[AirdropEvent]:
        return [
            e for e in sample_events
            if (start_date is None or e.event_date >= start_date) and
               (end_date is None or e.event_date <= end_date)
        ]

    def get_by_protocol(protocol_name: str) -> List[AirdropEvent]:
        return [e for e in sample_events if e.protocol_name.lower() == protocol_name.lower()]

    tracker.get_airdrops_by_date_range.side_effect = get_by_date_range
    tracker.get_airdrops_by_protocol.side_effect = get_by_protocol
    return tracker


@pytest.fixture
def reporter(mock_tracker: MagicMock) -> AirdropReporter:
    """Fixture for an AirdropReporter instance."""
    return AirdropReporter(mock_tracker)


def test_generate_comprehensive_report(reporter: AirdropReporter) -> None:
    """Test generating a comprehensive report."""
    report = reporter.generate_comprehensive_report()

    assert isinstance(report, AirdropReport)
    assert report.total_airdrops == 3
    assert report.total_protocols == 2
    assert report.total_estimated_value_usd == Decimal("350")
    assert len(report.protocol_summaries) == 2

    scroll_summary = next(s for s in report.protocol_summaries if s.protocol_name == "Scroll")
    assert scroll_summary.total_events == 2
    assert scroll_summary.total_estimated_value_usd == Decimal("250")

    zksync_summary = next(s for s in report.protocol_summaries if s.protocol_name == "Zksync")
    assert zksync_summary.total_events == 1
    assert zksync_summary.total_estimated_value_usd == Decimal("100")


def test_generate_protocol_report(reporter: AirdropReporter) -> None:
    """Test generating a protocol-specific report."""
    report = reporter.generate_protocol_report("Scroll")

    assert isinstance(report, ProtocolSummary)
    assert report.protocol_name == "Scroll"
    assert report.total_events == 2
    assert report.total_estimated_value_usd == Decimal("250")
    assert set(report.unique_tokens) == {"ETH", "USDT"}


def test_generate_protocol_report_not_found(reporter: AirdropReporter) -> None:
    """Test generating a report for a non-existent protocol."""
    report = reporter.generate_protocol_report("non_existent")
    assert report.total_events == 0


def test_export_report_json(reporter: AirdropReporter, tmp_path: Path) -> None:
    """Test exporting a report to JSON."""
    report = reporter.generate_comprehensive_report()
    output_file = tmp_path / "report.json"

    reporter.export_report(report, str(output_file), ReportFormat.JSON)

    assert output_file.exists()
    with open(output_file, 'r') as f:
        data = json.load(f)
    assert data["total_airdrops"] == 3
    assert data["protocol_summaries"][0]["protocol_name"] == "Scroll"
    assert data["protocol_summaries"][0]["total_estimated_value_usd"] == "250"


def test_export_report_csv(reporter: AirdropReporter, tmp_path: Path) -> None:
    """Test exporting a report to CSV."""
    report = reporter.generate_comprehensive_report()
    output_file = tmp_path / "report.csv"

    reporter.export_report(report, str(output_file), ReportFormat.CSV)

    assert output_file.exists()
    with open(output_file, 'r') as f:
        lines = f.readlines()
    assert len(lines) == 3  # Header + 2 protocols
    assert "Protocol Name,Total Events" in lines[0]
    assert "Scroll,2" in lines[1]
    assert "Zksync,1" in lines[2]


def test_export_report_console(reporter: AirdropReporter, capsys: Any) -> None:
    """Test exporting a report to the console."""
    report = reporter.generate_comprehensive_report()

    reporter.export_report(report, "", ReportFormat.CONSOLE)

    captured = capsys.readouterr()
    assert "AIRDROP ANALYTICS REPORT" in captured.out
    assert "Total Airdrops: 3" in captured.out
    assert "Total Estimated Value: $350.00" in captured.out
    assert "Scroll:" in captured.out
    assert "Value: $250.00" in captured.out


def test_unsupported_report_format(reporter: AirdropReporter) -> None:
    """Test that an unsupported report format raises an error."""
    report = reporter.generate_comprehensive_report()
    with pytest.raises(ValueError, match="Unsupported format"):
        # Cast to ReportFormat to satisfy mypy
        reporter.export_report(report, "file.txt", "unsupported_format")  # type: ignore
