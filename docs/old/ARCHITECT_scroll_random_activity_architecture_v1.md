# Architecture: `perform_random_activity_scroll` Function v1

**Version:** 1.0
**Date:** 2025-05-31
**Author:** Roo-Architect

## 1. Objective

To design the architecture for the `perform_random_activity_scroll` function within the `airdrops.protocols.scroll` module. This function will randomly select and execute one or a sequence of the already implemented Scroll protocol functions (`bridge_assets`, `swap_tokens`, `provide_liquidity_scroll`, `lend_borrow_layerbank_scroll`) to increase on-chain interaction diversity for airdrop farming purposes.

## 2. Function Signature

```python
from typing import List, Dict, Any, Union, Tuple
from web3 import Web3

def perform_random_activity_scroll(
    web3_l1: Web3,
    web3_scroll: Web3,
    private_key: str,
    action_count: int,
    config: Dict[str, Any]
) -> Tuple[bool, Union[List[str], str]]:
    """
    Performs a random sequence of actions on the Scroll network.

    Args:
        web3_l1 (Web3): Web3 instance for L1 (Ethereum).
        web3_scroll (Web3): Web3 instance for Scroll L2.
        private_key (str): Private key of the account performing actions.
        action_count (int): The number of random actions to perform (e.g., 1 to N).
        config (Dict[str, Any]): Configuration dictionary. Expected to contain
                                 a 'random_activity_scroll' key with specific
                                 configurations for this function, including
                                 parameters for sub-actions.

    Returns:
        Tuple[bool, Union[List[str], str]]: A tuple where the first element is a boolean
                                            indicating overall success (True if all actions
                                            were attempted according to stop_on_failure policy,
                                            False if a critical setup error occurred).
                                            The second element is a list of transaction hashes
                                            for successful actions, or an error message string
                                            if the process failed catastrophically before any actions.
                                            Individual action failures within a sequence will be logged.
    """
    pass
```

## 3. Core Logic - Random Action Selection & Execution

### 3.1. Action Pool

The pool of available actions consists of the following functions from [`airdrops/src/airdrops/protocols/scroll/scroll.py`](../../airdrops/src/airdrops/protocols/scroll/scroll.py):
1.  `bridge_assets(...)`
2.  `swap_tokens(...)` (SyncSwap)
3.  `provide_liquidity_scroll(...)` (SyncSwap)
4.  `lend_borrow_layerbank_scroll(...)` (LayerBank V2)

### 3.2. Random Selection

*   **Method:** Actions will be selected using `random.choices()` (or `random.choice()` if `action_count` is 1) from the defined action pool.
*   **Weighting:** The `config` parameter can include weights for each action (via `config['random_activity_scroll']['action_weights']`), allowing certain actions to be selected more frequently. If weights are not provided or are invalid, selection will be uniform.
    ```json
    // Example in config['random_activity_scroll']['action_weights']
    {
        "bridge_assets": 0.1,
        "swap_tokens": 0.4,
        "provide_liquidity_scroll": 0.2,
        "lend_borrow_layerbank_scroll": 0.3
    }
    ```

### 3.3. Parameter Generation/Selection

For each selected action, its required parameters will be determined as follows:

*   **Fixed Parameters:**
    *   `web3_l1`, `web3_scroll`, `private_key`: Passed directly from `perform_random_activity_scroll` arguments.
*   **Intelligent/Random Parameters (configured via `config['random_activity_scroll'][<action_name>]`):**
    *   **General Strategy:**
        *   A helper function, e.g., `_get_wallet_balances(web3_instance, address, tokens_to_check)`, will be used to fetch current ETH and specified ERC20 token balances on Scroll L2. This helps in making realistic choices for amounts.
        *   The `config` will define allowable tokens, token pairs, amount ranges (absolute or as a percentage of balance), slippage, etc., for each type of action.
    *   **`bridge_assets`:**
        *   `direction`: Randomly chosen from configured options (e.g., `[("deposit", 0.5), ("withdraw", 0.5)]`).
        *   `token_symbol`: Randomly chosen from a configured list (e.g., `["ETH", "USDC"]`).
        *   `amount`: Randomly chosen from a configured range (e.g., 0.001-0.005 ETH). If withdrawing, check L2 balance. If depositing, check L1 balance.
        *   `recipient_address`: Defaults to sender's address.
    *   **`swap_tokens`:**
        *   `token_in_symbol`, `token_out_symbol`: Randomly chosen from a configured list of valid weighted pairs (e.g., `[("ETH", "USDC", 0.5), ("USDC", "WETH", 0.3)]`).
        *   `amount_in`: Randomly chosen from a configured range or as a percentage of the `token_in` balance. Ensure balance exists.
        *   `slippage_percent`: From config.
    *   **`provide_liquidity_scroll`:**
        *   `action`: Randomly chosen from configured options (e.g., `[("add", 0.7), ("remove", 0.3)]`).
        *   `token_a_symbol`, `token_b_symbol`: Randomly chosen from configured weighted pairs.
        *   `amount_a_desired`, `amount_b_desired` (for "add"): Randomly chosen from ranges or as percentages of balances. Ensure balances exist.
        *   `lp_token_amount` (for "remove"): If removing, this implies prior state. The function will attempt to fetch current LP balance for the selected pair and use a percentage of it, as defined in config.
        *   `slippage_percent`: From config.
    *   **`lend_borrow_layerbank_scroll`:**
        *   `action`: Randomly chosen from configured weighted options (e.g., `[("lend", 0.4), ("borrow", 0.2)]`).
        *   `token_symbol`: Randomly chosen from configured list (e.g., `["ETH", "USDC"]`).
        *   `amount`:
            *   "lend": Percentage of available `token_symbol` balance.
            *   "borrow": Percentage of available collateral value. Requires fetching current collateral/borrow state.
            *   "repay": Percentage of current debt for `token_symbol`. Requires fetching debt state.
            *   "withdraw": Percentage of currently supplied `token_symbol`. Requires fetching supply state.
        *   Fetching LayerBank specific state (collateral, debt, supply) via helper functions will be necessary for intelligent "borrow", "repay", "withdraw" actions.

### 3.4. Sequential Execution

*   If `action_count > 1`, actions will be executed sequentially.
*   **Delays:** The `config` can specify an optional random delay range (e.g., `config['random_activity_scroll']['inter_action_delay_seconds_range'] = [60, 300]`) between actions.

### 3.5. State Management (Simple for V1)

*   **V1 Approach:** Actions are largely treated as independent. Parameter generation will query current on-chain state (balances, LP tokens, LayerBank positions) immediately before each action to make informed decisions.
*   Complex state passing (e.g., ensuring USDC bridged in step 1 is specifically earmarked for a swap in step 2) is out of scope for V1.

### 3.6. Calling Sub-Functions

*   A dispatch mechanism (e.g., a dictionary mapping action names to function objects) will be used.
*   The selected sub-function will be called with the generated parameters.
    ```python
    # Conceptual
    # import airdrops.protocols.scroll.scroll as scroll_module
    # action_map = {
    #     "bridge_assets": scroll_module.bridge_assets,
    #     "swap_tokens": scroll_module.swap_tokens,
    #     # ...
    # }
    # action_to_call = action_map[selected_action_name]
    # params_for_action = _generate_params_for_scroll_action(selected_action_name, ...)
    # tx_hash = action_to_call(**params_for_action)
    ```

## 4. Configuration for Randomness

The "randomness" will be primarily configured via the `config['random_activity_scroll']` dictionary.

```python
# Example structure for config['random_activity_scroll']
# This would be a value within the main `config` object passed to the function.
# e.g., main_config['random_activity_scroll'] = { ... }
"""
random_activity_scroll_config_example = {
    "action_weights": { # Optional, defaults to uniform if not provided
        "bridge_assets": 0.1,
        "swap_tokens": 0.4,
        "provide_liquidity_scroll": 0.2,
        "lend_borrow_layerbank_scroll": 0.3
    },
    "stop_on_failure": True, # If True, sequence stops on first sub-action error
    "inter_action_delay_seconds_range": [60, 300], # Optional delay [min, max]

    "bridge_assets": {
        "directions": [("deposit", 0.5), ("withdraw", 0.5)], # action and weight
        "tokens_l1_l2": ["ETH", "USDC"], # Tokens that can be bridged
        "amount_eth_range": [0.001, 0.005], # Min-max for ETH bridging
        "amount_usdc_range": [1, 10]      # Min-max for USDC bridging (actual units)
    },
    "swap_tokens": { # SyncSwap
        "token_pairs": [ # (token_in, token_out, weight)
            ("ETH", "USDC", 0.5),
            ("USDC", "WETH", 0.3),
            ("WETH", "USDC", 0.2)
        ],
        "amount_eth_percent_range": [5, 15], # Percentage of available ETH balance
        "amount_usdc_percent_range": [10, 30], # Percentage of available USDC balance
        "slippage_percent": 0.5
    },
    "provide_liquidity_scroll": { # SyncSwap
        "actions": [("add", 0.7), ("remove", 0.3)],
        "token_pairs": [ # (token_a, token_b, weight)
            ("ETH", "USDC", 1.0)
        ],
        "add_amount_eth_percent_range": [5, 10],
        "add_amount_usdc_percent_range": [5, 10],
        "remove_lp_percent_range": [20, 50], # Percentage of available LP tokens for the pair
        "slippage_percent": 0.5
    },
    "lend_borrow_layerbank_scroll": { # LayerBank V2
        "actions": [ # (action_name, weight)
            ("lend", 0.4),
            ("borrow", 0.2), # Borrowing requires existing collateral
            ("repay", 0.2),  # Repaying requires existing debt
            ("withdraw", 0.2) # Withdrawing requires existing supply
        ],
        "tokens": ["ETH", "USDC"], # Tokens to interact with
        "lend_amount_eth_percent_range": [10, 25],
        "lend_amount_usdc_percent_range": [10, 25],
        "borrow_collateral_percent_range": [10, 30], # Percentage of collateral value to borrow
        "repay_debt_percent_range": [20, 50], # Percentage of debt to repay
        "withdraw_supply_percent_range": [20, 50] # Percentage of supply to withdraw
    }
}
"""
```

## 5. Error Handling

*   **Sub-Function Errors:** Errors from sub-functions (e.g., `ScrollSwapError`, `InsufficientBalanceError` from [`airdrops/src/airdrops/protocols/scroll/exceptions.py`](../../airdrops/src/airdrops/protocols/scroll/exceptions.py:1)) will be caught.
*   **Sequence Control:** `config['random_activity_scroll']['stop_on_failure']` (bool, default: `True`) determines if the sequence halts on the first error. If `False`, errors are logged, and the sequence continues.
*   **Overall Function Error:**
    *   A new custom exception `ScrollRandomActivityError(ScrollBridgeError)` will be defined in [`airdrops/src/airdrops/protocols/scroll/exceptions.py`](../../airdrops/src/airdrops/protocols/scroll/exceptions.py:1). This can be raised for orchestration-specific errors (e.g., invalid config, parameter generation failure).
    ```python
    # To be added to airdrops/src/airdrops/protocols/scroll/exceptions.py
    class ScrollRandomActivityError(ScrollBridgeError):
        """Raised for errors specific to the perform_random_activity_scroll orchestration."""
        pass
    ```
*   **Logging:** Detailed logs for selected actions, parameters, outcomes (tx_hash or error), and a final summary.

## 6. Helper Functions (Conceptual)

Internal helpers will be needed:

*   `_select_random_scroll_action(config: Dict[str, Any]) -> str`: Selects action by weight.
*   `_generate_params_for_scroll_action(action_name: str, web3_l1: Web3, web3_scroll: Web3, private_key: str, user_address: str, activity_config: Dict[str, Any], scroll_token_config: Dict[str,Any]) -> Dict[str, Any]`: Generates parameters for the chosen action, fetching on-chain state as needed. `scroll_token_config` would be the general token address/decimal mapping.
*   `_get_wallet_balances(web3_instance: Web3, address: str, token_symbols: List[str], token_configs: Dict[str, Any]) -> Dict[str, int]`: Fetches ETH/ERC20 balances.
*   `_get_layerbank_positions(...)`: Fetches LayerBank supply/borrow/collateral state.
*   `_get_syncswap_lp_balance(...)`: Fetches SyncSwap LP token balance for a pair.

## 7. Return Value

Tuple: `(bool, Union[List[str], str])`.
*   `bool`: Overall success indicator based on `stop_on_failure` policy and absence of critical setup errors.
*   `Union[List[str], str]`: List of successful transaction hashes, or an error message for catastrophic failure.

## 8. Dependencies

*   Python `random` module.
*   Existing functions from `airdrops.protocols.scroll.scroll`.
*   Existing exceptions from `airdrops.protocols.scroll.exceptions`.
*   `web3.py`.

## 9. Open Questions / Future Enhancements

*   **Complex State Management:** V2 could track outputs of one action as inputs for subsequent ones.
*   **Predefined Sequences:** Allow users to define fixed sequences with parameter linking.
*   **Gas Cost Estimation:** Pre-sequence gas cost estimation.