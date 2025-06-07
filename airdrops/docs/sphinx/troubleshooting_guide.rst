Troubleshooting Guide
=====================

This guide provides solutions to common issues encountered when operating the Airdrops Automation system. Issues are organized by category with problem descriptions, symptoms, and step-by-step resolution procedures.

Installation and Setup Problems
--------------------------------

Poetry Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Poetry installation fails or dependencies cannot be resolved.

**Symptoms**:
- ``poetry install`` fails with dependency conflicts
- ``ModuleNotFoundError`` when importing airdrops modules
- Version conflicts between packages

**Solutions**:

1. **Clear Poetry Cache**:
   
   .. code-block:: bash
   
      poetry cache clear pypi --all
      poetry cache clear --all
      rm -rf ~/.cache/pypoetry

2. **Reset Virtual Environment**:
   
   .. code-block:: bash
   
      poetry env remove python
      poetry install --no-cache

3. **Check Python Version**:
   
   .. code-block:: bash
   
      python --version  # Should be 3.9+
      poetry env use python3.9  # Or higher version

4. **Manual Dependency Resolution**:
   
   .. code-block:: bash
   
      # Update pyproject.toml with specific versions
      poetry add "web3==6.0.0" --group main
      poetry add "pytest==7.0.0" --group dev

Environment Configuration Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Environment variables not loading or configuration errors.

**Symptoms**:
- ``KeyError`` for missing environment variables
- ``ConfigurationError`` when starting the system
- Authentication failures with RPC endpoints

**Solutions**:

1. **Verify .env File**:
   
   .. code-block:: bash
   
      # Check .env file exists and has correct format
      ls -la .env
      head -5 .env  # Should show KEY=value format

2. **Test Configuration Loading**:
   
   .. code-block:: bash
   
      poetry run python -c "
      from airdrops.shared.config import Config
      config = Config()
      print('Configuration loaded successfully')
      print(f'RPC endpoints configured: {len(config.get_rpc_endpoints())}')
      "

3. **Check Required Variables**:
   
   .. code-block:: bash
   
      # Verify all required environment variables are set
      poetry run python -c "
      import os
      required_vars = [
          'ETHEREUM_RPC_URL', 'SCROLL_RPC_URL', 'ZKSYNC_RPC_URL',
          'WALLET_PRIVATE_KEY', 'RISK_MANAGEMENT_ENABLED'
      ]
      missing = [var for var in required_vars if not os.getenv(var)]
      if missing:
          print(f'Missing variables: {missing}')
      else:
          print('All required variables present')
      "

4. **Fix Common Variable Issues**:
   
   .. code-block:: bash
   
      # Remove quotes from boolean values
      # Wrong: RISK_MANAGEMENT_ENABLED="true"
      # Right: RISK_MANAGEMENT_ENABLED=true
      
      # Ensure private keys start with 0x
      # Wrong: WALLET_PRIVATE_KEY=abcd1234...
      # Right: WALLET_PRIVATE_KEY=0xabcd1234...

Task Failures in Scheduler
---------------------------

Scheduler Not Starting
~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Scheduler bot fails to start or crashes immediately.

**Symptoms**:
- Process exits with error code
- ``ImportError`` or ``ModuleNotFoundError`` in logs
- Configuration validation errors

**Solutions**:

1. **Check Scheduler Logs**:
   
   .. code-block:: bash
   
      # View recent scheduler logs
      tail -50 logs/scheduler.log
      
      # Or run in foreground to see errors
      poetry run python -m airdrops.scheduler.bot

2. **Verify Dependencies**:
   
   .. code-block:: bash
   
      # Test scheduler imports
      poetry run python -c "
      from airdrops.scheduler.bot import SchedulerBot
      print('Scheduler imports successfully')
      "

3. **Check Database Connectivity**:
   
   .. code-block:: bash
   
      # Test database connection if used
      poetry run python -c "
      from airdrops.monitoring.collector import MetricsCollector
      collector = MetricsCollector()
      collector.test_connection()
      print('Database connection successful')
      "

4. **Validate Configuration**:
   
   .. code-block:: bash
   
      # Run configuration validation
      poetry run python -c "
      from airdrops.shared.config import Config
      config = Config()
      config.validate()
      print('Configuration validation passed')
      "

Task Execution Failures
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Individual tasks fail during execution.

**Symptoms**:
- Tasks marked as failed in scheduler logs
- RPC timeout errors
- Transaction failures
- Insufficient balance errors

**Solutions**:

1. **Check Task Logs**:
   
   .. code-block:: bash
   
      # Filter logs for specific task
      grep "task_id:12345" logs/scheduler.log
      
      # Check for specific error patterns
      grep -E "(ERROR|FAILED|Exception)" logs/scheduler.log | tail -10

2. **RPC Connection Issues**:
   
   .. code-block:: bash
   
      # Test RPC connectivity
      poetry run python -c "
      from web3 import Web3
      from airdrops.shared.config import Config
      config = Config()
      w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_RPC_URL))
      print(f'Connected: {w3.is_connected()}')
      print(f'Latest block: {w3.eth.block_number}')
      "

3. **Check Wallet Balances**:
   
   .. code-block:: bash
   
      # Verify sufficient funds
      poetry run python -c "
      from airdrops.protocols.scroll.scroll import ScrollProtocol
      scroll = ScrollProtocol()
      balance = scroll.get_eth_balance()
      print(f'ETH Balance: {balance} ETH')
      if balance < 0.01:
          print('WARNING: Low ETH balance')
      "

4. **Retry Failed Tasks**:
   
   .. code-block:: bash
   
      # Manually retry specific task
      poetry run python -c "
      from airdrops.scheduler.bot import SchedulerBot
      bot = SchedulerBot()
      bot.retry_task('task_id_here')
      "

Gas Price Issues
~~~~~~~~~~~~~~~~

**Problem**: Transactions fail due to gas price problems.

**Symptoms**:
- ``Transaction underpriced`` errors
- ``Out of gas`` errors
- Transactions stuck in mempool

**Solutions**:

1. **Check Current Gas Prices**:
   
   .. code-block:: bash
   
      # Get current network gas prices
      poetry run python -c "
      from web3 import Web3
      from airdrops.shared.config import Config
      config = Config()
      w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_RPC_URL))
      gas_price = w3.eth.gas_price
      print(f'Current gas price: {gas_price / 1e9} gwei')
      "

2. **Adjust Gas Settings**:
   
   .. code-block:: bash
   
      # Update gas multiplier in config
      # Edit .env file:
      # GAS_PRICE_MULTIPLIER=1.2  # 20% above network price

3. **Clear Stuck Transactions**:
   
   .. code-block:: bash
   
      # Check for pending transactions
      poetry run python -c "
      from airdrops.protocols.scroll.scroll import ScrollProtocol
      scroll = ScrollProtocol()
      pending = scroll.get_pending_transactions()
      print(f'Pending transactions: {len(pending)}')
      for tx in pending:
          print(f'TX: {tx[\"hash\"]} - Nonce: {tx[\"nonce\"]}')
      "

Risk Management Alerts
----------------------

High Risk Score Alerts
~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Risk management system triggers high risk alerts.

**Symptoms**:
- Risk score above configured thresholds
- Tasks being paused automatically
- Frequent risk alerts in logs

**Solutions**:

1. **Check Risk Factors**:
   
   .. code-block:: bash
   
      # Get current risk assessment
      poetry run python -c "
      from airdrops.risk_management.core import RiskManager
      risk_manager = RiskManager()
      assessment = risk_manager.assess_current_risk()
      print(f'Overall risk score: {assessment.overall_score}')
      for factor, score in assessment.factors.items():
          print(f'{factor}: {score}')
      "

2. **Review Risk Thresholds**:
   
   .. code-block:: bash
   
      # Check configured thresholds
      poetry run python -c "
      from airdrops.shared.config import Config
      config = Config()
      print(f'Risk threshold: {config.RISK_THRESHOLD}')
      print(f'Max gas price: {config.MAX_GAS_PRICE_GWEI} gwei')
      print(f'Min balance threshold: {config.MIN_BALANCE_ETH} ETH')
      "

3. **Adjust Risk Parameters**:
   
   .. code-block:: bash
   
      # Temporarily adjust thresholds if needed
      # Edit .env file:
      # RISK_THRESHOLD=0.8  # Increase from 0.7
      # MAX_GAS_PRICE_GWEI=100  # Increase gas limit

4. **Manual Risk Override**:
   
   .. code-block:: bash
   
      # Temporarily disable risk management
      poetry run python -c "
      from airdrops.risk_management.core import RiskManager
      risk_manager = RiskManager()
      risk_manager.set_override(enabled=False, duration_minutes=60)
      print('Risk management disabled for 1 hour')
      "

Insufficient Balance Alerts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Wallet balances fall below minimum thresholds.

**Symptoms**:
- Balance alerts in monitoring system
- Transaction failures due to insufficient funds
- Tasks being skipped

**Solutions**:

1. **Check All Wallet Balances**:
   
   .. code-block:: bash
   
      # Get comprehensive balance report
      poetry run python -c "
      from airdrops.analytics.portfolio import PortfolioAnalyzer
      analyzer = PortfolioAnalyzer()
      balances = analyzer.get_all_balances()
      for protocol, balance in balances.items():
          print(f'{protocol}: {balance}')
      "

2. **Fund Wallets**:
   
   .. code-block:: bash
   
      # Transfer funds to low-balance wallets
      # Use external wallet or exchange
      # Verify transfers completed:
      poetry run python -c "
      from airdrops.protocols.scroll.scroll import ScrollProtocol
      scroll = ScrollProtocol()
      balance = scroll.get_eth_balance()
      print(f'Updated balance: {balance} ETH')
      "

3. **Adjust Balance Thresholds**:
   
   .. code-block:: bash
   
      # Lower minimum balance requirements temporarily
      # Edit .env file:
      # MIN_BALANCE_ETH=0.005  # Reduce from 0.01

Capital Allocation Issues
-------------------------

Allocation Engine Failures
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Capital allocation engine fails to rebalance portfolios.

**Symptoms**:
- Rebalancing tasks fail
- Portfolio drift beyond target allocations
- Allocation engine errors in logs

**Solutions**:

1. **Check Allocation Engine Status**:
   
   .. code-block:: bash
   
      # Test allocation engine
      poetry run python -c "
      from airdrops.capital_allocation.engine import AllocationEngine
      engine = AllocationEngine()
      status = engine.get_status()
      print(f'Engine status: {status}')
      "

2. **Review Current Allocations**:
   
   .. code-block:: bash
   
      # Get current vs target allocations
      poetry run python -c "
      from airdrops.capital_allocation.engine import AllocationEngine
      engine = AllocationEngine()
      current = engine.get_current_allocation()
      target = engine.get_target_allocation()
      print('Current vs Target:')
      for protocol in current:
          print(f'{protocol}: {current[protocol]:.2%} vs {target[protocol]:.2%}')
      "

3. **Manual Rebalancing**:
   
   .. code-block:: bash
   
      # Force rebalancing
      poetry run python -c "
      from airdrops.capital_allocation.engine import AllocationEngine
      engine = AllocationEngine()
      result = engine.rebalance(force=True)
      print(f'Rebalancing result: {result}')
      "

4. **Check Rebalancing Constraints**:
   
   .. code-block:: bash
   
      # Verify rebalancing parameters
      poetry run python -c "
      from airdrops.shared.config import Config
      config = Config()
      print(f'Rebalance threshold: {config.REBALANCE_THRESHOLD}')
      print(f'Max allocation per protocol: {config.MAX_PROTOCOL_ALLOCATION}')
      "

Monitoring and Alerting Issues
-------------------------------

Missing Metrics Data
~~~~~~~~~~~~~~~~~~~~~

**Problem**: Metrics not appearing in Grafana dashboards.

**Symptoms**:
- Empty or incomplete dashboards
- Missing data points in time series
- Metrics collection errors

**Solutions**:

1. **Check Metrics Collector**:
   
   .. code-block:: bash
   
      # Test metrics collection
      poetry run python -c "
      from airdrops.monitoring.collector import MetricsCollector
      collector = MetricsCollector()
      metrics = collector.collect_all_metrics()
      print(f'Collected {len(metrics)} metrics')
      for metric in metrics[:5]:  # Show first 5
          print(f'{metric.name}: {metric.value}')
      "

2. **Verify Database Connection**:
   
   .. code-block:: bash
   
      # Test metrics database
      poetry run python -c "
      from airdrops.monitoring.aggregator import MetricsAggregator
      aggregator = MetricsAggregator()
      count = aggregator.get_metrics_count()
      print(f'Total metrics in database: {count}')
      "

3. **Check Grafana Configuration**:
   
   .. code-block:: bash
   
      # Verify Grafana data source
      curl -u admin:admin http://localhost:3000/api/datasources
      
      # Test data source connectivity
      curl -u admin:admin http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up

4. **Restart Metrics Collection**:
   
   .. code-block:: bash
   
      # Restart metrics collector
      poetry run python -c "
      from airdrops.monitoring.collector import MetricsCollector
      collector = MetricsCollector()
      collector.restart()
      print('Metrics collector restarted')
      "

Alert System Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Alerts not being sent when conditions are met.

**Symptoms**:
- No alert notifications received
- Alert rules not triggering
- Alerter service errors

**Solutions**:

1. **Check Alert Rules**:
   
   .. code-block:: bash
   
      # Verify alert rules configuration
      cat src/airdrops/monitoring/config/alert_rules.yaml
      
      # Test alert rule evaluation
      poetry run python -c "
      from airdrops.monitoring.alerter import AlertManager
      alerter = AlertManager()
      alerter.test_rules()
      "

2. **Test Notification Channels**:
   
   .. code-block:: bash
   
      # Test email notifications
      poetry run python -c "
      from airdrops.monitoring.alerter import AlertManager
      alerter = AlertManager()
      alerter.send_test_alert('email')
      print('Test alert sent')
      "

3. **Check Alert History**:
   
   .. code-block:: bash
   
      # Review recent alerts
      poetry run python -c "
      from airdrops.monitoring.alerter import AlertManager
      alerter = AlertManager()
      recent_alerts = alerter.get_recent_alerts(hours=24)
      print(f'Alerts in last 24h: {len(recent_alerts)}')
      for alert in recent_alerts:
          print(f'{alert.timestamp}: {alert.message}')
      "

4. **Update Notification Settings**:
   
   .. code-block:: bash
   
      # Check notification configuration
      cat src/airdrops/monitoring/config/notifications.yaml
      
      # Update email/webhook settings if needed

Analytics Data Issues
---------------------

Tracking Data Inconsistencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Analytics data shows inconsistencies or missing information.

**Symptoms**:
- ROI calculations seem incorrect
- Missing transaction records
- Portfolio value discrepancies

**Solutions**:

1. **Verify Data Sources**:
   
   .. code-block:: bash
   
      # Check data collection status
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      status = tracker.get_collection_status()
      print(f'Data collection status: {status}')
      "

2. **Reconcile Transaction Data**:
   
   .. code-block:: bash
   
      # Compare tracked vs blockchain data
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      discrepancies = tracker.find_discrepancies()
      if discrepancies:
          print(f'Found {len(discrepancies)} discrepancies')
          for disc in discrepancies[:5]:
              print(f'TX: {disc[\"tx_hash\"]} - Issue: {disc[\"issue\"]}')
      else:
          print('No discrepancies found')
      "

3. **Refresh Analytics Data**:
   
   .. code-block:: bash
   
      # Rebuild analytics from blockchain data
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      tracker.rebuild_from_blockchain()
      print('Analytics data rebuilt')
      "

4. **Check Price Data**:
   
   .. code-block:: bash
   
      # Verify price feed connectivity
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      prices = tracker.get_current_prices()
      print('Current token prices:')
      for token, price in prices.items():
          print(f'{token}: ${price}')
      "

Log Analysis
------------

Finding Relevant Logs
~~~~~~~~~~~~~~~~~~~~~~

**Log Locations**:

- **Scheduler**: ``logs/scheduler.log``
- **Risk Management**: ``logs/risk_management.log``
- **Protocols**: ``logs/protocols/``
- **Monitoring**: ``logs/monitoring.log``
- **Analytics**: ``logs/analytics.log``

**Common Log Analysis Commands**:

1. **Error Analysis**:
   
   .. code-block:: bash
   
      # Find all errors in last hour
      find logs/ -name "*.log" -exec grep -l "ERROR" {} \; | \
      xargs grep "ERROR" | grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')"

2. **Transaction Tracking**:
   
   .. code-block:: bash
   
      # Track specific transaction
      grep -r "0x1234567890abcdef" logs/
      
      # Find failed transactions
      grep -r "transaction.*failed\|tx.*failed" logs/

3. **Performance Analysis**:
   
   .. code-block:: bash
   
      # Find slow operations
      grep -r "took.*[0-9]\{2,\}.*seconds\|timeout" logs/
      
      # Check gas usage
      grep -r "gas.*used\|gas.*price" logs/

4. **Protocol-Specific Issues**:
   
   .. code-block:: bash
   
      # Scroll protocol issues
      grep -r "scroll.*error\|scroll.*failed" logs/
      
      # RPC issues
      grep -r "rpc.*error\|connection.*failed" logs/

Log Rotation and Cleanup
~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Log files growing too large or filling disk space.

**Solutions**:

1. **Manual Log Rotation**:
   
   .. code-block:: bash
   
      # Rotate large log files
      for log in logs/*.log; do
          if [ $(stat -f%z "$log" 2>/dev/null || stat -c%s "$log") -gt 100000000 ]; then
              mv "$log" "${log}.$(date +%Y%m%d)"
              touch "$log"
          fi
      done

2. **Clean Old Logs**:
   
   .. code-block:: bash
   
      # Remove logs older than 30 days
      find logs/ -name "*.log.*" -mtime +30 -delete

3. **Configure Log Rotation**:
   
   .. code-block:: bash
   
      # Set up logrotate (Linux)
      cat > /etc/logrotate.d/airdrops << EOF
      /path/to/airdrops/logs/*.log {
          daily
          rotate 30
          compress
          delaycompress
          missingok
          notifempty
          create 644 user group
      }
      EOF

Emergency Contacts and Escalation
----------------------------------

When to Escalate
~~~~~~~~~~~~~~~~

**Immediate Escalation Required**:
- Security incidents (unauthorized access, key compromise)
- Complete system failure affecting all protocols
- Data corruption or loss
- Significant financial losses

**Standard Escalation**:
- Persistent task failures across multiple protocols
- Monitoring system failures
- Performance degradation affecting operations

Contact Information
~~~~~~~~~~~~~~~~~~~

**Primary Operations Team**:
- Email: ops@company.com
- Phone: +1-XXX-XXX-XXXX
- Slack: #airdrops-ops

**Development Team**:
- Email: dev@company.com
- Slack: #airdrops-dev

**Security Team**:
- Email: security@company.com
- Phone: +1-XXX-XXX-XXXX (24/7)

**Management Escalation**:
- Email: management@company.com
- Phone: +1-XXX-XXX-XXXX

Incident Response Checklist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Immediate Actions**:
   - Stop affected systems if necessary
   - Preserve logs and evidence
   - Assess scope and impact
   - Notify appropriate teams

2. **Investigation**:
   - Gather relevant logs and metrics
   - Identify root cause
   - Document timeline of events

3. **Resolution**:
   - Implement fix or workaround
   - Test resolution thoroughly
   - Monitor for recurrence

4. **Post-Incident**:
   - Document lessons learned
   - Update procedures if needed
   - Schedule follow-up review

Additional Resources
--------------------

**Documentation Links**:
- Installation Guide: :doc:`installation_guide`
- Setup Guide: :doc:`setup_guide`
- Operational Runbooks: :doc:`operational_runbooks`

**External Resources**:
- Web3.py Documentation: https://web3py.readthedocs.io/
- Ethereum JSON-RPC API: https://ethereum.org/en/developers/docs/apis/json-rpc/
- Grafana Documentation: https://grafana.com/docs/

**Community Support**:
- GitHub Issues: https://github.com/company/airdrops-automation/issues
- Discord: https://discord.gg/airdrops-automation
- Forum: https://forum.company.com/airdrops