import logging
import random
import time
from typing import Any, Dict, Tuple

from web3 import Web3


# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# Constants for EVM roundtrip functionality
ARBITRUM_CHAIN_ID = 42161
USDC_ARBITRUM_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
HYPERLIQUID_BRIDGE2_ARBITRUM_ADDRESS = "0x2df1c58541F4A5E519B0313f4A4A7A379AC3A78F"
USDC_DECIMALS = 6

# Standard ERC-20 ABI for USDC transfer operations
ERC20_TRANSFER_ABI = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "to",
                "type": "address",
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256",
            },
        ],
        "name": "transfer",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address",
            }
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def stake_rotate(
    exchange_agent: Any,  # Expected: hyperliquid.exchange.Exchange
    info_agent: Any,  # Expected: hyperliquid.info.Info (pre-checks)
    current_validator_address: str,
    new_validator_address: str,
    amount_wei: int,
) -> bool:
    """
    Rotates staked HYPE from one validator to another on Hyperliquid.

    This involves undelegating from the current validator and then delegating
    the same amount to a new validator using the Hyperliquid API.

    Parameters
    ----------
    exchange_agent : hyperliquid.exchange.Exchange
        An initialized Exchange agent from the hyperliquid-python-sdk.
    info_agent : hyperliquid.info.Info
        An initialized Info agent from the hyperliquid-python-sdk,
        used for optional pre-checks like validator info or current
        delegations.
    current_validator_address : str
        The 0x-address of the validator to undelegate from.
    new_validator_address : str
        The 0x-address of the validator to delegate to.
    amount_wei : int
        The amount of HYPE in wei to rotate.

    Returns
    -------
    bool
        True if both undelegation and delegation were successful, False
        otherwise.

    Examples
    --------
    >>> # Conceptual example, requires live initialized agents
    >>> # from hyperliquid.exchange import Exchange
    >>> # from hyperliquid.info import Info
    >>> # from hyperliquid.utils import constants
    >>> # config = {"wallet": "0x...", "private_key": "...",
    >>> #           "base_url": constants.MAINNET_API_URL}
    >>> # exchange_agent = Exchange(config["wallet"], config["private_key"],
    >>> #                           base_url=config["base_url"])
    >>> # info_agent = Info(base_url=config["base_url"])
    >>> # stake_rotate(exchange_agent, info_agent, "0xValidatorA",
    >>> #              "0xValidatorB", 1000000000000000000)  # 1 HYPE
    True  # If successful
    """
    logging.info(
        f"Attempting to rotate {amount_wei} wei from validator "
        f"{current_validator_address} to {new_validator_address}."
    )

    try:
        # Step 1: Undelegate from the current validator
        logging.info(
            f"Undelegating {amount_wei} wei from " f"{current_validator_address}..."
        )
        unstake_response = exchange_agent.unstake(
            validator_address=current_validator_address,
            amount_wei=amount_wei,
        )
        logging.info(f"Undelegate response: {unstake_response}")

        # Basic check, SDK might have more robust success indicators
        if not isinstance(unstake_response, dict) or (
            unstake_response.get("status") != "ok"
            and not (
                isinstance(unstake_response.get("response"), dict)
                and unstake_response["response"].get("type") == "ok"
            )
        ):
            nested_status_ok = False
            if (
                isinstance(unstake_response.get("response"), dict)
                and unstake_response["response"].get("type") == "ok"
                and isinstance(unstake_response["response"].get("data"), dict)
                and unstake_response["response"]["data"].get("status") == "ok"
            ):
                nested_status_ok = True

            if not nested_status_ok:
                logging.error(
                    f"Failed to undelegate from {current_validator_address}. "
                    f"Response: {unstake_response}"
                )
                return False
        logging.info(f"Successfully undelegated from {current_validator_address}.")

        # Step 2: Delegate to the new validator
        logging.info(f"Delegating {amount_wei} wei to {new_validator_address}...")
        stake_response = exchange_agent.stake(
            validator_address=new_validator_address,
            amount_wei=amount_wei,
        )
        logging.info(f"Delegate response: {stake_response}")

        if not isinstance(stake_response, dict) or (
            stake_response.get("status") != "ok"
            and not (
                isinstance(stake_response.get("response"), dict)
                and stake_response["response"].get("type") == "ok"
            )
        ):
            nested_status_ok = False
            if (
                isinstance(stake_response.get("response"), dict)
                and stake_response["response"].get("type") == "ok"
                and isinstance(stake_response["response"].get("data"), dict)
                and stake_response["response"]["data"].get("status") == "ok"
            ):
                nested_status_ok = True

            if not nested_status_ok:
                logging.error(
                    f"Failed to delegate to {new_validator_address}. "
                    f"Response: {stake_response}"
                )
                return False
        logging.info(f"Successfully delegated to {new_validator_address}.")

        logging.info("Stake rotation successful.")
        return True

    except Exception as e:
        logging.error(
            f"An error occurred during stake rotation: {e}",
            exc_info=True,
        )
        return False


def vault_cycle(
    exchange_agent: Any,  # Expected: hyperliquid.exchange.Exchange
    info_agent: Any,  # Expected: hyperliquid.info.Info
    user_address: str,  # The user's 0x address for fetching vault equity
    vault_address: str = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
    min_deposit_usd_units: int = 20_000_000,  # 20 USDC
    max_deposit_usd_units: int = 40_000_000,  # 40 USDC
    min_hold_seconds: int = 1800,  # 30 minutes
    max_hold_seconds: int = 5400,  # 90 minutes
) -> bool:
    """
    Performs a vault cycle: deposit, hold, and withdraw from a Hyperliquid
    vault.

    This function deposits a random amount of USDC into a specified vault,
    holds it for a random duration, and then withdraws the full equity.
    Operations use the hyperliquid-python-sdk.

    Parameters
    ----------
    exchange_agent : hyperliquid.exchange.Exchange
        An initialized Exchange agent from the hyperliquid-python-sdk.
    info_agent : hyperliquid.info.Info
        An initialized Info agent from the hyperliquid-python-sdk.
    user_address : str
        The user's 0x address, used for fetching vault equity before
        withdrawal.
    vault_address : str, optional
        The 0x-address of the vault to interact with. Defaults to HLP
        vault "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303".
    min_deposit_usd_units : int, optional
        Minimum deposit amount in 6-decimal USD units
        (e.g., 20_000_000 for 20 USDC). Defaults to 20_000_000.
    max_deposit_usd_units : int, optional
        Maximum deposit amount in 6-decimal USD units
        (e.g., 40_000_000 for 40 USDC). Defaults to 40_000_000.
    min_hold_seconds : int, optional
        Minimum duration in seconds to hold the deposit. Defaults to 1800
        (30 minutes).
    max_hold_seconds : int, optional
        Maximum duration in seconds to hold the deposit. Defaults to 5400
        (90 minutes).

    Returns
    -------
    bool
        True if the entire vault cycle (deposit, hold, withdraw) was
        successful, False otherwise.

    Examples
    --------
    >>> # Conceptual example, requires live initialized agents
    >>> # and a valid user address
    >>> # from hyperliquid.exchange import Exchange
    >>> # from hyperliquid.info import Info
    >>> # from hyperliquid.utils import constants
    >>> # config = {
    >>> #     "wallet": "0xYOUR_WALLET_ADDRESS",
    >>> #     "private_key": "YOUR_PRIVATE_KEY",
    >>> #     "base_url": constants.MAINNET_API_URL
    >>> # }
    >>> # exchange_agent = Exchange(
    >>> #     config["wallet"], config["private_key"],
    >>> #     base_url=config["base_url"]
    >>> # )
    >>> # info_agent = Info(base_url=config["base_url"])
    >>> # user_address = config["wallet"]
    >>> # vault_cycle(exchange_agent, info_agent, user_address)
    True # If successful
    """
    logging.info(
        f"Starting vault cycle for user {user_address} " f"and vault {vault_address}."
    )

    # Step 1: Deposit
    deposit_amount_usd_units = random.randint(
        min_deposit_usd_units, max_deposit_usd_units
    )
    logging.info(
        f"Attempting to deposit "
        f"{deposit_amount_usd_units / 1_000_000:.2f} USDC "
        f"({deposit_amount_usd_units} units) into vault "
        f"{vault_address}."
    )
    try:
        deposit_response = exchange_agent.vault_transfer(
            vault_address=vault_address,
            is_deposit=True,
            usd_amount=deposit_amount_usd_units,
        )
        logging.info(f"Deposit response: {deposit_response}")

        # Check response status (structure may vary, adapt as needed)
        # Assuming a successful response contains a 'status' field or similar
        # Or that the SDK raises an exception on failure.
        # For this example, we'll check for a common pattern.
        if not isinstance(deposit_response, dict) or (
            deposit_response.get("status") != "ok"
            and not (
                isinstance(deposit_response.get("response"), dict)
                and deposit_response["response"].get("type") == "ok"
            )
        ):
            # More specific check for nested success status
            nested_status_ok = False
            if (
                isinstance(deposit_response.get("response"), dict)
                and deposit_response["response"].get("type") == "ok"
                and isinstance(deposit_response["response"].get("data"), dict)
                and deposit_response["response"]["data"].get("status") == "ok"
            ):
                nested_status_ok = True

            if not nested_status_ok:
                logging.error(
                    f"Failed to deposit into vault {vault_address}. "
                    f"Response: {deposit_response}"
                )
                return False
        logging.info(
            f"Successfully deposited "
            f"{deposit_amount_usd_units / 1_000_000:.2f} USDC "
            f"into vault {vault_address}."
        )

    except Exception as e:
        logging.error(
            f"Error during deposit to vault {vault_address}: {e}",
            exc_info=True,
        )
        return False

    # Step 2: Hold
    hold_duration_seconds = random.randint(min_hold_seconds, max_hold_seconds)
    logging.info(
        f"Holding deposit in vault {vault_address} for "
        f"{hold_duration_seconds} seconds "
        f"({hold_duration_seconds / 60:.2f} minutes)."
    )
    time.sleep(hold_duration_seconds)
    logging.info(f"Hold period finished for vault {vault_address}.")

    # Step 3: Withdraw
    logging.info(
        f"Attempting to withdraw full equity from vault {vault_address} "
        f"for user {user_address}."
    )
    try:
        user_vault_equities = info_agent.user_vault_equities(user_address)
        logging.debug(f"User vault equities response: {user_vault_equities}")

        target_vault_equity = None
        if isinstance(user_vault_equities, list):
            for equity_info in user_vault_equities:
                if (
                    isinstance(equity_info, dict)
                    and equity_info.get("vault_address", "").lower()
                    == vault_address.lower()
                ):
                    target_vault_equity = equity_info
                    break

        if not target_vault_equity:
            logging.warning(
                f"No equity found for user {user_address} in vault "
                f"{vault_address}. Skipping withdrawal. "
                f"Full equities: {user_vault_equities}"
            )
            # Depending on desired behavior, this could be False or True
            # If no deposit means no funds to withdraw, it might not be an
            # "error" for the cycle's success if the goal is to attempt a
            # cycle. For now, let's consider it a situation where
            # withdrawal can't proceed.
            return False  # Or True, if zero equity means "nothing to withdraw"

        normalized_equity_str = target_vault_equity.get("normalized_equity")
        if normalized_equity_str is None:
            logging.error(
                f"Could not find 'normalized_equity' for user "
                f"{user_address} in vault {vault_address}. "
                f"Equity info: {target_vault_equity}"
            )
            return False

        withdraw_amount_usd_units = int(float(normalized_equity_str) * 1_000_000)
        if withdraw_amount_usd_units <= 0:
            logging.info(
                f"User {user_address} has zero or negligible equity "
                f"({withdraw_amount_usd_units} units) in vault "
                f"{vault_address}. Skipping withdrawal."
            )
            return True  # Successfully did nothing as nothing to withdraw

        logging.info(
            f"Attempting to withdraw "
            f"{withdraw_amount_usd_units / 1_000_000:.2f} USDC "
            f"({withdraw_amount_usd_units} units) from vault "
            f"{vault_address}."
        )
        withdraw_response = exchange_agent.vault_transfer(
            vault_address=vault_address,
            is_deposit=False,
            usd_amount=withdraw_amount_usd_units,
        )
        logging.info(f"Withdrawal response: {withdraw_response}")

        if not isinstance(withdraw_response, dict) or (
            withdraw_response.get("status") != "ok"
            and not (
                isinstance(withdraw_response.get("response"), dict)
                and withdraw_response["response"].get("type") == "ok"
            )
        ):
            nested_status_ok = False
            if (
                isinstance(withdraw_response.get("response"), dict)
                and withdraw_response["response"].get("type") == "ok"
                and isinstance(withdraw_response["response"].get("data"), dict)
                and withdraw_response["response"]["data"].get("status") == "ok"
            ):
                nested_status_ok = True

            if not nested_status_ok:
                logging.error(
                    f"Failed to withdraw from vault {vault_address}. "
                    f"Response: {withdraw_response}"
                )
                return False
        logging.info(
            f"Successfully withdrew "
            f"{withdraw_amount_usd_units / 1_000_000:.2f} USDC "
            f"from vault {vault_address}."
        )

    except Exception as e:
        logging.error(
            f"Error during withdrawal from vault {vault_address}: {e}",
            exc_info=True,
        )
        return False

    logging.info(
        f"Vault cycle for user {user_address} and vault {vault_address} "
        f"completed successfully."
    )
    return True


def spot_swap(
    exchange_agent: Any,  # Expected: hyperliquid.exchange.Exchange
    info_agent: Any,  # Expected: hyperliquid.info.Info
    from_token: str,
    to_token: str,
    amount_from: float,
    # e.g., {"limit": {"tif": "Gtc", "price": "123.45"}}
    order_type: dict[str, Any],
) -> dict[str, Any]:
    """
    Performs a spot swap on Hyperliquid using the SDK's Exchange.order()
    method.

    This function handles the mapping of human-readable token names to
    Hyperliquid's internal asset IDs and determines the 'is_buy' flag based on
    the swap direction (e.g., TOKEN/USDC). It supports market and limit orders.

    Parameters
    ----------
    exchange_agent : hyperliquid.exchange.Exchange
        An initialized Exchange agent from the hyperliquid-python-sdk.
    info_agent : hyperliquid.info.Info
        An initialized Info agent from the hyperliquid-python-sdk, used to
        fetch asset metadata (universe).
    from_token : str
        The symbol of the token to swap from (e.g., "ETH", "USDC").
    to_token : str
        The symbol of the token to swap to (e.g., "USDC", "BTC").
    amount_from : float
        The quantity of the `from_token` to be swapped.
    order_type : dict
        A dictionary specifying the order type.
        Examples:
        - Market order: `{"market": {}}`
        - Limit order: `{"limit": {"tif": "Gtc", "price": "123.45"}}`

    Returns
    -------
    dict
        The API response dictionary from the order placement. Returns an error
        dictionary if the swap cannot be processed (e.g., unsupported pair,
        invalid token).

    Raises
    ------
    NotImplementedError
        If attempting a swap between two non-USDC tokens (e.g., BTC to ETH),
        as this initial implementation only supports USDC-based pairs.
    ValueError
        If a specified token is not found in Hyperliquid's asset universe.

    Examples
    --------
    >>> # Conceptual example, requires live initialized agents
    >>> # from hyperliquid.exchange import Exchange
    >>> # from hyperliquid.info import Info
    >>> # from hyperliquid.utils import constants
    >>> # config = {"wallet": "0x...", "private_key": "...",
    >>> #           "base_url": constants.MAINNET_API_URL}
    >>> # exchange_agent = Exchange(config["wallet"], config["private_key"],
    >>> #                           base_url=config["base_url"])
    >>> # info_agent = Info(base_url=config["base_url"])
    >>> #
    >>> # # Example: Sell 0.01 ETH for USDC (market order)
    >>> # response = spot_swap(
    >>> #     exchange_agent, info_agent, "ETH", "USDC", 0.01, {"market": {}}
    >>> # )
    >>> # print(response)
    >>> #
    >>> # # Example: Buy 0.005 BTC with USDC at a limit price of 70000
    >>> # # (limit order)
    >>> # response = spot_swap(
    >>> #     exchange_agent, info_agent, "USDC", "BTC", 0.005,
    >>> #     {"limit": {"tif": "Gtc", "price": "70000"}}
    >>> # )
    >>> # print(response)
    """
    logging.info(
        f"Attempting spot swap: {amount_from} {from_token} to {to_token} "
        f"with order type: {order_type}"
    )

    try:
        meta = info_agent.meta()
        assets = meta["universe"]

        asset_id = -1
        is_buy = False
        trading_asset_name = ""

        if to_token == "USDC":
            # Selling from_token for USDC (e.g., ETH/USDC, selling ETH)
            is_buy = False
            trading_asset_name = from_token
        elif from_token == "USDC":
            # Buying to_token with USDC (e.g., USDC/BTC, buying BTC)
            is_buy = True
            trading_asset_name = to_token
        else:
            logging.error(
                f"Unsupported swap pair: {from_token} to {to_token}. "
                "Only USDC-based spot swaps are supported in this "
                "implementation."
            )
            raise NotImplementedError("Direct non-USDC pair swaps are not supported.")

        # Find asset_id
        found_asset = False
        for i, asset_info in enumerate(assets):
            if asset_info["name"] == trading_asset_name:
                asset_id = i
                found_asset = True
                break

        if not found_asset:
            logging.error(f"Token '{trading_asset_name}' not found in asset universe.")
            raise ValueError(f"Token '{trading_asset_name}' not found.")

        # Determine size (`sz`)
        # The order() method takes float for size, so no explicit decimal
        # conversion needed here unless amount_from needs to be scaled by
        # 10^sz_decimals for some reason, but SDK usually handles this.
        # Assuming amount_from is already human-readable.
        sz = amount_from

        # Determine limit_px
        limit_px = "0"  # Default for market orders
        if "limit" in order_type and "price" in order_type["limit"]:
            limit_px = str(order_type["limit"]["price"])

        logging.info(
            f"Placing order: asset_id={asset_id}, is_buy={is_buy}, sz={sz}, "
            f"limit_px={limit_px}, order_type={order_type}"
        )

        response = exchange_agent.order(
            asset=asset_id,
            is_buy=is_buy,
            sz=sz,
            limit_px=limit_px,
            order_type=order_type,
            reduce_only=False,
        )
        logging.info(f"Order placement response: {response}")

        # Basic check for success, adapt based on actual SDK response structure
        if not isinstance(response, dict) or (
            response.get("status") != "ok"
            and not (
                isinstance(response.get("response"), dict)
                and response["response"].get("type") == "ok"
            )
        ):
            nested_status_ok = False
            if (
                isinstance(response.get("response"), dict)
                and response["response"].get("type") == "ok"
                and isinstance(response["response"].get("data"), dict)
                and response["response"]["data"].get("status") == "ok"
            ):
                nested_status_ok = True

            if not nested_status_ok:
                logging.error(f"Order placement failed. Response: {response}")
                return {
                    "status": "error",
                    "message": "Order placement failed",
                    "response": response,
                }

        logging.info("Spot swap order placed successfully.")
        return dict(response)

    except NotImplementedError as e:
        logging.error(f"Spot swap error: {e}")
        return {"status": "error", "message": str(e)}
    except ValueError as e:
        logging.error(f"Spot swap error: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during spot swap: {e}",
            exc_info=True,
        )
        return {
            "status": "error",
            "message": f"Unexpected error: {e}",
        }


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
    """
    Performs a fully automated EVM roundtrip: Arbitrum -> L1 -> Arbitrum.

    This function automates the complete lifecycle of moving USDC from Arbitrum
    to Hyperliquid L1 and back to Arbitrum. It handles deposit confirmation,
    optional hold periods, withdrawal initiation, and withdrawal confirmation.

    Parameters
    ----------
    exchange_agent : Any
        An initialized Exchange agent from the hyperliquid-python-sdk.
    info_agent : Any
        An initialized Info agent from the hyperliquid-python-sdk.
    web3_arbitrum : Web3
        Web3 instance configured for Arbitrum network.
    user_evm_address : str
        User's Ethereum address on Arbitrum (0x format).
    arbitrum_private_key : str
        Private key for signing Arbitrum transactions. Should be managed
        securely via environment variables or secrets management.
    amount_usdc : float
        Amount of USDC to transfer in the roundtrip (minimum 5.0).
    l1_hold_duration_seconds : int, optional
        Duration to hold funds on Hyperliquid L1 before withdrawal, default 0.
    poll_interval_seconds : int, optional
        Interval between polling attempts for confirmations, by default 10.
    timeout_seconds : int, optional
        Maximum time to wait for each confirmation step, by default 300.

    Returns
    -------
    bool
        True if the entire roundtrip completed successfully, False otherwise.

    Examples
    --------
    >>> from web3 import Web3
    >>> from hyperliquid.exchange import Exchange
    >>> from hyperliquid.info import Info
    >>> # Initialize components (example)
    >>> w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))
    >>> exchange = Exchange(
    ...     wallet_address, private_key, base_url="https://api.hyperliquid.xyz"
    ... )
    >>> info = Info(base_url="https://api.hyperliquid.xyz")
    >>> # Perform roundtrip
    >>> success = evm_roundtrip(
    ...     exchange, info, w3, "0x123...", "0xabc...", 25.0, 60
    ... )
    >>> print(success)
    True
    """
    if amount_usdc < 5.0:
        logging.error(f"Amount {amount_usdc} USDC is below minimum of 5.0 USDC")
        return False

    logging.info(
        f"Starting EVM roundtrip: {amount_usdc} USDC "
        f"from Arbitrum -> L1 -> Arbitrum"
    )

    try:
        # Step 1: Deposit USDC to Hyperliquid L1 via Arbitrum Bridge2
        if not _deposit_to_l1(
            web3_arbitrum,
            user_evm_address,
            arbitrum_private_key,
            amount_usdc,
        ):
            return False

        # Step 2: Poll for L1 deposit confirmation
        if not _poll_l1_deposit_confirmation(
            info_agent,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds,
            timeout_seconds,
        ):
            return False

        # Step 3: Optional hold on L1
        if l1_hold_duration_seconds > 0:
            logging.info(f"Holding on L1 for {l1_hold_duration_seconds} seconds")
            time.sleep(l1_hold_duration_seconds)

        # Step 4: Withdraw USDC from Hyperliquid L1 to Arbitrum
        if not _withdraw_from_l1(exchange_agent, amount_usdc):
            return False

        # Step 5: Poll for Arbitrum withdrawal confirmation
        if not _poll_arbitrum_withdrawal_confirmation(
            web3_arbitrum,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds,
            timeout_seconds,
        ):
            return False

        logging.info("EVM roundtrip completed successfully")
        return True

    except Exception as e:
        logging.error(f"EVM roundtrip failed with exception: {e}", exc_info=True)
        return False


def _deposit_to_l1(
    web3_arbitrum: Web3,
    user_evm_address: str,
    arbitrum_private_key: str,
    amount_usdc: float,
) -> bool:
    """
    Deposits USDC from Arbitrum to Hyperliquid L1 via Bridge2 contract.

    Parameters
    ----------
    web3_arbitrum : Web3
        Web3 instance for Arbitrum network.
    user_evm_address : str
        User's Ethereum address.
    arbitrum_private_key : str
        Private key for signing transactions.
    amount_usdc : float
        Amount of USDC to deposit.

    Returns
    -------
    bool
        True if deposit transaction was successful, False otherwise.
    """
    try:
        # Convert amount to integer units (USDC has 6 decimals)
        amount_units = int(amount_usdc * (10**USDC_DECIMALS))

        # Create USDC contract instance
        usdc_contract = web3_arbitrum.eth.contract(
            address=Web3.to_checksum_address(USDC_ARBITRUM_ADDRESS),
            abi=ERC20_TRANSFER_ABI,
        )

        # Build transfer transaction
        transaction = usdc_contract.functions.transfer(
            HYPERLIQUID_BRIDGE2_ARBITRUM_ADDRESS, amount_units
        ).build_transaction(
            {
                "from": user_evm_address,
                "nonce": web3_arbitrum.eth.get_transaction_count(
                    Web3.to_checksum_address(user_evm_address)
                ),
                "gas": 100000,
                "maxFeePerGas": web3_arbitrum.to_wei("2", "gwei"),
                "maxPriorityFeePerGas": web3_arbitrum.to_wei("1", "gwei"),
                "chainId": ARBITRUM_CHAIN_ID,
            }
        )

        # Sign transaction
        signed_txn = web3_arbitrum.eth.account.sign_transaction(
            transaction, private_key=arbitrum_private_key
        )

        # Send transaction
        tx_hash = web3_arbitrum.eth.send_raw_transaction(signed_txn.raw_transaction)
        logging.info(f"Deposit transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt
        receipt = web3_arbitrum.eth.wait_for_transaction_receipt(tx_hash)
        if receipt["status"] == 1:
            logging.info(f"Deposit transaction confirmed: {amount_usdc} USDC")
            return True
        else:
            logging.error(f"Deposit transaction failed: {tx_hash.hex()}")
            return False

    except Exception as e:
        logging.error(f"Failed to deposit to L1: {e}", exc_info=True)
        return False


def _poll_l1_deposit_confirmation(
    info_agent: Any,
    user_evm_address: str,
    amount_usdc: float,
    poll_interval_seconds: int,
    timeout_seconds: int,
) -> bool:
    """
    Polls Hyperliquid L1 to confirm deposit has been credited.

    Parameters
    ----------
    info_agent : Any
        Hyperliquid Info agent instance.
    user_evm_address : str
        User's Ethereum address.
    amount_usdc : float
        Expected deposit amount.
    poll_interval_seconds : int
        Polling interval.
    timeout_seconds : int
        Maximum time to wait.

    Returns
    -------
    bool
        True if deposit confirmed, False if timeout or error.
    """
    start_time = time.time()

    try:
        # Get initial balance
        initial_state = info_agent.user_state(user_evm_address)
        initial_balance = 0.0
        if initial_state and "withdrawable" in initial_state:
            for balance in initial_state["withdrawable"]:
                if balance["coin"] == "USDC":
                    initial_balance = float(balance["total"])
                    break

        logging.info(f"Initial L1 USDC balance: {initial_balance}")
        expected_balance = initial_balance + amount_usdc

        while time.time() - start_time < timeout_seconds:
            current_state = info_agent.user_state(user_evm_address)
            current_balance = 0.0

            if current_state and "withdrawable" in current_state:
                for balance in current_state["withdrawable"]:
                    if balance["coin"] == "USDC":
                        current_balance = float(balance["total"])
                        break

            if current_balance >= expected_balance:
                logging.info(f"L1 deposit confirmed: {current_balance} USDC")
                return True

            logging.info(f"Waiting for L1 credit... Current: {current_balance} USDC")
            time.sleep(poll_interval_seconds)

        logging.error(f"L1 deposit confirmation timeout after {timeout_seconds}s")
        return False

    except Exception as e:
        logging.error(f"Failed to confirm L1 deposit: {e}", exc_info=True)
        return False


def _withdraw_from_l1(exchange_agent: Any, amount_usdc: float) -> bool:
    """
    Withdraws USDC from Hyperliquid L1 to Arbitrum.

    Parameters
    ----------
    exchange_agent : Any
        Hyperliquid Exchange agent instance.
    amount_usdc : float
        Amount to withdraw.

    Returns
    -------
    bool
        True if withdrawal initiated successfully, False otherwise.
    """
    try:
        # Convert to the format expected by the SDK (integer units)
        amount_units = int(amount_usdc * (10**USDC_DECIMALS))

        # Initiate withdrawal
        response = exchange_agent.withdraw(amount_units, "USDC")
        logging.info(f"Withdrawal response: {response}")

        # Check if withdrawal was successful
        if isinstance(response, dict):
            if response.get("status") == "ok" or (
                isinstance(response.get("response"), dict)
                and response["response"].get("type") == "ok"
            ):
                logging.info(f"L1 withdrawal initiated: {amount_usdc} USDC")
                return True

        logging.error(f"L1 withdrawal failed: {response}")
        return False

    except Exception as e:
        logging.error(f"Failed to withdraw from L1: {e}", exc_info=True)
        return False


def _poll_arbitrum_withdrawal_confirmation(
    web3_arbitrum: Web3,
    user_evm_address: str,
    amount_usdc: float,
    poll_interval_seconds: int,
    timeout_seconds: int,
) -> bool:
    """
    Polls Arbitrum to confirm withdrawal has been received.

    Parameters
    ----------
    web3_arbitrum : Web3
        Web3 instance for Arbitrum.
    user_evm_address : str
        User's Ethereum address.
    amount_usdc : float
        Expected withdrawal amount (minus fees).
    poll_interval_seconds : int
        Polling interval.
    timeout_seconds : int
        Maximum time to wait.

    Returns
    -------
    bool
        True if withdrawal confirmed, False if timeout or error.
    """
    start_time = time.time()

    try:
        # Create USDC contract instance
        usdc_contract = web3_arbitrum.eth.contract(
            address=Web3.to_checksum_address(USDC_ARBITRUM_ADDRESS),
            abi=ERC20_TRANSFER_ABI,
        )

        # Get initial balance
        initial_balance_units = usdc_contract.functions.balanceOf(
            user_evm_address
        ).call()
        initial_balance = initial_balance_units / (10**USDC_DECIMALS)

        logging.info(f"Initial Arbitrum USDC balance: {initial_balance}")

        # Account for Hyperliquid withdrawal fee (~$1)
        expected_increase = amount_usdc - 1.0
        expected_balance = initial_balance + expected_increase

        while time.time() - start_time < timeout_seconds:
            current_balance_units = usdc_contract.functions.balanceOf(
                user_evm_address
            ).call()
            current_balance = current_balance_units / (10**USDC_DECIMALS)

            if current_balance >= expected_balance:
                logging.info(f"Arbitrum withdrawal confirmed: {current_balance} USDC")
                return True

            logging.info(
                f"Waiting for Arbitrum withdrawal... "
                f"Current: {current_balance} USDC"
            )
            time.sleep(poll_interval_seconds)

        logging.error(
            f"Arbitrum withdrawal confirmation timeout " f"after {timeout_seconds}s"
        )
        return False

    except Exception as e:
        logging.error(
            f"Failed to confirm Arbitrum withdrawal: {e}",
            exc_info=True,
        )
        return False


def perform_random_onchain(
    exchange_agent: Any,  # hyperliquid.exchange.Exchange
    info_agent: Any,  # hyperliquid.info.Info
    web3_arbitrum: Any,  # web3.Web3 (for evm_roundtrip)
    user_evm_address: str,
    arbitrum_private_key: str,  # To be handled securely by caller
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Performs a randomly selected on-chain action on Hyperliquid.

    This function randomly selects and executes one of several possible
    actions:
    stake_rotate, vault_cycle, spot_swap, evm_roundtrip, or read-only queries
    (query_user_state, query_meta, query_all_mids,
    query_clearing_house_state).
    The selection is based on configurable weights, and parameters are
    generated
    safely by querying current state and using configurable ranges.

    Parameters
    ----------
    exchange_agent : Any
        An initialized Exchange agent from the hyperliquid-python-sdk.
    info_agent : Any
        An initialized Info agent from the hyperliquid-python-sdk.
    web3_arbitrum : Any
        Web3 instance for Arbitrum network (for evm_roundtrip action).
    user_evm_address : str
        The user's 0x EVM address.
    arbitrum_private_key : str
        Private key for signing Arbitrum transactions. Should be handled
        securely by the caller.
    config : Dict[str, Any]
        Configuration dictionary containing action weights, randomization
        parameters, and other settings. Expected structure:
        {
            "action_weights": {
                "stake_rotate": int, "vault_cycle": int,
                "spot_swap": int,
                "evm_roundtrip": int, "query_user_state": int,
                "query_meta": int,
                "query_all_mids": int,
                "query_clearing_house_state": int
            },
            "stake_rotate_params": {
                "min_hype_percentage": float, "max_hype_percentage": float
            },
            "vault_cycle_params": {
                "min_deposit_usd_units": int,
                "max_deposit_usd_units": int,
                "min_hold_seconds": int, "max_hold_seconds": int
            },
            "spot_swap_params": {
                "safe_pairs": List[Tuple[str, str]],
                "min_from_token_percentage": float,
                "max_from_token_percentage": float
            },
            "evm_roundtrip_params": {
                "min_amount_usdc": float, "max_amount_usdc": float,
                "min_l1_hold_seconds": int, "max_l1_hold_seconds": int
            },
            "hyperliquid_vault_address": str
        }

    Returns
    -------
    Tuple[bool, str]
        A tuple containing:
        - bool: True if the selected action was successful, False otherwise.
        - str: A message describing the action taken and its outcome.

    Examples
    --------
    >>> # Conceptual example with mock agents and config
    >>> config = {
    ...     "action_weights": {"query_user_state": 10, "spot_swap": 5},
    ...     "spot_swap_params": {"safe_pairs": [("USDC", "ETH")],
    ...                         "min_from_token_percentage": 0.01,
    ...                         "max_from_token_percentage": 0.05}
    ... }
    >>> success, message = perform_random_onchain(
    ...     exchange_agent, info_agent, web3_arbitrum,
    ...     "0x123...", "0xabc...", config
    ... )
    >>> print(f"Success: {success}, Message: {message}")
    Success: True, Message: Successfully performed query_user_state
    """
    logging.info("Starting perform_random_onchain execution")

    try:
        # Extract action weights from config
        action_weights = config.get("action_weights", {})
        if not action_weights:
            return False, "No action weights provided in config"

        # Define available actions and their weights
        actions = list(action_weights.keys())
        weights = list(action_weights.values())

        # Randomly select an action
        selected_action = random.choices(actions, weights=weights, k=1)[0]
        logging.info(f"Selected action: {selected_action}")

        # Execute the selected action
        if selected_action == "stake_rotate":
            return _execute_stake_rotate(
                exchange_agent, info_agent, user_evm_address, config
            )
        elif selected_action == "vault_cycle":
            return _execute_vault_cycle(
                exchange_agent, info_agent, user_evm_address, config
            )
        elif selected_action == "spot_swap":
            return _execute_spot_swap(exchange_agent, info_agent, config)
        elif selected_action == "evm_roundtrip":
            return _execute_evm_roundtrip(
                exchange_agent,
                info_agent,
                web3_arbitrum,
                user_evm_address,
                arbitrum_private_key,
                config,
            )
        elif selected_action == "query_user_state":
            return _execute_query_user_state(info_agent, user_evm_address)
        elif selected_action == "query_meta":
            return _execute_query_meta(info_agent)
        elif selected_action == "query_all_mids":
            return _execute_query_all_mids(info_agent)
        elif selected_action == "query_clearing_house_state":
            return _execute_query_clearing_house_state(info_agent)
        else:
            return False, f"Unknown action: {selected_action}"

    except Exception as e:
        logging.error(f"Error in perform_random_onchain: {e}", exc_info=True)
        return False, f"Failed to perform random action: {e}"


def _execute_stake_rotate(
    exchange_agent: Any, info_agent: Any, user_evm_address: str, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Execute stake_rotate action with randomly generated parameters.

    Parameters
    ----------
    exchange_agent : Any
        Hyperliquid Exchange agent instance.
    info_agent : Any
        Hyperliquid Info agent instance.
    user_evm_address : str
        User's EVM address.
    config : Dict[str, Any]
        Configuration containing stake_rotate_params.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        # Get current delegations and validators
        delegations = info_agent.user_staking_delegations(user_evm_address)
        validators = info_agent.validators()

        if not delegations or not validators:
            return False, "No current delegations or validators available"

        # Select a current delegation to rotate from
        current_delegation = random.choice(delegations)
        current_validator = current_delegation.get("validator")
        delegated_amount = int(current_delegation.get("amount", 0))

        if delegated_amount <= 0:
            return False, "No delegated amount to rotate"

        # Select a different validator to rotate to
        available_validators = [
            v for v in validators if v.get("address") != current_validator
        ]
        if not available_validators:
            return False, "No alternative validators available"

        new_validator = random.choice(available_validators).get("address")

        # Generate random rotation amount (percentage of delegated amount)
        params = config.get("stake_rotate_params", {})
        min_pct = params.get("min_hype_percentage", 0.01)
        max_pct = params.get("max_hype_percentage", 0.1)
        rotation_pct = random.uniform(min_pct, max_pct)
        rotation_amount = int(delegated_amount * rotation_pct)

        # Execute stake rotation
        success = stake_rotate(
            exchange_agent,
            info_agent,
            current_validator,
            new_validator,
            rotation_amount,
        )

        if success:
            msg = (
                f"Successfully rotated {rotation_amount} wei from "
                f"{current_validator} to {new_validator}"
            )
            return True, msg
        else:
            msg = (
                f"Failed to rotate stake from {current_validator} "
                f"to {new_validator}"
            )
            return False, msg

    except Exception as e:
        logging.error(f"Error in _execute_stake_rotate: {e}", exc_info=True)
        return False, f"Error executing stake_rotate: {e}"


def _execute_vault_cycle(
    exchange_agent: Any, info_agent: Any, user_evm_address: str, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Execute vault_cycle action with randomly generated parameters.

    Parameters
    ----------
    exchange_agent : Any
        Hyperliquid Exchange agent instance.
    info_agent : Any
        Hyperliquid Info agent instance.
    user_evm_address : str
        User's EVM address.
    config : Dict[str, Any]
        Configuration containing vault_cycle_params.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        params = config.get("vault_cycle_params", {})
        default_vault = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
        vault_address = config.get("hyperliquid_vault_address", default_vault)

        min_deposit = params.get("min_deposit_usd_units", 20_000_000)
        max_deposit = params.get("max_deposit_usd_units", 40_000_000)
        min_hold = params.get("min_hold_seconds", 1800)
        max_hold = params.get("max_hold_seconds", 5400)

        success = vault_cycle(
            exchange_agent=exchange_agent,
            info_agent=info_agent,
            user_address=user_evm_address,
            vault_address=vault_address,
            min_deposit_usd_units=min_deposit,
            max_deposit_usd_units=max_deposit,
            min_hold_seconds=min_hold,
            max_hold_seconds=max_hold,
        )

        if success:
            msg = f"Successfully completed vault cycle for vault " f"{vault_address}"
            return True, msg
        else:
            msg = f"Failed to complete vault cycle for vault {vault_address}"
            return False, msg

    except Exception as e:
        logging.error(f"Error in _execute_vault_cycle: {e}", exc_info=True)
        return False, f"Error executing vault_cycle: {e}"


def _execute_spot_swap(
    exchange_agent: Any, info_agent: Any, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Execute spot_swap action with randomly generated parameters.

    Parameters
    ----------
    exchange_agent : Any
        Hyperliquid Exchange agent instance.
    info_agent : Any
        Hyperliquid Info agent instance.
    config : Dict[str, Any]
        Configuration containing spot_swap_params.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        params = config.get("spot_swap_params", {})
        safe_pairs = params.get("safe_pairs", [("USDC", "ETH")])
        min_pct = params.get("min_from_token_percentage", 0.01)
        max_pct = params.get("max_from_token_percentage", 0.05)

        # Select a random trading pair
        from_token, to_token = random.choice(safe_pairs)

        # Get user state to check balance
        user_state = info_agent.user_state(exchange_agent.wallet.address)
        if not user_state or "withdrawable" not in user_state:
            return False, "Could not fetch user balance"

        # Find balance for from_token
        from_balance = 0.0
        for balance in user_state["withdrawable"]:
            if balance["coin"] == from_token:
                from_balance = float(balance["total"])
                break

        if from_balance <= 0:
            return False, f"Insufficient {from_token} balance for swap"

        # Generate random swap amount
        swap_pct = random.uniform(min_pct, max_pct)
        amount_from = from_balance * swap_pct

        # Execute spot swap (market order)
        response = spot_swap(
            exchange_agent=exchange_agent,
            info_agent=info_agent,
            from_token=from_token,
            to_token=to_token,
            amount_from=amount_from,
            order_type={"market": {}},
        )

        if response.get("status") == "error":
            error_msg = response.get("message", "Unknown error")
            return False, f"Spot swap failed: {error_msg}"
        else:
            msg = (
                f"Successfully swapped {amount_from:.6f} {from_token} "
                f"for {to_token}"
            )
            return True, msg

    except Exception as e:
        logging.error(f"Error in _execute_spot_swap: {e}", exc_info=True)
        return False, f"Error executing spot_swap: {e}"


def _execute_evm_roundtrip(
    exchange_agent: Any,
    info_agent: Any,
    web3_arbitrum: Any,
    user_evm_address: str,
    arbitrum_private_key: str,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Execute evm_roundtrip action with randomly generated parameters.

    Parameters
    ----------
    exchange_agent : Any
        Hyperliquid Exchange agent instance.
    info_agent : Any
        Hyperliquid Info agent instance.
    web3_arbitrum : Any
        Web3 instance for Arbitrum.
    user_evm_address : str
        User's EVM address.
    arbitrum_private_key : str
        Private key for Arbitrum transactions.
    config : Dict[str, Any]
        Configuration containing evm_roundtrip_params.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        params = config.get("evm_roundtrip_params", {})
        min_amount = params.get("min_amount_usdc", 5.0)
        max_amount = params.get("max_amount_usdc", 25.0)
        min_hold = params.get("min_l1_hold_seconds", 0)
        max_hold = params.get("max_l1_hold_seconds", 300)

        # Generate random parameters
        amount_usdc = random.uniform(min_amount, max_amount)
        hold_duration = random.randint(min_hold, max_hold)

        success = evm_roundtrip(
            exchange_agent=exchange_agent,
            info_agent=info_agent,
            web3_arbitrum=web3_arbitrum,
            user_evm_address=user_evm_address,
            arbitrum_private_key=arbitrum_private_key,
            amount_usdc=amount_usdc,
            l1_hold_duration_seconds=hold_duration,
        )

        if success:
            msg = (
                f"Successfully completed EVM roundtrip with " f"{amount_usdc:.2f} USDC"
            )
            return True, msg
        else:
            msg = f"Failed to complete EVM roundtrip with " f"{amount_usdc:.2f} USDC"
            return False, msg

    except Exception as e:
        logging.error(f"Error in _execute_evm_roundtrip: {e}", exc_info=True)
        return False, f"Error executing evm_roundtrip: {e}"


def _execute_query_user_state(
    info_agent: Any, user_evm_address: str
) -> Tuple[bool, str]:
    """
    Execute query_user_state read-only action.

    Parameters
    ----------
    info_agent : Any
        Hyperliquid Info agent instance.
    user_evm_address : str
        User's EVM address.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        user_state = info_agent.user_state(user_evm_address)
        char_count = len(str(user_state))
        logging.info(f"User state query successful: {char_count} characters")
        return True, "Successfully performed query_user_state"
    except Exception as e:
        logging.error(f"Error in _execute_query_user_state: {e}", exc_info=True)
        return False, f"Error executing query_user_state: {e}"


def _execute_query_meta(info_agent: Any) -> Tuple[bool, str]:
    """
    Execute query_meta read-only action.

    Parameters
    ----------
    info_agent : Any
        Hyperliquid Info agent instance.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        meta = info_agent.meta()
        asset_count = len(meta.get("universe", []))
        logging.info(f"Meta query successful: {asset_count} assets")
        return True, "Successfully performed query_meta"
    except Exception as e:
        logging.error(f"Error in _execute_query_meta: {e}", exc_info=True)
        return False, f"Error executing query_meta: {e}"


def _execute_query_all_mids(info_agent: Any) -> Tuple[bool, str]:
    """
    Execute query_all_mids read-only action.

    Parameters
    ----------
    info_agent : Any
        Hyperliquid Info agent instance.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        all_mids = info_agent.all_mids()
        logging.info(f"All mids query successful: {len(all_mids)} markets")
        return True, "Successfully performed query_all_mids"
    except Exception as e:
        logging.error(f"Error in _execute_query_all_mids: {e}", exc_info=True)
        return False, f"Error executing query_all_mids: {e}"


def _execute_query_clearing_house_state(info_agent: Any) -> Tuple[bool, str]:
    """
    Execute query_clearing_house_state read-only action.

    Parameters
    ----------
    info_agent : Any
        Hyperliquid Info agent instance.

    Returns
    -------
    Tuple[bool, str]
        Success status and descriptive message.
    """
    try:
        info_agent.clearing_house_state()
        logging.info("Clearing house state query successful")
        return True, "Successfully performed query_clearing_house_state"
    except Exception as e:
        logging.error(
            f"Error in _execute_query_clearing_house_state: {e}", exc_info=True
        )
        return False, f"Error executing query_clearing_house_state: {e}"
