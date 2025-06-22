"""
Integration tests for the scheduler interacting with various protocols.
"""

import pytest
from decimal import Decimal
from typing import Generator, Callable, Any
from unittest.mock import MagicMock, patch

from airdrops.scheduler.bot import AirdropSchedulerBot
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.protocols.eigenlayer import EigenLayerProtocol
from airdrops.protocols.layerzero import LayerZeroProtocol
from airdrops.protocols.hyperliquid import HyperliquidProtocol
from tests.shared.capital_tracker import TestCapitalTracker


class MockAirdropTask:
    """A mock airdrop task for testing purposes."""

    def __init__(self, name: str, protocol_name: str, value: Decimal, protocol_functions: MagicMock) -> None:
        self.name = name
        self.protocol_name = protocol_name
        self.value = value
        self.executed = False
        self.protocol_functions = protocol_functions

    def execute(self) -> bool:
        """Simulate task execution by calling appropriate protocol function."""
        try:
            if self.protocol_name == "scroll":
                success = self.protocol_functions.bridge_assets(self.value) is not None
            elif self.protocol_name == "zksync":
                success = self.protocol_functions.bridge_assets(self.value) is not None
            elif self.protocol_name == "eigenlayer":
                success = self.protocol_functions.perform_airdrop(self.value)
            elif self.protocol_name == "layerzero":
                success = self.protocol_functions.perform_airdrop(self.value)
            elif self.protocol_name == "hyperliquid":
                success = self.protocol_functions.perform_airdrop(self.value)
            else:
                success = False

            self.executed = success
            return success
        except Exception:
            self.executed = False
            return False


@pytest.fixture
def mock_capital_allocator() -> CapitalAllocator:
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
def mock_capital_tracker(mock_capital_allocator: CapitalAllocator) -> TestCapitalTracker:
    """Fixture for a TestCapitalTracker with initial capital."""
    return TestCapitalTracker(mock_capital_allocator, Decimal("10000"))


@pytest.fixture
def mock_metrics_collector() -> MagicMock:
    """Fixture for a mock MetricsCollector."""
    return MagicMock(spec=MetricsCollector)


@pytest.fixture
def mock_scheduler_bot(mock_capital_tracker: TestCapitalTracker, mock_metrics_collector: MagicMock) -> Generator[AirdropSchedulerBot, None, None]:
    """Fixture for a mock AirdropSchedulerBot."""
    with patch("airdrops.scheduler.bot.BlockingScheduler"):
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
        # Attach the capital tracker to the bot for testing
        bot.capital_tracker = mock_capital_tracker  # type: ignore[attr-defined]
        yield bot


@pytest.fixture
def mock_scroll_protocol_functions() -> MagicMock:
    """Mock Scroll protocol functions."""
    mock_funcs = MagicMock()
    mock_funcs.bridge_assets.return_value = "0xmock_tx_hash_scroll_bridge"
    return mock_funcs


@pytest.fixture
def mock_zksync_protocol_functions() -> MagicMock:
    """Mock ZkSync protocol functions."""
    mock_funcs = MagicMock()
    mock_funcs.bridge_assets.return_value = "0xmock_tx_hash_zksync_bridge"
    return mock_funcs


@pytest.fixture
def mock_eigenlayer_protocol() -> MagicMock:
    """Mock EigenLayerProtocol instance."""
    mock_protocol = MagicMock(spec=EigenLayerProtocol)
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


@pytest.fixture
def mock_layerzero_protocol() -> MagicMock:
    """Mock LayerZeroProtocol instance."""
    mock_protocol = MagicMock(spec=LayerZeroProtocol)
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


@pytest.fixture
def mock_hyperliquid_protocol() -> MagicMock:
    """Mock HyperliquidProtocol instance."""
    mock_protocol = MagicMock(spec=HyperliquidProtocol)
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


def test_scheduler_with_scroll_protocol(
    mock_scheduler_bot: Any, mock_scroll_protocol_functions: Any
) -> None:
    """
    Integration test: Scheduler executes a task for Scroll protocol.
    """
    bot = mock_scheduler_bot
    initial_capital = bot.capital_tracker.total_capital  

    task = MockAirdropTask("Scroll Airdrop", "scroll", Decimal("500"), mock_scroll_protocol_functions)
 
    def task_func() -> bool:
        success = task.execute()
        if success:
            bot.capital_tracker.total_capital -= task.value  
        bot.metrics_collector.record_transaction(
            protocol=task.protocol_name,
            action="bridge",
            wallet="0xTestWallet",
            success=success,
            gas_used=50000,
            value_usd=task.value,
            tx_hash="0xmock"
        )
        return success

    bot.add_job(task_id="scroll_airdrop", func=task_func, trigger="date")
    bot._execute_task_wrapper("scroll_airdrop")

    assert task.executed
    mock_scroll_protocol_functions.bridge_assets.assert_called_once_with(task.value)
    bot.metrics_collector.record_transaction.assert_called_once_with(
        protocol="scroll",
        action="bridge",
        wallet="0xTestWallet",
        success=True,
        gas_used=50000,
        value_usd=task.value,
        tx_hash="0xmock"
    )
    assert isinstance(bot.capital_tracker.total_capital, Decimal)  
    assert bot.capital_tracker.total_capital == initial_capital - Decimal("500")  


def test_scheduler_with_zksync_protocol_failure(
    mock_scheduler_bot: Any, mock_zksync_protocol_functions: Any
) -> None:
    """
    Integration test: Scheduler handles a failed task for ZkSync protocol.
    """
    bot = mock_scheduler_bot
    initial_capital = bot.capital_tracker.total_capital  

    mock_zksync_protocol_functions.bridge_assets.return_value = None

    task = MockAirdropTask("ZkSync Airdrop", "zksync", Decimal("750"), mock_zksync_protocol_functions)
 
    def task_func() -> bool:
        success = task.execute()
        bot.metrics_collector.record_transaction(
            protocol=task.protocol_name,
            action="bridge",
            wallet="0xTestWallet",
            success=success,
            gas_used=50000,
            value_usd=task.value,
            tx_hash="0xmock_fail"
        )
        return success

    bot.add_job(task_id="zksync_airdrop", func=task_func, trigger="date")
    bot._execute_task_wrapper("zksync_airdrop")

    assert not task.executed
    mock_zksync_protocol_functions.bridge_assets.assert_called_once_with(task.value)
    bot.metrics_collector.record_transaction.assert_called_once_with(
        protocol="zksync",
        action="bridge",
        wallet="0xTestWallet",
        success=False,
        gas_used=50000,
        value_usd=task.value,
        tx_hash="0xmock_fail"
    )
    assert bot.capital_tracker.total_capital == initial_capital


def test_scheduler_multiple_protocols(
    mock_scheduler_bot: Any,
    mock_scroll_protocol_functions: Any,
    mock_eigenlayer_protocol: Any,
    mock_layerzero_protocol: Any,
) -> None:
    """
    Integration test: Scheduler handles tasks for multiple protocols.
    """
    bot = mock_scheduler_bot
    # Reset capital tracker to a higher amount for this test
    bot.capital_tracker.total_capital = Decimal("20000")  
    initial_capital = bot.capital_tracker.total_capital  

    task1 = MockAirdropTask("Scroll Task", "scroll", Decimal("1000"), mock_scroll_protocol_functions)
    task2 = MockAirdropTask("EigenLayer Task", "eigenlayer", Decimal("2000"), mock_eigenlayer_protocol)
    task3 = MockAirdropTask("LayerZero Task", "layerzero", Decimal("500"), mock_layerzero_protocol)
 
    def make_task_func(task: MockAirdropTask) -> Callable[[], bool]:
        def task_func() -> bool:
            success = task.execute()
            if success:
                bot.capital_tracker.total_capital -= task.value  
            bot.metrics_collector.record_transaction(
                protocol=task.protocol_name,
                action="airdrop",
                wallet="0xTestWallet",
                success=success,
                gas_used=50000,
                value_usd=task.value,
                tx_hash=f"0xmock_{task.protocol_name}"
            )
            return success
        return task_func

    bot.add_job(task_id="scroll_task", func=make_task_func(task1), trigger="date")
    bot.add_job(task_id="eigenlayer_task", func=make_task_func(task2), trigger="date")
    bot.add_job(task_id="layerzero_task", func=make_task_func(task3), trigger="date")

    bot._execute_task_wrapper("scroll_task")
    bot._execute_task_wrapper("eigenlayer_task")
    bot._execute_task_wrapper("layerzero_task")

    assert task1.executed
    assert task2.executed
    assert task3.executed

    mock_scroll_protocol_functions.bridge_assets.assert_called_once_with(task1.value)
    mock_eigenlayer_protocol.perform_airdrop.assert_called_once_with(task2.value)
    mock_layerzero_protocol.perform_airdrop.assert_called_once_with(task3.value)

    assert bot.metrics_collector.record_transaction.call_count == 3
    expected_remaining_capital = initial_capital - task1.value - task2.value - task3.value
    assert bot.capital_tracker.total_capital == expected_remaining_capital  


def test_scheduler_dry_run_with_protocols(
    mock_capital_allocator: CapitalAllocator, mock_hyperliquid_protocol: MagicMock
) -> None:
    """
    Integration test: Scheduler in dry run mode does not execute protocol tasks.
    """
    # Use a fresh MagicMock for this specific test
    mock_metrics_collector = MagicMock(spec=MetricsCollector)

    with patch("airdrops.scheduler.bot.BlockingScheduler"):
        bot = AirdropSchedulerBot(
            capital_allocator=mock_capital_allocator,
            metrics_collector=mock_metrics_collector,
            config={"scheduler": {"dry_run": True}},
        )
        bot.start()

    initial_capital = Decimal("10000")
    capital_tracker = TestCapitalTracker(mock_capital_allocator, initial_capital)
    bot.capital_tracker = capital_tracker  # type: ignore[attr-defined]

    task = MockAirdropTask("Hyperliquid Task", "hyperliquid", Decimal("1500"), mock_hyperliquid_protocol)

    def task_func() -> None:
        if bot.config.get("scheduler", {}).get("dry_run"):
            return

        success = task.execute()
        if success:
            capital_tracker.total_capital -= task.value
        mock_metrics_collector.record_transaction(
            protocol=task.protocol_name,
            action="airdrop",
            wallet="0xTestWallet",
            success=success,
            gas_used=50000,
            value_usd=task.value,
            tx_hash="0xmock_hyper"
        )

    bot.add_job(task_id="hyperliquid_task", func=task_func, trigger="date")
    bot._execute_task_wrapper("hyperliquid_task")

    assert not task.executed
    mock_hyperliquid_protocol.perform_airdrop.assert_not_called()
    mock_metrics_collector.record_transaction.assert_not_called()
    assert bot.capital_tracker.total_capital == initial_capital  # type: ignore[attr-defined]
