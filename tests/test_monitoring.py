"""
Tests for the monitoring infrastructure module.

This module contains comprehensive tests for MetricsCollector and MetricsAggregator
classes, covering metrics collection, aggregation, and error handling scenarios.
"""

import time
import pytest

from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from airdrops.monitoring.collector import MetricsCollector, SystemMetrics, ComponentMetrics
from airdrops.monitoring.aggregator import MetricsAggregator, AggregatedMetric, AggregationConfig


class TestMetricsCollector:
    """Test cases for MetricsCollector class."""

    def test_init_default_config(self):
        """Test MetricsCollector initialization with default configuration."""
        collector = MetricsCollector()
        
        assert collector.config == {}
        assert collector.collection_interval == 30.0
        assert collector.metrics_port == 8000
        assert collector.registry is not None

    def test_init_custom_config(self):
        """Test MetricsCollector initialization with custom configuration."""
        config = {"custom_setting": "value"}
        collector = MetricsCollector(config)
        
        assert collector.config == config

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    @patch('airdrops.monitoring.collector.psutil.virtual_memory')
    @patch('airdrops.monitoring.collector.psutil.disk_usage')
    @patch('airdrops.monitoring.collector.psutil.net_io_counters')
    def test_collect_system_metrics_success(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test successful system metrics collection."""
        # Mock psutil responses
        mock_cpu.return_value = 45.2
        mock_memory.return_value = Mock(percent=67.8)
        mock_disk.return_value = Mock(used=50000000000, total=100000000000)
        mock_net.return_value = Mock(bytes_sent=1000000, bytes_recv=2000000)
        
        collector = MetricsCollector()
        metrics = collector.collect_system_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.memory_usage_percent == 67.8
        assert metrics.disk_usage_percent == 50.0
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_recv == 2000000

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    def test_collect_system_metrics_failure(self, mock_cpu):
        """Test system metrics collection failure handling."""
        mock_cpu.side_effect = Exception("psutil error")
        
        collector = MetricsCollector()
        
        with pytest.raises(RuntimeError, match="System metrics collection failed"):
            collector.collect_system_metrics()

    def test_collect_risk_manager_metrics_success(self):
        """Test successful risk manager metrics collection."""
        # Mock risk manager
        mock_risk_manager = Mock()
        mock_risk_manager.risk_limits = Mock()
        mock_risk_manager.risk_limits.max_protocol_exposure_pct = Decimal("20.0")
        mock_risk_manager.circuit_breaker_active = False
        
        collector = MetricsCollector()
        metrics = collector.collect_risk_manager_metrics(mock_risk_manager)
        
        assert isinstance(metrics, dict)
        assert "max_protocol_exposure" in metrics
        assert "circuit_breaker_active" in metrics
        assert "risk_level" in metrics
        assert "portfolio_value_usd" in metrics
        assert metrics["max_protocol_exposure"] == 20.0
        assert metrics["circuit_breaker_active"] == 0

    def test_collect_risk_manager_metrics_circuit_breaker_active(self):
        """Test risk manager metrics with circuit breaker active."""
        mock_risk_manager = Mock()
        mock_risk_manager.circuit_breaker_active = True
        
        collector = MetricsCollector()
        metrics = collector.collect_risk_manager_metrics(mock_risk_manager)
        
        assert metrics["circuit_breaker_active"] == 1

    def test_collect_risk_manager_metrics_failure(self):
        """Test risk manager metrics collection failure handling."""
        mock_risk_manager = Mock()
        mock_risk_manager.risk_limits = Mock()
        mock_risk_manager.risk_limits.max_protocol_exposure_pct = Mock()
        mock_risk_manager.risk_limits.max_protocol_exposure_pct.side_effect = Exception("Error")
        
        collector = MetricsCollector()
        
        with pytest.raises(RuntimeError, match="Risk manager metrics collection failed"):
            collector.collect_risk_manager_metrics(mock_risk_manager)

    def test_collect_capital_allocator_metrics_with_history(self):
        """Test capital allocator metrics collection with portfolio history."""
        # Mock capital allocator with portfolio history
        mock_allocator = Mock()
        mock_portfolio_metrics = Mock()
        mock_portfolio_metrics.capital_utilization = Decimal("0.85")
        mock_portfolio_metrics.protocol_allocations = {
            "scroll": Decimal("0.30"),
            "zksync": Decimal("0.70")
        }
        mock_portfolio_metrics.total_return = Decimal("0.15")
        mock_portfolio_metrics.sharpe_ratio = Decimal("1.2")
        mock_portfolio_metrics.max_drawdown = Decimal("0.05")
        
        mock_allocator.portfolio_history = [mock_portfolio_metrics]
        
        collector = MetricsCollector()
        metrics = collector.collect_capital_allocator_metrics(mock_allocator)
        
        assert isinstance(metrics, dict)
        assert "capital_utilization_percent" in metrics
        assert "protocol_allocation_scroll" in metrics
        assert "protocol_allocation_zksync" in metrics
        assert metrics["capital_utilization_percent"] == 85.0
        assert metrics["protocol_allocation_scroll"] == 30.0
        assert metrics["protocol_allocation_zksync"] == 70.0

    def test_collect_capital_allocator_metrics_no_history(self):
        """Test capital allocator metrics collection without portfolio history."""
        mock_allocator = Mock()
        mock_allocator.portfolio_history = []
        
        collector = MetricsCollector()
        metrics = collector.collect_capital_allocator_metrics(mock_allocator)
        
        assert metrics["capital_utilization_percent"] == 0.0

    def test_collect_capital_allocator_metrics_failure(self):
        """Test capital allocator metrics collection failure handling."""
        mock_allocator = Mock()
        mock_allocator.portfolio_history = Mock()
        mock_allocator.portfolio_history.side_effect = Exception("Error")
        
        collector = MetricsCollector()
        
        with pytest.raises(RuntimeError, match="Capital allocator metrics collection failed"):
            collector.collect_capital_allocator_metrics(mock_allocator)

    def test_collect_scheduler_metrics_running(self):
        """Test scheduler metrics collection when scheduler is running."""
        mock_scheduler = Mock()
        mock_scheduler._running = True
        mock_scheduler._task_definitions = {"task1": Mock(), "task2": Mock()}
        
        # Mock task executions
        mock_execution1 = Mock()
        mock_execution1.status = Mock()
        mock_execution1.status.value = "completed"
        mock_execution2 = Mock()
        mock_execution2.status = Mock()
        mock_execution2.status.value = "pending"
        
        mock_scheduler._task_executions = {
            "task1": mock_execution1,
            "task2": mock_execution2
        }
        
        collector = MetricsCollector()
        metrics = collector.collect_scheduler_metrics(mock_scheduler)
        
        assert isinstance(metrics, dict)
        assert "scheduler_running" in metrics
        assert "total_scheduled_tasks" in metrics
        assert metrics["scheduler_running"] == 1
        assert metrics["total_scheduled_tasks"] == 2

    def test_collect_scheduler_metrics_not_running(self):
        """Test scheduler metrics collection when scheduler is not running."""
        mock_scheduler = Mock()
        mock_scheduler._running = False
        
        collector = MetricsCollector()
        metrics = collector.collect_scheduler_metrics(mock_scheduler)
        
        assert metrics["scheduler_running"] == 0

    def test_collect_scheduler_metrics_failure(self):
        """Test scheduler metrics collection failure handling."""
        mock_scheduler = Mock()
        mock_scheduler._running = Mock()
        mock_scheduler._running.side_effect = Exception("Error")
        
        collector = MetricsCollector()
        
        with pytest.raises(RuntimeError, match="Scheduler metrics collection failed"):
            collector.collect_scheduler_metrics(mock_scheduler)

    @patch('airdrops.monitoring.collector.psutil.cpu_percent')
    @patch('airdrops.monitoring.collector.psutil.virtual_memory')
    @patch('airdrops.monitoring.collector.psutil.disk_usage')
    @patch('airdrops.monitoring.collector.psutil.net_io_counters')
    def test_collect_all_metrics_success(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test successful collection of all metrics."""
        # Mock psutil responses
        mock_cpu.return_value = 45.2
        mock_memory.return_value = Mock(percent=67.8)
        mock_disk.return_value = Mock(used=50000000000, total=100000000000)
        mock_net.return_value = Mock(bytes_sent=1000000, bytes_recv=2000000)
        
        # Mock components
        mock_risk_manager = Mock()
        mock_risk_manager.circuit_breaker_active = False
        
        mock_allocator = Mock()
        mock_allocator.portfolio_history = []
        
        mock_scheduler = Mock()
        mock_scheduler._running = True
        mock_scheduler._task_definitions = {}
        mock_scheduler._task_executions = {}
        
        collector = MetricsCollector()
        
        with patch('time.time', return_value=1234567890):
            metrics = collector.collect_all_metrics(
                risk_manager=mock_risk_manager,
                capital_allocator=mock_allocator,
                scheduler=mock_scheduler
            )
        
        assert isinstance(metrics, dict)
        assert "collection_timestamp" in metrics
        assert "system" in metrics
        assert "risk_manager" in metrics
        assert "capital_allocator" in metrics
        assert "scheduler" in metrics
        assert metrics["collection_timestamp"] == 1234567890

    def test_collect_all_metrics_no_components(self):
        """Test collection of all metrics without component instances."""
        collector = MetricsCollector()
        
        with patch.object(collector, 'collect_system_metrics') as mock_system:
            mock_system.return_value = SystemMetrics(
                cpu_usage_percent=50.0,
                memory_usage_percent=60.0,
                disk_usage_percent=70.0,
                network_bytes_sent=1000,
                network_bytes_recv=2000
            )
            
            metrics = collector.collect_all_metrics()
        
        assert "system" in metrics
        assert "risk_manager" not in metrics
        assert "capital_allocator" not in metrics
        assert "scheduler" not in metrics

    def test_export_prometheus_format_success(self):
        """Test successful Prometheus format export."""
        collector = MetricsCollector()
        
        # Set some metric values
        collector.system_cpu_usage.set(45.2)
        collector.system_memory_usage.set(67.8)
        
        prometheus_data = collector.export_prometheus_format()
        
        assert isinstance(prometheus_data, bytes)
        assert b"system_cpu_usage_percent" in prometheus_data
        assert b"system_memory_usage_percent" in prometheus_data

    @patch('airdrops.monitoring.collector.generate_latest')
    def test_export_prometheus_format_failure(self, mock_generate):
        """Test Prometheus format export failure handling."""
        mock_generate.side_effect = Exception("Export error")
        
        collector = MetricsCollector()
        
        with pytest.raises(RuntimeError, match="Prometheus export failed"):
            collector.export_prometheus_format()


class TestMetricsAggregator:
    """Test cases for MetricsAggregator class."""

    def test_init_default_config(self):
        """Test MetricsAggregator initialization with default configuration."""
        aggregator = MetricsAggregator()
        
        assert aggregator.config == {}
        assert isinstance(aggregator.aggregation_config, AggregationConfig)
        assert aggregator.aggregation_config.window_size_seconds == 300
        assert aggregator.metrics_buffer == []
        assert aggregator.aggregated_metrics == []

    def test_init_custom_config(self):
        """Test MetricsAggregator initialization with custom configuration."""
        config = {"custom_setting": "value"}
        aggregator = MetricsAggregator(config)
        
        assert aggregator.config == config

    def test_add_metrics_to_buffer_success(self):
        """Test successful addition of metrics to buffer."""
        aggregator = MetricsAggregator()
        metrics = {"system": {"cpu_usage_percent": 45.2}}
        
        aggregator.add_metrics_to_buffer(metrics)
        
        assert len(aggregator.metrics_buffer) == 1
        assert "collection_timestamp" in aggregator.metrics_buffer[0]

    def test_add_metrics_to_buffer_with_timestamp(self):
        """Test addition of metrics to buffer with existing timestamp."""
        aggregator = MetricsAggregator()
        metrics = {
            "collection_timestamp": 1234567890,
            "system": {"cpu_usage_percent": 45.2}
        }
        
        aggregator.add_metrics_to_buffer(metrics)
        
        assert aggregator.metrics_buffer[0]["collection_timestamp"] == 1234567890

    def test_add_metrics_to_buffer_max_size_limit(self):
        """Test buffer size limiting functionality."""
        aggregator = MetricsAggregator()
        
        # Add metrics beyond the default max size
        with patch.dict('os.environ', {'METRICS_BUFFER_MAX_SIZE': '3'}):
            for i in range(5):
                metrics = {"system": {"cpu_usage_percent": float(i)}}
                aggregator.add_metrics_to_buffer(metrics)
        
        # Buffer should be limited to max size
        assert len(aggregator.metrics_buffer) <= 3

    def test_add_metrics_to_buffer_failure(self):
        """Test metrics buffer addition failure handling."""
        aggregator = MetricsAggregator()
        
        # Mock time.time to raise an exception
        with patch('time.time', side_effect=Exception("Time error")):
            with pytest.raises(RuntimeError, match="Buffer operation failed"):
                aggregator.add_metrics_to_buffer({})

    def test_process_system_metrics_success(self):
        """Test successful system metrics processing."""
        aggregator = MetricsAggregator()
        system_metrics = {
            "cpu_usage_percent": 45.2,
            "memory_usage_percent": 67.8,
            "disk_usage_percent": 80.0
        }
        
        with patch('time.time', return_value=1234567890):
            aggregated = aggregator.process_system_metrics(system_metrics)
        
        assert isinstance(aggregated, list)
        assert len(aggregated) > 0
        
        # Check that metrics were created for each aggregation function
        expected_functions = aggregator.aggregation_config.aggregation_functions
        assert len(aggregated) == len(system_metrics) * len(expected_functions)
        
        for metric in aggregated:
            assert isinstance(metric, AggregatedMetric)
            assert metric.timestamp == 1234567890
            assert "component" in metric.labels
            assert metric.labels["component"] == "system"

    def test_process_system_metrics_non_numeric_values(self):
        """Test system metrics processing with non-numeric values."""
        aggregator = MetricsAggregator()
        system_metrics = {
            "cpu_usage_percent": 45.2,
            "status": "healthy",  # Non-numeric value
            "memory_usage_percent": 67.8
        }
        
        aggregated = aggregator.process_system_metrics(system_metrics)
        
        # Should only process numeric values
        expected_count = 2 * len(aggregator.aggregation_config.aggregation_functions)
        assert len(aggregated) == expected_count

    def test_process_system_metrics_failure(self):
        """Test system metrics processing failure handling."""
        aggregator = MetricsAggregator()
        
        with patch('time.time', side_effect=Exception("Time error")):
            with pytest.raises(RuntimeError, match="System metrics processing failed"):
                aggregator.process_system_metrics({"cpu_usage_percent": 45.2})

    def test_process_component_metrics_success(self):
        """Test successful component metrics processing."""
        aggregator = MetricsAggregator()
        component_metrics = {
            "risk_level": 1,
            "portfolio_value_usd": 100000.0,
            "circuit_breaker_active": 0
        }
        
        with patch('time.time', return_value=1234567890):
            aggregated = aggregator.process_component_metrics("risk_manager", component_metrics)
        
        assert isinstance(aggregated, list)
        assert len(aggregated) > 0
        
        for metric in aggregated:
            assert isinstance(metric, AggregatedMetric)
            assert metric.timestamp == 1234567890
            assert "component" in metric.labels
            assert metric.labels["component"] == "risk_manager"
            assert metric.metric_name.startswith("risk_manager_")

    def test_process_component_metrics_failure(self):
        """Test component metrics processing failure handling."""
        aggregator = MetricsAggregator()
        
        with patch('time.time', side_effect=Exception("Time error")):
            with pytest.raises(RuntimeError, match="Component metrics processing failed"):
                aggregator.process_component_metrics("test_component", {"metric": 1.0})

    def test_aggregate_time_window_success(self):
        """Test successful time window aggregation."""
        aggregator = MetricsAggregator()
        
        # Add some metrics to buffer
        current_time = time.time()
        metrics1 = {
            "collection_timestamp": current_time - 100,
            "system": {"cpu_usage_percent": 45.0},
            "risk_manager": {"risk_level": 1}
        }
        metrics2 = {
            "collection_timestamp": current_time - 50,
            "system": {"cpu_usage_percent": 55.0},
            "risk_manager": {"risk_level": 2}
        }
        
        aggregator.metrics_buffer = [metrics1, metrics2]
        
        window_start = current_time - 200
        window_end = current_time
        
        aggregated = aggregator.aggregate_time_window(window_start, window_end)
        
        assert isinstance(aggregated, list)
        assert len(aggregated) > 0

    def test_aggregate_time_window_no_metrics(self):
        """Test time window aggregation with no metrics in window."""
        aggregator = MetricsAggregator()
        
        current_time = time.time()
        window_start = current_time - 200
        window_end = current_time - 100
        
        aggregated = aggregator.aggregate_time_window(window_start, window_end)
        
        assert aggregated == []

    def test_aggregate_time_window_failure(self):
        """Test time window aggregation failure handling."""
        aggregator = MetricsAggregator()
        
        # Add invalid metrics to buffer
        aggregator.metrics_buffer = [{"invalid": "data"}]
        
        with patch.object(aggregator, 'process_system_metrics', side_effect=Exception("Process error")):
            with pytest.raises(RuntimeError, match="Time window aggregation failed"):
                aggregator.aggregate_time_window(0, time.time())

    def test_process_metrics_aggregation_window_reached(self):
        """Test metrics processing when aggregation window is reached."""
        aggregator = MetricsAggregator()
        
        # Set last aggregation time to trigger aggregation
        aggregator.last_aggregation_time = time.time() - 400  # More than 300 seconds ago
        
        raw_metrics = {
            "system": {"cpu_usage_percent": 45.0},
            "risk_manager": {"risk_level": 1}
        }
        
        with patch.object(aggregator, 'aggregate_time_window') as mock_aggregate:
            mock_aggregate.return_value = [
                AggregatedMetric("test_metric", 1.0, time.time(), {}, "avg")
            ]
            
            result = aggregator.process_metrics(raw_metrics)
        
        assert isinstance(result, list)
        assert len(result) == 1
        mock_aggregate.assert_called_once()

    def test_process_metrics_aggregation_window_not_reached(self):
        """Test metrics processing when aggregation window is not reached."""
        aggregator = MetricsAggregator()
        
        # Set last aggregation time to recent time
        aggregator.last_aggregation_time = time.time() - 100  # Less than 300 seconds ago
        
        raw_metrics = {
            "system": {"cpu_usage_percent": 45.0}
        }
        
        result = aggregator.process_metrics(raw_metrics)
        
        assert result == []
        assert len(aggregator.metrics_buffer) == 1

    def test_process_metrics_failure(self):
        """Test metrics processing failure handling."""
        aggregator = MetricsAggregator()
        
        with patch.object(aggregator, 'add_metrics_to_buffer', side_effect=Exception("Buffer error")):
            with pytest.raises(RuntimeError, match="Metrics processing failed"):
                aggregator.process_metrics({"system": {"cpu": 50.0}})

    def test_get_aggregated_metrics_no_filters(self):
        """Test retrieving aggregated metrics without filters."""
        aggregator = MetricsAggregator()
        
        # Add some aggregated metrics
        metric1 = AggregatedMetric("metric1", 1.0, time.time(), {}, "avg")
        metric2 = AggregatedMetric("metric2", 2.0, time.time(), {}, "max")
        aggregator.aggregated_metrics = [metric1, metric2]
        
        result = aggregator.get_aggregated_metrics()
        
        assert len(result) == 2
        assert result[0] == metric1
        assert result[1] == metric2

    def test_get_aggregated_metrics_with_time_filters(self):
        """Test retrieving aggregated metrics with time filters."""
        aggregator = MetricsAggregator()
        
        current_time = time.time()
        metric1 = AggregatedMetric("metric1", 1.0, current_time - 100, {}, "avg")
        metric2 = AggregatedMetric("metric2", 2.0, current_time - 50, {}, "max")
        metric3 = AggregatedMetric("metric3", 3.0, current_time - 10, {}, "min")
        aggregator.aggregated_metrics = [metric1, metric2, metric3]
        
        # Filter for metrics from last 60 seconds
        result = aggregator.get_aggregated_metrics(
            start_time=current_time - 60,
            end_time=current_time
        )
        
        assert len(result) == 2  # metric2 and metric3
        assert metric1 not in result

    def test_get_aggregated_metrics_with_name_filter(self):
        """Test retrieving aggregated metrics with name filter."""
        aggregator = MetricsAggregator()
        
        metric1 = AggregatedMetric("system_cpu_avg", 1.0, time.time(), {}, "avg")
        metric2 = AggregatedMetric("system_memory_avg", 2.0, time.time(), {}, "avg")
        metric3 = AggregatedMetric("risk_level_avg", 3.0, time.time(), {}, "avg")
        aggregator.aggregated_metrics = [metric1, metric2, metric3]
        
        result = aggregator.get_aggregated_metrics(metric_name_filter="system")
        
        assert len(result) == 2  # metric1 and metric2
        assert metric3 not in result

    def test_get_aggregated_metrics_failure(self):
        """Test aggregated metrics retrieval failure handling."""
        aggregator = MetricsAggregator()
        
        # Mock aggregated_metrics to raise an exception
        with patch.object(aggregator, 'aggregated_metrics', side_effect=Exception("Access error")):
            with pytest.raises(RuntimeError, match="Metrics retrieval failed"):
                aggregator.get_aggregated_metrics()

    def test_cleanup_old_metrics_success(self):
        """Test successful cleanup of old metrics."""
        aggregator = MetricsAggregator()
        
        current_time = time.time()
        # Create metrics with different ages
        old_metric = AggregatedMetric("old", 1.0, current_time - 200000, {}, "avg")  # Very old
        recent_metric = AggregatedMetric("recent", 2.0, current_time - 1000, {}, "avg")  # Recent
        
        aggregator.aggregated_metrics = [old_metric, recent_metric]
        
        aggregator._cleanup_old_metrics()
        
        # Only recent metric should remain
        assert len(aggregator.aggregated_metrics) == 1
        assert aggregator.aggregated_metrics[0] == recent_metric

    def test_cleanup_old_metrics_failure(self):
        """Test cleanup old metrics failure handling."""
        aggregator = MetricsAggregator()
        
        with patch('time.time', side_effect=Exception("Time error")):
            # Should not raise exception, just log error
            aggregator._cleanup_old_metrics()


class TestDataClasses:
    """Test cases for data classes."""

    def test_system_metrics_creation(self):
        """Test SystemMetrics data class creation."""
        metrics = SystemMetrics(
            cpu_usage_percent=45.2,
            memory_usage_percent=67.8,
            disk_usage_percent=80.0,
            network_bytes_sent=1000000,
            network_bytes_recv=2000000
        )
        
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.memory_usage_percent == 67.8
        assert metrics.disk_usage_percent == 80.0
        assert metrics.network_bytes_sent == 1000000
        assert metrics.network_bytes_recv == 2000000

    def test_component_metrics_creation(self):
        """Test ComponentMetrics data class creation."""
        metrics = ComponentMetrics(
            component_name="risk_manager",
            status="healthy",
            last_execution_time=123.45,
            error_count=0,
            success_count=10
        )
        
        assert metrics.component_name == "risk_manager"
        assert metrics.status == "healthy"
        assert metrics.last_execution_time == 123.45
        assert metrics.error_count == 0
        assert metrics.success_count == 10

    def test_aggregated_metric_creation(self):
        """Test AggregatedMetric data class creation."""
        metric = AggregatedMetric(
            metric_name="system_cpu_avg",
            value=45.2,
            timestamp=1234567890.0,
            labels={"component": "system"},
            aggregation_type="avg"
        )
        
        assert metric.metric_name == "system_cpu_avg"
        assert metric.value == 45.2
        assert metric.timestamp == 1234567890.0
        assert metric.labels == {"component": "system"}
        assert metric.aggregation_type == "avg"

    def test_aggregation_config_creation(self):
        """Test AggregationConfig data class creation."""
        config = AggregationConfig(
            window_size_seconds=300,
            aggregation_functions=["avg", "max", "min"],
            retention_period_hours=168
        )
        
        assert config.window_size_seconds == 300
        assert config.aggregation_functions == ["avg", "max", "min"]
        assert config.retention_period_hours == 168