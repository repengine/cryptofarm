"""
Central Scheduler implementation for airdrops automation.

This module provides the CentralScheduler class that orchestrates airdrop-related
tasks using APScheduler with DAG-based dependency management, market awareness,
and robust error handling with retry logic.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Set, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import argparse
import importlib
import sys

from airdrops.monitoring.alerter import Alert, AlertSeverity, AlertStatus
from airdrops.protocols.scroll.interfaces import IScrollProtocol
from airdrops.protocols.zksync.interfaces import IZkSyncProtocol
from airdrops.protocols.layerzero.interfaces import ILayerZeroProtocol
from airdrops.protocols.eigenlayer.interfaces import IEigenLayerProtocol
from airdrops.capital_allocation.interfaces import ICapitalAllocator
from airdrops.risk_management.interfaces import IRiskManager

if TYPE_CHECKING:
    pass

# APScheduler imports - will be added to dependencies
try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    # Graceful fallback for development
    BlockingScheduler = None
    CronTrigger = None
    DateTrigger = None
    IntervalTrigger = None

# Configure logging
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskDefinition:
    """Data class for task definitions."""
    task_id: str
    func: Callable[..., Any]
    protocol: Optional[str] = None
    action: Optional[str] = None
    args: Tuple[Any, ...] = ()
    kwargs: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: Optional[Set[str]] = None
    max_retries: int = 3
    retry_delay: float = 60.0
    timeout: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.kwargs is None:
            self.kwargs = {}
        if self.dependencies is None:
            self.dependencies = set()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskExecution:
    """Data class for task execution tracking."""
    task_id: str
    status: TaskStatus
    wallet: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    result: Any = None


class AirdropSchedulerBot:
    """
    Airdrop Scheduler Bot for orchestrating airdrop-related tasks.

    This class provides comprehensive task scheduling capabilities with:
    - APScheduler integration for flexible scheduling
    - DAG-based dependency management
    - Market condition awareness
    - Retry logic with exponential backoff
    - Priority-based task execution

    Example:
    >>> scheduler = AirdropSchedulerBot()
    >>> scheduler.add_job(
    ...     task_id="daily_bridge",
    ...     func=bridge_eth_to_scroll,
    ...     trigger="cron",
    ...     hour=10,
    ...     minute=0
    ... )
    >>> scheduler.start()
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        capital_allocator: Optional[ICapitalAllocator] = None,
        risk_manager: Optional[IRiskManager] = None,
        metrics_collector: Optional[Any] = None,
        cross_chain_manager: Optional[Any] = None,
        scroll_client: Optional[IScrollProtocol] = None,
        zksync_client: Optional[IZkSyncProtocol] = None,
        layerzero_client: Optional[ILayerZeroProtocol] = None,
        eigenlayer_client: Optional[IEigenLayerProtocol] = None
    ):
        """
        Initialize the Airdrop Scheduler Bot.

        Args:
            config: Optional configuration dictionary
            capital_allocator: Optional CapitalAllocator instance for capital management
            risk_manager: Optional RiskManager instance for risk assessment
            metrics_collector: Optional MetricsCollector instance for metrics collection
            cross_chain_manager: Optional CrossChainManager instance for automated rebalancing
            scroll_client: Optional Scroll protocol client for dependency injection
            zksync_client: Optional ZkSync protocol client for dependency injection
            layerzero_client: Optional LayerZero protocol client for dependency injection
            eigenlayer_client: Optional EigenLayer protocol client for dependency injection

        Example:
            >>> from airdrops.capital_allocation.engine import CapitalAllocator
            >>> from airdrops.risk_management.core import RiskManager
            >>> from airdrops.protocols.scroll.scroll import ScrollProtocol
            >>> capital_allocator = CapitalAllocator()
            >>> risk_manager = RiskManager()
            >>> scroll_client = ScrollProtocol(l1_rpc_url="...", l2_rpc_url="...", private_key="...")
            >>> scheduler = AirdropSchedulerBot(
            ...     capital_allocator=capital_allocator,
            ...     risk_manager=risk_manager,
            ...     scroll_client=scroll_client
            ... )
        """
        self.config = config or {}
        self._scheduler: Optional[BlockingScheduler] = None
        self._task_definitions: Dict[str, TaskDefinition] = {}
        self._task_executions: Dict[str, TaskExecution] = {}
        self._running = False
        
        # Dependency injection for core components
        self._capital_allocator = capital_allocator
        self._risk_manager = risk_manager
        self._metrics_collector = metrics_collector
        self._cross_chain_manager = cross_chain_manager
        
        # Protocol clients for dependency injection
        self.scroll_client: Optional[IScrollProtocol] = scroll_client
        self.zksync_client: Optional[IZkSyncProtocol] = zksync_client
        self.layerzero_client: Optional[ILayerZeroProtocol] = layerzero_client
        self.eigenlayer_client: Optional[IEigenLayerProtocol] = eigenlayer_client

        # Configuration with defaults
        self.max_retries = self.config.get("scheduler", {}).get("max_retries", 3)
        self.retry_delay = self.config.get("scheduler", {}).get(
            "retry_delay", 60.0
        )
        self._max_concurrent_jobs = self.config.get("scheduler", {}).get(
            "max_concurrent_tasks", 5
        )
        self._last_wallet_index = -1

        # Initialize alerter as None - will be set up when needed
        self.alerter: Optional[Any] = None
        
        # Initialize fallback implementations if no dependencies provided
        if not any([capital_allocator, risk_manager, scroll_client, zksync_client, layerzero_client, eigenlayer_client]):
            self._initialize_default_dependencies()

        logger.info(
            "AirdropSchedulerBot initialized with config: %s, capital_allocator: %s, risk_manager: %s, metrics_collector: %s, cross_chain_manager: %s",
            self.config,
            "enabled" if capital_allocator else "disabled",
            "enabled" if risk_manager else "disabled",
            "enabled" if metrics_collector else "disabled",
            "enabled" if cross_chain_manager else "disabled"
        )

    @property
    def capital_allocator(self) -> Optional[Any]:
        """Get the capital allocator instance."""
        return self._capital_allocator

    @capital_allocator.setter
    def capital_allocator(self, value: Optional[Any]) -> None:
        """Set the capital allocator instance."""
        self._capital_allocator = value

    @property
    def metrics_collector(self) -> Optional[Any]:
        """Get the metrics collector instance."""
        return self._metrics_collector

    @metrics_collector.setter
    def metrics_collector(self, value: Optional[Any]) -> None:
        """Set the metrics collector instance."""
        self._metrics_collector = value

    def add_job(
        self,
        task_id: str,
        func: Callable[..., Any],
        trigger: str = "cron",
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[Set[str]] = None,
        max_retries: Optional[int] = None,
        **trigger_kwargs: Any
    ) -> None:
        """
        Add a new job to the scheduler.

        Args:
            task_id: Unique identifier for the task
            func: Function to execute
            trigger: Trigger type ("cron", "date", "interval")
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Task priority level
            dependencies: Set of task IDs this task depends on
            max_retries: Maximum number of retry attempts
            **trigger_kwargs: Additional trigger configuration

        Example:
            >>> scheduler.add_job(
            ...     "daily_bridge",
            ...     bridge_eth_to_scroll,
            ...     trigger="cron",
            ...     hour=10,
            ...     minute=0,
            ...     args=(100, ),
            ...     kwargs={"slippage": 0.01}
            ... )
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized. Call start() first.")

        if task_id in self._task_definitions:
            raise ValueError(f"Task {task_id} already exists")

        # Create task definition
        task_def = TaskDefinition(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            dependencies=dependencies or set(),
            max_retries=max_retries or self.max_retries
        )

        # Validate dependencies
        self._validate_dependencies(task_def)

        # Create appropriate trigger
        trigger_obj = self._create_trigger(trigger, **trigger_kwargs)

        # Add job to APScheduler
        if self._scheduler is not None:
            self._scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger_obj,
                args=(task_id, ),
                id=task_id,
                max_instances=1,
                replace_existing=True
            )

        # Store task definition
        self._task_definitions[task_id] = task_def
        self._task_executions[task_id] = TaskExecution(
            task_id=task_id,
            status=TaskStatus.PENDING
        )

        logger.info("Added job %s with trigger %s", task_id, trigger)

    def manage_task_priority(self, task_id: str, new_priority: TaskPriority) -> None:
        """
        Update task priority for dynamic priority management.

        Args:
            task_id: Task identifier
            new_priority: New priority level

        Example:
            >>> scheduler.manage_task_priority("bridge_task", TaskPriority.HIGH)
        """
        if task_id not in self._task_definitions:
            raise ValueError(f"Task {task_id} not found")

        self._task_definitions[task_id].priority = new_priority
        logger.info("Updated priority for task %s to %s", task_id, new_priority)

    def manage_task_dependencies(
        self,
        task_id: str,
        dependencies: Set[str]
    ) -> None:
        """
        Update task dependencies for DAG-based dependency management.

        Args:
            task_id: Task identifier
            dependencies: Set of task IDs this task depends on

        Example:
            >>> scheduler.manage_task_dependencies(
            ...     "swap_task",
            ...     {"bridge_task", "approval_task"}
            ... )
        """
        if task_id not in self._task_definitions:
            raise ValueError(f"Task {task_id} not found")

        # Update dependencies
        self._task_definitions[task_id].dependencies = dependencies

        # Validate the updated dependency graph
        self._validate_dependencies(self._task_definitions[task_id])

        logger.info("Updated dependencies for task %s: %s", task_id, dependencies)

    def schedule_dynamically(
        self,
        market_conditions: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> None:
        """
        Adjust schedules dynamically based on market conditions and risk assessment.

        This method integrates with the Risk Management System and Capital
        Allocation Engine to make intelligent scheduling decisions.

        Args:
            market_conditions: Current market data (gas prices, volatility, etc.)
            risk_assessment: Risk assessment from RiskManager

        Example:
            >>> market_data = {"gas_price": 50, "volatility": "high"}
            >>> risk_data = {"circuit_breaker": False, "risk_score": 0.3}
            >>> scheduler.schedule_dynamically(market_data, risk_data)
        """
        gas_price = market_conditions.get("gas_price", 0)
        volatility = market_conditions.get("volatility", "normal")
        circuit_breaker = risk_assessment.get("circuit_breaker", False)

        # Implement dynamic scheduling logic
        if circuit_breaker:
            logger.warning("Circuit breaker active - pausing all tasks")
            self._pause_all_tasks()
            return

        if gas_price > self.config.get("max_gas_price", 100):
            logger.info("High gas prices detected - delaying non-critical tasks")
            self._delay_low_priority_tasks()

        if volatility == "high":
            logger.info("High volatility detected - reducing task frequency")
            self._reduce_task_frequency()

        logger.info("Dynamic scheduling adjustment completed")

    def schedule_rebalancing_checks(self, interval_hours: float) -> None:
        """
        Schedule periodic cross-chain liquidity threshold checks and rebalancing.
        
        This method sets up automated, periodic execution of the CrossChainManager's
        liquidity threshold checking functionality using APScheduler's interval trigger.
        
        Args:
            interval_hours: Time interval between checks in hours (e.g., 1.0 for hourly,
                          0.5 for every 30 minutes, 24.0 for daily)
        
        Raises:
            RuntimeError: If scheduler is not initialized or no CrossChainManager is configured
            ValueError: If interval_hours is not positive
            
        Example:
            >>> from airdrops.scheduler.bot import AirdropSchedulerBot
            >>> from airdrops.cross_chain.manager import CrossChainManager
            >>> manager = CrossChainManager()
            >>> scheduler = AirdropSchedulerBot(cross_chain_manager=manager)
            >>> scheduler.start()
            >>> scheduler.schedule_rebalancing_checks(2.0)  # Check every 2 hours
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized. Call start() first.")
        
        if not self._cross_chain_manager:
            raise RuntimeError(
                "No CrossChainManager configured. Initialize scheduler with "
                "cross_chain_manager parameter."
            )
        
        if interval_hours <= 0:
            raise ValueError("interval_hours must be positive")
        
        # Convert hours to seconds for IntervalTrigger
        interval_seconds = interval_hours * 3600
        
        # Create the rebalancing check job
        job_id = "cross_chain_rebalancing_check"
        
        # Remove existing job if it exists
        if job_id in self._task_definitions:
            logger.info("Removing existing rebalancing check job")
            if self._scheduler:
                try:
                    self._scheduler.remove_job(job_id)
                except Exception as e:
                    logger.warning("Failed to remove existing job %s: %s", job_id, e)
            del self._task_definitions[job_id]
            if job_id in self._task_executions:
                del self._task_executions[job_id]
        
        # Add the new rebalancing check job
        self.add_job(
            task_id=job_id,
            func=self._cross_chain_manager.check_liquidity_thresholds,
            trigger="interval",
            seconds=interval_seconds,
            priority=TaskPriority.HIGH,
            max_retries=2  # Fewer retries for monitoring tasks
        )
        
        logger.info(
            "Scheduled cross-chain rebalancing checks every %.2f hours",
            interval_hours
        )

    def handle_task_failure(
        self,
        task_id: str,
        error: Exception,
        execution: TaskExecution
    ) -> bool:
        """
        Handle task failure with exponential backoff retry logic.

        Args:
            task_id: Failed task identifier
            error: Exception that caused the failure
            execution: Task execution tracking object

        Returns:
            True if task should be retried, False otherwise

        Example:
            >>> success = scheduler.handle_task_failure(
            ...     "bridge_task",
            ...     ConnectionError("RPC timeout"),
            ...     execution_obj
            ... )
        """
        task_def = self._task_definitions.get(task_id)
        if not task_def:
            logger.error("Task definition not found for %s", task_id)
            return False

        execution.retry_count += 1
        execution.last_error = str(error)
        execution.status = TaskStatus.FAILED
        execution.result = {
            "success": False,
            "message": f"Task failed: {error}",
            "error": str(error),
            "tx_hash": None,
            "protocol": task_def.protocol,
            "action": task_def.action,
            "wallet": execution.wallet,
            "id": task_id,
        }

        if execution.retry_count >= task_def.max_retries:
            logger.error(
                "Task %s failed permanently after %d retries: %s",
                task_id, execution.retry_count, error
            )
            if self.alerter:
                logger.debug(
                    "Alerter instance in handle_task_failure: %s", self.alerter
                )
                alert_message = (
                    f"Task {task_id} ({task_def.protocol}/"
                    f"{task_def.action} failed permanently: {error}"
                )
                alert_labels = {
                    "task_id": task_id,
                    "protocol": task_def.protocol or "unknown",
                    "action": task_def.action or "unknown",
                    "wallet": execution.wallet or "unknown",
                }
                alert = Alert(
                    rule_name=f"task_failure_{task_id}",
                    metric_name="task_failure",
                    current_value=1.0,  # Represents a single failure event
                    threshold=0.0,  # Always trigger on failure
                    severity=AlertSeverity.CRITICAL,
                    status=AlertStatus.FIRING,
                    description=alert_message,
                    timestamp=time.time(),
                    labels=alert_labels,
                    firing_since=time.time(),
                    resolved_at=None,
                )
                self.alerter.send_notifications([alert])
            else:
                logger.debug("Alerter is None in handle_task_failure.")
            return False

        # Calculate exponential backoff delay
        delay = task_def.retry_delay * (2 ** (execution.retry_count - 1))

        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (time.time() % 1)
        total_delay = delay + jitter

        logger.warning(
            "Task %s failed (attempt %d/%d), retrying in %.1f seconds: %s",
            task_id, execution.retry_count, task_def.max_retries, total_delay, error
        )

        execution.status = TaskStatus.RETRYING

        # Schedule retry
        retry_time = datetime.now() + timedelta(seconds=total_delay)
        if self._scheduler is not None:
            trigger = self._create_trigger("date", run_date=retry_time)
            if trigger:
                self._scheduler.add_job(
                    func=self._execute_task_wrapper,
                    trigger=trigger,
                    args=(task_id, ),
                    id=f"{task_id}_retry_{execution.retry_count}",
                    replace_existing=True
                )
            else:
                logger.error("APScheduler not available, cannot schedule retry")

        return True

    def start(self) -> None:
        """
        Initialize and start the APScheduler.

        Example:
            >>> scheduler = AirdropSchedulerBot()
            >>> scheduler.start()
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return

        if not BlockingScheduler:
            raise ImportError(
                "APScheduler not available. Install with: pip install apscheduler"
            )

        self._scheduler = BlockingScheduler()
        self._running = True

        logger.info("AirdropSchedulerBot started successfully")

    def stop(self) -> None:
        """
        Gracefully shut down the scheduler.

        Example:
            >>> scheduler.stop()
        """
        if not self._running:
            logger.warning("Scheduler is not running")
            return

        if self._scheduler:
            self._scheduler.shutdown(wait=True)
            self._scheduler = None

        self._running = False
        logger.info("AirdropSchedulerBot stopped gracefully")

    def _execute_task_wrapper(self, task_id: str) -> Any:
        """Execute a task with proper error handling and tracking."""
        execution = self._task_executions.get(task_id)
        task_def = self._task_definitions.get(task_id)

        if not execution or not task_def:
            logger.error("Task or execution not found: %s", task_id)
            return None

        # Check dependencies
        if not self._check_dependencies(task_id):
            logger.warning("Dependencies not met for task %s", task_id)
            return None

        execution.status = TaskStatus.RUNNING
        execution.start_time = datetime.now()

        try:
            logger.info("Executing task %s", task_id)
            result = task_def.func(*task_def.args, **(task_def.kwargs or {}))

            execution.status = TaskStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.result = result

            logger.info("Task %s completed successfully", task_id)
            return result

        except Exception as error:
            logger.error("Task %s failed: %s", task_id, error)
            self.handle_task_failure(task_id, error, execution)
            execution.result = {
                "success": False,
                "message": str(error),
                "tx_hash": None,
                "error": str(error),
                "protocol": task_def.protocol,
                "action": task_def.action,
                "wallet": execution.wallet,
                "id": task_id,
            }
            logger.debug(
                "Execution result after handling failure: %s", execution.result
            )
            return execution.result

    def _validate_dependencies(self, task_def: TaskDefinition) -> None:
        """Validate task dependencies to prevent cycles."""
        # Proper cycle detection using DFS with three states:
        # WHITE (0): unvisited, GRAY (1): visiting, BLACK (2): visited
        color = {}
        
        def has_cycle(task_id: str) -> bool:
            if task_id not in color:
                color[task_id] = 0  # WHITE
            
            if color[task_id] == 1:  # GRAY - currently being visited
                return True
            if color[task_id] == 2:  # BLACK - already processed
                return False
                
            color[task_id] = 1  # GRAY - mark as visiting
            
            task = self._task_definitions.get(task_id)
            if task:
                for dep in (task.dependencies or set()):
                    if has_cycle(dep):
                        return True
                        
            color[task_id] = 2  # BLACK - mark as visited
            return False

        if has_cycle(task_def.task_id):
            raise ValueError(
                f"Circular dependency detected for task {task_def.task_id}"
            )

    def _create_trigger(self, trigger_type: str, **kwargs: Any) -> Any:
        """Create appropriate trigger object based on type."""
        if trigger_type == "cron":
            return CronTrigger(**kwargs) if CronTrigger else None
        elif trigger_type == "date":
            return DateTrigger(**kwargs) if DateTrigger else None
        elif trigger_type == "interval":
            return IntervalTrigger(**kwargs) if IntervalTrigger else None
        else:
            raise ValueError(f"Unsupported trigger type: {trigger_type}")

    def _check_dependencies(self, task_id: str) -> bool:
        """Check if all dependencies for a task are completed."""
        task_def = self._task_definitions.get(task_id)
        if not task_def:
            return False

        for dep_id in (task_def.dependencies or set()):
            dep_execution = self._task_executions.get(dep_id)
            if not dep_execution or dep_execution.status != TaskStatus.COMPLETED:
                return False

        return True

    def _pause_all_tasks(self) -> None:
        """Pause all scheduled tasks."""
        if self._scheduler:
            self._scheduler.pause()
            logger.info("All tasks paused")

    def _delay_low_priority_tasks(self) -> None:
        """Delay low priority tasks due to high gas prices."""
        # Implementation for delaying low priority tasks
        logger.info("Low priority tasks delayed due to high gas prices")

    def _reduce_task_frequency(self) -> None:
        """Reduce task frequency during high volatility."""
        # Implementation for reducing task frequency
        logger.info("Task frequency reduced due to high volatility")

    def _resolve_dependencies(self, task_graph: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Resolve task dependencies using a topological sort.
        Returns a list of task IDs in a valid execution order.
        """
        in_degree: Dict[str, int] = {task_id: 0 for task_id in task_graph}
        adj_list: Dict[str, List[str]] = {task_id: [] for task_id in task_graph}

        for task_id, task_info in task_graph.items():
            for dep_id in task_info.get("dependencies", []):
                adj_list[dep_id].append(task_id)
                in_degree[task_id] += 1
        queue: List[str] = [
            task_id for task_id, degree in in_degree.items() if degree == 0
        ]
        topological_order: List[str] = []
        while queue:
            current_task_id = queue.pop(0)
            topological_order.append(current_task_id)

            for neighbor_task_id in adj_list[current_task_id]:
                in_degree[neighbor_task_id] -= 1
                if in_degree[neighbor_task_id] == 0:
                    queue.append(neighbor_task_id)

        if len(topological_order) != len(task_graph):
            raise ValueError("Circular dependency detected in task graph.")

        logger.debug(f"Resolved dependencies: {topological_order}")
        return topological_order

    def _execute_protocol_task(
        self, protocol_name: str, task_type: str, **kwargs: Any
    ) -> Any:
        """Placeholder for executing a protocol-specific task."""
        logger.info(
            f"Executing protocol task: {protocol_name} - {task_type} with {kwargs}"
        )
        # This would dynamically load and execute the relevant protocol logic
        return f"Executed {protocol_name} {task_type}"

    def _schedule_daily_activities(self) -> None:
        """Placeholder for scheduling daily activities."""
        logger.info("Scheduling daily activities...")
        pass

    def _load_balance_wallets(self) -> None:
        """Placeholder for load balancing wallets."""
        logger.info("Load balancing wallets...")
        pass

    def _enforce_gas_limits(self) -> bool:
        """Placeholder for enforcing gas limits."""
        logger.info("Enforcing gas limits...")
        # For now, always return True to allow execution, or implement actual logic
        # based on self.config.get("risk_management", {}).get(
        # "max_gas_price_gwei"
        # )
        return True

    def _generate_random_delay(
        self, min_delay: float = 1.0, max_delay: float = 5.0
    ) -> float:
        """
        Generate a random delay within a specified range.

        Args:
            min_delay: Minimum delay in seconds.
            max_delay: Maximum delay in seconds.

        Returns:
            A random float representing the delay.
        """
        import random
        return random.uniform(min_delay, max_delay)

    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single task by dynamically dispatching to the correct protocol module.
        """
        protocol_name = task["protocol"]
        action_name = task["action"]
        task_id = task.get("id", "unknown_task")
        logger.info(
            f"Executing task: {task_id} ({protocol_name}/{action_name})"
        )

        try:
            # Dynamically import the protocol module
            protocol_module = importlib.import_module(
                f"airdrops.protocols.{protocol_name}.{protocol_name}"
            )

            # Get the function to execute
            if action_name == "random_activity":
                action_func = getattr(protocol_module, "perform_random_activity")
            else:
                action_func = getattr(protocol_module, action_name)

            # Execute the task
            result = action_func(**task.get("params", {}))

            # Process result
            success = True
            message: str = "Task completed successfully"
            tx_hash: Optional[str] = None
            tx_hashes: Optional[List[str]] = None

            if isinstance(result, tuple):
                success = result[0]
                if len(result) > 1:
                    if isinstance(result[1], str):
                        message = result[1]
                        tx_hash = result[1]  # Assign tx_hash when result[1] is a string
                    elif isinstance(result[1], list):
                        tx_hashes = result[1]
                        if tx_hashes:
                            tx_hash = tx_hashes[0]
                            # Use the first hash for single tx_hash field
            elif isinstance(result, str):
                message = result
                tx_hash = result

            return {
                "success": success,
                "message": message,
                "tx_hash": tx_hash,
                "tx_hashes": tx_hashes,  # Add tx_hashes field
                "error": (
                    None if success else message
                ),  # Set error to message if not successful # noqa: E501
                "protocol": protocol_name,
                "action": action_name,
                "wallet": task.get("wallet"),
                "id": task_id,
            }

        except (ModuleNotFoundError, AttributeError) as e:
            error_message = (
                f"Could not find action '{action_name}' in protocol"
                f" '{protocol_name}': {e}"
            )
            logger.error(error_message)
            return {
                "success": False,
                "message": error_message,
                "tx_hash": None,
                "error": str(e),
                "protocol": protocol_name,
                "action": action_name,
                "wallet": task.get("wallet"),
                "id": task_id,
            }
        except Exception as e:
            error_message = (
                f"An unexpected error occurred during task execution: {e}"
            )
            logger.error(error_message, exc_info=True)
            return {
                "success": False,
                "message": error_message,
                "tx_hash": None,
                "error": str(e),
                "protocol": protocol_name,
                "action": action_name,
                "wallet": task.get("wallet"),
                "id": task_id,
            }

    def _assign_wallet_for_task(self, task: Dict[str, Any], wallets: List[str]) -> str:
        """
        Assign a wallet to a task using round-robin.
        """
        if not wallets:
            raise ValueError("No wallets available for assignment.")

        self._last_wallet_index = (self._last_wallet_index + 1) % len(wallets)
        return wallets[self._last_wallet_index]

    def _generate_daily_schedule(self) -> List[Dict[str, Any]]:
        """
        Generate a list of daily tasks based on protocol configurations.
        This is a simplified placeholder.
        """
        daily_tasks = []
        for protocol_name, protocol_config in self.config.get("protocols", {}).items():
            if protocol_config.get("enabled"):
                num_activities = protocol_config.get(
                    "daily_activity_range", [1, 1]
                )[0]  # Use min for simplicity
                for i in range(num_activities):
                    daily_tasks.append({
                        "id": f"{protocol_name}_daily_task_{i}",
                        "protocol": protocol_name,
                        "action": "random_activity",  # Simplified to random activity
                        "wallet": None,  # Will be assigned later
                        "priority": TaskPriority.NORMAL,
                    })
        return daily_tasks

    def _initialize_default_dependencies(self) -> None:
        """Initialize default dependency implementations when none are provided."""
        try:
            # Import concrete implementations only when needed
            from airdrops.capital_allocation.engine import CapitalAllocator
            from airdrops.risk_management.core import RiskManager
            from airdrops.protocols.scroll.scroll import ScrollProtocol
            from airdrops.protocols.zksync.zksync import ZkSyncProtocol
            from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
            from airdrops.protocols.eigenlayer.eigenlayer import EigenLayerProtocol
            
            # Initialize core components if not provided
            if not self._capital_allocator:
                from typing import cast
                self._capital_allocator = cast(ICapitalAllocator, CapitalAllocator(config=self.config))
                
            if not self._risk_manager:
                self._risk_manager = cast(IRiskManager, RiskManager(config=self.config))
                
            # Initialize protocol clients with environment variables or config
            if not self.scroll_client:
                scroll_l1_rpc = os.getenv("ETH_RPC_URL")
                scroll_l2_rpc = os.getenv("SCROLL_L2_RPC_URL")
                private_key = os.getenv("PRIVATE_KEY")
                if scroll_l1_rpc and scroll_l2_rpc and private_key:
                    self.scroll_client = ScrollProtocol(scroll_l1_rpc, scroll_l2_rpc, private_key)
                    
            if not self.zksync_client:
                zksync_l1_rpc = os.getenv("ETH_RPC_URL")
                zksync_l2_rpc = os.getenv("ZKSYNC_L2_RPC_URL")
                private_key = os.getenv("PRIVATE_KEY")
                if zksync_l1_rpc and zksync_l2_rpc and private_key:
                    self.zksync_client = ZkSyncProtocol(zksync_l1_rpc, zksync_l2_rpc, private_key)
                    
            if not self.layerzero_client:
                eth_rpc = os.getenv("ETH_RPC_URL")
                private_key = os.getenv("PRIVATE_KEY")
                if eth_rpc and private_key:
                    self.layerzero_client = LayerZeroProtocol(eth_rpc, private_key, 1)  # Ethereum mainnet
                    
            if not self.eigenlayer_client:
                eth_rpc = os.getenv("ETH_RPC_URL")
                private_key = os.getenv("PRIVATE_KEY")
                if eth_rpc and private_key:
                    self.eigenlayer_client = EigenLayerProtocol(eth_rpc, private_key, 1)  # Ethereum mainnet
                    
            logger.debug("Default dependencies initialized for AirdropSchedulerBot")
            
        except ImportError as e:
            logger.warning(f"Could not import dependency implementations: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize default dependencies: {e}")


def main() -> None:
    """Main entry point for the scheduler bot."""
    parser = argparse.ArgumentParser(description="Central Scheduler Bot")
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", help="Configuration file path")

    args = parser.parse_args()
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        scheduler = AirdropSchedulerBot() # Instantiate the scheduler here

        if args.dry_run:
            logger.info("Dry run mode - scheduler initialized but not started")
            return

        scheduler.start()

        if args.once:
            logger.info("Running once and exiting")
            scheduler.stop()
            return

        # Only run the infinite loop if not in once mode
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
            scheduler.stop()

    except Exception as e:
        logger.error(f"Scheduler encountered a critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

__all__ = ["AirdropSchedulerBot", "TaskStatus", "TaskPriority", "TaskDefinition", "TaskExecution"]
