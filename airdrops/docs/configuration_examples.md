# Configuration Examples

This document provides comprehensive configuration examples for the Airdrops system. These examples cover various deployment scenarios from development to production.

## Table of Contents
1. [Basic Configuration](#basic-configuration)
2. [Protocol Configuration](#protocol-configuration)
3. [Capital Allocation Configuration](#capital-allocation-configuration)
4. [Risk Management Configuration](#risk-management-configuration)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Advanced Configurations](#advanced-configurations)

## Basic Configuration

### Minimal Development Configuration
```yaml
# config/development.yaml
system:
  environment: development
  log_level: DEBUG
  
wallets:
  - address: "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775"
    private_key: "${WALLET_1_PRIVATE_KEY}"  # Environment variable
    type: hot

networks:
  ethereum:
    rpc_url: "${ETHEREUM_RPC_URL}"
    chain_id: 1
  
  scroll:
    rpc_url: "${SCROLL_RPC_URL}"
    chain_id: 534352

protocols:
  scroll:
    enabled: true
    
capital_allocation:
  total_capital_usd: 10000
  strategy: equal_weight
```

### Production Configuration
```yaml
# config/production.yaml
system:
  environment: production
  log_level: INFO
  error_reporting:
    sentry_dsn: "${SENTRY_DSN}"
  
  # Performance settings
  max_concurrent_operations: 10
  operation_timeout: 300  # seconds
  
  # Security
  require_2fa: true
  ip_whitelist:
    - "10.0.0.0/8"
    - "172.16.0.0/12"

wallets:
  # Hot wallets for operations
  - address: "0x742d35Cc6634C0532925a3b844Bc9e7195Ed5E47283775"
    private_key: "aws-kms://arn:aws:kms:us-east-1:123456789:key/abc"
    type: hot
    daily_limit_usd: 5000
    
  - address: "0x853d35Cc6634C0532925a3b844Bc9e7195Ed5E47283776"
    private_key: "aws-kms://arn:aws:kms:us-east-1:123456789:key/def"
    type: hot
    daily_limit_usd: 5000
    
  # Cold wallet for reserves
  - address: "0x963d35Cc6634C0532925a3b844Bc9e7195Ed5E47283777"
    type: cold
    multisig: true
    threshold: 2
    signers: 3
```

## Protocol Configuration

### Multi-Protocol Setup
```yaml
protocols:
  # Layer 2 - zkSync
  zksync:
    enabled: true
    daily_activity_range: [3, 6]  # Min/max operations per day
    
    # Network settings
    networks:
      mainnet:
        rpc_url: "https://mainnet.era.zksync.io"
        fallback_rpcs:
          - "https://zksync-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}"
          - "https://zksync-era.blockpi.network/v1/rpc/public"
    
    # Operation weights (must sum to 100)
    operations:
      bridge:
        enabled: true
        weight: 25
        min_amount_eth: 0.05
        max_amount_eth: 0.5
        
      swap:
        enabled: true
        weight: 40
        dexs:
          - name: syncswap
            router: "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295"
            weight: 60
          - name: mute
            router: "0x8B791913eB07C32779a16750e3868aA8495F5964"
            weight: 40
            
      lending:
        enabled: true
        weight: 25
        protocols:
          eralend:
            pool_manager: "0x5E23E96196f40e8DD7F2fd4E11aC9D2eBE8Af7e2"
            min_health_factor: 1.5
            
      liquidity:
        enabled: true
        weight: 10
        min_position_usd: 100
        max_slippage_bps: 100  # 1%

  # Layer 2 - Scroll
  scroll:
    enabled: true
    daily_activity_range: [4, 8]
    
    networks:
      mainnet:
        rpc_url: "https://rpc.scroll.io"
        fallback_rpcs:
          - "https://scroll-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}"
          - "https://1rpc.io/scroll"
    
    contracts:
      bridge:
        l1_gateway: "0xD8A791fE2bE73eb6E6cF1eb0cb3F36adC9B3F8f9"
        l2_gateway: "0x4C0926FF5252A435FD19e10ED15e5a249Ba19d79"
      
      dexs:
        syncswap:
          router: "0x80e38291e06339d10AAB483C65695D004dBD5C69"
          factory: "0x37BAc764494c8db4e54BDE72f6965beA9fa0AC2d"
          
    operations:
      bridge:
        enabled: true
        weight: 30
        bridge_delay_minutes: [10, 60]  # Random delay after bridge
        
      swap:
        enabled: true
        weight: 35
        preferred_pairs:
          - ["ETH", "USDC"]
          - ["USDC", "USDT"]
          - ["ETH", "WBTC"]
          
      lending:
        enabled: true
        weight: 20
        protocols:
          - layerbank
          - aave_v3
          
      liquidity:
        enabled: true
        weight: 15
        concentrated_liquidity: true
        range_percentage: 10  # ±10% from current price

  # Cross-chain - LayerZero
  layerzero:
    enabled: true
    daily_activity_range: [2, 4]
    
    # Supported chains for bridging
    supported_chains:
      - ethereum
      - arbitrum
      - optimism
      - polygon
      - avalanche
      - bsc
      - fantom
      - scroll
      - zksync
      
    operations:
      bridge:
        enabled: true
        weight: 60
        use_stargate: true
        
      messaging:
        enabled: true
        weight: 30
        omnichain_nfts:
          - "0x..." # Pudgy Penguins
          
      governance:
        enabled: true
        weight: 10

  # Perps - Hyperliquid
  hyperliquid:
    enabled: true
    daily_activity_range: [5, 10]
    
    trading:
      max_position_size_usd: 10000
      max_leverage: 5
      preferred_pairs:
        - "ETH-USD"
        - "BTC-USD"
        - "ARB-USD"
      
      risk_limits:
        max_drawdown: 0.10  # 10%
        stop_loss: 0.05     # 5%
        take_profit: 0.15   # 15%
      
      strategies:
        - name: momentum
          weight: 40
        - name: mean_reversion
          weight: 30
        - name: arbitrage
          weight: 30

  # Restaking - EigenLayer
  eigenlayer:
    enabled: true
    daily_activity_range: [1, 2]  # Less frequent
    
    strategies:
      - name: "stETH-strategy"
        address: "0x93c4b944D05dfe6df7645A86cd2206016c51564D"
        allocation: 0.6
        
      - name: "rETH-strategy"
        address: "0x1BeE69b7dFFfA4E2d53C2a2Df135C388AD25dCD2"
        allocation: 0.4
    
    operators:
      selection_criteria:
        - min_tvl: 1000000  # $1M
        - max_commission: 10  # 10%
        - min_uptime: 0.99   # 99%
```

## Capital Allocation Configuration

### Advanced Capital Allocation
```yaml
capital_allocation:
  # Total capital settings
  total_capital_usd: 100000
  reserve_percentage: 0.10  # Keep 10% liquid
  
  # Allocation strategy
  strategy: mean_variance  # Options: equal_weight, risk_parity, mean_variance, kelly_criterion
  
  # Strategy-specific parameters
  mean_variance:
    lookback_days: 30
    target_return: 0.15  # 15% annual
    risk_free_rate: 0.04  # 4%
    
  risk_parity:
    risk_budget: 0.25  # 25% annual volatility
    
  kelly_criterion:
    confidence_level: 0.25  # Use 25% of Kelly allocation
    
  # Rebalancing
  rebalancing:
    enabled: true
    threshold: 0.15  # Rebalance if drift > 15%
    frequency: weekly
    min_trade_size_usd: 50
    
  # Per-protocol limits
  protocol_limits:
    min_allocation: 0.05  # 5% minimum
    max_allocation: 0.30  # 30% maximum
    
  # Asset allocation
  asset_targets:
    eth: 0.40
    stables: 0.30
    wbtc: 0.20
    other: 0.10
```

### Dynamic Allocation Rules
```yaml
dynamic_allocation:
  # Market condition adjustments
  market_conditions:
    bull:
      eth_multiplier: 1.2
      risk_multiplier: 1.1
      
    bear:
      eth_multiplier: 0.8
      stable_multiplier: 1.3
      risk_multiplier: 0.7
      
    volatile:
      stable_multiplier: 1.2
      max_position_size: 0.8  # Reduce by 20%
  
  # Performance-based adjustments
  performance_adjustments:
    outperformers:
      threshold: 0.20  # 20% above average
      allocation_increase: 0.10  # +10%
      
    underperformers:
      threshold: -0.10  # 10% below average
      allocation_decrease: 0.15  # -15%
  
  # Time-based rules
  time_rules:
    - name: weekend_reduction
      days: [6, 7]  # Saturday, Sunday
      multiplier: 0.7
      
    - name: month_end_increase
      days: [28, 29, 30, 31]
      multiplier: 1.2
```

## Risk Management Configuration

### Comprehensive Risk Settings
```yaml
risk_management:
  # Gas price limits
  gas_limits:
    ethereum:
      max_gas_price_gwei: 100
      urgent_max_gwei: 200
      warning_threshold_gwei: 80
      
    l2_chains:
      max_gas_price_gwei: 10
      warning_threshold_gwei: 5
  
  # Exposure limits
  exposure_limits:
    max_protocol_exposure: 0.30  # 30% of portfolio
    max_chain_exposure: 0.40     # 40% per chain
    max_asset_exposure: 0.50     # 50% in any token
    max_lp_exposure: 0.25        # 25% in LPs
    
  # Position health
  position_health:
    lending:
      min_health_factor: 1.5
      warning_health_factor: 1.8
      target_ltv: 0.50  # 50%
      
    liquidity:
      max_impermanent_loss: 0.10  # 10%
      rebalance_threshold: 0.20    # 20% drift
  
  # Stop loss settings
  stop_loss:
    enabled: true
    portfolio_level: 0.15  # 15% portfolio drawdown
    position_level: 0.20   # 20% position loss
    daily_loss_limit: 0.05 # 5% daily loss
    
  # Emergency procedures
  emergency:
    triggers:
      - type: exploit_detected
        action: pause_all_operations
        
      - type: extreme_gas_prices
        threshold: 500  # gwei
        action: pause_non_critical
        
      - type: portfolio_drawdown
        threshold: 0.25  # 25%
        action: move_to_stables
        
  # Slippage protection
  slippage:
    normal_trades:
      max_slippage_bps: 50  # 0.5%
      
    large_trades:  # >$10k
      max_slippage_bps: 100  # 1%
      use_twap: true
      twap_duration_minutes: 30
```

## Monitoring and Alerting

### Monitoring Configuration
```yaml
monitoring:
  # Metrics collection
  metrics:
    enabled: true
    interval_seconds: 60
    retention_days: 90
    
    # Prometheus settings
    prometheus:
      enabled: true
      port: 9090
      path: /metrics
      
    # Custom metrics
    custom_metrics:
      - name: protocol_roi
        type: gauge
        labels: ["protocol", "timeframe"]
        
      - name: gas_efficiency
        type: histogram
        buckets: [0.01, 0.02, 0.05, 0.1, 0.2]
  
  # Health checks
  health_checks:
    enabled: true
    interval_seconds: 300
    
    checks:
      - name: rpc_connectivity
        timeout: 10
        
      - name: wallet_balances
        min_eth: 0.05
        
      - name: position_health
        
      - name: api_availability
  
  # Logging
  logging:
    level: INFO
    format: json
    
    outputs:
      - type: console
        
      - type: file
        path: /var/log/airdrops/
        rotation: daily
        retention: 30
        
      - type: elasticsearch
        hosts:
          - "http://elasticsearch:9200"
        index: airdrops-logs
```

### Alerting Configuration
```yaml
alerting:
  # Alert channels
  channels:
    discord:
      enabled: true
      webhook_url: "${DISCORD_WEBHOOK}"
      severity_filter: [warning, critical]
      
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      chat_id: "${TELEGRAM_CHAT_ID}"
      severity_filter: [critical]
      
    email:
      enabled: true
      smtp_server: smtp.gmail.com
      smtp_port: 587
      from_address: alerts@example.com
      to_addresses:
        - admin@example.com
      severity_filter: [critical]
      
    pagerduty:
      enabled: false
      api_key: "${PAGERDUTY_KEY}"
      severity_filter: [critical]
  
  # Alert rules
  rules:
    # Performance alerts
    - name: low_success_rate
      condition: success_rate < 0.8
      severity: warning
      cooldown_minutes: 30
      
    - name: high_gas_costs
      condition: daily_gas_usd > 100
      severity: warning
      cooldown_minutes: 60
      
    # Security alerts
    - name: unauthorized_transaction
      condition: unknown_tx_detected
      severity: critical
      cooldown_minutes: 0
      
    - name: wallet_drained
      condition: balance_drop > 0.5
      severity: critical
      cooldown_minutes: 0
      
    # System alerts
    - name: high_error_rate
      condition: error_rate > 0.1
      severity: warning
      cooldown_minutes: 15
      
    - name: service_down
      condition: health_check_failed
      severity: critical
      cooldown_minutes: 5
```

## Advanced Configurations

### Multi-Environment Setup
```yaml
# config/base.yaml - Shared settings
base:
  version: "1.0.0"
  
  constants:
    min_eth_balance: 0.01
    max_retries: 3
    timeout_seconds: 300

---
# config/staging.yaml - Extends base
extends: base.yaml

system:
  environment: staging
  
networks:
  ethereum:
    rpc_url: "https://goerli.infura.io/v3/${INFURA_KEY}"
    chain_id: 5  # Goerli

---
# config/production.yaml - Extends base
extends: base.yaml

system:
  environment: production
  
networks:
  ethereum:
    rpc_url: "https://mainnet.infura.io/v3/${INFURA_KEY}"
    chain_id: 1  # Mainnet
```

### Scheduler Configuration
```yaml
scheduler:
  # Task scheduling
  enabled: true
  timezone: UTC
  
  # Execution settings
  max_concurrent_tasks: 5
  task_timeout_seconds: 300
  retry_policy:
    max_attempts: 3
    backoff_multiplier: 2
    max_backoff_seconds: 300
    
  # Task priorities
  priorities:
    critical: 10
    high: 7
    normal: 5
    low: 3
    
  # Schedule templates
  schedules:
    - name: regular_trading
      cron: "0 */4 * * *"  # Every 4 hours
      tasks:
        - protocol: scroll
          action: swap
          priority: normal
          
    - name: daily_rebalance
      cron: "0 14 * * *"  # 2 PM UTC daily
      tasks:
        - action: rebalance_portfolio
          priority: high
          
    - name: weekly_harvest
      cron: "0 10 * * 1"  # Monday 10 AM UTC
      tasks:
        - action: claim_rewards
          priority: normal
          
  # Activity windows
  activity_windows:
    - name: asia_hours
      start: "01:00"
      end: "09:00"
      multiplier: 1.2
      
    - name: europe_hours
      start: "08:00"
      end: "16:00"
      multiplier: 1.0
      
    - name: us_hours
      start: "14:00"
      end: "22:00"
      multiplier: 1.1
```

### Database Configuration
```yaml
database:
  # Primary database
  primary:
    type: postgresql
    host: "${DB_HOST}"
    port: 5432
    name: airdrops
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    
    # Connection pool
    pool:
      min_connections: 5
      max_connections: 20
      idle_timeout: 300
      
    # Performance
    statement_timeout: 30000  # 30 seconds
    lock_timeout: 10000       # 10 seconds
    
  # Read replicas
  replicas:
    - host: "${DB_REPLICA_1}"
      weight: 50
      
    - host: "${DB_REPLICA_2}"
      weight: 50
      
  # Redis cache
  redis:
    host: "${REDIS_HOST}"
    port: 6379
    password: "${REDIS_PASSWORD}"
    db: 0
    
    # Cache settings
    ttl:
      default: 3600         # 1 hour
      price_data: 60        # 1 minute
      gas_prices: 30        # 30 seconds
      protocol_config: 86400  # 24 hours
```

### Security Configuration
```yaml
security:
  # Authentication
  authentication:
    required: true
    methods:
      - api_key
      - jwt
      
    jwt:
      secret: "${JWT_SECRET}"
      algorithm: HS256
      expiry_hours: 24
      
  # Authorization
  authorization:
    rbac_enabled: true
    roles:
      - name: admin
        permissions: ["*"]
        
      - name: operator
        permissions:
          - execute_trades
          - view_positions
          - claim_rewards
          
      - name: viewer
        permissions:
          - view_positions
          - view_metrics
          
  # Encryption
  encryption:
    at_rest:
      enabled: true
      algorithm: AES-256-GCM
      
    in_transit:
      tls_required: true
      min_version: "1.2"
      
  # Wallet security
  wallet_security:
    private_key_storage: aws_kms
    require_multisig: true
    transaction_limits:
      hourly: 10000   # $10k
      daily: 50000    # $50k
      per_tx: 5000    # $5k
```

## Environment Variables

### Required Environment Variables
```bash
# .env.example

# API Keys
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
SCROLL_RPC_URL=https://rpc.scroll.io
ZKSYNC_RPC_URL=https://mainnet.era.zksync.io
ALCHEMY_KEY=your_alchemy_key
INFURA_KEY=your_infura_key

# Wallet Keys (use KMS in production)
WALLET_1_PRIVATE_KEY=0x...
WALLET_2_PRIVATE_KEY=0x...

# Database
DB_HOST=localhost
DB_USER=airdrops
DB_PASSWORD=secure_password
DB_REPLICA_1=replica1.example.com
DB_REPLICA_2=replica2.example.com

# Redis
REDIS_HOST=localhost
REDIS_PASSWORD=redis_password

# Monitoring
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=bot_token
TELEGRAM_CHAT_ID=chat_id
SENTRY_DSN=https://...@sentry.io/...

# Security
JWT_SECRET=your_jwt_secret
API_KEY=your_api_key

# AWS (if using)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## Configuration Best Practices

1. **Use Environment Variables**: Never hardcode sensitive data
2. **Separate Environments**: Use different configs for dev/staging/prod
3. **Version Control**: Track config changes in git (except secrets)
4. **Validation**: Validate all config on startup
5. **Documentation**: Document all config options
6. **Defaults**: Provide sensible defaults where possible
7. **Monitoring**: Alert on config changes in production

## Configuration Loading Order

1. Default configuration (built into code)
2. Base configuration file (base.yaml)
3. Environment-specific file (production.yaml)
4. Environment variables (override files)
5. Command-line arguments (highest priority)

Example:
```python
config = load_config(
    default="config/defaults.yaml",
    base="config/base.yaml",
    environment="config/production.yaml",
    env_prefix="AIRDROPS_",
    cli_args=sys.argv[1:]
)
```