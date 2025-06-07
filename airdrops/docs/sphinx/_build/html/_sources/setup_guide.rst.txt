Setup Guide
===========

This guide covers the post-installation configuration of the Airdrops Automation system components. Complete the :doc:`installation_guide` before proceeding with this setup.

Overview
--------

The Airdrops Automation system consists of several core modules that require individual configuration:

* **Risk Manager**: Monitors and controls risk exposure
* **Capital Allocator**: Optimizes portfolio allocation and rebalancing
* **Central Scheduler**: Orchestrates task execution and dependencies
* **Monitoring System**: Provides observability and alerting
* **Analytics Platform**: Tracks performance and generates insights

Core Module Configuration
--------------------------

Risk Manager Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Risk Manager monitors system risk and enforces safety limits. Configure risk parameters in your environment or configuration files.

**Environment Variables:**

.. code-block:: bash

   # Risk limits
   MAX_POSITION_SIZE_USD=10000
   MAX_DAILY_LOSS_USD=1000
   MAX_GAS_PRICE_GWEI=100
   MIN_WALLET_BALANCE_ETH=0.1
   
   # Risk assessment intervals
   RISK_CHECK_INTERVAL_SECONDS=300
   POSITION_MONITOR_INTERVAL_SECONDS=60

**Configuration Example:**

.. code-block:: python

   from airdrops.risk_management.core import RiskManager
   
   # Initialize with custom risk parameters
   risk_manager = RiskManager(
       max_position_size_usd=10000,
       max_daily_loss_usd=1000,
       max_gas_price_gwei=100,
       min_wallet_balance_eth=0.1
   )
   
   # Configure risk rules
   risk_manager.add_risk_rule("gas_price", max_value=100)
   risk_manager.add_risk_rule("position_size", max_value=10000)

**Risk Rule Configuration:**

Create a risk configuration file ``config/risk_rules.yaml``:

.. code-block:: yaml

   risk_rules:
     gas_price:
       max_gwei: 100
       check_interval: 300
     
     position_limits:
       max_position_usd: 10000
       max_daily_loss_usd: 1000
       max_portfolio_exposure: 0.8
     
     wallet_health:
       min_eth_balance: 0.1
       min_stable_balance: 100
     
     market_conditions:
       max_volatility: 0.05
       min_liquidity_usd: 50000

Capital Allocator Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Capital Allocator manages portfolio optimization and rebalancing strategies.

**Environment Variables:**

.. code-block:: bash

   # Capital allocation settings
   INITIAL_CAPITAL_USD=50000
   REBALANCE_THRESHOLD=0.05
   MAX_ALLOCATION_PER_PROTOCOL=0.3
   MIN_ALLOCATION_PER_PROTOCOL=0.05
   
   # Allocation strategy
   ALLOCATION_STRATEGY=risk_adjusted  # Options: equal_weight, risk_adjusted, momentum

**Configuration Example:**

.. code-block:: python

   from airdrops.capital_allocation.engine import CapitalAllocationEngine
   
   # Initialize with allocation parameters
   allocator = CapitalAllocationEngine(
       initial_capital_usd=50000,
       rebalance_threshold=0.05,
       max_allocation_per_protocol=0.3
   )
   
   # Configure allocation strategy
   allocator.set_strategy("risk_adjusted")
   
   # Set protocol weights
   allocator.set_protocol_weights({
       "scroll": 0.25,
       "zksync": 0.25,
       "eigenlayer": 0.20,
       "layerzero": 0.15,
       "hyperliquid": 0.15
   })

**Allocation Strategy Configuration:**

Create ``config/allocation_strategy.yaml``:

.. code-block:: yaml

   allocation_strategy:
     name: "risk_adjusted"
     
     parameters:
       risk_free_rate: 0.03
       target_volatility: 0.15
       rebalance_frequency: "weekly"
     
     protocol_constraints:
       max_weight: 0.30
       min_weight: 0.05
     
     protocol_preferences:
       scroll:
         target_weight: 0.25
         risk_multiplier: 1.0
       zksync:
         target_weight: 0.25
         risk_multiplier: 1.1
       eigenlayer:
         target_weight: 0.20
         risk_multiplier: 0.8

Central Scheduler Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Central Scheduler orchestrates task execution with dependency management.

**Environment Variables:**

.. code-block:: bash

   # Scheduler settings
   SCHEDULER_TIMEZONE=UTC
   MAX_CONCURRENT_TASKS=5
   TASK_TIMEOUT_SECONDS=3600
   RETRY_ATTEMPTS=3
   RETRY_DELAY_SECONDS=300

**Configuration Example:**

.. code-block:: python

   from airdrops.scheduler.bot import CentralScheduler
   
   # Initialize scheduler
   scheduler = CentralScheduler(
       timezone="UTC",
       max_concurrent_tasks=5,
       task_timeout_seconds=3600
   )
   
   # Configure task schedules
   scheduler.add_recurring_task(
       task_id="daily_rebalance",
       function="airdrops.capital_allocation.engine.rebalance",
       schedule="0 9 * * *",  # Daily at 9 AM UTC
       dependencies=["risk_check"]
   )

**Task Schedule Configuration:**

Create ``config/task_schedules.yaml``:

.. code-block:: yaml

   tasks:
     risk_assessment:
       schedule: "*/5 * * * *"  # Every 5 minutes
       function: "airdrops.risk_management.core.assess_risk"
       timeout: 300
       retry_attempts: 2
     
     portfolio_rebalance:
       schedule: "0 9 * * *"  # Daily at 9 AM
       function: "airdrops.capital_allocation.engine.rebalance"
       dependencies: ["risk_assessment"]
       timeout: 1800
     
     airdrop_activities:
       scroll_activity:
         schedule: "0 */6 * * *"  # Every 6 hours
         function: "airdrops.protocols.scroll.perform_random_activity_scroll"
         dependencies: ["risk_assessment", "capital_check"]
       
       zksync_activity:
         schedule: "30 */6 * * *"  # Every 6 hours, offset by 30 minutes
         function: "airdrops.protocols.zksync.perform_random_activity"
         dependencies: ["risk_assessment", "capital_check"]

Monitoring Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Configure the monitoring system for observability and alerting.

**Environment Variables:**

.. code-block:: bash

   # Prometheus metrics
   PROMETHEUS_PORT=8000
   METRICS_COLLECTION_INTERVAL=60
   
   # Alerting configuration
   ALERT_CHECK_INTERVAL=300
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password

**Monitoring Setup:**

.. code-block:: python

   from airdrops.monitoring.collector import MetricsCollector
   from airdrops.monitoring.aggregator import MetricsAggregator
   from airdrops.monitoring.alerter import AlertManager
   
   # Initialize monitoring components
   collector = MetricsCollector(collection_interval=60)
   aggregator = MetricsAggregator()
   alerter = AlertManager()
   
   # Start monitoring
   collector.start()
   aggregator.start()
   alerter.start()

**Alert Rules Configuration:**

The system uses ``src/airdrops/monitoring/config/alert_rules.yaml``:

.. code-block:: yaml

   alert_rules:
     high_gas_price:
       condition: "gas_price_gwei > 100"
       severity: "warning"
       message: "Gas price is high: {gas_price_gwei} gwei"
       cooldown: 1800  # 30 minutes
     
     low_wallet_balance:
       condition: "wallet_balance_eth < 0.1"
       severity: "critical"
       message: "Wallet balance is low: {wallet_balance_eth} ETH"
       cooldown: 3600  # 1 hour
     
     failed_transaction:
       condition: "transaction_failed == true"
       severity: "error"
       message: "Transaction failed: {transaction_hash}"
       cooldown: 300  # 5 minutes

**Notification Configuration:**

Configure ``src/airdrops/monitoring/config/notifications.yaml``:

.. code-block:: yaml

   notification_channels:
     slack:
       webhook_url: "${SLACK_WEBHOOK_URL}"
       enabled: true
       severity_levels: ["warning", "error", "critical"]
     
     email:
       smtp_server: "${EMAIL_SMTP_SERVER}"
       smtp_port: ${EMAIL_SMTP_PORT}
       username: "${EMAIL_USERNAME}"
       password: "${EMAIL_PASSWORD}"
       to_addresses: ["admin@example.com"]
       enabled: true
       severity_levels: ["error", "critical"]

Analytics Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Configure the analytics platform for performance tracking and insights.

**Environment Variables:**

.. code-block:: bash

   # Database configuration
   DATABASE_URL=sqlite:///./airdrops.db
   # For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/airdrops
   
   # Analytics settings
   ANALYTICS_UPDATE_INTERVAL=3600  # 1 hour
   REPORT_GENERATION_SCHEDULE="0 0 * * *"  # Daily at midnight

**Analytics Setup:**

.. code-block:: python

   from airdrops.analytics.tracker import AirdropTracker
   from airdrops.analytics.reporter import AirdropReporter
   from airdrops.analytics.optimizer import ROIOptimizer
   
   # Initialize analytics components
   tracker = AirdropTracker()
   reporter = AirdropReporter(tracker)
   optimizer = ROIOptimizer(tracker)
   
   # Configure reporting
   reporter.schedule_daily_report()

Wallet Setup
------------

Secure Wallet Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Private Key Management:**

For development and testing:

.. code-block:: bash

   # Use environment variables
   export WALLET_PRIVATE_KEY="0x..."
   export WALLET_ADDRESS="0x..."

For production deployments, consider:

* **Hardware Wallets**: Ledger, Trezor integration
* **Key Management Services**: AWS KMS, HashiCorp Vault
* **Multi-signature Wallets**: Gnosis Safe, multi-sig contracts

**Wallet Validation:**

.. code-block:: python

   from web3 import Web3
   import os
   
   # Validate wallet configuration
   private_key = os.getenv("WALLET_PRIVATE_KEY")
   wallet_address = os.getenv("WALLET_ADDRESS")
   
   # Verify private key matches address
   account = Web3().eth.account.from_key(private_key)
   assert account.address.lower() == wallet_address.lower()
   
   print(f"Wallet configured: {wallet_address}")

**Multi-Wallet Setup:**

For advanced configurations with multiple wallets:

.. code-block:: bash

   # Primary wallet
   PRIMARY_WALLET_PRIVATE_KEY="0x..."
   PRIMARY_WALLET_ADDRESS="0x..."
   
   # Secondary wallets
   WALLET_2_PRIVATE_KEY="0x..."
   WALLET_2_ADDRESS="0x..."
   
   WALLET_3_PRIVATE_KEY="0x..."
   WALLET_3_ADDRESS="0x..."

Protocol-Specific Configuration
-------------------------------

Scroll Protocol Setup
~~~~~~~~~~~~~~~~~~~~~

Configure Scroll L2 interactions:

.. code-block:: bash

   # Scroll-specific settings
   SCROLL_L1_RPC_URL=https://ethereum-rpc-url
   SCROLL_L2_RPC_URL=https://rpc.scroll.io
   SCROLL_BRIDGE_MIN_AMOUNT=0.01
   SCROLL_BRIDGE_MAX_AMOUNT=1.0

zkSync Protocol Setup
~~~~~~~~~~~~~~~~~~~~~

Configure zkSync Era interactions:

.. code-block:: bash

   # zkSync-specific settings
   ZKSYNC_L1_RPC_URL=https://ethereum-rpc-url
   ZKSYNC_L2_RPC_URL=https://mainnet.era.zksync.io
   ZKSYNC_MIN_BRIDGE_AMOUNT=0.01
   ZKSYNC_MAX_BRIDGE_AMOUNT=1.0

EigenLayer Protocol Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure EigenLayer restaking:

.. code-block:: bash

   # EigenLayer-specific settings
   EIGENLAYER_STRATEGY_MANAGER=0x858646372CC42E1A627fcE94aa7A7033e7CF075A
   EIGENLAYER_DELEGATION_MANAGER=0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A
   EIGENLAYER_MIN_RESTAKE_AMOUNT=0.1

LayerZero Protocol Setup
~~~~~~~~~~~~~~~~~~~~~~~~

Configure cross-chain bridging:

.. code-block:: bash

   # LayerZero-specific settings
   LAYERZERO_ENDPOINT_ETHEREUM=0x66A71Dcef29A0fFBDBE3c6a460a3B5BC225Cd675
   LAYERZERO_ENDPOINT_ARBITRUM=0x3c2269811836af69497E5F486A85D7316753cf62
   LAYERZERO_MIN_BRIDGE_AMOUNT=10  # USDC

Hyperliquid Protocol Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure Hyperliquid trading:

.. code-block:: bash

   # Hyperliquid-specific settings
   HYPERLIQUID_API_URL=https://api.hyperliquid.xyz
   HYPERLIQUID_MIN_TRADE_SIZE=10
   HYPERLIQUID_MAX_LEVERAGE=5

System Validation
-----------------

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~~

Run comprehensive configuration validation:

.. code-block:: bash

   # Validate all configurations
   poetry run python -c "
   from airdrops.shared.config import validate_configuration
   
   try:
       validate_configuration()
       print('✅ Configuration validation passed')
   except Exception as e:
       print(f'❌ Configuration validation failed: {e}')
   "

Component Health Checks
~~~~~~~~~~~~~~~~~~~~~~~

Verify all components are properly configured:

.. code-block:: bash

   # Test individual components
   poetry run python -c "
   from airdrops.risk_management.core import RiskManager
   from airdrops.capital_allocation.engine import CapitalAllocationEngine
   from airdrops.scheduler.bot import CentralScheduler
   from airdrops.monitoring.health_checker import HealthChecker
   
   # Test each component
   components = {
       'Risk Manager': RiskManager(),
       'Capital Allocator': CapitalAllocationEngine(),
       'Scheduler': CentralScheduler(),
       'Health Checker': HealthChecker()
   }
   
   for name, component in components.items():
       try:
           # Basic initialization test
           print(f'✅ {name}: OK')
       except Exception as e:
           print(f'❌ {name}: {e}')
   "

End-to-End System Test
~~~~~~~~~~~~~~~~~~~~~~

Run a complete system test:

.. code-block:: bash

   # Run end-to-end test
   poetry run python -c "
   from airdrops.scheduler.bot import CentralScheduler
   from airdrops.monitoring.health_checker import HealthChecker
   
   # Initialize system
   scheduler = CentralScheduler()
   health_checker = HealthChecker()
   
   # Run health check
   health_status = health_checker.check_system_health()
   print(f'System Health: {health_status}')
   
   # Test scheduler
   scheduler.start()
   print('✅ System test completed successfully')
   scheduler.stop()
   "

Production Deployment Considerations
------------------------------------

Security Hardening
~~~~~~~~~~~~~~~~~~

**Environment Security:**

* Use encrypted environment variable storage
* Implement proper access controls
* Regular security audits and key rotation
* Network security and firewall configuration

**Monitoring Security:**

* Secure monitoring endpoints
* Encrypted communication channels
* Access logging and audit trails
* Intrusion detection systems

**Operational Security:**

* Regular backups of configuration and state
* Disaster recovery procedures
* Incident response plans
* Security monitoring and alerting

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

**Resource Management:**

* Monitor CPU and memory usage
* Optimize database queries and indexing
* Implement connection pooling
* Configure appropriate timeouts

**Scaling Considerations:**

* Horizontal scaling for high-volume operations
* Load balancing for multiple instances
* Database replication and sharding
* Caching strategies for frequently accessed data

Maintenance and Updates
~~~~~~~~~~~~~~~~~~~~~~~

**Regular Maintenance:**

* Monitor system logs and metrics
* Update dependencies and security patches
* Performance tuning and optimization
* Backup and recovery testing

**Update Procedures:**

* Staged deployment process
* Rollback procedures
* Configuration migration
* Testing and validation protocols

Next Steps
----------

After completing the setup:

1. **Test Individual Protocols**: Start with small amounts to verify each protocol integration
2. **Monitor System Performance**: Use the monitoring dashboard to track system health
3. **Gradual Scale-Up**: Increase position sizes and activity frequency gradually
4. **Regular Reviews**: Monitor performance and adjust configurations as needed

For operational guidance, refer to the operational runbooks and protocol-specific tutorials in the main documentation.