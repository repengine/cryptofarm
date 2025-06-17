# Mock Testing Framework

## Overview

The Mock Testing Framework provides comprehensive wallet mocking capabilities for blockchain interaction testing. This framework enables robust testing of wallet interaction scenarios including security breaches, insufficient funds, and network failures without requiring actual blockchain transactions.

## Architecture

### Abstract Base Class

The framework is built around the `MockWallet` abstract base class that defines a standardized interface for all wallet mock implementations:

```python
from tests.mocks.wallets import MockWallet
```

### Core Features

- **Balance Management**: Track and modify wallet balances with Wei precision
- **Transaction Simulation**: Generate deterministic transaction hashes for reproducible tests
- **Nonce Tracking**: Maintain transaction nonce state across operations
- **Transaction History**: Complete history of all wallet transactions
- **Error Simulation**: Configurable failure scenarios for comprehensive testing

## Wallet Types

### NormalMockWallet

Standard wallet implementation for normal operation testing:

```python
from tests.mocks.wallets import NormalMockWallet

wallet = NormalMockWallet(
    address="0x1234567890123456789012345678901234567890",
    private_key="0xabcdef...",
    balance=1000000000000000000  # 1 ETH in Wei
)

# Send transaction
tx_hash = wallet.send_transaction({
    'to': '0x...',
    'value': 500000000000000000,  # 0.5 ETH
    'gas': 21000,
    'gasPrice': 20000000000
})
```

### SecurityBreachMockWallet

Simulates security incidents and unauthorized transactions:

```python
from tests.mocks.wallets import SecurityBreachMockWallet

wallet = SecurityBreachMockWallet(
    address="0x1234567890123456789012345678901234567890",
    private_key="0xabcdef...",
    balance=1000000000000000000,
    breach_probability=0.3  # 30% chance of breach per transaction
)

# May trigger security breach
try:
    tx_hash = wallet.send_transaction(tx_params)
except Exception as e:
    print(f"Security breach detected: {e}")
```

### InsufficientFundsMockWallet

Tests insufficient balance scenarios with configurable gas cost calculations:

```python
from tests.mocks.wallets import InsufficientFundsMockWallet

wallet = InsufficientFundsMockWallet(
    address="0x1234567890123456789012345678901234567890",
    private_key="0xabcdef...",
    balance=100000000000000000,  # 0.1 ETH
    gas_multiplier=2.0  # Double gas costs for testing
)

# Will raise InsufficientFundsError if total cost exceeds balance
tx_hash = wallet.send_transaction(tx_params)
```

### NetworkFailureMockWallet

Simulates network connectivity issues and transaction failures:

```python
from tests.mocks.wallets import NetworkFailureMockWallet

wallet = NetworkFailureMockWallet(
    address="0x1234567890123456789012345678901234567890",
    private_key="0xabcdef...",
    balance=1000000000000000000,
    failure_probability=0.2  # 20% chance of network failure
)

# May raise NetworkError
try:
    tx_hash = wallet.send_transaction(tx_params)
except Exception as e:
    print(f"Network failure: {e}")
```

## Usage Examples

### Basic Testing

```python
import pytest
from tests.mocks.wallets import NormalMockWallet

def test_wallet_transaction():
    wallet = NormalMockWallet(
        address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef...",
        balance=1000000000000000000
    )
    
    initial_balance = wallet.get_balance()
    
    tx_hash = wallet.send_transaction({
        'to': '0x9876543210987654321098765432109876543210',
        'value': 500000000000000000,
        'gas': 21000,
        'gasPrice': 20000000000
    })
    
    assert wallet.get_balance() < initial_balance
    assert len(wallet.get_transaction_history()) == 1
    assert wallet.get_nonce() == 1
```

### Error Scenario Testing

```python
def test_insufficient_funds():
    wallet = InsufficientFundsMockWallet(
        address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef...",
        balance=100000000000000000  # 0.1 ETH
    )
    
    with pytest.raises(Exception, match="Insufficient funds"):
        wallet.send_transaction({
            'to': '0x9876543210987654321098765432109876543210',
            'value': 1000000000000000000,  # 1 ETH - more than balance
            'gas': 21000,
            'gasPrice': 20000000000
        })
```

### Integration Testing

```python
def test_multiple_wallet_types():
    wallets = [
        NormalMockWallet("0x1111...", "0xkey1", 1000000000000000000),
        SecurityBreachMockWallet("0x2222...", "0xkey2", 1000000000000000000, 0.1),
        InsufficientFundsMockWallet("0x3333...", "0xkey3", 100000000000000000),
        NetworkFailureMockWallet("0x4444...", "0xkey4", 1000000000000000000, 0.1)
    ]
    
    for wallet in wallets:
        try:
            tx_hash = wallet.send_transaction({
                'to': '0x9876543210987654321098765432109876543210',
                'value': 50000000000000000,  # 0.05 ETH
                'gas': 21000,
                'gasPrice': 20000000000
            })
            print(f"Transaction successful: {tx_hash}")
        except Exception as e:
            print(f"Transaction failed: {e}")
```

## Testing Coverage

The framework includes comprehensive test coverage with 23 test cases covering:

- **Basic Functionality**: Balance management, transaction sending, nonce tracking
- **Edge Cases**: Zero balances, maximum values, invalid parameters
- **Error Scenarios**: Insufficient funds, security breaches, network failures
- **Integration**: Multi-wallet scenarios, transaction history validation
- **Type Safety**: Full mypy --strict compliance with proper type annotations

## Implementation Details

### Deterministic Transaction Hashes

All wallet implementations generate deterministic transaction hashes based on:
- Wallet address
- Transaction parameters (to, value, gas, gasPrice)
- Current nonce
- Timestamp

This ensures reproducible test results while maintaining realistic transaction hash formats.

### Type Safety

The framework is fully typed with mypy --strict compliance:
- All methods have proper return type annotations
- Generic types are properly parameterized
- Custom type aliases for blockchain-specific types (Address, HexStr)
- Comprehensive error handling with typed exceptions

### Performance Considerations

- O(1) balance operations
- O(n) transaction history retrieval where n is number of transactions
- Minimal memory footprint with efficient data structures
- No external dependencies beyond standard library and web3 types

## Future Enhancements

Planned improvements include:
- Multi-signature wallet mocking
- ERC-20 token balance tracking
- Gas estimation simulation
- Block confirmation simulation
- Event log generation
- Integration with actual test networks for hybrid testing