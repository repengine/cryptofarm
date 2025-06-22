"""
Integration tests for the monitoring module.
"""

import pytest
from decimal import Decimal
import time
from unittest.mock import patch

from airdrops.monitoring.collector import MetricsCollector
from airdrops.monitoring.aggregator import MetricsAggregator
from airdrops.monitoring.alerter import Alerter
from airdrops.monitoring.health_checker import HealthChecker


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Fixture for a MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def metrics_aggregator(metrics_collector: MetricsCollector) -> MetricsAggregator:
    """Fixture for a MetricsAggregator instance."""
    return MetricsAggregator(collector=metrics_collector)


@pytest.fixture
def alerter() -> Alerter:
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
def health_checker() -> HealthChecker:
    """Fixture for a HealthChecker instance."""
    config = {
        "health_check": {
            "max_unhealthy_protocols": 1,
            "max_consecutive_failures": 3,
        }
    }
    return HealthChecker(config)


def test_end_to_end_monitoring_flow(
    metrics_collector: MetricsCollector, metrics_aggregator: MetricsAggregator, alerter: Alerter, health_checker: HealthChecker
) -> None:
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
    aggregated_metrics_list = metrics_aggregator.aggregate_time_window(0, time.time())

    scroll_success = 0
    scroll_fail = 0
    zksync_success = 0
    zksync_fail = 0

    # Debug: Print all metrics to understand the structure
    print(f"Total aggregated metrics: {len(aggregated_metrics_list)}")
    for metric in aggregated_metrics_list:
        print(f"Metric: name={metric.metric_name}, value={metric.value}, labels={metric.labels}")
        
        # The aggregator transforms task_execution_status_total into protocol_status_transactions_count
        if metric.metric_name == "scroll_success_transactions_count":
            scroll_success = int(metric.value)
        elif metric.metric_name == "scroll_failure_transactions_count":
            scroll_fail = int(metric.value)
        elif metric.metric_name == "zksync_success_transactions_count":
            zksync_success = int(metric.value)
        elif metric.metric_name == "zksync_failure_transactions_count":
            zksync_fail = int(metric.value)

    assert scroll_success == 2
    assert scroll_fail == 0
    assert zksync_success == 0
    assert zksync_fail == 3

    # Create a dictionary for the alerter (which expects a different format)
    aggregated_metrics_dict = {
        "scroll": {
            "successful_transactions": scroll_success,
            "failed_transactions": scroll_fail,
            "total_transactions": scroll_success + scroll_fail,
            "failure_rate": Decimal(scroll_fail) / Decimal(scroll_success + scroll_fail) if (scroll_success + scroll_fail) > 0 else Decimal(0)
        },
        "zksync": {
            "successful_transactions": zksync_success,
            "failed_transactions": zksync_fail,
            "total_transactions": zksync_success + zksync_fail,
            "failure_rate": Decimal(zksync_fail) / Decimal(zksync_success + zksync_fail) if (zksync_success + zksync_fail) > 0 else Decimal(0)
        }
    }

    # --- Step 3: Alerting ---
    # Mock the send_alert method to capture calls
    with patch.object(alerter, 'send_alert') as mock_send_alert:
        # Check for alerts based on aggregated metrics
        alerts_triggered = alerter.check_and_send_alerts(aggregated_metrics_dict)

        # ZkSync should trigger a failure rate alert (100% failure > 10% threshold)
        assert alerts_triggered is True
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args[0][0]
        assert "ZkSync transaction failure rate" in call_args
    assert "100.00%" in call_args

    # --- Step 4: Health Check ---
    # Update health checker with current metrics (uses the list from aggregator)
    health_checker.update_protocol_health(aggregated_metrics_list)

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
    aggregated_metrics_2 = metrics_aggregator.aggregate_time_window(0, time.time())
    health_checker.update_protocol_health(aggregated_metrics_2)

    zksync_health_after_more_fails = health_checker.get_protocol_health("zksync")
    assert zksync_health_after_more_fails["is_healthy"] is False
    assert zksync_health_after_more_fails["consecutive_failures"] == 4  # Exceeds 3

    # Overall health should still be False
    assert health_checker.check_overall_health() is False
