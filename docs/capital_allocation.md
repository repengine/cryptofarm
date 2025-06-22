# Capital Allocation Module

## Overview
The capital allocation module provides sophisticated portfolio management and risk-adjusted capital distribution across multiple DeFi protocols and strategies.

## Core Components

### CapitalAllocator (`src/airdrops/capital_allocation/engine.py`)
Main engine for capital allocation decisions and portfolio management.

**Key Features:**
- Multiple allocation strategies (Equal Weight, Risk Parity, Mean Variance)
- Risk-adjusted position sizing
- Dynamic rebalancing capabilities
- Integration with multiple DeFi protocols

**Configuration:**
- `ALLOCATION_STRATEGY`: Strategy type (default: EQUAL_WEIGHT)
- `MAX_POSITION_SIZE`: Maximum position size as decimal (default: 0.25)
- `REBALANCE_THRESHOLD`: Threshold for triggering rebalancing (default: 0.05)
- `RISK_FREE_RATE`: Risk-free rate for calculations (default: 0.02)

**Dependencies:**
- Risk Manager: Portfolio risk assessment and management
- Scroll Protocol: Layer 2 DeFi operations
- LayerZero Protocol: Cross-chain operations
- zkSync Protocol: Layer 2 scaling operations

## Testing

### Test Coverage
Comprehensive unit tests for the `CapitalAllocator` class:
- **Location**: `tests/capital_allocation/test_engine.py`
- **Coverage**: 56 test cases covering complete functionality
- **Test Categories**:
  - Initialization with various configurations (18 tests)
  - Portfolio optimization algorithms (15 tests)
  - Individual allocation strategies (15 tests)
  - Edge cases and error handling (8 tests)

### Key Test Scenarios
1. **Initialization Testing**: Default and custom configurations, environment variables, error handling
2. **Portfolio Optimization**: All three strategies (Equal-Weight, Risk-Parity, Mean-Variance) with various constraints
3. **Strategy-Specific Testing**: Detailed testing of each allocation algorithm with edge cases
4. **Integration Testing**: Dependency injection and protocol interface compatibility
5. **Error Handling**: Invalid parameters, runtime errors, and boundary conditions

## Architecture

### Allocation Strategies
- **EQUAL_WEIGHT**: Distributes capital equally across all positions
- **RISK_PARITY**: Allocates based on risk contribution parity
- **MEAN_VARIANCE**: Optimizes risk-return trade-off using modern portfolio theory

### Risk Management Integration
- Real-time risk monitoring and assessment
- Position size limits and concentration controls
- Dynamic risk-adjusted rebalancing

### Protocol Integration
- **Scroll**: Layer 2 DeFi operations and yield farming
- **LayerZero**: Cross-chain asset transfers and arbitrage
- **zkSync**: Scalable DeFi operations and liquidity provision

## Usage Examples

### Basic Initialization
```python
from airdrops.capital_allocation.engine import CapitalAllocator, AllocationStrategy

# Default configuration
allocator = CapitalAllocator()

# Custom strategy
allocator = CapitalAllocator({
    'allocation_strategy': AllocationStrategy.RISK_PARITY,
    'max_position_size': '0.20',
    'rebalance_threshold': '0.03'
})
```

### Portfolio Optimization
```python
# Optimize portfolio across protocols
protocols = ['scroll', 'zksync', 'layerzero']
risk_constraints = {
    'max_position_size': 0.25,
    'rebalance_threshold': 0.05
}
risk_scores = {
    'scroll': Decimal('0.3'),
    'zksync': Decimal('0.4'),
    'layerzero': Decimal('0.5')
}

allocations = allocator.optimize_portfolio(
    protocols=protocols,
    risk_constraints=risk_constraints,
    risk_scores=risk_scores
)
```

### Portfolio Rebalancing
```python
# Generate rebalancing orders
current_allocations = {
    'scroll': Decimal('0.4'),
    'zksync': Decimal('0.6')
}
target_allocations = {
    'scroll': Decimal('0.5'),
    'zksync': Decimal('0.5')
}
total_value = Decimal('10000')

rebalance_orders = allocator.rebalance_portfolio(
    current_allocations=current_allocations,
    target_allocations=target_allocations,
    total_portfolio_value=total_value
)
```

### Environment Configuration
```bash
export ALLOCATION_STRATEGY=MEAN_VARIANCE
export MAX_POSITION_SIZE=0.30
export REBALANCE_THRESHOLD=0.04
export RISK_FREE_RATE=0.025
```

## Future Enhancements
- Machine learning-based allocation strategies
- Real-time market data integration
- Advanced risk metrics and monitoring
- Cross-chain yield optimization
- Automated rebalancing triggers

## Related Documentation
- [Risk Management](risk_management.md)
- [Scroll Protocol](protocols/scroll.md)
- [System Monitoring](monitoring.md)