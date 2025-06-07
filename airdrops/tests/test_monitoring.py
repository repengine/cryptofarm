"""
Comprehensive tests for the monitoring module.

This module tests the MetricsCollector class and related functionality
to ensure proper metrics collection from system and components.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass, asdict
from typing import Dict, Any

from airdrops.monitoring.collector import (
    MetricsCollector,
    SystemMetrics,
    ComponentMetrics
)

@dataclass
class MockRiskLimits:
    """Mock risk limits for testing."""
    max_protocol_exposure_pct: float = 0.25

@dataclass
class MockPortfolioMetrics:
    """Mock portfolio metrics for testing."""
    capital_utilization: float = 0.75
    protocol_allocations: Dict[str, float] = None
    total_return: float = 0.15
    sharpe_ratio: float = 1.2
    max_drawdown: float = -0.08

    def __post_init__(self):
        if self.protocol_allocations is None:
            self.protocol_allocations = {
                'scroll': 0.4,
                'zksync': 0.3,
                'layerzero': 0.3
            }

class MockRiskManager:
    """Mock RiskManager for testing."""

    def __init__(self, circuit_breaker_active: bool = False):
        self.risk_limits = MockRiskLimits()
        self.circuit_breaker_active = circuit_breaker_active

class MockCapitalAllocator:
    """Mock CapitalAllocator for testing."""

    def __init__(self, has_history: bool = True):
        if has_history:
            self.portfolio_history = [MockPortfolioMetrics()]
        else:
            self.portfolio_history = []

class MockTaskExecution:
    """Mock task execution for testing."""

    def __init__(self, status_value: str = "completed"):
        self.status = Mock()
        self.status.value = status_value

class MockScheduler:
    """Mock CentralScheduler for testing."""

    def __init__(self, running: bool = True, task_count: int = 5):
        self._running = running
        self._task_definitions = {f"task_{i}": f"definition_{i}" for i in range(task_count)}
        self._task_executions = {
            "exec_1": MockTaskExecution("completed"),
            "exec_2": MockTaskExecution("failed"),
            "exec_3": MockTaskExecution("running")
        }

class TestSystemMetrics:
    """Test SystemMetrics dataclass."""

    def test_system_metrics_creation(self):
        """Test SystemMetrics dataclass creation."""
        metrics = SystemMetrics(
            cpu_usage_percent=45.5,
            memory_usage_percent=67.2,
            disk_usage_percent=23.8,
            network_bytes_sent=1024000,
            network_bytes_recv=2048000
        )

        assert metrics.cpu_usage_percent == 45.5
        assert metrics.memory_usage_percent == 67.2
        assert metrics.disk_usage_percent == 23.8
        assert metrics.network_bytes_sent == 1024000
        assert metrics.network_bytes_recv == 2048000

class TestComponentMetrics:
    """Test ComponentMetrics dataclass."""

    def test_component_metrics_creation(self):
        """Test ComponentMetrics dataclass creation."""
        metrics = ComponentMetrics(
            component_name="test_component",
            status="healthy",
            last_execution_time=123.45,
            error_count=2,
            success_count=98
        )

        assert metrics.component_name == "test_component"
        assert metrics.status == "healthy"
        assert metrics.last_execution_time == 123.45
        assert metrics.error_count == 2
        assert metrics.success_count == 98

class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_init_default_config(self):
        """Test MetricsCollector initialization with default config."""
        collector = MetricsCollector()

        assert collector.config == {}
        assert collector.registry is not None
        assert collector.collection_interval == 30.0
        assert collector.metrics_port == 8000

    def test_init_custom_config(self):
        """Test MetricsCollector initialization with custom config."""
        config = {"test_key": "test_value"}
        collector = MetricsCollector(config=config)

        assert collector.config == config

    @patch.dict('os.environ', {
        'METRICS_COLLECTION_INTERVAL': '60.0',
        'METRICS_HTTP_PORT': '9090'
    })
    def test_init_environment_variables(self):
        """Test MetricsCollector initialization with environment variables."""
        collector = MetricsCollector()

        assert collector.collection_interval == 60.0
        assert collector.metrics_port == 9090

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    @patch('airdrops.monitoring.collector.psutil.virtual_memory')
    @patch('airdrops.monitoring.collector.psutil.disk_usage')
    @patch('airdrops.monitoring.collector.psutil.net_io_counters')
    def test_collect_system_metrics_success(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test successful system metrics collection."""
        # Setup mocks
        mock_cpu.return_value = 45.5

        mock_memory_obj = Mock()
        mock_memory_obj.percent = 67.2
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = Mock()
        mock_disk_obj.used = 500 * 1024**3  # 500GB
        mock_disk_obj.total = 1000 * 1024**3  # 1TB
        mock_disk.return_value = mock_disk_obj

        mock_net_obj = Mock()
        mock_net_obj.bytes_sent = 1024000
        mock_net_obj.bytes_recv = 2048000
        mock_net.return_value = mock_net_obj

        collector = MetricsCollector()
        metrics = collector.collect_system_metrics()

        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_usage_percent == 45.5
        assert metrics.memory_usage_percent == 67.2
        assert metrics.disk_usage_percent == 50.0  # 500/1000 * 100
        assert metrics.network_bytes_sent == 1024000
        assert metrics.network_bytes_recv == 2048000

        # Verify Prometheus metrics were updated
        assert collector.system_cpu_usage._value._value == 45.5
        assert collector.system_memory_usage._value._value == 67.2
        assert collector.system_disk_usage._value._value == 50.0

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    def test_collect_system_metrics_failure(self, mock_cpu):
        """Test system metrics collection failure."""
        mock_cpu.side_effect = Exception("CPU collection failed")

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="System metrics collection failed"):
            collector.collect_system_metrics()

    def test_collect_risk_manager_metrics_success(self):
        """Test successful risk manager metrics collection."""
        risk_manager = MockRiskManager(circuit_breaker_active=False)
        collector = MetricsCollector()

        metrics = collector.collect_risk_manager_metrics(risk_manager)

        assert 'max_protocol_exposure' in metrics
        assert metrics['max_protocol_exposure'] == 0.25
        assert 'circuit_breaker_active' in metrics
        assert metrics['circuit_breaker_active'] == 0
        assert 'risk_level' in metrics
        assert metrics['risk_level'] == 0
        assert 'portfolio_value_usd' in metrics
        assert metrics['portfolio_value_usd'] == 100000.0

    def test_collect_risk_manager_metrics_circuit_breaker_active(self):
        """Test risk manager metrics with circuit breaker active."""
        risk_manager = MockRiskManager(circuit_breaker_active=True)
        collector = MetricsCollector()

        metrics = collector.collect_risk_manager_metrics(risk_manager)

        assert metrics['circuit_breaker_active'] == 1

    def test_collect_risk_manager_metrics_missing_attributes(self):
        """Test risk manager metrics with missing attributes."""
        risk_manager = Mock()  # Mock without expected attributes
        # Ensure hasattr returns False for expected attributes
        del risk_manager.risk_limits
        del risk_manager.circuit_breaker_active
        collector = MetricsCollector()

        metrics = collector.collect_risk_manager_metrics(risk_manager)

        # Should still return basic metrics
        assert 'risk_level' in metrics
        assert 'portfolio_value_usd' in metrics

    def test_collect_risk_manager_metrics_failure(self):
        """Test risk manager metrics collection failure."""
        risk_manager = Mock()
        risk_manager.risk_limits = Mock()
        risk_manager.risk_limits.max_protocol_exposure_pct = Mock(side_effect=Exception("Access failed"))

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="Risk manager metrics collection failed"):
            collector.collect_risk_manager_metrics(risk_manager)

    def test_collect_capital_allocator_metrics_with_history(self):
        """Test capital allocator metrics collection with portfolio history."""
        allocator = MockCapitalAllocator(has_history=True)
        collector = MetricsCollector()

        metrics = collector.collect_capital_allocator_metrics(allocator)

        assert 'capital_utilization_percent' in metrics
        assert metrics['capital_utilization_percent'] == 0.75
        assert 'protocol_allocation_scroll' in metrics
        assert metrics['protocol_allocation_scroll'] == 40.0  # 0.4 * 100
        assert 'protocol_allocation_zksync' in metrics
        assert metrics['protocol_allocation_zksync'] == 30.0
        assert 'protocol_allocation_layerzero' in metrics
        assert metrics['protocol_allocation_layerzero'] == 30.0
        assert 'total_return' in metrics
        assert metrics['total_return'] == 0.15
        assert 'sharpe_ratio' in metrics
        assert metrics['sharpe_ratio'] == 1.2
        assert 'max_drawdown' in metrics
        assert metrics['max_drawdown'] == -0.08

    def test_collect_capital_allocator_metrics_no_history(self):
        """Test capital allocator metrics collection without portfolio history."""
        allocator = MockCapitalAllocator(has_history=False)
        collector = MetricsCollector()

        metrics = collector.collect_capital_allocator_metrics(allocator)

        assert 'capital_utilization_percent' in metrics
        assert metrics['capital_utilization_percent'] == 0.0

    def test_collect_capital_allocator_metrics_failure(self):
        """Test capital allocator metrics collection failure."""
        allocator = Mock()
        allocator.portfolio_history = Mock(side_effect=Exception("History access failed"))

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="Capital allocator metrics collection failed"):
            collector.collect_capital_allocator_metrics(allocator)

    def test_collect_scheduler_metrics_success(self):
        """Test successful scheduler metrics collection."""
        scheduler = MockScheduler(running=True, task_count=5)
        collector = MetricsCollector()

        metrics = collector.collect_scheduler_metrics(scheduler)

        assert 'scheduler_running' in metrics
        assert metrics['scheduler_running'] == 1
        assert 'total_scheduled_tasks' in metrics
        assert metrics['total_scheduled_tasks'] == 5
        assert 'tasks_completed' in metrics
        assert 'tasks_failed' in metrics
        assert 'tasks_running' in metrics

    def test_collect_scheduler_metrics_not_running(self):
        """Test scheduler metrics when scheduler is not running."""
        scheduler = MockScheduler(running=False)
        collector = MetricsCollector()

        metrics = collector.collect_scheduler_metrics(scheduler)

        assert metrics['scheduler_running'] == 0

    def test_collect_scheduler_metrics_missing_attributes(self):
        """Test scheduler metrics with missing attributes."""
        scheduler = Mock()  # Mock without expected attributes
        # Ensure hasattr returns False for expected attributes
        del scheduler._running
        del scheduler._task_definitions
        del scheduler._task_executions
        collector = MetricsCollector()

        metrics = collector.collect_scheduler_metrics(scheduler)

        # Should return empty metrics dict without errors
        assert isinstance(metrics, dict)

    def test_collect_scheduler_metrics_failure(self):
        """Test scheduler metrics collection failure."""
        scheduler = Mock()
        scheduler._running = Mock(side_effect=Exception("Running check failed"))

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="Scheduler metrics collection failed"):
            collector.collect_scheduler_metrics(scheduler)

    @patch('airdrops.monitoring.collector.time.time')
    @patch.object(MetricsCollector, 'collect_system_metrics')
    def test_collect_all_metrics_system_only(self, mock_system, mock_time):
        """Test collecting all metrics with system only."""
        mock_time.return_value = 1234567890.0
        mock_system_metrics = SystemMetrics(
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            disk_usage_percent=30.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000
        )
        mock_system.return_value = mock_system_metrics

        collector = MetricsCollector()
        metrics = collector.collect_all_metrics()

        assert 'collection_timestamp' in metrics
        assert metrics['collection_timestamp'] == 1234567890.0
        assert 'system' in metrics
        assert metrics['system']['cpu_usage_percent'] == 50.0

    @patch('airdrops.monitoring.collector.time.time')
    @patch.object(MetricsCollector, 'collect_system_metrics')
    @patch.object(MetricsCollector, 'collect_risk_manager_metrics')
    @patch.object(MetricsCollector, 'collect_capital_allocator_metrics')
    @patch.object(MetricsCollector, 'collect_scheduler_metrics')
    def test_collect_all_metrics_all_components(
        self, mock_scheduler, mock_allocator, mock_risk, mock_system, mock_time
    ):
        """Test collecting all metrics with all components."""
        mock_time.return_value = 1234567890.0
        mock_system.return_value = SystemMetrics(50.0, 60.0, 30.0, 1000, 2000)
        mock_risk.return_value = {'risk_level': 0}
        mock_allocator.return_value = {'capital_utilization_percent': 75.0}
        mock_scheduler.return_value = {'scheduler_running': 1}

        collector = MetricsCollector()
        risk_manager = MockRiskManager()
        allocator = MockCapitalAllocator()
        scheduler = MockScheduler()

        metrics = collector.collect_all_metrics(
            risk_manager=risk_manager,
            capital_allocator=allocator,
            scheduler=scheduler
        )

        assert 'collection_timestamp' in metrics
        assert 'system' in metrics
        assert 'risk_manager' in metrics
        assert 'capital_allocator' in metrics
        assert 'scheduler' in metrics

    @patch.object(MetricsCollector, 'collect_system_metrics')
    def test_collect_all_metrics_failure(self, mock_system):
        """Test collect all metrics failure."""
        mock_system.side_effect = Exception("System collection failed")

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="Metrics collection failed"):
            collector.collect_all_metrics()

    def test_export_prometheus_format_success(self):
        """Test successful Prometheus format export."""
        collector = MetricsCollector()

        # Set some metric values
        collector.system_cpu_usage.set(45.5)
        collector.system_memory_usage.set(67.2)

        prometheus_data = collector.export_prometheus_format()

        assert isinstance(prometheus_data, bytes)
        prometheus_text = prometheus_data.decode('utf-8')
        assert 'system_cpu_usage_percent' in prometheus_text
        assert 'system_memory_usage_percent' in prometheus_text
        assert '45.5' in prometheus_text
        assert '67.2' in prometheus_text

    @patch('airdrops.monitoring.collector.generate_latest')
    def test_export_prometheus_format_failure(self, mock_generate):
        """Test Prometheus format export failure."""
        mock_generate.side_effect = Exception("Export failed")

        collector = MetricsCollector()

        with pytest.raises(RuntimeError, match="Prometheus export failed"):
            collector.export_prometheus_format()

class TestIntegration:
    """Integration tests for MetricsCollector."""

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    @patch('airdrops.monitoring.collector.psutil.virtual_memory')
    @patch('airdrops.monitoring.collector.psutil.disk_usage')
    @patch('airdrops.monitoring.collector.psutil.net_io_counters')
    def test_full_metrics_collection_workflow(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test complete metrics collection workflow."""
        # Setup system mocks
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=67.2)
        mock_disk.return_value = Mock(used=500*1024**3, total=1000*1024**3)
        mock_net.return_value = Mock(bytes_sent=1024000, bytes_recv=2048000)

        # Create components
        risk_manager = MockRiskManager(circuit_breaker_active=False)
        allocator = MockCapitalAllocator(has_history=True)
        scheduler = MockScheduler(running=True, task_count=3)

        # Create collector and collect metrics
        collector = MetricsCollector()
        all_metrics = collector.collect_all_metrics(
            risk_manager=risk_manager,
            capital_allocator=allocator,
            scheduler=scheduler
        )

        # Verify all metrics are present
        assert 'collection_timestamp' in all_metrics
        assert 'system' in all_metrics
        assert 'risk_manager' in all_metrics
        assert 'capital_allocator' in all_metrics
        assert 'scheduler' in all_metrics

        # Export to Prometheus format
        prometheus_data = collector.export_prometheus_format()
        prometheus_text = prometheus_data.decode('utf-8')

        # Verify key metrics are in Prometheus output
        assert 'system_cpu_usage_percent' in prometheus_text
        assert 'component_status' in prometheus_text
        assert 'capital_utilization_percent' in prometheus_text
        assert 'scheduled_tasks_total' in prometheus_text
