# Central Scheduler Module

## Overview

The Central Scheduler module provides comprehensive task orchestration capabilities for the airdrops automation system. Built on APScheduler, it offers flexible scheduling, DAG-based dependency management, market condition awareness, and robust error handling with retry logic.

## Purpose

The Central Scheduler serves as the orchestration layer that:

- **Schedules Tasks**: Uses APScheduler for flexible cron, date, and interval-based scheduling
- **Manages Dependencies**: Implements DAG-based task dependency management to ensure proper execution order
- **Adapts to Market Conditions**: Integrates with Risk Management System and Capital Allocation Engine for intelligent scheduling decisions
- **Handles Failures**: Provides exponential backoff retry logic with configurable parameters
- **Prioritizes Tasks**: Supports dynamic task priority management for optimal resource utilization

## Architecture

### Core Components

1. **CentralScheduler Class**: Main orchestrator class providing all scheduling functionality
2. **TaskDefinition**: Data structure defining task parameters, dependencies, and retry configuration
3. **TaskExecution**: Tracking structure for monitoring task execution state and history
4. **Priority Management**: Dynamic priority adjustment based on market conditions and system state
5. **Dependency Resolution**: DAG-based dependency checking with cycle detection

### Integration Points

- **Risk Management System**: Receives market data and risk assessments for dynamic scheduling
- **Capital Allocation Engine**: Gets allocation decisions and rebalancing instructions
- **Protocol Modules**: Executes specific airdrop tasks (bridging, swapping, lending, etc.)

## Key Features

### Scheduling Engine

- **Multiple Trigger Types**:
  - `CronTrigger`: Regular recurring tasks (daily, weekly, monthly)
  - `DateTrigger`: One-time tasks scheduled for specific times
  - `IntervalTrigger`: Fixed interval execution
  - Event-driven triggers (future enhancement)

### Task Management

- **Atomic Task Definition**: Each task represents a specific, atomic action
- **Configurable Parameters**: Protocol ID, action type, asset, amount, target wallet, gas settings
- **Task Catalog**: Registry of defined task types and execution logic
- **State Persistence**: Maintains task state across scheduler restarts

### Dependency Management

- **DAG Implementation**: Directed Acyclic Graph for task dependencies
- **Cycle Detection**: Prevents circular dependencies
- **Prerequisite Checking**: Ensures dependencies are completed before task execution
- **Dynamic Updates**: Allows runtime modification of dependency relationships

### Market & Risk Awareness

- **Gas Price Monitoring**: Delays tasks when gas prices exceed thresholds
- **Volatility Response**: Reduces task frequency during high market volatility
- **Circuit Breaker Integration**: Halts operations when risk limits are exceeded
- **Dynamic Adjustment**: Real-time schedule modification based on conditions

### Error Handling & Retry Logic

- **Exponential Backoff**: Configurable retry delays with exponential increase
- **Jitter Addition**: Prevents thundering herd problems
- **Retry Limits**: Configurable maximum retry attempts per task
- **Failure Escalation**: Permanent failure handling and notification
- **Error Logging**: Comprehensive error tracking and reporting

## Usage Examples

### Basic Task Scheduling

```python
from airdrops.scheduler.bot import CentralScheduler, TaskPriority

# Initialize scheduler
scheduler = CentralScheduler({
    "max_concurrent_jobs": 5,
    "default_retry_delay": 60.0,
    "max_gas_price": 100
})

# Start scheduler
scheduler.start()

# Add daily bridge task
scheduler.add_job(
    task_id="daily_eth_bridge",
    func=bridge_eth_to_scroll,
    trigger="cron",
    hour=10,
    minute=0,
    args=(100,),  # 100 ETH
    kwargs={"slippage": 0.01},
    priority=TaskPriority.HIGH
)

# Add interval-based monitoring
scheduler.add_job(
    task_id="portfolio_check",
    func=check_portfolio_status,
    trigger="interval",
    minutes=15,
    priority=TaskPriority.NORMAL
)
```

### Dependency Management

```python
# Add tasks with dependencies
scheduler.add_job(
    task_id="approve_tokens",
    func=approve_erc20_tokens,
    trigger="cron",
    hour=9,
    minute=30
)

scheduler.add_job(
    task_id="bridge_after_approval",
    func=bridge_tokens,
    trigger="cron",
    hour=10,
    minute=0,
    dependencies={"approve_tokens"}  # Wait for approval
)

# Update dependencies dynamically
scheduler.manage_task_dependencies(
    "complex_swap",
    {"approve_tokens", "bridge_after_approval"}
)
```

### Dynamic Scheduling

```python
# Market condition response
market_data = {
    "gas_price": 150,  # High gas price
    "volatility": "high"
}

risk_assessment = {
    "circuit_breaker": False,
    "risk_score": 0.7
}

# Adjust scheduling based on conditions
scheduler.schedule_dynamically(market_data, risk_assessment)
```

### Priority Management

```python
# Adjust task priority based on conditions
scheduler.manage_task_priority(
    "urgent_rebalance",
    TaskPriority.CRITICAL
)
```

## Configuration

### Scheduler Configuration

```python
config = {
    "max_concurrent_jobs": 5,        # Maximum parallel tasks
    "default_retry_delay": 60.0,     # Base retry delay (seconds)
    "default_max_retries": 3,        # Default retry attempts
    "max_gas_price": 100,            # Gas price threshold (gwei)
    "volatility_threshold": "medium", # Volatility response level
    "circuit_breaker_timeout": 3600   # CB timeout (seconds)
}
```

### Task Configuration

```python
task_config = {
    "max_retries": 5,           # Task-specific retry limit
    "retry_delay": 120.0,       # Task-specific retry delay
    "timeout": 300.0,           # Task execution timeout
    "priority": TaskPriority.HIGH,
    "dependencies": {"task1", "task2"},
    "metadata": {
        "protocol": "scroll",
        "action_type": "bridge"
    }
}
```

## Command Line Interface

The scheduler can be run as a standalone service:

```bash
# Run scheduler continuously
python -m airdrops.scheduler.bot

# Run once and exit
python -m airdrops.scheduler.bot --once

# Dry run mode (testing)
python -m airdrops.scheduler.bot --dry-run

# With custom configuration
python -m airdrops.scheduler.bot --config /path/to/config.json
```

## Integration with Other Modules

### Risk Management Integration

```python
# The scheduler automatically integrates with risk management
from airdrops.risk_management.core import RiskManager

risk_manager = RiskManager()
risk_data = risk_manager.assess_current_risk()

# Scheduler uses this data for dynamic adjustments
scheduler.schedule_dynamically(market_data, risk_data)
```

### Capital Allocation Integration

```python
# Scheduler receives allocation instructions
from airdrops.capital_allocation.engine import CapitalAllocator

allocator = CapitalAllocator()
allocations = allocator.optimize_portfolio(protocols, total_capital)

# Tasks are scheduled based on allocation decisions
for protocol, allocation in allocations.items():
    scheduler.add_job(
        task_id=f"allocate_{protocol}",
        func=deploy_capital,
        args=(protocol, allocation.amount),
        priority=allocation.priority
    )
```

## Monitoring and Logging

The scheduler provides comprehensive logging and monitoring:

- **Task Execution Logs**: Start/end times, success/failure status
- **Dependency Resolution**: Logs dependency checking and resolution
- **Retry Attempts**: Detailed retry logging with backoff calculations
- **Market Response**: Logs dynamic scheduling adjustments
- **Performance Metrics**: Task execution times and success rates

## Error Handling

### Common Error Scenarios

1. **Network Failures**: Automatic retry with exponential backoff
2. **Gas Price Spikes**: Task delay until prices normalize
3. **Dependency Failures**: Dependent tasks are automatically cancelled
4. **Circuit Breaker Activation**: All tasks paused until conditions improve
5. **Resource Exhaustion**: Task queuing and priority-based execution

### Recovery Mechanisms

- **State Persistence**: Task state survives scheduler restarts
- **Graceful Shutdown**: Completes running tasks before stopping
- **Failure Escalation**: Permanent failures trigger notifications
- **Manual Intervention**: Admin interface for task management

## Future Enhancements

- **Advanced DAG Visualization**: Web-based dependency graph viewer
- **Machine Learning Integration**: Predictive scheduling based on historical data
- **Multi-Instance Coordination**: Distributed scheduler deployment
- **Real-time Monitoring Dashboard**: Live task execution monitoring
- **Advanced Retry Strategies**: Custom retry logic per task type
- **Event-Driven Triggers**: React to external events (price movements, protocol updates)

## Security Considerations

- **Input Validation**: All task parameters are validated before execution
- **Secret Management**: No secrets are logged or stored in task definitions
- **Access Control**: Task execution permissions and restrictions
- **Audit Trail**: Complete execution history for compliance and debugging

## Performance Characteristics

- **Scalability**: Handles hundreds of concurrent tasks efficiently
- **Memory Usage**: O(n) where n is the number of active tasks
- **CPU Usage**: Minimal overhead for scheduling operations
- **Network Impact**: Batches operations to minimize RPC calls
- **Storage**: Persistent state storage for reliability

The Central Scheduler provides a robust, flexible foundation for orchestrating complex airdrop farming operations while maintaining safety, efficiency, and reliability.