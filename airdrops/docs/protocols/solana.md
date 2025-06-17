# Solana Protocol Module

This document outlines the design, configuration, and usage of the Solana protocol module within the Airdrops Automation project.

## 1. Overview

The Solana module provides core functionality for interacting with the Solana blockchain, including network connection, balance checking, and SOL transfers.

**Current Capabilities:**
- ✅ Protocol initialization and configuration
- ✅ Solana RPC client integration
- ✅ Keypair management and wallet operations
- ✅ SOL balance queries
- ✅ SOL transfers between addresses
- ✅ Comprehensive error handling with custom exceptions
- ✅ Type-safe interface design
- ✅ Full test coverage with mocked dependencies

**Planned Functionalities (Future Development):**
- SPL token interactions
- DeFi protocol integrations (Jupiter, Raydium, etc.)
- NFT operations
- Staking and delegation
- Cross-chain bridging

## 2. Configuration

The Solana protocol requires the following configuration parameters:

```python
SOLANA_CONFIG = {
    "rpc_url": "https://api.devnet.solana.com",  # or mainnet-beta
    "private_key": "your_base58_encoded_private_key",
    "commitment": "confirmed"  # processed, confirmed, or finalized
}
```

### Environment Variables

Set the following environment variables for production use:

```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key_here
SOLANA_COMMITMENT=confirmed
```

## 3. Usage Examples

### Basic Initialization

```python
from airdrops.protocols.solana import SolanaProtocol

# Initialize the protocol
protocol = SolanaProtocol(
    rpc_url="https://api.devnet.solana.com",
    private_key="your_private_key",
    commitment="confirmed"
)

# Get connection information
info = protocol.get_connection_info()
print(f"Connected to: {info['rpc_url']}")
print(f"Public key: {info['public_key']}")
```

### Balance Operations

```python
# Check SOL balance
balance = protocol.get_balance()
print(f"Current balance: {balance} SOL")
```

### SOL Transfers

```python
# Transfer SOL to another address
try:
    signature = protocol.transfer_sol(
        recipient_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        amount_sol=0.1
    )
    print(f"Transfer successful! Signature: {signature}")
except SolanaError as e:
    print(f"Transfer failed: {e}")
```

### Error Handling

```python
from airdrops.protocols.solana import SolanaError

try:
    protocol = SolanaProtocol("", "invalid_key")
except SolanaError as e:
    print(f"Configuration error: {e}")

try:
    balance = protocol.get_balance()
except SolanaError as e:
    print(f"Balance query failed: {e}")
```

## 4. Architecture

The module follows the established protocol patterns:

- **`SolanaProtocol`**: Main protocol class for blockchain interactions
- **`SolanaError`**: Base exception class for protocol-specific errors
- **Type Safety**: Full mypy compliance with strict type checking
- **Logging**: Integrated logging for debugging and monitoring
- **Dependency Injection**: Uses solana-py library for blockchain operations

### Core Methods

#### `__init__(rpc_url, private_key, commitment="confirmed")`
Initializes the protocol with Solana RPC client and keypair.

#### `get_balance() -> float`
Returns the SOL balance of the wallet as a float.

#### `transfer_sol(recipient_address, amount_sol) -> str`
Transfers SOL to a recipient and returns the transaction signature.

#### `get_connection_info() -> dict`
Returns connection details including RPC URL, commitment level, and public key.

## 5. Development Status

**Current Phase**: Core Functionality ✅
- [x] Basic module structure
- [x] Protocol class initialization
- [x] Solana client integration
- [x] Keypair management
- [x] Balance queries
- [x] SOL transfers
- [x] Error handling framework
- [x] Type annotations and documentation
- [x] Comprehensive unit tests

**Next Phase**: SPL Token Support (Planned)
- [ ] SPL token balance queries
- [ ] SPL token transfers
- [ ] Token account creation and management
- [ ] Multi-token operations

## 6. Testing

The module includes comprehensive test coverage with mocked dependencies:

```bash
# Run Solana protocol tests
pytest tests/protocols/test_solana.py -v

# Run with coverage
pytest tests/protocols/test_solana.py --cov=airdrops.protocols.solana

# Run specific test categories
pytest tests/protocols/test_solana.py -k "test_get_balance" -v
pytest tests/protocols/test_solana.py -k "test_transfer_sol" -v
```

### Test Coverage

- ✅ Protocol initialization (success and failure cases)
- ✅ Balance retrieval (success, failure, and edge cases)
- ✅ SOL transfers (success, validation, and error cases)
- ✅ Connection info retrieval
- ✅ Error handling and exception propagation
- ✅ Input validation and security checks

## 7. Dependencies

**Current Dependencies:**
- `solana` (0.36.6) - Official Solana Python SDK
- Standard library (logging, typing)

**Development Dependencies:**
- `pytest` - Testing framework
- `pytest-mock` - Mocking utilities
- `unittest.mock` - Built-in mocking support

## 8. Security Considerations

- ✅ Private keys are stored in memory only during execution
- ✅ Connection information excludes sensitive data
- ✅ Input validation for all configuration parameters
- ✅ Secure error handling without exposing sensitive information
- ✅ Address validation for transfer operations
- ✅ Amount validation to prevent negative transfers
- ✅ Transaction confirmation with configurable commitment levels

## 9. Error Handling

The module provides comprehensive error handling:

### SolanaError Types
- **Initialization errors**: Invalid RPC URL or private key
- **Network errors**: RPC connection failures
- **Transaction errors**: Failed transfers or invalid addresses
- **Validation errors**: Invalid amounts or addresses

### Error Context
All errors include descriptive messages and optional context for debugging.

## 10. Future Roadmap

1. **Phase 2**: SPL Token Support
   - Token transfers and approvals
   - Token account creation and management
   - Multi-token operations

2. **Phase 3**: DeFi Integration
   - DEX interactions (Jupiter, Raydium)
   - Lending protocol support
   - Yield farming strategies

3. **Phase 4**: Advanced Features
   - NFT operations
   - Staking and delegation
   - Cross-chain bridging
   - MEV protection strategies

---

*This module is part of the Airdrops Automation project's protocol expansion initiative.*