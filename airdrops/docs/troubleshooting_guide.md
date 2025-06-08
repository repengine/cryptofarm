# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Airdrops system. It covers installation problems, runtime errors, performance issues, and integration challenges.

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Connection Problems](#connection-problems)
3. [Transaction Failures](#transaction-failures)
4. [Performance Issues](#performance-issues)
5. [Configuration Errors](#configuration-errors)
6. [Protocol-Specific Issues](#protocol-specific-issues)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Recovery Procedures](#recovery-procedures)

## Installation Issues

### Poetry Installation Fails

**Problem**: Poetry installation hangs or fails with dependency conflicts.

**Solution**:
```bash
# Clear Poetry cache
poetry cache clear pypi --all

# Update Poetry
poetry self update

# Install with verbose output
poetry install -vvv

# If specific package fails
poetry add package_name --verbose
```

### Python Version Mismatch

**Problem**: Error about Python version requirements.

**Solution**:
```bash
# Check current Python version
python --version

# Use pyenv to install correct version
pyenv install 3.11.0
pyenv local 3.11.0

# Verify Poetry uses correct Python
poetry env use 3.11
poetry install
```

### Missing System Dependencies

**Problem**: Compilation errors for packages like `cytoolz` or `lru-dict`.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential python3-dev

# macOS
brew install python@3.11
xcode-select --install

# Windows
# Install Visual Studio Build Tools
```

## Connection Problems

### RPC Connection Failures

**Problem**: Cannot connect to Ethereum/L2 RPC endpoints.

**Symptoms**:
```
ConnectionError: HTTPSConnectionPool(host='mainnet.infura.io', port=443): Max retries exceeded
```

**Solutions**:

1. **Check RPC URL**:
```python
# Verify URL format
from web3 import Web3

# Test connection
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_KEY'))
print(f"Connected: {w3.is_connected()}")
print(f"Block number: {w3.eth.block_number}")
```

2. **Use Fallback RPCs**:
```yaml
# config.yaml
networks:
  ethereum:
    rpc_url: "https://mainnet.infura.io/v3/${INFURA_KEY}"
    fallback_rpcs:
      - "https://eth-mainnet.g.alchemy.com/v2/${ALCHEMY_KEY}"
      - "https://rpc.ankr.com/eth"
      - "https://eth.llamarpc.com"
```

3. **Implement Retry Logic**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def get_web3_connection(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {rpc_url}")
    return w3
```

### WebSocket Connection Drops

**Problem**: WebSocket connections disconnect frequently.

**Solution**:
```python
# Use persistent WebSocket with reconnection
from web3 import Web3
from web3.providers import WebsocketProvider

class PersistentWebsocket:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.w3 = None
        self.connect()
    
    def connect(self):
        self.w3 = Web3(WebsocketProvider(
            self.ws_url,
            websocket_timeout=60,
            websocket_kwargs={'ping_interval': 20}
        ))
    
    def get_connection(self):
        if not self.w3.is_connected():
            self.connect()
        return self.w3
```

## Transaction Failures

### Insufficient Gas

**Problem**: Transaction fails with "out of gas" error.

**Diagnosis**:
```python
# Check gas estimation
estimated_gas = contract.functions.method().estimate_gas({'from': address})
print(f"Estimated gas: {estimated_gas}")

# Add buffer
safe_gas = int(estimated_gas * 1.2)  # 20% buffer
```

**Solution**:
```python
def safe_transaction(contract_function, account, **kwargs):
    # Get current gas price
    gas_price = w3.eth.gas_price
    
    # Estimate gas with buffer
    estimated_gas = contract_function.estimate_gas({'from': account})
    gas_limit = int(estimated_gas * 1.2)
    
    # Build transaction
    tx = contract_function.build_transaction({
        'from': account,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account),
        **kwargs
    })
    
    return tx
```

### Nonce Issues

**Problem**: "nonce too low" or "replacement transaction underpriced" errors.

**Solution**:
```python
class NonceManager:
    def __init__(self, w3, address):
        self.w3 = w3
        self.address = address
        self.local_nonce = None
    
    def get_nonce(self):
        if self.local_nonce is None:
            self.local_nonce = self.w3.eth.get_transaction_count(self.address)
        else:
            self.local_nonce += 1
        return self.local_nonce
    
    def reset_nonce(self):
        self.local_nonce = None
```

### Transaction Stuck/Pending

**Problem**: Transaction remains pending for extended period.

**Solution**:
```python
def cancel_or_speed_up_tx(w3, tx_hash, private_key):
    try:
        # Get original transaction
        tx = w3.eth.get_transaction(tx_hash)
        
        # Create replacement with higher gas price
        new_gas_price = int(tx['gasPrice'] * 1.1)  # 10% increase
        
        replacement_tx = {
            'nonce': tx['nonce'],
            'to': tx['to'],
            'value': 0,  # For cancellation
            'gas': 21000,
            'gasPrice': new_gas_price
        }
        
        # Sign and send
        signed = w3.eth.account.sign_transaction(replacement_tx, private_key)
        new_tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        return new_tx_hash
    except Exception as e:
        print(f"Error replacing transaction: {e}")
```

## Performance Issues

### Slow Task Execution

**Problem**: Tasks taking longer than expected.

**Diagnosis Script**:
```python
import time
import cProfile
import pstats

def profile_function(func, *args, **kwargs):
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    
    profiler.disable()
    
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
    
    return result
```

**Common Optimizations**:

1. **Batch RPC Calls**:
```python
from web3.providers import HTTPProvider
from web3._utils.request import make_post_request

def batch_requests(w3, calls):
    """Execute multiple RPC calls in one request."""
    batch = []
    for i, call in enumerate(calls):
        batch.append({
            "jsonrpc": "2.0",
            "method": call["method"],
            "params": call["params"],
            "id": i
        })
    
    response = make_post_request(
        w3.provider.endpoint_uri,
        {"jsonrpc": "2.0", "method": "batch", "params": batch}
    )
    
    return response
```

2. **Cache Contract Instances**:
```python
class ContractCache:
    def __init__(self):
        self._cache = {}
    
    def get_contract(self, w3, address, abi):
        key = f"{w3.provider.endpoint_uri}:{address}"
        if key not in self._cache:
            self._cache[key] = w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
        return self._cache[key]
```

### High Memory Usage

**Problem**: System consuming excessive memory.

**Diagnosis**:
```python
import tracemalloc
import gc

# Start tracing
tracemalloc.start()

# Your code here
run_tasks()

# Get memory usage
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 10**6:.2f} MB")
print(f"Peak memory usage: {peak / 10**6:.2f} MB")

# Get top memory consumers
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)

# Clean up
gc.collect()
tracemalloc.stop()
```

## Configuration Errors

### Invalid Configuration Values

**Problem**: System fails to start due to configuration errors.

**Validation Script**:
```python
from jsonschema import validate, ValidationError

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "protocols": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["enabled"],
                "properties": {
                    "enabled": {"type": "boolean"},
                    "daily_activity_range": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0},
                        "minItems": 2,
                        "maxItems": 2
                    }
                }
            }
        }
    },
    "required": ["protocols"]
}

def validate_config(config):
    try:
        validate(config, CONFIG_SCHEMA)
        print("Configuration is valid")
    except ValidationError as e:
        print(f"Configuration error: {e.message}")
        print(f"Path: {' -> '.join(str(p) for p in e.path)}")
```

### Environment Variables Not Loading

**Problem**: Environment variables not being read correctly.

**Debug Script**:
```python
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(verbose=True)

# Check required variables
required_vars = [
    'ETHEREUM_RPC_URL',
    'WALLET_1_PRIVATE_KEY',
    'DB_HOST',
    'REDIS_HOST'
]

missing = []
for var in required_vars:
    value = os.getenv(var)
    if not value:
        missing.append(var)
    else:
        # Don't print sensitive values
        masked = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
        print(f"{var}: {masked}")

if missing:
    print(f"\nMissing variables: {', '.join(missing)}")
```

## Protocol-Specific Issues

### Scroll Bridge Failures

**Problem**: Bridge transactions fail or assets don't appear.

**Debugging Steps**:

1. **Check Bridge Status**:
```python
def check_bridge_status(l1_tx_hash):
    # Get L1 transaction
    l1_tx = w3_l1.eth.get_transaction_receipt(l1_tx_hash)
    
    # Find L1 to L2 message
    for log in l1_tx['logs']:
        if log['topics'][0] == DEPOSIT_INITIATED_TOPIC:
            l2_tx_hash = log['data']
            print(f"L2 transaction hash: {l2_tx_hash}")
            
            # Check L2 status
            try:
                l2_tx = w3_l2.eth.get_transaction_receipt(l2_tx_hash)
                print(f"L2 status: {'Success' if l2_tx['status'] else 'Failed'}")
            except:
                print("L2 transaction not yet processed")
```

2. **Verify Contract Addresses**:
```python
SCROLL_CONTRACTS = {
    'mainnet': {
        'l1_gateway': '0xD8A791fE2bE73eb6E6cF1eb0cb3F36adC9B3F8f9',
        'l2_gateway': '0x4C0926FF5252A435FD19e10ED15e5a249Ba19d79'
    },
    'testnet': {
        'l1_gateway': '0xe5E30E7c24e4dFcb281A682562E53154C15D3332',
        'l2_gateway': '0x91e8ADDFe1358aCa5314c644312d38237fC1101C'
    }
}
```

### zkSync Account Abstraction Issues

**Problem**: AA transactions fail with unclear errors.

**Solution**:
```python
from zksync2.module.module_builder import ZkSyncBuilder
from zksync2.core.types import EIP712Meta

def debug_aa_transaction(provider_url, account_address):
    # Initialize zkSync provider
    zk_web3 = ZkSyncBuilder.build(provider_url)
    
    # Check if account is deployed
    code = zk_web3.eth.get_code(account_address)
    if code == '0x':
        print("Account not deployed. Need to deploy AA wallet first.")
        return
    
    # Check paymaster balance if using
    paymaster_params = {
        "paymaster": PAYMASTER_ADDRESS,
        "paymasterInput": "0x"
    }
    
    # Verify paymaster has funds
    paymaster_balance = zk_web3.eth.get_balance(PAYMASTER_ADDRESS)
    print(f"Paymaster balance: {Web3.from_wei(paymaster_balance, 'ether')} ETH")
```

### Hyperliquid WebSocket Issues

**Problem**: WebSocket connection to Hyperliquid drops frequently.

**Solution**:
```python
import websocket
import json
from threading import Thread
import time

class HyperliquidWebSocket:
    def __init__(self, on_message):
        self.url = "wss://api.hyperliquid.xyz/ws"
        self.ws = None
        self.on_message = on_message
        self.running = True
        
    def connect(self):
        def on_open(ws):
            print("Connected to Hyperliquid")
            # Subscribe to channels
            ws.send(json.dumps({
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": "ETH"}
            }))
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        def on_close(ws, close_code, close_msg):
            print(f"WebSocket closed: {close_code} - {close_msg}")
            if self.running:
                time.sleep(5)  # Wait before reconnecting
                self.connect()
        
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=on_open,
            on_message=self.on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run in separate thread
        wst = Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
```

## Monitoring and Alerting

### Metrics Not Collecting

**Problem**: Prometheus metrics not showing up.

**Debug Steps**:

1. **Check Metrics Endpoint**:
```bash
curl http://localhost:9090/metrics
```

2. **Verify Metric Registration**:
```python
from prometheus_client import REGISTRY

# List all registered metrics
for collector in REGISTRY._collector_to_names:
    print(f"Collector: {collector}")
    print(f"Metrics: {REGISTRY._collector_to_names[collector]}")
```

### Alerts Not Firing

**Problem**: Alerts configured but not triggering.

**Debug Checklist**:

1. **Test Alert Manually**:
```python
from airdrops.monitoring.alerter import Alerter

alerter = Alerter(config)

# Send test alert
alerter.send_alert({
    "title": "Test Alert",
    "message": "This is a test alert",
    "severity": "warning",
    "details": {"test": True}
})
```

2. **Check Alert Rules**:
```python
# Verify alert conditions
def test_alert_condition(metric_value, rule):
    condition = rule['condition']
    threshold = rule['threshold']
    
    if 'less_than' in condition:
        should_alert = metric_value < threshold
    elif 'greater_than' in condition:
        should_alert = metric_value > threshold
    
    print(f"Metric: {metric_value}, Threshold: {threshold}")
    print(f"Should alert: {should_alert}")
    
    return should_alert
```

## Recovery Procedures

### System Crash Recovery

**Steps to recover after unexpected shutdown**:

1. **Check System State**:
```bash
# Check if processes are running
ps aux | grep airdrops

# Check last logs
tail -n 100 /var/log/airdrops/error.log
```

2. **Recover Pending Transactions**:
```python
from airdrops.shared.state_manager import StateManager

state_manager = StateManager(config)

# Get pending transactions
pending = state_manager.get_pending_transactions()
for tx in pending:
    print(f"Pending TX: {tx['hash']} on {tx['protocol']}")
    
    # Check status
    receipt = w3.eth.get_transaction_receipt(tx['hash'])
    if receipt:
        print(f"Status: {'Success' if receipt['status'] else 'Failed'}")
    else:
        print("Still pending")
```

3. **Resume Operations**:
```python
# Recover task queue
from airdrops.scheduler.bot import CentralScheduler

scheduler = CentralScheduler(config)
scheduler.recover_from_checkpoint()

# Resume with reduced load
scheduler.set_concurrency_limit(2)  # Start slow
scheduler.start()
```

### Database Corruption

**Problem**: Database queries failing or returning corrupted data.

**Recovery Steps**:

1. **Backup Current State**:
```bash
pg_dump -h localhost -U airdrops -d airdrops > backup_$(date +%Y%m%d_%H%M%S).sql
```

2. **Check Database Integrity**:
```sql
-- Check for corruption
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');

-- Verify indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public';

-- Check constraints
SELECT conname, contype, conrelid::regclass 
FROM pg_constraint 
WHERE connamespace = 'public'::regnamespace;
```

3. **Repair Tables**:
```sql
-- Reindex
REINDEX TABLE transactions;
REINDEX TABLE positions;

-- Vacuum and analyze
VACUUM ANALYZE;

-- If severe corruption
ALTER TABLE transactions RENAME TO transactions_corrupt;
CREATE TABLE transactions AS SELECT * FROM transactions_corrupt WHERE id IS NOT NULL;
```

### Wallet Compromise

**CRITICAL: If wallet compromise is suspected**:

1. **Immediate Actions**:
```python
# Emergency withdrawal script
import asyncio

async def emergency_withdraw(compromised_wallet, safe_wallet):
    # Get all positions
    positions = await get_all_positions(compromised_wallet)
    
    # Withdraw from all protocols
    for position in positions:
        try:
            if position['type'] == 'lending':
                await withdraw_lending(position, safe_wallet)
            elif position['type'] == 'liquidity':
                await remove_liquidity(position, safe_wallet)
            elif position['type'] == 'staking':
                await unstake(position, safe_wallet)
        except Exception as e:
            print(f"Failed to withdraw {position}: {e}")
            # Continue with other positions
    
    # Transfer remaining tokens
    await transfer_all_tokens(compromised_wallet, safe_wallet)
```

2. **Post-Incident**:
- Revoke all token approvals
- Update configuration with new wallets
- Review security practices
- Implement additional safeguards

## Common Error Messages

### Error Reference Table

| Error Message | Likely Cause | Solution |
|--------------|--------------|-----------|
| `execution reverted: insufficient allowance` | Token approval needed | Call `approve()` before operation |
| `nonce too low` | Transaction already processed | Reset nonce manager |
| `insufficient funds for gas * price + value` | Not enough ETH | Add ETH to wallet |
| `replacement transaction underpriced` | Gas price too low for replacement | Increase gas by >10% |
| `transaction underpriced` | Gas price below network minimum | Check current gas prices |
| `contract not found` | Wrong network or address | Verify network and contract address |
| `invalid opcode` | Contract bug or wrong network | Check contract verification |
| `stack too deep` | Solidity limitation | Simplify transaction |

## Getting Help

If issues persist after trying these solutions:

1. **Check Logs**: Enable debug logging
```python
import logging
logging.getLogger('airdrops').setLevel(logging.DEBUG)
```

2. **Community Support**: 
- Discord: [Project Discord]
- GitHub Issues: [Create detailed issue]

3. **Include in Bug Reports**:
- System configuration
- Error messages and stack traces
- Steps to reproduce
- Transaction hashes (if applicable)
- Log files (sanitized)