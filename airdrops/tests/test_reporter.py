"""
Tests for the airdrops.analytics.reporter module.
"""

import json
import pytest
from decimal import Decimal
from enum import Enum
from unittest.mock import MagicMock

from airdrops.analytics.reporter import AirdropReporter, ReportFormat  # type: ignore
from airdrops.analytics.tracker import AirdropTracker  # type: ignore


@pytest.fixture
def mock_tracker():
    """Fixture for a mock AirdropTracker instance."""
    tracker = MagicMock(spec=AirdropTracker)
    tracker.total_airdrops_tracked = 5
    tracker.total_value_tracked = Decimal("1500")
    tracker.protocol_metrics = {
        "scroll": {
            "total_airdrops": 3,
            "successful_airdrops": 2,
            "failed_airdrops": 1,
            "total_value_usd": Decimal("1000"),
        },
        "zksync": {
            "total_airdrops": 2,
            "successful_airdrops": 1,
            "failed_airdrops": 1,
            "total_value_usd": Decimal("500"),
        },
    }
    tracker.wallet_metrics = {
        "0x1": {
            "total_airdrops": 3,
            "successful_airdrops": 2,
            "failed_airdrops": 1,
            "total_value_usd": Decimal("1200"),
        },
        "0x2": {
            "total_airdrops": 2,
            "successful_airdrops": 1,
            "failed_airdrops": 1,
            "total_value_usd": Decimal("300"),
        },
    }
    tracker.get_protocol_summary.return_value = tracker.protocol_metrics
    tracker.get_wallet_summary.return_value = tracker.wallet_metrics
    return tracker


@pytest.fixture
def reporter(mock_tracker):
    """Fixture for an AirdropReporter instance."""
    return AirdropReporter(mock_tracker)


def test_generate_summary_report_text(reporter):
    """Test generating a summary report in text format."""
    report = reporter.generate_summary_report(ReportFormat.TEXT)
    assert isinstance(report, str)
    assert "Airdrop Performance Summary" in report
    assert "Total Airdrops Tracked: 5" in report
    assert "Total Value Tracked: $1,500.00" in report
    assert "Protocol Metrics:" in report
    assert "Scroll: Total=3, Successful=2, Failed=1, Value=$1,000.00" in report
    assert "ZkSync: Total=2, Successful=1, Failed=1, Value=$500.00" in report
    assert "Wallet Metrics:" in report
    assert "0x1: Total=3, Successful=2, Failed=1, Value=$1,200.00" in report
    assert "0x2: Total=2, Successful=1, Failed=1, Value=$300.00" in report


def test_generate_summary_report_json(reporter):
    """Test generating a summary report in JSON format."""
    report = reporter.generate_summary_report(ReportFormat.JSON)
    assert isinstance(report, str)
    report_json = json.loads(report)
    assert report_json["total_airdrops_tracked"] == 5
    assert report_json["total_value_tracked"] == "1500.00"  # Stored as string in JSON
    assert report_json["protocol_metrics"]["scroll"]["total_airdrops"] == 3
    assert report_json["wallet_metrics"]["0x1"]["total_value_usd"] == "1200.00"


def test_generate_summary_report_markdown(reporter):
    """Test generating a summary report in Markdown format."""
    report = reporter.generate_summary_report(ReportFormat.MARKDOWN)
    assert isinstance(report, str)
    assert "# Airdrop Performance Summary" in report
    assert "**Total Airdrops Tracked:** 5" in report
    assert "**Total Value Tracked:** $1,500.00" in report
    assert "## Protocol Metrics" in report
    assert "| Protocol | Total | Successful | Failed | Value (USD) |" in report
    assert "|----------|-------|------------|--------|-------------|" in report
    assert "| scroll   | 3     | 2          | 1      | 1000.00     |" in report
    assert "## Wallet Metrics" in report
    assert "| Wallet | Total | Successful | Failed | Value (USD) |" in report


def test_generate_protocol_report_text(reporter):
    """Test generating a protocol-specific report in text format."""
    report = reporter.generate_protocol_report("scroll", ReportFormat.TEXT)
    assert isinstance(report, str)
    assert "Protocol Performance Report: scroll" in report
    assert "Total Airdrops: 3" in report
    assert "Successful Airdrops: 2" in report
    assert "Failed Airdrops: 1" in report
    assert "Total Value (USD): $1,000.00" in report


def test_generate_protocol_report_json(reporter):
    """Test generating a protocol-specific report in JSON format."""
    report = reporter.generate_protocol_report("zksync", ReportFormat.JSON)
    assert isinstance(report, str)
    report_json = json.loads(report)
    assert report_json["protocol"] == "zksync"
    assert report_json["total_airdrops"] == 2
    assert report_json["successful_airdrops"] == 1
    assert report_json["total_value_usd"] == "500.00"


def test_generate_protocol_report_markdown(reporter):
    """Test generating a protocol-specific report in Markdown format."""
    report = reporter.generate_protocol_report("scroll", ReportFormat.MARKDOWN)
    assert isinstance(report, str)
    assert "# Protocol Performance Report: scroll" in report
    assert "**Total Airdrops:** 3" in report
    assert "**Successful Airdrops:** 2" in report
    assert "**Total Value (USD):** $1,000.00" in report


def test_generate_wallet_report_text(reporter):
    """Test generating a wallet-specific report in text format."""
    report = reporter.generate_wallet_report("0x1", ReportFormat.TEXT)
    assert isinstance(report, str)
    assert "Wallet Performance Report: 0x1" in report
    assert "Total Airdrops: 3" in report
    assert "Successful Airdrops: 2" in report
    assert "Failed Airdrops: 1" in report
    assert "Total Value (USD): $1,200.00" in report


def test_generate_wallet_report_json(reporter):
    """Test generating a wallet-specific report in JSON format."""
    report = reporter.generate_wallet_report("0x2", ReportFormat.JSON)
    assert isinstance(report, str)
    report_json = json.loads(report)
    assert report_json["wallet"] == "0x2"
    assert report_json["total_airdrops"] == 2
    assert report_json["successful_airdrops"] == 1
    assert report_json["total_value_usd"] == "300.00"


def test_generate_wallet_report_markdown(reporter):
    """Test generating a wallet-specific report in Markdown format."""
    report = reporter.generate_wallet_report("0x1", ReportFormat.MARKDOWN)
    assert isinstance(report, str)
    assert "# Wallet Performance Report: 0x1" in report
    assert "**Total Airdrops:** 3" in report
    assert "**Successful Airdrops:** 2" in report
    assert "**Total Value (USD):** $1,200.00" in report


def test_unsupported_report_format(reporter):
    """Test that an unsupported report format raises an error."""
    class UnsupportedFormat(Enum):
        UNSUPPORTED = "unsupported"

    with pytest.raises(ValueError, match="Unsupported report format"):
        reporter.generate_summary_report(UnsupportedFormat.UNSUPPORTED)  # type: ignore


def test_non_existent_protocol_report(reporter):
    """Test generating a report for a non-existent protocol."""
    report = reporter.generate_protocol_report("non_existent", ReportFormat.TEXT)
    assert "No data available for protocol: non_existent" in report


def test_non_existent_wallet_report(reporter):
    """Test generating a report for a non-existent wallet."""
    report = reporter.generate_wallet_report("0xnon_existent", ReportFormat.TEXT)
    assert "No data available for wallet: 0xnon_existent" in report
