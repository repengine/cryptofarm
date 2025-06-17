"""
Tests for the airdrops.analytics.tracker module.
"""

import pytest
from decimal import Decimal
import pendulum

from airdrops.analytics.tracker import AirdropTracker  # type: ignore
from airdrops.shared.utils import get_current_timestamp  # type: ignore


@pytest.fixture
def tracker():
    """Fixture for a fresh AirdropTracker instance."""
    return AirdropTracker()


def test_initial_state(tracker):
    """Test the initial state of the tracker."""
    assert tracker.total_airdrops_tracked == 0
    assert tracker.total_value_tracked == Decimal("0")
    assert tracker.protocol_metrics == {}
    assert tracker.wallet_metrics == {}


def test_track_airdrop_success(tracker):
    """Test tracking a successful airdrop."""
    protocol = "scroll"
    wallet = "0x123abc"
    value_usd = Decimal("100.50")
    timestamp = get_current_timestamp()

    tracker.track_airdrop(protocol, wallet, value_usd, timestamp, success=True)

    assert tracker.total_airdrops_tracked == 1
    assert tracker.total_value_tracked == value_usd

    # Protocol metrics
    assert protocol in tracker.protocol_metrics
    assert tracker.protocol_metrics[protocol]["total_airdrops"] == 1
    assert tracker.protocol_metrics[protocol]["successful_airdrops"] == 1
    assert tracker.protocol_metrics[protocol]["failed_airdrops"] == 0
    assert tracker.protocol_metrics[protocol]["total_value_usd"] == value_usd

    # Wallet metrics
    assert wallet in tracker.wallet_metrics
    assert tracker.wallet_metrics[wallet]["total_airdrops"] == 1
    assert tracker.wallet_metrics[wallet]["successful_airdrops"] == 1
    assert tracker.wallet_metrics[wallet]["failed_airdrops"] == 0
    assert tracker.wallet_metrics[wallet]["total_value_usd"] == value_usd


def test_track_airdrop_failure(tracker):
    """Test tracking a failed airdrop."""
    protocol = "zksync"
    wallet = "0x456def"
    value_usd = Decimal("50.25")
    timestamp = get_current_timestamp()

    tracker.track_airdrop(protocol, wallet, value_usd, timestamp, success=False)

    assert tracker.total_airdrops_tracked == 1
    assert tracker.total_value_tracked == Decimal("0")  # Failed airdrops don't add value

    # Protocol metrics
    assert protocol in tracker.protocol_metrics
    assert tracker.protocol_metrics[protocol]["total_airdrops"] == 1
    assert tracker.protocol_metrics[protocol]["successful_airdrops"] == 0
    assert tracker.protocol_metrics[protocol]["failed_airdrops"] == 1
    assert tracker.protocol_metrics[protocol]["total_value_usd"] == Decimal("0")

    # Wallet metrics
    assert wallet in tracker.wallet_metrics
    assert tracker.wallet_metrics[wallet]["total_airdrops"] == 1
    assert tracker.wallet_metrics[wallet]["successful_airdrops"] == 0
    assert tracker.wallet_metrics[wallet]["failed_airdrops"] == 1
    assert tracker.wallet_metrics[wallet]["total_value_usd"] == Decimal("0")


def test_track_multiple_airdrops(tracker):
    """Test tracking multiple airdrops for same protocol/wallet."""
    protocol1 = "eigenlayer"
    protocol2 = "layerzero"
    wallet1 = "0x789ghi"
    wallet2 = "0xabcjkl"

    tracker.track_airdrop(protocol1, wallet1, Decimal("100"), get_current_timestamp(), True)
    tracker.track_airdrop(protocol1, wallet1, Decimal("200"), get_current_timestamp(), True)
    tracker.track_airdrop(protocol2, wallet1, Decimal("50"), get_current_timestamp(), False)
    tracker.track_airdrop(protocol2, wallet2, Decimal("150"), get_current_timestamp(), True)

    assert tracker.total_airdrops_tracked == 4
    assert tracker.total_value_tracked == Decimal("100") + Decimal("200") + Decimal("150")

    # Protocol1 metrics
    assert tracker.protocol_metrics[protocol1]["total_airdrops"] == 2
    assert tracker.protocol_metrics[protocol1]["successful_airdrops"] == 2
    assert tracker.protocol_metrics[protocol1]["failed_airdrops"] == 0
    assert tracker.protocol_metrics[protocol1]["total_value_usd"] == Decimal("300")

    # Protocol2 metrics
    assert tracker.protocol_metrics[protocol2]["total_airdrops"] == 2
    assert tracker.protocol_metrics[protocol2]["successful_airdrops"] == 1
    assert tracker.protocol_metrics[protocol2]["failed_airdrops"] == 1
    assert tracker.protocol_metrics[protocol2]["total_value_usd"] == Decimal("150")

    # Wallet1 metrics
    assert tracker.wallet_metrics[wallet1]["total_airdrops"] == 3
    assert tracker.wallet_metrics[wallet1]["successful_airdrops"] == 2
    assert tracker.wallet_metrics[wallet1]["failed_airdrops"] == 1
    assert tracker.wallet_metrics[wallet1]["total_value_usd"] == Decimal("300")

    # Wallet2 metrics
    assert tracker.wallet_metrics[wallet2]["total_airdrops"] == 1
    assert tracker.wallet_metrics[wallet2]["successful_airdrops"] == 1
    assert tracker.wallet_metrics[wallet2]["failed_airdrops"] == 0
    assert tracker.wallet_metrics[wallet2]["total_value_usd"] == Decimal("150")


def test_get_protocol_summary(tracker):
    """Test retrieving protocol summary."""
    tracker.track_airdrop("scroll", "0x1", Decimal("100"), get_current_timestamp(), True)
    tracker.track_airdrop("scroll", "0x2", Decimal("200"), get_current_timestamp(), True)
    tracker.track_airdrop("zksync", "0x3", Decimal("50"), get_current_timestamp(), False)

    summary = tracker.get_protocol_summary()
    assert isinstance(summary, dict)
    assert "scroll" in summary
    assert "zksync" in summary
    assert summary["scroll"]["total_airdrops"] == 2
    assert summary["scroll"]["successful_airdrops"] == 2
    assert summary["scroll"]["total_value_usd"] == Decimal("300")
    assert summary["zksync"]["total_airdrops"] == 1
    assert summary["zksync"]["failed_airdrops"] == 1
    assert summary["zksync"]["total_value_usd"] == Decimal("0")


def test_get_wallet_summary(tracker):
    """Test retrieving wallet summary."""
    tracker.track_airdrop("scroll", "0x1", Decimal("100"), get_current_timestamp(), True)
    tracker.track_airdrop("zksync", "0x1", Decimal("200"), get_current_timestamp(), True)
    tracker.track_airdrop("scroll", "0x2", Decimal("50"), get_current_timestamp(), False)

    summary = tracker.get_wallet_summary()
    assert isinstance(summary, dict)
    assert "0x1" in summary
    assert "0x2" in summary
    assert summary["0x1"]["total_airdrops"] == 2
    assert summary["0x1"]["successful_airdrops"] == 2
    assert summary["0x1"]["total_value_usd"] == Decimal("300")
    assert summary["0x2"]["total_airdrops"] == 1
    assert summary["0x2"]["failed_airdrops"] == 1
    assert summary["0x2"]["total_value_usd"] == Decimal("0")


def test_reset_metrics(tracker):
    """Test resetting all metrics."""
    tracker.track_airdrop("scroll", "0x1", Decimal("100"), get_current_timestamp(), True)
    tracker.reset_metrics()

    assert tracker.total_airdrops_tracked == 0
    assert tracker.total_value_tracked == Decimal("0")
    assert tracker.protocol_metrics == {}
    assert tracker.wallet_metrics == {}


def test_time_based_tracking(tracker):
    """Test that timestamps are correctly recorded and used."""
    mock_now = pendulum.datetime(2023, 1, 1, 10, 0, 0)
    pendulum.set_test_now(mock_now)

    tracker.track_airdrop("protocol_x", "wallet_a", Decimal("100"), get_current_timestamp(), True)

    pendulum.set_test_now(mock_now.add(hours=1))
    tracker.track_airdrop("protocol_x", "wallet_a", Decimal("50"), get_current_timestamp(), True)

    pendulum.set_test_now()  # Reset test time

    assert tracker.protocol_metrics["protocol_x"]["total_airdrops"] == 2
    assert tracker.protocol_metrics["protocol_x"]["total_value_usd"] == Decimal("150")
    assert tracker.wallet_metrics["wallet_a"]["total_airdrops"] == 2
    assert tracker.wallet_metrics["wallet_a"]["total_value_usd"] == Decimal("150")


def test_edge_case_zero_value_airdrop(tracker):
    """Test tracking an airdrop with zero USD value."""
    protocol = "test_protocol"
    wallet = "0xdeadbeef"
    value_usd = Decimal("0")
    timestamp = get_current_timestamp()

    tracker.track_airdrop(protocol, wallet, value_usd, timestamp, success=True)

    assert tracker.total_airdrops_tracked == 1
    assert tracker.total_value_tracked == Decimal("0")
    assert tracker.protocol_metrics[protocol]["total_value_usd"] == Decimal("0")
    assert tracker.wallet_metrics[wallet]["total_value_usd"] == Decimal("0")


def test_edge_case_empty_strings(tracker):
    """Test tracking with empty protocol or wallet strings."""
    with pytest.raises(ValueError):
        tracker.track_airdrop("", "0x1", Decimal("10"), get_current_timestamp(), True)
    with pytest.raises(ValueError):
        tracker.track_airdrop("protocol", "", Decimal("10"), get_current_timestamp(), True)
