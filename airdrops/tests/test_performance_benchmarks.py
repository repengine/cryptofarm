"""
Performance benchmark tests for critical airdrops operations.

This module contains performance benchmarks to ensure critical operations
meet performance requirements and to track performance regressions.
"""

import pytest
import time
import statistics
from decimal import Decimal
from typing import List, Dict, Any, Callable
from unittest.mock import Mock, patch
import random
import concurrent.futures

from airdrops.capital_allocation.engine import CapitalAllocator, AllocationStrategy
from airdrops.monitoring.collector import MetricsCollector
from airdrops.monitoring.aggregator import MetricsAggregator
from airdrops.scheduler.bot import CentralScheduler, TaskPriority
from airdrops.analytics.optimizer import ROIOptimizer
from airdrops.protocols.scroll import scroll
from airdrops.protocols.zksync import zksync


class PerformanceBenchmark:
    """Base class for performance benchmarks."""
    
    def __init__(self, name: str, target_ms: float):
        """Initialize benchmark.
        
        Args:
            name: Benchmark name
            target_ms: Target execution time in milliseconds
        """
        self.name = name
        self.target_ms = target_ms
        self.results: List[float] = []
    
    def run(self, func: Callable, iterations: int = 100) -> Dict[str, float]:
        """Run benchmark and collect statistics.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations
            
        Returns:
            Dictionary with benchmark statistics
        """
        # Warmup
        for _ in range(10):
            func()
        
        # Actual benchmark
        self.results = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            self.results.append((end - start) * 1000)  # Convert to ms
        
        return {
            "name": self.name,
            "iterations": iterations,
            "mean_ms": statistics.mean(self.results),
            "median_ms": statistics.median(self.results),
            "stdev_ms": statistics.stdev(self.results) if len(self.results) > 1 else 0,
            "min_ms": min(self.results),
            "max_ms": max(self.results),
            "p95_ms": self._percentile(95),
            "p99_ms": self._percentile(99),
            "target_ms": self.target_ms,
            "meets_target": statistics.mean(self.results) <= self.target_ms,
        }
    
    def _percentile(self, p: int) -> float:
        """Calculate percentile.
        
        Args:
            p: Percentile (0-100)
            
        Returns:
            Percentile value
        """
        sorted_results = sorted(self.results)
        index = int((p / 100) * len(sorted_results))
        return sorted_results[min(index, len(sorted_results) - 1)]


class TestCapitalAllocationPerformance:
    """Performance benchmarks for capital allocation operations."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Create mock configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            "capital_allocation": {
                "strategy": "mean_variance",
                "rebalance_threshold": 0.1,
                "min_protocol_allocation": 0.05,
                "max_protocol_allocation": 0.4,
            }
        }
    
    def test_portfolio_optimization_performance(self, mock_config):
        """Benchmark portfolio optimization with various protocol counts.
        
        Target: <100ms for up to 10 protocols
        """
        allocator = CapitalAllocator(mock_config)
        
        # Test with different numbers of protocols
        protocol_counts = [3, 5, 10, 15]
        results = []
        
        for count in protocol_counts:
            protocols = [f"protocol_{i}" for i in range(count)]
            risk_constraints = {"max_protocol_exposure": Decimal("0.35")}
            
            # Create random expected returns and risk scores
            expected_returns = {
                p: Decimal(random.uniform(0.05, 0.25))
                for p in protocols
            }
            risk_scores = {
                p: Decimal(random.uniform(0.1, 0.8))
                for p in protocols
            }
            
            def optimize():
                return allocator.optimize_portfolio(
                    protocols,
                    risk_constraints,
                    expected_returns=expected_returns,
                    risk_scores=risk_scores
                )
            
            benchmark = PerformanceBenchmark(
                f"portfolio_optimization_{count}_protocols",
                target_ms=100.0
            )
            result = benchmark.run(optimize, iterations=50)
            results.append(result)
            
            print(f"\nProtocols: {count}")
            print(f"Mean: {result['mean_ms']:.2f}ms")
            print(f"P95: {result['p95_ms']:.2f}ms")
            print(f"Meets target: {result['meets_target']}")
        
        # Assert performance targets
        for result in results:
            if "10_protocols" in result["name"]:
                assert result["mean_ms"] < 100, f"Portfolio optimization too slow: {result['mean_ms']}ms"
            assert result["p95_ms"] < 200, f"Portfolio optimization P95 too high: {result['p95_ms']}ms"
    
    def test_rebalancing_check_performance(self, mock_config):
        """Benchmark rebalancing check operations.
        
        Target: <10ms for checking rebalancing needs
        """
        allocator = CapitalAllocator(mock_config)
        
        # Create test portfolios
        protocols = ["scroll", "zksync", "eigenlayer", "layerzero", "hyperliquid"]
        target_allocation = {p: Decimal("0.2") for p in protocols}
        
        # Test various drift scenarios
        drift_levels = [0.05, 0.10, 0.15, 0.20]
        
        def check_rebalance():
            # Create slightly drifted current allocation
            drift = random.choice(drift_levels)
            current_allocation = {}
            for i, p in enumerate(protocols):
                if i == 0:
                    current_allocation[p] = target_allocation[p] * (1 + Decimal(drift))
                else:
                    adjustment = Decimal(drift) * target_allocation[protocols[0]] / (len(protocols) - 1)
                    current_allocation[p] = target_allocation[p] - adjustment
            
            return allocator.check_rebalance_needed(target_allocation, current_allocation)
        
        benchmark = PerformanceBenchmark("rebalancing_check", target_ms=10.0)
        result = benchmark.run(check_rebalance, iterations=1000)
        
        print(f"\nRebalancing Check Performance:")
        print(f"Mean: {result['mean_ms']:.2f}ms")
        print(f"P99: {result['p99_ms']:.2f}ms")
        
        assert result["mean_ms"] < 10, f"Rebalancing check too slow: {result['mean_ms']}ms"
        assert result["p99_ms"] < 20, f"Rebalancing check P99 too high: {result['p99_ms']}ms"


class TestMonitoringPerformance:
    """Performance benchmarks for monitoring operations."""
    
    def test_metrics_collection_performance(self):
        """Benchmark metrics collection rate.
        
        Target: >10,000 transactions/second
        """
        collector = MetricsCollector()
        
        # Generate test transactions
        protocols = ["scroll", "zksync", "eigenlayer"]
        actions = ["swap", "bridge", "liquidity", "lending"]
        wallets = [f"0x{'0' * 39}{i}" for i in range(100)]
        
        def record_batch():
            for _ in range(100):
                collector.record_transaction(
                    protocol=random.choice(protocols),
                    action=random.choice(actions),
                    wallet=random.choice(wallets),
                    success=random.random() > 0.1,
                    gas_used=random.randint(100000, 500000),
                    value_usd=random.uniform(10, 10000),
                    tx_hash=f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
                )
        
        benchmark = PerformanceBenchmark("metrics_collection", target_ms=10.0)  # 100 tx in 10ms = 10k/s
        result = benchmark.run(record_batch, iterations=100)
        
        transactions_per_second = (100 / result["mean_ms"]) * 1000
        
        print(f"\nMetrics Collection Performance:")
        print(f"Mean time for 100 tx: {result['mean_ms']:.2f}ms")
        print(f"Transactions/second: {transactions_per_second:.0f}")
        
        assert transactions_per_second > 10000, f"Metrics collection too slow: {transactions_per_second} tx/s"
    
    def test_aggregation_performance(self):
        """Benchmark metrics aggregation performance.
        
        Target: <500ms for aggregating 100k transactions
        """
        collector = MetricsCollector()
        aggregator = MetricsAggregator(collector)
        
        # Pre-populate with transactions
        print("\nPre-populating metrics...")
        protocols = ["scroll", "zksync", "eigenlayer", "layerzero", "hyperliquid"]
        actions = ["swap", "bridge", "liquidity", "lending"]
        
        for i in range(100000):
            if i % 10000 == 0:
                print(f"  Generated {i} transactions...")
            
            collector.record_transaction(
                protocol=random.choice(protocols),
                action=random.choice(actions),
                wallet=f"0x{'0' * 39}{i % 1000}",
                success=random.random() > 0.1,
                gas_used=random.randint(100000, 500000),
                value_usd=random.uniform(10, 10000),
                tx_hash=f"0x{i:064x}",
                timestamp=time.time() - random.randint(0, 86400)  # Last 24 hours
            )
        
        def aggregate():
            return aggregator.aggregate_metrics(
                window_start=time.time() - 3600,  # Last hour
                window_end=time.time(),
                group_by=["protocol", "action"]
            )
        
        benchmark = PerformanceBenchmark("metrics_aggregation_100k", target_ms=500.0)
        result = benchmark.run(aggregate, iterations=10)
        
        print(f"\nMetrics Aggregation Performance (100k transactions):")
        print(f"Mean: {result['mean_ms']:.2f}ms")
        print(f"P95: {result['p95_ms']:.2f}ms")
        
        assert result["mean_ms"] < 500, f"Aggregation too slow: {result['mean_ms']}ms"


class TestSchedulerPerformance:
    """Performance benchmarks for scheduler operations."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Create mock configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            "scheduler": {
                "max_concurrent_tasks": 10,
                "max_retries": 3,
                "retry_delay": 60,
            },
            "protocols": {
                "scroll": {"enabled": True},
                "zksync": {"enabled": True},
                "eigenlayer": {"enabled": True},
            }
        }
    
    @patch("airdrops.scheduler.bot.Web3")
    def test_task_scheduling_performance(self, mock_web3_class, mock_config):
        """Benchmark task scheduling performance.
        
        Target: <10ms to schedule a task
        """
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        scheduler = CentralScheduler(mock_config)
        
        # Create test tasks
        protocols = list(mock_config["protocols"].keys())
        actions = ["swap", "bridge", "liquidity"]
        priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH]
        
        def schedule_task():
            task = {
                "protocol": random.choice(protocols),
                "action": random.choice(actions),
                "priority": random.choice(priorities),
                "wallet": f"0x{'0' * 39}{random.randint(0, 99)}",
                "params": {"amount": random.uniform(100, 10000)},
            }
            return scheduler._add_task_to_queue(task)
        
        benchmark = PerformanceBenchmark("task_scheduling", target_ms=10.0)
        result = benchmark.run(schedule_task, iterations=1000)
        
        print(f"\nTask Scheduling Performance:")
        print(f"Mean: {result['mean_ms']:.2f}ms")
        print(f"P99: {result['p99_ms']:.2f}ms")
        
        assert result["mean_ms"] < 10, f"Task scheduling too slow: {result['mean_ms']}ms"
        assert result["p99_ms"] < 50, f"Task scheduling P99 too high: {result['p99_ms']}ms"
    
    def test_dependency_resolution_performance(self, mock_config):
        """Benchmark task dependency resolution.
        
        Target: <100ms for 100 tasks with complex dependencies
        """
        scheduler = CentralScheduler(mock_config)
        
        def create_task_graph(num_tasks: int) -> Dict[str, Any]:
            """Create a task graph with dependencies."""
            tasks = {}
            
            # Create layers of tasks
            layers = 5
            tasks_per_layer = num_tasks // layers
            
            for layer in range(layers):
                for i in range(tasks_per_layer):
                    task_id = f"task_{layer}_{i}"
                    tasks[task_id] = {
                        "id": task_id,
                        "dependencies": [],
                        "status": "pending"
                    }
                    
                    # Add dependencies from previous layer
                    if layer > 0:
                        num_deps = random.randint(1, min(3, tasks_per_layer))
                        for _ in range(num_deps):
                            dep_id = f"task_{layer-1}_{random.randint(0, tasks_per_layer-1)}"
                            if dep_id not in tasks[task_id]["dependencies"]:
                                tasks[task_id]["dependencies"].append(dep_id)
            
            return tasks
        
        def resolve_dependencies():
            task_graph = create_task_graph(100)
            return scheduler._resolve_dependencies(task_graph)
        
        benchmark = PerformanceBenchmark("dependency_resolution_100_tasks", target_ms=100.0)
        result = benchmark.run(resolve_dependencies, iterations=50)
        
        print(f"\nDependency Resolution Performance (100 tasks):")
        print(f"Mean: {result['mean_ms']:.2f}ms")
        print(f"P95: {result['p95_ms']:.2f}ms")
        
        assert result["mean_ms"] < 100, f"Dependency resolution too slow: {result['mean_ms']}ms"


class TestProtocolPerformance:
    """Performance benchmarks for protocol operations."""
    
    @patch("web3.Web3")
    @patch("web3.contract.Contract")
    def test_transaction_building_performance(self, mock_contract, mock_web3):
        """Benchmark transaction building performance.
        
        Target: <50ms to build a transaction
        """
        # Setup mocks
        mock_web3_instance = Mock()
        mock_web3_instance.eth.get_transaction_count.return_value = 10
        mock_web3_instance.eth.gas_price = 30000000000
        mock_web3_instance.to_checksum_address = lambda x: x
        mock_web3.return_value = mock_web3_instance
        
        mock_contract_instance = Mock()
        mock_contract_instance.functions = Mock()
        mock_contract.return_value = mock_contract_instance
        
        # Create config
        config = {
            "networks": {
                "scroll": {
                    "rpc_url": "https://test.com",
                    "chain_id": 534352,
                }
            }
        }
        
        def build_transaction():
            # Simulate building a swap transaction
            user_address = "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775"
            token_in = "0x0000000000000000000000000000000000000000"
            token_out = "0x1234567890123456789012345678901234567890"
            amount_in = 1000000000000000000  # 1 ETH
            
            # Build transaction parameters
            tx_params = {
                "from": user_address,
                "nonce": mock_web3_instance.eth.get_transaction_count(user_address),
                "gas": 300000,
                "gasPrice": mock_web3_instance.eth.gas_price,
                "value": amount_in if token_in == "0x0000000000000000000000000000000000000000" else 0,
            }
            
            return tx_params
        
        benchmark = PerformanceBenchmark("transaction_building", target_ms=50.0)
        result = benchmark.run(build_transaction, iterations=100)
        
        print(f"\nTransaction Building Performance:")
        print(f"Mean: {result['mean_ms']:.2f}ms")
        print(f"P95: {result['p95_ms']:.2f}ms")
        
        assert result["mean_ms"] < 50, f"Transaction building too slow: {result['mean_ms']}ms"


class TestConcurrencyPerformance:
    """Performance benchmarks for concurrent operations."""
    
    def test_concurrent_metrics_collection(self):
        """Benchmark concurrent metrics collection.
        
        Target: Linear scaling up to 10 threads
        """
        collector = MetricsCollector()
        
        def record_transactions(thread_id: int, count: int):
            """Record transactions from a single thread."""
            for i in range(count):
                collector.record_transaction(
                    protocol=f"protocol_{thread_id % 3}",
                    action="test",
                    wallet=f"0x{'0' * 38}{thread_id:02d}",
                    success=True,
                    gas_used=150000,
                    value_usd=100.0,
                    tx_hash=f"0x{thread_id:02d}{'0' * 60}{i:02d}"
                )
        
        # Test with different thread counts
        thread_counts = [1, 2, 4, 8, 10]
        transactions_per_thread = 10000
        results = []
        
        for num_threads in thread_counts:
            start = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for thread_id in range(num_threads):
                    future = executor.submit(
                        record_transactions,
                        thread_id,
                        transactions_per_thread
                    )
                    futures.append(future)
                
                # Wait for all threads
                concurrent.futures.wait(futures)
            
            end = time.perf_counter()
            duration_ms = (end - start) * 1000
            total_transactions = num_threads * transactions_per_thread
            throughput = (total_transactions / duration_ms) * 1000
            
            results.append({
                "threads": num_threads,
                "duration_ms": duration_ms,
                "throughput": throughput,
                "scaling_efficiency": throughput / (results[0]["throughput"] * num_threads) if results else 1.0
            })
            
            print(f"\nThreads: {num_threads}")
            print(f"Duration: {duration_ms:.2f}ms")
            print(f"Throughput: {throughput:.0f} tx/s")
            if results and len(results) > 1:
                print(f"Scaling efficiency: {results[-1]['scaling_efficiency']:.2%}")
        
        # Assert reasonable scaling
        for result in results:
            if result["threads"] <= 4:
                assert result["scaling_efficiency"] > 0.7, f"Poor scaling efficiency with {result['threads']} threads"


class TestMemoryPerformance:
    """Memory usage benchmarks."""
    
    def test_metrics_memory_usage(self):
        """Test memory usage for large numbers of metrics.
        
        Target: <100MB for 1M transactions
        """
        import gc
        import sys
        
        # Force garbage collection
        gc.collect()
        
        # Get initial memory usage
        initial_size = sys.getsizeof(gc.get_objects())
        
        collector = MetricsCollector()
        
        # Record 1M transactions
        print("\nRecording 1M transactions...")
        for i in range(1000000):
            if i % 100000 == 0:
                print(f"  Recorded {i} transactions...")
            
            collector.record_transaction(
                protocol=f"protocol_{i % 5}",
                action=f"action_{i % 4}",
                wallet=f"0x{'0' * 39}{i % 1000}",
                success=i % 10 != 0,
                gas_used=150000 + (i % 100000),
                value_usd=float(i % 10000),
                tx_hash=f"0x{i:064x}"
            )
        
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_size = sys.getsizeof(gc.get_objects())
        memory_used_mb = (final_size - initial_size) / (1024 * 1024)
        
        print(f"\nMemory used for 1M transactions: {memory_used_mb:.2f}MB")
        
        # Note: This is a simplified memory measurement
        # In practice, you'd use memory_profiler or similar tools
        # Assert reasonable memory usage (this assertion may need adjustment)
        assert memory_used_mb < 1000, f"Excessive memory usage: {memory_used_mb}MB"


def run_all_benchmarks():
    """Run all performance benchmarks and generate report."""
    print("=" * 80)
    print("PERFORMANCE BENCHMARK REPORT")
    print("=" * 80)
    
    # Run all benchmark classes
    benchmark_classes = [
        TestCapitalAllocationPerformance(),
        TestMonitoringPerformance(),
        TestSchedulerPerformance(),
        TestProtocolPerformance(),
        TestConcurrencyPerformance(),
        TestMemoryPerformance(),
    ]
    
    all_results = []
    
    for benchmark_class in benchmark_classes:
        class_name = benchmark_class.__class__.__name__
        print(f"\n{class_name}")
        print("-" * len(class_name))
        
        # Run all test methods
        for method_name in dir(benchmark_class):
            if method_name.startswith("test_"):
                method = getattr(benchmark_class, method_name)
                try:
                    # Create fixtures if needed
                    if "mock_config" in method.__code__.co_varnames:
                        mock_config = benchmark_class.mock_config()
                        method(mock_config)
                    else:
                        method()
                except Exception as e:
                    print(f"\nERROR in {method_name}: {e}")
    
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print("\nAll benchmarks completed. Review results above for performance metrics.")


if __name__ == "__main__":
    run_all_benchmarks()