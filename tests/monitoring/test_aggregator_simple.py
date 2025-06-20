"""Simple tests for monitoring aggregator to improve coverage."""

from unittest.mock import Mock, patch
from airdrops.monitoring.aggregator import MetricsAggregator, AggregatedMetric
import time


class TestMetricsAggregatorSimple:
    """Simple test cases for MetricsAggregator to improve coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_collector = Mock()
        # Configure the registry to be iterable by default
        self.mock_collector.registry.collect.return_value = []
        self.aggregator = MetricsAggregator(self.mock_collector)

    def test_init_with_collector(self) -> None:
        """Test MetricsAggregator initialization with collector."""
        assert self.aggregator.collector == self.mock_collector
        assert self.aggregator.metrics_buffer == []
        assert self.aggregator.aggregated_metrics == []

    def test_add_metrics_to_buffer_success(self) -> None:
        """Test successful addition of metrics to buffer."""
        metrics = {"test_metric": 100}

        with patch('airdrops.monitoring.aggregator.time.time', return_value=1234567890):
            self.aggregator.add_metrics_to_buffer(metrics)

        assert len(self.aggregator.metrics_buffer) == 1
        assert self.aggregator.metrics_buffer[0]["test_metric"] == 100
        assert self.aggregator.metrics_buffer[0]["collection_timestamp"] == 1234567890

    def test_add_metrics_to_buffer_with_timestamp(self) -> None:
        """Test adding metrics with collection timestamp."""
        metrics = {"value": 50, "collection_timestamp": 9999999999}

        self.aggregator.add_metrics_to_buffer(metrics)

        assert self.aggregator.metrics_buffer[0]["collection_timestamp"] == 9999999999

    def test_get_aggregated_metrics_empty(self) -> None:
        """Test getting aggregated metrics when empty."""
        result = self.aggregator.get_aggregated_metrics()
        assert result == []

    def test_get_aggregated_metrics_with_data(self) -> None:
        """Test getting aggregated metrics with data."""
        test_data = [
            AggregatedMetric(
                metric_name="test_metric_avg",
                value=100.0,
                timestamp=1234567890.0,
                labels={"component": "test"},
                aggregation_type="avg"
            )
        ]
        self.aggregator.aggregated_metrics = test_data

        result = self.aggregator.get_aggregated_metrics()
        assert result == test_data

    def test_process_system_metrics_basic(self) -> None:
        """Test basic system metrics processing."""
        system_metrics = {
            "cpu_usage_percent": 45.5,
            "memory_usage_percent": 60.2,
            "disk_usage_percent": 30.1
        }

        with patch('airdrops.monitoring.aggregator.time.time', return_value=1111111111):
            result = self.aggregator.process_system_metrics(system_metrics)

        assert len(result) > 0
        # Check for specific aggregated metrics
        cpu_metric = next((m for m in result if m.metric_name == "system_cpu_usage_percent_avg"), None)
        assert cpu_metric is not None
        assert cpu_metric.value == 45.5
        assert cpu_metric.timestamp == 1111111111
        assert cpu_metric.labels == {"component": "system", "type": "cpu_usage_percent"}
        assert cpu_metric.aggregation_type == "avg"

    def test_process_component_metrics_basic(self) -> None:
        """Test basic component metrics processing."""
        component_metrics = {"requests_per_second": 150, "error_rate": 0.02}
        component_name = "test_component"

        with patch('airdrops.monitoring.aggregator.time.time', return_value=2222222222):
            result = self.aggregator.process_component_metrics(component_name, component_metrics)

        assert len(result) > 0
        # Check for specific aggregated metrics
        req_metric = next((m for m in result if m.metric_name == "test_component_requests_per_second_avg"), None)
        assert req_metric is not None
        assert req_metric.value == 150.0
        assert req_metric.timestamp == 2222222222
        assert req_metric.labels == {"component": "test_component", "metric": "requests_per_second"}
        assert req_metric.aggregation_type == "avg"

    def test_process_metrics_aggregation_window_reached(self) -> None:
        """Test process_metrics when aggregation window is reached."""
        self.aggregator.aggregation_config.window_size_seconds = 1
        self.aggregator.last_aggregation_time = time.time() - 2  # Ensure window is reached

        # Mock Prometheus metrics for this test
        class MockSample:
            def __init__(self, name, value, labels):
                self.name = name
                self.value = value
                self.labels = labels

        class MockMetricFamily:
            def __init__(self, name, documentation, _type, samples):
                self.name = name
                self.documentation = documentation
                self.type = _type
                self.samples = samples

        mock_samples = [
            MockSample(
                name='test_metric',
                value=100.0,
                labels={'component': 'test', 'collection_timestamp': str(time.time())}
            )
        ]
        mock_metric_family = MockMetricFamily(
            name='test_metric',
            documentation='Test metric',
            _type='gauge',
            samples=mock_samples
        )
        self.mock_collector.registry.collect.return_value = [mock_metric_family]

        raw_metrics = {"system": {"cpu": 50}}
        with patch('airdrops.monitoring.aggregator.time.time', return_value=time.time()):
            aggregated = self.aggregator.process_metrics(raw_metrics)

        assert len(aggregated) > 0
        assert len(self.aggregator.aggregated_metrics) > 0

    def test_process_metrics_aggregation_window_not_reached(self) -> None:
        """Test process_metrics when aggregation window is not reached."""
        self.aggregator.aggregation_config.window_size_seconds = 100
        self.aggregator.last_aggregation_time = time.time() - 1  # Ensure window is not reached

        raw_metrics = {"system": {"cpu": 50}}
        aggregated = self.aggregator.process_metrics(raw_metrics)

        assert len(aggregated) == 0
        assert len(self.aggregator.aggregated_metrics) == 0

    def test_aggregate_time_window_no_metrics(self) -> None:
        """Test aggregate_time_window with no metrics in the window."""
        self.mock_collector.registry.collect.return_value = []
        result = self.aggregator.aggregate_time_window(0, time.time())
        assert result == []

    def test_aggregate_time_window_with_metrics(self) -> None:
        """Test aggregate_time_window with metrics in the window."""
        # Mock Prometheus MetricFamily and Sample objects
        class MockSample:
            def __init__(self, name, value, labels):
                self.name = name
                self.value = value
                self.labels = labels

        class MockMetricFamily:
            def __init__(self, name, documentation, _type, samples):
                self.name = name
                self.documentation = documentation
                self.type = _type
                self.samples = samples

        mock_samples = [
            MockSample(
                name='task_execution_status_total',
                value=2.0,
                labels={'protocol': 'scroll', 'status': 'success', 'collection_timestamp': str(time.time() - 10)}
            ),
            MockSample(
                name='task_execution_status_total',
                value=3.0,
                labels={'protocol': 'zksync', 'status': 'failure', 'collection_timestamp': str(time.time() - 5)}
            ),
            MockSample(
                name='some_other_metric',
                value=100.0,
                labels={'component': 'test', 'collection_timestamp': str(time.time() - 7)}
            )
        ]
        mock_metric_family = MockMetricFamily(
            name='task_execution_status_total',
            documentation='Task execution status counts',
            _type='counter',
            samples=mock_samples
        )
        self.mock_collector.registry.collect.return_value = [mock_metric_family]

        result = self.aggregator.aggregate_time_window(time.time() - 15, time.time())
        assert len(result) > 0
        
        scroll_success_metric = next((m for m in result if m.metric_name == "scroll_success_transactions_count"), None)
        assert scroll_success_metric is not None
        assert scroll_success_metric.value == 2.0

        zksync_failure_metric = next((m for m in result if m.metric_name == "zksync_failure_transactions_count"), None)
        assert zksync_failure_metric is not None
        assert zksync_failure_metric.value == 3.0

    def test_cleanup_old_metrics(self) -> None:
        """Test cleanup of old aggregated metrics."""
        self.aggregator.aggregation_config.retention_period_hours = 0.0001  # Very short retention
        self.aggregator.aggregated_metrics = [
            AggregatedMetric("old_metric", 1.0, time.time() - 1000, {}, "avg"),
            AggregatedMetric("new_metric", 2.0, time.time(), {}, "avg"),
        ]
        self.aggregator._cleanup_old_metrics()
        assert len(self.aggregator.aggregated_metrics) == 1
        assert self.aggregator.aggregated_metrics[0].metric_name == "new_metric"

    def test_generate_dashboard_data(self) -> None:
        """Test generate_dashboard_data returns expected structure."""
        result = self.aggregator.generate_dashboard_data(1, "hourly")
        assert "time_series" in result
        assert "protocol_breakdown" in result

    def test_compare_protocol_performance(self) -> None:
        """Test compare_protocol_performance returns expected structure."""
        result = self.aggregator.compare_protocol_performance()
        assert isinstance(result, list)
        assert len(result) > 0
        assert "protocol" in result[0]
