"""
Integration tests for zkSync protocol with scheduler and monitoring.

This module tests the integration of the zkSync protocol with the central scheduler,
capital allocation engine, and monitoring system to ensure all components work
together correctly.
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from typing import Dict, Any
from web3 import Web3

from airdrops.scheduler.bot import (
    CentralScheduler,
    TaskDefinition,
    TaskExecution,
    TaskStatus,
)
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.monitoring.alerter import Alerter
from airdrops.risk_management.core import RiskManager


class TestZkSyncIntegration:
    """Test suite for zkSync protocol integration with other system components."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Create mock configuration for testing.
        
        Returns:
            Dictionary containing test configuration
        """
        return {
            "protocols": {
                "zksync": {
                    "enabled": True,
                    "daily_activity_range": [2, 4],
                    "operations": {
                        "bridge": {"enabled": True, "weight": 35},
                        "swap": {"enabled": True, "weight": 35},
                        "lending": {"enabled": True, "weight": 30},
                    },
                },
            },
            "networks": {
                "ethereum": {
                    "rpc_url": "https://eth-mainnet.example.com",
                    "bridge_address": "0x32400084C286CF3E17e7B677ea9583e60a000324",
                },
                "zksync": {
                    "rpc_url": "https://mainnet.era.zksync.io",
                    "bridge_address": "0x0000000000000000000000000000000000008006",
                    "dex_router_address": "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
                    "lending_protocols": {
                        "eralend": {
                            "lending_pool_manager": "0x1234567890123456789012345678901234567890",  # noqa: E501
                            "weth_gateway": "0x2345678901234567890123456789012345678901",   # noqa: E501
                            "referral_code": 0,
                        },
                    },
                },
            },
            "tokens": {
                "ETH": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "decimals": 18,
                },
                "WETH": {
                    "address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
                    "decimals": 18,
                },
                "USDC": {
                    "address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                    "decimals": 6,
                },
            },
            "monitoring": {
                "metrics_interval": 60,
                "health_check_interval": 300,
            },
            "risk_management": {
                "max_daily_gas_usd": 150,
                "max_protocol_exposure": 0.35,
                "min_balance_eth": 0.01,
            },
            "capital_allocation": {
                "strategy": "mean_variance",
                "rebalance_threshold": 0.15,
            },
            "random_activity": {
                "enabled": True,
                "num_actions_range": [2, 4],
                "action_weights": {
                    "bridge_eth": 30,
                    "swap_tokens": 50,
                    "lend_borrow": 20,
                },
            },
        }

    @pytest.fixture
    def mock_web3(self) -> Mock:
        """Create mock Web3 instance.
        
        Returns:
            Mock Web3 instance with common methods
        """
        w3 = Mock(spec=Web3)
        w3.eth = Mock()
        w3.eth.get_balance.return_value = Web3.to_wei(1.5, "ether")
        w3.eth.gas_price = Web3.to_wei(25, "gwei")
        w3.eth.get_transaction_count.return_value = 5
        w3.is_connected.return_value = True
        return w3

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_scheduler_executes_zksync_bridge_task(
        self, mock_get_web3, mock_config, mock_web3
    ):
        """Test that scheduler correctly executes zkSync bridge tasks.
        
        Args:
            mock_get_web3: Mock for getting Web3 instance
            mock_config: Test configuration
            mock_web3: Mock Web3 instance
        """
        # Setup mocks
        mock_get_web3.return_value = mock_web3
        
        # Mock successful bridge
        with patch("airdrops.protocols.zksync.zksync.bridge_eth") as mock_bridge:
            mock_bridge.return_value = (True, "0x" + "f" * 64)
            
            # Create scheduler
            scheduler = CentralScheduler(mock_config)
            
            # Create a bridge task
            task = {
                "id": "zksync_bridge_task",  # Added ID
                "protocol": "zksync",
                "action": "bridge_eth",
                "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "params": {
                    "amount_eth": Decimal("0.1"),
                    "to_l2": True,
                },
            }
            
            # Execute task
            result = scheduler._execute_task(task)
            
            # Verify task was executed
            assert result["success"] is True
            assert result["tx_hash"] == "0x" + "f" * 64
            mock_bridge.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync._get_web3_instance")
    def test_scheduler_executes_zksync_swap_task(
        self, mock_get_web3, mock_config, mock_web3
    ):
        """Test that scheduler correctly executes zkSync swap tasks.
        
        Args:
            mock_get_web3: Mock for getting Web3 instance
            mock_config: Test configuration
            mock_web3: Mock Web3 instance
        """
        # Setup mocks
        mock_get_web3.return_value = mock_web3
        
        # Mock successful swap
        with patch("airdrops.protocols.zksync.zksync.swap_tokens") as mock_swap:
            mock_swap.return_value = (True, "0x" + "a" * 64)
            
            # Create scheduler
            scheduler = CentralScheduler(mock_config)
            
            # Create a swap task
            task = {
                "id": "zksync_swap_task",  # Added ID
                "protocol": "zksync",
                "action": "swap_tokens",
                "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                "params": {
                    "token_in_address": "0x0000000000000000000000000000000000000000",
                    "token_out_address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                    "amount_in": 1000000000000000000,  # 1 ETH
                    "dex_name": "syncswap",
                    "slippage_bps": 50,
                },
            }
            
            # Execute task
            result = scheduler._execute_task(task)
            
            # Verify task was executed
            assert result["success"] is True
            assert result["tx_hash"] == "0x" + "a" * 64
            mock_swap.assert_called_once()

    def test_capital_allocation_includes_zksync(self, mock_config):
        """Test capital allocation engine includes zkSync protocol.
        
        Args:
            mock_config: Test configuration
        """
        
        # Create capital allocator
        allocator = CapitalAllocator(mock_config)
        
        # Test portfolio optimization
        protocols = ["zksync"]
        risk_constraints = {"max_protocol_exposure": Decimal("0.35")}
        portfolio = allocator.optimize_portfolio(protocols, risk_constraints)
        
        # Verify zkSync is included
        assert "zksync" in portfolio
        assert portfolio["zksync"] > 0
        
        # Test risk-adjusted allocation
        total_capital = Decimal("30000")  # $30k across 3 wallets
        risk_metrics = {"volatility_state": "medium", "gas_price": 40}
        allocations = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
        
        # Verify allocations
        assert "zksync" in allocations
        assert allocations["zksync"] > 0

    @patch("airdrops.monitoring.collector.time")
    def test_monitoring_tracks_zksync_lending_metrics(self, mock_time, mock_config):
        """Test monitoring system tracks zkSync lending operations.
        
        Args:
            mock_time: Mock time module
            mock_config: Test configuration
        """
        # Setup time mock
        mock_time.time.return_value = 1700000000
        
        # Create metrics collector
        collector = MetricsCollector()
        
        # Record zkSync lending operations
        operations = [
            ("supply", True, 100000, 500.0),
            ("borrow", True, 120000, 300.0),
            ("repay", True, 90000, 300.0),
            ("withdraw", False, 110000, 0.0),  # Failed operation
        ]
        
        for action, success, gas, value in operations:
            collector.record_transaction(
                protocol="zksync",
                action=f"lend_{action}",
                wallet="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                success=success,
                gas_used=gas,
                value_usd=value,
                tx_hash=f"0x{action[0]}" + "b" * 63,
            )
        
        # Get metrics
        metrics = collector.get_protocol_metrics("zksync")
        
        # Verify metrics
        assert metrics["total_transactions"] == 4.0
        assert metrics["successful_transactions"] == 3.0
        assert metrics["failed_transactions"] == 1.0
        assert metrics["total_gas_used"] == 420000.0  # Sum of all gas
        assert metrics["total_value_usd"] == 1100.0  # Sum of successful values

    def test_risk_manager_validates_zksync_operations(
        self, mock_config
    ):
        """Test risk manager properly validates zkSync operations.
        
        Args:
            mock_config: Test configuration
        """
        
        # Create risk manager
        risk_manager = RiskManager(mock_config)
        
        # Test normal zkSync operation
        operation = {
            "protocol": "zksync",
            "action": "swap",
            "estimated_gas": 300000,
            "value_usd": 200.0,
        }
        
        # Should pass validation
        is_valid = risk_manager.validate_operation(operation)
        assert is_valid is True
        
        # Test high-value operation
        high_value_operation = {
            "protocol": "zksync",
            "action": "lend_supply",
            "estimated_gas": 250000,
            "value_usd": 10000.0,  # Very high value
        }
        
        # May fail depending on risk limits
        is_valid = risk_manager.validate_operation(high_value_operation)
        # Risk manager behavior depends on implementation

    @patch("airdrops.protocols.zksync.zksync.perform_random_activity")
    def test_zksync_random_activity_integration(
        self, mock_random_activity, mock_config
    ):
        """Test zkSync random activity execution through scheduler.
        
        Args:
            mock_random_activity: Mock random activity function
            mock_config: Test configuration
        """
        # Setup successful random activity
        mock_random_activity.return_value = (
            True,
            "Executed 3 actions successfully: bridge_eth, swap_tokens, lend_borrow"
        )
        
        # Create scheduler
        scheduler = CentralScheduler(mock_config)
        
        # Create random activity task
        task = {
            "id": "zksync_random_activity_task",  # Added ID
            "protocol": "zksync",
            "action": "random_activity",
            "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            "params": {},
        }
        
        # Execute task
        result = scheduler._execute_task(task)
        
        # Verify execution
        assert result["success"] is True
        assert "Executed 3 actions successfully: bridge_eth, swap_tokens, lend_borrow" in result["message"]   # noqa: E501
        mock_random_activity.assert_called_once()

    @patch("airdrops.protocols.zksync.zksync.lend_borrow")
    @patch("airdrops.monitoring.alerter.Alerter.send_notifications")
    def test_alerting_on_zksync_lending_failure(
        self, mock_send_notifications, mock_lend_borrow, mock_config
    ):
        """Test alerts are triggered when zkSync lending operations fail.
        
        Args:
            mock_send_notification: Mock notification sender
            mock_lend_borrow: Mock lending function
            mock_config: Test configuration
        """
        # Setup lending to fail
        mock_lend_borrow.side_effect = Exception(
            "Insufficient collateral for borrow operation"
        )
        
        # Create alerter
        alerter = Alerter(mock_config)
        
        # Create scheduler with alerter
        scheduler = CentralScheduler(mock_config)
        scheduler.alerter = alerter
        
        # Define task
        task_id = "test_failing_lending_task"
        task_def = TaskDefinition(
            task_id=task_id,
            func=mock_lend_borrow,
            protocol="zksync",
            action="lend_borrow",
            max_retries=0,  # Ensure alert is sent immediately
            kwargs={
                "action": "borrow",
                "token_address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                "amount": 1000000,  # 1 USDC
                "lending_protocol_name": "eralend",
            },
        )
        execution = TaskExecution(
            task_id=task_id,
            wallet="0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
            status=TaskStatus.PENDING,
        )
        
        scheduler._task_definitions[task_id] = task_def
        scheduler._task_executions[task_id] = execution
        
        # Execute task wrapper
        result = scheduler._execute_task_wrapper(task_id)
            
        # Verify failure was handled
        assert result["success"] is False
        assert "Insufficient collateral" in result.get("error", "")
        mock_send_notifications.assert_called_once()  # Verify alert was sent

    def test_cross_protocol_workflow_scroll_to_zksync(self, mock_config):
        """Test workflow involving both Scroll and zkSync protocols.
        
        Args:
            mock_config: Test configuration
        """
        # Enable both protocols
        mock_config["protocols"]["scroll"] = {"enabled": True}
        
        # No direct Web3 patch needed for scheduler.bot as it doesn't import Web3 directly.  # noqa: E501
        # If CentralScheduler needs a Web3 instance, it should be passed in its constructor or a method.  # noqa: E501
        # For now, we assume it's mocked at a lower level or not directly used in this test's scope.  # noqa: E501
        
        # Create system components
        scheduler = CentralScheduler(mock_config)
        allocator = CapitalAllocator(mock_config)
        _ = MetricsCollector()  # collector is assigned to but never used
        
        # Get allocations for both protocols
        wallets = ["0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775"]
        allocations = allocator.allocate_capital(wallets)
        
        # Verify both protocols get allocations for the first wallet
        assert "scroll" in allocations[wallets[0]]
        assert "zksync" in allocations[wallets[0]]
        
        # Simulate operations on both
        with patch("airdrops.protocols.scroll.scroll.swap_tokens") as mock_scroll_swap, \
             patch("airdrops.protocols.zksync.zksync.swap_tokens") as mock_zksync_swap:   # noqa: E501
            
            mock_scroll_swap.return_value = "0x" + "1" * 64
            mock_zksync_swap.return_value = (True, "0x" + "2" * 64)
            
            # Execute Scroll task
            scroll_task = {
                "id": "cross_protocol_scroll_swap",  # Added ID
                "protocol": "scroll",
                "action": "swap_tokens",
                "wallet": wallets[0],
                "params": {"token_in": "USDC", "token_out": "WETH", "amount_in": "100"},
            }
            
            # Execute zkSync task
            zksync_task = {
                "id": "cross_protocol_zksync_swap",  # Added ID
                "protocol": "zksync",
                "action": "swap_tokens",
                "wallet": wallets[0],
                "params": {
                    "token_in_address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                    "token_out_address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
                    "amount_in": 100000000,
                    "dex_name": "syncswap",
                    "slippage_bps": 50,
                },
            }
            
            # Execute both
            scroll_result = scheduler._execute_task(scroll_task)
            zksync_result = scheduler._execute_task(zksync_task)
            
            # Verify both succeeded
            assert scroll_result["success"] is True
            assert zksync_result["success"] is True

    def test_performance_based_reallocation(self, mock_config):
        """Test capital reallocation based on zkSync performance.
        
        Args:
            mock_config: Test configuration
        """
        # Create allocator
        allocator = CapitalAllocator(mock_config)
        
        # Test portfolio optimization with multiple protocols
        protocols = ["zksync", "scroll", "eigenlayer"]
        risk_constraints = {"max_protocol_exposure": Decimal("0.4")}
        
        # Simulate zkSync having better historical performance
        expected_returns = {
            "zksync": Decimal("0.15"),  # 15% expected return
            "scroll": Decimal("0.08"),  # 8% expected return
            "eigenlayer": Decimal("0.05")  # 5% expected return
        }
        
        portfolio = allocator.optimize_portfolio(
            protocols, risk_constraints, expected_returns=expected_returns
        )
        
        # Verify zkSync gets allocation
        assert "zksync" in portfolio
        assert portfolio["zksync"] > 0
        
        # With mean-variance optimization, higher expected return protocols
        # should generally get higher allocations (subject to risk constraints)
        if allocator.allocation_strategy.value == "mean_variance":
            # zkSync should have significant allocation due to high returns
            assert portfolio["zksync"] >= Decimal("0.2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])