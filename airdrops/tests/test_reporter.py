"""
Tests for the airdrop reporter module.
"""

import pytest
import json
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Generator, List
from unittest.mock import patch, MagicMock
import tempfile
import os

from airdrops.analytics.tracker import AirdropTracker, AirdropEvent
from airdrops.analytics.reporter import (
    AirdropReporter,
    AirdropReport,
    ProtocolSummary,
    ReportFormat
)


class TestAirdropReporter:
    """Test cases for AirdropReporter class."""

    @pytest.fixture
    def temp_db_path(self) -> Generator[str, Any, None]:
        """Create a temporary database path for testing."""
        yield ":memory:"

    @pytest.fixture
    def tracker(self, temp_db_path: str) -> AirdropTracker:
        """Create a tracker instance with temporary database."""
        return AirdropTracker(db_path=temp_db_path)

    @pytest.fixture
    def reporter(self, tracker: AirdropTracker) -> AirdropReporter:
        """Create a reporter instance."""
        return AirdropReporter(tracker)

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

    def test_reporter_initialization(self, tracker: AirdropTracker) -> None:
        """Test reporter initialization."""
        reporter = AirdropReporter(tracker)

        assert reporter.tracker == tracker

    def test_generate_comprehensive_report_empty(self, reporter: AirdropReporter) -> None:
        """Test generating comprehensive report with no data."""
        report = reporter.generate_comprehensive_report()

        assert isinstance(report, AirdropReport)
        assert report.total_airdrops == 0
        assert report.total_protocols == 0
        assert report.total_estimated_value_usd is None
        assert len(report.protocol_summaries) == 0
        assert len(report.top_protocols_by_value) == 0
        assert len(report.monthly_breakdown) == 0

    def test_generate_comprehensive_report_with_data(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test generating comprehensive report with sample data."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        report = reporter.generate_comprehensive_report()

        assert report.total_airdrops == 3
        assert report.total_protocols == 2
        assert report.total_estimated_value_usd == Decimal("2600.75")
        assert len(report.protocol_summaries) == 2
        assert len(report.top_protocols_by_value) == 2
        assert len(report.monthly_breakdown) >= 1

    def test_generate_comprehensive_report_date_range(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test generating report with date range filter."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=20)
        report = reporter.generate_comprehensive_report(start_date, end_date)

        assert report.total_airdrops == 2
        assert report.total_protocols == 2

    def test_generate_protocol_report_success(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test generating protocol-specific report."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        summary = reporter.generate_protocol_report("Uniswap")

        assert isinstance(summary, ProtocolSummary)
        assert summary.protocol_name == "Uniswap"
        assert summary.total_events == 2
        assert summary.total_tokens_received == Decimal("600")
        assert summary.total_estimated_value_usd == Decimal("1800.75")
        assert "UNI" in summary.unique_tokens

    def test_generate_protocol_report_not_found(self, reporter: AirdropReporter) -> None:
        """Test generating report for non-existent protocol."""
        summary = reporter.generate_protocol_report("NonExistent")

        assert summary.protocol_name == "NonExistent"
        assert summary.total_events == 0
        assert summary.total_tokens_received == Decimal("0")
        assert summary.total_estimated_value_usd is None
        assert len(summary.unique_tokens) == 0

    def test_export_report_json(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test exporting report as JSON."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        report = reporter.generate_comprehensive_report()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            reporter.export_report(report, temp_path, ReportFormat.JSON)

            assert Path(temp_path).exists()

            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert data['total_airdrops'] == 3
            assert data['total_protocols'] == 2
            assert len(data['protocol_summaries']) == 2

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_report_csv(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test exporting report as CSV."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        report = reporter.generate_comprehensive_report()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            reporter.export_report(report, temp_path, ReportFormat.CSV)

            assert Path(temp_path).exists()

            with open(temp_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 3
            assert rows[0][0] == 'Protocol Name'

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_report_console(self, reporter: AirdropReporter, sample_events: List[AirdropEvent], capsys: Any) -> None:
        """Test exporting report to console."""
        for event in sample_events:
            reporter.tracker.record_airdrop(event)

        report = reporter.generate_comprehensive_report()

        reporter.export_report(report, "", ReportFormat.CONSOLE)

        captured = capsys.readouterr()

        assert "AIRDROP ANALYTICS REPORT" in captured.out
        assert "Total Airdrops: 3" in captured.out
        assert "Total Protocols: 2" in captured.out
        assert "Uniswap" in captured.out
        assert "Arbitrum" in captured.out

    def test_export_report_unsupported_format(self, reporter: AirdropReporter) -> None:
        """Test exporting report with unsupported format."""
        report = AirdropReport(
            report_generated_at=datetime.now(),
            total_airdrops=0,
            total_protocols=0,
            total_estimated_value_usd=None,
            date_range_start=None,
            date_range_end=None,
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )

        with pytest.raises(ValueError, match="Unsupported format"):
            reporter.export_report(report, "test.txt", "INVALID")  # type: ignore

    def test_generate_protocol_summaries(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test internal method for generating protocol summaries."""
        summaries = reporter._generate_protocol_summaries(sample_events)

        assert len(summaries) == 2

        assert summaries[0].protocol_name == "Uniswap"
        assert summaries[0].total_estimated_value_usd == Decimal("1800.75")
        assert summaries[1].protocol_name == "Arbitrum"
        assert summaries[1].total_estimated_value_usd == Decimal("800.00")

    def test_generate_top_protocols_by_value(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test generating top protocols by value."""
        summaries = reporter._generate_protocol_summaries(sample_events)
        top_protocols = reporter._generate_top_protocols_by_value(summaries)

        assert len(top_protocols) == 2
        assert top_protocols[0]["protocol_name"] == "Uniswap"
        assert top_protocols[0]["total_value_usd"] == Decimal("1800.75")
        assert top_protocols[1]["protocol_name"] == "Arbitrum"
        assert top_protocols[1]["total_value_usd"] == Decimal("800.00")

    def test_generate_monthly_breakdown(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test generating monthly breakdown."""
        breakdown = reporter._generate_monthly_breakdown(sample_events)

        assert len(breakdown) >= 1

        for entry in breakdown:
            assert "month" in entry
            assert "event_count" in entry
            assert "total_value_usd" in entry
            assert isinstance(entry["event_count"], int)
            assert isinstance(entry["total_value_usd"], Decimal)

    def test_create_protocol_summary(self, reporter: AirdropReporter, sample_events: List[AirdropEvent]) -> None:
        """Test creating protocol summary from events."""
        uniswap_events = [e for e in sample_events if e.protocol_name == "Uniswap"]
        summary = reporter._create_protocol_summary("Uniswap", uniswap_events)

        assert summary.protocol_name == "Uniswap"
        assert summary.total_events == 2
        assert summary.total_tokens_received == Decimal("600")
        assert summary.total_estimated_value_usd == Decimal("1800.75")
        assert summary.unique_tokens == ["UNI"]
        assert summary.first_airdrop_date is not None
        assert summary.last_airdrop_date is not None

    def test_report_generation_error_handling(self, reporter: AirdropReporter) -> None:
        """Test error handling during report generation."""
        with patch.object(reporter.tracker, 'get_airdrops_by_date_range') as mock_get:
            mock_get.side_effect = Exception("Database error")

            with pytest.raises(RuntimeError, match="Report generation failed"):
                reporter.generate_comprehensive_report()

    def test_protocol_report_error_handling(self, reporter: AirdropReporter) -> None:
        """Test error handling during protocol report generation."""
        with patch.object(reporter.tracker, 'get_airdrops_by_protocol') as mock_get:
            mock_get.side_effect = Exception("Database error")

            with pytest.raises(RuntimeError, match="Protocol report generation failed"):
                reporter.generate_protocol_report("Uniswap")

    def test_export_error_handling(self, reporter: AirdropReporter) -> None:
        """Test error handling during export."""
        report = AirdropReport(
            report_generated_at=datetime.now(),
            total_airdrops=0,
            total_protocols=0,
            total_estimated_value_usd=None,
            date_range_start=None,
            date_range_end=None,
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")
            with pytest.raises(RuntimeError, match="Report export failed"):
                reporter.export_report(report, "/invalid/path/report.json", ReportFormat.JSON)


class TestReportFormat:
    """Test cases for ReportFormat enum."""

    def test_report_format_values(self) -> None:
        """Test ReportFormat enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.CSV.value == "csv"
        assert ReportFormat.CONSOLE.value == "console"


class TestProtocolSummary:
    """Test cases for ProtocolSummary model."""

    def test_protocol_summary_creation(self) -> None:
        """Test creating a ProtocolSummary instance."""
        summary = ProtocolSummary(
            protocol_name="Uniswap",
            total_events=5,
            total_tokens_received=Decimal("1000"),
            total_estimated_value_usd=Decimal("3000.50"),
            unique_tokens=["UNI", "USDC"],
            first_airdrop_date=datetime.now() - timedelta(days=30),
            last_airdrop_date=datetime.now()
        )

        assert summary.protocol_name == "Uniswap"
        assert summary.total_events == 5
        assert summary.total_tokens_received == Decimal("1000")
        assert summary.total_estimated_value_usd == Decimal("3000.50")
        assert len(summary.unique_tokens) == 2


class TestAirdropReport:
    """Test cases for AirdropReport model."""

    def test_airdrop_report_creation(self) -> None:
        """Test creating an AirdropReport instance."""
        report = AirdropReport(
            report_generated_at=datetime.now(),
            total_airdrops=10,
            total_protocols=3,
            total_estimated_value_usd=Decimal("5000.00"),
            date_range_start=datetime.now() - timedelta(days=30),
            date_range_end=datetime.now(),
            protocol_summaries=[],
            top_protocols_by_value=[],
            monthly_breakdown=[]
        )

        assert report.total_airdrops == 10
        assert report.total_protocols == 3
        assert report.total_estimated_value_usd == Decimal("5000.00")
        assert isinstance(report.protocol_summaries, list)
        assert isinstance(report.top_protocols_by_value, list)
        assert isinstance(report.monthly_breakdown, list)