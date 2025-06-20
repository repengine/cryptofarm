# ZkSync Protocol Module

## Overview

The ZkSync protocol module provides comprehensive functionality for interacting with the ZkSync Era Layer 2 network. This module enables users to bridge assets between Ethereum (L1) and ZkSync Era (L2), and swap tokens on SyncSwap DEX within the ZkSync ecosystem.

## Supported Operations

### Cross-Chain Bridging
- **ETH Bridging**: Bridge ETH between Ethereum mainnet and ZkSync Era L2
- **ERC20 Token Bridging**: Bridge supported ERC20 tokens (USDC, USDT, DAI, WETH) between L1 and L2

### Token Swapping
- **SyncSwap Integration**: Swap tokens on SyncSwap DEX on ZkSync Era L2
- **Multi-hop Routing**: Automatic routing through WETH for token pairs without direct pools
- **Slippage Protection**: Configurable slippage tolerance for swaps

## Configuration

The module uses the following contract addresses on ZkSync Era network:

### Bridge Addresses
- **L1 Bridge**: Configured via `ZKSYNC_L1_BRIDGE_ADDRESS`
- **L2 Bridge**: Configured via `ZKSYNC_L2_BRIDGE_ADDRESS`

### SyncSwap DEX Addresses
- **SyncSwap Router**: Configured via `SYNC_SWAP_ROUTER_ADDRESS_ZKSYNC`
- **Classic Pool Factory**: Configured via `SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_ZKSYNC`

### Supported Tokens
The module supports the following tokens with both L1 and L2 addresses:
- **USDC**: USD Coin
- **USDT**: Tether USD
- **WETH**: Wrapped Ethereum
- **DAI**: Dai Stablecoin
- **ETH**: Native Ethereum (handled via WETH for L2 operations)

## Classes

### `ZkSyncProtocol`

High-level interface for ZkSync Era network interactions.

**Initialization:**
```python
protocol = ZkSyncProtocol(
    l1_rpc_url="https://mainnet.infura.io/v3/YOUR_KEY",
    l2_rpc_url="https://mainnet.era.zksync.io",
    private_key="0x..."
)
```

**Methods:**
- `bridge_assets(token_symbol, amount, direction)`: Bridge assets between L1 and L2
- `swap_tokens(from_token, to_token, amount)`: Swap tokens on ZkSync L2

## Functions

### `bridge_assets(web3_l1, web3_l2, private_key, token_symbol, amount, direction, l2_gas_limit, l2_gas_price)`

Bridges ETH or ERC20 tokens between L1 (Ethereum) and L2 (ZkSync Era).

**Parameters:**
- `web3_l1` (Web3): Web3 instance for L1 (Ethereum)
- `web3_l2` (Web3): Web3 instance for L2 (ZkSync Era)
- `private_key` (str): Private key of the account
- `token_symbol` (str): Symbol of the token to bridge (e.g., "ETH", "USDC")
- `amount` (int): Amount of token to bridge (in Wei for ETH, smallest unit for ERC20)
- `direction` (str): "deposit" (L1 to L2) or "withdraw" (L2 to L1)
- `l2_gas_limit` (int, optional): Gas limit for the L2 transaction (for deposits)
- `l2_gas_price` (int, optional): Gas price for the L2 transaction (for deposits)

**Returns:**
- `str`: Transaction hash of the bridge operation

**Example:**
```python
from web3 import Web3
from airdrops.protocols.zksync import bridge_assets

# Initialize Web3 connections
w3_l1 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))
w3_l2 = Web3(Web3.HTTPProvider("https://mainnet.era.zksync.io"))

# Bridge 0.1 ETH from L1 to L2
tx_hash = bridge_assets(
    web3_l1=w3_l1,
    web3_l2=w3_l2,
    private_key="0x...",
    token_symbol="ETH",
    amount=100000000000000000,  # 0.1 ETH in wei
    direction="deposit"
)

print(f"Bridge transaction hash: {tx_hash}")
```

### `swap_tokens(web3_zksync, private_key, token_in_symbol, token_out_symbol, amount_in, slippage_percent, deadline_seconds)`

Swaps tokens on SyncSwap DEX on the ZkSync Era network.

**Parameters:**
- `web3_zksync` (Web3): Web3 instance for ZkSync L2
- `private_key` (str): Private key of the account performing the swap
- `token_in_symbol` (str): Symbol of the token to swap from (e.g., "ETH", "USDC")
- `token_out_symbol` (str): Symbol of the token to swap to (e.g., "USDC", "WETH")
- `amount_in` (int): Amount of token_in to swap (in Wei or smallest unit)
- `slippage_percent` (float, optional): Allowed slippage percentage (default: 0.5%)
- `deadline_seconds` (int, optional): Transaction deadline in seconds from now (default: 1800)

**Returns:**
- `str`: Transaction hash of the swap operation

**Example:**
```python
from web3 import Web3
from airdrops.protocols.zksync import swap_tokens

# Initialize Web3 connection to ZkSync Era
w3_zksync = Web3(Web3.HTTPProvider("https://mainnet.era.zksync.io"))

# Swap 0.1 ETH for USDC with 1% slippage
tx_hash = swap_tokens(
    web3_zksync=w3_zksync,
    private_key="0x...",
    token_in_symbol="ETH",
    token_out_symbol="USDC",
    amount_in=100000000000000000,  # 0.1 ETH in wei
    slippage_percent=1.0,
    deadline_seconds=3600
)

print(f"Swap transaction hash: {tx_hash}")
```

## Error Handling

The module defines comprehensive custom exceptions for different error scenarios:

### Bridge Errors
- **`ZkSyncBridgeError`**: Base exception for bridging operation failures
- **`InsufficientBalanceError`**: Raised when account balance is insufficient
- **`TokenNotSupportedError`**: Raised when token symbol is not configured
- **`ApprovalError`**: Raised when ERC20 approval fails
- **`GasEstimationError`**: Raised when gas estimation fails
- **`TransactionRevertedError`**: Raised when transaction is reverted

### Swap Errors
- **`ZkSyncSwapError`**: Base exception for swap-related errors
- **`InsufficientLiquidityError`**: Raised when liquidity is insufficient or no path found

### Transaction Errors
- **`TransactionBuildError`**: Raised when transaction building fails
- **`TransactionSendError`**: Raised when transaction sending fails
- **`MaxRetriesExceededError`**: Raised when maximum retry attempts are exceeded

## Security Considerations

- Private keys are never logged or stored
- All contract addresses are validated using checksums
- Transaction parameters are validated before execution
- Gas estimation is performed to prevent failed transactions
- Slippage protection prevents excessive value loss in swaps
- Retry logic handles transient network issues with exponential backoff

## Gas Optimization

- Default gas limits are configured for different operation types
- Gas estimation is performed with safety multipliers (1.2x)
- Failed gas estimation triggers appropriate error handling
- Retry logic handles transient network issues
- Automatic nonce management prevents stuck transactions

## Dependencies

- `web3.py`: Ethereum and ZkSync blockchain interaction
- `eth_abi`: ABI encoding for complex contract interactions
- `hexbytes`: Handling of hexadecimal byte data
- `eth_account`: Account management and transaction signing
- `typing`: Type hints for better code clarity
- Standard library modules for JSON handling and logging

## Testing

Comprehensive unit tests cover:
- Successful bridging scenarios for ETH and ERC20 tokens
- Token swapping with various routing scenarios
- Error handling for various failure modes
- Input validation and edge cases
- Contract interaction mocking
- Gas estimation and transaction building
- Protocol class initialization and method calls

Run tests with:
```bash
pytest tests/protocols/test_zksync.py tests/protocols/test_zksync_coverage.py -v
```

## Architecture Notes

The module is designed with modularity and reliability in mind:
- Separate helper functions for different operations
- Comprehensive error handling with specific exception types
- Retry logic for network-related failures with configurable attempts
- Multi-hop routing support for SyncSwap swaps
- Configurable parameters for gas limits and slippage
- Class-based API for convenient high-level usage
- Module-level functions for fine-grained control
- Proper type hints throughout for better maintainability

## Network Configuration

### Mainnet
- **L1 RPC**: Ethereum mainnet RPC endpoint
- **L2 RPC**: `https://mainnet.era.zksync.io`
- **Chain ID**: 324

### Testnet
- **L1 RPC**: Ethereum testnet (Goerli/Sepolia) RPC endpoint  
- **L2 RPC**: `https://testnet.era.zksync.dev`
- **Chain ID**: 280

## Performance Considerations

- Connection pooling recommended for high-frequency operations
- Batch operations where possible to reduce gas costs
- Monitor gas prices for optimal transaction timing
- Use appropriate slippage settings based on market conditions
- Consider L2 gas price fluctuations for bridging operations