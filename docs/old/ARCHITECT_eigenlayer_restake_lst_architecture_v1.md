## Plan v1: EigenLayer `restake_lst` Function Architecture

### Objective
Design the architecture for the `restake_lst` function, enabling the deposit of stETH and rETH Liquid Staking Tokens (LSTs) into their respective EigenLayer Strategy contracts.

### 1. Function Signature

```python
from typing import Tuple, Optional
from web3 import Web3

def restake_lst(
    web3_eth: Web3,
    private_key: str,
    lst_symbol: str,  # "stETH" or "rETH"
    amount: int  # Amount in Wei or smallest unit of the LST
) -> Tuple[bool, Optional[str]]:
    """
    Deposits the specified LST (stETH or rETH) into its corresponding EigenLayer Strategy contract.

    Args:
        web3_eth: Web3 instance connected to Ethereum Mainnet.
        private_key: The private key of the user's wallet.
        lst_symbol: The symbol of the LST to deposit ("stETH" or "rETH").
        amount: The amount of LST to deposit, in its smallest unit (e.g., Wei for stETH).

    Returns:
        A tuple containing:
        - bool: True if the deposit transaction was successfully broadcast, False otherwise.
        - Optional[str]: The transaction hash if successful, or an error message string if not.
    """
    pass
```

### 2. Core Logic

The `restake_lst` function will perform the following steps:

1.  **Derive User Address:** Obtain the user's Ethereum address from the `private_key`.
2.  **Strategy Selection:**
    *   Based on the `lst_symbol` parameter ("stETH" or "rETH"), determine the correct EigenLayer LST Strategy contract address and the LST token contract address. This will likely involve a helper function (e.g., `_get_eigenlayer_lst_strategy_details`).
3.  **Approval:**
    *   Interact with the LST's ERC20 contract (`stETH_token_address` or `rETH_token_address`).
    *   Call the `approve(address spender, uint256 amount)` method on the LST contract.
    *   The `spender` will be the selected EigenLayer LST Strategy contract address.
    *   The `amount` will be the `amount` parameter passed to `restake_lst`.
    *   Wait for the approval transaction to be mined.
4.  **Deposit:**
    *   Interact with the selected EigenLayer LST Strategy contract (`stETH_strategy_address` or `rETH_strategy_address`).
    *   Call the `deposit(uint256 _amount, address _depositor)` method (or verified equivalent) on the Strategy contract.
        *   `_amount`: The `amount` parameter.
        *   `_depositor`: The user's Ethereum address.
    *   Wait for the deposit transaction to be mined.
5.  **Return Transaction Hash:** If the deposit is successful, return the transaction hash.

#### Caps and Limits Consideration:

*   EigenLayer strategies have deposit caps (e.g., `maxTotalShares`, `totalShares`).
*   **V1 Approach:** The initial version might proceed with the deposit and let the transaction fail if a cap is reached. The error handling should catch this.
*   **Future Enhancement (V2):** Implement a pre-deposit check using a helper function (e.g., `_check_eigenlayer_deposit_cap`). This function would query the relevant view function on the Strategy contract (e.g., `maxTotalShares()`, `totalShares()`) or potentially the `StrategyManager` contract (`strategyAndUnderlyingTokens(strategy).totalShares` and `strategyAndUnderlyingTokens(strategy).strategy.totalSharesCap`). If the deposit would exceed the cap, the function could raise a `DepositCapReachedError` or return an appropriate status.

### 3. Contract Interaction

#### 3.1 LST Contracts (Standard ERC20)

*   **stETH Token Address:** `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84`
*   **rETH Token Address:** `0xae78736Cd615f374D3085123A210448E74Fc6393`
*   **Key Function:**
    *   `approve(address spender, uint256 amount) returns (bool)`
*   **ABI:** Standard ERC20 ABI.

#### 3.2 EigenLayer Strategy Contracts (StrategyBaseTVLLimits)

*   **stETH Strategy Address:** `0x93c4b944D05dfe6df72a2751b1A0541D03217475`
*   **rETH Strategy Address:** `0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3`
*   **Key Functions:**
    *   `deposit(uint256 _amount, address _depositor) returns (uint256 shares)` (Signature to be verified from actual ABI. The `_depositor` parameter is crucial.)
    *   **View Functions for Caps (Examples, verify from ABI):**
        *   `totalShares() returns (uint256)`
        *   `maxTotalShares() returns (uint256)` (or similar like `strategyCap()`, `MAX_TOTAL_SHARES`)
        *   Alternatively, `StrategyManager.strategyAndUnderlyingTokens(strategy_address)` might provide cap info.
*   **ABI:** Specific ABIs for these Strategy contracts need to be sourced (e.g., from Etherscan) and stored.

#### 3.3 EigenLayer StrategyManager (Optional for this function, but relevant for cap checks)

*   **Address:** `0x858646372CC42E1A627fcE94aa7A7033e7CF075A`
*   **Potential View Function for Caps:**
    *   `strategyAndUnderlyingTokens(IStrategy strategy) returns (IERC20[] memory underlyingTokens, uint256[] memory totalShares, uint256[] memory totalStrategyShares)` (This is a guess, verify exact signature and return structure from ABI).
    *   The strategy itself might have a `totalSharesCap()` or similar.

### 4. Configuration Management

1.  **Contract Addresses:**
    *   LST Token Addresses (stETH, rETH).
    *   EigenLayer LST Strategy Addresses (stETH Strategy, rETH Strategy).
    *   EigenLayer StrategyManager Address.
    *   These will be stored as constants, likely in a new configuration file: `airdrops/src/airdrops/protocols/eigenlayer/eigenlayer_config.py`.
    ```python
    # Example eigenlayer_config.py
    STETH_TOKEN_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
    RETH_TOKEN_ADDRESS = "0xae78736Cd615f374D3085123A210448E74Fc6393"

    STETH_STRATEGY_ADDRESS = "0x93c4b944D05dfe6df72a2751b1A0541D03217475"
    RETH_STRATEGY_ADDRESS = "0x1BeE69b7dFFfA4E2d53C2A2Df135C34A2B5202c3"

    STRATEGY_MANAGER_ADDRESS = "0x858646372CC42E1A627fcE94aa7A7033e7CF075A"

    # Mapping for easy lookup
    LST_ASSET_DETAILS = {
        "stETH": {
            "token_address": STETH_TOKEN_ADDRESS,
            "strategy_address": STETH_STRATEGY_ADDRESS,
            "token_abi_file": "ERC20.json", # Standard ERC20 ABI
            "strategy_abi_file": "StrategyBaseTVLLimits_stETH.json" # Specific strategy ABI
        },
        "rETH": {
            "token_address": RETH_TOKEN_ADDRESS,
            "strategy_address": RETH_STRATEGY_ADDRESS,
            "token_abi_file": "ERC20.json", # Standard ERC20 ABI
            "strategy_abi_file": "StrategyBaseTVLLimits_rETH.json" # Specific strategy ABI
        }
    }
    ```

2.  **ABIs:**
    *   Standard ERC20 ABI (can be a single shared file).
    *   Specific ABIs for each EigenLayer LST Strategy contract.
    *   ABI for StrategyManager (if used for cap checks).
    *   ABIs will be stored as JSON files in a new directory: `airdrops/src/airdrops/protocols/eigenlayer/abi/`.
        *   `ERC20.json`
        *   `StrategyBaseTVLLimits_stETH.json` (or a more generic name if ABI is identical for both strategies, just ensure it's the correct one for `StrategyBaseTVLLimits` type contracts)
        *   `StrategyBaseTVLLimits_rETH.json`
        *   `StrategyManager.json` (if needed)

### 5. Error Handling

Common error scenarios and proposed custom exceptions:

*   **Invalid LST Symbol:** If `lst_symbol` is not "stETH" or "rETH".
    *   Custom Exception: `UnsupportedLSTError(Exception)`
*   **Insufficient LST Balance:** User does not have enough LST to cover the `amount` and gas fees.
    *   Standard Web3.py exceptions or a custom `EigenLayerRestakeError`.
*   **Approval Failure:** The `approve` transaction fails or is rejected.
    *   Custom Exception: `EigenLayerRestakeError("LST approval failed")`
*   **Deposit Failure (General):** The `deposit` transaction fails for reasons other than cap.
    *   Custom Exception: `EigenLayerRestakeError("LST deposit failed")`
*   **Deposit Cap Reached:** The deposit cannot proceed because the strategy's cap is met.
    *   Custom Exception: `DepositCapReachedError(EigenLayerRestakeError)`
*   **Transaction Timeout/RPC Issues:**
    *   Handled by underlying Web3.py transaction sending logic, potentially wrapped in `EigenLayerRestakeError`.

A new file for EigenLayer specific exceptions will be created: `airdrops/src/airdrops/protocols/eigenlayer/exceptions.py`.

```python
# Example airdrops/src/airdrops/protocols/eigenlayer/exceptions.py
class EigenLayerRestakeError(Exception):
    """Base exception for EigenLayer restaking errors."""
    pass

class UnsupportedLSTError(EigenLayerRestakeError):
    """Raised when an unsupported LST symbol is provided."""
    pass

class DepositCapReachedError(EigenLayerRestakeError):
    """Raised when a deposit attempt exceeds the strategy's cap."""
    pass

# Other specific errors can be added as needed.
```

### 6. Helper Functions (Conceptual)

1.  **`_get_eigenlayer_lst_strategy_details(lst_symbol: str) -> dict`:**
    *   **Goal:** Takes an `lst_symbol` ("stETH" or "rETH").
    *   **Returns:** A dictionary containing the LST token address, LST strategy contract address, and paths to their ABI files (fetched from `eigenlayer_config.LST_ASSET_DETAILS`).
    *   **Raises:** `UnsupportedLSTError` if the symbol is invalid.

2.  **`_check_eigenlayer_deposit_cap(strategy_contract: web3.contract.Contract, amount_to_deposit: int) -> bool` (For V2):**
    *   **Goal:** Takes an initialized Strategy contract instance and the amount to deposit.
    *   **Logic:**
        *   Queries `totalShares()` and `maxTotalShares()` (or equivalent) from the `strategy_contract`.
        *   (Note: `deposit` takes token amount, `totalShares` is in shares. A conversion or direct cap check on token amount might be needed if the strategy provides it. The `deposit` function returns shares, so we might need to estimate shares for the given amount if checking against `maxTotalShares`.)
        *   Alternatively, if the strategy has a view function like `getDepositLimit()` or `availableToDeposit()`, that would be simpler.
    *   **Returns:** `True` if the deposit is within limits, `False` otherwise.
    *   **Raises:** `EigenLayerRestakeError` if cap check fails or contract calls revert.

3.  **`_build_and_send_transaction(web3_eth: Web3, transaction: dict, private_key: str) -> Tuple[bool, Optional[str]]`:**
    *   A generic helper (could be shared across modules) to sign and send a transaction, wait for receipt, and handle common errors.
    *   Returns `(success_status, transaction_hash_or_error_message)`.

### Task Blocks
| ID     | Description                                                                 | Owner Mode | Deliverable                                                                                                | Acceptance Test                                                                                                                               |
|--------|-----------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| TB-EL-RL-1 | Define `restake_lst` function signature and core logic flow.                | Architect  | Section in Arch. Doc.                                                                                      | Signature matches requirements; logic covers selection, approval, deposit.                                                                    |
| TB-EL-RL-2 | Detail LST and EigenLayer Strategy contract interactions (addresses, ABIs). | Architect  | Section in Arch. Doc.                                                                                      | Correct contract addresses listed; ABI sourcing plan clear; key functions identified.                                                         |
| TB-EL-RL-3 | Design configuration management for addresses and ABIs.                     | Architect  | Section in Arch. Doc.; Example `eigenlayer_config.py`; Plan for `abi/` dir.                                | Clear plan for storing constants and ABI files; new file/dir structure defined.                                                               |
| TB-EL-RL-4 | Outline error handling strategy and define custom exceptions.               | Architect  | Section in Arch. Doc.; Example `exceptions.py`.                                                            | Common errors identified; custom exceptions defined; new exceptions file planned.                                                             |
| TB-EL-RL-5 | Conceptualize helper functions.                                             | Architect  | Section in Arch. Doc.                                                                                      | Logical helper functions proposed to modularize code.                                                                                         |
| TB-EL-RL-6 | Create `docs/ARCHITECT_eigenlayer_restake_lst_architecture_v1.md` file.     | Architect  | `write_to_file` tool call with full markdown content.                                                      | File created successfully with the defined architecture.                                                                                      |
| TB-EL-RL-7 | Update `docs/planning/airdrops_automation_plan.md` progress log.            | Architect  | `insert_content` tool call with new log entry.                                                             | Planning document updated with a timestamped entry referencing the new architecture doc.                                                        |

### Flow Diagram
```mermaid
graph TD
    A[Start restake_lst(web3, pk, lst_symbol, amount)] --> B{Validate lst_symbol};
    B -- Valid --> C[Get LST & Strategy Details (address, ABI) via _get_eigenlayer_lst_strategy_details];
    B -- Invalid --> X1[Raise UnsupportedLSTError];
    C --> D[Load LST Contract (ERC20)];
    D --> E[Approve Strategy to spend LST];
    E -- Success --> F[Load Strategy Contract];
    E -- Failure --> X2[Return (False, "Approval Failed")];
    F --> G[Call Strategy.deposit(_amount, _depositor)];
    G -- Success --> H[Return (True, tx_hash)];
    G -- Deposit Cap Reached --> X3[Raise DepositCapReachedError / Return (False, "Cap Reached")];
    G -- Other Failure --> X4[Return (False, "Deposit Failed")];
```

### PCRM Analysis

*   **Pros:**
    *   Provides a clear, reusable function for LST restaking on EigenLayer.
    *   Modular design with helper functions and configuration files.
    *   Addresses key aspects like approvals, deposits, and basic error handling.
*   **Cons:**
    *   V1 does not include proactive deposit cap checks, relying on transaction failure.
    *   ABI sourcing from Etherscan requires manual effort initially.
    *   Complexity of EigenLayer (shares vs. underlying amounts, strategy-specific behaviors) might require further refinement during implementation.
*   **Risks:**
    *   **ABI Mismatches:** ABIs sourced from Etherscan might not perfectly match the exact contract version or could be incomplete for all necessary functions. Mitigation: Thoroughly test ABI interactions on a testnet if possible, or carefully verify against official developer documentation.
    *   **Strategy Contract `deposit` Signature:** The exact signature of `deposit` (parameters, return value) on `StrategyBaseTVLLimits` contracts needs verification. Mitigation: Obtain actual ABIs before coding.
    *   **Gas Costs:** Approval and deposit transactions can be gas-intensive. Mitigation: Inform user, allow gas price configuration.
    *   **EigenLayer Protocol Upgrades:** Contract addresses or functionalities might change. Mitigation: Design for configurability; monitor EigenLayer announcements.
*   **Mitigations:**
    *   Prioritize obtaining official ABIs or using tools that can reliably fetch them.
    *   Implement comprehensive logging for easier debugging.
    *   Start with one LST (e.g., stETH) to iron out the process before adding the second.
    *   Encourage thorough testing by the Code mode.

### Next Step
Reply **Approve** to proceed with creating the architectural document and updating the planning log, or suggest edits.