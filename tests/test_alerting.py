"""
Tests for the alerting system implementation.

This module provides comprehensive test coverage for the Alerter class,
including rule evaluation, notification sending, and configuration loading.
"""

import os
import tempfile
import time
import yaml

import pytest
from unittest.mock import patch, Mock

from airdrops.monitoring.alerter import (
    Alerter, AlertRule, Alert, NotificationChannel,
    AlertSeverity, AlertStatus
)


class TestAlerter:
    """Test cases for the Alerter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.alerter = Alerter()

        # Sample alert rule
        self.sample_rule = AlertRule(
            name="test_cpu_alert",
            metric_name="system.cpu_usage_percent",
            condition="gt",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            description="CPU usage is high",
            for_duration=60,
            labels={"component": "system"}
        )

        # Sample notification channel
        self.sample_channel = NotificationChannel(
            name="test_email",
            type="email",
            config={
                "smtp_host": "localhost",
                "smtp_port": 587,
                "from": "test@example.com",
                "to": "admin@example.com"
            }
        )

    def test_init_default_config(self):
        """Test Alerter initialization with default configuration."""
        alerter = Alerter()

        assert alerter.config == {}
        assert alerter.alert_rules == []
        assert alerter.notification_channels == []
        assert alerter.active_alerts == {}
        assert alerter.alert_history == []
        assert alerter.evaluation_interval == 60
        assert alerter.alert_retention_hours == 168

    def test_init_custom_config(self):
        """Test Alerter initialization with custom configuration."""
        config = {"custom_setting": "value"}
        alerter = Alerter(config)

        assert alerter.config == config

    def test_load_alert_rules_success(self):
        """Test successful loading of alert rules from YAML file."""
        rules_data = {
            "rules": [
                {
                    "name": "cpu_alert",
                    "metric_name": "cpu_usage",
                    "condition": "gt",
                    "threshold": 80.0,
                    "severity": "high",
                    "description": "High CPU usage",
                    "for_duration": 300,
                    "labels": {"component": "system"}
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(rules_data, f)
            rules_file = f.name

        try:
            self.alerter.load_alert_rules(rules_file)

            assert len(self.alerter.alert_rules) == 1
            rule = self.alerter.alert_rules[0]
            assert rule.name == "cpu_alert"
            assert rule.metric_name == "cpu_usage"
            assert rule.condition == "gt"
            assert rule.threshold == 80.0
            assert rule.severity == AlertSeverity.HIGH

        finally:
            os.unlink(rules_file)

    def test_load_alert_rules_file_not_found(self):
        """Test loading alert rules when file doesn't exist."""
        self.alerter.load_alert_rules("nonexistent_file.yaml")
        assert len(self.alerter.alert_rules) == 0

    def test_load_alert_rules_invalid_yaml(self):
        """Test loading alert rules with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            rules_file = f.name

        try:
            with pytest.raises(RuntimeError, match="Alert rules loading failed"):
                self.alerter.load_alert_rules(rules_file)
        finally:
            os.unlink(rules_file)

    def test_load_notification_channels_success(self):
        """Test successful loading of notification channels."""
        channels_data = {
            "channels": [
                {
                    "name": "email_alerts",
                    "type": "email",
                    "config": {
                        "smtp_host": "localhost",
                        "from": "test@example.com",
                        "to": "admin@example.com"
                    },
                    "enabled": True
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(channels_data, f)
            channels_file = f.name

        try:
            self.alerter.load_notification_channels(channels_file)

            assert len(self.alerter.notification_channels) == 1
            channel = self.alerter.notification_channels[0]
            assert channel.name == "email_alerts"
            assert channel.type == "email"
            assert channel.enabled is True

        finally:
            os.unlink(channels_file)

    def test_load_notification_channels_file_not_found(self):
        """Test loading notification channels when file doesn't exist."""
        self.alerter.load_notification_channels("nonexistent_file.yaml")
        assert len(self.alerter.notification_channels) == 0

    def test_evaluate_rules_condition_met_new_alert(self):
        """Test rule evaluation when condition is met for new alert."""
        self.alerter.alert_rules = [self.sample_rule]
        metrics = {"system": {"cpu_usage_percent": 85.0}}

        alerts = self.alerter.evaluate_rules(metrics)

        # Should create pending alert but not fire yet
        assert len(alerts) == 0
        assert len(self.alerter.active_alerts) == 1

        alert_key = "test_cpu_alert_system.cpu_usage_percent"
        alert = self.alerter.active_alerts[alert_key]
        assert alert.status == AlertStatus.PENDING
        assert alert.current_value == 85.0

    def test_evaluate_rules_condition_met_alert_fires(self):
        """Test rule evaluation when alert should fire after duration."""
        self.alerter.alert_rules = [self.sample_rule]

        # Create existing pending alert that's been pending long enough
        current_time = time.time()
        alert_key = "test_cpu_alert_system.cpu_usage_percent"
        existing_alert = Alert(
            rule_name="test_cpu_alert",
            metric_name="system.cpu_usage_percent",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.PENDING,
            description="CPU usage is high",
            timestamp=current_time,
            labels={"component": "system"},
            firing_since=current_time - 120  # 2 minutes ago
        )
        self.alerter.active_alerts[alert_key] = existing_alert

        metrics = {"system": {"cpu_usage_percent": 85.0}}
        alerts = self.alerter.evaluate_rules(metrics)

        # Should fire the alert
        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.FIRING

    def test_evaluate_rules_condition_not_met_resolves_alert(self):
        """Test rule evaluation when condition is not met and alert resolves."""
        self.alerter.alert_rules = [self.sample_rule]

        # Create existing firing alert
        current_time = time.time()
        alert_key = "test_cpu_alert_system.cpu_usage_percent"
        existing_alert = Alert(
            rule_name="test_cpu_alert",
            metric_name="system.cpu_usage_percent",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="CPU usage is high",
            timestamp=current_time,
            labels={"component": "system"},
            firing_since=current_time - 120
        )
        self.alerter.active_alerts[alert_key] = existing_alert

        metrics = {"system": {"cpu_usage_percent": 70.0}}  # Below threshold
        alerts = self.alerter.evaluate_rules(metrics)

        # Should resolve the alert
        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.RESOLVED
        assert alert_key not in self.alerter.active_alerts
        assert len(self.alerter.alert_history) == 1

    def test_evaluate_rules_metric_not_found(self):
        """Test rule evaluation when metric is not found."""
        self.alerter.alert_rules = [self.sample_rule]
        metrics = {"other": {"metric": 50.0}}  # Missing target metric

        alerts = self.alerter.evaluate_rules(metrics)

        assert len(alerts) == 0
        assert len(self.alerter.active_alerts) == 0

    def test_evaluate_rules_invalid_condition(self):
        """Test rule evaluation with invalid condition."""
        invalid_rule = AlertRule(
            name="test_alert",
            metric_name="test_metric",
            condition="invalid_condition",
            threshold=50.0,
            severity=AlertSeverity.LOW,
            description="Test alert"
        )
        self.alerter.alert_rules = [invalid_rule]
        metrics = {"test_metric": 60.0}

        alerts = self.alerter.evaluate_rules(metrics)

        assert len(alerts) == 0
        assert len(self.alerter.active_alerts) == 0

    def test_extract_metric_value_nested_path(self):
        """Test extracting metric value from nested path."""
        metrics = {"system": {"cpu_usage_percent": 75.0}}

        value = self.alerter._extract_metric_value(metrics, "system.cpu_usage_percent")
        assert value == 75.0

    def test_extract_metric_value_direct_path(self):
        """Test extracting metric value from direct path."""
        metrics = {"cpu_usage": 80.0}

        value = self.alerter._extract_metric_value(metrics, "cpu_usage")
        assert value == 80.0

    def test_extract_metric_value_not_found(self):
        """Test extracting metric value when path doesn't exist."""
        metrics = {"other": {"metric": 50.0}}

        value = self.alerter._extract_metric_value(metrics, "system.cpu_usage")
        assert value is None

    def test_extract_metric_value_invalid_type(self):
        """Test extracting metric value with invalid type."""
        metrics = {"metric": "not_a_number"}

        value = self.alerter._extract_metric_value(metrics, "metric")
        assert value is None

    def test_evaluate_condition_greater_than(self):
        """Test condition evaluation for greater than."""
        assert self.alerter._evaluate_condition(85.0, "gt", 80.0) is True
        assert self.alerter._evaluate_condition(75.0, "gt", 80.0) is False

    def test_evaluate_condition_less_than(self):
        """Test condition evaluation for less than."""
        assert self.alerter._evaluate_condition(75.0, "lt", 80.0) is True
        assert self.alerter._evaluate_condition(85.0, "lt", 80.0) is False

    def test_evaluate_condition_equal(self):
        """Test condition evaluation for equal."""
        assert self.alerter._evaluate_condition(80.0, "eq", 80.0) is True
        assert self.alerter._evaluate_condition(75.0, "eq", 80.0) is False

    def test_evaluate_condition_not_equal(self):
        """Test condition evaluation for not equal."""
        assert self.alerter._evaluate_condition(75.0, "ne", 80.0) is True
        assert self.alerter._evaluate_condition(80.0, "ne", 80.0) is False

    def test_evaluate_condition_greater_than_equal(self):
        """Test condition evaluation for greater than or equal."""
        assert self.alerter._evaluate_condition(80.0, "gte", 80.0) is True
        assert self.alerter._evaluate_condition(85.0, "gte", 80.0) is True
        assert self.alerter._evaluate_condition(75.0, "gte", 80.0) is False

    def test_evaluate_condition_less_than_equal(self):
        """Test condition evaluation for less than or equal."""
        assert self.alerter._evaluate_condition(80.0, "lte", 80.0) is True
        assert self.alerter._evaluate_condition(75.0, "lte", 80.0) is True
        assert self.alerter._evaluate_condition(85.0, "lte", 80.0) is False

    @patch('smtplib.SMTP')
    def test_send_email_notification_success(self, mock_smtp):
        """Test successful email notification sending."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        channel = NotificationChannel(
            name="email_test",
            type="email",
            config={
                "smtp_host": "localhost",
                "smtp_port": 587,
                "from": "test@example.com",
                "to": "admin@example.com",
                "use_tls": True,
                "username": "user",
                "password": "pass"
            }
        )

        self.alerter._send_email_notification(alert, channel)

        mock_smtp.assert_called_once_with("localhost", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('requests.post')
    def test_send_slack_notification_success(self, mock_post):
        """Test successful Slack notification sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        channel = NotificationChannel(
            name="slack_test",
            type="slack",
            config={"webhook_url": "https://hooks.slack.com/test"}
        )

        self.alerter._send_slack_notification(alert, channel)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['attachments'][0]['title'] == "test_alert"

    @patch('requests.post')
    def test_send_webhook_notification_success(self, mock_post):
        """Test successful webhook notification sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        channel = NotificationChannel(
            name="webhook_test",
            type="webhook",
            config={
                "url": "https://example.com/webhook",
                "headers": {"Authorization": "Bearer token"}
            }
        )

        self.alerter._send_webhook_notification(alert, channel)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://example.com/webhook"
        assert call_args[1]['headers']['Authorization'] == "Bearer token"

    def test_send_notifications_disabled_channel(self):
        """Test that disabled channels are skipped."""
        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        disabled_channel = NotificationChannel(
            name="disabled_test",
            type="email",
            config={},
            enabled=False
        )

        self.alerter.notification_channels = [disabled_channel]

        # Should not raise any exceptions
        self.alerter.send_notifications([alert])

    def test_send_notifications_unknown_channel_type(self):
        """Test handling of unknown notification channel type."""
        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        unknown_channel = NotificationChannel(
            name="unknown_test",
            type="unknown_type",
            config={}
        )

        self.alerter.notification_channels = [unknown_channel]

        # Should not raise any exceptions
        self.alerter.send_notifications([alert])

    def test_get_active_alerts(self):
        """Test getting list of active alerts."""
        alert = Alert(
            rule_name="test_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={}
        )

        self.alerter.active_alerts["test_key"] = alert

        active_alerts = self.alerter.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0] == alert

    def test_get_alert_history(self):
        """Test getting alert history with time filtering."""
        current_time = time.time()

        # Recent alert (within 24 hours)
        recent_alert = Alert(
            rule_name="recent_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.RESOLVED,
            description="Recent alert",
            timestamp=current_time - 3600,  # 1 hour ago
            labels={}
        )

        # Old alert (older than 24 hours)
        old_alert = Alert(
            rule_name="old_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.RESOLVED,
            description="Old alert",
            timestamp=current_time - 86400 - 3600,  # 25 hours ago
            labels={}
        )

        self.alerter.alert_history = [recent_alert, old_alert]

        # Get last 24 hours
        recent_history = self.alerter.get_alert_history(hours=24)
        assert len(recent_history) == 1
        assert recent_history[0] == recent_alert

        # Get last 48 hours
        extended_history = self.alerter.get_alert_history(hours=48)
        assert len(extended_history) == 2

    def test_cleanup_old_alerts(self):
        """Test cleanup of old alerts from history."""
        current_time = time.time()

        # Recent alert
        recent_alert = Alert(
            rule_name="recent_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.RESOLVED,
            description="Recent alert",
            timestamp=current_time - 3600,  # 1 hour ago
            labels={}
        )

        # Very old alert (older than retention period)
        old_alert = Alert(
            rule_name="old_alert",
            metric_name="test_metric",
            current_value=85.0,
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.RESOLVED,
            description="Old alert",
            timestamp=current_time - (168 * 3600) - 3600,  # Older than 7 days
            labels={}
        )

        self.alerter.alert_history = [recent_alert, old_alert]
        self.alerter._cleanup_old_alerts()

        # Should only keep recent alert
        assert len(self.alerter.alert_history) == 1
        assert self.alerter.alert_history[0] == recent_alert


class TestDataClasses:
    """Test cases for data classes."""

    def test_alert_rule_creation(self):
        """Test AlertRule data class creation."""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            condition="gt",
            threshold=50.0,
            severity=AlertSeverity.MEDIUM,
            description="Test rule"
        )

        assert rule.name == "test_rule"
        assert rule.metric_name == "test_metric"
        assert rule.condition == "gt"
        assert rule.threshold == 50.0
        assert rule.severity == AlertSeverity.MEDIUM
        assert rule.description == "Test rule"
        assert rule.for_duration == 300  # Default
        assert rule.labels == {}  # Default

    def test_alert_rule_with_custom_values(self):
        """Test AlertRule with custom values."""
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            condition="lt",
            threshold=25.0,
            severity=AlertSeverity.CRITICAL,
            description="Test rule",
            for_duration=600,
            labels={"env": "prod"}
        )

        assert rule.for_duration == 600
        assert rule.labels == {"env": "prod"}

    def test_alert_creation(self):
        """Test Alert data class creation."""
        alert = Alert(
            rule_name="test_rule",
            metric_name="test_metric",
            current_value=75.0,
            threshold=50.0,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            description="Test alert",
            timestamp=time.time(),
            labels={"component": "test"}
        )

        assert alert.rule_name == "test_rule"
        assert alert.metric_name == "test_metric"
        assert alert.current_value == 75.0
        assert alert.threshold == 50.0
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.FIRING
        assert alert.description == "Test alert"
        assert alert.labels == {"component": "test"}
        assert alert.firing_since is None  # Default
        assert alert.resolved_at is None  # Default

    def test_notification_channel_creation(self):
        """Test NotificationChannel data class creation."""
        channel = NotificationChannel(
            name="test_channel",
            type="email",
            config={"smtp_host": "localhost"}
        )

        assert channel.name == "test_channel"
        assert channel.type == "email"
        assert channel.config == {"smtp_host": "localhost"}
        assert channel.enabled is True  # Default

    def test_notification_channel_disabled(self):
        """Test NotificationChannel with disabled flag."""
        channel = NotificationChannel(
            name="test_channel",
            type="slack",
            config={"webhook_url": "https://example.com"},
            enabled=False
        )

        assert channel.enabled is False


class TestEnums:
    """Test cases for enum classes."""

    def test_alert_severity_values(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_status_values(self):
        """Test AlertStatus enum values."""
        assert AlertStatus.FIRING.value == "firing"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.PENDING.value == "pending"
