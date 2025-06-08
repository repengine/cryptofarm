"""
Integration tests for scheduler with multiple protocols.

This module tests the CentralScheduler's ability to execute tasks across
different protocols, manage dependencies, and handle failures gracefully.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any, List
import pendulum
from web3 import Web3

from airdrops.scheduler.bot import CentralScheduler, TaskStatus, TaskPriority
from airdrops.protocols.scroll import scroll
from airdrops.protocols.zksync import zksync


class TestSchedulerProtocolIntegration:
    """Test suite for scheduler integration with multiple protocols."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Create mock configuration for testing.
        
        Returns:
            Dictionary containing test configuration
        """
        return {
            "protocols": {
                "scroll": {
                    "enabled": True,
                    "daily_activity_range": [2, 4],
                    "operations": {
                        "bridge": {"enabled": True, "weight": 30},
                        "swap": {"enabled": True, "weight": 40},
                        "liquidity": {"enabled": True, "weight": 20},
                        "lending": {"enabled": True, "weight": 10},
                    },
                },
                "zksync": {
                    "enabled": True,
                    "daily_activity_range": [2, 4],
                    "operations": {
                        "bridge": {"enabled": True, "weight": 35},
                        "swap": {"enabled": True, "weight": 35},
                        "lending": {"enabled": True, "weight": 30},
                    },
                },
                "eigenlayer": {
                    "enabled": False,  # Disabled for this test
                },
            },
            "scheduler": {
                "max_retries": 3,
                "retry_delay": 60,
                "task_timeout": 300,
                "max_concurrent_tasks": 5,
            },
            "wallets": [
                "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "0x853d35Cc6634C0532925a3b844Bc9e7195Ed5E47283776",
            ],
            "networks": {
                "ethereum": {
                    "rpc_url": "https://eth-mainnet.example.com",
                },
                "scroll": {
                    "rpc_url": "https://scroll-mainnet.example.com",
                },
                "zksync": {
                    "rpc_url": "https://mainnet.era.zksync.io",
                },
            },
        }

    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_initializes_with_protocols(self, mock_web3_class, mock_config):
        """Test scheduler initializes correctly with multiple protocols.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Verify initialization
        assert scheduler is not None
        assert scheduler.config == mock_config
        assert scheduler.max_retries == 3
        assert scheduler.retry_delay == 60

    @patch("airdrops.protocols.scroll.scroll.bridge_assets")
    @patch("airdrops.protocols.zksync.zksync.bridge_eth")
    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_executes_multiple_protocol_tasks(
        self, mock_web3_class, mock_zksync_bridge, mock_scroll_bridge, mock_config
    ):
        """Test scheduler can execute tasks from different protocols.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_zksync_bridge: Mock zkSync bridge function
            mock_scroll_bridge: Mock Scroll bridge function
            mock_config: Test configuration
        """
        # Setup mocks
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        mock_scroll_bridge.return_value = "0x" + "a" * 64
        mock_zksync_bridge.return_value = (True, "0x" + "b" * 64)
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create tasks for both protocols
        tasks = [
            {
                "id": "task_1",
                "protocol": "scroll",
                "action": "bridge",
                "wallet": mock_config["wallets"][0],
                "priority": TaskPriority.HIGH,
                "params": {
                    "is_deposit": True,
                    "token_symbol": "ETH",
                    "amount": "0.1",
                },
            },
            {
                "id": "task_2",
                "protocol": "zksync",
                "action": "bridge_eth",
                "wallet": mock_config["wallets"][1],
                "priority": TaskPriority.NORMAL,
                "params": {
                    "amount_eth": Decimal("0.05"),
                    "to_l2": True,
                },
            },
        ]
        
        # Execute tasks through scheduler
        results = []
        for task in tasks:
            result = scheduler._execute_task(task)
            results.append(result)
        
        # Verify both tasks executed
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert mock_scroll_bridge.called
        assert mock_zksync_bridge.called

    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_respects_task_dependencies(self, mock_web3_class, mock_config):
        """Test scheduler handles task dependencies correctly.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create tasks with dependencies
        task_graph = {
            "bridge_eth": {
                "id": "bridge_eth",
                "protocol": "scroll",
                "action": "bridge",
                "dependencies": [],
                "status": TaskStatus.PENDING,
            },
            "swap_tokens": {
                "id": "swap_tokens",
                "protocol": "scroll",
                "action": "swap",
                "dependencies": ["bridge_eth"],  # Depends on bridge
                "status": TaskStatus.PENDING,
            },
            "provide_liquidity": {
                "id": "provide_liquidity",
                "protocol": "scroll",
                "action": "liquidity",
                "dependencies": ["swap_tokens"],  # Depends on swap
                "status": TaskStatus.PENDING,
            },
        }
        
        # Verify dependency resolution
        execution_order = scheduler._resolve_dependencies(task_graph)
        
        # Should execute in order: bridge -> swap -> liquidity
        assert execution_order == ["bridge_eth", "swap_tokens", "provide_liquidity"]

    @patch("airdrops.protocols.scroll.scroll.swap_tokens")
    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_handles_task_failure_with_retry(
        self, mock_web3_class, mock_swap, mock_config
    ):
        """Test scheduler retries failed tasks according to configuration.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_swap: Mock swap function
            mock_config: Test configuration
        """
        # Setup mocks
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        # Make swap fail first 2 times, succeed on 3rd
        mock_swap.side_effect = [
            Exception("Network error"),
            Exception("Insufficient liquidity"),
            "0x" + "c" * 64,  # Success on 3rd try
        ]
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create failing task
        task = {
            "id": "failing_task",
            "protocol": "scroll",
            "action": "swap",
            "wallet": mock_config["wallets"][0],
            "retry_count": 0,
            "params": {
                "token_in": "USDC",
                "token_out": "WETH",
                "amount_in": "100",
            },
        }
        
        # Execute with retry logic
        final_result = None
        for attempt in range(scheduler.max_retries):
            result = scheduler._execute_task(task)
            if result["success"]:
                final_result = result
                break
            task["retry_count"] = attempt + 1
        
        # Should eventually succeed
        assert final_result is not None
        assert final_result["success"] is True
        assert mock_swap.call_count == 3

    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_enforces_gas_limits(self, mock_web3_class, mock_config):
        """Test scheduler enforces gas price limits before execution.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock with high gas price
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3.eth.gas_price = Web3.to_wei(200, "gwei")  # Very high
        mock_web3_class.return_value = mock_web3
        
        # Add gas limits to config
        mock_config["risk_management"] = {
            "max_gas_price_gwei": 100,
            "emergency_stop_gas_gwei": 150,
        }
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create task
        task = {
            "protocol": "scroll",
            "action": "bridge",
            "wallet": mock_config["wallets"][0],
            "params": {"amount": "0.1"},
        }
        
        # Check if task should be delayed due to high gas
        should_execute = scheduler._check_gas_conditions()
        
        # Should not execute with gas above emergency stop
        assert should_execute is False

    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_load_balances_across_wallets(self, mock_web3_class, mock_config):
        """Test scheduler distributes tasks across multiple wallets.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_config: Test configuration
        """
        # Setup mock
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create multiple tasks
        tasks = []
        for i in range(10):
            tasks.append({
                "id": f"task_{i}",
                "protocol": "scroll" if i % 2 == 0 else "zksync",
                "action": "swap",
                "wallet": None,  # Let scheduler assign
            })
        
        # Assign wallets using round-robin
        wallet_assignments = {}
        for i, task in enumerate(tasks):
            wallet = scheduler._assign_wallet_for_task(
                task, mock_config["wallets"]
            )
            task["wallet"] = wallet
            wallet_assignments[wallet] = wallet_assignments.get(wallet, 0) + 1
        
        # Verify balanced distribution
        assert len(wallet_assignments) == 2
        assert abs(wallet_assignments[mock_config["wallets"][0]] - 
                  wallet_assignments[mock_config["wallets"][1]]) <= 1

    def test_scheduler_generates_random_delays(self, mock_config):
        """Test scheduler generates appropriate random delays between tasks.
        
        Args:
            mock_config: Test configuration
        """
        scheduler = CentralScheduler(mock_config)
        
        # Generate multiple delays
        delays = []
        for _ in range(100):
            delay = scheduler._generate_random_delay(
                min_seconds=60,
                max_seconds=300
            )
            delays.append(delay)
        
        # Verify delays are within bounds
        assert all(60 <= d <= 300 for d in delays)
        
        # Verify randomness (not all the same)
        assert len(set(delays)) > 10

    @patch("airdrops.scheduler.bot.BlockingScheduler")
    @patch("airdrops.scheduler.bot.Web3")
    def test_scheduler_schedules_daily_activities(
        self, mock_web3_class, mock_scheduler_class, mock_config
    ):
        """Test scheduler creates daily activity schedules for each protocol.
        
        Args:
            mock_web3_class: Mock Web3 class
            mock_scheduler_class: Mock APScheduler class
            mock_config: Test configuration
        """
        # Setup mocks
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        mock_scheduler_instance = Mock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Generate daily schedule
        daily_tasks = scheduler._generate_daily_schedule()
        
        # Verify tasks generated for enabled protocols
        protocol_tasks = {}
        for task in daily_tasks:
            protocol = task["protocol"]
            protocol_tasks[protocol] = protocol_tasks.get(protocol, 0) + 1
        
        # Should have tasks for both enabled protocols
        assert "scroll" in protocol_tasks
        assert "zksync" in protocol_tasks
        assert "eigenlayer" not in protocol_tasks  # Disabled
        
        # Verify task counts are within configured ranges
        assert 2 <= protocol_tasks["scroll"] <= 4 * len(mock_config["wallets"])
        assert 2 <= protocol_tasks["zksync"] <= 4 * len(mock_config["wallets"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])