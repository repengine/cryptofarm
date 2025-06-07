Operational Runbooks
====================

This document provides step-by-step operational procedures for managing the Airdrops Automation system. These runbooks are designed for operators and developers responsible for deploying, monitoring, and maintaining the system.

Starting and Stopping the System
---------------------------------

Starting the Main Application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Verify Prerequisites**:
   
   .. code-block:: bash
   
      # Check Python environment
      python --version  # Should be 3.9+
      
      # Verify Poetry installation
      poetry --version
      
      # Check environment variables
      poetry run python -c "from airdrops.shared.config import Config; print('Config loaded successfully')"

2. **Start the Central Scheduler**:
   
   .. code-block:: bash
   
      # Navigate to project directory
      cd /path/to/airdrops
      
      # Start the scheduler in background
      poetry run python -m airdrops.scheduler.bot &
      
      # Or use screen/tmux for persistent sessions
      screen -S airdrop-scheduler
      poetry run python -m airdrops.scheduler.bot

3. **Verify System Startup**:
   
   .. code-block:: bash
   
      # Check scheduler logs
      tail -f logs/scheduler.log
      
      # Verify health check endpoint (if configured)
      curl http://localhost:8080/health
      
      # Check process status
      ps aux | grep "airdrops.scheduler"

Stopping the System Safely
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Graceful Shutdown**:
   
   .. code-block:: bash
   
      # Send SIGTERM to allow graceful shutdown
      pkill -TERM -f "airdrops.scheduler.bot"
      
      # Wait for tasks to complete (check logs)
      tail -f logs/scheduler.log
      
      # Force kill if necessary (after 30 seconds)
      pkill -KILL -f "airdrops.scheduler.bot"

2. **Verify Shutdown**:
   
   .. code-block:: bash
   
      # Ensure no processes remain
      ps aux | grep "airdrops"
      
      # Check for any pending transactions
      poetry run python -c "
      from airdrops.monitoring.collector import MetricsCollector
      collector = MetricsCollector()
      print(f'Pending transactions: {collector.get_pending_tx_count()}')
      "

Monitoring System Health
------------------------

Grafana Dashboard Access
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Primary Dashboards**:
   
   - **System Overview**: ``http://grafana:3000/d/system-overview``
     
     - Overall system health metrics
     - Active protocol connections
     - Transaction success rates
   
   - **Capital Allocation**: ``http://grafana:3000/d/capital-allocation``
     
     - Portfolio distribution
     - Rebalancing events
     - ROI tracking
   
   - **Risk Management**: ``http://grafana:3000/d/risk-management``
     
     - Risk score trends
     - Alert frequency
     - Threshold violations

2. **Key Metrics to Monitor**:
   
   - **Transaction Success Rate**: Should be >95%
   - **Average Gas Costs**: Monitor for unusual spikes
   - **Wallet Balances**: Ensure sufficient funds across protocols
   - **API Response Times**: RPC endpoints should respond <2s
   - **Error Rates**: Should be <1% for critical operations

Health Check API Interpretation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Health Check Endpoint**:
   
   .. code-block:: bash
   
      curl -s http://localhost:8080/health | jq .

2. **Response Interpretation**:
   
   .. code-block:: json
   
      {
        "status": "healthy",
        "timestamp": "2025-06-02T20:24:00Z",
        "components": {
          "scheduler": {"status": "running", "tasks_queued": 5},
          "risk_manager": {"status": "active", "alerts": 0},
          "protocols": {
            "scroll": {"status": "connected", "last_tx": "2025-06-02T20:20:00Z"},
            "zksync": {"status": "connected", "last_tx": "2025-06-02T20:15:00Z"}
          }
        }
      }

3. **Status Codes**:
   
   - ``healthy``: All systems operational
   - ``degraded``: Some non-critical issues detected
   - ``unhealthy``: Critical systems failing

Routine Maintenance
-------------------

Database Cleanup
~~~~~~~~~~~~~~~~

1. **Log Rotation** (Weekly):
   
   .. code-block:: bash
   
      # Rotate application logs
      poetry run python -c "
      from airdrops.shared.config import Config
      import logging.handlers
      # Logs are automatically rotated by RotatingFileHandler
      print('Log rotation handled automatically')
      "

2. **Metrics Data Cleanup** (Monthly):
   
   .. code-block:: bash
   
      # Clean old metrics data (>90 days)
      poetry run python -c "
      from airdrops.monitoring.aggregator import MetricsAggregator
      aggregator = MetricsAggregator()
      aggregator.cleanup_old_data(days=90)
      print('Old metrics data cleaned')
      "

Dependency Updates
~~~~~~~~~~~~~~~~~~

1. **Security Updates** (Weekly):
   
   .. code-block:: bash
   
      # Check for security vulnerabilities
      poetry run safety check
      
      # Update dependencies if needed
      poetry update
      
      # Run tests after updates
      poetry run pytest

2. **Protocol ABI Updates** (As needed):
   
   .. code-block:: bash
   
      # Update protocol ABIs when contracts change
      # Check protocol documentation for ABI updates
      # Update files in src/airdrops/protocols/*/abi/

Adding a New Protocol
---------------------

Conceptual Steps
~~~~~~~~~~~~~~~~

1. **Create Protocol Module**:
   
   .. code-block:: bash
   
      mkdir -p src/airdrops/protocols/new_protocol
      touch src/airdrops/protocols/new_protocol/__init__.py
      touch src/airdrops/protocols/new_protocol/new_protocol.py
      touch src/airdrops/protocols/new_protocol/exceptions.py

2. **Implement Base Interface**:
   
   .. code-block:: python
   
      # Follow existing protocol patterns
      # Implement required methods: execute_transaction, get_balance, etc.
      # Add comprehensive error handling and logging

3. **Add Configuration**:
   
   .. code-block:: python
   
      # Add protocol-specific config to shared/config.py
      # Include RPC endpoints, contract addresses, etc.

4. **Create Tests**:
   
   .. code-block:: bash
   
      touch tests/protocols/test_new_protocol.py
      # Implement unit and integration tests

5. **Update Documentation**:
   
   .. code-block:: bash
   
      # Add protocol to docs/sphinx/protocols.rst
      # Update API documentation

Updating Wallet Configurations
-------------------------------

Adding New Wallets
~~~~~~~~~~~~~~~~~~

1. **Environment Variables**:
   
   .. code-block:: bash
   
      # Add to .env file (never commit private keys!)
      WALLET_PRIVATE_KEY_NEW="0x..."
      WALLET_ADDRESS_NEW="0x..."

2. **Configuration Update**:
   
   .. code-block:: python
   
      # Update shared/config.py to include new wallet
      # Add wallet to appropriate protocol configurations

3. **Verification**:
   
   .. code-block:: bash
   
      # Test wallet connectivity
      poetry run python -c "
      from airdrops.shared.config import Config
      config = Config()
      print(f'New wallet configured: {config.WALLET_ADDRESS_NEW}')
      "

Removing Wallets
~~~~~~~~~~~~~~~~

1. **Drain Funds First**:
   
   .. code-block:: bash
   
      # Ensure all funds are moved before removal
      # Check balances across all protocols

2. **Update Configuration**:
   
   .. code-block:: bash
   
      # Remove from .env file
      # Update shared/config.py
      # Remove from protocol configurations

3. **Update Scheduler Tasks**:
   
   .. code-block:: bash
   
      # Remove any scheduled tasks for the wallet
      # Update task configurations

Backup and Restore Procedures
------------------------------

Configuration Backup
~~~~~~~~~~~~~~~~~~~~

1. **Critical Files to Backup**:
   
   .. code-block:: bash
   
      # Configuration files
      cp .env .env.backup.$(date +%Y%m%d)
      cp src/airdrops/shared/config.py config.py.backup.$(date +%Y%m%d)
      
      # Monitoring configurations
      cp -r src/airdrops/monitoring/config/ monitoring_config.backup.$(date +%Y%m%d)/

2. **Automated Backup Script**:
   
   .. code-block:: bash
   
      #!/bin/bash
      # backup.sh
      BACKUP_DIR="/backup/airdrops/$(date +%Y%m%d)"
      mkdir -p $BACKUP_DIR
      
      # Backup configurations (excluding secrets)
      cp src/airdrops/shared/config.py $BACKUP_DIR/
      cp -r src/airdrops/monitoring/config/ $BACKUP_DIR/
      cp -r monitoring/dashboards/ $BACKUP_DIR/
      
      echo "Backup completed: $BACKUP_DIR"

Database Backup
~~~~~~~~~~~~~~~

1. **Metrics Database**:
   
   .. code-block:: bash
   
      # If using SQLite for metrics storage
      cp metrics.db metrics.db.backup.$(date +%Y%m%d)
      
      # If using PostgreSQL
      pg_dump airdrops_metrics > airdrops_metrics.backup.$(date +%Y%m%d).sql

2. **State Database**:
   
   .. code-block:: bash
   
      # Backup any persistent state
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      tracker.export_data('state_backup_$(date +%Y%m%d).json')
      "

Restore Procedures
~~~~~~~~~~~~~~~~~~

1. **Configuration Restore**:
   
   .. code-block:: bash
   
      # Stop system first
      pkill -TERM -f "airdrops.scheduler.bot"
      
      # Restore configuration files
      cp config.py.backup.YYYYMMDD src/airdrops/shared/config.py
      cp -r monitoring_config.backup.YYYYMMDD/ src/airdrops/monitoring/config/
      
      # Verify configuration
      poetry run python -c "from airdrops.shared.config import Config; Config()"

2. **Database Restore**:
   
   .. code-block:: bash
   
      # Restore metrics database
      cp metrics.db.backup.YYYYMMDD metrics.db
      
      # Or for PostgreSQL
      psql airdrops_metrics < airdrops_metrics.backup.YYYYMMDD.sql

3. **Verification**:
   
   .. code-block:: bash
   
      # Start system and verify
      poetry run python -m airdrops.scheduler.bot &
      
      # Check health
      curl http://localhost:8080/health
      
      # Verify data integrity
      poetry run python -c "
      from airdrops.analytics.tracker import AirdropTracker
      tracker = AirdropTracker()
      print(f'Records restored: {tracker.get_record_count()}')
      "

Emergency Procedures
--------------------

System Recovery
~~~~~~~~~~~~~~~

1. **Complete System Failure**:
   
   .. code-block:: bash
   
      # Stop all processes
      pkill -KILL -f "airdrops"
      
      # Check for stuck transactions
      poetry run python -c "
      from airdrops.protocols.scroll.scroll import ScrollProtocol
      scroll = ScrollProtocol()
      print(f'Pending transactions: {scroll.get_pending_transactions()}')
      "
      
      # Restore from backup if needed
      # Restart system with health checks

2. **Partial Service Recovery**:
   
   .. code-block:: bash
   
      # Restart specific components
      poetry run python -c "
      from airdrops.scheduler.bot import SchedulerBot
      bot = SchedulerBot()
      bot.restart_failed_tasks()
      "

Contact Information
~~~~~~~~~~~~~~~~~~~

- **Primary Operator**: [Contact details]
- **Development Team**: [Contact details]
- **Emergency Escalation**: [Contact details]

Maintenance Schedule
--------------------

Daily
~~~~~
- Monitor Grafana dashboards
- Check system health endpoint
- Review error logs

Weekly
~~~~~~
- Run security dependency checks
- Review and rotate logs
- Update protocol configurations if needed

Monthly
~~~~~~~
- Clean old metrics data
- Review and update documentation
- Perform backup verification
- Review and update emergency procedures

Quarterly
~~~~~~~~~
- Full system backup and restore test
- Security audit of configurations
- Performance optimization review
- Update operational procedures