"""
Central Scheduler implementation for airdrops automation.

This module provides the CentralScheduler class that orchestrates airdrop-related
tasks using APScheduler with DAG-based dependency management, market awareness,
and robust error handling with retry logic.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Set, Tuple, List
from dataclasses import dataclass
from enum import Enum
import argparse
import importlib
import sys

from airdrops.monitoring.alerter import Alert, AlertSeverity, AlertStatus

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


class CentralScheduler:
    """
    Central Scheduler for orchestrating airdrop-related tasks.

    This class provides comprehensive task scheduling capabilities with:
    - APScheduler integration for flexible scheduling
    - DAG-based dependency management
    - Market condition awareness
    - Retry logic with exponential backoff
    - Priority-based task execution

    Example:
        >>> scheduler = CentralScheduler()
        >>> scheduler.add_job(
        ...     task_id="daily_bridge",
        ...     func=bridge_eth_to_scroll,
        ...     trigger="cron",
        ...     hour=10,
        ...     minute=0
        ... )
        >>> scheduler.start()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Central Scheduler.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._scheduler: Optional[BlockingScheduler] = None
        self._task_definitions: Dict[str, TaskDefinition] = {}
        self._task_executions: Dict[str, TaskExecution] = {}
        self._running = False

        # Configuration with defaults
        self.max_retries = self.config.get("scheduler", {}).get("max_retries", 3)
        self.retry_delay = self.config.get("scheduler", {}).get(
            "retry_delay", 60.0
        )
        self._max_concurrent_jobs = self.config.get("scheduler", {}).get(
            "max_concurrent_tasks", 5
        )
        self._last_wallet_index = -1

        logger.info("CentralScheduler initialized with config: %s", self.config)

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
            ...     args=(100,),
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
                args=(task_id,),
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
                    f"{task_def.action}) failed permanently: {error}"
                )
                alert_labels = {
                    "task_id": task_id,
                    "protocol": task_def.protocol,
                    "action": task_def.action,
                    "wallet": execution.wallet,
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
        if DateTrigger is None:
            logger.error("APScheduler not available, cannot schedule retry")
            return False

        if self._scheduler is not None:
            self._scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=DateTrigger(run_date=retry_time),
                args=(task_id,),
                id=f"{task_id}_retry_{execution.retry_count}",
                replace_existing=True
            )

        return True

    def start(self) -> None:
        """
        Initialize and start the APScheduler.

        Example:
            >>> scheduler = CentralScheduler()
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

        logger.info("CentralScheduler started successfully")

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
        logger.info("CentralScheduler stopped gracefully")

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
            return {
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
        # Simple cycle detection - can be enhanced for complex DAGs
        visited = set()

        def has_cycle(task_id: str) -> bool:
            if task_id in visited:
                return True
            visited.add(task_id)

            task = self._task_definitions.get(task_id)
            if task:
                for dep in (task.dependencies or set()):
                    if has_cycle(dep):
                        return True
            visited.remove(task_id)
            return False

        if has_cycle(task_def.task_id):
            raise ValueError(
                f"Circular dependency detected for task {task_def.task_id}"
            )

    def _create_trigger(self, trigger_type: str, **kwargs: Any) -> Any:
        """Create appropriate trigger object based on type."""
        if CronTrigger is None:
            raise ImportError("APScheduler not available")

        if trigger_type == "cron":
            return CronTrigger(**kwargs)
        elif trigger_type == "date":
            return DateTrigger(**kwargs)
        elif trigger_type == "interval":
            return IntervalTrigger(**kwargs)
        else:
            raise ValueError(
                f"Unsupported trigger type: {trigger_type}"
            )

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
        scheduler = CentralScheduler()

        if args.dry_run:
            logger.info("Dry run mode - scheduler initialized but not started")
            return

        scheduler.start()

        if args.once:
            logger.info("Running once and exiting")
            scheduler.stop()
        else:
            logger.info("Scheduler running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                scheduler.stop()

    except Exception as error:
        logger.error("Scheduler failed: %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
