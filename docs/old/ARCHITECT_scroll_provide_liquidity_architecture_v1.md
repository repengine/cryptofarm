## Scroll Protocol: `provide_liquidity` Function Architecture v1

### 1. Introduction

This document outlines the architectural design for the `provide_liquidity` function within the `airdrops.protocols.scroll` module. This function will manage adding and removing liquidity for token pairs on the SyncSwap Decentralized Exchange (DEX) operating on the Scroll network.

### 2. Function Signature

```python
def provide_liquidity_scroll(
    web3_scroll: Web3,
    private_key: str,
    action: str,  # "add" or "remove"
    token_a_symbol: str,
    token_b_symbol: str,
    amount_a_desired: Optional[int] = None,  # For "add"
    amount_b_desired: Optional[int] = None,  # For "add"
    lp_token_amount: Optional[int] = None,   # For "remove"
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800
) -> str:
    """
    Adds or removes liquidity for a token pair on SyncSwap on Scroll.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        private_key: Private key of the account.
        action: "add" to add liquidity, "remove" to remove liquidity.
        token_a_symbol: Symbol of the first token (e.g., "ETH", "USDC").
        token_b_symbol: Symbol of the second token (e.g., "USDC", "WETH").
        amount_a_desired: Desired amount of token_a to add (smallest unit). Required for "add".
        amount_b_desired: Desired amount of token_b to add (smallest unit). Required for "add".
        lp_token_amount: Amount of LP tokens to remove (smallest unit). Required for "remove".
        slippage_percent: Allowed slippage percentage for calculating min amounts.
        deadline_seconds: Transaction deadline in seconds from now.

    Returns:
        Transaction hash of the add/remove liquidity operation.

    Raises:
        ScrollLiquidityError: For general liquidity provision errors.
        PoolNotFoundError: If the liquidity pool for the pair is not found.
        InsufficientBalanceError: If balances are insufficient.
        ApprovalError: If token approval fails.
        TransactionRevertedError: If the transaction is reverted.
        ValueError: For invalid inputs.
    """
    # Implementation to follow based on this architecture
    pass
```

### 3. Core Logic - Add Liquidity

**Inputs:** `web3_scroll`, `private_key`, `action="add"`, `token_a_symbol`, `token_b_symbol`, `amount_a_desired`, `amount_b_desired`, `slippage_percent`, `deadline_seconds`.

1.  **Resolve Token Addresses & Decimals:**
    *   Get L2 addresses and decimals for `token_a_symbol` and `token_b_symbol` from configuration (e.g., `SCROLL_TOKEN_ADDRESSES` in [`airdrops/src/airdrops/shared/config.py`](airdrops/src/airdrops/shared/config.py)).
    *   If "ETH" is a symbol, its corresponding address will be WETH's address (`0x5300000000000000000000000000000000000004`) for router interaction.

2.  **Get Pool Address:**
    *   Fetch the SyncSwap pool address (which is also the LP token address) using `SyncSwapClassicPoolFactory.getPool(token_a_address, token_b_address)`.
    *   If the pool address is the zero address, raise `PoolNotFoundError`.

3.  **Calculate Minimum Amounts:**
    *   `amount_a_min = amount_a_desired * (1 - slippage_percent / 100)`
    *   `amount_b_min = amount_b_desired * (1 - slippage_percent / 100)`
    *   These are simplified. Actual calculation might involve querying pool reserves for a more accurate quote if only one desired amount is provided, but the task implies both `amount_a_desired` and `amount_b_desired` are given for "add". For the router's `addLiquidity` function, the `minLiquidity` parameter is key, which is derived from `amount_a_min` and `amount_b_min` relative to pool reserves. A helper `_calculate_liquidity_amounts_min_scroll` will be needed to determine the `minLiquidity` parameter for the router, or directly the `amountAMin`/`amountBMin` if the router function takes those (the SyncSwap ABI for `addLiquidity` takes `minLiquidity` derived from token inputs).
    *   The `inputs` parameter for `addLiquidity` is `TokenInput[] inputs` where `TokenInput` is `{address token, uint256 amount}`. The `minLiquidity` parameter will be used for slippage control on the LP tokens minted.

4.  **Transaction Deadline:**
    *   Calculate `deadline = current_block_timestamp + deadline_seconds`.

5.  **Prepare `TokenInput` Array for Router:**
    *   `token_inputs = []`
    *   If `token_a_symbol` is "ETH":
        *   `token_inputs.append({'token': weth_address, 'amount': amount_a_desired})`
        *   `msg_value = amount_a_desired` (ETH amount)
    *   Else:
        *   `token_inputs.append({'token': token_a_address, 'amount': amount_a_desired})`
        *   Approve SyncSwap Router for `token_a_address` for `amount_a_desired`.
    *   If `token_b_symbol` is "ETH" (and `token_a_symbol` was not ETH):
        *   `token_inputs.append({'token': weth_address, 'amount': amount_b_desired})`
        *   `msg_value = amount_b_desired` (ETH amount)
    *   Else:
        *   `token_inputs.append({'token': token_b_address, 'amount': amount_b_desired})`
        *   Approve SyncSwap Router for `token_b_address` for `amount_b_desired`.
    *   If both are tokens (not ETH), `msg_value = 0`.

6.  **Interact with SyncSwap Router (`addLiquidity`):**
    *   Function: `addLiquidity(address pool, TokenInput[] inputs, bytes data, uint256 minLiquidity, address callback, bytes callbackData)`
    *   Parameters:
        *   `pool`: The pool address obtained in step 2.
        *   `inputs`: The `token_inputs` array prepared in step 5.
        *   `data`: `0x` (empty bytes, typically for classic pools unless specific pool type needs data).
        *   `minLiquidity`: Calculated based on `amount_a_min`, `amount_b_min`, and current pool reserves. This requires a helper function to query reserves and calculate expected LP tokens, then apply slippage.
        *   `callback`: Zero address (`0x00...00`).
        *   `callbackData`: `0x`.
    *   If ETH is involved, the transaction `value` field must be set to `msg_value`.
    *   Build and send the transaction.

7.  **Return Transaction Hash.**

### 4. Core Logic - Remove Liquidity

**Inputs:** `web3_scroll`, `private_key`, `action="remove"`, `token_a_symbol`, `token_b_symbol`, `lp_token_amount`, `slippage_percent`, `deadline_seconds`.

1.  **Resolve Token Addresses:**
    *   Get L2 addresses for `token_a_symbol` and `token_b_symbol` (WETH if "ETH").

2.  **Get Pool Address (LP Token Address):**
    *   Fetch the SyncSwap pool address using `SyncSwapClassicPoolFactory.getPool(token_a_address, token_b_address)`. This address is the LP token contract address.
    *   If the pool address is the zero address, raise `PoolNotFoundError`.

3.  **Calculate Minimum Amounts Out (`amountAMin`, `amountBMin`):**
    *   This requires querying the pool for current reserves of `token_a` and `token_b`, and the total supply of LP tokens.
    *   `amount_a_out_expected = (lp_token_amount / total_lp_supply) * reserve_a`
    *   `amount_b_out_expected = (lp_token_amount / total_lp_supply) * reserve_b`
    *   `amount_a_min = amount_a_out_expected * (1 - slippage_percent / 100)`
    *   `amount_b_min = amount_b_out_expected * (1 - slippage_percent / 100)`
    *   The `minAmounts` parameter for `burnLiquidity` will be `[amount_a_min, amount_b_min]` (order might matter, typically sorted token addresses or as per pool's token0/token1).

4.  **Transaction Deadline:**
    *   Calculate `deadline = current_block_timestamp + deadline_seconds`.

5.  **Approve LP Tokens:**
    *   Approve the SyncSwap Router to spend `lp_token_amount` of the LP tokens (pool address from step 2). Use standard ERC20 ABI.

6.  **Interact with SyncSwap Router (`burnLiquidity`):**
    *   Function: `burnLiquidity(address pool, uint256 liquidity, bytes data, uint256[] minAmounts, address callback, bytes callbackData)`
    *   Parameters:
        *   `pool`: The pool address (LP token address).
        *   `liquidity`: `lp_token_amount`.
        *   `data`: `0x` (empty bytes).
        *   `minAmounts`: Array `[amount_a_min, amount_b_min]` calculated in step 3. The order should match the pool's internal token order or how it expects them.
        *   `callback`: Zero address. If ETH is desired back (and one token is WETH), the router might handle unwrapping. If specific callback logic is needed for ETH, this would change. For now, assume router handles it or user receives WETH.
        *   `callbackData`: `0x`.
    *   The task mentions `removeLiquidityETHSupportingFeeOnTransferTokens`. The generic `burnLiquidity` is used here. If ETH is one of the tokens in the pair (represented as WETH in the pool), the router should ideally handle unwrapping WETH to ETH if the `callback` or `data` fields are used appropriately, or if the `minAmounts` are specified for ETH and the other token. If the router returns WETH, an additional step to unwrap WETH might be needed outside this function if the user strictly wants ETH. For fee-on-transfer tokens, the `data` field or the pool itself might handle it.
    *   Build and send the transaction.

7.  **Return Transaction Hash.**

### 5. Contract Interaction (SyncSwap)

*   **SyncSwap Router:** `0x80e38291e06339d10AAB483C65695D004DBd5C69`
    *   ABI: [`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapRouter.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapRouter.json:1)
    *   **Key Functions from ABI:**
        *   `addLiquidity(address pool, TokenInput[] inputs, bytes data, uint256 minLiquidity, address callback, bytes callbackData)`
            *   `pool`: address of the liquidity pool.
            *   `inputs`: Array of `(address token, uint256 amount)` structs for tokens being added.
            *   `data`: Bytes, typically `0x` for classic pools.
            *   `minLiquidity`: Minimum amount of LP tokens to receive (slippage control).
            *   `callback`: Address for callback, usually zero address.
            *   `callbackData`: Data for callback, usually `0x`.
            *   `payable`: Yes (can receive ETH if one input token is WETH).
        *   `burnLiquidity(address pool, uint256 liquidity, bytes data, uint256[] minAmounts, address callback, bytes callbackData)`
            *   `pool`: address of the liquidity pool (LP token address).
            *   `liquidity`: Amount of LP tokens to burn.
            *   `data`: Bytes, typically `0x`.
            *   `minAmounts`: Array of minimum amounts of underlying tokens to receive.
            *   `callback`: Address for callback, usually zero address.
            *   `callbackData`: Data for callback, usually `0x`.

*   **SyncSwap Classic Pool Factory:** `0x3722D347d419D021D51863FA33992A909C2bB296`
    *   ABI: [`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPoolFactory.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPoolFactory.json:1)
    *   **Key Function for LP Token Address Retrieval:**
        *   `getPool(address tokenA, address tokenB) returns (address poolAddress)`
            *   `tokenA`: Address of the first token in the pair.
            *   `tokenB`: Address of the second token in the pair.
            *   Returns the address of the LP token / pool contract.

*   **LP Token (Pool Contract):** Address is dynamic, obtained via `SyncSwapClassicPoolFactory.getPool()`.
    *   ABI: Standard ERC20, e.g., [`airdrops/src/airdrops/protocols/scroll/abi/ERC20.json`](airdrops/src/airdrops/protocols/scroll/abi/ERC20.json:1) for `approve()`, `balanceOf()`, `totalSupply()`.
    *   To get reserves for `amountMin` calculation during removal, the pool contract itself will have functions like `getReserves()` or similar (e.g., `SyncSwapClassicPool.json` ABI might be needed if not standard ERC20 for this). The `SyncSwapClassicPool.json` ABI ([`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPool.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPool.json)) should be consulted for `getReserves` or equivalent.

### 6. Configuration Management

*   **SyncSwap Router:**
    *   Address: `SYNC_SWAP_ROUTER_ADDRESS_SCROLL` (from [`airdrops/src/airdrops/shared/config.py`](airdrops/src/airdrops/shared/config.py)). Value: `0x80e38291e06339d10AAB483C65695D004DBd5C69`.
    *   ABI Path: [`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapRouter.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapRouter.json:1).
*   **SyncSwap Classic Pool Factory:**
    *   Address: `SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL` (from [`airdrops/src/airdrops/shared/config.py`](airdrops/src/airdrops/shared/config.py)). Value: `0x3722D347d419D021D51863FA33992A909C2bB296`.
    *   ABI Path: [`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPoolFactory.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPoolFactory.json:1).
*   **ERC20 ABI (for token approvals and LP token interactions):**
    *   ABI Path: [`airdrops/src/airdrops/protocols/scroll/abi/ERC20.json`](airdrops/src/airdrops/protocols/scroll/abi/ERC20.json:1).
*   **SyncSwap Classic Pool ABI (for `getReserves` if needed):**
    *   ABI Path: [`airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPool.json`](airdrops/src/airdrops/protocols/scroll/abi/SyncSwapClassicPool.json:1). This will be needed for querying reserves to calculate `minAmounts` for removal and `minLiquidity` for adding.
*   **Token Addresses (ETH, WETH, USDC, etc.):**
    *   Managed in `SCROLL_TOKEN_ADDRESSES` within [`airdrops/src/airdrops/shared/config.py`](airdrops/src/airdrops/shared/config.py).
    *   WETH: `0x5300000000000000000000000000000000000004`
    *   USDC: `0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4`

### 7. Error Handling

Custom exceptions from [`airdrops/src/airdrops/protocols/scroll/exceptions.py`](airdrops/src/airdrops/protocols/scroll/exceptions.py:1) should be used:

*   `ScrollLiquidityError`: Generic error for this function.
*   `PoolNotFoundError`: If `SyncSwapClassicPoolFactory.getPool()` returns the zero address.
*   `InsufficientBalanceError` (from shared exceptions): If token or ETH balance is too low.
*   `ApprovalError` (from `scroll.exceptions` or shared): If `approve()` transaction fails or is reverted.
*   `TransactionRevertedError` (from shared exceptions): If `addLiquidity` or `burnLiquidity` calls revert. Specific router errors like `NotEnoughLiquidityMinted` or `TooLittleReceived` (from SyncSwapRouter ABI errors) could be caught and wrapped into this.
*   `ValueError`: For invalid `action` parameter, negative amounts, or invalid `slippage_percent`.
*   `GasEstimationError` (from shared exceptions).

### 8. Helper Functions (Conceptual)

*   `_get_syncswap_pool_address_scroll(web3_scroll, token_a_address, token_b_address) -> str`:
    *   Uses `SyncSwapClassicPoolFactory.getPool()`.
    *   Handles token address sorting if required by the factory.
*   `_calculate_add_liquidity_min_lp_scroll(web3_scroll, pool_address, token_a_address, amount_a_desired, token_b_address, amount_b_desired, slippage_percent) -> int`:
    *   Queries pool reserves (using `SyncSwapClassicPool.json` ABI's `getReserves` or equivalent).
    *   Calculates expected LP tokens to be minted.
    *   Applies slippage to determine `minLiquidity`.
*   `_calculate_remove_liquidity_min_amounts_scroll(web3_scroll, pool_address, lp_token_amount, token_a_address, token_b_address, slippage_percent) -> Tuple[int, int]`:
    *   Queries pool reserves and total LP supply.
    *   Calculates expected `amount_a_out` and `amount_b_out`.
    *   Applies slippage to get `amount_a_min` and `amount_b_min`.
*   `_approve_token_scroll(web3_scroll, private_key, token_address, spender_address, amount)`: Standard token approval helper.