"""
Test scenarios for airdrops, simulating various market conditions and outcomes.
"""

import pytest
from decimal import Decimal
import pendulum

from airdrops.capital_allocation.engine import CapitalAllocator  # type: ignore
from airdrops.monitoring.collector import MetricsCollector  # type: ignore
from airdrops.scheduler.bot import AirdropSchedulerBot  # type: ignore


class MockAirdropTask:
    """A mock airdrop task for testing purposes."""

    def __init__(self, name: str, protocol: str, value: Decimal):
        self.name = name
        self.protocol = protocol
        self.value = value
        self.executed = False

    def execute(self) -> bool:
        """Simulate task execution."""
        self.executed = True
        return True


@pytest.fixture
def mock_capital_allocator():
    """Fixture for a mock CapitalAllocator."""
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
def mock_metrics_collector():
    """Fixture for a mock MetricsCollector."""
    return MetricsCollector()


@pytest.fixture
def mock_scheduler_bot(mock_capital_allocator, mock_metrics_collector):
    """Fixture for a mock AirdropSchedulerBot."""
    return AirdropSchedulerBot(
        capital_allocator=mock_capital_allocator,
        metrics_collector=mock_metrics_collector,
        config={
            "scheduler": {
                "interval_minutes": 60,
                "max_concurrent_tasks": 5,
                "dry_run": False,
            }
        },
    )


def test_scenario_normal_operation(mock_scheduler_bot):
    """
    Scenario: Normal operation with successful task execution.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    # Simulate adding tasks
    task1 = MockAirdropTask("Task A", "scroll", Decimal("1000"))
    task2 = MockAirdropTask("Task B", "zksync", Decimal("2000"))
    bot.add_task(task1)
    bot.add_task(task2)

    # Run a cycle
    bot.run_cycle()

    # Assertions
    assert task1.executed
    assert task2.executed
    assert bot.metrics_collector.get_protocol_metrics("scroll")[
        "successful_transactions"
    ] == 1
    assert bot.metrics_collector.get_protocol_metrics("zksync")[
        "successful_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital < initial_capital  # Capital used


def test_scenario_capital_shortage(mock_scheduler_bot):
    """
    Scenario: Capital shortage prevents task execution.
    """
    bot = mock_scheduler_bot
    bot.capital_allocator.total_capital = Decimal("500")  # Very low capital

    task1 = MockAirdropTask("Task C", "eigenlayer", Decimal("1000"))
    bot.add_task(task1)

    bot.run_cycle()

    # Assertions
    assert not task1.executed  # Task should not be executed due to capital
    assert bot.metrics_collector.get_protocol_metrics("eigenlayer")[
        "failed_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital == Decimal("500")  # Capital unchanged


def test_scenario_mixed_success_and_failure(mock_scheduler_bot):
    """
    Scenario: Some tasks succeed, others fail.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Task D", "layerzero", Decimal("500"))
    task2 = MockAirdropTask("Task E", "hyperliquid", Decimal("5000"))  # Will fail
    bot.add_task(task1)
    bot.add_task(task2)

    # Mock a failure for Task E
    def failing_execute():
        return False

    task2.execute = failing_execute

    bot.run_cycle()

    # Assertions
    assert task1.executed
    assert not task2.executed
    assert bot.metrics_collector.get_protocol_metrics("layerzero")[
        "successful_transactions"
    ] == 1
    assert bot.metrics_collector.get_protocol_metrics("hyperliquid")[
        "failed_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital < initial_capital


def test_scenario_rebalancing_trigger(mock_scheduler_bot):
    """
    Scenario: Portfolio drift triggers rebalancing.
    """
    bot = mock_scheduler_bot
    bot.capital_allocator.total_capital = Decimal("100000")

    # Manually set up a portfolio that needs rebalancing
    bot.capital_allocator.current_portfolio = {
        "scroll": Decimal("0.8"),
        "zksync": Decimal("0.2"),
    }
    bot.capital_allocator.target_portfolio = {
        "scroll": Decimal("0.5"),
        "zksync": Decimal("0.5"),
    }

    # Mock check_rebalance_needed to always return True for this test
    original_check = bot.capital_allocator.check_rebalance_needed
    bot.capital_allocator.check_rebalance_needed = lambda x, y: True

    # Run a cycle (should trigger rebalance)
    bot.run_cycle()

    # Assertions
    # Check if rebalancing logic was applied (portfolio should be closer to target)
    assert abs(bot.capital_allocator.current_portfolio["scroll"] - Decimal("0.5")) < Decimal("0.1")
    assert abs(bot.capital_allocator.current_portfolio["zksync"] - Decimal("0.5")) < Decimal("0.1")

    # Restore original method
    bot.capital_allocator.check_rebalance_needed = original_check


def test_scenario_dry_run_mode(mock_capital_allocator, mock_metrics_collector):
    """
    Scenario: Dry run mode prevents actual execution.
    """
    bot = AirdropSchedulerBot(
        capital_allocator=mock_capital_allocator,
        metrics_collector=mock_metrics_collector,
        config={
            "scheduler": {
                "interval_minutes": 60,
                "max_concurrent_tasks": 5,
                "dry_run": True,  # Enable dry run
            }
        },
    )
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Task F", "scroll", Decimal("1000"))
    bot.add_task(task1)

    bot.run_cycle()

    # Assertions
    assert not task1.executed  # Task should not be executed in dry run
    assert bot.metrics_collector.get_protocol_metrics("scroll")[
        "total_transactions"
    ] == 0  # No transactions recorded
    assert bot.capital_allocator.total_capital == initial_capital  # Capital unchanged


def test_scenario_multiple_cycles(mock_scheduler_bot):
    """
    Scenario: Running multiple cycles over time.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Task G", "zksync", Decimal("500"))
    task2 = MockAirdropTask("Task H", "eigenlayer", Decimal("700"))
    bot.add_task(task1)
    bot.add_task(task2)

    # First cycle
    bot.run_cycle()
    assert task1.executed
    assert task2.executed
    assert bot.metrics_collector.get_protocol_metrics("zksync")[
        "successful_transactions"
    ] == 1
    assert bot.metrics_collector.get_protocol_metrics("eigenlayer")[
        "successful_transactions"
    ] == 1

    # Reset executed status for next cycle (in a real scenario, new tasks would be added)
    task1.executed = False
    task2.executed = False

    # Second cycle with new tasks
    task3 = MockAirdropTask("Task I", "layerzero", Decimal("300"))
    bot.add_task(task3)
    bot.run_cycle()

    assert task3.executed
    assert bot.metrics_collector.get_protocol_metrics("layerzero")[
        "successful_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital < initial_capital - Decimal("1200")


def test_scenario_no_available_tasks(mock_scheduler_bot):
    """
    Scenario: Scheduler runs with no available tasks.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    # No tasks added
    bot.run_cycle()

    # Assertions
    assert bot.metrics_collector.get_total_metrics()["total_transactions"] == 0
    assert bot.capital_allocator.total_capital == initial_capital


def test_scenario_high_gas_fees(mock_scheduler_bot):
    """
    Scenario: High gas fees impact profitability.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Task J", "scroll", Decimal("1000"))
    bot.add_task(task1)

    # Mock record_transaction to simulate high gas
    original_record = bot.metrics_collector.record_transaction

    def high_gas_record(
        protocol: str,
        action: str,
        wallet: str,
        success: bool,
        gas_used: int,
        value_usd: Decimal,
        tx_hash: str,
    ):
        original_record(
            protocol, action, wallet, success, gas_used * 100, value_usd, tx_hash
        )  # Simulate 100x gas

    bot.metrics_collector.record_transaction = high_gas_record

    bot.run_cycle()

    # Assertions
    assert task1.executed
    metrics = bot.metrics_collector.get_protocol_metrics("scroll")
    assert metrics["total_gas_used"] > 21000 * 100  # Check for increased gas

    # Restore original method
    bot.metrics_collector.record_transaction = original_record


def test_scenario_time_based_scheduling(mock_scheduler_bot):
    """
    Scenario: Tasks are scheduled and executed based on time.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    # Mock current time
    mock_now = pendulum.datetime(2023, 1, 1, 10, 0, 0)
    pendulum.set_test_now(mock_now)

    task1 = MockAirdropTask("Task K", "zksync", Decimal("1000"))
    task2 = MockAirdropTask("Task L", "eigenlayer", Decimal("500"))

    # Add tasks with scheduled times
    bot.add_task(task1, schedule_time=mock_now.add(minutes=5))
    bot.add_task(task2, schedule_time=mock_now.add(minutes=15))

    # Run cycle before tasks are due
    bot.run_cycle()
    assert not task1.executed
    assert not task2.executed

    # Advance time past first task
    pendulum.set_test_now(mock_now.add(minutes=10))
    bot.run_cycle()
    assert task1.executed
    assert not task2.executed

    # Advance time past second task
    pendulum.set_test_now(mock_now.add(minutes=20))
    bot.run_cycle()
    assert task1.executed
    assert task2.executed

    pendulum.set_test_now()  # Reset test time


def test_scenario_max_concurrent_tasks(mock_capital_allocator, mock_metrics_collector):
    """
    Scenario: Max concurrent tasks limit is respected.
    """
    bot = AirdropSchedulerBot(
        capital_allocator=mock_capital_allocator,
        metrics_collector=mock_metrics_collector,
        config={
            "scheduler": {
                "interval_minutes": 60,
                "max_concurrent_tasks": 1,  # Only 1 concurrent task allowed
                "dry_run": False,
            }
        },
    )
    initial_capital = Decimal("100000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Task M", "scroll", Decimal("1000"))
    task2 = MockAirdropTask("Task N", "zksync", Decimal("2000"))
    task3 = MockAirdropTask("Task O", "eigenlayer", Decimal("3000"))

    bot.add_task(task1)
    bot.add_task(task2)
    bot.add_task(task3)

    bot.run_cycle()

    # Assertions: Only one task should have been executed
    executed_count = sum([t.executed for t in [task1, task2, task3]])
    assert executed_count == 1

    # Run another cycle, another task should execute
    bot.run_cycle()
    executed_count = sum([t.executed for t in [task1, task2, task3]])
    assert executed_count == 2

    # Run final cycle, last task should execute
    bot.run_cycle()
    executed_count = sum([t.executed for t in [task1, task2, task3]])
    assert executed_count == 3
