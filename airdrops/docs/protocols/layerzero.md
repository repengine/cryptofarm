# LayerZero / Stargate Protocol Module

This document outlines the design, configuration, and usage of the LayerZero / Stargate protocol module within the Airdrops Automation project.

## 1. Overview

The LayerZero module facilitates cross-chain interactions, primarily focusing on bridging assets using Stargate Finance, which is built on top of LayerZero's messaging protocol. The primary goal is to enable automated, reliable, and configurable asset transfers between supported EVM-compatible chains.

**Key Functionalities:**
- `bridge()`: Perform a specific asset bridge between two supported chains using Stargate.
- `perform_random_bridge()`: Execute a randomized bridging action based on a predefined strategy and configuration, utilizing the `bridge()` function.

**Interaction Strategy:**
The module employs a **Hybrid Contract+API Approach**:
*   **Direct Smart Contract Interaction:** `web3.py` is used for all on-chain actions, including:
    *   Interacting with the Stargate Router contract on the source chain for initiating bridges (`swap` function).
    *   Interacting with ERC20 token contracts for approvals (`approve`, `allowance`) and balance checks (`balanceOf`).
    *   Estimating LayerZero fees via the Stargate Router (`quoteLayerZeroFee` function).
*   **Stargate REST API (Optional/Fallback):** While primary fee estimation is via contract, Stargate's public APIs (e.g., for quotes, pool information, or transaction status) can serve as a supplementary data source or for advanced routing decisions if needed. Direct contract interaction is preferred for core operations.

## 2. Configuration

The LayerZero/Stargate module relies on a comprehensive configuration dictionary, typically loaded from a central configuration file (e.g., `config.toml`) or environment variables.

```python
# Example Structure (conceptual, actual format might be TOML/YAML)
CONFIG = {
    "layerzero": {
        "chains": {
            1: { # Ethereum
                "name": "ethereum",
                "rpc_url": "YOUR_ETHEREUM_RPC_URL",
                "layerzero_chain_id": 101,
                "stargate_router_address": "0x8731d54E9D02c286767d56ac03e8037C07e01e98",
                "explorer_url": "https://etherscan.io/tx/"
            },
            42161: { # Arbitrum
                "name": "arbitrum",
                "rpc_url": "YOUR_ARBITRUM_RPC_URL",
                "layerzero_chain_id": 110,
                "stargate_router_address": "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614",
                "explorer_url": "https://arbiscan.io/tx/"
            },
            10: { # Optimism
                "name": "optimism",
                "rpc_url": "YOUR_OPTIMISM_RPC_URL",
                "layerzero_chain_id": 111,
                "stargate_router_address": "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b",
                "explorer_url": "https://optimistic.etherscan.io/tx/"
            },
            137: { # Polygon
                "name": "polygon",
                "rpc_url": "YOUR_POLYGON_RPC_URL",
                "layerzero_chain_id": 109,
                "stargate_router_address": "0x45A01E4e04F14f7A4a6702c74187c5F6222033cd",
                "explorer_url": "https://polygonscan.com/tx/"
            },
            8453: { # Base
                "name": "base",
                "rpc_url": "YOUR_BASE_RPC_URL",
                "layerzero_chain_id": 184,
                "stargate_router_address": "0x41e4145795f82421555385997115550C52196009", # Note: Verify official Base router
                "explorer_url": "https://basescan.org/tx/"
            }
            # Add other supported chains (e.g., BSC, Avalanche)
        },
        "tokens": {
            "USDC": {
                1: {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6, "stargate_pool_id": 1},
                42161: {"address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6, "stargate_pool_id": 1},
                10: {"address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "decimals": 6, "stargate_pool_id": 1},
                137: {"address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "decimals": 6, "stargate_pool_id": 1},
                8453: {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6, "stargate_pool_id": 1}
            },
            "USDT": {
                1: {"address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6, "stargate_pool_id": 2},
                42161: {"address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "decimals": 6, "stargate_pool_id": 2},
                # Add USDT for other chains if supported by Stargate
            },
            "ETH": { # Native ETH (uses WETH pool on Stargate, but handled as native for tx)
                1: {"address": "NATIVE", "decimals": 18, "stargate_pool_id": 13}, # Stargate uses WETH pool for ETH
                42161: {"address": "NATIVE", "decimals": 18, "stargate_pool_id": 13},
                # Add ETH for other chains
            }
            # Add other supported tokens (e.g., DAI)
        },
        "perform_random_bridge_settings": {
            "enabled_chains": ["ethereum", "arbitrum", "optimism", "polygon", "base"], # Names from config.chains
            "enabled_tokens": ["USDC", "USDT", "ETH"], # Symbols from config.tokens
            "chain_weights": {"ethereum": 10, "arbitrum": 20, "optimism": 20, "polygon": 20, "base": 20},
            "token_weights": {"USDC": 50, "USDT": 30, "ETH": 20},
            "amount_usd_min": 10.0,
            "amount_usd_max": 100.0,
            "slippage_bps_min": 30, # 0.3%
            "slippage_bps_max": 100, # 1.0%
            "min_source_balance_usd_threshold": 20.0 # Min USD value of token on source chain to consider bridging
        },
        "default_slippage_bps": 50, # 0.5%
        "gas_settings": {
            "max_gas_price_gwei": { # Optional: chain-specific max gas price
                "ethereum": 100,
                "arbitrum": 1
            },
            "transaction_timeout_seconds": 300,
            "gas_limit_multiplier": 1.2 # Multiplier for web3.eth.estimate_gas
        },
        "retry_settings": {
            "max_retries": 3,
            "delay_seconds": 10
        }
    }
}
```

**Configuration Parameters:**

*   **`chains.<chain_id>`**:
    *   `name`: (str) Human-readable chain name (e.g., "ethereum").
    *   `rpc_url`: (str) RPC URL for connecting to the chain. **User must provide this.**
    *   `layerzero_chain_id`: (int) LayerZero's unique identifier for this chain.
    *   `stargate_router_address`: (str) Deployed Stargate Router contract address on this chain.
    *   `explorer_url`: (str, optional) Base URL for the chain's transaction explorer.
*   **`tokens.<SYMBOL>.<chain_id>`**:
    *   `address`: (str) Token contract address on the chain. Use "NATIVE" for the native chain asset (e.g., ETH).
    *   `decimals`: (int) Token decimals.
    *   `stargate_pool_id`: (int) Stargate's internal pool ID for this token on this chain.
*   **`perform_random_bridge_settings`**:
    *   `enabled_chains`: (List[str]) Chain names eligible for random bridging.
    *   `enabled_tokens`: (List[str]) Token symbols eligible for random bridging.
    *   `chain_weights`: (Dict[str, int]) Weights for selecting source/destination chains.
    *   `token_weights`: (Dict[str, int]) Weights for selecting tokens.
    *   `amount_usd_min`, `amount_usd_max`: (float) Range for random bridge amount in USD. (Requires price oracle).
    *   `slippage_bps_min`, `slippage_bps_max`: (int) Range for random slippage in basis points.
    *   `min_source_balance_usd_threshold`: (float) Minimum USD equivalent balance of a token on the source chain required to consider it for a random bridge.
*   **`default_slippage_bps`**: (int) Default slippage (in basis points) if not specified in `bridge()` call.
*   **`gas_settings`**: (optional)
    *   `max_gas_price_gwei`: (Dict[str, int], optional) Chain-specific max gas price in Gwei.
    *   `transaction_timeout_seconds`: (int) Timeout for waiting for transaction receipts.
    *   `gas_limit_multiplier`: (float) Multiplier applied to `web3.eth.estimate_gas` result.
*   **`retry_settings`**:
    *   `max_retries`: (int) Maximum number of retries for failed RPC calls or transactions.
    *   `delay_seconds`: (int) Base delay between retries.

## 3. Core Functions

### 3.1. `bridge()`

Performs a specific asset bridge from a source chain to a destination chain via Stargate.

**Signature:**
```python
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

def bridge(
    source_chain_id: int,
    destination_chain_id: int,
    source_token_symbol: str, # e.g., "USDC", "ETH"
    amount_in_source_token_units: Decimal, # Amount of source_token_symbol to bridge
    user_address: str, # User's wallet address
    slippage_bps: int, # Slippage tolerance in basis points (e.g., 50 for 0.5%)
    config: Dict[str, Any], # Global LayerZero configuration
    private_key: str # User's private key for signing transactions
) -> Tuple[bool, Optional[str]]: # (success, source_tx_hash_or_error_message)
```

**Parameters:**
*   `source_chain_id`: (int) Network ID of the source chain (e.g., 1 for Ethereum).
*   `destination_chain_id`: (int) Network ID of the destination chain.
*   `source_token_symbol`: (str) Symbol of the token to bridge (e.g., "USDC", "ETH"). Must be defined in `config.tokens`.
*   `amount_in_source_token_units`: (`Decimal`) The amount of the source token to bridge, in its standard units (e.g., 100.5 for 100.5 USDC).
*   `user_address`: (str) The EOA initiating the bridge and typically receiving funds on the destination.
*   `slippage_bps`: (int) Maximum acceptable slippage in basis points (1 bps = 0.01%).
*   `config`: (Dict) The LayerZero module configuration.
*   `private_key`: (str) Private key for the `user_address` to sign transactions on the source chain.

**Return Value:**
*   `Tuple[bool, Optional[str]]`: A tuple where:
    *   The first element is `True` if the bridge transaction was successfully submitted on the source chain, `False` otherwise.
    *   The second element is the transaction hash (hex string) on the source chain if successful, or an error message string if failed.
    *   *Note: Successful return only indicates source chain submission. Destination chain confirmation is asynchronous.*

**High-Level Internal Logic:**
1.  **Load Configuration & Validate Inputs:**
    *   Retrieve chain and token details from `config` using IDs and symbols.
    *   Validate that chains and tokens are supported and configured.
    *   Validate `amount_in_source_token_units` and `slippage_bps`.
2.  **Initialize Web3 for Source Chain:**
    *   Create a `Web3` instance using `config.chains[source_chain_id].rpc_url`.
3.  **Prepare Token Details:**
    *   Get source token address, decimals, and Stargate pool ID from `config.tokens[source_token_symbol][source_chain_id]`.
    *   Get destination token Stargate pool ID from `config.tokens[source_token_symbol][destination_chain_id]`. (Assumes bridging the same token type).
    *   Convert `amount_in_source_token_units` to wei using source token decimals.
4.  **Token Approval (if not native token):**
    *   If `source_token_symbol` is not "ETH" (or other native configured symbol):
        *   Get an ERC20 contract instance for the source token.
        *   Check current `allowance(user_address, stargate_router_address)`.
        *   If `allowance < amount_wei`, build, sign, and send an `approve(stargate_router_address, amount_wei)` transaction. Wait for its receipt. Handle approval failure.
5.  **Estimate LayerZero Fees:**
    *   Get Stargate Router contract instance for the source chain (`config.chains[source_chain_id].stargate_router_address`).
    *   Call `router.functions.quoteLayerZeroFee(destination_lz_chain_id, 1, user_address_bytes, b'', (0, 0, "0x0000000000000000000000000000000000000001"))`.
        *   `destination_lz_chain_id`: from `config.chains[destination_chain_id].layerzero_chain_id`.
        *   `function_type = 1` (for Stargate `swap`).
        *   The `lzTxParams` (`(dstGasForCall, dstNativeAmount, dstNativeAddr)`) are typically minimal for standard token sends. `dstNativeAddr` can be a burn address if no specific gas drop-off is needed on destination for the user.
    *   This call returns `(nativeFee, zroFee)`. `nativeFee` is paid as `msg.value` in the `swap` call.
6.  **Construct `swap` Transaction Parameters:**
    *   `_dstChainId`: `config.chains[destination_chain_id].layerzero_chain_id`.
    *   `_srcPoolId`: Source token's Stargate pool ID.
    *   `_dstPoolId`: Destination token's Stargate pool ID.
    *   `_refundAddress`: `user_address`.
    *   `_amountLD`: `amount_wei` (amount in local decimals of the token).
    *   `_minAmountLD`: `amount_wei * (10000 - slippage_bps) // 10000`.
    *   `_lzTxParams`: As determined for fee quoting, or refined. `(dst_gas_for_call_estimate, dst_native_amount_for_gas, user_address_bytes)`.
    *   `_to`: `user_address` (bytes format).
    *   `_payload`: `b''` (empty bytes for a standard Stargate token bridge).
7.  **Send `swap` Transaction:**
    *   Build the transaction: `router.functions.swap(...).build_transaction({...})`.
        *   Set `'from': user_address`.
        *   Set `'value': nativeFee` (from `quoteLayerZeroFee`).
        *   Set appropriate `'gas'` and `'gasPrice'` (or `maxFeePerGas`, `maxPriorityFeePerGas` for EIP-1559 chains). Use `config.gas_settings`.
    *   Sign the transaction with `private_key`.
    *   Send the raw transaction using `w3.eth.send_raw_transaction()`.
    *   Wait for the transaction receipt using `w3.eth.wait_for_transaction_receipt()`.
8.  **Return Result:**
    *   If receipt status is 1 (success), return `(True, tx_hash.hex())`.
    *   Otherwise, return `(False, "Transaction failed on source chain")` or more specific error.

### 3.2. `perform_random_bridge()`

Executes a randomized bridging action by selecting chains, tokens, and amounts based on the provided configuration and then calling the `bridge()` function.

**Signature:**
```python
def perform_random_bridge(
    user_address: str, # User's wallet address
    config: Dict[str, Any], # Global LayerZero configuration
    private_key: str # User's private key for signing transactions
) -> Tuple[bool, str]: # (success, message_string_with_action_taken_and_tx_hash_or_error)
```

**Parameters:**
*   `user_address`: (str) The EOA initiating the bridge.
*   `config`: (Dict) The LayerZero module configuration, including `perform_random_bridge_settings`.
*   `private_key`: (str) Private key for the `user_address`.

**Return Value:**
*   `Tuple[bool, str]`: A tuple where:
    *   The first element is `True` if a bridge attempt was successfully initiated, `False` otherwise.
    *   The second element is a descriptive message including the action taken (e.g., "Bridged 10.5 USDC from Ethereum to Arbitrum, tx: 0xabc...") or an error message.

**High-Level Internal Logic:**
1.  **Load Random Bridge Settings:**
    *   Extract `perform_random_bridge_settings` from `config`.
2.  **Select Random Parameters:**
    *   **Chains:**
        *   Select `source_chain_name` from `settings.enabled_chains` using `settings.chain_weights`.
        *   Select `destination_chain_name` from `settings.enabled_chains` (must be different from source) using `settings.chain_weights`.
        *   Convert names to `source_chain_id` and `destination_chain_id` by looking up in `config.chains`.
    *   **Token:**
        *   Select `token_symbol` from `settings.enabled_tokens` using `settings.token_weights`.
        *   Verify the selected token is configured for both chosen chains in `config.tokens`. If not, re-select or skip.
    *   **Amount:**
        *   Requires fetching the user's balance of the `token_symbol` on the `source_chain_id`.
        *   Requires a price oracle to convert `settings.amount_usd_min/max` to token units, or to check `settings.min_source_balance_usd_threshold`.
        *   Alternatively, bridge a random percentage of the available balance, ensuring it's above protocol minimums and within reasonable bounds.
        *   For simplicity if no oracle: use a small, fixed token amount range if balances are sufficient.
        *   Let `amount_to_bridge` be the determined `Decimal` value.
    *   **Slippage:**
        *   Select random `slippage_bps` from `settings.slippage_bps_min` to `settings.slippage_bps_max`.
3.  **Pre-Bridge Checks (Optional but Recommended):**
    *   Check if `user_address` has sufficient balance of `token_symbol` on `source_chain_id` for `amount_to_bridge`.
    *   Check if `user_address` has sufficient native gas token balance on `source_chain_id`.
4.  **Call `bridge()`:**
    *   Invoke `bridge(source_chain_id, destination_chain_id, token_symbol, amount_to_bridge, user_address, slippage_bps, config, private_key)`.
5.  **Log and Return Result:**
    *   Construct a descriptive message based on the outcome of the `bridge()` call.
    *   Return `(success_status_from_bridge, message)`.

## 4. Technical Details & Dependencies

*   **Smart Contracts Interacted With:**
    *   **Stargate Router:** (Addresses per chain in `config`)
        *   `swap(...) payable`: Initiates the cross-chain bridge.
        *   `quoteLayerZeroFee(...)`: Estimates the LayerZero messaging fee.
        *   Other view functions for pool info if needed (e.g., `poolIdToLpToken`, `getChainPath`).
    *   **ERC20 Token Contracts:** (Addresses per chain/token in `config`)
        *   `approve(spender, amount)`: To allow Stargate Router to spend tokens.
        *   `allowance(owner, spender)`: To check current approval.
        *   `balanceOf(account)`: To check user's token balance.
        *   `decimals()`: To get token decimal precision.
*   **LayerZero Concepts:**
    *   **LayerZero Chain ID:** A unique ID LayerZero assigns to each supported blockchain (distinct from network/chain ID). Used in Stargate Router calls.
    *   **LayerZero Endpoint:** The LayerZero contract on each chain responsible for message sending/receiving (interaction is abstracted by Stargate).
*   **Stargate Finance Concepts:**
    *   **Pool ID:** Stargate's identifier for a specific token's liquidity pool on a chain.
    *   **`sgReceive`:** The function on the Stargate Router that LayerZero calls on the destination chain to complete the bridge and credit funds.
*   **Relevant ABIs:**
    *   Standard ERC20 ABI.
    *   Stargate Router ABI (obtainable from block explorers of deployed router contracts).
*   **APIs (External):**
    *   Stargate Finance might have public REST APIs for quotes, supported chains/tokens, or transaction status. Example (verify current validity): `https://stargate.finance/api/v1/quote` or `https://stargate.finance/api/v2/...`. These are optional if contract calls suffice.
*   **Python Dependencies:**
    *   `web3.py>=6.0.0`: For EVM interactions.
    *   `requests`: If using any external REST APIs.
    *   `python-dotenv`: For managing environment variables (like private keys, RPC URLs).
    *   `eth-abi`: Often a sub-dependency of `web3.py`, used for encoding/decoding.

## 5. Error Handling & Logging

*   **Input Validation:** Functions should validate inputs (e.g., chain IDs exist in config, token symbols valid, amounts positive).
*   **RPC/Network Errors:**
    *   Implement retries with exponential backoff for `web3.py` calls that might fail due to temporary network issues (e.g., `ConnectionError`, `Timeout`). Use `config.retry_settings`.
*   **Transaction Errors:**
    *   Catch exceptions from `w3.eth.send_raw_transaction` or `w3.eth.wait_for_transaction_receipt`.
    *   `ValueError` from `web3.py` can indicate issues like insufficient funds for gas, transaction revert (e.g., slippage too high, pool depleted).
    *   Log detailed error messages, including transaction parameters if possible.
*   **Token Approval Failures:** Handle errors during the `approve` transaction.
*   **Slippage Errors:** If a transaction reverts due to not meeting `_minAmountLD`, this should be caught and reported.
*   **LayerZero Message Delivery Issues:**
    *   The `bridge` function primarily confirms source chain transaction success.
    *   Destination confirmation is asynchronous. If the LayerZero message gets stuck, it's outside the direct control of this function.
    *   Logging the source transaction hash and any LayerZero-specific identifiers (if emitted in events like `Send`) is crucial for manual tracking or separate monitoring.
*   **Logging Strategy:**
    *   Use Python's `logging` module.
    *   Log key events: function calls with parameters, successful transactions with hashes, errors encountered with tracebacks.
    *   Include timestamps and relevant context (e.g., chain IDs, token symbols).
    *   Consider different log levels (INFO for successful operations, WARNING for recoverable issues, ERROR for failures).

## 6. Testing Strategy (Architectural Perspective)

A robust testing strategy is crucial for reliability.
*   **Unit Tests:**
    *   Mock `Web3` provider interactions:
        *   Mock contract read calls (e.g., `balanceOf`, `allowance`, `quoteLayerZeroFee`).
        *   Mock contract write calls (`approve`, `swap`) to simulate transaction building, signing, and sending, returning mock receipts.
    *   Mock any external API calls (e.g., Stargate REST API, price oracles).
    *   **`bridge()` Test Cases:**
        *   Successful bridge for an ERC20 token (including approval step).
        *   Successful bridge for a native token (e.g., ETH, skipping approval).
        *   Failure due to insufficient token balance.
        *   Failure due to insufficient native gas balance.
        *   Failure due to RPC error during fee quoting or transaction submission (test retry logic).
        *   Failure due to transaction revert on source chain (e.g., simulated high slippage).
        *   Correct calculation of `_minAmountLD`.
        *   Correct `msg.value` for `nativeFee`.
    *   **`perform_random_bridge()` Test Cases:**
        *   Correct random selection of chains, token, amount, and slippage based on config and weights.
        *   Ensuring selected token is valid on both selected chains.
        *   Correct invocation of the `bridge()` function with generated parameters.
        *   Handling of scenarios where no valid random bridge can be constructed (e.g., insufficient balance for all options, misconfiguration).
*   **Integration Tests (More Complex):**
    *   Could involve forked mainnet testing (e.g., using Hardhat or Anvil) to interact with real Stargate contracts without spending real funds.
    *   Testnet interactions if feasible, though Stargate liquidity and support might vary.
*   **Configuration Validation:** Test that the functions handle missing or malformed configuration entries gracefully.