# Scroll Protocol Module

## Overview

The Scroll protocol module provides comprehensive functionality for interacting with the Scroll Layer 2 network. This module enables users to bridge assets between Ethereum (L1) and Scroll (L2), swap tokens on SyncSwap DEX, and perform lending/borrowing operations on LayerBank V2.

## Supported Operations

### Cross-Chain Bridging
- **ETH Bridging**: Bridge ETH between Ethereum mainnet and Scroll L2
- **ERC20 Token Bridging**: Bridge supported ERC20 tokens (USDC, etc.) between L1 and L2

### Token Swapping
- **SyncSwap Integration**: Swap tokens on SyncSwap DEX on Scroll L2
- **Multi-hop Routing**: Automatic routing through WETH for token pairs without direct pools
- **Slippage Protection**: Configurable slippage tolerance for swaps

### Lending & Borrowing
- **LayerBank V2 Integration**: Lend and borrow assets on LayerBank protocol
- **Supported Assets**: ETH and USDC lending/borrowing
- **Collateral Management**: Automatic market entry and liquidity checks

## Configuration

The module uses the following contract addresses on Scroll network:

### Gateway Router Addresses
- **L1 Gateway Router**: Configured via `SCROLL_L1_GATEWAY_ROUTER_ADDRESS`
- **L2 Gateway Router**: Configured via `SCROLL_L2_GATEWAY_ROUTER_ADDRESS`

### SyncSwap DEX Addresses
- **SyncSwap Router**: Configured via `SYNC_SWAP_ROUTER_ADDRESS_SCROLL`
- **Classic Pool Factory**: Configured via `SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL`

### LayerBank V2 Addresses
- **Comptroller**: Configured via `LAYERBANK_COMPTROLLER_ADDRESS_SCROLL`
- **lbETH Token**: Configured via `LAYERBANK_LBETH_ADDRESS_SCROLL`
- **lbUSDC Token**: Configured via `LAYERBANK_LBUSDC_ADDRESS_SCROLL`

## Functions

### `bridge_assets(web3_l1, web3_l2, private_key, token_symbol, amount, direction, l2_gas_limit, l2_gas_price)`

Bridges ETH or ERC20 tokens between L1 (Ethereum) and L2 (Scroll).

**Parameters:**
- `web3_l1` (Web3): Web3 instance for L1 (Ethereum)
- `web3_l2` (Web3): Web3 instance for L2 (Scroll)
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
from airdrops.protocols.scroll import bridge_assets

# Initialize Web3 connections
w3_l1 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))
w3_l2 = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))

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

### `swap_tokens(web3_scroll, private_key, token_in_symbol, token_out_symbol, amount_in, slippage_percent, deadline_seconds)`

Swaps tokens on SyncSwap DEX on the Scroll network.

**Parameters:**
- `web3_scroll` (Web3): Web3 instance for Scroll L2
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
from airdrops.protocols.scroll import swap_tokens

# Initialize Web3 connection to Scroll
w3_scroll = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))

# Swap 0.1 ETH for USDC with 1% slippage
tx_hash = swap_tokens(
    web3_scroll=w3_scroll,
    private_key="0x...",
    token_in_symbol="ETH",
    token_out_symbol="USDC",
    amount_in=100000000000000000,  # 0.1 ETH in wei
    slippage_percent=1.0,
    deadline_seconds=3600
)

print(f"Swap transaction hash: {tx_hash}")
```

### `lend_borrow_layerbank_scroll(web3_scroll, private_key, action, token_symbol, amount)`

Handles lending, borrowing, repaying, and withdrawing assets on LayerBank V2 on Scroll.

**Parameters:**
- `web3_scroll` (Web3): Web3 instance for Scroll L2
- `private_key` (str): Private key of the account
- `action` (str): Action to perform ("lend", "borrow", "repay", "withdraw")
- `token_symbol` (str): Token symbol ("ETH" or "USDC")
- `amount` (int): Amount in Wei for ETH, smallest unit for USDC

**Returns:**
- `str`: Transaction hash of the operation

**Example:**
```python
from web3 import Web3
from airdrops.protocols.scroll import lend_borrow_layerbank_scroll

# Initialize Web3 connection to Scroll
w3_scroll = Web3(Web3.HTTPProvider("https://rpc.scroll.io"))

# Lend 0.5 ETH to LayerBank
tx_hash = lend_borrow_layerbank_scroll(
    web3_scroll=w3_scroll,
    private_key="0x...",
    action="lend",
    token_symbol="ETH",
    amount=500000000000000000  # 0.5 ETH in wei
)

print(f"Lending transaction hash: {tx_hash}")
```

## Error Handling

The module defines comprehensive custom exceptions for different error scenarios:

### Bridge Errors
- **`ScrollBridgeError`**: Base exception for bridging operation failures
- **`InsufficientBalanceError`**: Raised when account balance is insufficient
- **`TokenNotSupportedError`**: Raised when token symbol is not configured
- **`ApprovalError`**: Raised when ERC20 approval fails
- **`GasEstimationError`**: Raised when gas estimation fails
- **`TransactionRevertedError`**: Raised when transaction is reverted

### Swap Errors
- **`ScrollSwapError`**: Base exception for swap-related errors
- **`InsufficientLiquidityError`**: Raised when liquidity is insufficient or no path found

### Lending Errors
- **`ScrollLendingError`**: Base exception for lending-related errors
- **`InsufficientCollateralError`**: Raised when insufficient collateral for borrowing
- **`RepayAmountExceedsDebtError`**: Raised when repay amount exceeds current debt
- **`LayerBankComptrollerRejectionError`**: Raised when LayerBank Comptroller rejects operation

## Security Considerations

- Private keys are never logged or stored
- All contract addresses are validated using checksums
- Transaction parameters are validated before execution
- Gas estimation is performed to prevent failed transactions
- Slippage protection prevents excessive value loss in swaps
- Collateral checks prevent unsafe borrowing operations

## Gas Optimization

- Default gas limits are configured for different operation types
- Gas estimation is performed with safety multipliers
- Failed gas estimation triggers appropriate error handling
- Retry logic handles transient network issues

## Dependencies

- `web3.py`: Ethereum and Scroll blockchain interaction
- `eth_abi`: ABI encoding for complex contract interactions
- `hexbytes`: Handling of hexadecimal byte data
- `eth_account`: Account management and transaction signing
- `typing`: Type hints for better code clarity
- Standard library modules for JSON handling and logging

## Testing

Comprehensive unit tests cover:
- Successful bridging scenarios for ETH and ERC20 tokens
- Token swapping with various routing scenarios
- LayerBank lending, borrowing, and repaying operations
- Error handling for various failure modes
- Input validation and edge cases
- Contract interaction mocking
- Gas estimation and transaction building

Run tests with:
```bash
pytest tests/protocols/test_scroll.py -v
```

## Architecture Notes

The module is designed with modularity and reliability in mind:
- Separate helper functions for different operations
- Comprehensive error handling with specific exception types
- Retry logic for network-related failures
- Automatic market entry for LayerBank operations
- Multi-hop routing support for SyncSwap swaps
- Configurable parameters for gas limits and slippage