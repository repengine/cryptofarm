# zkSync Era Protocol Module

This document outlines the design, configuration, and usage of the zkSync Era protocol module within the Airdrops Automation project.

## 1. Overview

The zkSync Era module enables interaction with the zkSync Era Layer 2 network, including bridging assets (ETH), swapping tokens on decentralized exchanges (DEXes), and engaging with lending protocols.

**Key Functionalities:**
- `bridge_eth()`: Bridge ETH to/from zkSync Era.
- `swap_tokens()`: Perform token swaps on zkSync Era DEXes (e.g., SyncSwap, Mute.io).
- `lend_borrow()`: Interact with lending protocols on zkSync Era (e.g., EraLend).
- `perform_random_activity()`: Execute a randomized sequence of the above actions.

## 2. Configuration

The `config` dictionary for the zkSync Era module, particularly relevant for `bridge_eth`, should contain:

```python
ZKSYNC_CONFIG = {
    "networks": {
        "ethereum": { # L1
            "chain_id": 1, # Example: Ethereum Mainnet
            "rpc_url": "YOUR_ETHEREUM_RPC_URL",
            "bridge_address": "0x32400084C286CF3E17e7B677ea9583e60a000324", # From project plan
            "abi_path_l1_bridge": "path/to/l1_bridge_abi.json" # Or ABI string
        },
        "zksync": { # L2
            "chain_id": 324, # zkSync Era Mainnet
            "rpc_url": "https://mainnet.era.zksync.io", # Official RPC
            "bridge_address": "0x0000000000000000000000000000000000008006", # L2 WETH contract, also used in bridging
            "abi_path_l2_bridge": "path/to/l2_bridge_abi.json", # Or ABI string for L2 bridge interactions
            "dex_router_address": "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295", # Example: SyncSwap Classic Router, VERIFY THIS!
            "dex_router_abi_path": "path/to/syncswap_router_abi.json", # Or ABI string for DEX Router
            "lending_protocols": {
                "eralend": { # Or other chosen protocol name
                    "lending_pool_manager_address": "0xEraLendLendingPoolManagerAddress_VERIFY",
                    "lending_pool_manager_abi_path": "path/to/eralend_lending_pool_manager_abi.json", # Or ABI string
                    "weth_gateway_address": "0xEraLendWETHGatewayAddress_VERIFY", # If applicable
                    "weth_gateway_abi_path": "path/to/eralend_weth_gateway_abi.json", # If applicable
                    "ztoken_abi_path": "path/to/eralend_ztoken_abi.json", # Generic ABI for zToken interactions
                    "supported_assets": {
                        "ETH": {
                            "underlying_address": "0x0000000000000000000000000000000000000000", # Native ETH
                            "ztoken_address": "0xEraLend_zETH_Address_VERIFY",
                            "decimals": 18
                        },
                        "USDC": {
                            "underlying_address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4", # Example, verify
                            "ztoken_address": "0xEraLend_zUSDC_Address_VERIFY",
                            "decimals": 6
                        }
                        # Add other supported assets
                    },
                    "referral_code": 0, # Default, verify
                    "default_interest_rate_mode_stable": 1, # Verify
                    "default_interest_rate_mode_variable": 2 # Verify
                }
            }
        }
    },
    "tokens": {
        "ETH": {"address": "0x0000000000000000000000000000000000000000", "decimals": 18, "is_native": true},
        "WETH": {"address": "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91", "decimals": 18},
        # Add other commonly traded/whitelisted tokens on zkSync Era with their addresses and decimals
        # e.g., "USDC": {"address": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4", "decimals": 6},
    },
    "settings": {
        "default_slippage_bps": 50, # Default for swaps, e.g., 0.5%
        "gas_limit_multiplier_l1": 1.2,
        "gas_limit_multiplier_l2": 1.5, # L2 gas can be more variable
        "l2_gas_per_pubdata_byte_limit": 800, # Default, may need adjustment
        "lending_health_factor_limits": { # Optional, for advanced automation
            "min_safe_hf": 1.5, # Example: minimum health factor before taking action
            "target_hf_after_repay": 2.0 # Example: target HF after a deleveraging action
        }
    },
    "random_activity": {
        "enabled": True,
        "num_actions_range": [2, 4],  # Min and max number of actions
        "action_weights": {
            "bridge_eth": 20,
            "swap_tokens": 50,
            "lend_borrow": 30
        },
        "max_action_selection_retries": 3,
        "stop_on_first_failure": False, # Default: continue all N actions

        "bridge_eth": {
            "amount_range_eth": [0.005, 0.01], # In ETH units (float/Decimal)
            "probability_to_l2": 0.6
        },

        "swap_tokens": { # For SyncSwap
            "token_pairs": [ # List of (token_in_symbol, token_out_symbol)
                ("ETH", "USDC"), ("USDC", "ETH")
                # Symbols must be defined in main config.tokens
            ],
            "amount_in_percentage_range": [0.1, 0.25], # % of token_in balance
            "slippage_bps_range": [30, 70]
        },

        "lend_borrow": { # For EraLend
            "sub_action_weights": {
                "supply": 40, "withdraw": 15, "borrow": 25,
                "repay": 15, "set_collateral": 5
            },
            "supported_tokens": ["ETH", "USDC"], # Symbols from config.tokens
            # Amount ranges are percentages of relevant balances/positions
            "supply_amount_percentage_range": [0.15, 0.5], # of L2 balance
            "withdraw_amount_percentage_of_supplied_range": [0.2, 0.8],
            "borrow_amount_percentage_of_capacity_range": [0.1, 0.3],
            "repay_amount_percentage_of_debt_range": [0.2, 0.7],
            "repay_all_debt_probability": 0.1,
            "set_collateral_enable_probability": 0.75,
            "min_health_factor_before_borrow": 1.2 # Minimum health factor to maintain before attempting a borrow
        },

        "initial_state_fetch": {
            "tokens_to_track_balance": ["ETH", "USDC", "WETH"] # Symbols from config.tokens
        }
    }
}
```

-   **`networks.ethereum.rpc_url`**: URL for an Ethereum L1 node.
-   **`networks.ethereum.bridge_address`**: Address of the zkSync L1 Bridge contract.
-   **`networks.ethereum.abi_path_l1_bridge`**: Path to the L1 Bridge ABI JSON file (or the ABI string itself).
-   **`networks.zksync.rpc_url`**: URL for a zkSync Era L2 node.
-   **`networks.zksync.bridge_address`**: Address of the zkSync L2 Bridge contract (often interacts with WETH contract for ETH).
-   **`networks.zksync.abi_path_l2_bridge`**: Path to the L2 Bridge ABI JSON file (or the ABI string itself).
-   **`settings.l2_gas_per_pubdata_byte_limit`**: A zkSync-specific gas parameter.

## 3. Core Functions

### 3.1. `bridge_eth(user_address, private_key, amount_eth, to_l2, config)`

This function handles bridging ETH between L1 (Ethereum) and L2 (zkSync Era).

**Parameters:**
-   `user_address (str)`: The address performing the bridge.
-   `private_key (str)`: Private key for `user_address` to sign transactions.
-   `amount_eth (float)`: The amount of ETH to bridge (e.g., 0.1).
-   `to_l2 (bool)`: Direction of the bridge. `True` for L1->L2 (deposit), `False` for L2->L1 (initiate withdrawal).
-   `config (dict)`: Configuration dictionary as defined in Section 2.

**Returns:**
-   `Tuple[bool, Optional[str]]`: A tuple containing a boolean indicating success, and an optional transaction hash string.

**Interaction Strategy & Logic Flow:**

**A. L1 -> L2 Deposit (`to_l2 = True`)**

1.  **Input Validation:** Check `amount_eth`, addresses, and config presence.
2.  **L1 Web3 Setup:** Initialize `web3.py` instance for L1 using `config.networks.ethereum.rpc_url`.
3.  **Load L1 Bridge Contract:** Instantiate L1 bridge contract object using `config.networks.ethereum.bridge_address` and its ABI.
4.  **Determine L2 Gas:** For some zkSync deposit functions, an L2 gas component might need to be estimated or provided. This might involve calling a function like `l2TransactionBaseCost` on the L1 bridge or using a default. The `msg.value` sent to the L1 bridge's deposit function will be `amount_eth` + this L2 gas fee.
    *   *Key L1 Bridge Function (Example):* `requestL2Transaction` or `depositETH`.
    *   *Parameters (Example):* `_contractL2`, `_l2Value` (amount to credit on L2), `_calldata` (if calling a contract on L2), `_l2GasLimit`, `_l2GasPerPubdataByteLimit`, `_factoryDeps` (bytecode for L2 contract deployment if any), `_refundRecipient`. For simple ETH deposit, many of these might be zero or default.
5.  **Build Transaction:**
    *   Construct the transaction dictionary for the L1 bridge deposit function.
    *   `from`: `user_address`.
    *   `to`: L1 bridge contract address.
    *   `value`: `Web3.to_wei(amount_eth, 'ether')` + calculated L2 gas fee.
    *   `gas`: Estimate using `contract.functions.your_deposit_function(...).estimate_gas({...})`. Apply `config.settings.gas_limit_multiplier_l1`.
    *   `gasPrice` (legacy) or `maxFeePerGas`/`maxPriorityFeePerGas` (EIP-1559): Fetch from L1 `web3` instance.
    *   `nonce`: `w3_l1.eth.get_transaction_count(user_address)`.
    *   `data`: Encoded function call.
6.  **Sign & Send:** Sign with `private_key` and send using `w3_l1.eth.send_raw_transaction()`.
7.  **Receipt Check:** Wait for transaction receipt and confirm success. Log L1 tx hash.

**B. L2 -> L1 Withdrawal Initiation (`to_l2 = False`)**

1.  **Input Validation:** Check `amount_eth`, addresses, and config presence.
2.  **L2 Web3 Setup:** Initialize `web3.py` instance for L2 (zkSync Era) using `config.networks.zksync.rpc_url`.
    *   Note: zkSync Era uses an EIP-712 compatible transaction type for many operations. `web3.py` might require specific handling or middleware for this if not automatically supported for zkSync.
3.  **Load L2 Bridge/WETH Contract:** Instantiate L2 bridge/WETH contract object using `config.networks.zksync.bridge_address` and its ABI. (The L2 WETH contract often has a `withdraw` function that initiates the L2->L1 process).
4.  **Build Transaction:**
    *   *Key L2 Bridge Function (Example):* `withdraw` (on WETH contract) or `initiateWithdrawal`.
    *   *Parameters (Example):* `_l1Receiver` (the `user_address` on L1), `_amount` (for ERC20, or `msg.value` for ETH).
    *   Construct the transaction dictionary.
    *   `from`: `user_address`.
    *   `to`: L2 bridge/WETH contract address.
    *   `value`: `Web3.to_wei(amount_eth, 'ether')` (if withdrawing ETH via a payable function).
    *   `gas`: Estimate using L2 `web3` instance. zkSync gas estimation might require specific parameters or methods.
    *   `gasPrice` or EIP-1559 params: Fetch from L2 `web3` instance.
    *   `nonce`: `w3_l2.eth.get_transaction_count(user_address)`.
    *   `data`: Encoded function call.
    *   zkSync specific fields like `gasPerPubdataByteLimit` might need to be included in the transaction if not handled by `web3.py` defaults for zkSync.
5.  **Sign & Send:** Sign with `private_key` and send using `w3_l2.eth.send_raw_transaction()`.
6.  **Receipt Check:** Wait for transaction receipt and confirm success. Log L2 tx hash.
    *   Note: This only *initiates* the withdrawal. Finalizing it on L1 is a separate, later process (typically after a challenge period) and is out of scope for this function.

### 3.2. `swap_tokens(user_address, private_key, token_in_address, token_out_address, amount_in, dex_name, slippage_bps, config)`

This function handles swapping tokens on a specified DEX on zkSync Era (initially targeting SyncSwap).

**Parameters:**
-   `user_address (str)`: The address performing the swap.
-   `private_key (str)`: Private key for `user_address` to sign transactions.
-   `token_in_address (str)`: Address of the token to swap from. Use "0x0000000000000000000000000000000000000000" or a similar constant for native ETH.
-   `token_out_address (str)`: Address of the token to swap to.
-   `amount_in (int)`: The amount of `token_in` to swap, in wei.
-   `dex_name (str)`: Name of the DEX to use (e.g., "syncswap").
-   `slippage_bps (int)`: Slippage tolerance in basis points (e.g., 50 for 0.5%).
-   `config (dict)`: Configuration dictionary as defined in Section 2.

**Returns:**
-   `Tuple[bool, Optional[str]]`: A tuple containing a boolean indicating success, and an optional transaction hash string.

**Interaction Strategy & Logic Flow (Example for SyncSwap):**

1.  **Input Validation:**
    *   Validate addresses, `amount_in` > 0, `dex_name`, `slippage_bps` range.
    *   Ensure necessary `config` keys are present (RPC URL, DEX router address/ABI, WETH address).
2.  **L2 Web3 Setup:** Initialize `web3.py` instance for zkSync Era L2 using `config.networks.zksync.rpc_url`.
3.  **Load Contracts:**
    *   Load DEX Router contract using `config.networks.zksync.dex_router_address` and its ABI.
    *   Load ERC20 contract for `token_in_address` (if not native ETH) for approval.
    *   Load WETH contract using `config.tokens.WETH.address` if ETH is involved.
4.  **Parameter Preparation:**
    *   `path (List[str])`: Determine the swap path.
        *   If `token_in_address` is native ETH: `[config.tokens.WETH.address, ..., token_out_address]`.
        *   If `token_out_address` is native ETH: `[token_in_address, ..., config.tokens.WETH.address]`.
        *   Otherwise: `[token_in_address, token_out_address]` or `[token_in_address, config.tokens.WETH.address, token_out_address]`.
        *   *Note: Actual path construction might involve querying the router or a pathfinder for optimal routes if not a direct pair.*
    *   `deadline (int)`: `w3_l2.eth.get_block('latest')['timestamp'] + N` (e.g., N=300 seconds).
5.  **Handle Native ETH Input:**
    *   If `token_in_address` is native ETH, `msg.value` for the transaction will be `amount_in`.
    *   The router function will likely be `swapExactETHForTokens` or similar.
6.  **Handle ERC20 Token Input:**
    *   **Approve Router:** Check allowance of `token_in_address` for `dex_router_address`. If insufficient, call `approve(dex_router_address, amount_in)` on the `token_in_address` contract. Wait for receipt.
    *   The router function will likely be `swapExactTokensForTokens` or similar.
7.  **Calculate `amountOutMin` (for exact input swaps):**
    *   Call `router.functions.getAmountsOut(amount_in, path).call()` to get `expectedAmountOut`.
    *   `amountOutMin = expectedAmountOut * (10000 - slippage_bps) // 10000`.
8.  **Build Transaction:**
    *   `to`: `dex_router_address`.
    *   `from`: `user_address`.
    *   `value`: `amount_in` if native ETH input, else 0.
    *   `data`: Encoded call to the appropriate router swap function (e.g., `swapExactTokensForTokens(amount_in, amountOutMin, path, user_address, deadline)` or `swapExactETHForTokens(amountOutMin, path, user_address, deadline)`).
    *   `gas`: Estimate using `contract.functions.SWAP_FUNCTION(...).estimate_gas({...})`. Apply `config.settings.gas_limit_multiplier_l2`.
    *   `gasPrice`: Fetch from L2 `web3` instance.
    *   `nonce`: `w3_l2.eth.get_transaction_count(user_address)`.
    *   Include zkSync specific fields like `gasPerPubdataByteLimit` from `config.settings` if not automatically handled by `web3.py` for zkSync.
9.  **Sign & Send Transaction:** Sign with `private_key` and send using `w3_l2.eth.send_raw_transaction()`.
10. **Wait for Receipt & Check Status:** `w3_l2.eth.wait_for_transaction_receipt(tx_hash)`. Check `receipt.status == 1`.
11. **Handle Native ETH Output:** If `token_out_address` was specified as native ETH and the path ended in WETH, the user receives WETH. An additional, separate transaction would be needed to call `withdraw(amount)` on the WETH contract to get native ETH. This function primarily ensures the `token_out_address` (which could be WETH) is received.

*Actual function names on the router (e.g., `swapExactTokensForTokensSupportingFeeOnTransferTokens`) must be verified from the DEX's ABI during implementation.*

### 3.3. `lend_borrow()`
This function handles interactions with a lending protocol on zkSync Era (e.g., EraLend), supporting actions like "supply", "withdraw", "borrow", and "repay".

**Chosen Protocol (Assumed):** EraLend. *Critical: All contract addresses, ABIs, function names, and specific behaviors mentioned below MUST be verified against official EraLend documentation before implementation.*

**Parameters:**
-   `user_address (str)`: The address performing the lending/borrowing action.
-   `private_key (str)`: Private key for `user_address`.
-   `action (str)`: The action to perform: "supply", "withdraw", "borrow", "repay", "set_collateral".
-   `token_address (str)`: Address of the underlying token for the action (e.g., ETH's zero address, USDC address).
-   `amount (int)`: The amount of `token_address` for the action, in wei. For "set_collateral", this can be ignored or used to specify which asset if `token_address` is ambiguous.
-   `lending_protocol_name (str)`: Name of the lending protocol to use (e.g., "eralend").
-   `config (dict)`: Configuration dictionary (see Section 2, with additions for lending protocols).
-   `collateral_status (Optional[bool])`: For "set_collateral" action, `True` to enable as collateral, `False` to disable.

**Returns:**
-   `Tuple[bool, Optional[str]]`: A tuple containing a boolean indicating success, and an optional transaction hash string.

**Interaction Strategy & Logic Flow (Conceptual for EraLend):**

**Common Pre-steps for all actions:**
1.  Input validation (addresses, amount, action, protocol name).
2.  Initialize `w3_l2` (zkSync Era web3 instance) from `config.networks.zksync.rpc_url`.
3.  Load Lending Pool Manager contract (e.g., `EraLendLendingPoolManagerAddress_VERIFY`) using its address and ABI from `config.networks.zksync.lending_protocols[lending_protocol_name]`.
4.  If ETH is involved and a WETH Gateway is used (e.g., `EraLendWETHGatewayAddress_VERIFY`), load WETH Gateway contract.
5.  Identify underlying token details (address, zToken address, decimals) from `config...lending_protocols[lending_protocol_name].supported_assets`.

**Action: `supply`**
1.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `depositETH` (or equivalent on Lending Pool Manager if it handles native ETH directly). `msg.value` will be `amount`.
    *   *Conceptual Parameters:* `lending_pool_address` (manager), `on_behalf_of` (`user_address`), `referral_code` (from config).
2.  **If `token_address` is ERC20:**
    *   **Approve:** Approve Lending Pool Manager contract to spend `amount` of `token_address` from `user_address`.
    *   Call Lending Pool Manager's `supply` function.
    *   *Conceptual Parameters:* `asset (token_address)`, `amount`, `on_behalf_of (user_address)`, `referral_code`.
3.  Build, sign, send transaction. Wait for receipt.

**Action: `withdraw`**
*Note: `amount` is assumed to be the amount of the underlying asset to withdraw.*
1.  **If `token_address` is native ETH (meaning withdrawing zETH and converting to ETH):**
    *   Call Lending Pool Manager's `withdraw` function for the underlying ETH.
    *   *Conceptual Parameters:* `asset (underlying_ETH_address_or_zETH_address)`, `amount`, `to (user_address)`.
    *   *Alternatively, if WETH Gateway handles this:* Call WETH Gateway's `withdrawETH`.
2.  **If `token_address` is ERC20 (withdrawing the underlying ERC20):**
    *   Call Lending Pool Manager's `withdraw` function.
    *   *Conceptual Parameters:* `asset (token_address)`, `amount`, `to (user_address)`.
3.  Build, sign, send transaction. Wait for receipt.

**Action: `borrow`**
1.  *(Optional Pre-check):* Call a view function on Lending Pool Manager to check user's borrowing power / health factor (e.g., `getUserAccountData(user_address)`).
2.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `borrowETH` (or equivalent on Lending Pool Manager).
    *   *Conceptual Parameters:* `lending_pool_address`, `amount`, `interest_rate_mode` (from config), `referral_code`, `on_behalf_of (user_address)`.
3.  **If `token_address` is ERC20:**
    *   Call Lending Pool Manager's `borrow` function.
    *   *Conceptual Parameters:* `asset (token_address)`, `amount`, `interest_rate_mode`, `referral_code`, `on_behalf_of (user_address)`.
4.  Build, sign, send transaction. Wait for receipt.

**Action: `repay`**
1.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `repayETH` (or equivalent). `msg.value` will be `amount`.
    *   *Conceptual Parameters:* `lending_pool_address`, `amount` (or special value for max repayment), `interest_rate_mode`, `on_behalf_of (user_address)`.
2.  **If `token_address` is ERC20:**
    *   **Approve:** Approve Lending Pool Manager contract to spend `amount` (or max for full repayment) of `token_address` from `user_address`.
    *   Call Lending Pool Manager's `repay` function.
    *   *Conceptual Parameters:* `asset (token_address)`, `amount` (or special value for max repayment), `interest_rate_mode`, `on_behalf_of (user_address)`.
3.  Build, sign, send transaction. Wait for receipt.

**Action: `set_collateral`**
1.  Requires `token_address` of the supplied asset and `collateral_status (bool)`.
2.  Call Lending Pool Manager's `setUserUseReserveAsCollateral` function.
    *   *Conceptual Parameters:* `asset (token_address_of_supplied_asset)`, `use_as_collateral (collateral_status)`.
3.  Build, sign, send transaction. Wait for receipt.

### 3.4. `perform_random_activity(user_address, private_key, config)`

This function orchestrates a randomized sequence of other zkSync Era actions (`bridge_eth`, `swap_tokens`, `lend_borrow`) based on a detailed configuration. Its primary goal is to simulate diverse, human-like on-chain activity.

**Parameters:**
-   `user_address (str)`: The address performing the random activities.
-   `private_key (str)`: Private key for `user_address` to sign transactions.
-   `config (dict)`: Configuration dictionary, including a `random_activity` section (see Section 2).

**Returns:**
-   `Tuple[bool, str]`: A tuple containing a boolean indicating overall success (e.g., if at least one action succeeded or no actions were configured but no errors occurred), and a summary message string detailing the executed actions and their outcomes.

**Interaction Strategy & Logic Flow:**

1.  **Initialization:**
    *   Validate inputs and the `config.random_activity` structure. If disabled or invalid, return appropriately.
    *   Fetch initial L2 balances for tokens specified in `config.random_activity.initial_state_fetch.tokens_to_track_balance`.
    *   Fetch initial EraLend positions (supplied, borrowed, collateral status) for `user_address`. Store this data in an in-memory state manager.

2.  **Determine Number of Actions:**
    *   Randomly select `num_total_actions` to perform based on `config.random_activity.num_actions_range`.

3.  **Main Action Loop:**
    *   Loop `num_total_actions` times:
        a.  **Select Action Type & Randomize Parameters:**
            *   Attempt (up to `config.random_activity.max_action_selection_retries`) to:
                1.  Select an action type (`bridge_eth`, `swap_tokens`, `lend_borrow`) using weights from `config.random_activity.action_weights`.
                2.  Randomize its specific parameters based on the corresponding sub-configuration (e.g., `config.random_activity.bridge_eth`, `config.random_activity.swap_tokens`, `config.random_activity.lend_borrow`) and the current in-memory state (e.g., available balances, existing lend/borrow positions).
                3.  Validate if the action with the randomized parameters is currently feasible (e.g., sufficient balance, collateral, no conflicting states like trying to withdraw an asset not supplied).
                4.  If not feasible, log the reason and retry selection. If all retries fail, skip this iteration's action and log it.
        b.  **Execute Action:**
            *   If a feasible action is selected:
                *   Call the corresponding internal function (`self.bridge_eth(...)`, `self.swap_tokens(...)`, `self.lend_borrow(...)`) with the randomized parameters.
                *   Log the attempt, parameters, and the outcome (success/failure, transaction hash or error message).
        c.  **Update Internal State:** If the individual action was successful, update the in-memory L2 balances and EraLend positions.
        d.  **Handle Individual Action Failure:**
            *   If an action fails, log the error.
            *   If `config.random_activity.stop_on_first_failure` is `True`, break the loop. Otherwise, continue to the next planned action.

4.  **Return Overall Status:**
    *   Compile a summary message detailing all attempted actions and their outcomes.
    *   The overall success is typically `True` if at least one action succeeded or if no actions were configured but no errors occurred during setup.
    *   Return `(overall_success, summary_message)`.

**State Management (Intra-call):**
*   The function maintains an in-memory state *during a single execution sequence*. This state is not persisted between calls.
*   **Data Tracked:**
    *   `l2_balances`: Dictionary of token symbols to their L2 balances (in ether units).
    *   `eralend_positions`: Dictionary detailing supplied amounts, borrowed amounts, and collateral status for assets on EraLend.
*   This state is used to:
    *   Randomize parameters realistically (e.g., swap % of balance).
    *   Check feasibility of actions (e.g., cannot borrow without collateral, cannot withdraw more than supplied).
    *   Reflect changes after each successful action.

**Parameter Randomization Details:**

*   **`bridge_eth`:**
    *   `amount_eth`: Random float within `config.random_activity.bridge_eth.amount_range_eth`.
    *   `to_l2`: Boolean based on `config.random_activity.bridge_eth.probability_to_l2`.
*   **`swap_tokens` (SyncSwap):**
    *   `token_in_address`, `token_out_address`: Selected from `config.random_activity.swap_tokens.token_pairs`.
    *   `amount_in`: Percentage (from `config.random_activity.swap_tokens.amount_in_percentage_range`) of available `token_in` balance, converted to wei.
    *   `slippage_bps`: Random integer from `config.random_activity.swap_tokens.slippage_bps_range`.
*   **`lend_borrow` (EraLend):**
    *   `action`: Selected from `config.random_activity.lend_borrow.sub_action_weights`.
    *   `token_address`: Selected from `config.random_activity.lend_borrow.supported_tokens`. For `withdraw`/`repay`/`set_collateral`, selection is prioritized from assets with existing positions.
    *   `amount`: Calculated as a percentage of relevant L2 balance, supplied amount, borrow capacity, or debt, based on ranges in `config.random_activity.lend_borrow` (e.g., `supply_amount_percentage_range`).
    *   `collateral_status`: For `set_collateral`, based on `config.random_activity.lend_borrow.set_collateral_enable_probability`.

## 4. Technical Details & Dependencies

**Primary Dependency:**
-   `web3.py>=6.0.0`: For all Ethereum L1 and zkSync Era L2 interactions.
-   `random` (Python standard library): Used by `perform_random_activity` for selection and parameter randomization.

**zkSync Era Specifics:**
-   **Gas Model:** zkSync Era transactions incur fees for both L2 execution and L1 data availability (pubdata). The L1 bridge deposit function often requires specifying L2 gas parameters like `_l2GasLimit` and `_l2GasPerPubdataByteLimit`. For L2 transactions, these are also important.
-   **Transaction Types:** zkSync Era primarily uses EIP-712 typed transactions. Ensure `web3.py` and the signing process correctly handle these for zkSync. If not, specific EIP-712 signing logic might be needed.
-   **Contract ABIs:** The ABIs for the L1 zkSync Bridge contract and the L2 Bridge/WETH contract are crucial. These should be obtained from official zkSync Era documentation or block explorers and stored securely, accessible via the `config`.
    *   L1 Bridge ABI (Example functions): `requestL2Transaction`, `depositETH`, `l2TransactionBaseCost`.
    *   L2 Bridge/WETH ABI (Example functions): `withdraw`, `initiateWithdrawal`.
    *   **DEX Router ABI (Example for SyncSwap):** `swapExactTokensForTokens`, `swapExactETHForTokens`, `swapTokensForExactETH`, `getAmountsOut`, `getAmountsIn`. (Actual function names and parameters must be verified from the specific DEX router ABI during implementation).
    *   **Lending Protocol ABIs (Example for EraLend - VERIFY!):**
        *   Lending Pool Manager/Core ABI: Functions like `supply`, `withdraw`, `borrow`, `repay`, `setUserUseReserveAsCollateral`, `getUserAccountData`.
        *   WETH Gateway ABI (if applicable): Functions like `depositETH`, `withdrawETH`, `borrowETH`, `repayETH`.
        *   zToken/eToken ABI: Standard ERC20 functions (`approve`, `balanceOf`), potentially `withdraw` if not via manager.
    *(Actual function names and parameters must be verified during implementation).*

## 5. Error Handling & Logging

**Common Error Scenarios for `bridge_eth`:**
-   **Insufficient L1 Balance:** For `amount_eth` + L1 gas + L2 gas pre-payment.
    *   *Handling:* Pre-flight balance check. Catch transaction reversion.
-   **Insufficient L2 Balance:** For `amount_eth` + L2 gas.
    *   *Handling:* Pre-flight balance check. Catch transaction reversion.
-   **Incorrect L1/L2 Gas Estimation:** Leading to transaction failure.
    *   *Handling:* Use conservative gas limits (e.g., via `gas_limit_multiplier`). Log detailed gas estimation parameters.
-   **RPC Errors:** Node connectivity issues, rate limiting.
    *   *Handling:* Implement retries with backoff. Allow configuration of multiple RPC endpoints.
-   **Transaction Reversion:** Due to incorrect parameters, contract state, slippage (if applicable to bridge), etc.
    *   *Handling:* Catch exceptions, log detailed error messages from the receipt.
-   **Private Key Issues:** Incorrect or compromised key.
    *   *Handling:* Secure key management. Fail gracefully.
-   **ABI/Contract Mismatch:** Incorrect ABI or contract address.
    *   *Handling:* Ensure config is correct. Fail early if contract loading fails.

**Common Error Scenarios for `swap_tokens`:**
-   **Insufficient Liquidity:** `getAmountsOut` may return zero or very low values, or the swap transaction itself may revert.
    *   *Handling:* Check `getAmountsOut` result. Catch transaction reversion and log details.
-   **Excessive Slippage / Price Impact (DEADLINE_EXCEEDED or INSUFFICIENT_OUTPUT_AMOUNT):** Transaction reverts if `amountOutMin` cannot be met or if the price moves too much before execution.
    *   *Handling:* Catch transaction reversion. The `amountOutMin` parameter is designed to prevent this. Ensure deadline is reasonable.
-   **Token Approval Failure:** The `approve` transaction for `token_in` fails or does not confirm.
    *   *Handling:* Ensure `approve` transaction is successful and confirmed before proceeding to swap.
-   **Insufficient Token Balance:** User does not have enough `token_in` or ETH for gas.
    *   *Handling:* Pre-flight balance checks. Catch transaction reversion.
-   **Invalid Path:** The token path provided to the router is invalid or unsupported.
    *   *Handling:* Ensure path construction logic is correct. Catch transaction reversion.
-   **DEX Specific Errors:** Router might have custom error messages (e.g., "SyncSwap: K").
    *   *Handling:* Log detailed error messages from the receipt. Consult DEX documentation for specific error codes.
-   **RPC Errors / Network Issues:** As with `bridge_eth`.
    *   *Handling:* Retries with backoff.
-   **Gas Estimation Failures:**
    *   *Handling:* Use conservative gas limits. Log detailed gas parameters.

**Common Error Scenarios for `lend_borrow` (Examples - Verify with EraLend docs!):**
-   **Input Validation:** Invalid address, amount <= 0, unsupported action/token/protocol.
-   **RPC Errors:** Node unavailable, rate limiting. (Implement retry logic).
-   **Transaction Reversions (General):**
    *   Log detailed error from receipt.
    *   `NotEnoughBalance`: Insufficient ETH for gas.
    *   `TransactionFailed`: Generic failure.
-   **Token Approval Failures:** `approve` transaction fails or doesn't confirm.
-   **Lending Protocol Specific Errors:**
    *   `COLLATERAL_CANNOT_BE_ZERO`: Trying to borrow without collateral.
    *   `HEALTH_FACTOR_LOWER_THAN_LIQUIDATION_THRESHOLD`: Borrowing would make Health Factor too low / lead to liquidation.
    *   `NO_BORROWING_POWER`: User cannot borrow this amount.
    *   `ASSET_NOT_BORROWABLE`: The specified asset cannot be borrowed on the protocol.
    *   `ASSET_NOT_LISTED`: Token not supported by the protocol.
    *   `INSUFFICIENT_LIQUIDITY`: Not enough of the asset available in the pool to borrow or withdraw.
    *   `AMOUNT_BIGGER_THAN_SUPPLY`: Trying to withdraw more than supplied/available.
    *   `AMOUNT_BIGGER_THAN_DEBT`: Trying to repay more than owed (unless using a "max repay" flag/amount).
    *   `MARKET_PAUSED`: Action on this market is temporarily disabled by protocol governance.
    *   `INVALID_INTEREST_RATE_MODE`: Specified interest rate mode is not valid.
-   **Handling Strategy:**
    *   Catch specific exceptions where possible based on error strings or codes if available.
    *   Log all transaction inputs, attempts, and outcomes (success/failure with tx hash or error message).
    *   Return `(False, error_message_string)` on failure, providing a clear reason.

**Common Error Scenarios for `perform_random_activity`:**
-   **Invalid `random_activity` Configuration:** Missing keys, invalid ranges, incorrect weights.
    *   *Handling:* Validate configuration at the start. Return `(False, "Invalid configuration")`.
-   **Parameter Generation Failure:** E.g., trying to select from an empty list of token pairs, or balance too low for configured percentage amounts.
    *   *Handling:* Log the issue. Skip the current action or retry selection if configured.
-   **State Fetching Failure:** RPC errors when fetching initial L2 balances or EraLend positions.
    *   *Handling:* Propagate error, potentially stopping the entire sequence.
-   **Action Feasibility Check Failure:** Logic error in determining if a randomized action is possible with current state.
    *   *Handling:* Log extensively. May indicate a bug in the feasibility logic or state update.
-   **Sequential Logic Errors:** E.g., trying to repay a loan that was never successfully borrowed in the current sequence due to an earlier failure.
    *   *Handling:* Robust state tracking and feasibility checks are key.
-   **Errors from Underlying Functions:** `bridge_eth`, `swap_tokens`, `lend_borrow` can fail.
    *   *Handling:* Log the error from the sub-function. Decide whether to continue or stop based on `config.random_activity.stop_on_first_failure`.
-   **Max Retries Exceeded:** If `max_action_selection_retries` is reached without finding a feasible action.
    *   *Handling:* Log and skip the current action iteration.

**Logging:**
-   Log all key parameters at the start of the function.
-   Log transaction hashes for both L1 and L2 operations.
-   Log success or failure status with relevant details.
-   Log any caught exceptions with full tracebacks.

## 6. Testing Strategy
*(Placeholder for `bridge_eth` specific testing notes, e.g., mocking L1/L2 providers, contract calls, testing deposit and withdrawal paths separately).*