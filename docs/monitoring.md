# Monitoring Infrastructure Module

## Overview

The Monitoring Infrastructure module provides comprehensive observability capabilities for the airdrop automation system. It implements Phase 4.1.1 (metrics collection and aggregation) and Phase 4.1.2 (real-time alerting system) of the architectural plan, focusing on metrics collection, aggregation, and real-time alerting from Phase 3 components and system-level monitoring.

## Purpose

The monitoring module serves as the foundation for system observability by:

- **Metrics Collection**: Gathering performance, health, and operational metrics from core components
- **System Monitoring**: Tracking CPU, memory, disk, and network usage
- **Data Aggregation**: Processing raw metrics into time-series data for analysis
- **Prometheus Integration**: Exposing metrics in Prometheus exposition format
- **Real-time Alerting**: Evaluating alert rules and triggering notifications through multiple channels
- **Notification Management**: Supporting email, Slack, and webhook notifications for alerts

## Architecture

### Core Components

#### MetricsCollector (`src/airdrops/monitoring/collector.py`)

The primary metrics collection engine that:

- Collects system-level metrics using `psutil`
- Interfaces with Phase 3 components:
  - **RiskManager**: Risk levels, portfolio values, circuit breaker status
  - **CapitalAllocator**: Capital utilization, protocol allocations, performance metrics
  - **CentralScheduler**: Task counts, execution status, scheduler health
- Exposes metrics in Prometheus format using `prometheus-client`
- Provides HTTP endpoint for metrics scraping

**Key Features:**
- Configurable collection intervals via environment variables
- Robust error handling with component-specific error tracking
- Prometheus metric types: Counters, Gauges, Histograms
- System resource monitoring with cross-platform support

#### MetricsAggregator (`src/airdrops/monitoring/aggregator.py`)

Processes and aggregates raw metrics for analysis:

- Time-window based aggregation (configurable window sizes)
- Multiple aggregation functions: average, maximum, minimum
- Metrics buffering with configurable retention policies
- Efficient data processing for analytics pipelines

**Key Features:**
- Configurable aggregation windows (default: 5 minutes)
- Automatic cleanup of old metrics based on retention policy
- Support for filtering by time range and metric names
- Memory-efficient buffering with size limits

#### Alerter (`src/airdrops/monitoring/alerter.py`)

Real-time alerting system that evaluates rules against metrics and triggers notifications:

- Configurable alert rules with multiple condition types (gt, lt, eq, ne, gte, lte)
- Multi-severity alert levels (low, medium, high, critical)
- Alert state management (pending, firing, resolved)
- Duration-based alert firing to prevent false positives
- Multi-channel notification support (email, Slack, webhooks)
- YAML-based configuration for rules and notification channels

**Key Features:**
- Rule-based alert evaluation with configurable thresholds
- Alert state persistence and history tracking
- Notification rate limiting and duplicate suppression
- Flexible notification routing based on severity
- Comprehensive logging and error handling

### Data Models

#### SystemMetrics
```python
@dataclass
class SystemMetrics:
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
```

#### ComponentMetrics
```python
@dataclass
class ComponentMetrics:
    component_name: str
    status: str
    last_execution_time: float
    error_count: int
    success_count: int
```

#### AggregatedMetric
```python
@dataclass
class AggregatedMetric:
    metric_name: str
    value: float
    timestamp: float
    labels: Dict[str, str]
    aggregation_type: str
```

#### AlertRule
```python
@dataclass
class AlertRule:
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "ne", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    description: str
    for_duration: int = 300  # seconds
    labels: Dict[str, str] = None
```

#### Alert
```python
@dataclass
class Alert:
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    status: AlertStatus
    description: str
    timestamp: float
    labels: Dict[str, str]
    firing_since: Optional[float] = None
    resolved_at: Optional[float] = None
```

#### NotificationChannel
```python
@dataclass
class NotificationChannel:
    name: str
    type: str  # "email", "slack", "webhook"
    config: Dict[str, Any]
    enabled: bool = True
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_COLLECTION_INTERVAL` | `30.0` | Collection interval in seconds |
| `METRICS_HTTP_PORT` | `8000` | HTTP port for metrics endpoint |
| `METRICS_AGGREGATION_WINDOW_SECONDS` | `300` | Aggregation window size |
| `METRICS_AGGREGATION_FUNCTIONS` | `avg,max,min` | Comma-separated aggregation functions |
| `METRICS_RETENTION_PERIOD_HOURS` | `168` | Metrics retention period (7 days) |
| `METRICS_BUFFER_MAX_SIZE` | `1000` | Maximum buffer size for raw metrics |

### Alerting Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_EVALUATION_INTERVAL` | `60` | Alert evaluation interval in seconds |
| `ALERT_RETENTION_HOURS` | `168` | Alert history retention period (7 days) |

## Usage Examples

### Basic Metrics Collection

```python
from airdrops.monitoring.collector import MetricsCollector
from airdrops.capital_allocation.engine import CapitalAllocator
from airdrops.scheduler.bot import CentralScheduler

# Initialize collector
collector = MetricsCollector()

# Initialize components
allocator = CapitalAllocator()
scheduler = CentralScheduler()

# Collect all metrics
metrics = collector.collect_all_metrics(
    capital_allocator=allocator,
    scheduler=scheduler
)

# Export in Prometheus format
prometheus_data = collector.export_prometheus_format()
print(prometheus_data.decode('utf-8'))
```

### Metrics Aggregation

```python
from airdrops.monitoring.aggregator import MetricsAggregator

# Initialize aggregator
aggregator = MetricsAggregator()

# Process raw metrics
raw_metrics = collector.collect_all_metrics()
aggregated = aggregator.process_metrics(raw_metrics)

# Retrieve filtered metrics
recent_metrics = aggregator.get_aggregated_metrics(
    start_time=time.time() - 3600,  # Last hour
    metric_name_filter="system_cpu"
)
```

### System Metrics Only

```python
# Collect only system metrics
system_metrics = collector.collect_system_metrics()
print(f"CPU: {system_metrics.cpu_usage_percent}%")
print(f"Memory: {system_metrics.memory_usage_percent}%")
```

### Real-time Alerting

```python
from airdrops.monitoring.alerter import Alerter

# Initialize alerter
alerter = Alerter()

# Load configuration files
alerter.load_alert_rules("src/airdrops/monitoring/config/alert_rules.yaml")
alerter.load_notification_channels("src/airdrops/monitoring/config/notifications.yaml")

# Collect metrics and evaluate alerts
metrics = collector.collect_all_metrics()
triggered_alerts = alerter.evaluate_rules(metrics)

# Send notifications for triggered alerts
if triggered_alerts:
    alerter.send_notifications(triggered_alerts)

# Get current active alerts
active_alerts = alerter.get_active_alerts()
print(f"Active alerts: {len(active_alerts)}")

# Get alert history
recent_alerts = alerter.get_alert_history(hours=6)
print(f"Recent alerts: {len(recent_alerts)}")
```

### Integrated Monitoring and Alerting

```python
from airdrops.monitoring import MetricsCollector, MetricsAggregator, Alerter

# Initialize all components
collector = MetricsCollector()
aggregator = MetricsAggregator()
alerter = Alerter()

# Load alerting configuration
alerter.load_alert_rules("config/alert_rules.yaml")
alerter.load_notification_channels("config/notifications.yaml")

# Monitoring loop
while True:
    # Collect metrics
    metrics = collector.collect_all_metrics()
    
    # Process and aggregate
    aggregated = aggregator.process_metrics(metrics)
    
    # Evaluate alerts
    alerts = alerter.evaluate_rules(metrics)
    
    # Send notifications
    if alerts:
        alerter.send_notifications(alerts)
    
    time.sleep(60)  # Wait 1 minute
```

## Metrics Exposed

### System Metrics
- `system_cpu_usage_percent`: CPU utilization percentage
- `system_memory_usage_percent`: Memory utilization percentage  
- `system_disk_usage_percent`: Disk utilization percentage

### Component Status Metrics
- `component_status{component="risk_manager|capital_allocator|scheduler"}`: Component health (1=healthy, 0=unhealthy)
- `component_execution_seconds{component}`: Component execution time histogram
- `component_errors_total{component}`: Total component errors counter

### Risk Management Metrics
- `risk_level`: Current risk level (0=low, 1=medium, 2=high, 3=critical)
- `portfolio_value_usd`: Current portfolio value in USD

### Capital Allocation Metrics
- `capital_utilization_percent`: Capital utilization percentage
- `protocol_allocation_percent{protocol}`: Protocol allocation percentage

### Scheduler Metrics
- `scheduled_tasks_total`: Total number of scheduled tasks
- `task_execution_status_total{status}`: Task execution status counts

## Integration Points

### Phase 3 Components

The monitoring module integrates with existing Phase 3 components:

1. **RiskManager** (`src/airdrops/risk_management/core.py`)
   - Accesses `risk_limits` for exposure thresholds
   - Monitors `circuit_breaker_active` status
   - Tracks risk assessment metrics

2. **CapitalAllocator** (`airdrops/src/airdrops/capital_allocation/engine.py`)
   - Reads `portfolio_history` for performance metrics
   - Monitors capital utilization and allocations
   - Tracks portfolio performance indicators

3. **CentralScheduler** (`airdrops/src/airdrops/scheduler/bot.py`)
   - Monitors `_running` status
   - Tracks `_task_definitions` and `_task_executions`
   - Counts task statuses and execution metrics

### External Dependencies

- **prometheus-client**: Metrics exposition and HTTP server
- **psutil**: System resource monitoring
- **Standard library**: logging, time, os, dataclasses

## Future Enhancements

As outlined in the Phase 4 architectural plan, future enhancements will include:

1. **HTTP Metrics Server**: Dedicated HTTP server for metrics exposition
2. **Grafana Dashboards**: Pre-built dashboards for visualization
3. **AlertManager Integration**: Automated alerting based on thresholds
4. **PostgreSQL Analytics**: ETL pipeline for long-term analytics storage
5. **Custom Collectors**: Protocol-specific metrics collection

## Testing

Comprehensive test coverage includes:

- Unit tests for all collector methods
- Mock-based testing for component integration
- Error handling and failure scenarios
- Aggregation logic validation
- Data class functionality verification

Run tests with:
```bash
pytest tests/test_monitoring.py -v
```

## Dependencies

The monitoring module adds the following dependencies to the project:

- `prometheus-client (>=0.20.0,<1.0.0)`: Prometheus metrics client library
- `psutil (>=5.9.0,<6.0.0)`: System and process utilities

These dependencies are automatically included when installing the airdrops package.