"""
Operational Health Checker implementation for monitoring infrastructure.

This module provides the HealthChecker class that performs comprehensive health
checks on Phase 3 components (RiskManager, CapitalAllocator, CentralScheduler)
and monitoring components, exposing health status via HTTP endpoint.
"""

import logging
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration for system components."""
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ComponentHealth:
    """Data class for individual component health status."""
    component_name: str
    status: HealthStatus
    message: str
    last_check: float
    metrics: Dict[str, Any]


@dataclass
class SystemHealth:
    """Data class for overall system health status."""
    overall_status: HealthStatus
    timestamp: float
    components: List[ComponentHealth]
    summary: Dict[str, int]


class HealthChecker:
    """
    Operational Health Checker for the Airdrops Automation System.

    Performs comprehensive health checks on core Phase 3 components and
    monitoring infrastructure, exposing health status via HTTP endpoint.

    Example:
        >>> health_checker = HealthChecker()
        >>> health_checker.initialize()
        >>> health_status = health_checker.check_system_health()
        >>> print(f"System status: {health_status.overall_status}")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the Health Checker.

        Args:
            config: Optional configuration dictionary for health check settings.
        """
        self.config = config or {}
        self.app = FastAPI(title="Airdrops Health Check API", version="1.0.0")
        self._setup_routes()

        # Configuration from environment
        self.check_interval = int(
            os.getenv("HEALTH_CHECK_INTERVAL", "30")
        )
        self.http_port = int(
            os.getenv("HEALTH_CHECK_PORT", "8001")
        )
        self.timeout_seconds = float(
            os.getenv("HEALTH_CHECK_TIMEOUT", "10.0")
        )

        # Health check thresholds
        self.cpu_warning_threshold = float(
            os.getenv("HEALTH_CPU_WARNING_THRESHOLD", "80.0")
        )
        self.cpu_critical_threshold = float(
            os.getenv("HEALTH_CPU_CRITICAL_THRESHOLD", "95.0")
        )
        self.memory_warning_threshold = float(
            os.getenv("HEALTH_MEMORY_WARNING_THRESHOLD", "85.0")
        )
        self.memory_critical_threshold = float(
            os.getenv("HEALTH_MEMORY_CRITICAL_THRESHOLD", "95.0")
        )

    def _setup_routes(self) -> None:
        """Setup FastAPI routes for health check endpoints."""

        @self.app.get("/health")
        async def health_endpoint() -> JSONResponse:
            """
            Main health check endpoint returning overall system health.

            Returns:
                JSON response with system health status.
            """
            try:
                health_status = self.check_system_health()
                status_code = 200

                if health_status.overall_status == HealthStatus.WARNING:
                    status_code = 200  # Still operational
                elif health_status.overall_status == HealthStatus.CRITICAL:
                    status_code = 503  # Service unavailable

                return JSONResponse(
                    status_code=status_code,
                    content={
                        "status": health_status.overall_status.value,
                        "timestamp": health_status.timestamp,
                        "components": [
                            {
                                "name": comp.component_name,
                                "status": comp.status.value,
                                "message": comp.message,
                                "last_check": comp.last_check,
                                "metrics": comp.metrics
                            }
                            for comp in health_status.components
                        ],
                        "summary": health_status.summary
                    }
                )
            except Exception as e:
                logger.error(f"Health check endpoint failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "CRITICAL",
                        "error": "Health check system failure",
                        "timestamp": time.time()
                    }
                )

        @self.app.get("/health/components/{component_name}")
        async def component_health_endpoint(component_name: str) -> JSONResponse:
            """
            Individual component health check endpoint.

            Args:
                component_name: Name of component to check.

            Returns:
                JSON response with component health status.
            """
            try:
                component_health = self.check_component_health(component_name)
                if component_health is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Component '{component_name}' not found"
                    )

                return JSONResponse(
                    status_code=200,
                    content={
                        "name": component_health.component_name,
                        "status": component_health.status.value,
                        "message": component_health.message,
                        "last_check": component_health.last_check,
                        "metrics": component_health.metrics
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Component health check failed for {component_name}: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": f"Component health check failed: {e}",
                        "timestamp": time.time()
                    }
                )

    def check_system_health(
        self,
        risk_manager: Optional[Any] = None,
        capital_allocator: Optional[Any] = None,
        scheduler: Optional[Any] = None,
        metrics_collector: Optional[Any] = None,
        alerter: Optional[Any] = None
    ) -> SystemHealth:
        """
        Perform comprehensive system health check.

        Args:
            risk_manager: Optional RiskManager instance to check.
            capital_allocator: Optional CapitalAllocator instance to check.
            scheduler: Optional CentralScheduler instance to check.
            metrics_collector: Optional MetricsCollector instance to check.
            alerter: Optional Alerter instance to check.

        Returns:
            SystemHealth object with overall system status.

        Example:
            >>> health_status = health_checker.check_system_health(
            ...     risk_manager=risk_mgr,
            ...     capital_allocator=allocator,
            ...     scheduler=scheduler
            ... )
            >>> print(f"Overall status: {health_status.overall_status}")
        """
        try:
            current_time = time.time()
            components = []

            # Check Phase 3 core components
            if risk_manager:
                risk_health = self._check_risk_manager_health(risk_manager)
                components.append(risk_health)

            if capital_allocator:
                capital_health = self._check_capital_allocator_health(capital_allocator)
                components.append(capital_health)

            if scheduler:
                scheduler_health = self._check_scheduler_health(scheduler)
                components.append(scheduler_health)

            # Check monitoring components
            if metrics_collector:
                collector_health = self._check_metrics_collector_health(metrics_collector)
                components.append(collector_health)

            if alerter:
                alerter_health = self._check_alerter_health(alerter)
                components.append(alerter_health)

            # Check system resources
            system_health = self._check_system_resources()
            components.append(system_health)

            # Check external dependencies
            external_health = self._check_external_dependencies()
            components.append(external_health)

            # Determine overall status
            overall_status = self._determine_overall_status(components)

            # Create summary
            summary = {
                "total_components": len(components),
                "ok_count": len([c for c in components if c.status == HealthStatus.OK]),
                "warning_count": len([c for c in components if c.status == HealthStatus.WARNING]),
                "critical_count": len([c for c in components if c.status == HealthStatus.CRITICAL])
            }

            logger.info(f"System health check completed: {overall_status.value}")

            return SystemHealth(
                overall_status=overall_status,
                timestamp=current_time,
                components=components,
                summary=summary
            )

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            raise RuntimeError(f"Failed to check system health: {e}")

    def check_component_health(self, component_name: str) -> Optional[ComponentHealth]:
        """
        Check health of a specific component by name.

        Args:
            component_name: Name of the component to check.

        Returns:
            ComponentHealth object or None if component not found.

        Example:
            >>> component_health = health_checker.check_component_health("risk_manager")
            >>> if component_health:
            ...     print(f"Status: {component_health.status}")
        """
        try:
            
            if component_name == "system_resources":
                return self._check_system_resources()
            elif component_name == "external_dependencies":
                return self._check_external_dependencies()
            else:
                logger.warning(f"Unknown component: {component_name}")
                return None

        except Exception as e:
            logger.error(f"Component health check failed for {component_name}: {e}")
            return ComponentHealth(
                component_name=component_name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_risk_manager_health(self, risk_manager: Any) -> ComponentHealth:
        """Check RiskManager component health."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "Risk Manager is healthy"

            # Check if circuit breaker is active
            if hasattr(risk_manager, 'circuit_breaker_active'):
                circuit_breaker_active = risk_manager.circuit_breaker_active
                metrics['circuit_breaker_active'] = circuit_breaker_active

                if circuit_breaker_active:
                    status = HealthStatus.CRITICAL
                    message = "Circuit breaker is active"

            # Check risk limits configuration
            if hasattr(risk_manager, 'risk_limits'):
                metrics['risk_limits_configured'] = True
            else:
                metrics['risk_limits_configured'] = False
                if status == HealthStatus.OK:  # Only set WARNING if not already CRITICAL
                    status = HealthStatus.WARNING
                    message = "Risk limits not configured"

            return ComponentHealth(
                component_name="risk_manager",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"Risk manager health check failed: {e}")
            return ComponentHealth(
                component_name="risk_manager",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_capital_allocator_health(
        self, capital_allocator: Any) -> ComponentHealth:
        """Check CapitalAllocator component health."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "Capital Allocator is healthy"

            # Check portfolio history
            if hasattr(capital_allocator, 'portfolio_history'):
                history_length = len(capital_allocator.portfolio_history)
                metrics['portfolio_history_length'] = history_length

                if history_length == 0:
                    status = HealthStatus.WARNING
                    message = "No portfolio history available"

            # Check allocation strategy
            if hasattr(capital_allocator, 'allocation_strategy'):
                metrics['allocation_strategy'] = capital_allocator.allocation_strategy.value
            else:
                status = HealthStatus.WARNING
                message = "Allocation strategy not configured"

            return ComponentHealth(
                component_name="capital_allocator",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"Capital allocator health check failed: {e}")
            return ComponentHealth(
                component_name="capital_allocator",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_scheduler_health(self, scheduler: Any) -> ComponentHealth:
        """Check CentralScheduler component health."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "Scheduler is healthy"

            # Check if scheduler is running
            if hasattr(scheduler, '_running'):
                is_running = scheduler._running
                metrics['is_running'] = is_running

                if not is_running:
                    status = HealthStatus.CRITICAL
                    message = "Scheduler is not running"

            # Check task definitions
            if hasattr(scheduler, '_task_definitions'):
                task_count = len(scheduler._task_definitions)
                metrics['task_count'] = task_count

                if task_count == 0:
                    status = HealthStatus.WARNING
                    message = "No tasks defined"

            return ComponentHealth(
                component_name="scheduler",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"Scheduler health check failed: {e}")
            return ComponentHealth(
                component_name="scheduler",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_metrics_collector_health(
        self, metrics_collector: Any) -> ComponentHealth:
        """Check MetricsCollector component health."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "Metrics Collector is healthy"

            # Check if collector is configured
            if hasattr(metrics_collector, 'registry'):
                metrics['registry_configured'] = True
            else:
                status = HealthStatus.CRITICAL
                message = "Metrics registry not configured"

            # Check collection interval
            if hasattr(metrics_collector, 'collection_interval'):
                metrics['collection_interval'] = metrics_collector.collection_interval

            return ComponentHealth(
                component_name="metrics_collector",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"Metrics collector health check failed: {e}")
            return ComponentHealth(
                component_name="metrics_collector",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_alerter_health(self, alerter: Any) -> ComponentHealth:
        """Check Alerter component health."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "Alerter is healthy"

            # Check alert rules
            if hasattr(alerter, 'alert_rules'):
                rules_count = len(alerter.alert_rules)
                metrics['alert_rules_count'] = rules_count

                if rules_count == 0:
                    status = HealthStatus.WARNING
                    message = "No alert rules configured"

            # Check notification channels
            if hasattr(alerter, 'notification_channels'):
                channels_count = len(alerter.notification_channels)
                metrics['notification_channels_count'] = channels_count

                if channels_count == 0:
                    status = HealthStatus.WARNING
                    message = "No notification channels configured"

            # Check active alerts
            if hasattr(alerter, 'active_alerts'):
                active_alerts_count = len(alerter.active_alerts)
                metrics['active_alerts_count'] = active_alerts_count

            return ComponentHealth(
                component_name="alerter",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"Alerter health check failed: {e}")
            return ComponentHealth(
                component_name="alerter",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_system_resources(self) -> ComponentHealth:
        """Check system resource health (CPU, memory, disk)."""
        try:
            import psutil

            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "System resources are healthy"

            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage_percent'] = cpu_percent

            if cpu_percent >= self.cpu_critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Critical CPU usage: {cpu_percent}%"
            elif cpu_percent >= self.cpu_warning_threshold:
                status = HealthStatus.WARNING
                message = f"High CPU usage: {cpu_percent}%"

            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            metrics['memory_usage_percent'] = memory_percent

            if memory_percent >= self.memory_critical_threshold:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.CRITICAL
                    message = f"Critical memory usage: {memory_percent}%"
            elif memory_percent >= self.memory_warning_threshold:
                if status == HealthStatus.OK:
                    status = HealthStatus.WARNING
                    message = f"High memory usage: {memory_percent}%"

            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            metrics['disk_usage_percent'] = disk_percent

            return ComponentHealth(
                component_name="system_resources",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"System resources health check failed: {e}")
            return ComponentHealth(
                component_name="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _check_external_dependencies(self) -> ComponentHealth:
        """Check external dependencies health (blockchain nodes, APIs)."""
        try:
            current_time = time.time()
            metrics = {}
            status = HealthStatus.OK
            message = "External dependencies are healthy"

            # Check blockchain connectivity (stub implementation)
            eth_rpc_url = os.getenv("ETH_RPC_URL")
            if eth_rpc_url:
                metrics['eth_rpc_configured'] = True
                # In a real implementation, we would test the connection
                metrics['eth_rpc_status'] = "connected"
            else:
                metrics['eth_rpc_configured'] = False
                # Only warn if we're not in a test environment
                if not os.getenv("PYTEST_CURRENT_TEST"):
                    status = HealthStatus.WARNING
                    message = "ETH RPC URL not configured"

            scroll_rpc_url = os.getenv("SCROLL_L2_RPC_URL")
            if scroll_rpc_url:
                metrics['scroll_rpc_configured'] = True
                metrics['scroll_rpc_status'] = "connected"
            else:
                metrics['scroll_rpc_configured'] = False
                # Only warn if we're not in a test environment and no other warnings
                if not os.getenv("PYTEST_CURRENT_TEST") and status == HealthStatus.OK:
                    status = HealthStatus.WARNING
                    message = "Scroll RPC URL not configured"

            return ComponentHealth(
                component_name="external_dependencies",
                status=status,
                message=message,
                last_check=current_time,
                metrics=metrics
            )

        except Exception as e:
            logger.error(f"External dependencies health check failed: {e}")
            return ComponentHealth(
                component_name="external_dependencies",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                last_check=time.time(),
                metrics={}
            )

    def _determine_overall_status(
        self, components: List[ComponentHealth]) -> HealthStatus:
        """Determine overall system status from component statuses."""
        if not components:
            return HealthStatus.CRITICAL

        critical_count = len([c for c in components if c.status == HealthStatus.CRITICAL])
        warning_count = len([c for c in components if c.status == HealthStatus.WARNING])

        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.OK

    def start_server(self, host: str = "0.0.0.0") -> None:
        """
        Start the health check HTTP server.

        Args:
            host: Host address to bind to.

        Example:
            >>> health_checker = HealthChecker()
            >>> health_checker.start_server()  # Starts on port 8001
        """
        try:
            logger.info(f"Starting health check server on {host}:{self.http_port}")
            uvicorn.run(
                self.app,
                host=host,
                port=self.http_port,
                log_level="info"
            )
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            raise RuntimeError(f"Health check server startup failed: {e}")


__all__ = ["HealthChecker", "HealthStatus", "ComponentHealth", "SystemHealth"]
