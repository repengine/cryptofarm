# Monitoring Infrastructure Documentation

This document provides comprehensive documentation for the Airdrops Automation System monitoring infrastructure, including metrics collection, aggregation, alerting, and performance monitoring dashboards.

## Overview

The monitoring infrastructure provides comprehensive observability for the airdrop automation system through:
- **Metrics Collection**: System and application metrics via Prometheus client
- **Metrics Aggregation**: Time-series data processing and aggregation
- **Real-time Alerting**: Configurable alert rules with multi-channel notifications
- **Health Monitoring**: Operational health checks for system components
- **Performance Dashboards**: Grafana dashboards for system visualization

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Components    │───▶│ MetricsCollector │───▶│ MetricsAggregator│
│ (Risk, Capital, │    │                  │    │                 │
│  Scheduler)     │    └──────────────────┘    └─────────────────┘
└─────────────────┘                                      │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Prometheus    │◀───│   HTTP Endpoint  │◀───│   Prometheus    │
│   Server        │    │   /metrics       │    │   Exposition    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Grafana      │    │     Alerter      │    │  Notification   │
│   Dashboards    │    │   (Rules Engine) │───▶│   Channels      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### MetricsCollector (`airdrops.monitoring.collector`)

Collects metrics from system resources and application components. All modules pass `mypy --strict` type checking and `ruff` linting with zero violations.

**System Metrics:**
- CPU usage percentage
- Memory usage percentage  
- Disk usage percentage
- Network I/O statistics

**Component Metrics:**
- Component health status (Risk Manager, Capital Allocator, Scheduler)
- Execution time histograms
- Error counters
- Custom component-specific metrics

**Usage Example:**
```python
from airdrops.monitoring.collector import MetricsCollector

collector = MetricsCollector()
metrics = collector.collect_all_metrics(
    risk_manager=risk_mgr,
    capital_allocator=allocator,
    scheduler=scheduler
)
prometheus_data = collector.export_prometheus_format()
```

### MetricsAggregator (`airdrops.monitoring.aggregator`)

Processes and aggregates raw metrics for analysis:

**Features:**
- Time-window aggregation (configurable window size)
- Multiple aggregation functions (avg, max, min, sum)
- Metric buffering and retention management
- Configurable aggregation intervals

**Usage Example:**
```python
from airdrops.monitoring.aggregator import MetricsAggregator

aggregator = MetricsAggregator()
raw_metrics = collector.collect_all_metrics()
aggregated = aggregator.process_metrics(raw_metrics)
```

### Alerter (`airdrops.monitoring.alerter`)

Real-time alerting system with configurable rules and notifications:

**Features:**
- YAML-based alert rule configuration
- Multiple severity levels (low, medium, high, critical)
- Duration-based firing (prevents false positives)
- Multi-channel notifications (email, Slack, webhooks)
- Alert state management (pending, firing, resolved)

**Alert Rule Configuration (`config/alert_rules.yaml`):**
```yaml
rules:
  - name: "High CPU Usage"
    metric_name: "system.cpu_usage_percent"
    condition: "gt"
    threshold: 80.0
    severity: "high"
    description: "System CPU usage is above 80%"
    for_duration: 300  # 5 minutes
    labels:
      component: "system"
```

**Notification Configuration (`config/notifications.yaml`):**
```yaml
channels:
  - name: "email-alerts"
    type: "email"
    enabled: true
    config:
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      from: "alerts@example.com"
      to: "admin@example.com"
      use_tls: true
      username: "${EMAIL_USERNAME}"
      password: "${EMAIL_PASSWORD}"
  
  - name: "slack-alerts"
    type: "slack"
    enabled: true
    config:
      webhook_url: "${SLACK_WEBHOOK_URL}"
```

**Usage Example:**
```python
from airdrops.monitoring.alerter import Alerter

alerter = Alerter()
alerter.load_alert_rules("config/alert_rules.yaml")
alerter.load_notification_channels("config/notifications.yaml")

# Evaluate rules against current metrics
alerts = alerter.evaluate_rules(metrics)
alerter.send_notifications(alerts)
```

### HealthChecker (`airdrops.monitoring.health_checker`)

Provides operational health checks for system components with HTTP endpoints:

**Features:**
- Component health verification (Risk Manager, Capital Allocator, Scheduler)
- System resource monitoring (CPU, memory, disk usage)
- External dependency checks (blockchain RPC endpoints)
- HTTP API for health status queries
- Configurable health thresholds
- Prometheus metrics integration

**Health Status Levels:**
- `OK`: Component is healthy and operational
- `WARNING`: Component has minor issues but is functional
- `CRITICAL`: Component has serious issues affecting operation

**HTTP Endpoints:**
- `GET /health`: Overall system health status
- `GET /health/components/{component_name}`: Individual component health
- `GET /health/system`: System resource health only

**Usage Example:**
```python
from airdrops.monitoring.health_checker import HealthChecker

# Initialize health checker
health_checker = HealthChecker()

# Check individual component health
risk_health = health_checker.check_risk_manager_health(risk_manager)
capital_health = health_checker.check_capital_allocator_health(allocator)

# Get overall system health
system_health = health_checker.get_system_health()

# Start HTTP server for health endpoints
health_checker.start_server(host="0.0.0.0", port=8080)
```

**Configuration Environment Variables:**
- `HEALTH_CHECK_CPU_THRESHOLD`: CPU usage warning threshold (default: 80.0)
- `HEALTH_CHECK_MEMORY_THRESHOLD`: Memory usage warning threshold (default: 85.0)
- `HEALTH_CHECK_DISK_THRESHOLD`: Disk usage warning threshold (default: 90.0)
- `HEALTH_CHECK_RPC_TIMEOUT`: RPC endpoint timeout seconds (default: 5.0)
- `HEALTH_CHECK_PORT`: HTTP server port (default: 8080)

**Health Check Response Format:**
```json
{
  "status": "OK",
  "timestamp": "2025-06-02T17:24:00Z",
  "components": {
    "risk_manager": {
      "status": "OK",
      "message": "Risk manager is healthy",
      "last_check": "2025-06-02T17:24:00Z"
    },
    "capital_allocator": {
      "status": "WARNING",
      "message": "High memory usage detected",
      "last_check": "2025-06-02T17:24:00Z"
    }
  },
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 23.1
  }
}
```

## Performance Monitoring Dashboards

The monitoring system includes comprehensive Grafana dashboards for system visualization:

### Dashboard Overview

1. **System Overview** (`system-overview.json`)
   - System health indicators
   - Resource utilization (CPU, Memory, Disk)
   - Component status summary
   - Active alerts overview

2. **Risk Management** (`risk-management.json`)
   - Current risk level monitoring
   - Portfolio value tracking
   - Circuit breaker status
   - Risk assessment performance

3. **Capital Allocation** (`capital-allocation.json`)
   - Capital utilization metrics
   - Protocol allocation distribution
   - Allocation efficiency tracking
   - Performance analytics

4. **Scheduler Performance** (`scheduler-performance.json`)
   - Task execution monitoring
   - Success/failure rates
   - Queue depth tracking
   - Execution time analysis

5. **Alerting System** (`alerting-system.json`)
   - Active alerts monitoring
   - Alert resolution tracking
   - Notification performance
   - Alert history analysis

### Dashboard Installation

**Prerequisites:**
- Grafana instance (v8.0+)
- Prometheus data source configured
- Monitoring system deployed and exposing metrics

**Import Instructions:**
1. Navigate to Grafana → Dashboards → Import
2. Copy JSON content from dashboard files in `airdrops/monitoring/dashboards/`
3. Configure Prometheus data source
4. Import dashboard

For detailed installation instructions, see `airdrops/monitoring/dashboards/README.md`.

## Configuration

### Environment Variables

**Metrics Collection:**
- `METRICS_COLLECTION_INTERVAL`: Collection interval in seconds (default: 30)
- `METRICS_HTTP_PORT`: HTTP endpoint port for metrics (default: 8000)

**Metrics Aggregation:**
- `METRICS_AGGREGATION_WINDOW_SECONDS`: Aggregation window size (default: 300)
- `METRICS_AGGREGATION_FUNCTIONS`: Comma-separated functions (default: "avg,max,min")
- `METRICS_RETENTION_PERIOD_HOURS`: Data retention period (default: 168)
- `METRICS_BUFFER_MAX_SIZE`: Maximum buffer size (default: 1000)

**Alerting:**
- `ALERT_EVALUATION_INTERVAL`: Rule evaluation interval (default: 60)
- `ALERT_RETENTION_HOURS`: Alert history retention (default: 168)

### Configuration Files

**Alert Rules** (`airdrops/src/airdrops/monitoring/config/alert_rules.yaml`):
```yaml
rules:
  - name: "System CPU High"
    metric_name: "system.cpu_usage_percent"
    condition: "gt"
    threshold: 85.0
    severity: "high"
    description: "System CPU usage exceeds 85%"
    for_duration: 300
    
  - name: "Risk Level Critical"
    metric_name: "risk_level"
    condition: "gte"
    threshold: 3.0
    severity: "critical"
    description: "Risk level has reached critical threshold"
    for_duration: 60
```

**Notification Channels** (`airdrops/src/airdrops/monitoring/config/notifications.yaml`):
```yaml
channels:
  - name: "operations-email"
    type: "email"
    enabled: true
    config:
      smtp_host: "smtp.example.com"
      smtp_port: 587
      from: "monitoring@example.com"
      to: "ops-team@example.com"
      use_tls: true
      
  - name: "critical-slack"
    type: "slack"
    enabled: true
    config:
      webhook_url: "https://hooks.slack.com/services/..."
```

## Metrics Reference

### System Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `system_cpu_usage_percent` | Gauge | CPU usage percentage | - |
| `system_memory_usage_percent` | Gauge | Memory usage percentage | - |
| `system_disk_usage_percent` | Gauge | Disk usage percentage | - |

### Component Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `component_status` | Gauge | Component health (1=healthy, 0=unhealthy) | `component` |
| `component_execution_seconds` | Histogram | Component execution time | `component` |
| `component_errors_total` | Counter | Total component errors | `component` |

### Risk Management Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `risk_level` | Gauge | Current risk level (0-3) | - |
| `portfolio_value_usd` | Gauge | Portfolio value in USD | - |

### Capital Allocation Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `capital_utilization_percent` | Gauge | Capital utilization percentage | - |
| `protocol_allocation_percent` | Gauge | Protocol allocation percentage | `protocol` |

### Scheduler Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `scheduled_tasks_total` | Gauge | Total scheduled tasks | - |
| `task_execution_status_total` | Counter | Task execution status counts | `status` |

## Deployment

### Docker Compose Example

```yaml
version: '3.8'
services:
  airdrops-monitoring:
    build: .
    ports:
      - "8000:8000"  # Metrics endpoint
    environment:
      - METRICS_COLLECTION_INTERVAL=30
      - ALERT_EVALUATION_INTERVAL=60
    volumes:
      - ./config:/app/config
      
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./dashboards:/var/lib/grafana/dashboards
```

### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'airdrops-monitoring'
    static_configs:
      - targets: ['airdrops-monitoring:8000']
    scrape_interval: 30s
    metrics_path: '/metrics'
```

## Troubleshooting

### Common Issues

**No Metrics Data:**
1. Verify metrics endpoint is accessible: `curl http://localhost:8000/metrics`
2. Check Prometheus targets: Prometheus UI → Status → Targets
3. Confirm components are instrumented correctly

**Alerts Not Firing:**
1. Verify alert rules syntax in YAML files
2. Check metric names match exactly
3. Confirm evaluation intervals and thresholds
4. Review alerter logs for evaluation errors

**Dashboard Issues:**
1. Verify Prometheus data source configuration
2. Check metric availability in Prometheus
3. Confirm time ranges include active periods
4. Validate dashboard JSON syntax

### Monitoring Health Checks

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Verify Prometheus scraping
curl http://localhost:9090/api/v1/targets

# Test alert rule evaluation
curl http://localhost:9090/api/v1/rules
```

## Performance Considerations

### Metrics Collection
- Default collection interval: 30 seconds
- Adjust based on system load and requirements
- Monitor collector execution time

### Aggregation
- Buffer size limits prevent memory issues
- Retention policies manage storage usage
- Aggregation windows balance accuracy vs. performance

### Alerting
- Evaluation intervals affect responsiveness
- Duration thresholds prevent alert fatigue
- Notification rate limiting recommended

## Security

### Metrics Exposure
- Metrics endpoint should be secured in production
- Consider authentication/authorization for sensitive metrics
- Network-level access controls recommended

### Notification Security
- Use environment variables for sensitive configuration
- Secure webhook URLs and API keys
- Encrypt SMTP credentials

### Data Privacy
- Avoid logging sensitive information in metrics
- Implement data retention policies
- Consider metric anonymization for compliance

## Integration

### With Existing Systems

**Prometheus Integration:**
- Standard Prometheus exposition format
- Compatible with existing Prometheus infrastructure
- Supports service discovery mechanisms

**Grafana Integration:**
- Standard Grafana dashboard format
- Compatible with Grafana provisioning
- Supports template variables and annotations

**External Monitoring:**
- Webhook notifications for external systems
- API endpoints for metric queries
- Integration with incident management tools

## Maintenance

### Regular Tasks
- Review and update alert thresholds
- Monitor dashboard performance
- Update retention policies
- Validate notification channels

### Upgrades
- Test dashboard compatibility with Grafana updates
- Verify Prometheus client library compatibility
- Update metric schemas as needed

### Backup and Recovery
- Export dashboard configurations
- Backup alert rule configurations
- Document notification channel settings

For additional support and troubleshooting, refer to the component-specific documentation and the main project documentation.