"""
Monitoring Infrastructure for Airdrops Automation.

This module provides comprehensive monitoring capabilities including metrics
collection, aggregation, real-time alerting, and exposition for the airdrop
automation system.
"""

from airdrops.monitoring.collector import MetricsCollector
from airdrops.monitoring.aggregator import MetricsAggregator
from airdrops.monitoring.alerter import Alerter, AlertRule, Alert, NotificationChannel, AlertSeverity, AlertStatus

__all__ = [
    "MetricsCollector",
    "MetricsAggregator",
    "Alerter",
    "AlertRule",
    "Alert",
    "NotificationChannel",
    "AlertSeverity",
    "AlertStatus"
]
