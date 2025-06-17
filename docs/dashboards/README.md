# Grafana Dashboard Configurations

This directory contains Grafana dashboard JSON configurations for monitoring the Airdrops Automation System. These dashboards provide comprehensive visibility into system health, performance, and operational metrics.

## Dashboard Overview

### 1. System Overview (`system-overview.json`)
**UID:** `airdrops-system-overview`

Provides a high-level view of system health and resource utilization:
- System health status indicator
- CPU, Memory, and Disk usage statistics
- Component status table (Risk Manager, Capital Allocator, Scheduler)
- Active alerts summary
- System resource trends over time

**Key Metrics:**
- `system_cpu_usage_percent`
- `system_memory_usage_percent` 
- `system_disk_usage_percent`
- `component_status`
- `ALERTS{alertstate="firing"}`

### 2. Risk Management (`risk-management.json`)
**UID:** `airdrops-risk-management`

Monitors risk assessment and portfolio management:
- Current risk level (Low/Medium/High/Critical)
- Portfolio value in USD
- Circuit breaker status
- Risk manager error rates
- Risk level history and portfolio value trends
- Risk manager performance metrics

**Key Metrics:**
- `risk_level`
- `portfolio_value_usd`
- `component_status{component="risk_manager"}`
- `component_errors_total{component="risk_manager"}`
- `component_execution_seconds_bucket{component="risk_manager"}`

### 3. Capital Allocation (`capital-allocation.json`)
**UID:** `airdrops-capital-allocation`

Tracks capital deployment and allocation efficiency:
- Capital utilization percentage
- Allocator health status
- Allocation error rates
- Protocol allocation distribution (pie chart)
- Capital utilization trends
- Protocol allocation history across all supported protocols

**Key Metrics:**
- `capital_utilization_percent`
- `protocol_allocation_percent`
- `component_status{component="capital_allocator"}`
- `component_errors_total{component="capital_allocator"}`
- `component_execution_seconds_bucket{component="capital_allocator"}`

### 4. Scheduler Performance (`scheduler-performance.json`)
**UID:** `airdrops-scheduler-performance`

Monitors task scheduling and execution:
- Scheduler running status
- Total scheduled tasks count
- Task success rate percentage
- Task execution status distribution
- Task execution rate over time
- Scheduler performance metrics (execution time percentiles)
- Task queue depth monitoring

**Key Metrics:**
- `component_status{component="scheduler"}`
- `scheduled_tasks_total`
- `task_execution_status_total`
- `component_execution_seconds_bucket{component="scheduler"}`
- `component_errors_total{component="scheduler"}`

### 5. Alerting System (`alerting-system.json`)
**UID:** `airdrops-alerting-system`

Provides visibility into the alerting infrastructure:
- Active alerts count by severity
- Critical alerts counter
- Alert resolution rate
- Notification success rate
- Active alerts table with details
- Notification channel performance
- Alert duration distribution
- Alert history (24-hour view)

**Key Metrics:**
- `ALERTS{alertstate="firing"}`
- `alerts_fired_total`
- `alerts_resolved_total`
- `notifications_sent_total`
- `alert_duration_seconds_bucket`

## Installation and Usage

### Prerequisites
- Grafana instance (v8.0+)
- Prometheus data source configured
- Airdrops monitoring system deployed and exposing metrics

### Import Instructions

1. **Via Grafana UI:**
   - Navigate to Grafana → Dashboards → Import
   - Copy the JSON content from any dashboard file
   - Paste into the import dialog
   - Configure data source (select your Prometheus instance)
   - Click "Import"

2. **Via Grafana API:**
   ```bash
   curl -X POST \
     http://your-grafana-instance/api/dashboards/db \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d @system-overview.json
   ```

3. **Via Grafana Provisioning:**
   - Copy dashboard files to your Grafana provisioning directory
   - Add dashboard provider configuration to `provisioning/dashboards/dashboards.yaml`:
   ```yaml
   apiVersion: 1
   providers:
     - name: 'airdrops-dashboards'
       type: file
       updateIntervalSeconds: 30
       options:
         path: /path/to/airdrops/monitoring/dashboards
   ```

### Data Source Configuration

These dashboards expect a Prometheus data source with the following configuration:
- **Name:** `Prometheus` (or update dashboard queries accordingly)
- **URL:** Your Prometheus server URL (e.g., `http://prometheus:9090`)
- **Access:** Server (default) or Browser depending on your setup

### Customization

#### Time Ranges
All dashboards default to appropriate time ranges:
- System Overview: Last 1 hour
- Risk Management: Last 6 hours  
- Capital Allocation: Last 6 hours
- Scheduler Performance: Last 6 hours
- Alerting System: Last 6 hours

#### Refresh Intervals
Default refresh interval is 30 seconds with options for:
- 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h

#### Thresholds
Color-coded thresholds are pre-configured for each metric:
- **Green:** Normal/healthy state
- **Yellow:** Warning state
- **Orange:** High concern
- **Red:** Critical/error state

#### Variables
Currently, dashboards use static queries. To add template variables:
1. Edit dashboard → Settings → Variables
2. Add variables for dynamic filtering (e.g., environment, instance)
3. Update panel queries to use variables: `${variable_name}`

## Troubleshooting

### Common Issues

1. **No Data Displayed:**
   - Verify Prometheus data source is configured correctly
   - Check that metrics are being exposed by the monitoring system
   - Confirm time range includes periods when system was running

2. **Missing Metrics:**
   - Ensure all monitoring components are deployed
   - Check Prometheus targets are being scraped successfully
   - Verify metric names match those in the collector implementation

3. **Performance Issues:**
   - Reduce time ranges for heavy queries
   - Increase refresh intervals
   - Consider using recording rules for complex queries

### Metric Validation

To verify metrics are available in Prometheus:
```promql
# Check if basic system metrics are present
up{job="airdrops-monitoring"}

# Verify component metrics
component_status

# Check alert metrics
ALERTS
```

## Maintenance

### Regular Updates
- Review and update threshold values based on operational experience
- Add new panels for additional metrics as the system evolves
- Update queries if metric names or labels change

### Performance Optimization
- Monitor dashboard load times
- Use recording rules for frequently queried complex expressions
- Consider splitting large dashboards if they become slow

### Version Control
- Keep dashboard JSON files in version control
- Document changes in commit messages
- Test dashboard imports in staging before production deployment

## Support

For issues with dashboard configurations:
1. Check Grafana logs for import errors
2. Validate JSON syntax
3. Verify data source connectivity
4. Review metric availability in Prometheus

For monitoring system issues, refer to the main monitoring documentation at `airdrops/docs/monitoring.md`.