# zkSync Era `lend_borrow` Function Architecture Plan v1

## 1. Objective

Define the technical architecture for the `lend_borrow` function in the zkSync Era module, enabling interactions with a lending protocol (assumed EraLend) for supplying, withdrawing, borrowing, and repaying assets.

## 2. Lending Protocol Selection & Interaction Strategy

*   **Chosen Protocol:** EraLend (as per project plan). *Verification of official documentation, contract addresses, and ABIs is crucial.*
*   **Interaction:** `web3.py` will be used to interact with EraLend's smart contracts on zkSync Era.
*   **Key Contracts (Placeholders - Verify!):**
    *   **Lending Pool Core/Manager:** `0xEraLendLendingPoolManagerAddress` (This contract would orchestrate market interactions).
    *   **WETH Gateway (if ETH is not native to the lending pool):** `0xEraLendWETHGatewayAddress` (For wrapping/unwrapping ETH during supply/repay).
    *   **Market Contracts (zTokens/eTokens - analogous to Aave's aTokens or Compound's cTokens):** Each supported asset will have a corresponding market token contract (e.g., `zETH`, `zUSDC`). Addresses will need to be identified for each.
        *   `zETH_ADDRESS = "0xEraLend_zETH_Address"`
        *   `zUSDC_ADDRESS = "0xEraLend_zUSDC_Address"`
*   **Key Contract Functions (Conceptual - Verify exact names and signatures!):**
    *   **Supply:**
        *   ERC20: `LendingPoolManager.supply(token_address, amount, on_behalf_of, referral_code)`
        *   ETH: `WETHGateway.depositETH(lending_pool_address, on_behalf_of, referral_code)` (payable)
    *   **Withdraw:**
        *   ERC20 (zToken): `zToken.withdraw(amount, to_address)` or `LendingPoolManager.withdraw(asset_address, amount, to_address)`
        *   ETH (from zETH): `WETHGateway.withdrawETH(lending_pool_address, amount, to_address)` (after withdrawing zETH to user's wallet) or directly if the pool supports it.
    *   **Borrow:**
        *   ERC20: `LendingPoolManager.borrow(asset_address, amount, interest_rate_mode, referral_code, on_behalf_of)`
        *   ETH: `WETHGateway.borrowETH(lending_pool_address, amount, interest_rate_mode, referral_code)`
    *   **Repay:**
        *   ERC20: `LendingPoolManager.repay(asset_address, amount, interest_rate_mode, on_behalf_of)`
        *   ETH: `WETHGateway.repayETH(lending_pool_address, amount, interest_rate_mode, on_behalf_of)` (payable)
    *   **Collateral Management:**
        *   `LendingPoolManager.setUserUseReserveAsCollateral(asset_address, use_as_collateral_bool)`

## 3. Transaction Parameters & Gas Handling

*   **zkSync Era Gas:**
    *   Standard `gasLimit` and `gasPrice` (or EIP-1559 `maxFeePerGas`, `maxPriorityFeePerGas`) will be estimated using `web3.py`'s `estimate_gas`.
    *   `gas_limit_multiplier_l2` from config will be applied.
    *   `l2_gas_per_pubdata_byte_limit` from config should be included in transaction parameters if required by `web3.py` or the RPC node for zkSync Era.
*   **Protocol-Specific Parameters:**
    *   `referral_code (uint16)`: Often `0` if no referral. (Verify if EraLend uses this).
    *   `interest_rate_mode (uint256)`: For borrow/repay, typically `1` for stable, `2` for variable. (Verify EraLend's modes).
    *   `on_behalf_of (address)`: Usually the `user_address`.

## 4. Data Structures & Configuration (`config` additions)

```python
# Additions/modifications to ZKSYNC_CONFIG within airdrops/docs/protocols/zksync.md
# ... existing config ...
        "zksync": {
            # ... existing zksync config ...
            "lending_protocols": {
                "eralend": { # Or other chosen protocol name
                    "lending_pool_manager_address": "0xEraLendLendingPoolManagerAddress_VERIFY",
                    "lending_pool_manager_abi_path": "path/to/eralend_lending_pool_manager_abi.json", # Or ABI string
                    "weth_gateway_address": "0xEraLendWETHGatewayAddress_VERIFY", # If applicable
                    "weth_gateway_abi_path": "path/to/eralend_weth_gateway_abi.json", # If applicable
                    "ztoken_abi_path": "path/to/eralend_ztoken_abi.json", # Generic ABI for zToken interactions like withdraw, if not via manager
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
                        },
                        # Add other supported assets
                    },
                    "referral_code": 0, # Default, verify
                    "default_interest_rate_mode_stable": 1, # Verify
                    "default_interest_rate_mode_variable": 2 # Verify
                }
            },
            # Health factor monitoring settings (optional, for advanced automation)
            "lending_health_factor_limits": {
                "min_safe_hf": 1.5, # Example: minimum health factor before taking action
                "target_hf_after_repay": 2.0 # Example: target HF after a deleveraging action
            }
        }
# ... rest of existing config ...
```

*   **ABIs:** Paths to JSON ABI files or direct ABI strings for:
    *   Lending Pool Manager/Core contract.
    *   WETH Gateway contract (if used).
    *   A generic zToken/eToken ABI (for functions like `balanceOf`, `approve`, potentially `withdraw` if not done via manager).

## 5. Function Logic Flow (`lend_borrow`)

**Common Pre-steps for all actions:**
1.  Input validation (addresses, amount, action, protocol name).
2.  Initialize `w3_l2` (zkSync Era web3 instance) from `config.networks.zksync.rpc_url`.
3.  Load Lending Pool Manager contract using its address and ABI from `config.networks.zksync.lending_protocols[lending_protocol_name]`.
4.  If ETH is involved and a WETH Gateway is used, load WETH Gateway contract.
5.  Identify underlying token address and zToken address from `config...supported_assets`.

**Action: `supply`**
1.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `depositETH` (or equivalent). `msg.value` will be `amount`.
    *   Parameters: `lending_pool_address` (manager), `on_behalf_of` (`user_address`), `referral_code`.
2.  **If `token_address` is ERC20:**
    *   Approve Lending Pool Manager contract to spend `amount` of `token_address` from `user_address`.
        *   Load ERC20 contract for `token_address`.
        *   Call `token.functions.approve(lending_pool_manager_address, amount_wei).build_transaction(...)`.
        *   Sign and send approval. Wait for receipt.
    *   Call Lending Pool Manager's `supply` function.
        *   Parameters: `asset (token_address)`, `amount`, `on_behalf_of (user_address)`, `referral_code`.
3.  Build, sign, send transaction. Wait for receipt.

**Action: `withdraw`**
1.  **If `token_address` is native ETH (meaning withdrawing zETH and converting to ETH):**
    *   Call Lending Pool Manager's `withdraw` function for the zETH equivalent of `amount` ETH.
        *   Parameters: `asset (zETH_address)`, `amount_zTokens_to_withdraw`, `to (user_address)`.
    *   *Alternatively, if WETH Gateway handles this:* Call WETH Gateway's `withdrawETH`.
        *   Parameters: `lending_pool_address`, `amount`, `to (user_address)`. This might internally handle zETH.
2.  **If `token_address` is ERC20 (withdrawing the underlying ERC20 by burning zTokens):**
    *   Call Lending Pool Manager's `withdraw` function.
        *   Parameters: `asset (token_address)`, `amount_to_withdraw_underlying`, `to (user_address)`.
    *   *Alternatively, if withdrawal is by calling `withdraw` on the zToken contract itself:*
        *   Load zToken contract for the asset.
        *   Call `zToken.functions.withdraw(amount_zTokens_to_withdraw, to_address).build_transaction(...)`.
3.  Build, sign, send transaction. Wait for receipt.
    *Note: `amount` parameter needs clarity: is it amount of underlying to withdraw or amount of zTokens? Assume underlying for now.*

**Action: `borrow`**
1.  *(Optional Pre-check):* Call a view function on Lending Pool Manager to check user's borrowing power / health factor. `getUserAccountData(user_address)`.
2.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `borrowETH` (or equivalent on Lending Pool Manager if it handles native ETH directly).
    *   Parameters: `lending_pool_address`, `amount`, `interest_rate_mode`, `referral_code`, `on_behalf_of (user_address)`.
3.  **If `token_address` is ERC20:**
    *   Call Lending Pool Manager's `borrow` function.
        *   Parameters: `asset (token_address)`, `amount`, `interest_rate_mode`, `referral_code`, `on_behalf_of (user_address)`.
4.  Build, sign, send transaction. Wait for receipt.

**Action: `repay`**
1.  **If `token_address` is native ETH:**
    *   Use WETH Gateway's `repayETH` (or equivalent). `msg.value` will be `amount`.
    *   Parameters: `lending_pool_address`, `amount`, `interest_rate_mode`, `on_behalf_of (user_address)`.
2.  **If `token_address` is ERC20:**
    *   Approve Lending Pool Manager contract to spend `amount` (or slightly more to cover accrued interest, e.g., `amount * 1.01` or use `uint(-1)` for max approval if strategy allows) of `token_address` from `user_address`.
    *   Call Lending Pool Manager's `repay` function.
        *   Parameters: `asset (token_address)`, `amount` (or `-1` for full repayment if supported), `interest_rate_mode`, `on_behalf_of (user_address)`.
3.  Build, sign, send transaction. Wait for receipt.

**Action: `set_collateral` (Consider as a separate sub-action or boolean flag in `supply`)**
*   Call `LendingPoolManager.setUserUseReserveAsCollateral(asset_address, use_as_collateral_bool)`.
*   This is typically done after a supply, or can be toggled. For simplicity, it might be best as a separate explicit action or an optional parameter in `supply`.

## 6. Error Handling

*   **Input Validation:** Invalid address, amount <= 0, unsupported action/token/protocol.
*   **RPC Errors:** Node unavailable, rate limiting. (Retry logic).
*   **Transaction Reversions (General):**
    *   Log detailed error from receipt.
    *   `NotEnoughBalance`: Insufficient ETH for gas.
    *   `TransactionFailed`: Generic failure.
*   **Token Approval Failures:** `approve` transaction fails or doesn't confirm.
*   **Lending Protocol Specific Errors (Examples - Verify with EraLend docs!):**
    *   `COLLATERAL_CANNOT_BE_ZERO`: Trying to borrow without collateral.
    *   `HEALTH_FACTOR_LOWER_THAN_LIQUIDATION_THRESHOLD`: Borrowing would make HF too low.
    *   `NO_BORROWING_POWER`: User cannot borrow this amount.
    *   `ASSET_NOT_BORROWABLE`: The specified asset cannot be borrowed.
    *   `ASSET_NOT_LISTED`: Token not supported by the protocol.
    *   `INSUFFICIENT_LIQUIDITY`: Not enough of the asset available in the pool to borrow/withdraw.
    *   `AMOUNT_BIGGER_THAN_SUPPLY`: Trying to withdraw more than supplied.
    *   `AMOUNT_BIGGER_THAN_DEBT`: Trying to repay more than owed (unless full repayment with -1).
    *   `MARKET_PAUSED`: Action on this market is temporarily disabled.
*   **Handling Strategy:**
    *   Catch specific exceptions where possible.
    *   Log all transaction inputs, attempts, and outcomes (success/failure with tx hash or error message).
    *   Return `(False, error_message_string)` on failure.

## 7. Dependencies

*   `web3.py>=6.0.0`

## 8. Open Questions & Verification Points

*   **EraLend Official Documentation:** CRITICAL to find this for accurate contract addresses, ABIs, function names, parameters, and error codes.
*   **Native ETH Handling:** Does EraLend use a WETH Gateway, or are ETH operations integrated directly into the main lending pool contract (e.g., via `msg.value`)?
*   **zToken/eToken Mechanics:** How are these issued/burned? Are interactions direct or always via the manager?
*   **Interest Rate Modes:** Confirm numeric values for stable/variable.
*   **Referral Codes:** Are they used? Default value?
*   **Gas Parameters for zkSync:** Confirm if `gasPerPubdataByteLimit` needs to be explicitly passed in `web3.py` transactions or if the RPC/library handles it.
*   **`amount` parameter in `withdraw`:** Does it refer to the amount of underlying asset or the amount of zTokens?
*   **Repaying full debt:** Is there a special value for `amount` (e.g., `type(uint256).max` or `-1`) to repay the entire outstanding debt for an asset?

This plan provides a foundational architecture. Implementation will require verifying all placeholder information against EraLend's official resources.