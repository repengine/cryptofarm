"""
Metrics Aggregation implementation for monitoring infrastructure.

This module provides the MetricsAggregator class that processes raw metrics
from the MetricsCollector and prepares them for storage and analysis.
"""

import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from decimal import Decimal

from airdrops.monitoring.collector import MetricsCollector

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AggregatedMetric:
    """Data class for aggregated metric data."""
    metric_name: str
    value: float
    timestamp: float
    labels: Dict[str, str]
    aggregation_type: str  # "avg", "sum", "max", "min", "count"


@dataclass
class AggregationConfig:
    """Configuration for metric aggregation."""
    window_size_seconds: int
    aggregation_functions: List[str]
    retention_period_hours: int


class MetricsAggregator:
    """
    Metrics Aggregator for processing and aggregating collected metrics.

    This class processes raw metrics from MetricsCollector, applies aggregation
    functions (average, sum, max, min), and prepares data for storage in
    time-series databases or analytics platforms.

    Example:
    >>> aggregator = MetricsAggregator()
    >>> aggregator.initialize()
    >>> raw_metrics = collector.collect_all_metrics()
    >>> aggregated = aggregator.process_metrics(raw_metrics)
    """

    def __init__(
        self,
        collector: "MetricsCollector",
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the Metrics Aggregator.

        Args:
            collector: The MetricsCollector instance to use.
            config: Optional configuration dictionary for aggregation settings.
        """
        self.collector = collector
        self.config = config or {}
        self.aggregation_config = self._load_aggregation_config()
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.aggregated_metrics: List[AggregatedMetric] = []
        self.last_aggregation_time = time.time()

    def _load_aggregation_config(self) -> AggregationConfig:
        """
        Load aggregation configuration from environment or defaults.

        Returns:
            AggregationConfig object with configured or default values.
        """
        return AggregationConfig(
            window_size_seconds=int(
                os.getenv("METRICS_AGGREGATION_WINDOW_SECONDS", "300")  # 5 minutes
            ),
            aggregation_functions=os.getenv(
                "METRICS_AGGREGATION_FUNCTIONS", "avg,sum,max,min,count"
            ).split(","),
            retention_period_hours=int(
                os.getenv("METRICS_RETENTION_PERIOD_HOURS", "168")  # 7 days
            ),
        )

    def add_metrics_to_buffer(self, metrics: Dict[str, Any]) -> None:
        """
        Add raw metrics to the processing buffer.

        Args:
            metrics: Raw metrics dictionary from MetricsCollector.

        Example:
            >>> raw_metrics = collector.collect_all_metrics()
            >>> aggregator.add_metrics_to_buffer(raw_metrics)
        """
        try:
            # Add timestamp if not present
            if 'collection_timestamp' not in metrics:
                metrics['collection_timestamp'] = time.time()

            self.metrics_buffer.append(metrics)

            # Limit buffer size to prevent memory issues
            max_buffer_size = int(os.getenv("METRICS_BUFFER_MAX_SIZE", "1000"))
            if len(self.metrics_buffer) > max_buffer_size:
                self.metrics_buffer = self.metrics_buffer[-max_buffer_size:]
                logger.warning(f"Metrics buffer exceeded {max_buffer_size}, truncated")

            logger.debug(
                f"Added metrics to buffer, buffer size: {len(self.metrics_buffer)}"
            )

        except Exception as e:
            logger.error(f"Failed to add metrics to buffer: {e}")
            raise RuntimeError(f"Buffer operation failed: {e}")

    def process_system_metrics(
        self,
        system_metrics: Dict[str, Any]
    ) -> List[AggregatedMetric]:
        """
        Process and aggregate system-level metrics.

        Args:
            system_metrics: System metrics dictionary.

        Returns:
            List of aggregated system metrics.

        Example:
            >>> system_data = {"cpu_usage_percent": 45.2, "memory_usage_percent": 67.8}
            >>> aggregated = aggregator.process_system_metrics(system_data)
        """
        try:
            aggregated = []
            timestamp = time.time()

            # Process each system metric
            for metric_name, value in system_metrics.items():
                if isinstance(value, (int, float)):
                    # Create aggregated metric for each configured function
                    for agg_func in self.aggregation_config.aggregation_functions:
                        aggregated_metric = AggregatedMetric(
                            metric_name=f"system_{metric_name}_{agg_func}",
                            value=float(value),
                            timestamp=timestamp,
                            labels={"component": "system", "type": metric_name},
                            aggregation_type=agg_func
                        )
                        aggregated.append(aggregated_metric)

            logger.debug(f"Processed {len(aggregated)} system metrics")
            return aggregated

        except Exception as e:
            logger.error(f"Failed to process system metrics: {e}")
            raise RuntimeError(f"System metrics processing failed: {e}")

    def process_component_metrics(
        self,
        component_name: str,
        component_metrics: Dict[str, Any]
    ) -> List[AggregatedMetric]:
        """
        Process and aggregate component-specific metrics.

        Args:
            component_name: Name of the component (e.g., "risk_manager").
            component_metrics: Component metrics dictionary.

        Returns:
            List of aggregated component metrics.

        Example:
            >>> risk_data = {"risk_level": 1, "portfolio_value_usd": 100000}
            >>> aggregated = aggregator.process_component_metrics(
            ...     "risk_manager", risk_data
            ... )
        """
        try:
            aggregated = []
            timestamp = time.time()

            # Process each component metric
            for metric_name, value in component_metrics.items():
                if isinstance(value, (int, float)):
                    # Create aggregated metric for each configured function
                    for agg_func in self.aggregation_config.aggregation_functions:
                        aggregated_metric = AggregatedMetric(
                            metric_name=f"{component_name}_{metric_name}_{agg_func}",
                            value=float(value),
                            timestamp=timestamp,
                            labels={"component": component_name, "metric": metric_name},
                            aggregation_type=agg_func
                        )
                        aggregated.append(aggregated_metric)

            logger.debug(f"Processed {len(aggregated)} {component_name} metrics")
            return aggregated

        except Exception as e:
            logger.error(f"Failed to process {component_name} metrics: {e}")
            raise RuntimeError(f"Component metrics processing failed: {e}")

    def aggregate_time_window(
        self,
        window_start: float,
        window_end: float
    ) -> List[AggregatedMetric]:
        """
        Aggregate metrics within a specific time window.

        Args:
            window_start: Start timestamp of the aggregation window.
            window_end: End timestamp of the aggregation window.

        Returns:
            List of aggregated metrics for the time window.

        Example:
            >>> start_time = time.time() - 300  # 5 minutes ago
            >>> end_time = time.time()
            >>> window_metrics = aggregator.aggregate_time_window(start_time, end_time)
        """
        try:
            aggregated_metrics_list: List[AggregatedMetric] = []
            current_time = time.time()

            # Dictionary to hold aggregated values for each unique metric + labels combination
            # Key: (metric_name, frozenset(labels.items()))
            # Value: current aggregated value
            temp_aggregated_values: Dict[Tuple[str, frozenset[Tuple[str, str]]], float] = {}

            for metric_family in self.collector.registry.collect():
                logger.info(f"Processing metric family: {metric_family.name}")
                for sample in metric_family.samples:
                    metric_name = sample.name
                    value = sample.value
                    labels = sample.labels
                    logger.info(f"  Sample: name={metric_name}, value={value}, labels={labels}")

                    # Use collection_timestamp from labels if available, otherwise use current_time
                    # Use the metric's creation timestamp if available, otherwise use current time
                    collection_timestamp = float(labels.get('collection_timestamp', current_time))
                    
                    # For metrics without explicit timestamps, be more lenient with time window
                    # Allow metrics from slightly before the current time
                    effective_window_start = window_start - 60  # Allow 60 seconds buffer
                    effective_window_end = window_end + 60  # Allow 60 seconds buffer
                    
                    logger.debug(f"Time window check for {metric_name}: "
                               f"collection_timestamp={collection_timestamp}, "
                               f"window=[{effective_window_start}, {effective_window_end}], "
                               f"current_time={current_time}, "
                               f"passes={effective_window_start <= collection_timestamp <= effective_window_end}")
                    
                    if effective_window_start <= collection_timestamp <= effective_window_end:
                        # For transaction success/failure metrics, we want to sum them up
                        if "task_execution_status_total" == metric_name:
                            protocol = labels.get("protocol", "unknown")
                            status = labels.get("status", "unknown")
                            
                            agg_metric_name = f"{protocol}_{status}_transactions_count"
                            agg_labels = frozenset({"protocol": protocol, "status": status}.items())
                            
                            key = (agg_metric_name, agg_labels)
                            temp_aggregated_values[key] = temp_aggregated_values.get(key, 0.0) + float(value)
                            
                            logger.info(f"DEBUG: Aggregating {metric_name} -> {agg_metric_name}, value={value}, "
                                       f"protocol={protocol}, status={status}, timestamp={collection_timestamp}, "
                                       f"window=[{effective_window_start}, {window_end}]")
                        else:
                            for agg_func in self.aggregation_config.aggregation_functions:
                                agg_metric_name = f"{metric_name}_{agg_func}"
                                key = (agg_metric_name, frozenset(labels.items()))
                                temp_aggregated_values[key] = float(value)

            for (metric_name, labels_frozenset), value in temp_aggregated_values.items():
                labels_dict = dict(labels_frozenset)
                
                aggregation_type = "sum"
                if "_avg" in metric_name:
                    aggregation_type = "avg"
                elif "_max" in metric_name:
                    aggregation_type = "max"
                elif "_min" in metric_name:
                    aggregation_type = "min"
                elif "_count" in metric_name:
                    aggregation_type = "count"

                aggregated_metrics_list.append(
                    AggregatedMetric(
                        metric_name=metric_name,
                        value=value,
                        timestamp=current_time,
                        labels=labels_dict,
                        aggregation_type=aggregation_type
                    )
                )

            logger.debug(f"Aggregated {len(aggregated_metrics_list)} metrics for time window "
                         f"[{window_start}, {window_end}]")
            return aggregated_metrics_list

        except Exception as e:
            logger.error(f"Failed to aggregate time window: {e}")
            raise RuntimeError(f"Time window aggregation failed: {e}")

    def process_metrics(self, raw_metrics: Dict[str, Any]) -> List[AggregatedMetric]:
        """
        Process raw metrics and return aggregated results.

        Args:
            raw_metrics: Raw metrics dictionary from MetricsCollector.

        Returns:
            List of processed and aggregated metrics.

        Example:
            >>> raw_data = collector.collect_all_metrics()
            >>> processed = aggregator.process_metrics(raw_data)
        """
        try:
            self.add_metrics_to_buffer(raw_metrics)
            aggregated = self.aggregate_time_window(0, time.time())
            self.aggregated_metrics.extend(aggregated)
            self._cleanup_old_metrics()
            return aggregated

        except Exception as e:
            logger.error(f"Failed to process metrics: {e}")
            raise RuntimeError(f"Metrics processing failed: {e}")

    def get_aggregated_metrics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        metric_name_filter: Optional[str] = None
    ) -> List[AggregatedMetric]:
        """
        Retrieve aggregated metrics with optional filtering.

        Args:
            start_time: Optional start timestamp for filtering.
            end_time: Optional end timestamp for filtering.
            metric_name_filter: Optional metric name pattern for filtering.

        Returns:
            List of filtered aggregated metrics.

        Example:
            >>> recent_metrics = aggregator.get_aggregated_metrics(
            ...     start_time=time.time() - 3600,  # Last hour
            ...     metric_name_filter="system_cpu"
            ... )
        """
        try:
            filtered_metrics = self.aggregated_metrics.copy()

            # Apply time filtering
            if start_time is not None:
                filtered_metrics = [
                    m for m in filtered_metrics if m.timestamp >= start_time
                ]

            if end_time is not None:
                filtered_metrics = [
                    m for m in filtered_metrics if m.timestamp <= end_time
                ]

            # Apply metric name filtering
            if metric_name_filter:
                filtered_metrics = [
                    m for m in filtered_metrics
                    if metric_name_filter in m.metric_name
                ]

            logger.debug(f"Retrieved {len(filtered_metrics)} filtered metrics")
            return filtered_metrics

        except Exception as e:
            logger.error(f"Failed to retrieve aggregated metrics: {e}")
            raise RuntimeError(f"Metrics retrieval failed: {e}")

    def _cleanup_old_metrics(self) -> None:
        """Clean up old aggregated metrics based on retention policy."""
        try:
            cutoff_time = time.time() - (
                self.aggregation_config.retention_period_hours * 3600
            )

            initial_count = len(self.aggregated_metrics)
            self.aggregated_metrics = [
                m for m in self.aggregated_metrics if m.timestamp > cutoff_time
            ]

            cleaned_count = initial_count - len(self.aggregated_metrics)
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old aggregated metrics")

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")

    def generate_dashboard_data(
        self, lookback_hours: int, granularity: str
    ) -> Dict[str, Any]:
        """
        Generate data suitable for monitoring dashboards.
        This is a placeholder for a more complex data generation logic.
        """
        logger.info(
            f"Generating dashboard data for last {lookback_hours} hours "
            f"with {granularity} granularity"
        )

        # Dummy data for demonstration
        time_series_data = []
        for i in range(lookback_hours):
            time_series_data.append(
                {
                    "timestamp": time.time() - (lookback_hours - i) * 3600,
                    "transaction_count": (
                        15 + (i % 5) if 9 <= i <= 17 else 5 + (i % 2)
                    ),  # More distinct activity for business hours
                    "success_rate": 0.9 + (i % 10) / 100,
                    "avg_gas_used": 100000 + (i * 1000),
                }
            )

        return {
            "time_series": time_series_data,
            "protocol_breakdown": {
                "scroll": {"total_transactions": 100, "success_rate": 0.95},
                "zksync": {"total_transactions": 80, "success_rate": 0.98},
                "eigenlayer": {"total_transactions": 50, "success_rate": 0.90},
            },
            "action_breakdown": {
                "swap": {"count": 150, "avg_value_usd": 500},
                "bridge": {"count": 80, "avg_value_usd": 1000},
            },
            "success_rate_trend": [0.9, 0.91, 0.92, 0.93, 0.94],
            "gas_usage_trend": [150000, 155000, 160000, 165000, 170000],
        }

    def compare_protocol_performance(self) -> List[Dict[str, Any]]:
        """
        Compare performance metrics across different protocols.
        This is a placeholder for a more complex comparison logic.
        """
        logger.info("Comparing protocol performance")

        # Dummy data for demonstration
        return [
            {
                "protocol": "scroll",
                "total_transactions": 100,
                "success_rate": 0.90,
                "avg_gas_used": 150000,
                "avg_value_usd": 500,
            },
            {
                "protocol": "zksync",
                "total_transactions": 80,
                "success_rate": 0.98,
                "avg_gas_used": 120000,
                "avg_value_usd": 700,
            },
            {
                "protocol": "eigenlayer",
                "total_transactions": 50,
                "success_rate": 0.95,
                "avg_gas_used": 180000,
                "avg_value_usd": 1000,
            },
        ]


def calculate_percentiles(
    values: List[float], percentiles: List[float]
) -> Dict[str, Decimal]:
    """
    Calculate percentiles for a list of numerical values.

    Args:
    values: A list of numerical values.
    percentiles: A list of percentiles to calculate (e.g., [5, 50, 95]).

    Returns:
    A dictionary mapping percentile (e.g., "p50") to its calculated value.
    """
    if not values:
        return {f"p{p}": Decimal("0.0") for p in percentiles}

    sorted_values = sorted(values)
    results = {}
    for p in percentiles:
        if not (0 <= p <= 100):
            raise ValueError("Percentile must be between 0 and 100")

        index = (len(sorted_values) - 1) * (p / 100.0)

        if index.is_integer():
            results[f"p{p}"] = Decimal(str(sorted_values[int(index)]))
        else:
            lower_idx = int(index)
            upper_idx = lower_idx + 1

            lower_val = Decimal(str(sorted_values[lower_idx]))
            upper_val = Decimal(str(sorted_values[upper_idx]))

            # Linear interpolation
            interpolated_value = (
                lower_val + (upper_val - lower_val) * Decimal(str(index - lower_idx))
            )
            results[f"p{p}"] = interpolated_value

    return results


__all__ = [
    "MetricsAggregator",
    "AggregatedMetric",
    "AggregationConfig",
    "calculate_percentiles",
]
