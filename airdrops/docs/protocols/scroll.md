# Scroll Protocol Module

This document provides an overview of the Scroll protocol module and its functionalities.

## Overview

The Scroll module (`airdrops.protocols.scroll`) facilitates interaction with the Scroll Layer 2 network, supporting asset bridging between Ethereum (L1) and Scroll (L2), DEX token swapping via SyncSwap, liquidity provision, and lending/borrowing via LayerBank V2 protocol.

## Functions

### `swap_tokens`

**Purpose:**

Swaps tokens on the SyncSwap DEX on the Scroll L2 network. Supports direct and multi-hop swaps between supported tokens (e.g., ETH, WETH, USDC, USDT).

**Parameters:**

- `web3_scroll` (`Web3`): Web3 instance for Scroll L2.
- `private_key` (`str`): Private key of the account performing the swap.
- `token_in_symbol` (`str`): Symbol of the token to swap from (e.g., "ETH", "USDC").
- `token_out_symbol` (`str`): Symbol of the token to swap to (e.g., "USDC", "WETH").
- `amount_in` (`int`): Amount of token_in to swap (in Wei or smallest unit).
- `slippage_percent` (`float`, default: `0.5`): Allowed slippage percentage.
- `deadline_seconds` (`int`, default: `1800`): Transaction deadline in seconds from now.

**Returns:**

- `str`: Transaction hash of the swap operation.

**Raises:**

- `ScrollSwapError`: For general swap-related errors.
- `InsufficientLiquidityError`: If liquidity is insufficient for the swap.
- `TokenNotSupportedError`: If one of the token symbols is not configured.
- `ApprovalError`: If token approval fails.
- `TransactionRevertedError`: If the swap transaction is reverted.
- `GasEstimationError`: If gas estimation fails.
- `ValueError`: For invalid inputs like slippage.

**Usage Example:**

```python
from web3 import Web3
from airdrops.protocols.scroll import swap_tokens
from airdrops.shared.config import SCROLL_L2_RPC_URL

web3_scroll = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))
private_key = "0x..."
tx_hash = swap_tokens(
    web3_scroll=web3_scroll,
    private_key=private_key,
    token_in_symbol="ETH",
    token_out_symbol="USDC",
    amount_in=10**18,  # 1 ETH in Wei
    slippage_percent=0.5,
    deadline_seconds=1800,
)
print("Swap transaction hash:", tx_hash)
---

### `provide_liquidity_scroll`

**Purpose:**

Adds or removes liquidity for a token pair on SyncSwap DEX on the Scroll L2 network. Supports both ETH-token and token-token pairs, and handles LP token approval, slippage, and deadlines.

**Parameters:**

- `web3_scroll` (`Web3`): Web3 instance for Scroll L2.
- `private_key` (`str`): Private key of the account.
- `action` (`str`): "add" to add liquidity, "remove" to remove liquidity.
- `token_a_symbol` (`str`): Symbol of the first token (e.g., "ETH", "USDC").
- `token_b_symbol` (`str`): Symbol of the second token (e.g., "USDC", "WETH").
- `amount_a_desired` (`int`, optional): Desired amount of token_a to add (required for "add").
- `amount_b_desired` (`int`, optional): Desired amount of token_b to add (required for "add").
- `lp_token_amount` (`int`, optional): Amount of LP tokens to remove (required for "remove").
- `slippage_percent` (`float`, default: `0.5`): Allowed slippage percentage.
- `deadline_seconds` (`int`, default: `1800`): Transaction deadline in seconds from now.

**Returns:**

- `str`: Transaction hash of the add/remove liquidity operation.

**Raises:**

- `InsufficientLiquidityError`: For pool not found or insufficient liquidity.
- `InsufficientBalanceError`: If balances are insufficient.
- `ApprovalError`: If token approval fails.
- `TransactionRevertedError`: If the transaction is reverted.
- `ValueError`: For invalid inputs.

**Usage Example:**

```python
from web3 import Web3
from airdrops.protocols.scroll import provide_liquidity_scroll
from airdrops.shared.config import SCROLL_L2_RPC_URL

web3_scroll = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))
private_key = "0x..."

# Add liquidity (ETH-USDC)
tx_hash = provide_liquidity_scroll(
    web3_scroll=web3_scroll,
    private_key=private_key,
    action="add",
    token_a_symbol="ETH",
    token_b_symbol="USDC",
    amount_a_desired=10**18,  # 1 ETH
    amount_b_desired=2 * 10**6,  # 2 USDC (assuming 6 decimals)
    slippage_percent=0.5,
    deadline_seconds=1800,
)
print("Add liquidity tx hash:", tx_hash)

# Remove liquidity
tx_hash = provide_liquidity_scroll(
    web3_scroll=web3_scroll,
    private_key=private_key,
    action="remove",
    token_a_symbol="ETH",
    token_b_symbol="USDC",
    lp_token_amount=10**18,  # Amount of LP tokens to burn
    slippage_percent=0.5,
    deadline_seconds=1800,
)
print("Remove liquidity tx hash:", tx_hash)
```
```
### `bridge_assets`

**Purpose:**

Bridges assets (ETH or supported ERC20 tokens) between Ethereum (L1) and Scroll (L2). This function handles both deposits (L1 to L2) and withdrawals (L2 to L1).

**Parameters:**

*   `web3_l1` (`Web3`): An initialized Web3 instance connected to the L1 network (Ethereum).
*   `web3_l2` (`Web3`): An initialized Web3 instance connected to the L2 network (Scroll).
*   `private_key` (`str`): The private key of the account performing the bridge operation.
*   `direction` (`str`): The direction of the bridge. Must be either `"deposit"` (for L1 to L2) or `"withdraw"` (for L2 to L1).
*   `token_symbol` (`str`): The symbol of the token to bridge. Supported tokens are "ETH", "WETH", "USDC", "USDT".
*   `amount` (`int`): The amount of the token to bridge, specified in its smallest unit (Wei for ETH/WETH, atomic units for ERC20s).
*   `recipient_address` (`Optional[str]`, default: `None`): The address that will receive the bridged assets on the destination chain. If `None`, the assets will be sent to the sender's address.

**Returns:**

*   `str`: The transaction hash of the main bridging transaction.

**Raises:**

*   `ValueError`: If an invalid `direction` or `token_symbol` is provided.
*   `InsufficientBalanceError`: If the account has an insufficient balance for the transaction or associated fees.
*   `TransactionRevertedError`: If the bridging transaction (or approval) is reverted on-chain. Includes receipt.
*   `RPCError`: If there's an issue communicating with the L1 or L2 RPC endpoints. (Note: Often wrapped by `MaxRetriesExceededError`)
*   `ApprovalError`: If an ERC20 token approval fails during a deposit. Inherits from `TransactionRevertedError`.
*   `GasEstimationError`: If gas estimation for the transaction fails.
*   `MaxRetriesExceededError`: If a transaction fails after multiple retries due to transient network issues.
*   `TransactionBuildError`: If there's an error building the transaction (e.g., signing).
*   `TransactionSendError`: If there's an error sending the transaction after retries.
*   `ScrollBridgeError`: For other Scroll bridge specific errors.

**Usage Example:**

```python
from web3 import Web3
from decimal import Decimal
from airdrops.protocols.scroll import bridge_assets
from airdrops.shared.config import SCROLL_L1_RPC_URL, SCROLL_L2_RPC_URL # Assuming RPC URLs are in config

# Initialize Web3 instances (replace with your actual RPC URLs)
web3_l1 = Web3(Web3.HTTPProvider(SCROLL_L1_RPC_URL))
web3_l2 = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))

# Account details (replace with your actual private key)
my_private_key = "0x..." 
my_address = web3_l1.eth.account.from_key(my_private_key).address

# Example: Deposit 0.01 ETH from L1 to L2
try:
    tx_hash_deposit_eth = bridge_assets(
        web3_l1=web3_l1,
        web3_l2=web3_l2,
        private_key=my_private_key,
        direction="deposit",
        token_symbol="ETH",
        amount=web3_l1.to_wei(Decimal("0.01"), "ether"),
        recipient_address=my_address  # Optional, defaults to sender
    )
    print(f"ETH Deposit initiated. Tx Hash: {tx_hash_deposit_eth}")
except Exception as e:
    print(f"Error during ETH deposit: {e}")

# Example: Withdraw 10 USDC from L2 to L1
# Ensure you have USDC on L2 and it's one of the configured tokens
try:
    # Amount for USDC (assuming 6 decimals)
    usdc_amount_atomic = int(Decimal("10") * (10**6)) 
    tx_hash_withdraw_usdc = bridge_assets(
        web3_l1=web3_l1,
        web3_l2=web3_l2,
        private_key=my_private_key,
        direction="withdraw",
        token_symbol="USDC",
        amount=usdc_amount_atomic,
        recipient_address=my_address
    )
    print(f"USDC Withdrawal initiated. Tx Hash: {tx_hash_withdraw_usdc}")
except Exception as e:
    print(f"Error during USDC withdrawal: {e}")
```

### `swap_tokens`

**Purpose:**

Swaps tokens on the SyncSwap decentralized exchange (DEX) on the Scroll L2 network. It supports ETH-to-Token, Token-to-ETH, and Token-to-Token swaps.

**Parameters:**

*   `web3_scroll` (`Web3`): An initialized Web3 instance connected to the Scroll L2 network.
*   `private_key` (`str`): The private key of the account performing the swap.
*   `token_in_symbol` (`str`): Symbol of the token to swap from (e.g., "ETH", "USDC").
*   `token_out_symbol` (`str`): Symbol of the token to swap to (e.g., "USDC", "WETH", "ETH").
*   `amount_in` (`int`): Amount of `token_in` to swap, specified in its smallest unit (Wei for ETH/WETH, atomic units for ERC20s).
*   `slippage_percent` (`float`, default: `0.5`): Allowed slippage percentage (e.g., 0.5 for 0.5%). This is used to calculate the minimum acceptable amount of `token_out`.
*   `deadline_seconds` (`int`, default: `1800`): Transaction deadline in seconds from the current block timestamp (e.g., 1800 for 30 minutes).

**Returns:**

*   `str`: The transaction hash of the swap operation.

**Supported Swap Types:**

*   **ETH to ERC20 Token:** e.g., ETH -> USDC.
*   **ERC20 Token to ETH:** e.g., USDC -> ETH. (ETH is received as native ETH)
*   **ERC20 Token to ERC20 Token:** e.g., USDC -> USDT, or WETH -> USDC.

**Raises:**

*   `ValueError`: If `amount_in` is not positive or `slippage_percent` is out of range.
*   `TokenNotSupportedError`: If `token_in_symbol` or `token_out_symbol` is not configured or L2 address is missing.
*   `InsufficientBalanceError`: If the account has an insufficient balance for the input token or ETH for gas.
*   `InsufficientLiquidityError`: If liquidity is insufficient for the swap, no path is found, or the quoted output is zero.
*   `ApprovalError`: If ERC20 token approval fails.
*   `TransactionRevertedError`: If the swap transaction is reverted on-chain.
*   `GasEstimationError`: If gas estimation for the transaction fails.
*   `MaxRetriesExceededError`: If a transaction fails after multiple retries.
*   `TransactionBuildError`: If there's an error building the transaction.
*   `TransactionSendError`: If there's an error sending the transaction.
*   `ScrollSwapError`: For other general swap-related errors on Scroll with SyncSwap.

**Usage Example:**

```python
from web3 import Web3
from decimal import Decimal
from airdrops.protocols.scroll import swap_tokens
from airdrops.shared.config import SCROLL_L2_RPC_URL # Assuming RPC URL is in config

# Initialize Web3 instance for Scroll L2
web3_scroll = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))

# Account details
my_private_key = "0x..."

# Example: Swap 0.005 ETH for USDC on Scroll
try:
    eth_amount_to_swap = web3_scroll.to_wei(Decimal("0.005"), "ether")
    tx_hash_eth_usdc = swap_tokens(
        web3_scroll=web3_scroll,
        private_key=my_private_key,
        token_in_symbol="ETH",
        token_out_symbol="USDC",
        amount_in=eth_amount_to_swap,
        slippage_percent=0.5
    )
    print(f"ETH to USDC swap initiated. Tx Hash: {tx_hash_eth_usdc}")
except Exception as e:
    print(f"Error during ETH to USDC swap: {e}")

# Example: Swap 10 USDC for WETH on Scroll
try:
    usdc_amount_atomic_swap = int(Decimal("10") * (10**6)) # USDC has 6 decimals
    tx_hash_usdc_weth = swap_tokens(
        web3_scroll=web3_scroll,
        private_key=my_private_key,
        token_in_symbol="USDC",
        token_out_symbol="WETH",
        amount_in=usdc_amount_atomic_swap,
        slippage_percent=1.0 # Allow 1% slippage
    )
    print(f"USDC to WETH swap initiated. Tx Hash: {tx_hash_usdc_weth}")
except Exception as e:
    print(f"Error during USDC to WETH swap: {e}")

# Example: Swap 5 USDC for native ETH on Scroll
try:
    usdc_amount_for_eth = int(Decimal("5") * (10**6))
    tx_hash_usdc_eth = swap_tokens(
        web3_scroll=web3_scroll,
        private_key=my_private_key,
        token_in_symbol="USDC",
        token_out_symbol="ETH", # Requesting native ETH as output
        amount_in=usdc_amount_for_eth
    )
    print(f"USDC to ETH swap initiated. Tx Hash: {tx_hash_usdc_eth}")
except Exception as e:
    print(f"Error during USDC to ETH swap: {e}")
```

## Configuration

The Scroll module relies on contract addresses and token addresses defined in `airdrops.src.airdrops.shared.config`. Ensure the following are correctly set up:

*   `SCROLL_L1_RPC_URL`
*   `SCROLL_L2_RPC_URL`
*   `SCROLL_L1_GATEWAY_ROUTER_ADDRESS`
*   `SCROLL_L2_GATEWAY_ROUTER_ADDRESS`
*   `SCROLL_L1_GAS_ORACLE_ADDRESS`
*   `SCROLL_TOKEN_ADDRESSES` (containing L1 and L2 addresses for WETH, USDC, USDT)
*   `SYNC_SWAP_ROUTER_ADDRESS_SCROLL`
*   `SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL`

## ABIs

Contract ABIs are stored in `airdrops/src/airdrops/protocols/scroll/abi/`:
*   `L1GatewayRouter.json` (for bridging)
*   `L2GatewayRouter.json` (for bridging)
*   `ERC20.json` (standard ERC20 token interface)
*   `SyncSwapRouter.json` (for SyncSwap DEX interactions)
*   `SyncSwapClassicPoolFactory.json` (for finding SyncSwap pool addresses)
*   `SyncSwapClassicPool.json` (for querying SyncSwap pools, e.g., getting quotes)

## Error Handling

The module defines custom exceptions to provide more specific error information.

**General Bridge and Transaction Errors:**
*   `ScrollBridgeError` (base class for bridge-specific errors)
*   `InsufficientBalanceError`
*   `TransactionRevertedError`
*   `RPCError` (Note: Often wrapped by `MaxRetriesExceededError`)
*   `ApprovalError`
*   `GasEstimationError`
*   `MaxRetriesExceededError`
*   `TransactionBuildError`
*   `TransactionSendError`

**Swap-Specific Errors (SyncSwap):**
*   `ScrollSwapError` (base class for SyncSwap specific errors)
*   `InsufficientLiquidityError` (if a swap path cannot be found or liquidity is too low)
*   `TokenNotSupportedError` (if a token symbol is not found in the configuration for swaps)

Note: `SlippageTooHighError` was considered but is generally handled by the `amountOutMin` parameter in swaps; explicit post-transaction slippage checks are not implemented.
### `lend_borrow_layerbank_scroll`

**Purpose:**

Handles lending, borrowing, repaying, and withdrawing assets on LayerBank V2 protocol on Scroll L2. Supports ETH and USDC operations with automatic market entry and collateral management.

**Parameters:**

- `web3_scroll` (`Web3`): Web3 instance for Scroll L2.
- `private_key` (`str`): Private key of the account performing the operation.
- `action` (`str`): Action to perform ("lend", "borrow", "repay", "withdraw").
- `token_symbol` (`str`): Token symbol ("ETH" or "USDC").
- `amount` (`int`): Amount in Wei for ETH, smallest unit for USDC.

**Returns:**

- `str`: Transaction hash of the operation.

**Raises:**

- `ScrollLendingError`: For general lending-related errors.
- `InsufficientCollateralError`: When insufficient collateral for borrowing.
- `TokenNotSupportedError`: If token symbol is not supported.
- `MarketNotEnteredError`: If market entry is required but fails.
- `RepayAmountExceedsDebtError`: If repay amount exceeds current debt.
- `LayerBankComptrollerRejectionError`: If comptroller rejects the operation.
- `ApprovalError`: If token approval fails.
- `TransactionRevertedError`: If transaction is reverted.

**Usage Example:**

```python
from web3 import Web3
from airdrops.protocols.scroll import lend_borrow_layerbank_scroll
from airdrops.shared.config import SCROLL_L2_RPC_URL

web3_scroll = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))
private_key = "0x..."

# Lend 1 ETH to LayerBank
tx_hash = lend_borrow_layerbank_scroll(
    web3_scroll=web3_scroll,
    private_key=private_key,
    action="lend",
    token_symbol="ETH",
    amount=1000000000000000000  # 1 ETH in Wei
)

# Borrow 500 USDC using ETH as collateral
tx_hash = lend_borrow_layerbank_scroll(
    web3_scroll=web3_scroll,
    private_key=private_key,
    action="borrow",
    token_symbol="USDC",
    amount=500000000  # 500 USDC (6 decimals)
)
```
### `perform_random_activity_scroll`

**Purpose:**

Orchestrates a sequence of random activities on the Scroll network, including bridging assets, token swapping, liquidity provision, and lending/borrowing operations. This function is designed for automated airdrop farming by performing realistic user interactions across multiple DeFi protocols on Scroll.

**Parameters:**

- `web3_l1` (`Web3`): Web3 instance for Ethereum L1 network.
- `web3_scroll` (`Web3`): Web3 instance for Scroll L2 network.
- `private_key` (`str`): Private key of the account performing the activities.
- `action_count` (`int`): Number of random actions to perform (must be positive).
- `config` (`Dict[str, Any]`): Configuration dictionary containing the `random_activity_scroll` key with detailed settings for action selection and parameters.

**Configuration Structure:**

The `config` parameter must contain a `random_activity_scroll` key with the following structure:

```python
config = {
    "random_activity_scroll": {
        # Action selection weights (optional, defaults to uniform)
        "action_weights": {
            "bridge_assets": 0.25,
            "swap_tokens": 0.35,
            "provide_liquidity_scroll": 0.25,
            "lend_borrow_layerbank_scroll": 0.15
        },
        
        # Global settings
        "stop_on_failure": True,  # Stop sequence on first failure (default: True)
        "inter_action_delay_seconds_range": [5.0, 15.0],  # Delay between actions
        
        # Bridge configuration
        "bridge_assets": {
            "directions": [("deposit", 0.6), ("withdraw", 0.4)],
            "tokens_l1_l2": ["ETH", "USDC"],
            "amount_eth_range": [0.001, 0.01],
            "amount_usdc_range": [5, 50]
        },
        
        # Swap configuration
        "swap_tokens": {
            "token_pairs": [("ETH", "USDC", 0.5), ("USDC", "WETH", 0.3), ("WETH", "USDT", 0.2)],
            "amount_eth_percent_range": [5, 20],
            "amount_usdc_percent_range": [10, 30],
            "slippage_percent": 0.5
        },
        
        # Liquidity provision configuration
        "provide_liquidity_scroll": {
            "actions": [("add", 0.7), ("remove", 0.3)],
            "token_pairs": [("ETH", "USDC", 1.0)],
            "add_amount_eth_percent_range": [5, 15],
            "add_amount_usdc_percent_range": [10, 25],
            "remove_lp_percent_range": [20, 50],
            "slippage_percent": 0.5
        },
        
        # Lending configuration
        "lend_borrow_layerbank_scroll": {
            "actions": [("lend", 0.4), ("borrow", 0.2), ("repay", 0.2), ("withdraw", 0.2)],
            "tokens": ["ETH", "USDC"],
            "lend_amount_eth_percent_range": [10, 25],
            "lend_amount_usdc_percent_range": [15, 30]
        }
    }
}
```

**Returns:**

- `Tuple[bool, Union[List[str], str]]`: A tuple where:
  - First element: Boolean indicating overall success
    - `True` if all actions completed according to the `stop_on_failure` policy
    - `False` if a critical setup error occurred or sequence was stopped due to failure
  - Second element: Either a list of transaction hashes from successful actions, or an error message string if the process failed before any actions could be attempted

**Orchestration Role:**

This function serves as the main orchestrator for random Scroll activities by:

1. **Action Selection**: Uses weighted random selection to choose from available actions based on configured weights
2. **Parameter Generation**: Dynamically generates realistic parameters for each action based on current wallet balances and configured ranges
3. **Execution Management**: Executes actions sequentially with optional inter-action delays
4. **Error Handling**: Provides configurable failure handling (stop on first failure vs. continue on errors)
5. **Result Aggregation**: Collects and returns transaction hashes from successful operations

**Raises:**

- `ValueError`: If `action_count` is not positive.
- `ScrollRandomActivityError`: For orchestration-specific errors such as:
  - Missing or invalid configuration
  - Action selection failures
  - Parameter generation failures
  - Invalid action weights

**Usage Example:**

```python
from web3 import Web3
from airdrops.protocols.scroll import perform_random_activity_scroll
from airdrops.shared.config import ETHEREUM_RPC_URL, SCROLL_L2_RPC_URL

# Initialize Web3 instances
web3_l1 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))
web3_scroll = Web3(Web3.HTTPProvider(SCROLL_L2_RPC_URL))

# Configuration for random activities
config = {
    "random_activity_scroll": {
        "action_weights": {
            "bridge_assets": 0.3,
            "swap_tokens": 0.4,
            "provide_liquidity_scroll": 0.2,
            "lend_borrow_layerbank_scroll": 0.1
        },
        "stop_on_failure": False,  # Continue on individual failures
        "inter_action_delay_seconds_range": [10.0, 30.0],
        "bridge_assets": {
            "directions": [("deposit", 1.0)],
            "tokens_l1_l2": ["ETH"],
            "amount_eth_range": [0.005, 0.02]
        },
        "swap_tokens": {
            "token_pairs": [("ETH", "USDC", 1.0)],
            "amount_eth_percent_range": [10, 25],
            "slippage_percent": 0.5
        }
    }
}

# Execute random activity sequence
try:
    success, result = perform_random_activity_scroll(
        web3_l1=web3_l1,
        web3_scroll=web3_scroll,
        private_key="0x...",
        action_count=3,
        config=config
    )
    
    if success:
        print(f"Successfully completed {len(result)} actions:")
        for i, tx_hash in enumerate(result, 1):
            print(f"  {i}. {tx_hash}")
    else:
        print(f"Activity sequence failed: {result}")
        
except Exception as e:
    print(f"Error during random activity execution: {e}")
```

**Security Considerations:**

- Private keys are handled securely and never logged
- All transaction parameters are validated before execution
- Configurable limits prevent excessive fund usage
- Error handling prevents cascading failures
- Inter-action delays help avoid detection as automated behavior