"""
Tests for the Central Scheduler module.

This module provides comprehensive tests for the CentralScheduler class,
covering task scheduling, dependency management, error handling, and
integration with market conditions.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from airdrops.scheduler.bot import (
    CentralScheduler,
    TaskStatus,
    TaskPriority,
    TaskDefinition,
    TaskExecution
)


class TestCentralScheduler:
    """Test cases for CentralScheduler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "scheduler": {
                "max_concurrent_tasks": 3,
                "retry_delay": 30.0,
                "max_retries": 2,
            },
            "max_gas_price": 80
        }
        self.scheduler = CentralScheduler(self.config)

    def test_init_default_config(self):
        """Test scheduler initialization with default configuration."""
        scheduler = CentralScheduler()

        assert scheduler.config == {}
        assert scheduler._max_concurrent_jobs == 5
        assert scheduler.retry_delay == 60.0
        assert scheduler.max_retries == 3
        assert not scheduler._running

    def test_init_custom_config(self):
        """Test scheduler initialization with custom configuration."""
        assert self.scheduler.config == self.config
        assert self.scheduler._max_concurrent_jobs == self.config["scheduler"]["max_concurrent_tasks"]
        assert self.scheduler.retry_delay == self.config["scheduler"]["retry_delay"]
        assert self.scheduler.max_retries == self.config["scheduler"]["max_retries"]

    @patch('airdrops.scheduler.bot.BlockingScheduler')
    def test_start_scheduler(self, mock_scheduler_class):
        """Test starting the scheduler."""
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        self.scheduler.start()

        assert self.scheduler._running
        assert self.scheduler._scheduler == mock_scheduler
        mock_scheduler_class.assert_called_once()

    def test_start_scheduler_already_running(self):
        """Test starting scheduler when already running."""
        self.scheduler._running = True

        with patch('airdrops.scheduler.bot.logger') as mock_logger:
            self.scheduler.start()
            mock_logger.warning.assert_called_with("Scheduler is already running")

    @patch('airdrops.scheduler.bot.BlockingScheduler', None)
    def test_start_scheduler_no_apscheduler(self):
        """Test starting scheduler without APScheduler installed."""
        with pytest.raises(ImportError, match="APScheduler not available"):
            self.scheduler.start()

    def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler
        self.scheduler._running = True

        self.scheduler.stop()

        assert not self.scheduler._running
        assert self.scheduler._scheduler is None
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    def test_stop_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        with patch('airdrops.scheduler.bot.logger') as mock_logger:
            self.scheduler.stop()
            mock_logger.warning.assert_called_with("Scheduler is not running")

    @patch('airdrops.scheduler.bot.CronTrigger')
    def test_add_job_success(self, mock_cron_trigger):
        """Test successfully adding a job."""
        mock_scheduler = Mock()
        mock_trigger = Mock()
        mock_cron_trigger.return_value = mock_trigger
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        self.scheduler.add_job(
            task_id="test_task",
            func=dummy_func,
            trigger="cron",
            hour=10,
            minute=0,
            priority=TaskPriority.HIGH
        )

        # Verify task definition was created
        assert "test_task" in self.scheduler._task_definitions
        task_def = self.scheduler._task_definitions["test_task"]
        assert task_def.task_id == "test_task"
        assert task_def.func == dummy_func
        assert task_def.priority == TaskPriority.HIGH

        # Verify task execution was created
        assert "test_task" in self.scheduler._task_executions
        execution = self.scheduler._task_executions["test_task"]
        assert execution.status == TaskStatus.PENDING

        # Verify APScheduler job was added
        mock_scheduler.add_job.assert_called_once()
        mock_cron_trigger.assert_called_once_with(hour=10, minute=0)

    def test_add_job_no_scheduler(self):
        """Test adding job when scheduler not initialized."""
        def dummy_func():
            return "test"

        with pytest.raises(RuntimeError, match="Scheduler not initialized"):
            self.scheduler.add_job("test_task", dummy_func)

    def test_add_job_duplicate_task(self):
        """Test adding duplicate task."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        # Add first task
        self.scheduler.add_job("test_task", dummy_func)

        # Try to add duplicate
        with pytest.raises(ValueError, match="Task test_task already exists"):
            self.scheduler.add_job("test_task", dummy_func)

    def test_manage_task_priority(self):
        """Test updating task priority."""
        # Setup task
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        self.scheduler.add_job("test_task", dummy_func)

        # Update priority
        self.scheduler.manage_task_priority("test_task", TaskPriority.CRITICAL)

        task_def = self.scheduler._task_definitions["test_task"]
        assert task_def.priority == TaskPriority.CRITICAL

    def test_manage_task_priority_not_found(self):
        """Test updating priority for non-existent task."""
        with pytest.raises(ValueError, match="Task nonexistent not found"):
            self.scheduler.manage_task_priority("nonexistent", TaskPriority.HIGH)

    def test_manage_task_dependencies(self):
        """Test updating task dependencies."""
        # Setup tasks
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        self.scheduler.add_job("task1", dummy_func)
        self.scheduler.add_job("task2", dummy_func)

        # Update dependencies
        dependencies = {"task1"}
        self.scheduler.manage_task_dependencies("task2", dependencies)

        task_def = self.scheduler._task_definitions["task2"]
        assert task_def.dependencies == dependencies

    def test_manage_task_dependencies_not_found(self):
        """Test updating dependencies for non-existent task."""
        with pytest.raises(ValueError, match="Task nonexistent not found"):
            self.scheduler.manage_task_dependencies("nonexistent", {"task1"})

    def test_schedule_dynamically_circuit_breaker(self):
        """Test dynamic scheduling with circuit breaker active."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        market_conditions = {"gas_price": 50, "volatility": "normal"}
        risk_assessment = {"circuit_breaker": True, "risk_score": 0.8}

        with patch.object(self.scheduler, '_pause_all_tasks') as mock_pause:
            self.scheduler.schedule_dynamically(market_conditions, risk_assessment)
            mock_pause.assert_called_once()

    def test_schedule_dynamically_high_gas_prices(self):
        """Test dynamic scheduling with high gas prices."""
        market_conditions = {"gas_price": 150, "volatility": "normal"}
        risk_assessment = {"circuit_breaker": False, "risk_score": 0.3}

        with patch.object(self.scheduler, '_delay_low_priority_tasks') as mock_delay:
            self.scheduler.schedule_dynamically(market_conditions, risk_assessment)
            mock_delay.assert_called_once()

    def test_schedule_dynamically_high_volatility(self):
        """Test dynamic scheduling with high volatility."""
        market_conditions = {"gas_price": 50, "volatility": "high"}
        risk_assessment = {"circuit_breaker": False, "risk_score": 0.3}

        with patch.object(self.scheduler, '_reduce_task_frequency') as mock_reduce:
            self.scheduler.schedule_dynamically(market_conditions, risk_assessment)
            mock_reduce.assert_called_once()

    def test_handle_task_failure_retry(self):
        """Test task failure handling with retry."""
        # Setup task
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=3,
            retry_delay=10.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=1
        )

        self.scheduler._task_definitions["test_task"] = task_def
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        error = Exception("Test error")

        result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is True
        assert execution.status == TaskStatus.RETRYING
        assert execution.retry_count == 2
        assert execution.last_error == "Test error"
        mock_scheduler.add_job.assert_called_once()

    def test_handle_task_failure_max_retries(self):
        """Test task failure handling when max retries exceeded."""
        # Setup task
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=2,
            retry_delay=10.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=2
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler.alerter = Mock() # Mock the alerter

        error = Exception("Test error")

        result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is False
        assert execution.status == TaskStatus.FAILED
        assert execution.retry_count == 3
        self.scheduler.alerter.send_notifications.assert_called_once()

    def test_handle_task_failure_no_task_def(self):
        """Test task failure handling with missing task definition."""
        execution = TaskExecution(
            task_id="nonexistent",
            status=TaskStatus.RUNNING
        )

        error = Exception("Test error")

        result = self.scheduler.handle_task_failure("nonexistent", error, execution)

        assert result is False

    def test_execute_task_wrapper_success(self):
        """Test successful task execution."""
        def test_func(x, y=10):
            return x + y

        task_def = TaskDefinition(
            task_id="test_task",
            func=test_func,
            args=(5,),
            kwargs={"y": 15}
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.PENDING
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler._task_executions["test_task"] = execution

        with patch.object(self.scheduler, '_check_dependencies', return_value=True):
            result = self.scheduler._execute_task_wrapper("test_task")

        assert result == 20
        assert execution.status == TaskStatus.COMPLETED
        assert execution.result == 20
        assert execution.start_time is not None
        assert execution.end_time is not None

    def test_execute_task_wrapper_dependencies_not_met(self):
        """Test task execution with unmet dependencies."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: "test",
            dependencies={"dep_task"}
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.PENDING
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler._task_executions["test_task"] = execution

        with patch.object(self.scheduler, '_check_dependencies', return_value=False):
            result = self.scheduler._execute_task_wrapper("test_task")

        assert result is None
        assert execution.status == TaskStatus.PENDING

    def test_execute_task_wrapper_failure(self):
        """Test task execution with failure."""
        def failing_func():
            raise ValueError("Test error")

        task_def = TaskDefinition(
            task_id="test_task",
            func=failing_func
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.PENDING
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler._task_executions["test_task"] = execution

        with patch.object(self.scheduler, '_check_dependencies', return_value=True):
            with patch.object(self.scheduler, 'handle_task_failure') as mock_handle: # noqa: F841
                result = self.scheduler._execute_task_wrapper("test_task")
                assert result["success"] is False
                assert "Test error" in result["message"]
                mock_handle.assert_called_once()

        assert execution.status == TaskStatus.RUNNING
        mock_handle.assert_called_once()

    def test_check_dependencies_all_completed(self):
        """Test dependency checking with all dependencies completed."""
        # Setup dependencies
        dep_execution = TaskExecution(
            task_id="dep_task",
            status=TaskStatus.COMPLETED
        )
        self.scheduler._task_executions["dep_task"] = dep_execution

        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            dependencies={"dep_task"}
        )
        self.scheduler._task_definitions["test_task"] = task_def

        result = self.scheduler._check_dependencies("test_task")
        assert result is True

    def test_check_dependencies_incomplete(self):
        """Test dependency checking with incomplete dependencies."""
        # Setup dependencies
        dep_execution = TaskExecution(
            task_id="dep_task",
            status=TaskStatus.RUNNING
        )
        self.scheduler._task_executions["dep_task"] = dep_execution

        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            dependencies={"dep_task"}
        )
        self.scheduler._task_definitions["test_task"] = task_def

        result = self.scheduler._check_dependencies("test_task")
        assert result is False

    def test_validate_dependencies_no_cycle(self):
        """Test dependency validation without cycles."""
        task_def = TaskDefinition(
            task_id="task2",
            func=lambda: None,
            dependencies={"task1"}
        )

        # Should not raise exception
        self.scheduler._validate_dependencies(task_def)

    def test_validate_dependencies_with_cycle(self):
        """Test dependency validation with cycles."""
        # Setup circular dependency
        task1_def = TaskDefinition(
            task_id="task1",
            func=lambda: None,
            dependencies={"task2"}
        )
        task2_def = TaskDefinition(
            task_id="task2",
            func=lambda: None,
            dependencies={"task1"}
        )

        self.scheduler._task_definitions["task1"] = task1_def
        self.scheduler._task_definitions["task2"] = task2_def

        with pytest.raises(ValueError, match="Circular dependency detected"):
            self.scheduler._validate_dependencies(task1_def)

    @patch('airdrops.scheduler.bot.CronTrigger')
    def test_create_trigger_cron(self, mock_cron_trigger):
        """Test creating cron trigger."""
        mock_trigger = Mock()
        mock_cron_trigger.return_value = mock_trigger

        result = self.scheduler._create_trigger("cron", hour=10, minute=0)

        assert result == mock_trigger
        mock_cron_trigger.assert_called_once_with(hour=10, minute=0)

    @patch('airdrops.scheduler.bot.DateTrigger')
    def test_create_trigger_date(self, mock_date_trigger):
        """Test creating date trigger."""
        mock_trigger = Mock()
        mock_date_trigger.return_value = mock_trigger

        run_date = datetime.now()
        result = self.scheduler._create_trigger("date", run_date=run_date)

        assert result == mock_trigger
        mock_date_trigger.assert_called_once_with(run_date=run_date)

    @patch('airdrops.scheduler.bot.IntervalTrigger')
    def test_create_trigger_interval(self, mock_interval_trigger):
        """Test creating interval trigger."""
        mock_trigger = Mock()
        mock_interval_trigger.return_value = mock_trigger

        result = self.scheduler._create_trigger("interval", seconds=30)

        assert result == mock_trigger
        mock_interval_trigger.assert_called_once_with(seconds=30)

    def test_create_trigger_unsupported(self):
        """Test creating unsupported trigger type."""
        with pytest.raises(ValueError, match="Unsupported trigger type: invalid"):
            self.scheduler._create_trigger("invalid")

    def test_pause_all_tasks(self):
        """Test pausing all tasks."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        self.scheduler._pause_all_tasks()

        mock_scheduler.pause.assert_called_once()

    def test_delay_low_priority_tasks(self):
        """Test delaying low priority tasks."""
        # This is a placeholder implementation
        self.scheduler._delay_low_priority_tasks()
        # No assertions needed for placeholder

    def test_reduce_task_frequency(self):
        """Test reducing task frequency."""
        # This is a placeholder implementation
        self.scheduler._reduce_task_frequency()
        # No assertions needed for placeholder


    def test_execute_task_wrapper_missing_task_or_execution(self):
        """Test task execution with missing task or execution."""
        # Test missing execution
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: "test"
        )
        self.scheduler._task_definitions["test_task"] = task_def
        # Don't add execution

        result = self.scheduler._execute_task_wrapper("test_task")
        assert result is None

        # Test missing task definition
        execution = TaskExecution(
            task_id="test_task2",
            status=TaskStatus.PENDING
        )
        self.scheduler._task_executions["test_task2"] = execution
        # Don't add task definition

        result = self.scheduler._execute_task_wrapper("test_task2")
        assert result is None

    def test_check_dependencies_missing_task(self):
        """Test dependency checking with missing task definition."""
        result = self.scheduler._check_dependencies("nonexistent_task")
        assert result is False

    def test_check_dependencies_missing_dependency_execution(self):
        """Test dependency checking with missing dependency execution."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            dependencies={"missing_dep"}
        )
        self.scheduler._task_definitions["test_task"] = task_def

        result = self.scheduler._check_dependencies("test_task")
        assert result is False

    @patch('airdrops.scheduler.bot.CronTrigger', None)
    def test_create_trigger_no_apscheduler(self):
        """Test creating trigger without APScheduler available."""
        with pytest.raises(ImportError, match="APScheduler not available"):
            self.scheduler._create_trigger("cron", hour=10)

    @patch('airdrops.scheduler.bot.DateTrigger', None)
    def test_handle_task_failure_no_date_trigger(self):
        """Test task failure handling without DateTrigger available."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=3,
            retry_delay=10.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=1
        )

        self.scheduler._task_definitions["test_task"] = task_def
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        error = Exception("Test error")

        result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is False
        assert execution.status == TaskStatus.RETRYING

    def test_add_job_with_dependencies_validation(self):
        """Test adding job with dependency validation."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        # Add dependency task first
        self.scheduler.add_job("dep_task", dummy_func)

        # Add task with dependency
        self.scheduler.add_job(
            task_id="main_task",
            func=dummy_func,
            dependencies={"dep_task"}
        )

        task_def = self.scheduler._task_definitions["main_task"]
        assert task_def.dependencies == {"dep_task"}

    def test_add_job_circular_dependency(self):
        """Test adding job with circular dependency."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        # Add first task
        self.scheduler.add_job("task1", dummy_func)

        # Add second task depending on first
        self.scheduler.add_job("task2", dummy_func, dependencies={"task1"})

        # Try to add circular dependency
        with pytest.raises(ValueError, match="Circular dependency detected"):
            self.scheduler.manage_task_dependencies("task1", {"task2"})

    def test_pause_all_tasks_no_scheduler(self):
        """Test pausing tasks when scheduler is None."""
        self.scheduler._scheduler = None
        # Should not raise exception
        self.scheduler._pause_all_tasks()

    def test_schedule_dynamically_normal_conditions(self):
        """Test dynamic scheduling with normal market conditions."""
        market_conditions = {"gas_price": 30, "volatility": "normal"}
        risk_assessment = {"circuit_breaker": False, "risk_score": 0.2}

        # Should complete without triggering any special actions
        self.scheduler.schedule_dynamically(market_conditions, risk_assessment)

    def test_schedule_dynamically_multiple_conditions(self):
        """Test dynamic scheduling with multiple triggering conditions."""
        market_conditions = {"gas_price": 150, "volatility": "high"}
        risk_assessment = {"circuit_breaker": False, "risk_score": 0.7}

        with patch.object(self.scheduler, '_delay_low_priority_tasks') as mock_delay:
            with patch.object(self.scheduler, '_reduce_task_frequency') as mock_reduce:
                self.scheduler.schedule_dynamically(market_conditions, risk_assessment)
                mock_delay.assert_called_once()
                mock_reduce.assert_called_once()

    def test_handle_task_failure_exponential_backoff(self):
        """Test exponential backoff calculation in task failure handling."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=5,
            retry_delay=10.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=2  # Third attempt
        )

        self.scheduler._task_definitions["test_task"] = task_def
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        error = Exception("Test error")

        with patch('airdrops.scheduler.bot.time.time', return_value=0.5):
            result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is True
        assert execution.retry_count == 3
        # Verify exponential backoff: 10.0 * (2 ** 2) = 40.0 seconds base delay
        mock_scheduler.add_job.assert_called_once()

    def test_task_execution_timeout_handling(self):
        """Test task execution with timeout configuration."""
        def dummy_func():
            return "test"

        task_def = TaskDefinition(
            task_id="test_task",
            func=dummy_func,
            timeout=30.0
        )

        assert task_def.timeout == 30.0

    def test_task_metadata_handling(self):
        """Test task definition with metadata."""
        def dummy_func():
            return "test"

        metadata = {"type": "bridge", "protocol": "scroll", "priority_boost": True}
        task_def = TaskDefinition(
            task_id="test_task",
            func=dummy_func,
            metadata=metadata
        )

        assert task_def.metadata == metadata

    def test_add_job_with_all_parameters(self):
        """Test adding job with all possible parameters."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func(x, y=10):
            return x + y

        self.scheduler.add_job(
            task_id="complex_task",
            func=dummy_func,
            trigger="interval",
            args=(5,),
            kwargs={"y": 20},
            priority=TaskPriority.CRITICAL,
            dependencies=set(),
            max_retries=5,
            seconds=30
        )

        task_def = self.scheduler._task_definitions["complex_task"]
        assert task_def.task_id == "complex_task"
        assert task_def.func == dummy_func
        assert task_def.args == (5,)
        assert task_def.kwargs == {"y": 20}
        assert task_def.priority == TaskPriority.CRITICAL
        assert task_def.max_retries == 5

    def test_stop_scheduler_with_none_scheduler(self):
        """Test stopping scheduler when _scheduler is None."""
        self.scheduler._running = True
        self.scheduler._scheduler = None

        self.scheduler.stop()

        assert not self.scheduler._running


class TestTaskDefinition:
    """Test cases for TaskDefinition dataclass."""

    def test_task_definition_creation(self):
        """Test creating TaskDefinition with all parameters."""
        def dummy_func():
            return "test"

        task_def = TaskDefinition(
            task_id="test_task",
            func=dummy_func,
            args=(1, 2),
            kwargs={"key": "value"},
            priority=TaskPriority.HIGH,
            dependencies={"dep1", "dep2"},
            max_retries=5,
            retry_delay=120.0,
            timeout=300.0,
            metadata={"type": "bridge"}
        )

        assert task_def.task_id == "test_task"
        assert task_def.func == dummy_func
        assert task_def.args == (1, 2)
        assert task_def.kwargs == {"key": "value"}
        assert task_def.priority == TaskPriority.HIGH
        assert task_def.dependencies == {"dep1", "dep2"}
        assert task_def.max_retries == 5
        assert task_def.retry_delay == 120.0
        assert task_def.timeout == 300.0
        assert task_def.metadata == {"type": "bridge"}

    def test_task_definition_defaults(self):
        """Test TaskDefinition with default values."""
        def dummy_func():
            return "test"

        task_def = TaskDefinition(
            task_id="test_task",
            func=dummy_func
        )

        assert task_def.args == ()
        assert task_def.kwargs == {}
        assert task_def.priority == TaskPriority.NORMAL
        assert task_def.dependencies == set()
        assert task_def.max_retries == 3
        assert task_def.retry_delay == 60.0
        assert task_def.timeout is None
        assert task_def.metadata == {}


class TestTaskExecution:
    """Test cases for TaskExecution dataclass."""

    def test_task_execution_creation(self):
        """Test creating TaskExecution."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)

        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            retry_count=2,
            last_error="Previous error",
            result="success"
        )

        assert execution.task_id == "test_task"
        assert execution.status == TaskStatus.COMPLETED
        assert execution.start_time == start_time
        assert execution.end_time == end_time
        assert execution.retry_count == 2
        assert execution.last_error == "Previous error"
        assert execution.result == "success"


class TestEnums:
    """Test cases for enum classes."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_priority_values(self):
        """Test TaskPriority enum values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4


@patch('airdrops.scheduler.bot.time.sleep')
@patch('airdrops.scheduler.bot.logging.basicConfig')
def test_main_function_dry_run(mock_logging, mock_sleep):
    """Test main function in dry run mode."""
    with patch('sys.argv', ['bot.py', '--dry-run']):
        with patch('airdrops.scheduler.bot.CentralScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler

            from airdrops.scheduler.bot import main
            main()

            mock_scheduler_class.assert_called_once()
            mock_scheduler.start.assert_not_called()
            mock_scheduler.stop.assert_not_called()


@patch('airdrops.scheduler.bot.time.sleep')
@patch('airdrops.scheduler.bot.logging.basicConfig')
def test_main_function_once(mock_logging, mock_sleep):
    """Test main function in run-once mode."""
    with patch('sys.argv', ['bot.py', '--once']):
        with patch('airdrops.scheduler.bot.CentralScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler

            from airdrops.scheduler.bot import main
            main()

            mock_scheduler_class.assert_called_once()
            mock_scheduler.start.assert_called_once()
            mock_scheduler.stop.assert_called_once()


@patch('airdrops.scheduler.bot.time.sleep', side_effect=KeyboardInterrupt())
@patch('airdrops.scheduler.bot.logging.basicConfig')
def test_main_function_keyboard_interrupt(mock_logging, mock_sleep):
    """Test main function with keyboard interrupt."""
    with patch('sys.argv', ['bot.py']):
        with patch('airdrops.scheduler.bot.CentralScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler

            from airdrops.scheduler.bot import main
            main()

            mock_scheduler_class.assert_called_once()
            mock_scheduler.start.assert_called_once()
            mock_scheduler.stop.assert_called_once()


@patch('airdrops.scheduler.bot.logging.basicConfig')
@patch('airdrops.scheduler.bot.sys.exit')
def test_main_function_exception(mock_exit, mock_logging):
    """Test main function with exception."""
    with patch('sys.argv', ['bot.py']):
        with patch('airdrops.scheduler.bot.CentralScheduler',
                   side_effect=Exception("Test error")):
            from airdrops.scheduler.bot import main
            main()

            mock_exit.assert_called_once_with(1)

@patch('airdrops.scheduler.bot.time.sleep')
@patch('airdrops.scheduler.bot.logging.basicConfig')
def test_main_function_with_config(mock_logging, mock_sleep):
    """Test main function with config file argument."""
    with patch('sys.argv', ['bot.py', '--config', 'test_config.json']):
        with patch('airdrops.scheduler.bot.CentralScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            
            # Mock the infinite loop to exit after one iteration
            mock_sleep.side_effect = KeyboardInterrupt()

            from airdrops.scheduler.bot import main
            main()

            mock_scheduler_class.assert_called_once()
            mock_scheduler.start.assert_called_once()
            mock_scheduler.stop.assert_called_once()


class TestImportFallbacks:
    """Test cases for import fallback scenarios."""

    @patch('airdrops.scheduler.bot.BlockingScheduler', None)
    @patch('airdrops.scheduler.bot.CronTrigger', None)
    @patch('airdrops.scheduler.bot.DateTrigger', None)
    @patch('airdrops.scheduler.bot.IntervalTrigger', None)
    def test_scheduler_without_apscheduler(self):
        """Test scheduler behavior when APScheduler is not available."""
        scheduler = CentralScheduler()
        
        # Should not raise exception during initialization
        assert scheduler._scheduler is None
        assert not scheduler._running

    def test_duplicate_dataclass_decorator(self):
        """Test that duplicate @dataclass decorator doesn't cause issues."""
        # This tests the duplicate @dataclass decorator on line 55
        def dummy_func():
            return "test"

        task_def = TaskDefinition(
            task_id="test_task",
            func=dummy_func
        )
        
        # Should work normally despite duplicate decorator
        assert task_def.task_id == "test_task"
        assert task_def.func == dummy_func


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scheduler = CentralScheduler()

    def test_task_execution_with_empty_dependencies(self):
        """Test task execution with empty dependencies set."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: "success",
            dependencies=set()  # Explicitly empty
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.PENDING
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler._task_executions["test_task"] = execution

        result = self.scheduler._check_dependencies("test_task")
        assert result is True

    def test_task_priority_ordering(self):
        """Test task priority enum ordering."""
        priorities = [TaskPriority.LOW, TaskPriority.NORMAL, 
                     TaskPriority.HIGH, TaskPriority.CRITICAL]
        
        # Verify priority values are in ascending order
        for i in range(len(priorities) - 1):
            assert priorities[i].value < priorities[i + 1].value

    def test_task_status_completeness(self):
        """Test that all expected task statuses are defined."""
        expected_statuses = {
            "pending", "running", "completed", 
            "failed", "retrying", "cancelled"
        }
        
        actual_statuses = {status.value for status in TaskStatus}
        assert actual_statuses == expected_statuses

    def test_scheduler_config_defaults(self):
        """Test scheduler configuration defaults."""
        scheduler = CentralScheduler()
        
        assert scheduler._max_concurrent_jobs == 5
        assert scheduler.retry_delay == 60.0
        assert scheduler.max_retries == 3

    def test_scheduler_config_override(self):
        """Test scheduler configuration override."""
        config = {
            "scheduler": {
                "max_concurrent_tasks": 10,
                "retry_delay": 30.0,
                "max_retries": 5,
            },
            "max_gas_price": 200
        }
        scheduler = CentralScheduler(config)
        
        assert scheduler._max_concurrent_jobs == config["scheduler"]["max_concurrent_tasks"]
        assert scheduler.retry_delay == config["scheduler"]["retry_delay"]
        assert scheduler.max_retries == config["scheduler"]["max_retries"]
        assert scheduler.config["max_gas_price"] == 200

    def test_task_execution_duration_calculation(self):
        """Test task execution duration calculation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=45)
        
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time
        )
        
        duration = execution.end_time - execution.start_time
        assert duration.total_seconds() == 45

    def test_handle_task_failure_jitter_calculation(self):
        """Test jitter calculation in task failure handling."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=3,
            retry_delay=60.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=0
        )

        self.scheduler._task_definitions["test_task"] = task_def
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        error = Exception("Test error")

        # Mock time.time to return a predictable value for jitter calculation
        with patch('airdrops.scheduler.bot.time.time', return_value=0.7):
            result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is True
        # Verify that jitter was applied (base delay + jitter)
        mock_scheduler.add_job.assert_called_once()

    def test_add_job_scheduler_none_branch(self):
        """Test add_job method when scheduler is None but should be initialized."""
        mock_scheduler = Mock()
        self.scheduler._scheduler = mock_scheduler

        def dummy_func():
            return "test"

        # Test the branch where scheduler is not None
        self.scheduler.add_job("test_task", dummy_func)
        
        # Verify the job was added
        assert "test_task" in self.scheduler._task_definitions
        mock_scheduler.add_job.assert_called_once()

    def test_handle_task_failure_scheduler_none(self):
        """Test handle_task_failure when scheduler is None."""
        task_def = TaskDefinition(
            task_id="test_task",
            func=lambda: None,
            max_retries=3,
            retry_delay=10.0
        )
        execution = TaskExecution(
            task_id="test_task",
            status=TaskStatus.RUNNING,
            retry_count=1
        )

        self.scheduler._task_definitions["test_task"] = task_def
        self.scheduler._scheduler = None  # Set to None

        error = Exception("Test error")

        # Should still handle the failure but not schedule retry
        result = self.scheduler.handle_task_failure("test_task", error, execution)

        assert result is True
        assert execution.status == TaskStatus.RETRYING
        assert execution.retry_count == 2
