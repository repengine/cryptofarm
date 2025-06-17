"""
Integration tests for the monitoring module.
"""

import pytest
from decimal import Decimal

from airdrops.monitoring.collector import MetricsCollector  # type: ignore
from airdrops.monitoring.aggregator import MetricsAggregator  # type: ignore
from airdrops.monitoring.alerter import Alerter  # type: ignore
from airdrops.monitoring.health_checker import HealthChecker  # type: ignore


@pytest.fixture
def metrics_collector():
    """Fixture for a MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def metrics_aggregator():
    """Fixture for a MetricsAggregator instance."""
    return MetricsAggregator()


@pytest.fixture
def alerter():
    """Fixture for an Alerter instance."""
    config = {
        "alerting": {
            "thresholds": {
                "transaction_failure_rate": Decimal("0.1"),  # 10%
                "gas_cost_increase_factor": Decimal("1.5"),  # 50% increase
            },
            "channels": ["email", "slack"],
        }
    }
    return Alerter(config)


@pytest.fixture
def health_checker():
    """Fixture for a HealthChecker instance."""
    config = {
        "health_check": {
            "max_unhealthy_protocols": 1,
            "max_consecutive_failures": 3,
        }
    }
    return HealthChecker(config)


def test_end_to_end_monitoring_flow(
    metrics_collector, metrics_aggregator, alerter, health_checker
):
    """
    Test the full monitoring flow from collection to alerting and health check.
    """
    # --- Step 1: Collect Metrics ---
    # Simulate some successful transactions
    metrics_collector.record_transaction(
        protocol="scroll",
        action="swap",
        wallet="0x1",
        success=True,
        gas_used=50000,
        value_usd=Decimal("100"),
        tx_hash="0xabc1",
    )
    metrics_collector.record_transaction(
        protocol="scroll",
        action="bridge",
        wallet="0x2",
        success=True,
        gas_used=70000,
        value_usd=Decimal("200"),
        tx_hash="0xabc2",
    )
    # Simulate some failed transactions to trigger alerts
    metrics_collector.record_transaction(
        protocol="zksync",
        action="deposit",
        wallet="0x3",
        success=False,
        gas_used=60000,
        value_usd=Decimal("50"),
        tx_hash="0xabc3",
    )
    metrics_collector.record_transaction(
        protocol="zksync",
        action="withdraw",
        wallet="0x4",
        success=False,
        gas_used=80000,
        value_usd=Decimal("70"),
        tx_hash="0xabc4",
    )
    metrics_collector.record_transaction(
        protocol="zksync",
        action="stake",
        wallet="0x5",
        success=False,
        gas_used=90000,
        value_usd=Decimal("80"),
        tx_hash="0xabc5",
    )

    # --- Step 2: Aggregate Metrics ---
    all_raw_metrics = metrics_collector.get_all_metrics()
    aggregated_metrics = metrics_aggregator.aggregate_metrics(all_raw_metrics)

    assert "scroll" in aggregated_metrics
    assert "zksync" in aggregated_metrics
    assert aggregated_metrics["scroll"]["total_transactions"] == 2
    assert aggregated_metrics["scroll"]["successful_transactions"] == 2
    assert aggregated_metrics["zksync"]["total_transactions"] == 3
    assert aggregated_metrics["zksync"]["failed_transactions"] == 3
    assert aggregated_metrics["zksync"]["failure_rate"] == Decimal("1.0")

    # --- Step 3: Alerting ---
    # Mock the send_alert method to capture calls
    alerter.send_alert = pytest.mock.MagicMock()

    # Check for alerts based on aggregated metrics
    alerts_triggered = alerter.check_and_send_alerts(aggregated_metrics)

    # ZkSync should trigger a failure rate alert (100% failure > 10% threshold)
    assert alerts_triggered is True
    alerter.send_alert.assert_called_once()
    call_args = alerter.send_alert.call_args[0][0]
    assert "ZkSync transaction failure rate" in call_args
    assert "100.00%" in call_args

    # --- Step 4: Health Check ---
    # Update health checker with current metrics
    health_checker.update_protocol_health(aggregated_metrics)

    # Check overall system health
    overall_health = health_checker.check_overall_health()
    assert overall_health is False  # ZkSync is unhealthy

    # Check individual protocol health
    zksync_health = health_checker.get_protocol_health("zksync")
    assert zksync_health["is_healthy"] is False
    assert zksync_health["consecutive_failures"] == 3

    scroll_health = health_checker.get_protocol_health("scroll")
    assert scroll_health["is_healthy"] is True
    assert scroll_health["consecutive_failures"] == 0

    # Simulate another failed transaction for ZkSync to exceed max_consecutive_failures
    metrics_collector.record_transaction(
        protocol="zksync",
        action="another_fail",
        wallet="0x6",
        success=False,
        gas_used=100000,
        value_usd=Decimal("10"),
        tx_hash="0xabc6",
    )
    all_raw_metrics_2 = metrics_collector.get_all_metrics()
    aggregated_metrics_2 = metrics_aggregator.aggregate_metrics(all_raw_metrics_2)
    health_checker.update_protocol_health(aggregated_metrics_2)

    zksync_health_after_more_fails = health_checker.get_protocol_health("zksync")
    assert zksync_health_after_more_fails["is_healthy"] is False
    assert zksync_health_after_more_fails["consecutive_failures"] == 4  # Exceeds 3

    # Overall health should still be False
    assert health_checker.check_overall_health() is False
