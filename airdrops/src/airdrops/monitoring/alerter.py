"""
Real-time Alerting System implementation for monitoring infrastructure.

This module provides the Alerter class that evaluates alert rules against
metrics from MetricsCollector/MetricsAggregator and triggers notifications
through various channels (email, Slack, webhooks).
"""

import logging
import os
import smtplib
import time
import yaml
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

import requests

# Configure logging
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    FIRING = "firing"
    RESOLVED = "resolved"
    PENDING = "pending"


@dataclass
class AlertRule:
    """Data class for alert rule definition."""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    description: str
    for_duration: int = 300  # seconds
    labels: Optional[Dict[str, str]] = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """Data class for active alert."""
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    status: AlertStatus
    description: str
    timestamp: float
    labels: Dict[str, str]
    firing_since: Optional[float] = None
    resolved_at: Optional[float] = None


@dataclass
class NotificationChannel:
    """Data class for notification channel configuration."""
    name: str
    type: str  # "email", "slack", "webhook"
    config: Dict[str, Any]
    enabled: bool = True


class Alerter:
    """
    Real-time Alerting System for monitoring infrastructure.

    Evaluates alert rules against metrics and triggers notifications through
    configured channels. Supports email, Slack, and webhook notifications.

    Example:
        >>> alerter = Alerter()
        >>> alerter.load_alert_rules("alert_rules.yaml")
        >>> alerter.load_notification_channels("notifications.yaml")
        >>> metrics = {"system_cpu_usage_percent": 85.0}
        >>> alerter.evaluate_rules(metrics)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Alerter.

        Args:
            config: Optional configuration dictionary for alerting settings.
        """
        self.config = config or {}
        self.alert_rules: List[AlertRule] = []
        self.notification_channels: List[NotificationChannel] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []

        # Configuration from environment
        self.evaluation_interval = int(
            os.getenv("ALERT_EVALUATION_INTERVAL", "60")
        )
        self.alert_retention_hours = int(
            os.getenv("ALERT_RETENTION_HOURS", "168")  # 7 days
        )

        # Condition evaluation functions
        self._condition_functions: Dict[str, Callable[[float, float], bool]] = {
            "gt": lambda x, y: x > y,
            "lt": lambda x, y: x < y,
            "eq": lambda x, y: x == y,
            "ne": lambda x, y: x != y,
            "gte": lambda x, y: x >= y,
            "lte": lambda x, y: x <= y,
        }

    def load_alert_rules(self, rules_file: str) -> None:
        """
        Load alert rules from YAML configuration file.

        Args:
            rules_file: Path to YAML file containing alert rules.

        Example:
            >>> alerter.load_alert_rules("config/alert_rules.yaml")
        """
        try:
            if not os.path.exists(rules_file):
                logger.warning(f"Alert rules file not found: {rules_file}")
                return

            with open(rules_file, 'r') as f:
                rules_config = yaml.safe_load(f)

            self.alert_rules = []
            for rule_data in rules_config.get('rules', []):
                rule = AlertRule(
                    name=rule_data['name'],
                    metric_name=rule_data['metric_name'],
                    condition=rule_data['condition'],
                    threshold=float(rule_data['threshold']),
                    severity=AlertSeverity(rule_data['severity']),
                    description=rule_data['description'],
                    for_duration=rule_data.get('for_duration', 300),
                    labels=rule_data.get('labels', {})
                )
                self.alert_rules.append(rule)

            logger.info(f"Loaded {len(self.alert_rules)} alert rules from {rules_file}")

        except Exception as e:
            logger.error(f"Failed to load alert rules from {rules_file}: {e}")
            raise RuntimeError(f"Alert rules loading failed: {e}")

    def load_notification_channels(self, channels_file: str) -> None:
        """
        Load notification channels from YAML configuration file.

        Args:
            channels_file: Path to YAML file containing notification channels.

        Example:
            >>> alerter.load_notification_channels("config/notifications.yaml")
        """
        try:
            if not os.path.exists(channels_file):
                logger.warning(f"Notification channels file not found: {channels_file}")
                return

            with open(channels_file, 'r') as f:
                channels_config = yaml.safe_load(f)

            self.notification_channels = []
            for channel_data in channels_config.get('channels', []):
                channel = NotificationChannel(
                    name=channel_data['name'],
                    type=channel_data['type'],
                    config=channel_data['config'],
                    enabled=channel_data.get('enabled', True)
                )
                self.notification_channels.append(channel)

            logger.info(
                f"Loaded {len(self.notification_channels)} notification channels"
            )

        except Exception as e:
            logger.error(
                f"Failed to load notification channels from {channels_file}: {e}"
            )
            raise RuntimeError(f"Notification channels loading failed: {e}")

    def evaluate_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate alert rules against current metrics.

        Args:
            metrics: Dictionary of current metric values.

        Returns:
            List of alerts that were triggered or resolved.

        Example:
            >>> metrics = {"system_cpu_usage_percent": 85.0}
            >>> alerts = alerter.evaluate_rules(metrics)
        """
        try:
            triggered_alerts = []
            current_time = time.time()

            for rule in self.alert_rules:
                alert_key = f"{rule.name}_{rule.metric_name}"

                # Get metric value
                metric_value = self._extract_metric_value(metrics, rule.metric_name)
                if metric_value is None:
                    continue

                # Evaluate condition
                condition_met = self._evaluate_condition(
                    metric_value, rule.condition, rule.threshold
                )

                if condition_met:
                    # Check if alert already exists
                    if alert_key in self.active_alerts:
                        alert = self.active_alerts[alert_key]
                        # Check if alert should fire (duration threshold met)
                        if (alert.status == AlertStatus.PENDING and
                                alert.firing_since is not None and
                                current_time - alert.firing_since >= rule.for_duration):
                            alert.status = AlertStatus.FIRING
                            triggered_alerts.append(alert)
                            logger.warning(f"Alert firing: {rule.name}")
                    else:
                        # Create new pending alert
                        alert = Alert(
                            rule_name=rule.name,
                            metric_name=rule.metric_name,
                            current_value=metric_value,
                            threshold=rule.threshold,
                            severity=rule.severity,
                            status=AlertStatus.PENDING,
                            description=rule.description,
                            timestamp=current_time,
                            labels=rule.labels.copy() if rule.labels else {},
                            firing_since=current_time
                        )
                        self.active_alerts[alert_key] = alert
                        logger.debug(f"Alert pending: {rule.name}")
                else:
                    # Condition not met - resolve alert if active
                    if alert_key in self.active_alerts:
                        alert = self.active_alerts[alert_key]
                        if alert.status in [AlertStatus.FIRING, AlertStatus.PENDING]:
                            alert.status = AlertStatus.RESOLVED
                            alert.resolved_at = current_time
                            triggered_alerts.append(alert)

                            # Move to history and remove from active
                            self.alert_history.append(alert)
                            del self.active_alerts[alert_key]
                            logger.info(f"Alert resolved: {rule.name}")

            # Cleanup old alerts from history
            self._cleanup_old_alerts()

            return triggered_alerts

        except Exception as e:
            logger.error(f"Failed to evaluate alert rules: {e}")
            raise RuntimeError(f"Alert rule evaluation failed: {e}")

    def send_notifications(self, alerts: List[Alert]) -> None:
        """
        Send notifications for triggered alerts.

        Args:
            alerts: List of alerts to send notifications for.

        Example:
            >>> alerts = alerter.evaluate_rules(metrics)
            >>> alerter.send_notifications(alerts)
        """
        try:
            for alert in alerts:
                for channel in self.notification_channels:
                    if not channel.enabled:
                        continue

                    try:
                        if channel.type == "email":
                            self._send_email_notification(alert, channel)
                        elif channel.type == "slack":
                            self._send_slack_notification(alert, channel)
                        elif channel.type == "webhook":
                            self._send_webhook_notification(alert, channel)
                        else:
                            logger.warning(f"Unknown notification type: {channel.type}")

                    except Exception as e:
                        logger.error(
                            f"Failed to send notification via {channel.name}: {e}"
                        )

        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
            raise RuntimeError(f"Notification sending failed: {e}")

    def _extract_metric_value(
        self, metrics: Dict[str, Any], metric_name: str
    ) -> Optional[float]:
        """Extract metric value from nested metrics dictionary."""
        try:
            # Handle nested metric paths (e.g., "system.cpu_usage_percent")
            if '.' in metric_name:
                parts = metric_name.split('.')
                value = metrics
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return None
                return float(value) if isinstance(value, (int, float)) else None
            else:
                # Direct metric name
                if metric_name in metrics:
                    value = metrics[metric_name]
                    return float(value) if isinstance(value, (int, float)) else None
                return None

        except (ValueError, TypeError, KeyError):
            return None

    def _evaluate_condition(
        self, value: float, condition: str, threshold: float
    ) -> bool:
        """Evaluate alert condition."""
        condition_func = self._condition_functions.get(condition)
        if condition_func is None:
            logger.error(f"Unknown condition: {condition}")
            return False
        return bool(condition_func(value, threshold))

    def _send_email_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> None:
        """Send email notification."""
        config = channel.config

        # Create message
        msg = MIMEMultipart()
        msg['From'] = config['from']
        msg['To'] = config['to']
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"

        # Email body
        body = f"""
Alert: {alert.rule_name}
Status: {alert.status.value}
Severity: {alert.severity.value}
Metric: {alert.metric_name}
Current Value: {alert.current_value}
Threshold: {alert.threshold}
Description: {alert.description}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}
"""
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server = smtplib.SMTP(config['smtp_host'], config.get('smtp_port', 587))
        if config.get('use_tls', True):
            server.starttls()
        if 'username' in config and 'password' in config:
            server.login(config['username'], config['password'])
        server.send_message(msg)
        server.quit()

        logger.info(f"Email notification sent for alert: {alert.rule_name}")

    def _send_slack_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> None:
        """Send Slack notification."""
        config = channel.config
        webhook_url = config['webhook_url']

        # Slack message payload
        color = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }.get(alert.severity, "warning")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"{alert.rule_name}",
                "text": alert.description,
                "fields": [
                    {"title": "Status", "value": alert.status.value, "short": True},
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Metric", "value": alert.metric_name, "short": True},
                    {
                        "title": "Value",
                        "value": str(alert.current_value),
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": str(alert.threshold),
                        "short": True
                    },
                ],
                "ts": int(alert.timestamp)
            }]
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"Slack notification sent for alert: {alert.rule_name}")

    def _send_webhook_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> None:
        """Send webhook notification."""
        config = channel.config
        webhook_url = config['url']

        # Webhook payload
        payload = {
            "alert": {
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "description": alert.description,
                "timestamp": alert.timestamp,
                "labels": alert.labels
            }
        }

        headers = config.get('headers', {})
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logger.info(f"Webhook notification sent for alert: {alert.rule_name}")

    def _cleanup_old_alerts(self) -> None:
        """Clean up old alerts from history."""
        try:
            cutoff_time = time.time() - (self.alert_retention_hours * 3600)
            initial_count = len(self.alert_history)

            self.alert_history = [
                alert for alert in self.alert_history
                if alert.timestamp >= cutoff_time
            ]

            cleaned_count = initial_count - len(self.alert_history)
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old alerts from history")

        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """
        Get list of currently active alerts.

        Returns:
            List of active alerts.

        Example:
            >>> active_alerts = alerter.get_active_alerts()
            >>> print(f"Active alerts: {len(active_alerts)}")
        """
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """
        Get alert history for specified time period.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of historical alerts.

        Example:
            >>> recent_alerts = alerter.get_alert_history(hours=6)
        """
        cutoff_time = time.time() - (hours * 3600)
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]


__all__ = [
    "Alerter",
    "AlertRule",
    "Alert",
    "NotificationChannel",
    "AlertSeverity",
    "AlertStatus"
]
