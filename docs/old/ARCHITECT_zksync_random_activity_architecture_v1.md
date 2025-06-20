# Architectural Plan: zkSync Era - perform_random_activity

**Version:** 1.0
**Date:** 2025-05-30
**Author:** Roo-Architect

## 1. Introduction

This document outlines the technical architecture for the `perform_random_activity` function within the zkSync Era protocol module. This function is designed to orchestrate a randomized sequence of other implemented zkSync Era actions (`bridge_eth`, `swap_tokens`, `lend_borrow`) based on a user-defined configuration. The goal is to simulate more human-like on-chain activity for airdrop farming.

**Function Signature (from `zksync.py`):**
`perform_random_activity(user_address: str, private_key: str, config: Dict[str, Any]) -> Tuple[bool, str]`

## 2. Core Architectural Decisions

### 2.1. Random Activity Selection Strategy

1.  **Selection Method:**
    *   Activities (`bridge_eth`, `swap_tokens`, `lend_borrow`) will be selected randomly based on weights specified in the `config.random_activity.action_weights`.
    *   Example: `config.random_activity.action_weights = {"bridge_eth": 30, "swap_tokens": 50, "lend_borrow": 20}`.
    *   The Python `random.choices()` function can be used with these weights.

2.  **Number of Actions:**
    *   The number of actions to perform per call to `perform_random_activity` will be a random integer within a range defined in `config.random_activity.num_actions_range`.
    *   Example: `config.random_activity.num_actions_range = [2, 5]` (meaning 2, 3, 4, or 5 actions).

3.  **Statefulness and Prerequisites:**
    *   **Intra-call State:** The function will maintain a simple internal state *during a single execution sequence* to handle basic dependencies. This state will not persist between calls to `perform_random_activity`.
    *   **State Tracking (Conceptual - details in Section 2.3):**
        *   Track available L2 balances of key tokens.
        *   Track supplied/borrowed amounts per asset in EraLend.
    *   **Dependency Handling Logic:**
        *   **`swap_tokens`**: Requires sufficient balance of `token_in`.
        *   **`lend_borrow ('withdraw')`**: Requires a prior `supply` of that asset.
        *   **`lend_borrow ('repay')`**: Requires a prior `borrow` of that asset.
        *   **`lend_borrow ('borrow')`**: Requires sufficient collateral and available liquidity. The function should check EraLend user account data.
        *   **Selection Retry/Skip:** If a selected action is not feasible due to unmet prerequisites or insufficient balance (after parameter randomization), the system will:
            1.  Attempt to re-select a different action (up to `config.random_activity.max_action_selection_retries` times).
            2.  If still not feasible, skip this iteration's action and log it.
    *   **Initial State Fetch:** Before the action loop, fetch initial L2 balances and EraLend user account data.

### 2.2. Parameter Randomization for Selected Actions

Parameters for each action will be randomized based on sub-configurations within `config.random_activity`.

1.  **`bridge_eth` Parameters:**
    *   `amount_eth (float)`: Randomized within a range (e.g., `[0.01, 0.05]` ETH) specified in `config.random_activity.bridge_eth.amount_range_eth`.
    *   `to_l2 (bool)`: Determined by a probability (e.g., `config.random_activity.bridge_eth.probability_to_l2 = 0.7`).

2.  **`swap_tokens` Parameters (SyncSwap):**
    *   `token_in_address (str)`, `token_out_address (str)`: Selected from `config.random_activity.swap_tokens.token_pairs`. Addresses looked up from `config.tokens`.
    *   `amount_in (int)`: Randomized as a percentage of the available balance of `token_in` (e.g., `config.random_activity.swap_tokens.amount_in_percentage_range = [0.1, 0.3]`). Converted to wei.
    *   `slippage_bps (int)`: Randomized within a range (e.g., `config.random_activity.swap_tokens.slippage_bps_range = [30, 100]`).
    *   `dex_name (str)`: Fixed to "syncswap".

3.  **`lend_borrow` Parameters (EraLend):**
    *   `action (str)`: Selected randomly based on weights from `config.random_activity.lend_borrow.sub_action_weights`.
    *   `token_address (str)`: Selected from `config.random_activity.lend_borrow.supported_tokens`. For `withdraw`/`repay`/`set_collateral`, selection should be from assets already supplied/borrowed.
    *   `amount (int)`:
        *   **Supply:** Percentage of available L2 balance (e.g., `config.random_activity.lend_borrow.supply_amount_percentage_range`).
        *   **Borrow:** Percentage of available borrowing capacity (e.g., `config.random_activity.lend_borrow.borrow_amount_percentage_of_capacity_range`).
        *   **Withdraw:** Percentage of supplied amount (e.g., `config.random_activity.lend_borrow.withdraw_amount_percentage_of_supplied_range`).
        *   **Repay:** Percentage of borrowed amount (e.g., `config.random_activity.lend_borrow.repay_amount_percentage_of_debt_range`). Option for `repay_all_debt_probability`.
        *   Converted to wei.
    *   `collateral_status (bool)`: For `set_collateral`, based on `config.random_activity.lend_borrow.set_collateral_enable_probability`.
    *   `lending_protocol_name (str)`: Fixed to "eralend".

### 2.3. State Management (Intra-call)

*   **Objective:** Manage state *during a single execution sequence* of `perform_random_activity`. Not persisted across calls.
*   **Data to Track (in-memory):**
    *   `l2_balances`: Dict ` {token_symbol: Decimal(balance_in_ether_units)}`. Fetched at start, updated after actions.
    *   `eralend_positions`: Dict ` {token_symbol: {"supplied": Decimal, "borrowed": Decimal, "is_collateral": bool}}`. Fetched at start, updated after `lend_borrow` actions.
*   **Updating State:**
    *   After successful `bridge_eth` (L1->L2 deposit): Increment L2 ETH balance. (L2->L1 withdrawal also affects L2 ETH).
    *   After successful `swap_tokens`: Update L2 balances of `token_in` and `token_out`.
    *   After successful `lend_borrow`: Update `l2_balances` and `eralend_positions` accordingly.
*   **Using State for Feasibility Checks:**
    *   Before any action, check if the randomized parameters are viable given the current `l2_balances` and `eralend_positions`.
    *   For `lend_borrow ('borrow')`, check health factor against `config.random_activity.lend_borrow.min_health_factor_before_borrow`.

### 2.4. Configuration Schema (`config.random_activity`)

A new section `random_activity` will be added to the main zkSync `config`.

```python
# Example structure for config['random_activity']
# This should be part of the main ZKSYNC_CONFIG dictionary
# ZKSYNC_CONFIG = {
#     "networks": { ... },
#     "tokens": { ... },
#     "settings": { ... },
#     "random_activity": {
#         "enabled": True,
#         "num_actions_range": [2, 4],  # Min and max number of actions
#         "action_weights": {
#             "bridge_eth": 20,
#             "swap_tokens": 50,
#             "lend_borrow": 30
#         },
#         "max_action_selection_retries": 3,
#         "stop_on_first_failure": False, # Default: continue all N actions
#
#         "bridge_eth": {
#             "amount_range_eth": [0.005, 0.01], # In ETH units (float/Decimal)
#             "probability_to_l2": 0.6
#         },
#
#         "swap_tokens": { # For SyncSwap
#             "token_pairs": [ # List of (token_in_symbol, token_out_symbol)
#                 ("ETH", "USDC"), ("USDC", "ETH")
#                 # Symbols must be defined in main config.tokens
#             ],
#             "amount_in_percentage_range": [0.1, 0.25], # % of token_in balance
#             "slippage_bps_range": [30, 70]
#         },
#
#         "lend_borrow": { # For EraLend
#             "sub_action_weights": {
#                 "supply": 40, "withdraw": 15, "borrow": 25,
#                 "repay": 15, "set_collateral": 5
#             },
#             "supported_tokens": ["ETH", "USDC"], # Symbols from config.tokens
#             # Amount ranges are percentages of relevant balances/positions
#             "supply_amount_percentage_range": [0.15, 0.5], # of L2 balance
#             "withdraw_amount_percentage_of_supplied_range": [0.2, 0.8],
#             "borrow_amount_percentage_of_capacity_range": [0.1, 0.3],
#             "repay_amount_percentage_of_debt_range": [0.2, 0.7],
#             "repay_all_debt_probability": 0.1,
#             "set_collateral_enable_probability": 0.75,
#             "min_health_factor_before_borrow": 1.2
#         },
#
#         "initial_state_fetch": {
#             "tokens_to_track_balance": ["ETH", "USDC", "WETH"]
#         }
#     }
# }
```
*(Note: The Python snippet above is illustrative of the structure and should be integrated into the main `ZKSYNC_CONFIG` definition in `airdrops/docs/protocols/zksync.md`)*

### 2.5. Function Logic Flow

1.  **Initialization:**
    *   Log start. Validate inputs (`user_address`, `private_key`, `config`).
    *   If `config.random_activity.enabled` is `False`, return `(True, "Random activity disabled in config.")`.
    *   Validate `config.random_activity` structure. If invalid, return `(False, "Invalid random_activity configuration")`.
    *   Fetch initial L2 balances and EraLend positions, store in local state variables.

2.  **Determine Number of Actions:**
    *   Randomly select `num_total_actions` from `config.random_activity.num_actions_range`.

3.  **Main Action Loop:**
    *   Initialize `successful_actions_count = 0`, `executed_actions_log = []`.
    *   Loop `num_total_actions` times:
        a.  **Select Action Type & Randomize Parameters:**
            *   Attempt (up to `max_action_selection_retries`) to:
                1.  Select an action type (`bridge_eth`, `swap_tokens`, `lend_borrow`) using weights.
                2.  Randomize its parameters using the configuration and current internal state.
                3.  Validate feasibility of the action with these parameters.
                4.  If not feasible, log and retry selection. If all retries fail, skip this iteration's action.
        b.  **Execute Action:**
            *   If a feasible action is selected and parameters are determined:
                *   Call the corresponding function (`self.bridge_eth()`, `self.swap_tokens()`, `self.lend_borrow()`).
                *   Log the attempt, parameters, and outcome (success/failure, tx_hash/error). Add to `executed_actions_log`.
        c.  **Update Internal State:** If the action was successful, update local `l2_balances` and `eralend_positions`. Increment `successful_actions_count`.
        d.  **Handle Individual Action Failure:** If an action returns `success=False`:
            *   If `config.random_activity.stop_on_first_failure` is `True`, break the loop and proceed to reporting.
            *   Otherwise, continue to the next planned action.

4.  **Return Overall Status:**
    *   Compile a summary message from `executed_actions_log`.
    *   Overall success is `True` if `successful_actions_count > 0` (or if `num_total_actions == 0` and no errors).
    *   Return `(overall_success, summary_message)`.

### 2.6. Error Handling

*   **Configuration Errors:** Validated at the start. Parameter generation issues (e.g., empty lists, invalid ranges) should be handled gracefully, potentially skipping an action.
*   **Underlying Action Errors:** Errors from sub-functions are logged. `perform_random_activity` continues or stops based on `stop_on_first_failure`.
*   **State Management Errors:** Robust updates to internal state are critical.
*   **Reporting:** The final summary message and detailed logs are key.

## 3. Helper Functions (Conceptual for Implementation)

*   `_validate_random_activity_config(config_section)`
*   `_get_initial_onchain_state(user_address, config, w3_l2)`: Fetches balances and EraLend data.
*   `_select_action_and_params(config_random, current_state)`: Orchestrates selection, randomization, and feasibility checks.
*   `_randomize_bridge_parameters(bridge_config, current_state)`
*   `_randomize_swap_parameters(swap_config, current_state)`
*   `_randomize_lend_borrow_parameters(lend_borrow_config, current_state)`
*   `_check_action_feasibility(action_type, params, current_state)`
*   `_update_internal_state(current_state, action_type, params, success, result_details)`

## 4. Impact on `airdrops/docs/protocols/zksync.md`

*   **Section 2 (Configuration):** Add the `random_activity` sub-dictionary to the main `ZKSYNC_CONFIG` example.
*   **Section 3.4 (`perform_random_activity()`):** Replace placeholder with detailed description based on this architecture.
*   **Section 4 (Technical Details):** Mention any new dependencies or considerations for `perform_random_activity` (e.g., `random` module).
*   **Section 5 (Error Handling):** Add error scenarios specific to `perform_random_activity` orchestration logic.

## 5. PCRM Analysis

*   **Pros:**
    *   Simulates diverse, human-like on-chain activity, potentially improving airdrop eligibility.
    *   High degree of automation for complex interaction sequences.
    *   Configurable to adapt to different strategies and risk profiles.
*   **Cons:**
    *   Increased complexity in configuration and internal state management.
    *   Potential for unintended transaction sequences if configuration is not carefully set.
    *   Debugging can be complex due to the randomized nature.
*   **Risks:**
    *   **Fund Loss:** Bugs in randomization, state management, or feasibility checks could lead to suboptimal trades or loss of funds.
    *   **Transaction Failures:** On-chain conditions (slippage, low liquidity) or RPC issues can cause individual actions to fail.
    *   **Configuration Errors:** Incorrect or illogical configuration can lead to undesirable behavior or repeated failures.
    *   **Gas Cost Inefficiency:** Random actions might not always be gas-optimal.
*   **Mitigations:**
    *   **Thorough Unit & Integration Testing:** Especially for randomization logic, state updates, and feasibility checks.
    *   **Clear and Comprehensive Configuration Validation:** Fail fast on invalid configurations.
    *   **Robust Error Handling & Logging:** Detailed logging for each step and action.
    *   **Sensible Default Configurations:** Provide safe and reasonable defaults.
    *   **Detailed Documentation:** For configuration and behavior.
    *   **(Future) Dry-Run Mode:** Allow simulation without actual transactions.
    *   **(Future) Gas Price Awareness:** Incorporate checks for high gas prices before executing a sequence.

This concludes the architectural plan for `perform_random_activity`.