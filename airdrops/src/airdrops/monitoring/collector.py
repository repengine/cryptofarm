"""
Metrics Collection implementation for monitoring infrastructure.

This module provides the MetricsCollector class that collects metrics from
Phase 3 components (RiskManager, CapitalAllocator, CentralScheduler) and
system-level metrics, exposing them in Prometheus exposition format.
"""

import logging
import os
import psutil
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry
from prometheus_client import generate_latest


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Data class for system-level metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int


@dataclass
class ComponentMetrics:
    """Data class for component-specific metrics."""
    component_name: str
    status: str
    last_execution_time: float
    error_count: int
    success_count: int


class MetricsCollector:
    """
    Metrics Collector for the Airdrops Automation System.

    Collects metrics from Phase 3 components (RiskManager, CapitalAllocator,
    CentralScheduler) and system-level metrics, exposing them in Prometheus
    exposition format for monitoring and alerting.

    Example:
        >>> collector = MetricsCollector()
        >>> collector.initialize()
        >>> metrics_data = collector.collect_all_metrics()
        >>> prometheus_output = collector.export_prometheus_format()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Metrics Collector.

        Args:
            config: Optional configuration dictionary for metrics collection.
        """
        self.config = config or {}
        self.registry = CollectorRegistry()
        self._initialize_prometheus_metrics()
        self.collection_interval = float(
            os.getenv("METRICS_COLLECTION_INTERVAL", "30.0")
        )
        self.metrics_port = int(
            os.getenv("METRICS_HTTP_PORT", "8000")
        )

    def _initialize_prometheus_metrics(self) -> None:
        """Initialize Prometheus metric objects."""
        # System metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )

        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )

        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'Disk usage percentage',
            registry=self.registry
        )

        # Component metrics
        self.component_status = Gauge(
            'component_status',
            'Component status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )

        self.component_execution_time = Histogram(
            'component_execution_seconds',
            'Component execution time in seconds',
            ['component'],
            registry=self.registry
        )

        self.component_errors_total = Counter(
            'component_errors_total',
            'Total number of component errors',
            ['component'],
            registry=self.registry
        )

        # Risk management metrics
        self.risk_level = Gauge(
            'risk_level',
            'Current risk level (0=low, 1=medium, 2=high, 3=critical)',
            registry=self.registry
        )

        self.portfolio_value = Gauge(
            'portfolio_value_usd',
            'Current portfolio value in USD',
            registry=self.registry
        )

        # Capital allocation metrics
        self.capital_utilization = Gauge(
            'capital_utilization_percent',
            'Capital utilization percentage',
            registry=self.registry
        )

        self.protocol_allocation = Gauge(
            'protocol_allocation_percent',
            'Protocol allocation percentage',
            ['protocol'],
            registry=self.registry
        )

        # Scheduler metrics
        self.scheduled_tasks_total = Gauge(
            'scheduled_tasks_total',
            'Total number of scheduled tasks',
            registry=self.registry
        )

        self.task_execution_status = Counter(
            'task_execution_status_total',
            'Task execution status counts',
            ['status'],
            registry=self.registry
        )

    def collect_system_metrics(self) -> SystemMetrics:
        """
        Collect system-level metrics (CPU, memory, disk, network).

        Returns:
            SystemMetrics object with current system metrics.

        Example:
            >>> metrics = collector.collect_system_metrics()
            >>> print(f"CPU usage: {metrics.cpu_usage_percent}%")
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage (root partition)
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()

            metrics = SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_percent,
                disk_usage_percent=disk_percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv
            )

            # Update Prometheus metrics
            self.system_cpu_usage.set(cpu_percent)
            self.system_memory_usage.set(memory_percent)
            self.system_disk_usage.set(disk_percent)

            logger.debug(f"Collected system metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            raise RuntimeError(f"System metrics collection failed: {e}")

    def collect_risk_manager_metrics(self, risk_manager: Any) -> Dict[str, Any]:
        """
        Collect metrics from RiskManager component.

        Args:
            risk_manager: RiskManager instance to collect metrics from.

        Returns:
            Dictionary containing risk management metrics.

        Example:
            >>> from airdrops.risk_management.core import RiskManager
            >>> risk_mgr = RiskManager()
            >>> metrics = collector.collect_risk_manager_metrics(risk_mgr)
        """
        try:
            metrics = {}

            # Check if risk manager has the expected attributes/methods
            if hasattr(risk_manager, 'risk_limits'):
                metrics['max_protocol_exposure'] = float(
                    risk_manager.risk_limits.max_protocol_exposure_pct
                )

            if hasattr(risk_manager, 'circuit_breaker_active'):
                circuit_breaker_status = 1 if risk_manager.circuit_breaker_active else 0
                metrics['circuit_breaker_active'] = circuit_breaker_status
                self.component_status.labels(component='risk_manager').set(
                    0 if risk_manager.circuit_breaker_active else 1
                )

            # Mock risk level for now (would be calculated from actual risk assessment)
            risk_level_value = 0  # 0=low, 1=medium, 2=high, 3=critical
            self.risk_level.set(risk_level_value)
            metrics['risk_level'] = risk_level_value

            # Mock portfolio value
            portfolio_value = 100000.0  # Would come from actual portfolio assessment
            self.portfolio_value.set(portfolio_value)
            metrics['portfolio_value_usd'] = portfolio_value

            logger.debug(f"Collected risk manager metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect risk manager metrics: {e}")
            self.component_errors_total.labels(component='risk_manager').inc()
            raise RuntimeError(f"Risk manager metrics collection failed: {e}")

    def collect_capital_allocator_metrics(self, allocator: Any) -> Dict[str, Any]:
        """
        Collect metrics from CapitalAllocator component.

        Args:
            allocator: CapitalAllocator instance to collect metrics from.

        Returns:
            Dictionary containing capital allocation metrics.

        Example:
            >>> from airdrops.capital_allocation.engine import CapitalAllocator
            >>> allocator = CapitalAllocator()
            >>> metrics = collector.collect_capital_allocator_metrics(allocator)
        """
        try:
            metrics = {}

            # Check if allocator has portfolio history
            if hasattr(allocator, 'portfolio_history') and allocator.portfolio_history:
                latest_metrics = allocator.portfolio_history[-1]

                # Capital utilization
                utilization = float(latest_metrics.capital_utilization)
                self.capital_utilization.set(utilization)
                metrics['capital_utilization_percent'] = utilization

                # Protocol allocations
                for protocol, allocation in latest_metrics.protocol_allocations.items():
                    allocation_percent = float(allocation) * 100
                    self.protocol_allocation.labels(protocol=protocol).set(
                        allocation_percent
                    )
                    metrics[f'protocol_allocation_{protocol}'] = allocation_percent

                # Portfolio performance
                metrics['total_return'] = float(latest_metrics.total_return)
                metrics['sharpe_ratio'] = float(latest_metrics.sharpe_ratio)
                metrics['max_drawdown'] = float(latest_metrics.max_drawdown)
            else:
                # Default values if no history available
                self.capital_utilization.set(0.0)
                metrics['capital_utilization_percent'] = 0.0

            self.component_status.labels(component='capital_allocator').set(1)

            logger.debug(f"Collected capital allocator metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect capital allocator metrics: {e}")
            self.component_errors_total.labels(component='capital_allocator').inc()
            raise RuntimeError(f"Capital allocator metrics collection failed: {e}")

    def collect_scheduler_metrics(self, scheduler: Any) -> Dict[str, Any]:
        """
        Collect metrics from CentralScheduler component.

        Args:
            scheduler: CentralScheduler instance to collect metrics from.

        Returns:
            Dictionary containing scheduler metrics.

        Example:
            >>> from airdrops.scheduler.bot import CentralScheduler
            >>> scheduler = CentralScheduler()
            >>> metrics = collector.collect_scheduler_metrics(scheduler)
        """
        try:
            metrics = {}

            # Check scheduler status
            if hasattr(scheduler, '_running'):
                scheduler_status = 1 if scheduler._running else 0
                self.component_status.labels(component='scheduler').set(
                    scheduler_status
                )
                metrics['scheduler_running'] = scheduler_status

            # Task counts
            if hasattr(scheduler, '_task_definitions'):
                total_tasks = len(scheduler._task_definitions)
                self.scheduled_tasks_total.set(total_tasks)
                metrics['total_scheduled_tasks'] = total_tasks

            # Task execution status counts
            if hasattr(scheduler, '_task_executions'):
                status_counts: Dict[str, int] = {}
                for execution in scheduler._task_executions.values():
                    status = execution.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1

                for status, count in status_counts.items():
                    self.task_execution_status.labels(status=status).inc(count)
                    metrics[f'tasks_{status}'] = count

            logger.debug(f"Collected scheduler metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect scheduler metrics: {e}")
            self.component_errors_total.labels(component='scheduler').inc()
            raise RuntimeError(f"Scheduler metrics collection failed: {e}")

    def collect_all_metrics(
        self,
        risk_manager: Optional[Any] = None,
        capital_allocator: Optional[Any] = None,
        scheduler: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Collect all metrics from system and components.

        Args:
            risk_manager: Optional RiskManager instance.
            capital_allocator: Optional CapitalAllocator instance.
            scheduler: Optional CentralScheduler instance.

        Returns:
            Dictionary containing all collected metrics.

        Example:
            >>> all_metrics = collector.collect_all_metrics(
            ...     risk_manager=risk_mgr,
            ...     capital_allocator=allocator,
            ...     scheduler=scheduler
            ... )
        """
        try:
            all_metrics = {
                'collection_timestamp': time.time(),
                'system': asdict(self.collect_system_metrics())
            }

            if risk_manager:
                all_metrics['risk_manager'] = self.collect_risk_manager_metrics(
                    risk_manager
                )

            if capital_allocator:
                all_metrics['capital_allocator'] = (
                    self.collect_capital_allocator_metrics(capital_allocator)
                )

            if scheduler:
                all_metrics['scheduler'] = self.collect_scheduler_metrics(scheduler)

            logger.info("Successfully collected all metrics")
            return all_metrics

        except Exception as e:
            logger.error(f"Failed to collect all metrics: {e}")
            raise RuntimeError(f"Metrics collection failed: {e}")

    def export_prometheus_format(self) -> bytes:
        """
        Export metrics in Prometheus exposition format.

        Returns:
            Metrics data in Prometheus text format.

        Example:
            >>> prometheus_data = collector.export_prometheus_format()
            >>> print(prometheus_data.decode('utf-8'))
        """
        try:
            return generate_latest(self.registry)
        except Exception as e:
            logger.error(f"Failed to export Prometheus format: {e}")
            raise RuntimeError(f"Prometheus export failed: {e}")


__all__ = ["MetricsCollector", "SystemMetrics", "ComponentMetrics"]
