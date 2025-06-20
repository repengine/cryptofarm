# LayerZero Protocol Module

## Overview

The LayerZero protocol module provides comprehensive functionality for interacting with the LayerZero omnichain interoperability protocol. This module enables users to send cross-chain messages, bridge tokens between different blockchains, and perform various cross-chain operations through LayerZero's unified infrastructure.

## Supported Operations

### Cross-Chain Messaging
- **Message Sending**: Send arbitrary data payloads between supported chains
- **Cross-Chain Calls**: Execute functions on remote chains
- **Omnichain Applications**: Build applications that span multiple blockchains

### Token Bridging
- **Native Token Bridging**: Bridge native tokens (ETH, MATIC, etc.) between chains
- **ERC20 Token Bridging**: Bridge supported ERC20 tokens across chains
- **Multi-hop Routing**: Automatic routing through intermediate chains when direct paths aren't available

### Random Bridge Operations
- **Automated Bridging**: Perform random bridge operations for airdrop farming
- **Multi-chain Support**: Support for Ethereum, Arbitrum, Optimism, Polygon, and other LayerZero-enabled chains

## Configuration

The module uses LayerZero's endpoint contracts deployed on each supported chain:

### Supported Chain IDs
- **Ethereum**: Chain ID 1 (LayerZero ID: 101)
- **Arbitrum**: Chain ID 42161 (LayerZero ID: 110)
- **Optimism**: Chain ID 10 (LayerZero ID: 111)
- **Polygon**: Chain ID 137 (LayerZero ID: 109)
- **BNB Chain**: Chain ID 56 (LayerZero ID: 102)

### Contract Addresses
- **LayerZero Endpoints**: Configured via `LAYERZERO_ENDPOINT_ADDRESSES` constant
- **Token Addresses**: Configured via `LAYERZERO_TOKEN_ADDRESSES` constant

## Functions

### `LayerZeroProtocol.__init__(rpc_url, private_key, chain_id)`

Initializes a LayerZero protocol instance for a specific chain.

**Parameters:**
- `rpc_url` (str): RPC URL for the source chain
- `private_key` (str): Private key of the wallet (64-character hex string with '0x' prefix)
- `chain_id` (int): Chain ID of the source blockchain

**Returns:**
- `LayerZeroProtocol`: Initialized protocol instance

**Example:**
```python
from airdrops.protocols.layerzero import LayerZeroProtocol

# Initialize for Ethereum mainnet
protocol = LayerZeroProtocol(
    rpc_url="https://mainnet.infura.io/v3/YOUR_KEY",
    private_key="0x...",
    chain_id=1
)
```

### `send_message(destination_chain_id, recipient_address, payload, value, gas_limit, zro_payment_address, adapter_params)`

Sends a cross-chain message via LayerZero.

**Parameters:**
- `destination_chain_id` (int): LayerZero chain ID of the destination
- `recipient_address` (str): Recipient address on the destination chain
- `payload` (bytes): Message payload to send
- `value` (int, optional): Native token value to send (in Wei, default: 0)
- `gas_limit` (int, optional): Gas limit for destination execution (default: 200000)
- `zro_payment_address` (str, optional): ZRO payment address (default: zero address)
- `adapter_params` (bytes, optional): Custom adapter parameters (default: empty)

**Returns:**
- `str`: Transaction hash of the message send operation

**Raises:**
- `MessageSendError`: If message sending fails
- `InsufficientBalanceError`: If balance is insufficient for fees
- `GasEstimationError`: If gas estimation fails

**Example:**
```python
# Send a cross-chain message from Ethereum to Arbitrum
tx_hash = protocol.send_message(
    destination_chain_id=110,  # Arbitrum LayerZero ID
    recipient_address="0x...",
    payload=b"Hello from Ethereum!",
    value=0,
    gas_limit=200000
)

print(f"Message sent with tx hash: {tx_hash}")
```

### `bridge(wallet, source_chain, destination_chain, token_symbol, amount, max_retries)`

Bridges tokens between chains using LayerZero.

**Parameters:**
- `wallet` (LocalAccount): Wallet account for the transaction
- `source_chain` (str): Source chain identifier
- `destination_chain` (str): Destination chain identifier  
- `token_symbol` (str): Token symbol to bridge
- `amount` (Decimal): Amount to bridge
- `max_retries` (int, optional): Maximum retry attempts (default: 3)

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
from eth_account import Account
from decimal import Decimal
from airdrops.protocols.layerzero import bridge

# Create wallet from private key
wallet = Account.from_key("0x...")

# Bridge 100 USDC from Ethereum to Arbitrum
success = bridge(
    wallet=wallet,
    source_chain="ethereum",
    destination_chain="arbitrum",
    token_symbol="USDC",
    amount=Decimal("100"),
    max_retries=3
)

if success:
    print("Bridge operation successful!")
else:
    print("Bridge operation failed.")
```

### `perform_random_bridge(wallet, available_chains, token_symbols, min_amount, max_amount, max_retries)`

Performs a random bridge operation for airdrop farming.

**Parameters:**
- `wallet` (LocalAccount): Wallet account for the transaction
- `available_chains` (list[str]): List of available chain identifiers
- `token_symbols` (list[str]): List of available token symbols
- `min_amount` (Decimal): Minimum amount to bridge
- `max_amount` (Decimal): Maximum amount to bridge
- `max_retries` (int, optional): Maximum retry attempts (default: 3)

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
from eth_account import Account
from decimal import Decimal
from airdrops.protocols.layerzero import perform_random_bridge

# Create wallet from private key
wallet = Account.from_key("0x...")

# Perform random bridge operation
success = perform_random_bridge(
    wallet=wallet,
    available_chains=["ethereum", "arbitrum", "optimism"],
    token_symbols=["USDC", "USDT"],
    min_amount=Decimal("10"),
    max_amount=Decimal("100"),
    max_retries=3
)

if success:
    print("Random bridge operation successful!")
```

### `get_message_status(tx_hash)`

Gets the status of a sent LayerZero message.

**Parameters:**
- `tx_hash` (str): Transaction hash of the send message operation

**Returns:**
- `Dict[str, Any]`: Dictionary containing message status details

**Example:**
```python
# Check message status
status = protocol.get_message_status("0x...")
print(f"Message status: {status['status']}")
print(f"Delivery timestamp: {status['delivery_timestamp']}")
```

### Utility Functions

#### `get_balance(address)`
Get native token balance for an address.

#### `get_gas_price()`
Get current gas price on the chain.

#### `get_transaction_count(address)`
Get transaction count (nonce) for an address.

#### `estimate_gas(transaction)`
Estimate gas required for a transaction.

## Error Handling

The module defines comprehensive custom exceptions for different error scenarios:

### Core Errors
- **`LayerZeroError`**: Base exception for LayerZero-related errors
- **`UnsupportedChainError`**: Raised when chain ID is not supported
- **`MessageSendError`**: Raised when message sending fails

### Transaction Errors
- **`InsufficientBalanceError`**: Raised when account balance is insufficient
- **`TransactionRevertedError`**: Raised when transaction is reverted
- **`TransactionBuildError`**: Raised when transaction building fails
- **`TransactionSendError`**: Raised when transaction sending fails
- **`MaxRetriesExceededError`**: Raised when max retries are exceeded

### Contract Interaction Errors
- **`ApprovalError`**: Raised when ERC20 approval fails
- **`GasEstimationError`**: Raised when gas estimation fails

## Security Considerations

- Private keys are never logged or stored
- All contract addresses are validated using checksums
- Transaction parameters are validated before execution
- Gas estimation is performed to prevent failed transactions
- Retry logic handles transient network issues
- Fee estimation prevents insufficient balance errors

## Gas Optimization

- Default gas limits are configured for different operation types
- Gas estimation is performed with safety multipliers (1.2x)
- Failed gas estimation triggers appropriate error handling
- Retry logic with exponential backoff for network issues

## Dependencies

- `web3.py`: Ethereum and multi-chain blockchain interaction
- `eth_account`: Account management and transaction signing
- `requests`: HTTP requests for external API calls
- `typing`: Type hints for better code clarity
- Standard library modules for JSON handling and logging

## Testing

Comprehensive unit tests cover:
- Successful message sending scenarios
- Token bridging operations with various routing scenarios
- Random bridge operations for airdrop farming
- Error handling for various failure modes
- Input validation and edge cases
- Contract interaction mocking
- Gas estimation and transaction building
- Retry logic and network failure handling

Run tests with:
```bash
pytest tests/protocols/test_layerzero.py -v
```

## Architecture Notes

The module is designed with reliability and cross-chain compatibility in mind:
- Modular helper functions for different operations
- Comprehensive error handling with specific exception types
- Retry logic for network-related failures with exponential backoff
- Support for custom adapter parameters
- Automatic fee estimation and validation
- Multi-chain routing support
- Configurable gas limits and retry parameters

## LayerZero Integration Details

### Message Flow
1. **Fee Estimation**: Calculate native and ZRO token fees
2. **Transaction Building**: Build send message transaction
3. **Transaction Execution**: Send transaction and wait for confirmation
4. **Relayer Processing**: LayerZero relayers pick up and process the message
5. **Destination Delivery**: Message is delivered to destination chain

### Supported Features
- **Arbitrary Message Passing**: Send any data between chains
- **Value Transfer**: Include native token value with messages
- **Custom Gas Limits**: Configure gas for destination execution
- **Adapter Parameters**: Use custom parameters for advanced features
- **Fee Payment Options**: Pay fees in native tokens or ZRO tokens

### Chain Compatibility
The module supports all LayerZero-enabled chains and automatically handles:
- Chain ID mapping between standard and LayerZero IDs
- Endpoint contract address resolution
- Network-specific configuration
- Gas price and limit optimization per chain