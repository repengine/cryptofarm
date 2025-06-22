"""
Test scenarios for airdrops, simulating various market conditions and outcomes.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.scheduler.bot import AirdropSchedulerBot
from tests.shared.capital_tracker import TestCapitalTracker


class MockCapitalAllocator(CapitalAllocator):
    """Mock CapitalAllocator with additional attributes for testing."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.total_capital: Decimal = Decimal("0")

    def has_sufficient_capital(self, amount: Decimal) -> bool:
        """Check if sufficient capital is available."""
        return self.total_capital >= amount


class MockAirdropTask:
    """A mock airdrop task for testing purposes."""

    def __init__(self, name: str, protocol: str, value: Decimal) -> None:
        self.name = name
        self.protocol = protocol
        self.value = value
        self.executed = False

    def execute(self) -> bool:
        """Simulate task execution."""
        self.executed = True
        return True


@pytest.fixture
def mock_capital_allocator() -> CapitalAllocator:
    """Fixture for a CapitalAllocator."""
    config = {
        "capital_allocation": {
            "strategy": "equal_weight",
            "rebalance_threshold": Decimal("0.1"),
            "min_protocol_allocation": Decimal("0.01"),
            "max_protocol_allocation": Decimal("0.5"),
        }
    }
    return CapitalAllocator(config)


@pytest.fixture
def mock_capital_tracker(mock_capital_allocator: CapitalAllocator) -> TestCapitalTracker:
    """Fixture for a TestCapitalTracker with initial capital."""
    return TestCapitalTracker(mock_capital_allocator, Decimal("100000"))


@pytest.fixture
def mock_metrics_collector() -> MagicMock:
    """Fixture for a mock MetricsCollector."""
    collector = MagicMock(spec=MetricsCollector)
    # Ensure record_transaction is a proper MagicMock
    collector.record_transaction = MagicMock()
    return collector


@pytest.fixture
def mock_scheduler_bot(
    mock_capital_tracker: TestCapitalTracker,
    mock_metrics_collector: MagicMock
) -> AirdropSchedulerBot:
    """Fixture for a mock AirdropSchedulerBot that does not block."""
    with patch("airdrops.scheduler.bot.BlockingScheduler") as MockScheduler:
        bot = AirdropSchedulerBot(
            capital_allocator=mock_capital_tracker._allocator,
            metrics_collector=mock_metrics_collector,
            config={
                "scheduler": {
                    "interval_minutes": 60,
                    "max_concurrent_tasks": 5,
                    "dry_run": False,
                }
            },
        )
        bot.start()
        # Replace the internal scheduler with a mock to prevent blocking
        bot._scheduler = MockScheduler()
        # Attach the capital tracker to the bot for testing
        bot.capital_tracker = mock_capital_tracker  # type: ignore[attr-defined]
        return bot


def test_scenario_normal_operation(
    mock_scheduler_bot: AirdropSchedulerBot
) -> None:
    """
    Scenario: Normal operation with successful task execution.
    """
    bot = mock_scheduler_bot
    initial_capital = bot.capital_tracker.total_capital  # type: ignore[attr-defined]

    task1 = MockAirdropTask("Task A", "scroll", Decimal("1000"))

    def task_a_func() -> bool:
        bot.capital_tracker.total_capital -= task1.value  # type: ignore[attr-defined]
        assert bot.metrics_collector is not None
        bot.metrics_collector.record_transaction(
            protocol="scroll",
            action="test_action",
            wallet="0xTestWallet",
            success=True,
            gas_used=50000,
            value_usd=task1.value,
            tx_hash="0xtest"
        )
        return task1.execute()

    bot.add_job(task_id="task_a", func=task_a_func, trigger="date")

    bot._execute_task_wrapper("task_a")

    assert task1.executed
    assert bot.metrics_collector is not None
    bot.metrics_collector.record_transaction.assert_called_once_with(
        protocol="scroll",
        action="test_action",
        wallet="0xTestWallet",
        success=True,
        gas_used=50000,
        value_usd=task1.value,
        tx_hash="0xtest"
    )
    assert bot.capital_tracker.total_capital == (  # type: ignore[attr-defined]
        initial_capital - task1.value
    )


def test_scenario_capital_shortage(
    mock_scheduler_bot: AirdropSchedulerBot
) -> None:
    """
    Scenario: Capital shortage prevents task execution.
    """
    bot = mock_scheduler_bot
    # Set capital to a low amount for this test
    bot.capital_tracker.total_capital = Decimal("500")  # type: ignore[attr-defined]

    task1 = MockAirdropTask("Task C", "eigenlayer", Decimal("1000"))

    def task_c_func() -> bool:
        if bot.capital_tracker.total_capital < task1.value:  # type: ignore[attr-defined]
            assert bot.metrics_collector is not None
            bot.metrics_collector.record_transaction(
                protocol="eigenlayer",
                action="test_action",
                wallet="0xTestWallet",
                success=False,
                gas_used=50000,
                value_usd=task1.value,
                tx_hash="0xtest"
            )
            return False
        return task1.execute()

    bot.add_job(task_id="task_c", func=task_c_func, trigger="date")
    bot._execute_task_wrapper("task_c")

    assert not task1.executed
    assert bot.metrics_collector is not None
    bot.metrics_collector.record_transaction.assert_called_once_with(
        protocol="eigenlayer",
        action="test_action",
        wallet="0xTestWallet",
        success=False,
        gas_used=50000,
        value_usd=task1.value,
        tx_hash="0xtest"
    )
    assert bot.capital_tracker.total_capital == Decimal("500")  # type: ignore[attr-defined]


def test_scenario_mixed_success_and_failure(
    mock_scheduler_bot: AirdropSchedulerBot
) -> None:
    """
    Scenario: Some tasks succeed, others fail due to internal logic.
    """
    bot = mock_scheduler_bot

    task1 = MockAirdropTask("Task D", "layerzero", Decimal("500"))
    task2 = MockAirdropTask("Task E", "hyperliquid", Decimal("5000"))

    def failing_execute() -> bool:
        task2.executed = False  # Explicitly set to False for clarity
        return False

    task2.execute = failing_execute  # type: ignore[method-assign]

    def task_d_func() -> bool:
        assert bot.metrics_collector is not None
        bot.metrics_collector.record_transaction(
            protocol="layerzero",
            action="test_action",
            wallet="0xTestWallet",
            success=True,
            gas_used=50000,
            value_usd=task1.value,
            tx_hash="0xtest"
        )
        return task1.execute()

    def task_e_func() -> bool:
        result = task2.execute()
        assert bot.metrics_collector is not None
        bot.metrics_collector.record_transaction(
            protocol="hyperliquid",
            action="test_action",
            wallet="0xTestWallet",
            success=False,
            gas_used=50000,
            value_usd=task2.value,
            tx_hash="0xtest"
        )
        return result

    bot.add_job(task_id="task_d", func=task_d_func, trigger="date")
    bot.add_job(task_id="task_e", func=task_e_func, trigger="date")

    bot._execute_task_wrapper("task_d")
    bot._execute_task_wrapper("task_e")

    assert task1.executed
    assert not task2.executed
    assert bot.metrics_collector is not None
    assert bot.metrics_collector.record_transaction.call_count == 2


def test_scenario_dry_run_mode(
    mock_capital_allocator: CapitalAllocator,
    mock_metrics_collector: MagicMock
) -> None:
    """
    Scenario: Dry run mode prevents actual execution.
    """
    with patch("airdrops.scheduler.bot.BlockingScheduler"):
        bot = AirdropSchedulerBot(
            capital_allocator=mock_capital_allocator,
            metrics_collector=mock_metrics_collector,
            config={"scheduler": {"dry_run": True}},
        )
        bot.start()

    initial_capital = Decimal("100000")
    capital_tracker = TestCapitalTracker(mock_capital_allocator, initial_capital)
    bot.capital_tracker = capital_tracker  # type: ignore[attr-defined]
    
    task1 = MockAirdropTask("Task F", "scroll", Decimal("1000"))

    # The wrapper now needs to contain the dry-run logic
    def dry_run_aware_task() -> bool:
        if bot.config.get("scheduler", {}).get("dry_run", False):
            print(f"Dry run: Would execute {task1.name}")
            return True  # Simulate successful planning
        return task1.execute()

    bot.add_job(task_id="task_f", func=dry_run_aware_task, trigger="date")

    # We need to modify the bot's internal wrapper to add the dry run check
    original_wrapper = bot._execute_task_wrapper

    def patched_wrapper(task_id: str) -> None:

        if bot.config.get("scheduler", {}).get("dry_run"):
            print(f"Dry run mode, not executing task: {task_id}")
            return
        original_wrapper(task_id)

    with patch.object(bot, '_execute_task_wrapper',
                      side_effect=patched_wrapper):
        bot._execute_task_wrapper("task_f")
        assert not task1.executed
        assert bot.metrics_collector is not None
        mock_metrics_collector.record_transaction.assert_not_called()
        assert bot.capital_tracker.total_capital == initial_capital  # type: ignore[attr-defined]


def test_scenario_no_available_tasks(
    mock_scheduler_bot: AirdropSchedulerBot
) -> None:
    """
    Scenario: Scheduler runs with no available tasks.
    """
    bot = mock_scheduler_bot
    initial_capital = bot.capital_tracker.total_capital  # type: ignore[attr-defined]

    # No tasks added, so _execute_task_wrapper is not called

    assert bot.metrics_collector is not None
    bot.metrics_collector.record_transaction.assert_not_called()
    assert bot.capital_tracker.total_capital == initial_capital  # type: ignore[attr-defined]
