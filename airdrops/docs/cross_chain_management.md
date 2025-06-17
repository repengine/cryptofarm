# Cross-Chain Capital Management

## Overview

The Cross-Chain Capital Management module provides automated cross-chain capital rebalancing capabilities for the airdrop farming system. This foundational implementation establishes the core data models and management infrastructure for orchestrating capital movements across multiple blockchain networks.

## Architecture

The module is built around four core components:

### Data Models

- **Chain**: Represents blockchain network configurations including chain ID, RPC endpoints, and metadata
- **Wallet**: Manages multi-chain wallet addresses for cross-chain operations
- **RebalancingJob**: Tracks the lifecycle of cross-chain capital transfer operations

### BridgeAdapter Framework

A unified interface for cross-chain bridging operations that provides:
- **BridgeAdapter**: Abstract base class defining the standard interface for all bridge protocols
- **LayerZeroBridgeAdapter**: Implementation for LayerZero cross-chain protocol
- **ZkSyncBridgeAdapter**: Implementation for ZkSync L1/L2 bridging
- **ScrollBridgeAdapter**: Implementation for Scroll L1/L2 bridging

### CrossChainManager

The central orchestrator class that manages:
- Chain and wallet configurations
- Liquidity threshold monitoring
- Bridge adapter selection and coordination
- Rebalancing job initiation and tracking
- Status reporting and job management

## Current Implementation Status

The cross-chain capital management system now includes full BridgeAdapter integration:

✅ **Completed:**
- Core data models with full validation
- BridgeAdapter interface and concrete implementations
- CrossChainManager with dynamic adapter selection
- LayerZero, ZkSync, and Scroll bridge integrations
- Comprehensive test coverage including adapter integration tests
- Type safety with mypy compliance
- Production-ready error handling and logging

🚧 **To Do:**
- Integration with capital allocation engine
- Real-time liquidity monitoring
- Cost estimation and optimization
- Additional bridge protocol integrations (Stargate, Wormhole, etc.)
- Production deployment configuration

## Risk Management and Alerting Integration

The CrossChainManager now integrates with the Risk Management System and Alerting infrastructure to ensure all rebalancing operations are risk-aware and properly monitored.

### Features

- **Risk Assessment**: Before initiating any rebalancing operation, the system checks the current risk level
- **Risk-Based Postponement**: Operations are automatically postponed when risk levels are HIGH or EXTREME
- **Real-time Alerts**: Comprehensive alerting for successful operations, failures, and risk-based postponements
- **Fail-Open Design**: If risk assessment fails, operations continue to prevent system lockup
- **Graceful Degradation**: Alert failures don't interrupt rebalancing operations

### Configuration

```python
from airdrops.cross_chain.manager import CrossChainManager
from airdrops.risk_management.core import RiskManager
from airdrops.monitoring.alerter import Alerter
from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol

# Initialize components
risk_manager = RiskManager()
alerter = Alerter()
alerter.load_alert_rules("config/alert_rules.yaml")
alerter.load_notification_channels("config/notifications.yaml")

# Initialize protocol and adapter
layerzero_protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
layerzero_adapter = LayerZeroBridgeAdapter(layerzero_protocol)

# Initialize CrossChainManager with risk management and alerting
manager = CrossChainManager(
    bridge_adapters=[layerzero_adapter],
    risk_manager=risk_manager,
    alerter=alerter
)
```

### Risk-Aware Operations

```python
# This operation will be risk-assessed before execution
try:
    job = manager.initiate_rebalancing(
        "ethereum", "arbitrum", "USDC", Decimal("1000"),
        "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
    )
    print(f"Rebalancing initiated: {job.job_id}")
except RuntimeError as e:
    if "postponed due to" in str(e):
        print(f"Operation postponed: {e}")
        # Implement retry logic or manual intervention
    else:
        print(f"Operation failed: {e}")
```

### Alert Types

The system generates three types of alerts:

1. **Success Alerts** (Severity: LOW)
   - Sent when rebalancing operations complete successfully
   - Include transaction hash and job details

2. **Failure Alerts** (Severity: CRITICAL)
   - Sent when rebalancing operations fail
   - Include error details and job information

3. **Postponement Alerts** (Severity: MEDIUM)
   - Sent when operations are postponed due to high risk
   - Include risk level and operation details

### Risk Level Behavior

| Risk Level | Behavior |
|------------|----------|
| LOW | Operations proceed normally |
| MEDIUM | Operations proceed normally |
| HIGH | Operations are postponed |
| EXTREME | Operations are postponed |

### Optional Components

Both risk management and alerting are optional:

```python
# Manager without risk management (alerts only)
manager = CrossChainManager([adapter], None, alerter)

# Manager without alerting (risk management only)
manager = CrossChainManager([adapter], risk_manager, None)

# Manager without either (basic functionality)
manager = CrossChainManager([adapter])
```

## Scheduler Integration

The CrossChainManager now integrates seamlessly with the AirdropSchedulerBot to enable automated, periodic liquidity checks and rebalancing:

### Configuration

```python
from airdrops.scheduler.bot import AirdropSchedulerBot
from airdrops.cross_chain.manager import CrossChainManager
from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
from decimal import Decimal

# Initialize CrossChainManager with bridge adapters
layerzero_protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
layerzero_adapter = LayerZeroBridgeAdapter(layerzero_protocol)
cross_chain_manager = CrossChainManager([layerzero_adapter])

# Set up liquidity thresholds
thresholds = {"ethereum": Decimal("1000"), "arbitrum": Decimal("500")}
cross_chain_manager.set_liquidity_thresholds(thresholds)

# Initialize scheduler with CrossChainManager
scheduler = AirdropSchedulerBot(
    config={"scheduler": {"max_concurrent_tasks": 5}},
    cross_chain_manager=cross_chain_manager
)

# Start scheduler and enable automated rebalancing checks
scheduler.start()
scheduler.schedule_rebalancing_checks(2.0)  # Check every 2 hours
```

### Features

- **Automated Monitoring**: Periodic execution of liquidity threshold checks
- **Configurable Intervals**: Set check frequency from minutes to hours
- **High Priority Scheduling**: Rebalancing checks are prioritized in the task queue
- **Error Handling**: Built-in retry logic for failed monitoring tasks
- **Logging Integration**: Comprehensive logging of all rebalancing activities

### Usage Patterns

```python
# Hourly checks for active trading
scheduler.schedule_rebalancing_checks(1.0)

# Every 30 minutes for high-frequency operations
scheduler.schedule_rebalancing_checks(0.5)

# Daily checks for conservative strategies
scheduler.schedule_rebalancing_checks(24.0)

# Update check frequency dynamically
scheduler.schedule_rebalancing_checks(4.0)  # Replaces existing schedule
```

## Usage Example

```python
from airdrops.cross_chain import CrossChainManager, Chain, Wallet
from airdrops.cross_chain.adapters.layerzero_adapter import LayerZeroBridgeAdapter
from airdrops.cross_chain.adapters.zksync_adapter import ZkSyncBridgeAdapter
from airdrops.cross_chain.adapters.scroll_adapter import ScrollBridgeAdapter
from airdrops.protocols.layerzero.layerzero import LayerZeroProtocol
from airdrops.protocols.zksync.zksync import ZkSyncProtocol
from airdrops.risk_management.core import RiskManager
from airdrops.monitoring.alerter import Alerter
from decimal import Decimal
from web3 import Web3

# Initialize risk management and alerting
risk_manager = RiskManager()
alerter = Alerter()
alerter.load_alert_rules("config/alert_rules.yaml")
alerter.load_notification_channels("config/notifications.yaml")

# Initialize bridge adapters
layerzero_protocol = LayerZeroProtocol("https://eth.llamarpc.com", "0x...", 1)
layerzero_adapter = LayerZeroBridgeAdapter(layerzero_protocol)

zksync_protocol = ZkSyncProtocol(
    "https://eth.llamarpc.com",
    "https://mainnet.era.zksync.io",
    "0x..."
)
zksync_adapter = ZkSyncBridgeAdapter(zksync_protocol)

web3_l1 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
web3_l2 = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))
scroll_adapter = ScrollBridgeAdapter(web3_l1, web3_l2, "0x...")

# Initialize manager with bridge adapters, risk management, and alerting
manager = CrossChainManager(
    [layerzero_adapter, zksync_adapter, scroll_adapter],
    risk_manager,
    alerter
)

# Add chain configurations
eth_chain = Chain("Ethereum", 1, "https://eth-mainnet.alchemyapi.io/v2/key")
arbitrum_chain = Chain("Arbitrum", 42161, "https://arb-mainnet.alchemyapi.io/v2/key")
zksync_chain = Chain("ZkSync", 324, "https://mainnet.era.zksync.io")

manager.add_chain(eth_chain)
manager.add_chain(arbitrum_chain)
manager.add_chain(zksync_chain)

# Add wallet configuration
wallet = Wallet("Main", {
    "ethereum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
    "arbitrum": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87",
    "zksync": "0x742d35Cc6634C0532925a3b8D4C9db96590c6C87"
})
manager.add_wallet(wallet)

# Set liquidity thresholds
thresholds = {
    "ethereum": Decimal("1000"),
    "arbitrum": Decimal("500"),
    "zksync": Decimal("300")
}
manager.set_liquidity_thresholds(thresholds)

# Initiate rebalancing - manager automatically selects appropriate adapter
job1 = manager.initiate_rebalancing(
    "ethereum", "arbitrum", "USDC", Decimal("1000")
)  # Uses LayerZero adapter

job2 = manager.initiate_rebalancing(
    "ethereum", "zksync", "ETH", Decimal("0.5")
)  # Uses ZkSync adapter

job3 = manager.initiate_rebalancing(
    "ethereum", "scroll", "ETH", Decimal("0.3")
)  # Uses Scroll adapter

# Check job status
status1 = manager.get_rebalancing_status(job1.job_id)
status2 = manager.get_rebalancing_status(job2.job_id)
status3 = manager.get_rebalancing_status(job3.job_id)

print(f"LayerZero job status: {status1}")
print(f"ZkSync job status: {status2}")
print(f"Scroll job status: {status3}")
```

## BridgeAdapter Framework

The BridgeAdapter framework provides a unified interface for cross-chain bridging operations:

### Key Features

- **Protocol Abstraction**: Standardized interface across different bridge protocols
- **Dynamic Selection**: Automatic adapter selection based on source/destination chains and assets
- **Error Handling**: Robust error handling with proper exception propagation
- **Extensibility**: Easy addition of new bridge protocols through the adapter pattern

### Supported Protocols

1. **LayerZero**: Multi-chain protocol supporting Ethereum, Arbitrum, Optimism
2. **ZkSync**: L1/L2 bridging between Ethereum and ZkSync Era
3. **Scroll**: L1/L2 bridging between Ethereum and Scroll

### Adding New Bridge Protocols

To add support for a new bridge protocol:

1. Create a new adapter class inheriting from `BridgeAdapter`
2. Implement all abstract methods (`get_supported_chains`, `get_supported_assets`, `estimate_bridge_fee`, `bridge_assets`)
3. Add comprehensive tests following the existing adapter test patterns
4. Register the adapter with the `CrossChainManager`

## Testing

The module includes comprehensive test coverage with:
- Unit tests for all data models
- Validation testing for edge cases
- CrossChainManager functionality tests
- BridgeAdapter integration tests
- Mock adapter testing for all supported protocols
- Error handling and type safety tests

Run tests with:
```bash
pytest airdrops/tests/cross_chain/ -v
```

## Future Development

The cross-chain capital management system is now production-ready with full BridgeAdapter integration. Next development phases will focus on:

1. Integration with existing capital allocation engine
2. Real-time balance monitoring and threshold alerts
3. Cost optimization algorithms and fee estimation
4. Additional bridge protocol integrations (Stargate, Wormhole, Hyperlane)
5. Advanced routing and multi-hop bridging
6. Production deployment configuration and monitoring

## Related Documentation

- [Cross-Chain Capital Management Plan](../planning/cross-chain-capital-management.md)
- [Capital Allocation Engine](capital_allocation.md)
- [LayerZero Protocol Integration](protocols/layerzero.md)
- [ZkSync Protocol Integration](protocols/zksync.md)
- [Scroll Protocol Integration](protocols/scroll.md)
- [Bridge Adapter Documentation](cross_chain/scroll_adapter.md)