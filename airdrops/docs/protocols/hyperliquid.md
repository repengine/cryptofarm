# Hyperliquid Protocol Module

## Overview

This document details the implementation and usage of the Hyperliquid protocol module within the airdrop automation project.

## Configuration

*   **API Endpoint (Mainnet - Exchange):** `https://api.hyperliquid.xyz/exchange`
*   **API Endpoint (Mainnet - Info):** `https://api.hyperliquid.xyz/info`
*   **HLP Mainnet Vault Address:** `0xdfc24b077bc1425ad1dea75bcb6f8158e10df303`
*   **RPC URL (Testnet):** `https://api.hyperliquid-testnet.xyz` (Standard Hyperliquid Testnet API endpoint)
*   **Note:** API calls require standard Hyperliquid request signing. The `hyperliquid-python-sdk` (v0.15.0) handles this.
*   **Arbitrum Chain ID:** `42161`
*   **USDC (Arbitrum) Contract Address:** `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
*   **Hyperliquid Bridge2 (Arbitrum) Contract Address:** `0x2df1c58541F4A5E519B0313f4A4A7A379AC3A78F`
*   Note: These are used by the fully automated `evm_roundtrip` function.
*   **Spot Market Information:** Spot market details, including available trading pairs, asset names, integer asset indices, and precision, are queryable via the `/info` API endpoint (e.g., using the SDK's `Info.meta()` method).
*   **`perform_random_onchain` Configuration:** This function utilizes a nested dictionary for its operational parameters. See the `perform_random_onchain()` function documentation below for details on the `config` parameter structure (e.g., action weights, amount percentages, safe token pairs).

## Functions

Detailed descriptions of the public functions available in this module.

### `stake_rotate()`
*   **Description:** Performs a "stake rotate" operation by first undelegating HYPE tokens from the current validator and then delegating them to a new validator. This is achieved through two separate `tokenDelegate` actions sent to the `/exchange` REST API endpoint. The `hyperliquid-python-sdk` provides helper functions (`hl.exchange.unstake()` and `hl.exchange.stake()`) for these actions.
*   **Parameters:**
    *   `exchange_agent` (`hyperliquid.exchange.Exchange` or `Any`): An initialized instance of the SDK's `Exchange` class, which handles wallet context and signing.
    *   `info_agent` (`hyperliquid.info.Info` or `Any`): An initialized instance of the SDK's `Info` class.
    *   `current_validator_address` (str): The address of the validator currently being delegated to.
    *   `new_validator_address` (str): The address of the validator to delegate to.
    *   `amount_wei` (int): The amount of HYPE tokens (in wei) to undelegate and then re-delegate.
*   **Returns:**
    *   `bool`: `True` if both undelegation and delegation were successful, `False` otherwise.
*   **High-Level Internal Logic:**
    1.  Execute the undelegation: Call `exchange_agent.unstake(validator_address=current_validator_address, amount_wei=amount_wei)`. This internally constructs and sends the signed JSON payload: `{"type": "tokenDelegate", "chain": "HYPERLIQUID", "payload": {"validator": current_validator_address, "amount": str(amount_wei), "isUndelegate": true}}`.
    2.  Execute the delegation: Call `exchange_agent.stake(validator_address=new_validator_address, amount_wei=amount_wei)`. This internally constructs and sends the signed JSON payload: `{"type": "tokenDelegate", "chain": "HYPERLIQUID", "payload": {"validator": new_validator_address, "amount": str(amount_wei), "isUndelegate": false}}`.
    3.  Log the results of both operations.
    4.  Return the success status.
    5.  (Optional pre-checks using `info_agent` for validator selection or delegation status can be added in future enhancements)
    6.  **(Optional):** Consider if HYPE needs to be moved to/from staking balance first using `cDeposit` or `cWithdraw` actions if the SDK doesn't handle this implicitly or if the user's HYPE isn't already in the staking balance.

### `vault_cycle()`
*   **Description:** Performs a "vault cycle" operation by depositing USDC into a specified vault (e.g., HLP vault `0xdfc24b077bc1425ad1dea75bcb6f8158e10df303`), holding the deposit for a defined period, and then withdrawing the full user equity. All operations are conducted via `POST /exchange` API calls with `action.type: "vaultTransfer"`, facilitated by the `hyperliquid-python-sdk`.
*   **Parameters:**
    *   `exchange_agent: Any` (An initialized instance of `hyperliquid.exchange.Exchange` for sending transactions.)
    *   `info_agent: Any` (An initialized instance of `hyperliquid.info.Info` for querying data.)
*   `user_address: str`: The user's 0x EVM address, required for fetching user-specific vault equity.
    *   `vault_address: str = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"` (The 0x address of the target vault, defaults to HLP Mainnet vault.)
    *   `min_deposit_usd_units: int = 20_000_000` (Minimum deposit amount in 6-decimal USD units; e.g., 20 USDC = 20 * 10^6.)
    *   `max_deposit_usd_units: int = 40_000_000` (Maximum deposit amount in 6-decimal USD units; e.g., 40 USDC = 40 * 10^6.)
    *   `min_hold_seconds: int = 1800` (Minimum duration to hold the deposit, in seconds; e.g., 30 minutes.)
    *   `max_hold_seconds: int = 5400` (Maximum duration to hold the deposit, in seconds; e.g., 90 minutes.)
*   **Returns:**
    *   `bool`: `True` if the complete deposit-hold-withdraw cycle is successful, `False` otherwise.
*   **High-Level Internal Logic:**
    1.  Generate a random deposit amount (integer, USD units) between `min_deposit_usd_units` and `max_deposit_usd_units`.
    2.  Call `exchange_agent.vault_transfer(vault_address=vault_address, is_deposit=True, usd_amount=deposit_amount_usd_units)` to deposit funds. This corresponds to a `POST /exchange` with `action.type: "vaultTransfer"`, `isDeposit: true`, `usd: deposit_amount_usd_units`, `vaultAddress: vault_address`.
    3.  Log the deposit action and outcome.
    4.  Generate a random hold time in seconds between `min_hold_seconds` and `max_hold_seconds`.
    5.  Pause execution for the generated hold duration (e.g., using `time.sleep()`).
    6.  Determine the user's current equity in the vault to withdraw the full amount. This is typically done by calling `info_agent.request({"type": "userVaultEquities", "user": <user_address_from_exchange_agent>})`. The specific field within the response that indicates the withdrawable amount in USD units needs to be identified and used. (Alternatively, `info_agent.request({"type": "vaultDetails", "vaultAddress": vault_address})` might provide total vault equity, but `userVaultEquities` is preferred for user-specific withdrawal amounts).
    7.  Convert the fetched equity (which might be in shares or another unit) to the required 6-decimal USD units format for the withdrawal transaction, if necessary. Let this be `withdraw_amount_usd_units`.
    8.  Call `exchange_agent.vault_transfer(vault_address=vault_address, is_deposit=False, usd_amount=withdraw_amount_usd_units)` to withdraw the full equity. This corresponds to a `POST /exchange` with `action.type: "vaultTransfer"`, `isDeposit: false`, `usd: withdraw_amount_usd_units`, `vaultAddress: vault_address`.
    9.  Log the withdrawal action and outcome.
    10. Return `True` if all steps (deposit, hold, equity fetch, withdrawal) complete successfully. Return `False` if any step fails.

### `spot_swap()`
*   **Description:** Performs a spot swap between two assets on the Hyperliquid platform. This is achieved by placing an order (market or limit) on the relevant spot market pair using the `/exchange` API endpoint. The `hyperliquid-python-sdk` (specifically `Exchange.order()` and `Info.meta()`) is used to facilitate this. For example, swapping HYPE for USDC involves identifying the HYPE/USDC market, determining HYPE as the base asset, and placing a sell order for HYPE.
*   **Parameters:**
    *   `exchange_agent` (`hyperliquid.exchange.Exchange`): An initialized instance of the SDK's `Exchange` class, handling wallet context and signing.
    *   `info_agent` (`hyperliquid.info.Info`): An initialized instance of the SDK's `Info` class, used to fetch asset metadata like integer IDs.
    *   `from_token` (`str`): The symbol of the asset to be sold (e.g., "HYPE", "USDC"). Must match the naming in `info_agent.meta()["universe"]`.
    *   `to_token` (`str`): The symbol of the asset to be bought (e.g., "USDC", "PURR"). Must match the naming in `info_agent.meta()["universe"]`.
    *   `amount_from` (`float`): The quantity of `from_token` to sell, in units of the `from_token` itself (e.g., if `from_token` is HYPE, 10.5 means 10.5 HYPE tokens).
    *   `order_type` (`dict`): A dictionary specifying the order type and its parameters.
        *   Example (Market Order): `{"market": {}}`
        *   Example (Limit Order, GTC): `{"limit": {"tif": "Gtc", "price": "2.55"}}` (Note: `price` must be a string).
        *   Supported TIF (Time in Force) for limit orders: `"Gtc"`, `"Alo"` (Add Liquidity Only), `"Ioc"` (Immediate Or Cancel).
*   **Returns:**
    *   `dict`: A dictionary containing the transaction response from Hyperliquid upon successful order placement (typically includes status and details of any filled/resting order). Structure is `{"status": "ok", "response": {"type": "order", "data": {"statuses": [{"resting": {"oid": ...}}, ...]}}}` or similar.
    *   Raises an exception on failure (e.g., API error, insufficient funds).
*   **High-Level Internal Logic:**
    1.  Use `info_agent.meta()["universe"]` to find the integer asset IDs and other metadata for `from_token` and `to_token`.
    2.  Determine the spot market pair (e.g., if `from_token`="HYPE", `to_token`="USDC", the market might be represented by the base asset "HYPE"). This step requires logic to select the correct market and base asset for the `Exchange.order()` call. For instance, if trading HYPE for USDC, the `asset` for the order call will be the integer ID of HYPE, and `is_buy` will be `False`. If trading USDC for HYPE, `asset` is HYPE's ID, and `is_buy` is `True`. (This assumes markets are defined like HYPE/USDC, where HYPE is the base).
    3.  The `asset_id_for_order` will be the integer ID of `from_token` if `from_token` is the base of the pair, or `to_token` if `to_token` is the base. The `is_buy_for_order` flag will be set accordingly. (This logic needs careful implementation).
        *   *Simpler approach:* Assume `from_token` is always the asset being directly sold or `to_token` is the asset being directly bought in the context of the `Exchange.order` `asset` parameter. For example, to swap HYPE for USDC:
            *   Identify the asset ID for HYPE (let's say `hype_id`).
            *   Call `exchange_agent.order(asset=hype_id, is_buy=False, sz=amount_from, limit_px=..., order_type=...)`. This sells HYPE. The counter asset (USDC) is implied by the market context Hyperliquid maintains for `hype_id` spot trading.
    4.  The `sz` parameter for `exchange_agent.order()` will be `amount_from`.
    5.  The `limit_px` parameter for `exchange_agent.order()` will be extracted from `order_type["limit"]["price"]` if it's a limit order. It must be a string.
    6.  Call `exchange_agent.order(...)` with the determined parameters.
    7.  Return the response from the SDK.

### `evm_roundtrip()`
*   **Description:** Performs a *fully automated* EVM roundtrip action. This involves:
    1.  Sending USDC from the user's wallet on Arbitrum to the Hyperliquid Bridge2 contract via a `web3.py` managed ERC-20 transfer.
    2.  Polling Hyperliquid L1 to confirm the deposit has been credited.
    3.  Optionally holding the funds on L1 for a specified duration.
    4.  Initiating a withdrawal of USDC from Hyperliquid L1 back to the user's Arbitrum wallet address using the SDK's `withdraw` action.
    5.  Polling the user's USDC balance on Arbitrum to confirm receipt of the withdrawn funds (accounting for Hyperliquid's withdrawal fee).
    This function requires pre-configured `web3.py` instances and a `LocalAccount` with an unlocked private key for signing Arbitrum transactions.
*   **Parameters:**
    ```python
    def evm_roundtrip(
        exchange_agent: Any,  # Expected: hyperliquid.exchange.Exchange
        info_agent: Any,  # Expected: hyperliquid.info.Info
        web3_arbitrum: Web3,  # Web3 instance for Arbitrum
        user_evm_address: str,  # User's address on Arbitrum
        arbitrum_private_key: str,  # Private key for signing Arbitrum transactions
        amount_usdc: float,  # Amount of USDC to roundtrip
        l1_hold_duration_seconds: int = 0,  # Optional hold time on L1
        poll_interval_seconds: int = 10,
        timeout_seconds: int = 300,
    ) -> bool:
    ```
*   **Returns:** `bool`: `True` for a successful full roundtrip, `False` otherwise.
*   **High-Level Internal Logic:**
    1.  **Prepare Arbitrum Deposit:**
        *   Construct an ERC-20 `transfer` transaction for `amount_usdc` to the `hyperliquid_bridge_arbitrum_address` using `usdc_contract`.
        *   Sign the transaction with `wallet_account`.
        *   Send the raw transaction using `web3_provider.eth.send_raw_transaction()`.
        *   Store the `deposit_tx_hash`.
    2.  **Confirm Arbitrum Deposit:**
        *   Wait for at least 1 on-chain confirmation for `deposit_tx_hash` on Arbitrum using `web3_provider.eth.wait_for_transaction_receipt()`.
    3.  **Confirm Hyperliquid L1 Credit:**
        *   Poll `info_agent.user_state(user=wallet_account.address)` on Hyperliquid L1.
        *   Check for an increase in the spot USDC balance corresponding to `amount_usdc`.
        *   Use exponential backoff and honor `deposit_confirmation_timeout_seconds`.
    4.  **Optional L1 Hold:**
        *   If `l1_hold_seconds` > 0, `await asyncio.sleep(l1_hold_seconds)`.
    5.  **Initiate Hyperliquid L1 Withdrawal:**
        *   Call `exchange_agent.withdraw(amount_usd=str(amount_usdc), destination_address=wallet_account.address, chain=chain_name)`.
        *   Store the `l1_withdrawal_response`. Verify `status == "ok"`.
    6.  **Confirm Arbitrum Withdrawal Reception:**
        *   Poll `usdc_contract.functions.balanceOf(wallet_account.address).call()` on Arbitrum.
        *   Check for an increase in the USDC balance (approximately `amount_usdc` minus the $1 Hyperliquid withdrawal fee).
        *   Use exponential backoff and honor `withdrawal_confirmation_timeout_seconds`.
    7.  **Return Status:**
        *   Compile and return a structured dictionary with the status of each step, relevant transaction hashes, and messages.
*   **Security Notice:** "This function requires access to a private key for signing transactions on an external EVM chain (Arbitrum). Ensure the private key is managed securely, for example, through environment variables or a dedicated secrets management system. Do not hardcode private keys."

### `perform_random_onchain()`
*   **Description:** Performs a randomly selected on-chain action on Hyperliquid. Actions can include `stake_rotate`, `vault_cycle`, `spot_swap`, `evm_roundtrip`, or simple read-only queries like fetching user state or market metadata. The selection is based on configurable weights. Parameters for the chosen action are generated randomly but safely (e.g., based on percentages of available balances or predefined safe ranges).
*   **Parameters:**
    ```python
    def perform_random_onchain(
        exchange_agent: Any,  # hyperliquid.exchange.Exchange
        info_agent: Any,  # hyperliquid.info.Info
        web3_arbitrum: Web3,  # Web3 instance for Arbitrum, only if evm_roundtrip might be chosen
        user_evm_address: str,
        arbitrum_private_key: str,  # Securely handled, passed to evm_roundtrip if chosen
        config: Dict[str, Any] # Configuration for random action generation
    ) -> Tuple[bool, str]: # (success_status, action_performed_message)
    ```
    *   `exchange_agent`: Initialized SDK `Exchange` class instance.
    *   `info_agent`: Initialized SDK `Info` class instance.
    *   `web3_arbitrum`: Initialized `Web3` instance for Arbitrum.
    *   `user_evm_address` (str): The user's 0x EVM address.
    *   `arbitrum_private_key` (str): User's Arbitrum private key (handle with extreme care).
    *   `config` (dict): A dictionary containing configuration for the random action generation. Expected structure:
        ```python
        {
            "action_weights": {
                "stake_rotate": int, "vault_cycle": int, "spot_swap": int,
                "evm_roundtrip": int, "query_user_state": int, "query_meta": int,
                "query_all_mids": int, "query_clearing_house_state": int
            },
            "stake_rotate": {"min_hype_percentage": float, "max_hype_percentage": float},
            "vault_cycle": { # Uses parameters from its own signature, but can be overridden/guided by this config
                "min_deposit_usd_units": int, "max_deposit_usd_units": int,
                "min_hold_seconds": int, "max_hold_seconds": int
            },
            "spot_swap": {
                "safe_pairs": List[Tuple[str, str]], # e.g., [("HYPE", "USDC")]
                "min_from_token_percentage": float, "max_from_token_percentage": float
            },
            "evm_roundtrip": {
                "min_amount_usdc": float, "max_amount_usdc": float,
                "min_l1_hold_seconds": int, "max_l1_hold_seconds": int
            },
            "hyperliquid_vault_address": str # e.g., "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
        }
        ```
*   **Returns:**
    *   `Tuple[bool, str]`: A tuple containing:
        *   `bool`: `True` if the selected action was attempted and reported success (or if a read-only query completed), `False` otherwise.
        *   `str`: A message describing the action taken and its outcome (e.g., "Successfully performed spot_swap: Sold 0.5 HYPE for USDC.", "Performed query_user_state.").
*   **High-Level Internal Logic:**
    1.  **Select Action:** Randomly choose an action from `["stake_rotate", "vault_cycle", "spot_swap", "evm_roundtrip", "query_user_state", "query_meta", "query_all_mids", "query_clearing_house_state"]` based on weights in `config["action_weights"]`.
    2.  **Generate Parameters (if applicable):**
        *   For `stake_rotate`: Query validators (`info_agent.validators()` or similar), current delegations, and HYPE balance (`info_agent.user_state()`). Select a new validator and a random percentage of HYPE balance (within `config["stake_rotate"]` percentages).
        *   For `vault_cycle`: Query L1 USDC balance (`info_agent.user_state()`). Use deposit/hold parameters from `config["vault_cycle"]`, ensuring deposit amount is feasible.
        *   For `spot_swap`: Query spot markets/assets (`info_agent.meta()`). Select a pair from `config["spot_swap"]["safe_pairs"]`. Query `from_token` balance (`info_agent.user_state()`). Use a random percentage of balance (within `config["spot_swap"]` percentages). Default to market order.
        *   For `evm_roundtrip`: Query Arbitrum USDC balance (via `web3_arbitrum`). Use amount/hold parameters from `config["evm_roundtrip"]`, ensuring amount is feasible.
        *   For simple queries: No dynamic parameters needed beyond agents and user address.
    3.  **Execute Action:** Call the corresponding sub-function (`stake_rotate()`, `vault_cycle()`, etc.) or SDK method (`info_agent.user_state()`, etc.).
    4.  **Log & Return:** Log the action, parameters, and outcome. Return success status and descriptive message.
    5.  **Safety:** Prioritize querying current balances before determining amounts. Use conservative ranges and percentages defined in `config`.

## ABIs/Addresses

Direct smart contract ABIs and addresses are **not** used for staking/delegation operations like `stake_rotate`. These actions are managed by HyperCore via signed REST API calls to the `/exchange` endpoint. The `hyperliquid-python-sdk` abstracts these API interactions.
*   **For `vault_cycle()`:** Vault operations are managed via signed REST API calls to the `/exchange` and `/info` endpoints. Direct smart contract ABIs and addresses are not used. The `hyperliquid-python-sdk` abstracts these API interactions.
*   **For `evm_roundtrip()` (fully automated):**
    *   Utilizes the fixed Arbitrum USDC contract address (`0xaf88d065e77c8cC2239327C5EDb3A432268e5831`) for `transfer` operations. Requires standard ERC-20 ABI.
    *   Utilizes the fixed Hyperliquid Bridge2 contract address on Arbitrum (`0x2df1c58541F4A5E519B0313f4A4A7A379AC3A78F`) as the recipient for USDC deposits.
    *   Hyperliquid L1 interactions (withdrawal, state polling) are managed via the SDK, abstracting L1 addresses.
*   **For `spot_swap()`:** Spot swap operations are executed via signed REST API calls to the `/exchange` endpoint, using an "order" action type. Direct smart contract interaction is not involved. The `hyperliquid-python-sdk` abstracts these API calls.

## RPC Details/API Endpoints

Interactions for staking, unstaking, and delegation are handled via the Hyperliquid REST API endpoints:
*   `/exchange` (e.g., `https://api.hyperliquid.xyz/exchange`) for actions like `tokenDelegate`.
*   `/info` (e.g., `https://api.hyperliquid.xyz/info`) for querying validator lists and current delegations.

Direct JSON-RPC interactions with Hyperliquid L1 or HyperEVM nodes are not required for these specific staking operations.
*   **For `vault_cycle()`:** Vault operations utilize the existing `/exchange` and `/info` REST API endpoints with specific action types (e.g., `vaultTransfer`, `userVaultEquities`). No separate RPC URLs or dedicated vault endpoints are required.
*   **For `spot_swap()`:**
    *   `/exchange` (e.g., `https://api.hyperliquid.xyz/exchange`): Used for submitting the spot order via the SDK.
    *   `/info` (e.g., `https://api.hyperliquid.xyz/info`): Used for querying spot market details, asset information (including token names to integer asset ID mappings via `meta()["universe"]`), and potentially order book data.
*   **For `evm_roundtrip()` (fully automated):**
    *   Requires an RPC endpoint for the external EVM chain (Arbitrum) to be configured with the `web3.py` provider.
    *   Hyperliquid L1 interactions (`/exchange` for withdrawal, `/info` for state polling) are abstracted by the SDK.