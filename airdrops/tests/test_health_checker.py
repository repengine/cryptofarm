"""
Tests for the Health Checker implementation.

This module provides comprehensive tests for the HealthChecker class,
covering positive, edge, and failure cases for all health check functionality.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from airdrops.monitoring.health_checker import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth
)


class TestHealthChecker:
    """Test cases for HealthChecker class."""

    def test_init_default_config(self):
        """Test HealthChecker initialization with default configuration."""
        health_checker = HealthChecker()

        assert health_checker.config == {}
        assert health_checker.check_interval == 30
        assert health_checker.http_port == 8001
        assert health_checker.timeout_seconds == 10.0
        assert health_checker.cpu_warning_threshold == 80.0
        assert health_checker.cpu_critical_threshold == 95.0
        assert health_checker.memory_warning_threshold == 85.0
        assert health_checker.memory_critical_threshold == 95.0

    def test_init_custom_config(self):
        """Test HealthChecker initialization with custom configuration."""
        config = {"custom_setting": "value"}

        with patch.dict('os.environ', {
            'HEALTH_CHECK_INTERVAL': '60',
            'HEALTH_CHECK_PORT': '8002',
            'HEALTH_CHECK_TIMEOUT': '20.0',
            'HEALTH_CPU_WARNING_THRESHOLD': '70.0',
            'HEALTH_CPU_CRITICAL_THRESHOLD': '90.0'
        }):
            health_checker = HealthChecker(config)

        assert health_checker.config == config
        assert health_checker.check_interval == 60
        assert health_checker.http_port == 8002
        assert health_checker.timeout_seconds == 20.0
        assert health_checker.cpu_warning_threshold == 70.0
        assert health_checker.cpu_critical_threshold == 90.0

    def test_check_system_health_all_components_healthy(self):
        """Test system health check with all components healthy."""
        health_checker = HealthChecker()

        # Mock components
        risk_manager = Mock()
        risk_manager.circuit_breaker_active = False
        risk_manager.risk_limits = Mock()

        capital_allocator = Mock()
        capital_allocator.portfolio_history = [Mock()]
        capital_allocator.allocation_strategy = Mock()
        capital_allocator.allocation_strategy.value = "equal_weight"

        scheduler = Mock()
        scheduler._running = True
        scheduler._task_definitions = {"task1": Mock()}

        metrics_collector = Mock()
        metrics_collector.registry = Mock()
        metrics_collector.collection_interval = 30

        alerter = Mock()
        alerter.alert_rules = [Mock()]
        alerter.notification_channels = [Mock()]
        alerter.active_alerts = {}

        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.used = 500000000
            mock_disk.return_value.total = 1000000000

            health_status = health_checker.check_system_health(
                risk_manager=risk_manager,
                capital_allocator=capital_allocator,
                scheduler=scheduler,
                metrics_collector=metrics_collector,
                alerter=alerter
            )

        assert health_status.overall_status == HealthStatus.OK
        assert len(health_status.components) == 7  # 5 components + system + external
        assert health_status.summary['ok_count'] >= 5
        assert health_status.summary['critical_count'] == 0

    def test_check_system_health_circuit_breaker_active(self):
        """Test system health check with circuit breaker active."""
        health_checker = HealthChecker()

        risk_manager = Mock()
        risk_manager.circuit_breaker_active = True
        risk_manager.risk_limits = Mock()

        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.used = 500000000
            mock_disk.return_value.total = 1000000000

            health_status = health_checker.check_system_health(
                risk_manager=risk_manager
            )

        assert health_status.overall_status == HealthStatus.CRITICAL

        # Find risk manager component
        risk_component = next(
            c for c in health_status.components
            if c.component_name == "risk_manager"
        )
        assert risk_component.status == HealthStatus.CRITICAL
        assert "circuit breaker" in risk_component.message.lower()

    def test_check_system_health_high_cpu_usage(self):
        """Test system health check with high CPU usage."""
        health_checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=85.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.used = 500000000
            mock_disk.return_value.total = 1000000000

            health_status = health_checker.check_system_health()

        assert health_status.overall_status == HealthStatus.WARNING

        # Find system resources component
        system_component = next(
            c for c in health_status.components
            if c.component_name == "system_resources"
        )
        assert system_component.status == HealthStatus.WARNING
        assert "High CPU usage" in system_component.message

    def test_check_system_health_critical_memory_usage(self):
        """Test system health check with critical memory usage."""
        health_checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 96.0
            mock_disk.return_value.used = 500000000
            mock_disk.return_value.total = 1000000000

            health_status = health_checker.check_system_health()

        assert health_status.overall_status == HealthStatus.CRITICAL

        # Find system resources component
        system_component = next(
            c for c in health_status.components
            if c.component_name == "system_resources"
        )
        assert system_component.status == HealthStatus.CRITICAL
        assert "Critical memory usage" in system_component.message

    def test_check_component_health_system_resources(self):
        """Test individual component health check for system resources."""
        health_checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 70.0
            mock_disk.return_value.used = 600000000
            mock_disk.return_value.total = 1000000000

            component_health = health_checker.check_component_health("system_resources")

        assert component_health is not None
        assert component_health.component_name == "system_resources"
        assert component_health.status == HealthStatus.OK
        assert component_health.metrics['cpu_usage_percent'] == 75.0
        assert component_health.metrics['memory_usage_percent'] == 70.0

    def test_check_component_health_external_dependencies(self):
        """Test individual component health check for external dependencies."""
        health_checker = HealthChecker()

        with patch.dict('os.environ', {
            'ETH_RPC_URL': 'https://eth.example.com',
            'SCROLL_L2_RPC_URL': 'https://scroll.example.com'
        }):
            component_health = health_checker.check_component_health("external_dependencies")

        assert component_health is not None
        assert component_health.component_name == "external_dependencies"
        assert component_health.status == HealthStatus.OK
        assert component_health.metrics['eth_rpc_configured'] is True
        assert component_health.metrics['scroll_rpc_configured'] is True

    def test_check_component_health_unknown_component(self):
        """Test individual component health check for unknown component."""
        health_checker = HealthChecker()

        component_health = health_checker.check_component_health("unknown_component")

        assert component_health is None

    def test_check_risk_manager_health_healthy(self):
        """Test risk manager health check when healthy."""
        health_checker = HealthChecker()

        risk_manager = Mock()
        risk_manager.circuit_breaker_active = False
        risk_manager.risk_limits = Mock()

        component_health = health_checker._check_risk_manager_health(risk_manager)

        assert component_health.component_name == "risk_manager"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "Risk Manager is healthy"
        assert component_health.metrics['circuit_breaker_active'] is False
        assert component_health.metrics['risk_limits_configured'] is True

    def test_check_risk_manager_health_circuit_breaker_active(self):
        """Test risk manager health check with circuit breaker active."""
        health_checker = HealthChecker()

        risk_manager = Mock()
        risk_manager.circuit_breaker_active = True
        risk_manager.risk_limits = Mock()

        component_health = health_checker._check_risk_manager_health(risk_manager)

        assert component_health.status == HealthStatus.CRITICAL
        assert component_health.message == "Circuit breaker is active"

    def test_check_risk_manager_health_no_risk_limits(self):
        """Test risk manager health check without risk limits."""
        health_checker = HealthChecker()

        risk_manager = Mock()
        risk_manager.circuit_breaker_active = False
        # Configure Mock to not have risk_limits attribute
        del risk_manager.risk_limits

        component_health = health_checker._check_risk_manager_health(risk_manager)

        assert component_health.status == HealthStatus.WARNING
        assert component_health.message == "Risk limits not configured"

    def test_check_capital_allocator_health_healthy(self):
        """Test capital allocator health check when healthy."""
        health_checker = HealthChecker()

        capital_allocator = Mock()
        capital_allocator.portfolio_history = [Mock(), Mock()]
        capital_allocator.allocation_strategy = Mock()
        capital_allocator.allocation_strategy.value = "risk_parity"

        component_health = health_checker._check_capital_allocator_health(capital_allocator)

        assert component_health.component_name == "capital_allocator"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "Capital Allocator is healthy"
        assert component_health.metrics['portfolio_history_length'] == 2
        assert component_health.metrics['allocation_strategy'] == "risk_parity"

    def test_check_capital_allocator_health_no_history(self):
        """Test capital allocator health check with no portfolio history."""
        health_checker = HealthChecker()

        capital_allocator = Mock()
        capital_allocator.portfolio_history = []
        capital_allocator.allocation_strategy = Mock()
        capital_allocator.allocation_strategy.value = "equal_weight"

        component_health = health_checker._check_capital_allocator_health(capital_allocator)

        assert component_health.status == HealthStatus.WARNING
        assert component_health.message == "No portfolio history available"

    def test_check_scheduler_health_healthy(self):
        """Test scheduler health check when healthy."""
        health_checker = HealthChecker()

        scheduler = Mock()
        scheduler._running = True
        scheduler._task_definitions = {"task1": Mock(), "task2": Mock()}

        component_health = health_checker._check_scheduler_health(scheduler)

        assert component_health.component_name == "scheduler"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "Scheduler is healthy"
        assert component_health.metrics['is_running'] is True
        assert component_health.metrics['task_count'] == 2

    def test_check_scheduler_health_not_running(self):
        """Test scheduler health check when not running."""
        health_checker = HealthChecker()

        scheduler = Mock()
        scheduler._running = False
        scheduler._task_definitions = {"task1": Mock()}

        component_health = health_checker._check_scheduler_health(scheduler)

        assert component_health.status == HealthStatus.CRITICAL
        assert component_health.message == "Scheduler is not running"

    def test_check_scheduler_health_no_tasks(self):
        """Test scheduler health check with no tasks defined."""
        health_checker = HealthChecker()

        scheduler = Mock()
        scheduler._running = True
        scheduler._task_definitions = {}

        component_health = health_checker._check_scheduler_health(scheduler)

        assert component_health.status == HealthStatus.WARNING
        assert component_health.message == "No tasks defined"

    def test_check_metrics_collector_health_healthy(self):
        """Test metrics collector health check when healthy."""
        health_checker = HealthChecker()

        metrics_collector = Mock()
        metrics_collector.registry = Mock()
        metrics_collector.collection_interval = 30

        component_health = health_checker._check_metrics_collector_health(metrics_collector)

        assert component_health.component_name == "metrics_collector"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "Metrics Collector is healthy"
        assert component_health.metrics['registry_configured'] is True
        assert component_health.metrics['collection_interval'] == 30

    def test_check_metrics_collector_health_no_registry(self):
        """Test metrics collector health check without registry."""
        health_checker = HealthChecker()

        metrics_collector = Mock()
        # Configure Mock to not have registry attribute
        del metrics_collector.registry

        component_health = health_checker._check_metrics_collector_health(metrics_collector)

        assert component_health.status == HealthStatus.CRITICAL
        assert component_health.message == "Metrics registry not configured"

    def test_check_alerter_health_healthy(self):
        """Test alerter health check when healthy."""
        health_checker = HealthChecker()

        alerter = Mock()
        alerter.alert_rules = [Mock(), Mock(), Mock()]
        alerter.notification_channels = [Mock(), Mock()]
        alerter.active_alerts = {"alert1": Mock()}

        component_health = health_checker._check_alerter_health(alerter)

        assert component_health.component_name == "alerter"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "Alerter is healthy"
        assert component_health.metrics['alert_rules_count'] == 3
        assert component_health.metrics['notification_channels_count'] == 2
        assert component_health.metrics['active_alerts_count'] == 1

    def test_check_alerter_health_no_rules(self):
        """Test alerter health check with no alert rules."""
        health_checker = HealthChecker()

        alerter = Mock()
        alerter.alert_rules = []
        alerter.notification_channels = [Mock()]
        alerter.active_alerts = {}

        component_health = health_checker._check_alerter_health(alerter)

        assert component_health.status == HealthStatus.WARNING
        assert component_health.message == "No alert rules configured"

    def test_check_alerter_health_no_channels(self):
        """Test alerter health check with no notification channels."""
        health_checker = HealthChecker()

        alerter = Mock()
        alerter.alert_rules = [Mock()]
        alerter.notification_channels = []
        alerter.active_alerts = {}

        component_health = health_checker._check_alerter_health(alerter)

        assert component_health.status == HealthStatus.WARNING
        assert component_health.message == "No notification channels configured"

    def test_check_external_dependencies_no_config(self):
        """Test external dependencies health check with no configuration."""
        health_checker = HealthChecker()

        with patch.dict('os.environ', {}, clear=True):
            component_health = health_checker._check_external_dependencies()

        assert component_health.component_name == "external_dependencies"
        assert component_health.status == HealthStatus.WARNING
        assert "ETH RPC URL not configured" in component_health.message

    def test_determine_overall_status_all_ok(self):
        """Test overall status determination with all components OK."""
        health_checker = HealthChecker()

        components = [
            ComponentHealth("comp1", HealthStatus.OK, "OK", time.time(), {}),
            ComponentHealth("comp2", HealthStatus.OK, "OK", time.time(), {}),
        ]

        overall_status = health_checker._determine_overall_status(components)
        assert overall_status == HealthStatus.OK

    def test_determine_overall_status_with_warnings(self):
        """Test overall status determination with warnings."""
        health_checker = HealthChecker()

        components = [
            ComponentHealth("comp1", HealthStatus.OK, "OK", time.time(), {}),
            ComponentHealth("comp2", HealthStatus.WARNING, "Warning", time.time(), {}),
        ]

        overall_status = health_checker._determine_overall_status(components)
        assert overall_status == HealthStatus.WARNING

    def test_determine_overall_status_with_critical(self):
        """Test overall status determination with critical components."""
        health_checker = HealthChecker()

        components = [
            ComponentHealth("comp1", HealthStatus.OK, "OK", time.time(), {}),
            ComponentHealth("comp2", HealthStatus.WARNING, "Warning", time.time(), {}),
            ComponentHealth("comp3", HealthStatus.CRITICAL, "Critical", time.time(), {}),
        ]

        overall_status = health_checker._determine_overall_status(components)
        assert overall_status == HealthStatus.CRITICAL

    def test_determine_overall_status_empty_components(self):
        """Test overall status determination with no components."""
        health_checker = HealthChecker()

        overall_status = health_checker._determine_overall_status([])
        assert overall_status == HealthStatus.CRITICAL

    def test_health_endpoint_success(self):
        """Test health endpoint returns successful response."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_system_health') as mock_check:
            mock_health = SystemHealth(
                overall_status=HealthStatus.OK,
                timestamp=time.time(),
                components=[
                    ComponentHealth("test", HealthStatus.OK, "OK", time.time(), {})
                ],
                summary={"total_components": 1, "ok_count": 1, "warning_count": 0, "critical_count": 0}
            )
            mock_check.return_value = mock_health

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert len(data["components"]) == 1
        assert data["summary"]["ok_count"] == 1

    def test_health_endpoint_warning_status(self):
        """Test health endpoint with warning status."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_system_health') as mock_check:
            mock_health = SystemHealth(
                overall_status=HealthStatus.WARNING,
                timestamp=time.time(),
                components=[
                    ComponentHealth("test", HealthStatus.WARNING, "Warning", time.time(), {})
                ],
                summary={"total_components": 1, "ok_count": 0, "warning_count": 1, "critical_count": 0}
            )
            mock_check.return_value = mock_health

            response = client.get("/health")

        assert response.status_code == 200  # Still operational
        data = response.json()
        assert data["status"] == "WARNING"

    def test_health_endpoint_critical_status(self):
        """Test health endpoint with critical status."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_system_health') as mock_check:
            mock_health = SystemHealth(
                overall_status=HealthStatus.CRITICAL,
                timestamp=time.time(),
                components=[
                    ComponentHealth("test", HealthStatus.CRITICAL, "Critical", time.time(), {})
                ],
                summary={"total_components": 1, "ok_count": 0, "warning_count": 0, "critical_count": 1}
            )
            mock_check.return_value = mock_health

            response = client.get("/health")

        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert data["status"] == "CRITICAL"

    def test_health_endpoint_exception(self):
        """Test health endpoint handles exceptions."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_system_health') as mock_check:
            mock_check.side_effect = Exception("Test error")

            response = client.get("/health")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "CRITICAL"
        assert "error" in data

    def test_component_health_endpoint_success(self):
        """Test component health endpoint returns successful response."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_component_health') as mock_check:
            mock_component = ComponentHealth(
                "system_resources", HealthStatus.OK, "OK", time.time(), {"cpu": 50.0}
            )
            mock_check.return_value = mock_component

            response = client.get("/health/components/system_resources")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "system_resources"
        assert data["status"] == "OK"
        assert data["metrics"]["cpu"] == 50.0

    def test_component_health_endpoint_not_found(self):
        """Test component health endpoint with unknown component."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_component_health') as mock_check:
            mock_check.return_value = None

            response = client.get("/health/components/unknown")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_component_health_endpoint_exception(self):
        """Test component health endpoint handles exceptions."""
        health_checker = HealthChecker()
        client = TestClient(health_checker.app)

        with patch.object(health_checker, 'check_component_health') as mock_check:
            mock_check.side_effect = Exception("Test error")

            response = client.get("/health/components/test")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    def test_system_health_check_exception_handling(self):
        """Test system health check handles exceptions gracefully."""
        health_checker = HealthChecker()

        with patch.object(health_checker, '_check_system_resources') as mock_check:
            mock_check.side_effect = Exception("System error")

            with pytest.raises(RuntimeError, match="Failed to check system health"):
                health_checker.check_system_health()

    def test_component_health_check_exception_handling(self):
        """Test component health check handles exceptions gracefully."""
        health_checker = HealthChecker()

        with patch.object(health_checker, '_check_system_resources') as mock_check:
            mock_check.side_effect = Exception("Component error")

            component_health = health_checker.check_component_health("system_resources")

        assert component_health.status == HealthStatus.CRITICAL
        assert "Health check failed" in component_health.message

    def test_start_server_configuration(self):
        """Test server start configuration."""
        health_checker = HealthChecker()

        with patch('uvicorn.run') as mock_run:
            health_checker.start_server("127.0.0.1")

            mock_run.assert_called_once_with(
                health_checker.app,
                host="127.0.0.1",
                port=8001,
                log_level="info"
            )

    def test_start_server_exception_handling(self):
        """Test server start handles exceptions."""
        health_checker = HealthChecker()

        with patch('uvicorn.run') as mock_run:
            mock_run.side_effect = Exception("Server error")

            with pytest.raises(RuntimeError, match="Health check server startup failed"):
                health_checker.start_server()


class TestDataClasses:
    """Test cases for data classes."""

    def test_component_health_creation(self):
        """Test ComponentHealth data class creation."""
        component_health = ComponentHealth(
            component_name="test_component",
            status=HealthStatus.OK,
            message="All good",
            last_check=1234567890.0,
            metrics={"cpu": 50.0}
        )

        assert component_health.component_name == "test_component"
        assert component_health.status == HealthStatus.OK
        assert component_health.message == "All good"
        assert component_health.last_check == 1234567890.0
        assert component_health.metrics == {"cpu": 50.0}

    def test_system_health_creation(self):
        """Test SystemHealth data class creation."""
        components = [
            ComponentHealth("comp1", HealthStatus.OK, "OK", time.time(), {})
        ]
        summary = {"total_components": 1, "ok_count": 1, "warning_count": 0, "critical_count": 0}

        system_health = SystemHealth(
            overall_status=HealthStatus.OK,
            timestamp=1234567890.0,
            components=components,
            summary=summary
        )

        assert system_health.overall_status == HealthStatus.OK
        assert system_health.timestamp == 1234567890.0
        assert len(system_health.components) == 1
        assert system_health.summary == summary


class TestEnums:
    """Test cases for enums."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.OK.value == "OK"
        assert HealthStatus.WARNING.value == "WARNING"
        assert HealthStatus.CRITICAL.value == "CRITICAL"
