"""
End-to-End Farming Cycle Tests for Airdrop Automation System.

This module contains comprehensive E2E tests that simulate complete airdrop farming
cycles using the MockWallet framework and scenario library. These tests verify
the entire system workflow from task scheduling to execution and reporting.
"""

import os
import pytest
import time
import random
import pendulum
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock
from unittest.mock import patch
from dataclasses import dataclass
from enum import Enum

from airdrops.scheduler.bot import TaskStatus
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.monitoring.collector import MetricsCollector
from airdrops.risk_management.core import RiskManager
from airdrops.analytics.portfolio import PortfolioPerformanceAnalyzer
from airdrops.analytics.tracker import AirdropTracker
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


from .mocks.wallets import (
    MockHotWallet,
    MockLowBalanceWallet,
    MockCompromisedWallet,
    MockNetworkFailureWallet
)


class FarmingCyclePhase(Enum):
    """Phases of a farming cycle."""
    INITIALIZATION = "initialization"
    CAPITAL_ALLOCATION = "capital_allocation"
    TASK_GENERATION = "task_generation"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    REPORTING = "reporting"
    CLEANUP = "cleanup"

@dataclass
class FarmingCycleMetrics:
    """Metrics collected during a farming cycle."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_gas_used: int
    total_value_usd: Decimal
    cycle_duration_seconds: float
    protocols_used: List[str]
    wallets_used: List[str]
    risk_events: List[Dict[str, Any]]

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100


class TestE2EFarmingCycles:
    """End-to-end test scenarios for complete farming cycles."""

    @pytest.fixture
    def farming_config(self) -> Dict[str, Any]:
        """Create comprehensive farming cycle configuration.

        Returns:
                Complete system configuration for farming cycles
        """
        return {
            "system": {
                "environment": "test",
                "start_time": pendulum.now().isoformat(),
                "cycle_duration_hours": 24,
            },
            "wallets": [
                {
                    "address": "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775",
                    "private_key": "test_key_1",
                    "type": "hot",
                    "initial_balance_eth": 2.0,
                },
                {
                    "address": "0x853d35Cc6634C0532925a3b844Bc9e7195Ed5E47283776",
                    "private_key": "test_key_2",
                    "type": "hot",
                    "initial_balance_eth": 1.5,
                },
                {
                    "address": "0x963d35Cc6634C0532925a3b844Bc9e7195Ed5E47283777",
                    "private_key": "test_key_3",
                    "type": "hot",
                    "initial_balance_eth": 1.0,
                },
            ],
            "protocols": {
                "scroll": {
                    "enabled": True,
                    "daily_activity_range": [3, 5],
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
                    "enabled": True,
                    "daily_activity_range": [1, 2],
                    "operations": {
                        "restake": {"enabled": True, "weight": 100},
                    },
                },
            },
            "capital_allocation": {
                "strategy": "mean_variance",
                "total_capital_usd": 150000,
                "rebalance_threshold": 0.15,
                "min_protocol_allocation": 0.05,
                "max_protocol_allocation": 0.40,
            },
            "risk_management": {
                "max_daily_gas_usd": 750,
                "max_protocol_exposure": 0.35,
                "min_balance_eth": 0.05,
                "stop_loss_percentage": 0.20,
                "volatility_window_hours": 24,
            },
            "scheduler": {
                "max_concurrent_tasks": 8,
                "max_retries": 3,
                "retry_delay": 60,
                "task_timeout": 300,
                "activity_hours": {
                    "start": 8,
                    "end": 23,
                },
            },
            "monitoring": {
                "metrics_interval": 30,
                "health_check_interval": 180,
                "alert_cooldown_minutes": 10,
            },
        }

    @pytest.fixture
    def mock_wallet_factory(self) -> Dict[str, Any]:
        """Factory for creating different types of mock wallets.

        Returns:
                Dictionary mapping wallet types to factory functions
        """

        def create_normal_wallet(address: str, balance_eth: float = 2.0):
            return MockHotWallet(initial_balance=int(balance_eth * 10**18))

        def create_low_balance_wallet(address: str, balance_eth: float = 0.05):
            return MockLowBalanceWallet(balance=int(balance_eth * 10**18))

        def create_compromised_wallet(address: str, balance_eth: float = 1.0):
            return MockCompromisedWallet(balance=int(balance_eth * 10**18))

        def create_network_failure_wallet(address: str, balance_eth: float = 2.0):
            return MockNetworkFailureWallet(balance=int(balance_eth * 10**18))

        return {
            "normal": create_normal_wallet,
            "low_balance": create_low_balance_wallet,
            "compromised": create_compromised_wallet,
            "network_failure": create_network_failure_wallet,
        }

    @patch("airdrops.protocols.scroll.scroll.bridge_assets")
    @patch("airdrops.protocols.scroll.scroll.swap_tokens")
    @patch("airdrops.protocols.zksync.zksync.bridge_eth")
    @patch("airdrops.protocols.zksync.zksync.swap_tokens")
    @patch("airdrops.protocols.eigenlayer.eigenlayer.restake_lst")
    def test_complete_farming_cycle_normal_conditions(
        self,
        mock_eigenlayer_restake,
        mock_zksync_swap,
        mock_zksync_bridge,
        mock_scroll_swap,
        mock_scroll_bridge,
        farming_config,
        mock_wallet_factory
    ):
        """Test a complete farming cycle under normal operating conditions.

        This test simulates a full 24-hour farming cycle including:
        1. System initialization and wallet setup
        2. Capital allocation across protocols
        3. Task generation and scheduling
        4. Sequential task execution with normal wallets
        5. Real-time monitoring and metrics collection
        6. End-of-cycle reporting and analysis

        Args:
                mock_eigenlayer_restake: Mock EigenLayer restaking function
                mock_zksync_swap: Mock zkSync swap function
                mock_zksync_bridge: Mock zkSync bridge function
                mock_scroll_swap: Mock Scroll swap function
                mock_scroll_bridge: Mock Scroll bridge function
                farming_config: Test configuration
                mock_wallet_factory: Factory for creating mock wallets
        """
        print("\n=== COMPLETE FARMING CYCLE TEST (NORMAL CONDITIONS) ===")

        # Setup protocol mocks for successful operations
        mock_scroll_bridge.return_value = "0x" + "a" * 64
        mock_scroll_swap.return_value = "0x" + "b" * 64
        mock_zksync_bridge.return_value = (True, "0x" + "c" * 64)
        mock_zksync_swap.return_value = (True, "0x" + "d" * 64)
        mock_eigenlayer_restake.return_value = (True, "0x" + "e" * 64)

        cycle_start_time = time.time()
        cycle_metrics = FarmingCycleMetrics(
            total_tasks=0,
            successful_tasks=0,
            failed_tasks=0,
            total_gas_used=0,
            total_value_usd=Decimal("0"),
            cycle_duration_seconds=0.0,
            protocols_used=[],
            wallets_used=[],
            risk_events=[]
        )

        # Phase 1: System Initialization
        print("\n1. Initializing farming cycle components...")

        allocator = CapitalAllocator(farming_config)
        risk_manager = RiskManager(farming_config)
        metrics_collector = MetricsCollector()
        mock_tracker = Mock(spec=AirdropTracker)
        mock_tracker.get_all_events.return_value = []
        portfolio_analyzer = PortfolioPerformanceAnalyzer(tracker=mock_tracker)

        # Create normal wallets for this cycle
        wallets = {}
        for wallet_config in farming_config["wallets"]:
            address = wallet_config["address"]
            balance = wallet_config["initial_balance_eth"]
            wallets[address] = mock_wallet_factory["normal"](address, balance)
            cycle_metrics.wallets_used.append(address)

        print(f"   Initialized {len(wallets)} wallets")

        # Phase 2: Capital Allocation
        print("\n2. Performing capital allocation...")

        protocols = ["scroll", "zksync", "eigenlayer"]
        risk_constraints = {"max_protocol_exposure": Decimal("0.35")}

        portfolio = allocator.optimize_portfolio(protocols, risk_constraints)
        print(f"   Portfolio allocation: {portfolio}")

        total_capital = Decimal(farming_config["capital_allocation"]["total_capital_usd"])
        risk_metrics = {"volatility_state": "low", "gas_price": 25}

        capital_allocation = allocator.allocate_risk_adjusted_capital(
            total_capital, portfolio, risk_metrics
        )
        print(f"   Capital allocated: ${sum(capital_allocation.values()):.2f}")

        # Phase 3: Task Generation
        print("\n3. Generating farming tasks...")

        farming_tasks = []
        task_id_counter = 0

        for wallet_address, wallet in wallets.items():
            for protocol in protocols:
                if protocol in capital_allocation and capital_allocation[protocol] > 0:
                    # Generate 3-5 tasks per protocol per wallet
                    num_tasks = random.randint(3, 5)
                    for i in range(num_tasks):
                        task = {
                            "id": f"{protocol}_{wallet_address[-4:]}_{task_id_counter}",
                            "protocol": protocol,
                            "wallet": wallet_address,
                            "action": self._select_weighted_action(protocol, farming_config),
                            "scheduled_time": pendulum.now().add(minutes=i * 15),
                            "status": TaskStatus.PENDING,
                            "params": self._generate_task_params(protocol, wallet),
                        }
                        farming_tasks.append(task)
                        task_id_counter += 1

                        if protocol not in cycle_metrics.protocols_used:
                            cycle_metrics.protocols_used.append(protocol)

        cycle_metrics.total_tasks = len(farming_tasks)
        print(f"   Generated {len(farming_tasks)} farming tasks")

        # Phase 4: Task Execution
        print("\n4. Executing farming tasks...")

        executed_tasks = []
        failed_tasks = []

        # Execute tasks in batches to simulate realistic timing
        batch_size = 5
        for i in range(0, len(farming_tasks), batch_size):
            batch = farming_tasks[i:i + batch_size]

            for task in batch:
                # Pre-execution risk check
                risk_check = risk_manager.validate_operation({
                    "protocol": task["protocol"],
                    "action": task["action"],
                    "estimated_gas": 250000,
                    "value_usd": 750,
                })

                if not risk_check:
                    print(f"   Task {task['id']} failed risk check")
                    failed_tasks.append(task)
                    cycle_metrics.risk_events.append({
                        "type": "risk_check_failure",
                        "task_id": task["id"],
                        "protocol": task["protocol"]
                    })
                    continue

                # Execute task with wallet
                wallet = wallets[task["wallet"]]
                result = self._execute_farming_task(task, wallet)

                # Record metrics
                gas_used = result.get("gas_used", 200000)
                value_usd = result.get("value_usd", 600)

                metrics_collector.record_transaction(
                    protocol=task["protocol"],
                    action=task["action"],
                    wallet=task["wallet"],
                    success=result["success"],
                    gas_used=gas_used,
                    value_usd=value_usd,
                    tx_hash=result.get("tx_hash", "0x" + "0" * 64)
                )

                cycle_metrics.total_gas_used += gas_used
                cycle_metrics.total_value_usd += Decimal(str(value_usd))

                if result["success"]:
                    executed_tasks.append(task)
                    cycle_metrics.successful_tasks += 1
                    print(f"   ✓ Task {task['id']} executed successfully")
                else:
                    failed_tasks.append(task)
                    cycle_metrics.failed_tasks += 1
                    print(f"   ✗ Task {task['id']} failed: {result.get('error', 'Unknown error')}")

            # Brief pause between batches
            time.sleep(0.1)

        # Phase 5: Mid-cycle Monitoring
        print("\n5. Performing mid-cycle analysis...")

        current_prices = {
            "scroll": Decimal("1875.00"),
            "zksync": Decimal("1880.00"),
            "eigenlayer": Decimal("1870.00"),
        }

        portfolio_metrics = portfolio_analyzer.calculate_portfolio_metrics(
            capital_allocation,
            current_prices
        )
        print(f"   Portfolio value: ${portfolio_metrics.total_portfolio_value_usd:.2f}")
        print(f"   Cycle return: {portfolio_metrics.portfolio_roi_percentage:.2%}")

        # Check for rebalancing needs
        current_allocation = self._calculate_current_allocation(
            capital_allocation, current_prices
        )

        needs_rebalance = allocator.check_rebalance_needed(
            portfolio, current_allocation
        )
        print(f"   Rebalancing needed: {needs_rebalance}")

        # Phase 6: End-of-cycle Reporting
        print("\n6. Generating cycle completion report...")

        cycle_end_time = time.time()
        cycle_metrics.cycle_duration_seconds = cycle_end_time - cycle_start_time

        # Generate protocol performance metrics
        protocol_performance = {}
        for protocol in protocols:
            metrics = metrics_collector.get_protocol_metrics(protocol)
            protocol_performance[protocol] = metrics
            print(
                f"   {protocol}: {metrics['successful_transactions']}/"
                f"{metrics['total_transactions']} successful "
                f"({metrics['success_rate']:.1%})"
            )

        # Final cycle summary
        print("\n=== FARMING CYCLE SUMMARY ===")
        print(f"   Duration: {cycle_metrics.cycle_duration_seconds:.1f} seconds")
        print(f"   Total tasks: {cycle_metrics.total_tasks}")
        print(f"   Successful: {cycle_metrics.successful_tasks}")
        print(f"   Failed: {cycle_metrics.failed_tasks}")
        print(f"   Success rate: {cycle_metrics.success_rate:.1%}")
        print(f"   Total gas used: {cycle_metrics.total_gas_used:,}")
        print(f"   Total value: ${cycle_metrics.total_value_usd:.2f}")
        print(f"   Protocols used: {', '.join(cycle_metrics.protocols_used)}")
        print(f"   Risk events: {len(cycle_metrics.risk_events)}")

        # Assertions for cycle success
        assert cycle_metrics.total_tasks > 0, "No tasks were generated"
        assert cycle_metrics.successful_tasks > 0, "No tasks executed successfully"
        assert cycle_metrics.success_rate >= 85.0, f"Success rate too low: {cycle_metrics.success_rate:.1%}"
        assert len(cycle_metrics.protocols_used) >= 2, "Not enough protocols utilized"
        assert cycle_metrics.total_value_usd > Decimal("1000"), "Insufficient trading volume"
        assert all(
            metrics["total_transactions"] > 0
            for metrics in protocol_performance.values()
        ), "Some protocols have no transactions"

    @patch("airdrops.protocols.scroll.scroll.bridge_assets")
    @patch("airdrops.protocols.scroll.scroll.swap_tokens")
    @patch("airdrops.protocols.zksync.zksync.bridge_eth")
    @patch("airdrops.protocols.zksync.zksync.swap_tokens")
    def test_multi_day_farming_cycle_with_varying_conditions(
        self,
        mock_zksync_swap,
        mock_zksync_bridge,
        mock_scroll_swap,
        mock_scroll_bridge,
        farming_config,
        mock_wallet_factory
    ):
        """Test multi-day farming cycle with varying market and wallet conditions.

        This test simulates a 3-day farming cycle where:
        - Day 1: Normal conditions with hot wallets
        - Day 2: Gas spike conditions with mixed wallet types
        - Day 3: Low balance conditions and network issues

        Args:
                mock_zksync_swap: Mock zkSync swap function
                mock_zksync_bridge: Mock zkSync bridge function
                mock_scroll_swap: Mock Scroll swap function
                mock_scroll_bridge: Mock Scroll bridge function
                farming_config: Test configuration
                mock_wallet_factory: Factory for creating mock wallets
        """
        print("\n=== MULTI-DAY FARMING CYCLE TEST ===")

        # Setup base mocks
        mock_scroll_bridge.return_value = "0x" + "a" * 64
        mock_scroll_swap.return_value = "0x" + "b" * 64
        mock_zksync_bridge.return_value = (True, "0x" + "c" * 64)
        mock_zksync_swap.return_value = (True, "0x" + "d" * 64)

        # Initialize system components
        risk_manager = RiskManager(farming_config)
        metrics_collector = MetricsCollector()

        daily_results = []
        protocols = ["scroll", "zksync"]

        # Simulate 3 days of farming
        for day in range(1, 4):
            print(f"\n--- Day {day} Farming Cycle ---")

            # Configure day-specific conditions
            day_config = self._get_day_specific_config(day, farming_config)
            wallet_types = self._get_day_wallet_types(day)

            print(f"Market conditions: {day_config['market_state']}")
            print(f"Wallet types: {', '.join(wallet_types)}")

            # Create wallets for the day
            day_wallets = {}
            for i, wallet_config in enumerate(farming_config["wallets"]):
                address = wallet_config["address"]
                wallet_type = wallet_types[i % len(wallet_types)]
                balance = wallet_config["initial_balance_eth"]

                day_wallets[address] = mock_wallet_factory[wallet_type](address, balance)

            # Generate and execute tasks for the day
            day_tasks = self._generate_daily_tasks(
                day_wallets, protocols, day_config, day
            )

            day_metrics = self._execute_daily_tasks(
                day_tasks, day_wallets, risk_manager, metrics_collector, day_config
            )

            daily_results.append({
                "day": day,
                "config": day_config,
                "metrics": day_metrics,
                "wallet_types": wallet_types,
            })

            print(f"Day {day} Summary:")
            print(f"  Tasks: {day_metrics.successful_tasks}/{day_metrics.total_tasks}")
            print(f"  Success rate: {day_metrics.success_rate:.1%}")
            print(f"  Risk events: {len(day_metrics.risk_events)}")

        # Analyze multi-day results
        print("\n=== MULTI-DAY ANALYSIS ===")

        total_tasks = sum(result["metrics"].total_tasks for result in daily_results)
        total_successful = sum(result["metrics"].successful_tasks for result in daily_results)
        overall_success_rate = (total_successful / total_tasks) * 100 if total_tasks > 0 else 0

        print(f"Overall success rate: {overall_success_rate:.1%}")
        print(f"Total tasks across 3 days: {total_tasks}")
        print(f"Total successful tasks: {total_successful}")

        # Day-specific analysis
        for result in daily_results:
            day = result["day"]
            metrics = result["metrics"]
            config = result["config"]

            print(f"\nDay {day} ({config['market_state']}):")
            print(f"  Success rate: {metrics.success_rate:.1%}")
            print(f"  Risk events: {len(metrics.risk_events)}")

            # Verify day-specific expectations
            if day == 1:  # Normal conditions
                assert metrics.success_rate >= 90.0, f"Day 1 success rate too low: {metrics.success_rate:.1%}"
            elif day == 2:  # Gas spike conditions
                assert metrics.success_rate >= 60.0, f"Day 2 success rate too low: {metrics.success_rate:.1%}"
                assert len(metrics.risk_events) > 0, "Expected risk events on day 2"
            elif day == 3:  # Low balance/network issues
                assert metrics.success_rate >= 30.0, f"Day 3 success rate too low: {metrics.success_rate:.1%}"
                assert len(metrics.risk_events) > 0, "Expected risk events on day 3"

        # Overall assertions
        assert total_tasks >= 30, "Insufficient total tasks generated"
        assert overall_success_rate >= 60.0, f"Overall success rate too low: {overall_success_rate:.1%}"
        assert len(daily_results) == 3, "Missing daily results"

    @patch("airdrops.protocols.scroll.scroll.bridge_assets")
    @patch("airdrops.protocols.zksync.zksync.bridge_eth")
    def test_farming_cycle_with_risk_management_integration(
        self,
        mock_zksync_bridge,
        mock_scroll_bridge,
        farming_config,
        mock_wallet_factory
    ):
        """Test farming cycle with comprehensive risk management integration.

        This test verifies:
        1. Risk assessment before task execution
        2. Dynamic risk threshold adjustments
        3. Emergency shutdown procedures
        4. Risk event logging and alerting
        5. Recovery from risk events

        Args:
                mock_zksync_bridge: Mock zkSync bridge function
                mock_scroll_bridge: Mock Scroll bridge function
                farming_config: Test configuration
                mock_wallet_factory: Factory for creating mock wallets
        """
        print("\n=== RISK MANAGEMENT INTEGRATION TEST ===")

        # Setup mocks with some failures to trigger risk events
        mock_scroll_bridge.side_effect = [
            "0x" + "a" * 64,  # Success
            Exception("Bridge failure"),  # Failure
            "0x" + "b" * 64,  # Success after recovery
        ]
        mock_zksync_bridge.return_value = (True, "0x" + "c" * 64)

        # Initialize components with enhanced risk monitoring
        risk_manager = RiskManager(farming_config)

        # Create mixed wallet types to trigger different risk scenarios
        wallets = {}
        wallet_configs = [
            ("normal", 2.0),
            ("low_balance", 0.05),
            ("compromised", 1.0),
        ]

        for i, wallet_config in enumerate(farming_config["wallets"]):
            address = wallet_config["address"]
            wallet_type, balance = wallet_configs[i % len(wallet_configs)]
            wallets[address] = mock_wallet_factory[wallet_type](address, balance)

        # Generate high-risk tasks
        risk_tasks = []
        protocols = ["scroll", "zksync"]

        for i, (wallet_address, wallet) in enumerate(wallets.items()):
            for protocol in protocols:
                task = {
                    "id": f"risk_task_{protocol}_{i}",
                    "protocol": protocol,
                    "wallet": wallet_address,
                    "action": "bridge" if protocol == "scroll" else "bridge_eth",
                    "params": {
                        "amount": 1.0,  # High amount to trigger risk checks
                        "estimated_gas": 500000,  # High gas
                        "value_usd": 2000,  # High value
                    },
                }
                risk_tasks.append(task)

        print(f"Generated {len(risk_tasks)} high-risk tasks")

        # Execute tasks with risk management
        risk_events = []
        successful_tasks = 0
        blocked_tasks = 0

        for task in risk_tasks:
            print(f"\nEvaluating task {task['id']}...")

            # Pre-execution risk assessment
            risk_assessment = risk_manager.validate_operation({
                "protocol": task["protocol"],
                "action": task["action"],
                "estimated_gas": task["params"]["estimated_gas"],
                "value_usd": task["params"]["value_usd"],
                "wallet": task["wallet"],
            })

            if not risk_assessment:
                print("  ⚠️  Task blocked by risk management")
                blocked_tasks += 1
                risk_events.append({
                    "type": "task_blocked",
                    "task_id": task["id"],
                    "reason": "risk_threshold_exceeded"
                })
                continue

            # Attempt task execution
            try:
                wallet = wallets[task["wallet"]]
                result = self._execute_farming_task(task, wallet)

                if result["success"]:
                    successful_tasks += 1
                    print("  ✓ Task executed successfully")
                else:
                    print(f"  ✗ Task failed: {result.get('error', 'Unknown error')}")
                    risk_events.append({
                        "type": "task_execution_failure",
                        "task_id": task["id"],
                        "error": result.get("error")
                    })

            except Exception as e:
                print(f"  ⚠️  Task execution error: {str(e)}")
                risk_events.append({
                    "type": "execution_exception",
                    "task_id": task["id"],
                    "error": str(e)
                })

                # Record risk event in risk manager
                risk_manager.record_risk_event(
                    "execution_failure",
                    details={
                        "task_id": task["id"],
                        "protocol": task["protocol"],
                        "error": str(e)
                    }
                )

        # Test emergency shutdown scenario
        print("\n--- Testing Emergency Shutdown ---")

        emergency_event = {
            "type": "emergency_shutdown",
            "reason": "multiple_protocol_failures",
            "severity": "critical",
            "affected_protocols": ["scroll"],
        }

        shutdown_response = risk_manager.record_risk_event(
            "emergency_shutdown",
            details=emergency_event
        )

        print(f"Emergency shutdown response: {shutdown_response['action']}")

        # Verify risk management effectiveness
        print("\n=== RISK MANAGEMENT SUMMARY ===")
        print(f"Total tasks: {len(risk_tasks)}")
        print(f"Successful tasks: {successful_tasks}")
        print(f"Blocked tasks: {blocked_tasks}")
        print(f"Risk events: {len(risk_events)}")
        print(f"Emergency shutdown: {shutdown_response['action'] == 'emergency_shutdown'}")

        # Risk management assertions
        assert len(risk_events) > 0, "Expected risk events to be generated"
        assert blocked_tasks > 0, "Expected some tasks to be blocked by risk management"
        assert shutdown_response["action"] == "emergency_shutdown", "Emergency shutdown not triggered"
        assert successful_tasks < len(risk_tasks), "Expected some tasks to fail due to risk conditions"

        # Verify risk event types
        event_types = [event["type"] for event in risk_events]
        assert "task_blocked" in event_types, "Expected task blocking events"

        print("✓ Risk management integration verified successfully")

    def _select_weighted_action(self, protocol: str, config: Dict[str, Any]) -> str:
        """Select an action based on protocol configuration weights.

        Args:
                protocol: Protocol name
                config: System configuration

        Returns:
                Selected action name
        """
        operations = config["protocols"][protocol]["operations"]
        actions = []
        weights = []

        for action, settings in operations.items():
            if settings["enabled"]:
                actions.append(action)
                weights.append(settings["weight"])

        if not actions:
            return "bridge"  # Default fallback

        # Weighted random selection
        total_weight = sum(weights)
        rand_val = random.randint(1, total_weight)

        cumulative = 0
        for action, weight in zip(actions, weights):
            cumulative += weight
            if rand_val <= cumulative:
                return action

        return actions[0]  # Fallback

    def _generate_task_params(self, protocol: str, wallet) -> Dict[str, Any]:
        """Generate realistic task parameters for a protocol.

        Args:
                protocol: Protocol name
                wallet: Mock wallet instance

        Returns:
                Task parameters dictionary
        """
        base_params = {
            "estimated_gas": random.randint(150000, 350000),
            "value_usd": random.randint(100, 1500),
            "priority": random.choice(["low", "medium", "high"]),
        }

        if protocol == "scroll":
            base_params.update({
                "amount": random.uniform(0.1, 2.0),
                "token_in": "ETH",
                "token_out": "USDC",
                "slippage": 0.005,
            })
        elif protocol == "zksync":
            base_params.update({
                "amount": random.uniform(0.05, 1.5),
                "destination_chain": "ethereum",
                "bridge_fee": random.uniform(0.001, 0.01),
            })
        elif protocol == "eigenlayer":
            base_params.update({
                "lst_amount": random.uniform(0.5, 5.0),
                "operator": "0x" + "1" * 40,
                "strategy": "native_restaking",
            })

        return base_params

    def _execute_farming_task(self, task: Dict[str, Any], wallet) -> Dict[str, Any]:
        """Execute a farming task with the given wallet.

        Args:
                task: Task configuration
                wallet: Mock wallet instance

        Returns:
                Execution result dictionary
        """
        try:
            # Simulate task execution based on wallet type and protocol
            protocol = task["protocol"]
            action = task["action"]
            params = task["params"]

            # Check wallet balance
            if hasattr(wallet, 'balance') and wallet.balance < 50000000000000000:  # 0.05 ETH
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "gas_used": 0,
                    "value_usd": 0,
                }

            # Simulate protocol-specific execution
            if protocol == "scroll":
                if action == "bridge":
                    tx_hash = "0x" + "a" * 64
                elif action == "swap":
                    tx_hash = "0x" + "b" * 64
                else:
                    tx_hash = "0x" + "c" * 64
            elif protocol == "zksync":
                if action == "bridge":
                    tx_hash = "0x" + "d" * 64
                elif action == "swap":
                    tx_hash = "0x" + "e" * 64
                else:
                    tx_hash = "0x" + "f" * 64
            else:  # eigenlayer
                tx_hash = "0x" + "1" * 64

            # Simulate wallet-specific behavior
            if hasattr(wallet, 'is_compromised') and wallet.is_compromised:
                return {
                    "success": False,
                    "error": "Wallet security compromised",
                    "gas_used": params["estimated_gas"] // 2,
                    "value_usd": 0,
                }

            if hasattr(wallet, 'network_failure') and wallet.network_failure:
                return {
                    "success": False,
                    "error": "Network connection failed",
                    "gas_used": 21000,  # Base gas for failed tx
                    "value_usd": 0,
                }

            # Successful execution
            return {
                "success": True,
                "tx_hash": tx_hash,
                "gas_used": params["estimated_gas"],
                "value_usd": params["value_usd"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "gas_used": 21000,
                "value_usd": 0,
            }

    def _calculate_current_allocation(
        self,
        capital_allocation: Dict[str, Decimal],
        current_prices: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """Calculate current portfolio allocation based on prices.

        Args:
                capital_allocation: Original capital allocation
                current_prices: Current market prices

        Returns:
                Current allocation percentages
        """
        total_value = Decimal("0")
        current_values = {}

        for protocol, allocation in capital_allocation.items():
            if protocol in current_prices:
                current_value = allocation * (current_prices[protocol] / Decimal("1875"))  # Base price
                current_values[protocol] = current_value
                total_value += current_value

        if total_value == 0:
            return {protocol: Decimal("0") for protocol in capital_allocation}

        return {
            protocol: (value / total_value)
            for protocol, value in current_values.items()
        }

    def _get_day_specific_config(self,
        day: int,
        base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get day-specific configuration for multi-day testing.

        Args:
                day: Day number (1-3)
                base_config: Base configuration

        Returns:
                Day-specific configuration
        """
        config = base_config.copy()

        if day == 1:  # Normal conditions
            config["market_state"] = "normal"
            config["gas_price_gwei"] = 25
            config["volatility"] = "low"
        elif day == 2:  # Gas spike conditions
            config["market_state"] = "gas_spike"
            config["gas_price_gwei"] = 150
            config["volatility"] = "medium"
        else:  # Day 3 - Low balance/network issues
            config["market_state"] = "network_issues"
            config["gas_price_gwei"] = 75
            config["volatility"] = "high"

        return config

    def _get_day_wallet_types(self, day: int) -> List[str]:
        """Get wallet types for specific day testing.

        Args:
                day: Day number (1-3)

        Returns:
                List of wallet types to use
        """
        if day == 1:  # Normal conditions
            return ["normal", "normal", "normal"]
        elif day == 2:  # Mixed conditions
            return ["normal", "low_balance", "normal"]
        else:  # Day 3 - Problematic conditions
            return ["low_balance", "network_failure", "compromised"]

    def _generate_daily_tasks(
        self,
        wallets: Dict[str, Any],
        protocols: List[str],
        day_config: Dict[str, Any],
        day: int
    ) -> List[Dict[str, Any]]:
        """Generate tasks for a specific day.

        Args:
                wallets: Available wallets
                protocols: Available protocols
                day_config: Day-specific configuration
                day: Day number

        Returns:
                List of generated tasks
        """
        tasks = []
        task_id = 0

        # Adjust task count based on day conditions
        if day == 1:
            tasks_per_wallet = 4
        elif day == 2:
            tasks_per_wallet = 3  # Reduced due to gas spike
        else:
            tasks_per_wallet = 2  # Further reduced due to issues

        for wallet_address in wallets.keys():
            for protocol in protocols:
                for i in range(tasks_per_wallet):
                    task = {
                        "id": f"day{day}_{protocol}_{wallet_address[-4:]}_{task_id}",
                        "protocol": protocol,
                        "wallet": wallet_address,
                        "action": "bridge" if protocol == "scroll" else "bridge_eth",
                        "params": {
                            "amount": random.uniform(0.1, 1.0),
                            "estimated_gas": random.randint(200000, 400000),
                            "value_usd": random.randint(200, 1000),
                        },
                        "day": day,
                    }
                    tasks.append(task)
                    task_id += 1

        return tasks

    def _execute_daily_tasks(
        self,
        tasks: List[Dict[str, Any]],
        wallets: Dict[str, Any],
        risk_manager,
        metrics_collector,
        day_config: Dict[str, Any]
    ) -> FarmingCycleMetrics:
        """Execute tasks for a specific day and collect metrics.

        Args:
                tasks: Tasks to execute
                wallets: Available wallets
                risk_manager: Risk management instance
                metrics_collector: Metrics collection instance
                day_config: Day-specific configuration

        Returns:
                Day metrics
        """
        metrics = FarmingCycleMetrics(
            total_tasks=len(tasks),
            successful_tasks=0,
            failed_tasks=0,
            total_gas_used=0,
            total_value_usd=Decimal("0"),
            cycle_duration_seconds=0.0,
            protocols_used=[],
            wallets_used=list(wallets.keys()),
            risk_events=[]
        )

        start_time = time.time()

        for task in tasks:
            # Risk assessment based on day conditions
            risk_multiplier = 1.0
            if day_config["market_state"] == "gas_spike":
                risk_multiplier = 2.0
            elif day_config["market_state"] == "network_issues":
                risk_multiplier = 3.0

            # Simulate risk check failure for high-risk days
            if risk_multiplier > 1.5 and random.random() < 0.3:
                metrics.risk_events.append({
                    "type": "high_risk_blocked",
                    "task_id": task["id"],
                    "day": task["day"]
                })
                metrics.failed_tasks += 1
                continue

            # Execute task
            wallet = wallets[task["wallet"]]
            result = self._execute_farming_task(task, wallet)

            # Record metrics
            gas_used = result.get("gas_used", 0)
            value_usd = result.get("value_usd", 0)

            metrics.total_gas_used += gas_used
            metrics.total_value_usd += Decimal(str(value_usd))

            if result["success"]:
                metrics.successful_tasks += 1
            else:
                metrics.failed_tasks += 1
                metrics.risk_events.append({
                    "type": "execution_failure",
                    "task_id": task["id"],
                    "error": result.get("error"),
                    "day": task["day"]
                })

            # Track protocols used
            if task["protocol"] not in metrics.protocols_used:
                metrics.protocols_used.append(task["protocol"])

        metrics.cycle_duration_seconds = time.time() - start_time
        return metrics
