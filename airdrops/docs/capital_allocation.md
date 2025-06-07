# Capital Allocation Engine

## Overview

The Capital Allocation Engine is a core component of the airdrop automation system that provides sophisticated portfolio optimization, risk-adjusted capital allocation, and dynamic rebalancing capabilities. It integrates seamlessly with the Risk Management System to ensure safe and efficient capital deployment across multiple airdrop protocols.

## Purpose

The Capital Allocation Engine serves several critical functions:

1. **Portfolio Optimization**: Implements multiple allocation strategies to optimize capital distribution across available airdrop protocols
2. **Risk-Adjusted Allocation**: Dynamically adjusts capital allocation based on real-time risk assessments from the Risk Management System
3. **Dynamic Rebalancing**: Monitors portfolio drift and generates rebalancing orders to maintain target allocations
4. **Performance Tracking**: Calculates comprehensive efficiency metrics including ROI, Sharpe ratio, and maximum drawdown

## Architecture

### Core Components

#### CapitalAllocator Class
The main class that orchestrates all capital allocation activities:

- **Portfolio Optimization**: Multiple strategies including equal weight, risk parity, and mean-variance optimization
- **Risk Integration**: Real-time integration with Risk Management System for dynamic risk adjustments
- **Rebalancing Logic**: Automated detection of portfolio drift and generation of rebalancing orders
- **Performance Analytics**: Comprehensive calculation of portfolio efficiency metrics

#### Allocation Strategies
- **Equal Weight**: Simple equal distribution across all protocols
- **Risk Parity**: Allocation based on inverse risk scores to achieve equal risk contribution
- **Mean Variance**: Optimization based on expected returns and risk scores
- **Kelly Criterion**: (Future implementation) Optimal bet sizing based on win probability

#### Data Classes
- **AllocationTarget**: Represents target allocations with risk and return metrics
- **PortfolioMetrics**: Comprehensive portfolio performance metrics
- **RebalanceOrder**: Structured rebalancing instructions with priority ordering

## Key Features

### 1. Multi-Strategy Portfolio Optimization

The engine supports multiple allocation strategies that can be configured based on market conditions and risk preferences:

```python
# Equal weight allocation
allocator = CapitalAllocator({"strategy": "equal_weight"})

# Risk parity allocation
allocator = CapitalAllocator({"strategy": "risk_parity"})

# Mean-variance optimization
allocator = CapitalAllocator({"strategy": "mean_variance"})
```

### 2. Risk-Adjusted Capital Allocation

Real-time integration with the Risk Management System ensures that capital allocation respects current risk conditions:

- **Volatility Adjustments**: Reduces allocation during high volatility periods
- **Gas Price Sensitivity**: Adjusts allocation based on current gas price conditions
- **Circuit Breaker Integration**: Immediately halts allocation when circuit breakers are triggered

### 3. Dynamic Rebalancing

Automated portfolio rebalancing maintains target allocations while minimizing transaction costs:

- **Threshold-Based Triggering**: Only rebalances when deviations exceed configurable thresholds
- **Priority Ordering**: Prioritizes rebalancing actions based on deviation magnitude
- **Cost Consideration**: Factors in transaction costs when determining rebalancing necessity

### 4. Comprehensive Performance Metrics

Tracks and reports detailed portfolio performance metrics:

- **Total Return**: Cumulative portfolio performance
- **Sharpe Ratio**: Risk-adjusted return measurement
- **Maximum Drawdown**: Worst-case loss from peak
- **Capital Utilization**: Percentage of capital actively deployed

## Integration with Risk Management System

The Capital Allocation Engine is designed to work in close coordination with the Risk Management System:

### Risk Constraint Enforcement
- Respects maximum protocol exposure limits
- Adheres to transaction size constraints
- Maintains asset concentration limits

### Real-Time Risk Adjustments
- Monitors volatility states and adjusts allocation accordingly
- Responds to gas price fluctuations
- Immediately halts allocation when circuit breakers are triggered

### Dynamic Risk Multipliers
The engine calculates risk multipliers based on current market conditions:

```python
# Normal conditions: 100% allocation
risk_multiplier = 1.0

# High volatility: 60% allocation
risk_multiplier = 0.6

# Circuit breaker active: 0% allocation
risk_multiplier = 0.0
```

## Configuration

The Capital Allocation Engine supports extensive configuration through environment variables:

### Core Settings
- `CAPITAL_RISK_FREE_RATE`: Risk-free rate for Sharpe ratio calculations (default: 0.02)
- `CAPITAL_REBALANCE_THRESHOLD`: Minimum deviation threshold for rebalancing (default: 0.10)
- `CAPITAL_MAX_PROTOCOLS`: Maximum number of protocols to allocate to (default: 10)

### Strategy-Specific Settings
- `CAPITAL_STRATEGY`: Default allocation strategy (default: "equal_weight")
- `CAPITAL_OPTIMIZATION_FREQUENCY`: How often to recalculate optimal allocations

## Usage Examples

### Basic Portfolio Optimization

```python
from airdrops.capital_allocation import CapitalAllocator

# Initialize allocator
allocator = CapitalAllocator()

# Define available protocols and constraints
protocols = ["scroll", "zksync", "eigenlayer"]
risk_constraints = {
    "max_protocol_exposure_pct": Decimal("20"),
    "max_transaction_size_pct": Decimal("5")
}

# Optimize portfolio
allocation = allocator.optimize_portfolio(protocols, risk_constraints)
print(f"Optimal allocation: {allocation}")
```

### Risk-Adjusted Capital Allocation

```python
# Get risk metrics from Risk Management System
risk_metrics = {
    "volatility_state": "medium",
    "gas_price_gwei": Decimal("75"),
    "circuit_breaker_triggered": False
}

# Allocate capital with risk adjustments
total_capital = Decimal("100000")
capital_amounts = allocator.allocate_risk_adjusted_capital(
    total_capital, allocation, risk_metrics
)
```

### Portfolio Rebalancing

```python
# Current and target allocations
current = {"scroll": Decimal("0.40"), "zksync": Decimal("0.60")}
target = {"scroll": Decimal("0.30"), "zksync": Decimal("0.70")}

# Generate rebalancing orders
orders = allocator.rebalance_portfolio(current, target, total_capital)

for order in orders:
    print(f"{order.action} {order.protocol} by ${order.amount}")
```

### Performance Analysis

```python
# Calculate portfolio metrics
portfolio_returns = [Decimal("0.02"), Decimal("0.01"), Decimal("-0.005")]
metrics = allocator.calculate_efficiency_metrics(portfolio_returns)

print(f"Total Return: {metrics.total_return:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
```

## Future Enhancements

### Advanced Optimization Algorithms
- Implementation of Kelly Criterion for optimal bet sizing
- Black-Litterman model for incorporating market views
- Multi-objective optimization considering multiple risk factors

### Machine Learning Integration
- Predictive models for expected returns estimation
- Reinforcement learning for dynamic strategy selection
- Anomaly detection for unusual market conditions

### Enhanced Risk Integration
- Real-time correlation analysis between protocols
- Dynamic risk factor modeling
- Stress testing and scenario analysis

## Dependencies

The Capital Allocation Engine relies on the following key dependencies:

- **numpy**: For numerical computations and optimization algorithms
- **decimal**: For precise financial calculations
- **Risk Management System**: For real-time risk assessments and constraints

## Testing

The module includes comprehensive test coverage:

- **Unit Tests**: Individual method testing with various scenarios
- **Integration Tests**: Testing interaction with Risk Management System
- **Performance Tests**: Validation of optimization algorithm efficiency
- **Edge Case Tests**: Handling of extreme market conditions and error scenarios

## Security Considerations

- **Input Validation**: All external inputs are validated before processing
- **Logging**: Comprehensive logging without exposing sensitive information
- **Error Handling**: Graceful handling of exceptions with appropriate error messages
- **Configuration Security**: Sensitive configuration through environment variables only