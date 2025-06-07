# Analytics Module Documentation

## Overview

The Analytics module provides comprehensive airdrop tracking and reporting capabilities for the airdrop automation system. It consists of three main components:

1.  **AirdropTracker**: Records and retrieves airdrop events with database persistence
2.  **AirdropReporter**: Generates detailed analytics reports with multiple export formats
3.  **ROIOptimizer**: Calculates Return on Investment (ROI) metrics and provides optimization suggestions

## Architecture

### Database Schema

The module uses SQLAlchemy with SQLite for data persistence:

```sql
CREATE TABLE airdrop_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_name VARCHAR(100) NOT NULL,
    token_symbol VARCHAR(20) NOT NULL,
    amount_received NUMERIC(36,18) NOT NULL,
    estimated_value_usd NUMERIC(20,8),
    wallet_address VARCHAR(42) NOT NULL,
    transaction_hash VARCHAR(66) UNIQUE,
    block_number INTEGER,
    event_date DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    notes TEXT
);
```

### Data Models

#### AirdropEvent (Pydantic)
```python
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

class AirdropEvent(BaseModel):
    protocol_name: str = Field(..., min_length=1, max_length=100)
    token_symbol: str = Field(..., min_length=1, max_length=20)
    amount_received: Decimal = Field(..., gt=0)
    estimated_value_usd: Optional[Decimal] = Field(None, ge=0)
    wallet_address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    transaction_hash: Optional[str] = Field(None, pattern=r"^0x[a-fA-F0-9]{64}$")
    block_number: Optional[int] = Field(None, ge=0)
    event_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('protocol_name')
    def validate_protocol_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Protocol name cannot be empty")
        return v.strip().title()

    @field_validator('token_symbol')
    def validate_token_symbol(cls, v: str) -> str:
        return v.strip().upper()
```

#### ProtocolSummary (Pydantic)
```python
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

class ProtocolSummary(BaseModel):
    protocol_name: str
    total_events: int
    total_tokens_received: Decimal
    total_estimated_value_usd: Optional[Decimal]
    unique_tokens: List[str]
    first_airdrop_date: Optional[datetime]
    last_airdrop_date: Optional[datetime]
```

#### AirdropReport (Pydantic)
```python
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

class AirdropReport(BaseModel):
    report_generated_at: datetime
    total_airdrops: int
    total_protocols: int
    total_estimated_value_usd: Optional[Decimal]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    protocol_summaries: List[ProtocolSummary]
    top_protocols_by_value: List[Dict[str, Union[str, Decimal, int]]]
    monthly_breakdown: List[Dict[str, Union[str, int, Decimal]]]
```

## Components

### AirdropTracker

The `AirdropTracker` class handles data persistence and retrieval:

#### Key Methods

- `record_airdrop(event: AirdropEvent) -> int`: Records a new airdrop event
- `get_airdrops_by_protocol(protocol_name: str) -> List[AirdropEvent]`: Retrieves events for a specific protocol
- `get_airdrops_by_wallet(wallet_address: str) -> List[AirdropEvent]`: Retrieves events for a specific wallet
- `get_airdrops_by_date_range(start_date: datetime, end_date: datetime) -> List[AirdropEvent]`: Retrieves events within a date range

#### Usage Example

```python
from airdrops.analytics import AirdropTracker, AirdropEvent
from datetime import datetime
from decimal import Decimal

# Initialize tracker
tracker = AirdropTracker()

# Record an event
event = AirdropEvent(
    protocol_name="Uniswap",
    token_symbol="UNI",
    amount_received=Decimal("400"),
    estimated_value_usd=Decimal("1200.50"),
    wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
    event_date=datetime.now()
)

event_id = tracker.record_airdrop(event)

# Retrieve events
protocol_events = tracker.get_airdrops_by_protocol("Uniswap")
wallet_events = tracker.get_airdrops_by_wallet("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
```

### AirdropReporter

The `AirdropReporter` class generates analytics reports and exports:

#### Key Methods

- `generate_comprehensive_report(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> AirdropReport`: Generates comprehensive analytics report
- `generate_protocol_report(protocol_name: str) -> ProtocolSummary`: Generates a detailed report for a specific protocol
- `export_report(report: AirdropReport, output_path: str, format_type: ReportFormat) -> None`: Exports report to file in specified format (JSON, CSV, CONSOLE)

#### Usage Example

```python
from airdrops.analytics import AirdropReporter, ReportFormat
from datetime import datetime, timedelta

# Initialize reporter
tracker = AirdropTracker() # Assuming tracker is initialized and has data
reporter = AirdropReporter(tracker)

# Generate report for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
report = reporter.generate_comprehensive_report(start_date, end_date)

# Export to different formats
reporter.export_report(report, "airdrop_report.json", ReportFormat.JSON)
reporter.export_report(report, "airdrop_report.csv", ReportFormat.CSV)
reporter.export_report(report, "", ReportFormat.CONSOLE)

# Get protocol report
uniswap_summary = reporter.generate_protocol_report("Uniswap")
```

## Error Handling

The module implements comprehensive error handling:

-   **Database Errors**: SQLAlchemy exceptions are caught and re-raised with context
-   **Validation Errors**: Pydantic validation ensures data integrity
-   **File I/O Errors**: Export operations handle file system errors gracefully

## Performance Considerations

-   **Database Indexing**: Indexes on `protocol_name`, `wallet_address`, and `event_date` for efficient queries
-   **Connection Pooling**: SQLAlchemy connection pooling for concurrent access
-   **Query Optimization**: Efficient queries with proper filtering and limiting

## Testing

The module includes comprehensive test coverage:

-   **Unit Tests**: Individual component testing
-   **Integration Tests**: Database integration testing
-   **Mock Testing**: External dependency mocking

## ROI Analysis and Optimization

### ROIOptimizer

The `ROIOptimizer` class provides advanced analytics for calculating Return on Investment and generating optimization suggestions.

#### Key Features

- **ROI Calculation**: Calculate ROI for individual protocols or entire portfolio
- **Cost Models**: Support for multiple cost calculation approaches (simple gas, manual input, estimated)
- **Optimization Strategies**: Generate suggestions based on different optimization approaches
- **Performance Analysis**: Analyze revenue per transaction, cost efficiency, and profit margins

#### Cost Models

The ROI optimizer supports three cost calculation models:

1. **Simple Gas Model**: Uses default or average gas costs per transaction
2. **Manual Input Model**: Allows manual specification of total costs
3. **Estimated Model**: Uses sophisticated cost estimation algorithms

#### Usage Example

```python
from airdrops.analytics import AirdropTracker, ROIOptimizer, CostData, CostModel
from decimal import Decimal

# Initialize tracker and optimizer
tracker = AirdropTracker()
optimizer = ROIOptimizer(
    tracker,
    default_gas_cost_usd=Decimal("5.0"),
    cost_model=CostModel.SIMPLE_GAS
)

# Set cost data for a protocol
cost_data = CostData(
    protocol_name="Uniswap",
    total_gas_cost_usd=Decimal("150.0"),
    transaction_count=30,
    average_gas_cost_usd=Decimal("5.0")
)
optimizer.set_protocol_cost_data(cost_data)

# Calculate ROI for a specific protocol
roi_metrics = optimizer.calculate_protocol_roi("Uniswap")
print(f"ROI: {roi_metrics.roi_percentage}%")
print(f"Profit: ${roi_metrics.profit_usd}")

# Calculate portfolio-wide ROI
portfolio_roi = optimizer.calculate_portfolio_roi()
for roi in portfolio_roi:
    print(f"{roi.protocol_name}: {roi.roi_percentage}% ROI")

# Generate optimization suggestions
suggestions = optimizer.generate_optimization_suggestions()
for suggestion in suggestions:
    print(f"{suggestion.priority}: {suggestion.description}")
```

#### ROI Metrics

The `ROIMetrics` model provides comprehensive ROI analysis:

```python
class ROIMetrics(BaseModel):
    protocol_name: str
    total_revenue_usd: Decimal
    total_cost_usd: Decimal
    roi_percentage: Decimal
    profit_usd: Decimal
    transaction_count: int
    revenue_per_transaction: Decimal
    cost_per_transaction: Decimal
    calculation_date: datetime
```

#### Optimization Strategies

The optimizer supports three optimization strategies:

1. **ROI Maximization**: Focus on protocols with highest returns
2. **Risk Adjusted**: Balance returns with consistency and transaction volume
3. **Diversified**: Promote portfolio diversification and reduce concentration risk

#### Integration with Reporter

The `AirdropReporter` can be enhanced with ROI analysis:

```python
from airdrops.analytics import AirdropReporter, ROIOptimizer

# Initialize reporter and optimizer
tracker = AirdropTracker()
reporter = AirdropReporter(tracker)
optimizer = ROIOptimizer(tracker)

# Enable ROI analysis in reports
reporter.enable_roi_analysis(optimizer)

# Generate comprehensive report with ROI analysis
report = reporter.generate_comprehensive_report(include_roi=True)

# ROI metrics and optimization suggestions are included in the report
if report.roi_metrics:
    for roi in report.roi_metrics:
        print(f"{roi.protocol_name}: {roi.roi_percentage}% ROI")

if report.optimization_suggestions:
    for suggestion in report.optimization_suggestions:
        print(f"Suggestion: {suggestion.description}")
```

### Cost Data Management

Cost data can be configured per protocol to improve ROI calculation accuracy:

```python
# Manual cost input
manual_cost = CostData(
    protocol_name="Arbitrum",
    manual_cost_usd=Decimal("200.0"),
    time_investment_hours=Decimal("15.5")
)

# Gas-based cost calculation
gas_cost = CostData(
    protocol_name="Uniswap",
    total_gas_cost_usd=Decimal("150.0"),
    transaction_count=30,
    average_gas_cost_usd=Decimal("5.0")
)

optimizer.set_protocol_cost_data(manual_cost)
optimizer.set_protocol_cost_data(gas_cost)
```

### Configuration Options

ROI analysis can be configured through various parameters:

- **Default Gas Cost**: Fallback cost per transaction when no specific cost data is available
- **Cost Model**: Choose between simple gas, manual input, or estimated cost models
- **ROI Threshold**: Minimum ROI threshold for optimization suggestions
- **Optimization Strategy**: Select the optimization approach that fits your investment strategy

## Security

-   **Input Validation**: All inputs validated through Pydantic models
-   **SQL Injection Prevention**: SQLAlchemy ORM prevents SQL injection
-   **Data Sanitization**: Sensitive data handling and sanitization
-   **Access Control**: Database access through controlled interfaces
-   **Cost Data Protection**: Sensitive cost information handled securely

## Predictive Analytics

### AirdropPredictor

The `AirdropPredictor` class provides foundational predictive analytics capabilities for airdrop timing predictions.

#### Key Features

- **Historical Pattern Analysis**: Analyzes past airdrop events to identify timing patterns
- **Data Source Integration**: Interfaces for market data, on-chain activity, and social sentiment (stubs for future implementation)
- **Heuristic Prediction Models**: Basic algorithms for timing prediction based on historical data
- **Confidence Scoring**: Prediction confidence levels based on data availability and quality
- **Extensible Architecture**: Designed for future machine learning model integration

#### Data Sources

The predictor supports multiple data source types through stub interfaces:

1. **Historical Airdrops**: Uses `AirdropTracker` for past airdrop event data
2. **Market Data**: Token price and trading volume data (stub implementation)
3. **On-Chain Activity**: Protocol transaction counts and active addresses (stub implementation)
4. **Social Sentiment**: Community sentiment scores and mention counts (stub implementation)

#### Usage Example

```python
from airdrops.analytics import AirdropTracker, AirdropPredictor

# Initialize tracker and predictor
tracker = AirdropTracker()
predictor = AirdropPredictor(tracker)

# Generate prediction for a protocol
prediction = predictor.predict_airdrop_timing("Arbitrum")

# Access prediction results
print(f"Protocol: {prediction.protocol_name}")
print(f"Confidence: {prediction.confidence_level}")

for window in prediction.prediction_windows:
    print(f"Window: {window.start_date} to {window.end_date}")
    print(f"Probability: {window.probability}")

# Check data source availability
status = predictor.get_data_source_status()
print(f"Historical data available: {status['historical_airdrops']}")
```

#### Prediction Models

The predictor currently implements a heuristic model that:

1. **Analyzes Historical Patterns**: Calculates average intervals between past airdrops
2. **Generates Time Windows**: Predicts future windows based on historical cadence
3. **Assigns Confidence Levels**: Determines confidence based on data availability
4. **Provides Default Patterns**: Uses typical airdrop patterns when no historical data exists

#### Prediction Output

Predictions are structured using Pydantic models:

```python
class PredictionResult(BaseModel):
    protocol_name: str
    prediction_windows: List[PredictionWindow]
    confidence_level: PredictionConfidence
    model_version: str
    data_sources_used: List[DataSourceType]
    prediction_date: datetime
    next_review_date: datetime
    metadata: Optional[Dict[str, Union[str, int, float]]]

class PredictionWindow(BaseModel):
    start_date: datetime
    end_date: datetime
    probability: Decimal  # 0.0 to 1.0
```

#### Confidence Levels

- **LOW**: No historical data available, using default patterns
- **MEDIUM**: 1-2 historical events available for analysis
- **HIGH**: 3+ historical events providing strong pattern recognition

#### Future Enhancements

The predictive analytics module is designed for future expansion:

- **Machine Learning Models**: Integration with scikit-learn or other ML frameworks
- **Real Data Sources**: Implementation of actual market data and on-chain activity APIs
- **Advanced Features**: Seasonal analysis, market condition correlation, multi-protocol predictions
- **Model Training**: Automated model retraining based on new airdrop events

#### Configuration

Predictive analytics can be configured through various parameters:

- **Lookback Period**: Number of days to analyze for historical patterns (default: 365)
- **Model Version**: Tracking of prediction model versions for reproducibility
- **Data Source Priorities**: Weighting of different data sources in predictions
- **Review Intervals**: Automatic scheduling of prediction updates

### Integration with Existing Analytics

The predictor integrates seamlessly with existing analytics components:

```python
# Combined analytics workflow
tracker = AirdropTracker()
reporter = AirdropReporter(tracker)
optimizer = ROIOptimizer(tracker)
predictor = AirdropPredictor(tracker)

# Generate comprehensive analysis
report = reporter.generate_comprehensive_report()
roi_metrics = optimizer.calculate_portfolio_roi()
predictions = predictor.predict_airdrop_timing("Protocol")

# Use predictions to inform strategy
for prediction in predictions.prediction_windows:
    if prediction.probability > 0.5:
        print(f"High probability window: {prediction.start_date}")
```

## Portfolio Performance Analytics

### PortfolioPerformanceAnalyzer

The `PortfolioPerformanceAnalyzer` class provides comprehensive portfolio performance analysis for airdrop activities, including value tracking, diversification metrics, and benchmark comparisons.

#### Key Features

- **Portfolio Value Tracking**: Calculate total portfolio value over time
- **Profit/Loss Analysis**: Track total P&L and ROI across all airdrops
- **Diversification Metrics**: Measure portfolio diversification using Herfindahl-Hirschman Index
- **Benchmark Comparisons**: Compare portfolio performance against ETH, BTC, or market indices
- **Value at Risk**: Calculate simplified VaR estimates based on diversification
- **Time Series Analysis**: Track portfolio evolution over custom time periods

#### Usage Example

```python
from airdrops.analytics import AirdropTracker, PortfolioPerformanceAnalyzer, BenchmarkType

# Initialize tracker and analyzer
tracker = AirdropTracker()
analyzer = PortfolioPerformanceAnalyzer(tracker)

# Calculate current portfolio metrics
metrics = analyzer.calculate_portfolio_metrics()
print(f"Portfolio Value: ${metrics.total_portfolio_value_usd:,.2f}")
print(f"Portfolio ROI: {metrics.portfolio_roi_percentage:.1f}%")
print(f"Diversification Index: {metrics.diversification_index:.3f}")

# Track portfolio value over time
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=365)
end_date = datetime.now()

snapshots = analyzer.calculate_portfolio_value_over_time(
    start_date, end_date, interval_days=30
)

for snapshot in snapshots:
    print(f"{snapshot.snapshot_date.strftime('%Y-%m')}: ${snapshot.total_value_usd:,.2f}")

# Compare to benchmark
comparison = analyzer.compare_to_benchmark(BenchmarkType.ETH, 365)
print(f"Portfolio Return: {comparison.portfolio_return_percentage:.1f}%")
print(f"ETH Return: {comparison.benchmark_return_percentage:.1f}%")
print(f"Alpha: {comparison.alpha_percentage:.1f}%")
```

#### Portfolio Metrics

The `PortfolioMetrics` model provides comprehensive portfolio analysis:

```python
class PortfolioMetrics(BaseModel):
    calculation_date: datetime
    total_portfolio_value_usd: Decimal
    total_profit_loss_usd: Decimal
    total_cost_usd: Decimal
    portfolio_roi_percentage: Decimal
    protocol_count: int
    token_count: int
    diversification_index: Decimal  # 0.0 to 1.0 (higher = more diversified)
    largest_position_percentage: Decimal  # 0.0 to 100.0
    value_at_risk_usd: Optional[Decimal]
```

#### Portfolio Snapshots

Track portfolio evolution over time with `PortfolioSnapshot`:

```python
class PortfolioSnapshot(BaseModel):
    snapshot_date: datetime
    total_value_usd: Decimal
    protocol_allocations: Dict[str, Decimal]  # protocol_name -> value_usd
    token_allocations: Dict[str, Decimal]     # token_symbol -> value_usd
    diversification_score: Decimal
```

#### Benchmark Comparisons

Compare portfolio performance against standard benchmarks:

```python
# Available benchmark types
BenchmarkType.ETH          # Ethereum price performance
BenchmarkType.BTC          # Bitcoin price performance
BenchmarkType.MARKET_INDEX # General market index

# Benchmark comparison result
class BenchmarkComparison(BaseModel):
    benchmark_type: BenchmarkType
    portfolio_return_percentage: Decimal
    benchmark_return_percentage: Decimal
    alpha_percentage: Decimal  # Portfolio return - Benchmark return
    comparison_period_days: int
    calculation_date: datetime
```

#### Integration with Reporter

Portfolio analytics can be integrated with the existing `AirdropReporter`:

```python
from airdrops.analytics import AirdropReporter, PortfolioPerformanceAnalyzer

# Initialize components
tracker = AirdropTracker()
reporter = AirdropReporter(tracker)
analyzer = PortfolioPerformanceAnalyzer(tracker)

# Enable portfolio analytics in reports
reporter.enable_portfolio_analytics(analyzer)

# Generate comprehensive report with portfolio analytics
report = reporter.generate_comprehensive_report(include_portfolio=True)

# Portfolio metrics are included in the report
if report.portfolio_metrics:
    pm = report.portfolio_metrics
    print(f"Portfolio Value: ${pm.total_portfolio_value_usd:,.2f}")
    print(f"Portfolio ROI: {pm.portfolio_roi_percentage:.1f}%")
    print(f"Diversification: {pm.diversification_index:.3f}")
```

#### Diversification Analysis

The analyzer uses the Herfindahl-Hirschman Index (HHI) to measure portfolio diversification:

- **Diversification Index**: 1 - HHI, where higher values indicate better diversification
- **Range**: 0.0 (completely concentrated) to 1.0 (perfectly diversified)
- **Calculation**: Based on protocol allocation percentages

```python
# Example diversification scenarios
equal_allocation = {"Protocol1": 33.3, "Protocol2": 33.3, "Protocol3": 33.4}
# Diversification Index ≈ 0.67 (well diversified)

concentrated_allocation = {"Protocol1": 90.0, "Protocol2": 5.0, "Protocol3": 5.0}
# Diversification Index ≈ 0.18 (poorly diversified)
```

#### Value at Risk (VaR)

Simplified VaR calculation based on portfolio diversification:

- **Base Risk**: 20% of portfolio value
- **Diversification Adjustment**: Up to 10% reduction based on diversification index
- **Formula**: VaR = Portfolio Value × (0.20 - 0.10 × Diversification Index)

#### Configuration Options

Portfolio analytics can be configured through various parameters:

- **ROI Integration**: Use `ROIOptimizer` for accurate cost calculations
- **Benchmark Selection**: Choose appropriate benchmark for comparison
- **Time Periods**: Customize analysis periods for different insights
- **Snapshot Intervals**: Adjust frequency of portfolio snapshots

#### Performance Considerations

- **Efficient Queries**: Uses indexed database queries for fast data retrieval
- **Caching**: Price data caching to reduce redundant calculations
- **Batch Processing**: Optimized for analyzing large numbers of airdrop events
- **Memory Usage**: Stateless design minimizes memory footprint

#### Future Enhancements

The portfolio analytics module is designed for future expansion:

- **Real Price Data**: Integration with live price feeds for accurate valuations
- **Advanced VaR Models**: Monte Carlo simulations and historical VaR
- **Correlation Analysis**: Cross-protocol correlation and risk modeling
- **Performance Attribution**: Detailed analysis of return sources
- **Risk-Adjusted Metrics**: Sharpe ratio, Sortino ratio, and other risk metrics