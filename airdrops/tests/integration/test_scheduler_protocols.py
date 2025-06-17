"""
Integration tests for the scheduler interacting with various protocols.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

from airdrops.scheduler.bot import AirdropSchedulerBot
from airdrops.capital_allocation.engine import CapitalAllocator  # type: ignore
from airdrops.monitoring.collector import MetricsCollector  # type: ignore
from airdrops.protocols.scroll import swap_tokens as scroll_swap_tokens, bridge_assets as scroll_bridge_assets  # type: ignore
from airdrops.protocols.zksync import swap_tokens as zksync_swap_tokens, bridge_assets as zksync_bridge_assets  # type: ignore
from airdrops.protocols.eigenlayer import EigenLayerProtocol  # type: ignore
from airdrops.protocols.layerzero import LayerZeroProtocol  # type: ignore
from airdrops.protocols.hyperliquid import HyperliquidProtocol  # type: ignore


class MockAirdropTask:
    """A mock airdrop task for testing purposes."""

    def __init__(self, name: str, protocol_name: str, value: Decimal, protocol_functions: Any = None):
        self.name = name
        self.protocol_name = protocol_name
        self.value = value
        self.executed = False
        self.protocol_functions = protocol_functions # For direct function calls

    def execute(self) -> bool:
        """Simulate task execution by calling appropriate protocol function."""
        try:
            if self.protocol_name == "scroll":
                # Assuming a simple mock for now, in real scenario,
                # this would involve more complex parameter passing
                success = self.protocol_functions.bridge_assets(None, None, None, self.value, None, None, None) is not None
            elif self.protocol_name == "zksync":
                success = self.protocol_functions.bridge_assets(None, None, None, self.value, None, None, None) is not None
            elif self.protocol_name == "eigenlayer":
                success = self.protocol_functions.perform_airdrop(self.value)
            elif self.protocol_name == "layerzero":
                success = self.protocol_functions.perform_airdrop(self.value)
            elif self.protocol_name == "hyperliquid":
                success = self.protocol_functions.perform_airdrop(self.value)
            else:
                success = False # Unknown protocol

            self.executed = success
            return success
        except Exception:
            self.executed = False
            return False


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


@pytest.fixture
def mock_scroll_protocol_functions():
    """Mock Scroll protocol functions."""
    mock_bridge = MagicMock(spec=scroll_bridge_assets)
    mock_swap = MagicMock(spec=scroll_swap_tokens)
    mock_bridge.return_value = "0xmock_tx_hash_scroll_bridge"
    mock_swap.return_value = "0xmock_tx_hash_scroll_swap"
    return MagicMock(bridge_assets=mock_bridge, swap_tokens=mock_swap)


@pytest.fixture
def mock_zksync_protocol_functions():
    """Mock ZkSync protocol functions."""
    mock_bridge = MagicMock(spec=zksync_bridge_assets)
    mock_swap = MagicMock(spec=zksync_swap_tokens)
    mock_bridge.return_value = "0xmock_tx_hash_zksync_bridge"
    mock_swap.return_value = "0xmock_tx_hash_zksync_swap"
    return MagicMock(bridge_assets=mock_bridge, swap_tokens=mock_swap)


@pytest.fixture
def mock_eigenlayer_protocol():
    """Mock EigenLayerProtocol instance."""
    mock_protocol = MagicMock(spec=EigenLayerProtocol)
    mock_protocol.name = "eigenlayer"
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


@pytest.fixture
def mock_layerzero_protocol():
    """Mock LayerZeroProtocol instance."""
    mock_protocol = MagicMock(spec=LayerZeroProtocol)
    mock_protocol.name = "layerzero"
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


@pytest.fixture
def mock_hyperliquid_protocol():
    """Mock HyperliquidProtocol instance."""
    mock_protocol = MagicMock(spec=HyperliquidProtocol)
    mock_protocol.name = "hyperliquid"
    mock_protocol.perform_airdrop.return_value = True
    return mock_protocol


def test_scheduler_with_scroll_protocol(
    mock_scheduler_bot, mock_scroll_protocol_functions
):
    """
    Integration test: Scheduler executes a task for Scroll protocol.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("10000")
    bot.capital_allocator.total_capital = initial_capital

    task = MockAirdropTask("Scroll Airdrop", "scroll", Decimal("500"), mock_scroll_protocol_functions)
    bot.add_task(task)

    bot.run_cycle()

    assert task.executed
    mock_scroll_protocol_functions.bridge_assets.assert_called_once() # Assuming bridge_assets is called
    assert bot.metrics_collector.get_protocol_metrics("scroll")[
        "successful_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital == initial_capital - Decimal("500")


def test_scheduler_with_zksync_protocol_failure(
    mock_scheduler_bot, mock_zksync_protocol_functions
):
    """
    Integration test: Scheduler handles a failed task for ZkSync protocol.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("10000")
    bot.capital_allocator.total_capital = initial_capital

    # Mock ZkSync protocol to fail
    mock_zksync_protocol_functions.bridge_assets.return_value = None # Simulate failure

    task = MockAirdropTask("ZkSync Airdrop", "zksync", Decimal("750"), mock_zksync_protocol_functions)
    bot.add_task(task)

    bot.run_cycle()

    assert not task.executed
    mock_zksync_protocol_functions.bridge_assets.assert_called_once() # Assuming bridge_assets is called
    assert bot.metrics_collector.get_protocol_metrics("zksync")[
        "failed_transactions"
    ] == 1
    assert bot.capital_allocator.total_capital == initial_capital  # Capital not used


def test_scheduler_multiple_protocols(
    mock_scheduler_bot,
    mock_scroll_protocol_functions,
    mock_eigenlayer_protocol,
    mock_layerzero_protocol,
):
    """
    Integration test: Scheduler handles tasks for multiple protocols.
    """
    bot = mock_scheduler_bot
    initial_capital = Decimal("20000")
    bot.capital_allocator.total_capital = initial_capital

    task1 = MockAirdropTask("Scroll Task", "scroll", Decimal("1000"), mock_scroll_protocol_functions)
    task2 = MockAirdropTask("EigenLayer Task", "eigenlayer", Decimal("2000"), mock_eigenlayer_protocol)
    task3 = MockAirdropTask("LayerZero Task", "layerzero", Decimal("500"), mock_layerzero_protocol)

    bot.add_task(task1)
    bot.add_task(task2)
    bot.add_task(task3)

    bot.run_cycle()

    assert task1.executed
    assert task2.executed
    assert task3.executed

    mock_scroll_protocol_functions.bridge_assets.assert_called_once()
    mock_eigenlayer_protocol.perform_airdrop.assert_called_once_with(Decimal("2000"))
    mock_layerzero_protocol.perform_airdrop.assert_called_once_with(Decimal("500"))

    assert bot.metrics_collector.get_protocol_metrics("scroll")[
        "successful_transactions"
    ] == 1
    assert bot.metrics_collector.get_protocol_metrics("eigenlayer")[
        "successful_transactions"
    ] == 1
    assert bot.metrics_collector.get_protocol_metrics("layerzero")[
        "successful_transactions"
    ] == 1

    expected_remaining_capital = initial_capital - Decimal("1000") - Decimal("2000") - Decimal("500")
    assert bot.capital_allocator.total_capital == expected_remaining_capital


def test_scheduler_dry_run_with_protocols(
    mock_capital_allocator, mock_metrics_collector, mock_hyperliquid_protocol
):
    """
    Integration test: Scheduler in dry run mode does not execute protocol tasks.
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
    initial_capital = Decimal("10000")
    bot.capital_allocator.total_capital = initial_capital

    task = MockAirdropTask("Hyperliquid Task", "hyperliquid", Decimal("1500"), mock_hyperliquid_protocol)
    bot.add_task(task)

    bot.run_cycle()

    assert not task.executed  # Task should not be executed in dry run
    mock_hyperliquid_protocol.perform_airdrop.assert_not_called()
    assert bot.metrics_collector.get_protocol_metrics("hyperliquid")[
        "total_transactions"
    ] == 0  # No transactions recorded
    assert bot.capital_allocator.total_capital == initial_capital  # Capital unchanged
