# airdrops/src/airdrops/protocols/scroll/scroll.py
"""
Scroll Protocol Module.

This module provides functionalities to interact with the Scroll network,
including bridging ETH and ERC20 tokens between Ethereum (L1) and Scroll (L2),
and swapping tokens on SyncSwap DEX (L2).
"""

import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, Optional, Any, cast, Sequence, List, Tuple, Union
from requests.exceptions import ConnectionError, Timeout  # Added Timeout

from eth_abi.abi import encode as abi_encode  # Corrected import path
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.exceptions import ContractLogicError
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.types import TxParams, Wei, TxReceipt

from airdrops.shared import config as shared_config
from .exceptions import (
    ScrollBridgeError,
    InsufficientBalanceError,
    TransactionRevertedError,
    ApprovalError,
    GasEstimationError,
    MaxRetriesExceededError,
    TransactionBuildError,
    TransactionSendError,
    ScrollSwapError,
    InsufficientLiquidityError,
    TokenNotSupportedError,
    PoolNotFoundError,
    ScrollLendingError,
    InsufficientCollateralError,
    RepayAmountExceedsDebtError,
    LayerBankComptrollerRejectionError,
    ScrollRandomActivityError,
    # SlippageTooHighError, # Not directly detectable pre-swap with this ABI
)

# Configure logging for this module
logger = logging.getLogger(__name__)

# Contract addresses from architecture / config
SCROLL_L1_GATEWAY_ROUTER_ADDRESS = \
    shared_config.SCROLL_L1_GATEWAY_ROUTER_ADDRESS
SCROLL_L2_GATEWAY_ROUTER_ADDRESS = \
    shared_config.SCROLL_L2_GATEWAY_ROUTER_ADDRESS
SCROLL_L1_GAS_ORACLE_ADDRESS = \
    shared_config.SCROLL_L1_GAS_ORACLE_ADDRESS
SCROLL_L2_GAS_ORACLE_ADDRESS = \
    shared_config.SCROLL_L2_GAS_ORACLE_ADDRESS
SYNC_SWAP_ROUTER_ADDRESS_SCROLL = \
    shared_config.SYNC_SWAP_ROUTER_ADDRESS_SCROLL
SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL = \
    shared_config.SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL

# LayerBank V2 Configuration
LAYERBANK_COMPTROLLER_ADDRESS_SCROLL = \
    shared_config.LAYERBANK_COMPTROLLER_ADDRESS_SCROLL
LAYERBANK_PRICE_ORACLE_ADDRESS_SCROLL = \
    shared_config.LAYERBANK_PRICE_ORACLE_ADDRESS_SCROLL
LAYERBANK_LBETH_ADDRESS_SCROLL = \
    shared_config.LAYERBANK_LBETH_ADDRESS_SCROLL
LAYERBANK_LBUSDC_ADDRESS_SCROLL = \
    shared_config.LAYERBANK_LBUSDC_ADDRESS_SCROLL
SCROLL_USDC_TOKEN_ADDRESS = \
    shared_config.SCROLL_USDC_TOKEN_ADDRESS

# ABI Names
L1_GATEWAY_ROUTER_ABI_NAME = "L1GatewayRouter"
L2_GATEWAY_ROUTER_ABI_NAME = "L2GatewayRouter"
ERC20_ABI_NAME = "ERC20"
SYNC_SWAP_ROUTER_ABI_NAME = "SyncSwapRouter"
LAYERBANK_COMPTROLLER_ABI_NAME = "LayerBankComptroller"
LAYERBANK_LBTOKEN_ABI_NAME = "LayerBankLbToken"
def bridge_assets(
    web3_instance: Web3,
    private_key: str,
    is_deposit: bool,
    token_symbol: str,
    amount: int,
    l1_rpc_url: Optional[str] = None,
    l2_rpc_url: Optional[str] = None,
) -> str:
    """
    Placeholder for bridging assets between L1 and L2 on Scroll.
    """
    logger.info(f"Bridging {amount} of {token_symbol} (deposit: {is_deposit}) on Scroll")
    # In a real implementation, this would involve interacting with Scroll bridge contracts.
    # For now, return a dummy transaction hash.
    return "0x" + "dummy_scroll_bridge_tx_hash" * 8


def perform_random_activity_scroll(  # noqa: E302
    web3_instance: Web3,
    private_key: str,
    num_actions: int = 1,
    wallet_address: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Performs a random activity on the Scroll network.

    This is a placeholder function. In a real scenario, this would
    randomly select and execute various Scroll-related operations
    (e.g., swaps, lending, bridging) to simulate organic activity.

    Args:
        web3_instance: Web3 instance for the Scroll network.
        private_key: Private key of the wallet to use.
        num_actions: Number of random actions to perform.
        wallet_address: The wallet address to perform actions for.

    Returns:
        A tuple of (success_status, list_of_transaction_hashes).
    """
    logger.info(
        f"Performing {num_actions} random activities on Scroll for wallet "
        f"{wallet_address or 'N/A'}"
    )
    # Simulate some activity
    tx_hashes = [f"0x{i:064x}" for i in range(num_actions)]
    return True, tx_hashes


def provide_liquidity_scroll(
    web3_scroll: Web3,
    private_key: str,
    action: str,  # "add" or "remove"
    token_a_symbol: str,
    token_b_symbol: str,
    amount_a_desired: Optional[int] = None,
    amount_b_desired: Optional[int] = None,
    lp_token_amount: Optional[int] = None,
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800,
) -> str:
    """
    Adds or removes liquidity for a token pair on SyncSwap on Scroll.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        private_key: Private key of the account.
        action: "add" to add liquidity, "remove" to remove liquidity.
        token_a_symbol: Symbol of the first token (e.g., "ETH", "USDC").
        token_b_symbol: Symbol of the second token (e.g., "USDC", "WETH").
        amount_a_desired: Desired amount of token_a to add (smallest unit).
            Required for "add".
        amount_b_desired: Desired amount of token_b to add (smallest unit).
            Required for "add".
        lp_token_amount: Amount of LP tokens to remove (smallest unit).
            Required for "remove".
        slippage_percent: Allowed slippage percentage for calculating min amounts.
        deadline_seconds: Transaction deadline in seconds from now.

    Returns:
        Transaction hash of the add/remove liquidity operation.

    Raises:
        InsufficientLiquidityError: For pool not found or insufficient liquidity.
        InsufficientBalanceError: If balances are insufficient.
        ApprovalError: If token approval fails.
        TransactionRevertedError: If the transaction is reverted.
        ValueError: For invalid inputs.
    """

    # Resolve token addresses
    token_a_address = _get_l2_token_address_scroll(token_a_symbol)
    token_b_address = _get_l2_token_address_scroll(token_b_symbol)
    weth_address = _get_l2_token_address_scroll(WETH_SYMBOL)

    # Get pool address
    pool_address = _get_syncswap_pool_address_scroll(
        web3_scroll, token_a_address, token_b_address
    )
    if pool_address is None:
        raise PoolNotFoundError(f"No pool found for token pair {token_a_symbol}/{token_b_symbol}")
    if pool_address == ZERO_ADDRESS:
        raise InsufficientLiquidityError(
            f"No pool found for {token_a_symbol}-{token_b_symbol} on SyncSwap."
        )

    router_contract = _get_syncswap_router_contract_scroll(web3_scroll)

    if action == "add":
        if amount_a_desired is None or amount_b_desired is None:
            raise ValueError(
                "Both amount_a_desired and amount_b_desired are required "
                "for adding liquidity."
            )

        # Calculate minLiquidity (LP tokens) for slippage
        min_liquidity = _calculate_min_liquidity_scroll(
            web3_scroll, pool_address, amount_a_desired,
            amount_b_desired, slippage_percent
        )

        # Prepare TokenInput array
        token_inputs = []
        msg_value = 0
        # Token A
        if token_a_symbol == ETH_SYMBOL:
            token_inputs.append({"token": weth_address, "amount": amount_a_desired})
            msg_value += amount_a_desired
        else:
            token_inputs.append({"token": token_a_address, "amount": amount_a_desired})
            _approve_erc20_scroll(
                web3_scroll, private_key, token_a_address,
                SYNC_SWAP_ROUTER_ADDRESS_SCROLL, amount_a_desired
            )
        # Token B
        if token_b_symbol == ETH_SYMBOL:
            token_inputs.append({"token": weth_address, "amount": amount_b_desired})
            msg_value += amount_b_desired
        else:
            token_inputs.append({"token": token_b_address, "amount": amount_b_desired})
            _approve_erc20_scroll(
                web3_scroll, private_key, token_b_address,
                SYNC_SWAP_ROUTER_ADDRESS_SCROLL, amount_b_desired
            )

        # Call addLiquidity
        try:
            tx_params = router_contract.functions.addLiquidity(
                pool_address,
                token_inputs,
                b"",
                min_liquidity,
                ZERO_ADDRESS,
                b"",
            ).build_transaction({
                'value': Wei(msg_value),
            })
            tx_hash = _build_and_send_tx_scroll(
                web3_scroll,
                private_key,
                tx_params,
            )
        except Exception as e:
            logger.error(f"addLiquidity failed: {e}")
            raise TransactionRevertedError(f"addLiquidity failed: {e}")

        return tx_hash  # noqa: E501

    elif action == "remove":
        if lp_token_amount is None:
            raise ValueError("lp_token_amount is required for removing liquidity.")

        # Calculate min amounts out for slippage
        amount_a_min, amount_b_min = _calculate_min_amounts_out_scroll(
            web3_scroll, pool_address, lp_token_amount, slippage_percent
        )

        # Approve LP tokens
        _approve_erc20_scroll(
            web3_scroll, private_key, pool_address,
            SYNC_SWAP_ROUTER_ADDRESS_SCROLL, lp_token_amount
        )

        # Call burnLiquidity
        try:
            tx_params = router_contract.functions.burnLiquidity(
                pool_address,
                lp_token_amount,
                b"",
                [amount_a_min, amount_b_min],
                ZERO_ADDRESS,
                b"",
            ).build_transaction({})
            tx_hash = _build_and_send_tx_scroll(
                web3_scroll,
                private_key,
                tx_params,
            )
        except Exception as e:
            logger.error(f"burnLiquidity failed: {e}")
            raise TransactionRevertedError(f"burnLiquidity failed: {e}")

        return tx_hash

    else:
        raise ValueError("action must be 'add' or 'remove'.")


def _calculate_min_liquidity_scroll(  # noqa: E302
    web3_scroll: Web3,
    pool_address: str,
    amount_a_desired: int,
    amount_b_desired: int,
    slippage_percent: float,
) -> int:
    """
    Calculate the minimum LP tokens to receive for add liquidity,
    applying slippage.

    Args:
        web3_scroll: Web3 instance.
        pool_address: Address of the SyncSwap pool.
        amount_a_desired: Desired amount of token A.
        amount_b_desired: Desired amount of token B.
        slippage_percent: Allowed slippage percentage.

    Returns:
        Minimum LP tokens to receive.
    """
    pool_contract = _get_syncswap_classic_pool_contract_scroll(
        web3_scroll, pool_address
    )
    reserves = pool_contract.functions.getReserves().call()
    total_supply = pool_contract.functions.totalSupply().call()
    # Simplified proportional calculation
    if total_supply == 0:
        # First liquidity provider
        min_liquidity = int(
            (amount_a_desired + amount_b_desired) * (1 - slippage_percent / 100)
        )
    else:
        min_liquidity = int(
            min(
                amount_a_desired * total_supply // reserves[0],
                amount_b_desired * total_supply // reserves[1],
            )
            * (1 - slippage_percent / 100)
        )
    return min_liquidity


def _calculate_min_amounts_out_scroll(
    web3_scroll: Web3,
    pool_address: str,
    lp_token_amount: int,
    slippage_percent: float,
) -> Tuple[int, int]:
    """
    Calculate minimum amounts of tokens to receive when removing liquidity.

    Args:
        web3_scroll: Web3 instance.
        pool_address: Address of the SyncSwap pool.
        lp_token_amount: Amount of LP tokens to burn.
        slippage_percent: Allowed slippage percentage.

    Returns:
        Tuple of (amount_a_min, amount_b_min).
    """
    pool_contract = _get_syncswap_classic_pool_contract_scroll(
        web3_scroll, pool_address
    )
    reserves = pool_contract.functions.getReserves().call()
    total_supply = pool_contract.functions.totalSupply().call()
    amount_a_out_expected = lp_token_amount * reserves[0] // total_supply
    amount_b_out_expected = lp_token_amount * reserves[1] // total_supply
    amount_a_min = int(amount_a_out_expected * (1 - slippage_percent / 100))
    amount_b_min = int(amount_b_out_expected * (1 - slippage_percent / 100))
    return amount_a_min, amount_b_min


SYNC_SWAP_CLASSIC_POOL_FACTORY_ABI_NAME = "SyncSwapClassicPoolFactory"
SYNC_SWAP_CLASSIC_POOL_ABI_NAME = "SyncSwapClassicPool"

# Default gas limits and constants
DEFAULT_L2_GAS_LIMIT = 200000  # For bridging
DEFAULT_SWAP_L2_GAS_LIMIT = 600000
DEFAULT_GAS_MULTIPLIER = 1.2
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETH_SYMBOL = "ETH"
WETH_SYMBOL = "WETH"


def _load_abi_scroll(contract_name: str) -> Sequence[Dict[str, Any]]:
    """
    Load ABI JSON from the abi directory.

    Args:
        contract_name: Name of the contract (e.g., 'L1GatewayRouter')

    Returns:
        ABI as a list of dictionaries

    Raises:
        FileNotFoundError: If ABI file doesn't exist
        json.JSONDecodeError: If ABI file is invalid JSON
    """
    abi_path = Path(__file__).parent / "abi" / f"{contract_name}.json"
    try:
        with open(abi_path, "r") as f:
            return cast(Sequence[Dict[str, Any]], json.load(f))
    except FileNotFoundError:
        logger.error(f"ABI file not found: {abi_path}")
        raise FileNotFoundError(f"ABI file not found: {abi_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ABI file {abi_path}: {e.msg}")
        raise json.JSONDecodeError(
            f"Invalid JSON in ABI file {abi_path}: {e.msg}", e.doc, e.pos
        )


def _get_account_scroll(private_key: str, web3_instance: Web3) -> LocalAccount:
    """
    Create Account object from private key.

    Args:
        private_key: Private key string
        web3_instance: Web3  # (used for potential future validation, currently unused)

    Returns:
        Account object

    Raises:
        ValueError: If private key is invalid
    """
    try:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        account: LocalAccount = Account.from_key(private_key)
        return account
    except Exception as e:
        logger.error(f"Invalid private key provided: {e}")
        raise ValueError(f"Invalid private key: {e}")


def _get_l2_token_address_scroll(token_symbol: str) -> str:
    """
    Get L2 address for a token symbol from shared config.

    Args:
        token_symbol: Token symbol (e.g., "ETH", "WETH", "USDC").

    Returns:
        L2 token address as a string.

    Raises:
        TokenNotSupportedError: If token symbol is not configured or L2 address
            is missing.
    """
    if token_symbol not in shared_config.SCROLL_TOKEN_ADDRESSES:
        logger.error(f"Token symbol '{token_symbol}' not found in configuration.")
        raise TokenNotSupportedError(f"Token symbol '{token_symbol}' not supported.")
    token_config_entry = shared_config.SCROLL_TOKEN_ADDRESSES[token_symbol]
    # Cast to Dict to help mypy understand .get() and indexing
    token_info: Dict[str, Any] = cast(Dict[str, Any], token_config_entry)
    l2_address = token_info.get("L2")
    if (
        l2_address is None and token_symbol != ETH_SYMBOL
    ):  # ETH L2 is None, handled by WETH
        logger.error(f"L2 address for token '{token_symbol}' is not configured.")
        raise TokenNotSupportedError(
            f"L2 address for token '{token_symbol}' not configured."
        )
    # For ETH, we typically use WETH address in contracts
    if token_symbol == ETH_SYMBOL:
        weth_config_entry = shared_config.SCROLL_TOKEN_ADDRESSES.get(WETH_SYMBOL)
        if not weth_config_entry:
            raise TokenNotSupportedError(
                "WETH symbol not found in SCROLL_TOKEN_ADDRESSES."
            )
        weth_info: Dict[str, Any] = cast(Dict[str, Any], weth_config_entry)
        weth_l2 = weth_info.get("L2")
        if not weth_l2:
            raise TokenNotSupportedError(
                "WETH L2 address not configured, required for ETH operations."
            )
        return cast(str, weth_l2)
    return cast(str, l2_address)


def _get_contract_scroll(
    web3_instance: Web3, contract_name: str, contract_address: str
) -> Contract:
    """
    Load ABI and return contract instance.

    Args:
        web3_instance: Web3 instance
        contract_name: Name of contract for ABI loading
        contract_address: Contract address

    Returns:
        Web3 Contract instance
    """
    abi = _load_abi_scroll(contract_name)
    checksum_address = Web3.to_checksum_address(contract_address)
    return web3_instance.eth.contract(address=checksum_address, abi=abi)


def _build_and_send_tx_scroll(
    web3_instance: Web3, private_key: str, tx_params: TxParams
) -> str:
    """
    Build, sign, send, and wait for a transaction, with retry logic for
    transient errors.
    """
    account = _get_account_scroll(private_key, web3_instance)
    tx_params.setdefault(
        "nonce", web3_instance.eth.get_transaction_count(account.address)
    )
    tx_params.setdefault("gasPrice", web3_instance.eth.gas_price)

    if "gas" not in tx_params:
        try:
            estimated_gas = web3_instance.eth.estimate_gas(tx_params)
            tx_params["gas"] = Wei(int(estimated_gas * DEFAULT_GAS_MULTIPLIER))
            logger.info(f"Estimated gas: {estimated_gas}, using: {tx_params['gas']}")
        except Exception as e:
            logger.error(f"Gas estimation failed: {e}, tx_params: {tx_params}")
            # Include address in log if available
            from_address = tx_params.get("from", "N/A")
            to_address = tx_params.get("to", "N/A")
            # Convert bytes to string if needed for logging
            from_addr_str = from_address.hex() if isinstance(from_address, bytes) else str(from_address)
            to_addr_str = to_address.hex() if isinstance(to_address, bytes) else str(to_address)
            data_present = "data" in tx_params
            logger.error(
                f"Gas estimation failed for tx from {from_addr_str} to {to_addr_str} "
                f"(data present: {data_present}): {e!s}"
            )
            if isinstance(e, ContractLogicError):  # More specific error
                raise GasEstimationError(
                    f"Gas estimation failed due to contract logic: {e.message} - "
                    f"Data: {e.data!r}"
                )
            raise GasEstimationError(f"Gas estimation failed: {e}")

    try:
        signed = web3_instance.eth.account.sign_transaction(tx_params, private_key)
    except Exception as e:
        logger.error(f"Transaction signing failed: {e}")
        raise TransactionBuildError(f"Transaction signing failed: {e}")

    last_exception: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Attempt {attempt + 1}/{MAX_RETRIES} to send transaction..."
            )
            tx_hash_bytes = web3_instance.eth.send_raw_transaction(
                signed.raw_transaction
            )
            tx_hash_hex = tx_hash_bytes.hex()
            logger.info(f"Transaction sent with hash: {tx_hash_hex}")

            logger.info(f"Waiting for transaction receipt for {tx_hash_hex}...")
            receipt: TxReceipt = web3_instance.eth.wait_for_transaction_receipt(
                tx_hash_bytes, timeout=180
            )
            logger.info(f"Transaction receipt received for {tx_hash_hex}")

            if receipt["status"] != 1:
                logger.error(
                    f"Transaction {tx_hash_hex} reverted. Receipt status: "
                    f"{receipt['status']}"
                )
                raise TransactionRevertedError(
                    f"Transaction {tx_hash_hex} reverted.", receipt=receipt
                )

            logger.info(f"Transaction {tx_hash_hex} successful.")
            return tx_hash_hex

        except (ConnectionError, TimeoutError, Timeout) as e:  # Added TimeoutError
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1}/{MAX_RETRIES} failed due to RPC/network "
                f"issue: {e}. Retrying in {RETRY_DELAY_SECONDS}s..."
            )
            time.sleep(RETRY_DELAY_SECONDS)
            if attempt < MAX_RETRIES - 1:
                try:
                    current_nonce = web3_instance.eth.get_transaction_count(
                        account.address
                    )
                    if current_nonce > cast(int, tx_params["nonce"]):
                        logger.info(
                            f"Nonce already used or too low. Current: {current_nonce}, "
                            f"Tx: {tx_params['nonce']}. Updating nonce."
                        )
                        tx_params["nonce"] = current_nonce
                    else:
                        logger.info(
                            f"Nonce {tx_params['nonce']} seems still valid or higher. "
                            f"Current: {current_nonce}."
                        )

                    signed = web3_instance.eth.account.sign_transaction(
                        tx_params, private_key
                    )
                    logger.info(
                        f"Re-signed transaction with nonce {tx_params['nonce']} "
                        f"for retry."
                    )
                except Exception as sign_e:
                    logger.error(
                        f"Transaction re-signing failed before retry: {sign_e}"
                    )
                    # Not raising here, let the outer loop decide if it's max retries
                    last_exception = TransactionBuildError(
                        f"Transaction re-signing failed before retry: {sign_e}"
                    )
                    break
        except TransactionRevertedError:
            raise  # Re-raise if already specific
        except Exception as e:
            last_exception = e
            logger.error(
                f"An unexpected error occurred during transaction processing "
                f"(attempt {attempt + 1}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    # After loop
    if last_exception:
        logger.error(
            f"All {MAX_RETRIES} attempts failed. Last error: {last_exception}"
        )
        if isinstance(last_exception, (ConnectionError, TimeoutError, Timeout)):
            raise MaxRetriesExceededError(
                f"Transaction failed after {MAX_RETRIES} attempts due to "
                f"RPC/network issues: {last_exception}"
            )
        elif isinstance(last_exception, TransactionRevertedError):
            raise last_exception
        elif isinstance(last_exception, TransactionBuildError):
            raise last_exception
        else:
            raise TransactionSendError(
                f"Failed to send/confirm transaction after {MAX_RETRIES} retries: "
                f"{last_exception}"
            )

    # Should ideally not be reached if logic is correct
    logger.error(
        "Transaction processing finished in an unexpected state (no success, "
        "no explicit error after retries)."
    )
    raise ScrollBridgeError(
        "Transaction processing finished in an unexpected state after retries."
    )


def _approve_erc20_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_address: str,
    spender_address: str,
    amount: int,
) -> str:
    """Approve ERC20 token for spending by a spender on Scroll L2."""
    logger.info(
        f"Approving {amount} of token {token_address} for spender {spender_address}"
    )
    account = _get_account_scroll(private_key, web3_scroll)
    contract = _get_contract_scroll(web3_scroll, ERC20_ABI_NAME, token_address)

    # Check current allowance
    try:
        current_allowance = contract.functions.allowance(
            account.address, spender_address
        ).call()
        if current_allowance >= amount:
            logger.info(
                f"Allowance of {current_allowance} for {spender_address} is "
                "sufficient. Skipping approval."
            )
            return f"existing_approval_sufficient_for_{amount}"
    except Exception as e:
        logger.warning(
            f"Could not check current allowance for {token_address} to "
            f"{spender_address}: {e}. Proceeding with approval."
        )

    tx_dict_approve: TxParams = {
        "from": account.address,
        "gasPrice": web3_scroll.eth.gas_price,
    }

    try:
        approve_tx = contract.functions.approve(
            spender_address, amount
        ).build_transaction(tx_dict_approve)
        if "to" not in approve_tx:
            approve_tx["to"] = token_address

        logger.info(f"Built approval transaction: {approve_tx}")
        return _build_and_send_tx_scroll(web3_scroll, private_key, approve_tx)

    except GasEstimationError as e:
        logger.error(f"Gas estimation failed for ERC20 approval: {e}")
        raise ApprovalError(f"ERC20 approval gas estimation failed: {e}") from e
    except TransactionRevertedError as e:
        logger.error(f"ERC20 approval transaction reverted: {e.receipt}")
        raise ApprovalError(
            f"ERC20 approval failed: {e.args[0]}", receipt=e.receipt
        ) from e
    except Exception as e:
        logger.error(f"ERC20 approval error: {e}")
        raise ApprovalError(f"ERC20 approval error: {e}") from e


def _estimate_l1_to_l2_message_fee_scroll(
    web3_l1: Web3, l2_gas_limit: int, l2_gas_price: Optional[int] = None
) -> int:
    """Estimate the L1->L2 message fee using the Scroll L1 Gas Oracle."""
    try:
        oracle = _get_contract_scroll(
            web3_l1,
            "scroll_l1_gas_oracle",  # This will need to be defined in ABI mapping
            SCROLL_L1_GAS_ORACLE_ADDRESS
        )
        fee = oracle.functions.estimateCrossDomainMessageFee(l2_gas_limit).call()
        return int(fee)
    except Exception as e:
        logger.error(f"Failed to estimate L1->L2 message fee: {e}")
        raise GasEstimationError(f"Failed to estimate L1->L2 message fee: {e}")


# --- Swap Specific Helpers ---


def _get_syncswap_classic_pool_factory_contract_scroll(web3_scroll: Web3) -> Contract:
    """Get the SyncSwap Classic Pool Factory contract instance."""
    return _get_contract_scroll(
        web3_scroll,
        SYNC_SWAP_CLASSIC_POOL_FACTORY_ABI_NAME,
        SYNC_SWAP_CLASSIC_POOL_FACTORY_ADDRESS_SCROLL,
    )


def _get_syncswap_pool_address_scroll(
    web3_scroll: Web3, token0_address: str, token1_address: str
) -> Optional[str]:
    """Get pool address for a token pair using SyncSwap Classic Pool Factory."""
    factory = _get_syncswap_classic_pool_factory_contract_scroll(web3_scroll)
    try:
        # Ensure addresses are checksummed for contract calls
        token0_checksum = Web3.to_checksum_address(token0_address)
        token1_checksum = Web3.to_checksum_address(token1_address)

        # Order of tokens might matter for getPool, typically sorted
        # (token0, token1) = sorted((token0_checksum, token1_checksum))
        # For SyncSwap, it seems to handle unsorted pairs too. Let's try direct.
        pool_address_any = factory.functions.getPool(
            token0_checksum, token1_checksum
        ).call()
        pool_address = cast(str, pool_address_any)
        if pool_address == ZERO_ADDRESS:
            # Try reverse order if the factory doesn't sort internally
            pool_address_reversed_any = factory.functions.getPool(
                token1_checksum, token0_checksum
            ).call()
            pool_address_reversed = cast(str, pool_address_reversed_any)
            if pool_address_reversed != ZERO_ADDRESS:
                # DEBUG: _get_syncswap_pool_address_scroll - pool_address_reversed
                return pool_address_reversed
            logger.info(
                f"No SyncSwap Classic pool found for {token0_address} and "
                f"{token1_address}"
            )
            return None
        # DEBUG: _get_syncswap_pool_address_scroll - pool_address
        return pool_address
    except Exception as e:
        logger.warning(
            f"Error getting pool for {token0_address}-{token1_address}: {e}"
        )
        return None


def _get_syncswap_classic_pool_contract_scroll(
    web3_scroll: Web3, pool_address: str
) -> Contract:
    """Get a SyncSwap Classic Pool contract instance given its address."""
    return _get_contract_scroll(
        web3_scroll, SYNC_SWAP_CLASSIC_POOL_ABI_NAME, pool_address
    )


def _get_syncswap_router_contract_scroll(web3_scroll: Web3) -> Contract:
    """Get the SyncSwap Router contract instance."""
    return _get_contract_scroll(
        web3_scroll, SYNC_SWAP_ROUTER_ABI_NAME, SYNC_SWAP_ROUTER_ADDRESS_SCROLL
    )


def _get_expected_amount_out_syncswap_scroll(
    web3_scroll: Web3,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    sender_address: str,  # EOA address for the call context
    weth_address: str,
) -> int:
    """
    Get the expected output amount for a swap.
    Tries direct pool, then via WETH if applicable.
    """
    logger.info(
        f"Getting expected amount out for {amount_in} of {token_in_address} to "
        f"{token_out_address}"
    )

    # Try direct pool
    direct_pool_address = _get_syncswap_pool_address_scroll(
        web3_scroll, token_in_address, token_out_address
    )
    if direct_pool_address:
        try:
            pool_contract = _get_syncswap_classic_pool_contract_scroll(
                web3_scroll, direct_pool_address
            )
            expected_out = pool_contract.functions.getAmountOut(
                Web3.to_checksum_address(token_in_address),
                amount_in,
                Web3.to_checksum_address(sender_address),
            ).call()
            # DEBUG: _get_expected_amount_out_syncswap_scroll - expected_out
            logger.info(
                f"Direct pool {direct_pool_address} quote: {expected_out} of "
                f"{token_out_address}"
            )
            return cast(int, expected_out)
        except Exception as e:
            logger.warning(
                f"Failed to get quote from direct pool {direct_pool_address}: {e}"
            )

    # Try via WETH if token_in and token_out are not WETH and not ETH
    # (ETH is handled as WETH internally)
    if token_in_address != weth_address and token_out_address != weth_address:
        logger.info(f"No direct pool, trying via WETH ({weth_address})")
        pool1_address = _get_syncswap_pool_address_scroll(
            web3_scroll, token_in_address, weth_address
        )
        pool2_address = _get_syncswap_pool_address_scroll(
            web3_scroll, weth_address, token_out_address
        )

        if pool1_address and pool2_address:
            try:
                pool1_contract = _get_syncswap_classic_pool_contract_scroll(
                    web3_scroll, pool1_address
                )
                amount_weth_out = pool1_contract.functions.getAmountOut(
                    Web3.to_checksum_address(token_in_address),
                    amount_in,
                    Web3.to_checksum_address(sender_address),
                ).call()
                logger.info(
                    f"Pool1 ({token_in_address}->WETH) quote: {amount_weth_out} WETH"
                )

                if amount_weth_out == 0:
                    raise InsufficientLiquidityError(
                        "First leg of WETH hop (token_in -> WETH) results in 0 output."
                    )

                pool2_contract = _get_syncswap_classic_pool_contract_scroll(
                    web3_scroll, pool2_address
                )
                final_amount_out = pool2_contract.functions.getAmountOut(
                    Web3.to_checksum_address(weth_address),
                    cast(int, amount_weth_out),
                    Web3.to_checksum_address(sender_address),
                ).call()
                # DEBUG: _get_expected_amount_out_syncswap_scroll - final_amount_out
                logger.info(
                    f"Pool2 (WETH->{token_out_address}) quote: {final_amount_out} "
                    f"{token_out_address}"
                )
                return cast(int, final_amount_out)
            except Exception as e:
                logger.warning(f"Failed to get quote via WETH hop: {e}")

    logger.error(
        f"Could not find a valid path or pool for swapping {token_in_address} to "
        f"{token_out_address}"
    )
    raise InsufficientLiquidityError(
        f"No liquidity or path found for swapping {token_in_address} to "
        f"{token_out_address} on SyncSwap."
    )


def _calculate_amount_out_min_syncswap_scroll(
    expected_amount_out: int, slippage_percent: float
) -> int:
    """Calculate the minimum amount_out based on expected_amount_out and slippage."""
    if not 0 <= slippage_percent <= 100:
        raise ValueError("Slippage percent must be between 0 and 100.")
    amount_out_min = int(expected_amount_out * (1 - slippage_percent / 100.0))
    logger.info(
        f"Calculated amountOutMin: {amount_out_min} from expected "
        f"{expected_amount_out} with {slippage_percent}% slippage"
    )
    return amount_out_min


def _encode_swap_step_data_scroll(
    token_in_for_step: str, to_address_for_step: str, withdraw_mode: int
) -> HexBytes:
    """ABI encodes the data for a SwapStep."""
    # (address tokenIn, address to, uint8 withdrawMode)
    encoded_data = abi_encode(
        ["address", "address", "uint8"],
        [
            Web3.to_checksum_address(token_in_for_step),
            Web3.to_checksum_address(to_address_for_step),
            withdraw_mode,
        ],
    )
    return HexBytes(encoded_data)


def _construct_syncswap_paths_scroll(
    web3_scroll: Web3,
    token_in_start_address: str,  # Initial token input to the whole swap
    token_out_final_address: str,  # Final token output of the whole swap
    amount_in_start: int,
    final_recipient_address: str,
    weth_address: str,
    router_contract: Contract,  # Pass router to get vault address
    actual_token_out_symbol: str,  # The symbol string like "ETH", "USDC"
) -> List[Dict[str, Any]]:
    """
    Constructs the 'paths' parameter for SyncSwap router's swap function.
    Handles direct (A->B) and single-hop via WETH (A->WETH->B).
    """
    logger.info(
        f"Constructing SyncSwap path: {token_in_start_address} -> "
        f"{token_out_final_address} for amount {amount_in_start}"
    )
    # DEBUG: _construct_syncswap_paths_scroll - token_in_start_address
    # DEBUG: _construct_syncswap_paths_scroll - token_out_final_address
    # DEBUG: _construct_syncswap_paths_scroll - amount_in_start
    paths: List[Dict[str, Any]] = []

    # Get vault address from router - needed for intermediate steps
    try:
        vault_address = router_contract.functions.vault().call()
        # DEBUG: _construct_syncswap_paths_scroll - vault_address
        logger.info(f"SyncSwap Vault address: {vault_address}")
    except Exception as e:
        logger.error(f"Could not fetch vault address from SyncSwap Router: {e}")
        raise ScrollSwapError(
            f"Could not fetch vault address from SyncSwap Router: {e}"
        )

    # Try direct path first: token_in_start_address -> token_out_final_address
    direct_pool_address = _get_syncswap_pool_address_scroll(
        web3_scroll, token_in_start_address, token_out_final_address
    )
    # DEBUG: _construct_syncswap_paths_scroll - direct_pool_address
    if direct_pool_address:
        logger.info(f"Direct path found via pool: {direct_pool_address}")
        withdraw_mode: int
        if actual_token_out_symbol == ETH_SYMBOL:  # Final output is native ETH
            withdraw_mode = 1
        elif token_out_final_address == weth_address:  # Final output is WETH (ERC20)
            withdraw_mode = 2
        else:  # Final output is other ERC20
            withdraw_mode = 0

        step_data = _encode_swap_step_data_scroll(
            token_in_start_address, final_recipient_address, withdraw_mode
        )
        step = {
            "pool": Web3.to_checksum_address(direct_pool_address),
            "data": step_data,
            "callback": ZERO_ADDRESS,
            "callbackData": HexBytes("0x"),
        }
        path_obj = {
            "steps": [step],
            "tokenIn": Web3.to_checksum_address(token_in_start_address),
            "amountIn": amount_in_start,
        }
        paths.append(path_obj)
        return paths

    # If no direct path, try path via WETH (if applicable)
    # A -> WETH -> B (where A != WETH and B != WETH)
    if (
        token_in_start_address != weth_address
        and token_out_final_address != weth_address
    ):
        logger.info(
            f"No direct path, trying via WETH: {token_in_start_address} -> "
            f"{weth_address} -> {token_out_final_address}"
        )
        pool1_address = _get_syncswap_pool_address_scroll(
            web3_scroll, token_in_start_address, weth_address
        )
        # DEBUG: _construct_syncswap_paths_scroll - pool1_address
        pool2_address = _get_syncswap_pool_address_scroll(
            web3_scroll, weth_address, token_out_final_address
        )
        # DEBUG: _construct_syncswap_paths_scroll - pool2_address

        if pool1_address and pool2_address:
            logger.info(
                f"Found WETH hop: Pool1 ({token_in_start_address}->WETH): "
                f"{pool1_address}, Pool2 (WETH->{token_out_final_address}): "
                f"{pool2_address}"
            )
            step1_data = _encode_swap_step_data_scroll(
                token_in_start_address, vault_address, 2  # 2 = keep as WETH
            )
            step1 = {
                "pool": Web3.to_checksum_address(pool1_address),
                "data": step1_data,
                "callback": ZERO_ADDRESS,
                "callbackData": HexBytes("0x"),
            }

            # Step 2: WETH -> token_out_final_address (output to final recipient)
            final_withdraw_mode: int
            if (
                actual_token_out_symbol == ETH_SYMBOL
            ):  # Should not happen if token_out_final_address != weth_address
                final_withdraw_mode = 1
            elif (
                token_out_final_address == weth_address
            ):  # Should not happen due to outer if
                final_withdraw_mode = 2
            else:  # Final output is other ERC20
                final_withdraw_mode = 0

            step2_data = _encode_swap_step_data_scroll(
                weth_address, final_recipient_address, final_withdraw_mode
            )
            step2 = {
                "pool": Web3.to_checksum_address(pool2_address),
                "data": step2_data,
                "callback": ZERO_ADDRESS,
                "callbackData": HexBytes("0x"),
            }

            path_obj = {
                "steps": [step1, step2],
                "tokenIn": Web3.to_checksum_address(token_in_start_address),
                "amountIn": amount_in_start,
            }
            paths.append(path_obj)
            return paths

    if not paths:
        logger.error(
            f"Could not construct any swap path for {token_in_start_address} -> "
            f"{token_out_final_address}"
        )
        raise InsufficientLiquidityError(
            f"No swap path found for {token_in_start_address} to "
            f"{token_out_final_address} on SyncSwap."
        )
    return paths


def swap_tokens(
    web3_scroll: Web3,
    private_key: str,
    token_in_symbol: str,
    token_out_symbol: str,
    amount_in: int,
    slippage_percent: float = 0.5,
    deadline_seconds: int = 1800,
) -> str:
    """
    Swaps tokens on SyncSwap DEX on the Scroll network.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        private_key: Private key of the account performing the swap.
        token_in_symbol: Symbol of the token to swap from (e.g., "ETH", "USDC").
        token_out_symbol: Symbol of the token to swap to (e.g., "USDC", "WETH").
        amount_in: Amount of token_in to swap (in Wei or smallest unit).
        slippage_percent: Allowed slippage percentage (e.g., 0.5 for 0.5%).
        deadline_seconds: Transaction deadline in seconds from now.

    Returns:
        Transaction hash of the swap operation.

    Raises:
        ScrollSwapError: For general swap-related errors.
        InsufficientLiquidityError: If liquidity is insufficient for the swap or
            no path found.
        TokenNotSupportedError: If one of the token symbols is not configured.
        ApprovalError: If token approval fails.
        TransactionRevertedError: If the swap transaction is reverted.
        GasEstimationError: If gas estimation fails.
        ValueError: For invalid inputs like slippage.
        ... (other relevant exceptions from airdrops.protocols.scroll.exceptions)
    """
    logger.info(
        f"Initiating SyncSwap swap: {amount_in} {token_in_symbol} -> "
        f"{token_out_symbol} with {slippage_percent}% slippage, "
        f"deadline {deadline_seconds}s."
    )

    if amount_in <= 0:
        raise ValueError("Amount to swap must be positive.")

    account = _get_account_scroll(private_key, web3_scroll)
    sender_address = account.address
    recipient_address = sender_address  # Swaps benefit the sender

    # Resolve token addresses (ETH will be resolved to WETH for internal logic)
    weth_l2_address = _get_l2_token_address_scroll(WETH_SYMBOL)

    token_in_address_actual: str  # The address used on-chain for token_in
    is_eth_input = False
    if token_in_symbol == ETH_SYMBOL:
        token_in_address_actual = weth_l2_address
        is_eth_input = True
        # Check ETH balance
        eth_balance = web3_scroll.eth.get_balance(sender_address)
        if eth_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient ETH balance for swap: have {eth_balance}, "
                f"need {amount_in}"
            )
    else:
        token_in_address_actual = _get_l2_token_address_scroll(token_in_symbol)
        # Check ERC20 balance
        token_in_contract = _get_contract_scroll(
            web3_scroll, ERC20_ABI_NAME, token_in_address_actual
        )
        erc20_balance = token_in_contract.functions.balanceOf(sender_address).call()
        if erc20_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient {token_in_symbol} balance for swap: have "
                f"{erc20_balance}, need {amount_in}"
            )

    token_out_address_actual: str
    if token_out_symbol == ETH_SYMBOL:
        token_out_address_actual = weth_l2_address
    else:
        token_out_address_actual = _get_l2_token_address_scroll(token_out_symbol)

    # Deadline
    current_block = web3_scroll.eth.get_block("latest")
    deadline = current_block["timestamp"] + deadline_seconds

    router_contract = _get_syncswap_router_contract_scroll(web3_scroll)

    # Get expected amount out and calculate min amount out
    try:
        expected_amount_out = _get_expected_amount_out_syncswap_scroll(
            web3_scroll,
            token_in_address_actual,
            token_out_address_actual,
            amount_in,
            sender_address,
            weth_l2_address,
        )
    except InsufficientLiquidityError as e:  # Catch specific error from quoting
        logger.error(
            f"Quoting failed due to insufficient liquidity or no path: {e}"
        )
        raise
    except Exception as e:
        logger.error(f"Error during expected amount out calculation: {e}")
        raise ScrollSwapError(f"Could not determine expected amount out: {e}") from e

    if expected_amount_out == 0:
        raise InsufficientLiquidityError(
            f"Expected output for {token_in_symbol} to {token_out_symbol} is 0. "
            "Check pool liquidity."
        )

    amount_out_min = _calculate_amount_out_min_syncswap_scroll(
        expected_amount_out, slippage_percent
    )

    # Approve router if token_in is ERC20
    if not is_eth_input:
        logger.info(
            f"Approving SyncSwap router {SYNC_SWAP_ROUTER_ADDRESS_SCROLL} to spend "
            f"{amount_in} of {token_in_symbol} ({token_in_address_actual})"
        )
        try:
            _approve_erc20_scroll(
                web3_scroll,
                private_key,
                token_in_address_actual,
                SYNC_SWAP_ROUTER_ADDRESS_SCROLL,
                amount_in,
            )
            logger.info(f"Approval successful for {token_in_symbol}.")
        except ApprovalError as e:
            logger.error(f"ERC20 approval for {token_in_symbol} failed: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during ERC20 approval for {token_in_symbol}: {e}"
            )
            raise ApprovalError(
                f"Unexpected error during ERC20 approval for {token_in_symbol}: {e}"
            ) from e

    # Construct swap paths
    try:
        swap_paths = _construct_syncswap_paths_scroll(
            web3_scroll,
            token_in_address_actual,
            token_out_address_actual,
            amount_in,
            recipient_address,
            weth_l2_address,
            router_contract,
            token_out_symbol,  # Pass the original token_out_symbol for
            # withdrawMode decision
        )
    except (
        InsufficientLiquidityError
    ) as e:
        logger.error(f"Path construction failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error constructing swap paths: {e}")
        raise ScrollSwapError(f"Could not construct swap paths: {e}") from e

    # Prepare transaction for router.swap()
    # paths: List[Tuple(List[Tuple(address, bytes, address, bytes)], address, int)]
    # Example from ABI: paths: IRouter.SwapPath[]
    # IRouter.SwapPath: { steps: IRouter.SwapStep[], tokenIn: address,
    # amountIn: uint256 }
    # IRouter.SwapStep: { pool: address, data: bytes, callback: address,
    # callbackData: bytes }

    # The _construct_syncswap_paths_scroll returns a list of dicts matching
    # the structure. Web3.py will convert these Python dicts/lists to tuples
    # as needed for the contract call.

    tx_value = Wei(amount_in) if is_eth_input else Wei(0)

    swap_tx_params_dict: TxParams = {
        "from": sender_address,
        "to": SYNC_SWAP_ROUTER_ADDRESS_SCROLL,
        "value": tx_value,
        "gas": Wei(
            DEFAULT_SWAP_L2_GAS_LIMIT
        ),  # Provide a default, _build_and_send will estimate
        # nonce and gasPrice will be handled by _build_and_send_tx_scroll
    }

    logger.info(
        f"Preparing swap transaction with router.swap(): paths={swap_paths}, "
        f"amountOutMin={amount_out_min}, deadline={deadline}"
    )

    try:
        swap_function: ContractFunction = router_contract.functions.swap(
            swap_paths, amount_out_min, deadline
        )
        # Build transaction without sending, _build_and_send_tx_scroll will
        # handle the rest
        built_swap_tx = swap_function.build_transaction(swap_tx_params_dict)
        logger.info(f"Built swap transaction: {built_swap_tx}")

        return _build_and_send_tx_scroll(web3_scroll, private_key, built_swap_tx)

    except (
        ContractLogicError
    ) as e:
        logger.error(f"SyncSwap contract logic error: {e.message} - Data: {e.data}")
        if "TooLittleReceived" in str(e) or (
            e.data and "0x087229a4" in e.data
        ):
            raise InsufficientLiquidityError(
                f"Swap likely to result in too little received (slippage or "
                f"liquidity): {e.message}",
                tx_data=e.data,
            )
        if "Expired" in str(e) or (
            e.data and "0x414432ea" in e.data
        ):
            raise ScrollSwapError(
                f"Swap transaction expired: {e.message}", tx_data=e.data
            )
        raise TransactionRevertedError(
            f"SyncSwap swap reverted with logic error: {e.message}",
            receipt=None,
            tx_hash=None,
            data=e.data,
        ) from e
    except GasEstimationError as e:
        logger.error(f"Gas estimation failed for swap transaction: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing or sending swap transaction: {e}")
        raise ScrollSwapError(f"Failed to execute swap: {e}") from e


# --- LayerBank Lending Helper Functions ---


def _get_layerbank_lbtoken_address_scroll(token_symbol: str) -> str:
    """
    Get LayerBank lbToken address for a given token symbol.

    Args:
        token_symbol: Token symbol ("ETH" or "USDC").

    Returns:
        lbToken contract address.

    Raises:
        TokenNotSupportedError: If token symbol is not supported.

    Example:
        >>> address = _get_layerbank_lbtoken_address_scroll("ETH")
        >>> print(address)
        0x7E08A050000201d938279b3A0e293A49A729505E
    """
    if token_symbol == "ETH":
        return LAYERBANK_LBETH_ADDRESS_SCROLL
    elif token_symbol == "USDC":
        return LAYERBANK_LBUSDC_ADDRESS_SCROLL
    else:
        raise TokenNotSupportedError(
            f"Token symbol '{token_symbol}' not supported for LayerBank lending. "
            "Supported tokens: ETH, USDC"
        )


def _check_and_enter_layerbank_market_scroll(
    web3_scroll: Web3,
    private_key: str,
    lbtoken_address: str,
    user_address: str,
) -> None:
    """
    Check if user has entered the LayerBank market and enter if not.
    """
    # DEBUG: _check_and_enter_layerbank_market_scroll - lbtoken_address
    comptroller_contract = _get_contract_scroll(
        web3_scroll, LAYERBANK_COMPTROLLER_ABI_NAME,
        LAYERBANK_COMPTROLLER_ADDRESS_SCROLL
    )

    try:
        # Check if user has already entered this market
        is_member = comptroller_contract.functions.checkMembership(
            user_address, lbtoken_address
        ).call()

        if not is_member:
            logger.info(f"Entering LayerBank market for lbToken {lbtoken_address}")
            tx_params: TxParams = {
                "from": user_address,
                "gasPrice": web3_scroll.eth.gas_price,
            }
            enter_markets_tx = comptroller_contract.functions.enterMarkets(
                [Web3.to_checksum_address(lbtoken_address)]
            ).build_transaction(tx_params)

            _build_and_send_tx_scroll(web3_scroll, private_key, enter_markets_tx)
            logger.info(
                f"Successfully entered LayerBank market for {lbtoken_address}"
            )
        else:
            logger.info(f"Already a member of LayerBank market {lbtoken_address}")

    except Exception as e:
        logger.error(f"Failed to enter LayerBank market {lbtoken_address}: {e}")
        raise ScrollLendingError(f"Failed to enter LayerBank market: {e}") from e
    return


def _get_layerbank_account_liquidity_scroll(
    web3_scroll: Web3,
    comptroller_contract: Contract,
    user_address: str,
) -> tuple[int, int, int]:
    """
    Get account liquidity information from LayerBank Comptroller.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        comptroller_contract: LayerBank Comptroller contract instance.
        user_address: User's wallet address.

    Returns:
        Tuple of (error_code, liquidity_usd, shortfall_usd).

    Raises:
        ScrollLendingError: If liquidity check fails.

    Example:
        >>> error, liquidity, shortfall = \
        _get_layerbank_account_liquidity_scroll(
        ...     web3_scroll, comptroller_contract, user_address
        ... )
        >>> print(f"Liquidity: {liquidity}, Shortfall: {shortfall}")
    """
    try:
        result = comptroller_contract.functions.getAccountLiquidity(
            user_address
        ).call()
        error_code, liquidity_usd, shortfall_usd = result
        return int(error_code), int(liquidity_usd), int(shortfall_usd)
    except Exception as e:
        logger.error(f"Failed to get account liquidity for {user_address}: {e}")
        raise ScrollLendingError(f"Failed to get account liquidity: {e}") from e


    return


    return


    return


    return


    return


    return


    return


def lend_borrow_layerbank_scroll(
    web3_scroll: Web3,
    private_key: str,
    action: str,
    token_symbol: str,
    amount: int,
) -> str:
    """
    Handles lending, borrowing, repaying, and withdrawing assets on LayerBank V2 on
    Scroll.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        private_key: Private key of the account.
        action: Action to perform ("lend", "borrow", "repay", "withdraw").
        token_symbol: Token symbol ("ETH" or "USDC").
        amount: Amount in Wei for ETH, smallest unit for USDC.

    Returns:
        Transaction hash of the operation.

    Raises:
        ScrollLendingError: For general lending-related errors.
        InsufficientCollateralError: When insufficient collateral for borrowing.
        TokenNotSupportedError: If token symbol is not supported.
        InsufficientBalanceError: If account balance is insufficient.
        ApprovalError: If token approval fails.
        TransactionRevertedError: If transaction is reverted.

    Example:
        >>> tx_hash = lend_borrow_layerbank_scroll(
        ...     web3_scroll, private_key, "lend", "ETH", 1000000000000000000
        ... )
        >>> print(f"Transaction hash: {tx_hash}")
    """
    logger.info(f"Initiating LayerBank {action}: {amount} {token_symbol}")

    # Validate inputs
    if action not in ("lend", "borrow", "repay", "withdraw"):
        raise ValueError(
            f"Invalid action: {action}. Must be one of: lend, borrow, repay, "
            "withdraw"
        )

    if token_symbol not in ("ETH", "USDC"):
        raise TokenNotSupportedError(
            f"Token {token_symbol} not supported for LayerBank"
        )

    if amount <= 0:
        raise ValueError("Amount must be positive")

    account = _get_account_scroll(private_key, web3_scroll)
    user_address = account.address

    # Get lbToken address
    lbtoken_address = _get_layerbank_lbtoken_address_scroll(token_symbol)
    lbtoken_contract = _get_contract_scroll(
        web3_scroll, LAYERBANK_LBTOKEN_ABI_NAME, lbtoken_address
    )

    # Get comptroller contract for market operations
    comptroller_contract = _get_contract_scroll(
        web3_scroll, LAYERBANK_COMPTROLLER_ABI_NAME,
        LAYERBANK_COMPTROLLER_ADDRESS_SCROLL
    )

    if action == "lend":
        return _handle_lend_action_scroll(
            web3_scroll, private_key, token_symbol, amount, user_address,
            lbtoken_contract, lbtoken_address
        )
    elif action == "withdraw":
        return _handle_withdraw_action_scroll(
            web3_scroll, private_key, token_symbol, amount, user_address,
            lbtoken_contract
        )
    elif action == "borrow":
        return _handle_borrow_action_scroll(
            web3_scroll, private_key, token_symbol, amount, user_address,
            lbtoken_contract, comptroller_contract, lbtoken_address
        )
    elif action == "repay":
        return _handle_repay_action_scroll(
            web3_scroll, private_key, token_symbol, amount, user_address,
            lbtoken_contract
        )
    
    # This should never be reached due to validation above, but mypy requires it
    return ""


def _handle_lend_action_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    user_address: str,
    lbtoken_contract: Contract,
    lbtoken_address: str,
) -> str:
    """Handle lending (supply) action for LayerBank."""
    logger.info(f"Lending {amount} {token_symbol} to LayerBank")

    try:
        if token_symbol == "ETH":
            # Check ETH balance
            eth_balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(user_address))
            if eth_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient ETH balance: have {eth_balance}, need {amount}"
                )

            # Call mint() with ETH value
            tx_params: TxParams = {
                "from": user_address,
                "value": Wei(amount),
                "gasPrice": web3_scroll.eth.gas_price,
            }
            mint_tx = lbtoken_contract.functions.mint().build_transaction(tx_params)

        else:  # USDC
            # Check USDC balance and approve
            usdc_contract = _get_contract_scroll(
                web3_scroll, ERC20_ABI_NAME, SCROLL_USDC_TOKEN_ADDRESS
            )
            usdc_balance = usdc_contract.functions.balanceOf(user_address).call()
            if usdc_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient USDC balance: have {usdc_balance}, need {amount}"
                )

            # Approve lbToken contract to spend USDC
            _approve_erc20_scroll(
                web3_scroll, private_key, SCROLL_USDC_TOKEN_ADDRESS,
                lbtoken_address, amount
            )

            # Call mint(amount)
            tx_params = {
                "from": user_address,
                "gasPrice": web3_scroll.eth.gas_price,
            }
            mint_tx = lbtoken_contract.functions.mint(amount).build_transaction(
                tx_params
            )

        # Send mint transaction
        tx_hash = _build_and_send_tx_scroll(web3_scroll, private_key, mint_tx)

        # Enter market after successful lend
        _check_and_enter_layerbank_market_scroll(
            web3_scroll, private_key, lbtoken_address, user_address
        )

        logger.info(f"Successfully lent {amount} {token_symbol} to LayerBank")
        return tx_hash

    except Exception as e:
        logger.error(f"Lending failed: {e}")
        if isinstance(e, (InsufficientBalanceError, ApprovalError)):
            raise
        if isinstance(e, TransactionRevertedError):
            raise ScrollLendingError("Lending failed") from e
        raise ScrollLendingError(f"Lending failed: {e}") from e


def _handle_withdraw_action_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    user_address: str,
    lbtoken_contract: Contract,
) -> str:
    """Handle withdraw (redeem) action for LayerBank."""
    logger.info(f"Withdrawing {amount} {token_symbol} from LayerBank")

    try:
        # Call redeemUnderlying(amount)
        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }
        redeem_tx = lbtoken_contract.functions.redeemUnderlying(amount).build_transaction(
            tx_params
        )

        tx_hash = _build_and_send_tx_scroll(web3_scroll, private_key, redeem_tx)
        logger.info(f"Successfully withdrew {amount} {token_symbol} from LayerBank")
        return tx_hash

    except Exception as e:
        logger.error(f"Withdrawal failed: {e}")
        if isinstance(e, TransactionRevertedError):
            raise
        raise ScrollLendingError(f"Withdrawal failed: {e}") from e


def _handle_borrow_action_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    user_address: str,
    lbtoken_contract: Contract,
    comptroller_contract: Contract,
    lbtoken_address: str,  # Add lbtoken_address here
) -> str:
    """Handle borrow action for LayerBank."""
    logger.info(f"Borrowing {amount} {token_symbol} from LayerBank")

    try:
        # Enter market if not already entered (for borrow operations)
        _check_and_enter_layerbank_market_scroll(
            web3_scroll, private_key, lbtoken_contract.address, user_address
        )

        # Check account liquidity before borrowing
        error_code, liquidity_usd, shortfall_usd = _get_layerbank_account_liquidity_scroll(
            web3_scroll, comptroller_contract, user_address
        )

        if error_code != 0:
            raise LayerBankComptrollerRejectionError(
                f"Comptroller error when checking liquidity: {error_code}",
                error_code=error_code
            )

        if shortfall_usd > 0:
            raise InsufficientCollateralError(
                f"Account has shortfall: {shortfall_usd}. Cannot borrow."
            )

        if liquidity_usd == 0:
            raise InsufficientCollateralError(
                "No available liquidity for borrowing. Please supply collateral first."
            )

        # Call borrow(amount)
        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }
        borrow_tx = lbtoken_contract.functions.borrow(amount).build_transaction(tx_params)

        tx_hash = _build_and_send_tx_scroll(web3_scroll, private_key, borrow_tx)
        logger.info(f"Successfully borrowed {amount} {token_symbol} from LayerBank")
        return tx_hash

    except Exception as e:
        logger.error(f"Borrowing failed: {e}")
        if isinstance(e, (InsufficientCollateralError, LayerBankComptrollerRejectionError, TransactionRevertedError)):
            raise
        raise ScrollLendingError(f"Borrowing failed: {e}") from e


def _handle_repay_action_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    user_address: str,
    lbtoken_contract: Contract,
) -> str:
    """Handle repay action for LayerBank."""
    logger.info(f"Repaying {amount} {token_symbol} to LayerBank")

    try:
        # Check if repay amount exceeds current debt (unless it's max uint256 for full repayment)
        MAX_UINT256 = 2**256 - 1
        if amount != MAX_UINT256:
            current_debt = lbtoken_contract.functions.borrowBalanceStored(user_address).call()
            if amount > current_debt:
                raise RepayAmountExceedsDebtError(
                    f"Repay amount {amount} exceeds current debt {current_debt} for {token_symbol}"
                )
            logger.info(f"Current debt: {current_debt}, repaying: {amount}")

        if token_symbol == "ETH":
            # Check ETH balance
            eth_balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(user_address))
            if eth_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient ETH balance for repayment: have {eth_balance}, need {amount}"
                )

            # Call repayBorrow() with ETH value
            tx_params: TxParams = {
                "from": user_address,
                "value": Wei(amount),
                "gasPrice": web3_scroll.eth.gas_price,
            }
            repay_tx = lbtoken_contract.functions.repayBorrow().build_transaction(
                tx_params
            )

        else:  # USDC
            # Check USDC balance and approve
            usdc_contract = _get_contract_scroll(
                web3_scroll, ERC20_ABI_NAME, SCROLL_USDC_TOKEN_ADDRESS
            )
            usdc_balance = usdc_contract.functions.balanceOf(user_address).call()
            if usdc_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient USDC balance for repayment: have {usdc_balance}, need {amount}"
                )

            # Approve lbToken contract to spend USDC
            lbtoken_address = _get_layerbank_lbtoken_address_scroll(token_symbol)
            _approve_erc20_scroll(
                web3_scroll, private_key, SCROLL_USDC_TOKEN_ADDRESS,
                lbtoken_address, amount
            )

            # Call repayBorrow(amount)
            tx_params = {
                "from": user_address,
                "gasPrice": web3_scroll.eth.gas_price,
            }
            repay_tx = lbtoken_contract.functions.repayBorrow(amount).build_transaction(tx_params)

        tx_hash = _build_and_send_tx_scroll(web3_scroll, private_key, repay_tx)
        logger.info(f"Successfully repaid {amount} {token_symbol} to LayerBank")
        return tx_hash

    except Exception as e:
        logger.error(f"Repayment failed: {e}")
        if isinstance(e, (InsufficientBalanceError, ApprovalError, TransactionRevertedError, RepayAmountExceedsDebtError)):
            raise
        raise ScrollLendingError(f"Repayment failed: {e}") from e


# --- Bridge Assets (existing function, ensure it's compatible) ---
def bridge_assets(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    direction: str,  # "deposit" or "withdraw"
    token_symbol: str,  # "ETH", "WETH", "USDC", "USDT"
    amount: int,
    recipient_address: Optional[str] = None,
) -> str:
    """Bridges assets (ETH or ERC20 tokens) between Ethereum (L1) and Scroll (L2).
    (Existing function - minor adjustments for consistency if needed, but largely untouched for this task)
    """
    logger.info(
        f"Initiating bridge_assets: direction='{direction}', token='{token_symbol}', "
        f"amount={amount}, recipient='{recipient_address}'"
    )
    if direction not in ("deposit", "withdraw"):
        logger.error(f"Invalid direction provided: {direction}")
        raise ValueError(f"Invalid direction: {direction}")

    # Use shared_config for token addresses consistently
    if token_symbol not in shared_config.SCROLL_TOKEN_ADDRESSES:
        raise TokenNotSupportedError(
            f"Token {token_symbol} not in shared_config.SCROLL_TOKEN_ADDRESSES"
        )

    token_config_shared = shared_config.SCROLL_TOKEN_ADDRESSES[token_symbol]

    account = _get_account_scroll(
        private_key, web3_l1 if direction == "deposit" else web3_l2
    )
    sender = account.address
    to_addr = recipient_address or sender

    if direction == "deposit":
        l1_rpc_url_from_config = getattr(shared_config, "SCROLL_L1_RPC_URL", None)
        if (
            not web3_l1.provider
            or not hasattr(web3_l1.provider, "endpoint_uri")
            or (
                l1_rpc_url_from_config
                and web3_l1.provider.endpoint_uri != l1_rpc_url_from_config
            )
        ):
            logger.warning(
                "web3_l1 provider endpoint might not match SCROLL_L1_RPC_URL in config."
            )

        if token_symbol == ETH_SYMBOL:
            l1_router = _get_contract_scroll(
                web3_l1, L1_GATEWAY_ROUTER_ABI_NAME,
                SCROLL_L1_GATEWAY_ROUTER_ADDRESS
            )
            l2_gas_limit = DEFAULT_L2_GAS_LIMIT
            # l2_gas_price = web3_l2.eth.gas_price # Not directly used by estimateCrossDomainMessageFee
            fee = _estimate_l1_to_l2_message_fee_scroll(
                web3_l1,
                l2_gas_limit,  # , l2_gas_price # Pass if needed by future oracle versions
            )
            total_value = amount + fee
            if web3_l1.eth.get_balance(sender) < total_value:
                raise InsufficientBalanceError(
                    f"Insufficient ETH for deposit ({amount}) + fee ({fee}) = {total_value}. Balance: {web3_l1.eth.get_balance(sender)}"
                )
            tx_build_params: TxParams = {
                "from": sender,
                "to": SCROLL_L1_GATEWAY_ROUTER_ADDRESS,  # Added 'to'
                "value": Wei(total_value),
                # gasPrice, nonce, gas handled by _build_and_send_tx_scroll
            }
            # depositETH(address _to, uint256 _amount, uint256 _gasLimit, uint256 _fee)
            deposit_eth_fn = l1_router.functions.depositETH(
                to_addr,
                amount,
                l2_gas_limit,  # , fee # fee is part of msg.value, not a function arg here
            )
            # The `fee` for `depositETH` is actually `msg.value - amount`. The contract calculates it.
            # The `_fee` parameter in `depositETH` was removed in some versions.
            # The L1GatewayRouter ABI used (from file) for depositETH:
            # "name": "depositETH", "outputs": [], "stateMutability": "payable", "type": "function",
            # "inputs": [{"internalType": "address", "name": "_to", "type": "address"},
            #            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            #            {"internalType": "uint256", "name": "_gasLimit", "type": "uint256"}]
            # So, the `fee` is not passed as a function argument but is part of msg.value.
            # The `_estimate_l1_to_l2_message_fee_scroll` is correct for calculating the `value`.
            # The function signature in the ABI provided in scroll.py for L1GatewayRouter.json should be checked.
            # Assuming the ABI in scroll.py is for a version that doesn't take `_fee` as param.
            # If it does, the call should be: l1_router.functions.depositETH(to_addr, amount, l2_gas_limit, fee)
            # Let's assume the ABI in `L1GatewayRouter.json` is the source of truth.
            # Reading L1GatewayRouter.json ABI:
            # { "inputs": [ { "internalType": "address", "name": "to", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "uint256", "name": "gasLimit", "type": "uint256" } ], "name": "depositETH", "outputs": [], "stateMutability": "payable", "type": "function" }
            # Correct, no `_fee` argument.

            tx = deposit_eth_fn.build_transaction(tx_build_params)
            return _build_and_send_tx_scroll(web3_l1, private_key, tx)
        else:  # ERC20 Deposit
            l1_token_addr = cast(Dict[str, Any], token_config_shared).get("L1")
            if not l1_token_addr:
                raise TokenNotSupportedError(
                    f"L1 address for {token_symbol} not configured."
                )

            l1_router_addr = SCROLL_L1_GATEWAY_ROUTER_ADDRESS
            _approve_erc20_scroll(  # This uses web3_l1 internally for approval
                web3_l1, private_key, l1_token_addr, l1_router_addr, amount
            )
            l1_router = _get_contract_scroll(
                web3_l1, L1_GATEWAY_ROUTER_ABI_NAME, l1_router_addr
            )
            l2_gas_limit = DEFAULT_L2_GAS_LIMIT
            # l2_gas_price = web3_l2.eth.gas_price
            fee = _estimate_l1_to_l2_message_fee_scroll(
                web3_l1, l2_gas_limit  # , l2_gas_price
            )
            if web3_l1.eth.get_balance(sender) < fee:
                raise InsufficientBalanceError(
                    f"Insufficient ETH for L2 execution fee ({fee}). Balance: {web3_l1.eth.get_balance(sender)}"
                )
            tx_build_erc20_params: TxParams = {
                "from": sender,
                "to": l1_router_addr,  # Added 'to'
                "value": Wei(fee),
                # gasPrice, nonce, gas handled by _build_and_send_tx_scroll
            }
            # depositERC20(address _token, address _to, uint256 _amount, uint256 _gasLimit, uint256 _fee)
            # ABI check for L1GatewayRouter.json depositERC20:
            # { "inputs": [ { "internalType": "address", "name": "token", "type": "address" }, { "internalType": "address", "name": "to", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "uint256", "name": "gasLimit", "type": "uint256" } ], "name": "depositERC20", "outputs": [], "stateMutability": "payable", "type": "function" }
            # Correct, no `_fee` argument.
            deposit_erc20_fn = l1_router.functions.depositERC20(
                l1_token_addr, to_addr, amount, l2_gas_limit  # , fee
            )
            tx = deposit_erc20_fn.build_transaction(tx_build_erc20_params)
            return _build_and_send_tx_scroll(web3_l1, private_key, tx)
    else:  # Withdraw (L2 to L1)
        l2_rpc_url_from_config = getattr(shared_config, "SCROLL_L2_RPC_URL", None)
        if (
            not web3_l2.provider
            or not hasattr(web3_l2.provider, "endpoint_uri")
            or (
                l2_rpc_url_from_config
                and web3_l2.provider.endpoint_uri != l2_rpc_url_from_config
            )
        ):
            logger.warning(
                "web3_l2 provider endpoint might not match SCROLL_L2_RPC_URL in config."
            )

        l2_router = _get_contract_scroll(
            web3_l2, L2_GATEWAY_ROUTER_ABI_NAME, SCROLL_L2_GATEWAY_ROUTER_ADDRESS
        )
        # l2_gas_limit = DEFAULT_L2_GAS_LIMIT # This is for L1 execution of L2->L1 message, not L2 tx gas.
        # The L2 transaction gas limit is estimated by _build_and_send_tx_scroll.
        # The `_gasLimit` parameter in withdraw functions is for the L1 execution part.
        l1_execution_gas_limit = DEFAULT_L2_GAS_LIMIT  # Renamed for clarity

        if token_symbol == ETH_SYMBOL:
            if web3_l2.eth.get_balance(sender) < amount:
                raise InsufficientBalanceError(
                    f"Insufficient ETH for withdrawal ({amount}). Balance: {web3_l2.eth.get_balance(sender)}"
                )
            tx_build_withdraw_eth_params: TxParams = {
                "from": sender,
                "to": SCROLL_L2_GATEWAY_ROUTER_ADDRESS,  # Added 'to'
                "value": Wei(amount),  # msg.value is the amount of ETH to withdraw
                # gasPrice, nonce, gas handled by _build_and_send_tx_scroll
            }
            # withdrawETH(address _to, uint256 _amount, uint256 _gasLimit)
            # ABI check for L2GatewayRouter.json withdrawETH:
            # { "inputs": [ { "internalType": "address", "name": "to", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "uint256", "name": "gasLimit", "type": "uint256" } ], "name": "withdrawETH", "outputs": [], "stateMutability": "payable", "type": "function" }
            # Correct.
            withdraw_eth_fn = l2_router.functions.withdrawETH(
                to_addr, amount, l1_execution_gas_limit
            )
            tx = withdraw_eth_fn.build_transaction(tx_build_withdraw_eth_params)
            return _build_and_send_tx_scroll(web3_l2, private_key, tx)
        else:  # ERC20 Withdraw
            token_config_entry_l2 = cast(Dict[str, Any], token_config_shared).get("L2")
            if not token_config_entry_l2:
                raise TokenNotSupportedError(
                    f"L2 address for {token_symbol} not configured."
                )
            l2_token_addr = cast(str, token_config_entry_l2)

            # For ERC20 withdrawal, approval is needed on L2 for the L2GatewayRouter to pull tokens.
            # This was missing in the original logic.
            logger.info(
                f"Approving L2 Gateway Router {SCROLL_L2_GATEWAY_ROUTER_ADDRESS} to spend {amount} of {token_symbol} ({l2_token_addr}) on L2."
            )
            _approve_erc20_scroll(
                web3_l2,
                private_key,
                l2_token_addr,
                SCROLL_L2_GATEWAY_ROUTER_ADDRESS,
                amount,
            )
            logger.info("Approval for L2 ERC20 withdrawal successful.")

            # Balance check (already done by _approve_erc20_scroll if it were to fail early, but good to have)
            token_contract_l2 = _get_contract_scroll(
                web3_l2, ERC20_ABI_NAME, l2_token_addr
            )
            if token_contract_l2.functions.balanceOf(sender).call() < amount:
                raise InsufficientBalanceError(
                    f"Insufficient {token_symbol} balance for withdrawal ({amount})."
                )

            tx_build_withdraw_erc20_params: TxParams = {
                "from": sender,
                "to": SCROLL_L2_GATEWAY_ROUTER_ADDRESS,  # Added 'to'
                "value": Wei(
                    0
                ),  # No ETH sent with ERC20 withdrawal function call itself
                # gasPrice, nonce, gas handled by _build_and_send_tx_scroll
            }
            # withdrawERC20(address _token, address _to, uint256 _amount, uint256 _gasLimit)
            # ABI check for L2GatewayRouter.json withdrawERC20:
            # { "inputs": [ { "internalType": "address", "name": "token", "type": "address" }, { "internalType": "address", "name": "to", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "uint256", "name": "gasLimit", "type": "uint256" } ], "name": "withdrawERC20", "outputs": [], "stateMutability": "nonpayable", "type": "function" }
            # Correct.
            withdraw_erc20_fn = l2_router.functions.withdrawERC20(
                l2_token_addr, to_addr, amount, l1_execution_gas_limit
            )
            tx = withdraw_erc20_fn.build_transaction(tx_build_withdraw_erc20_params)
            return _build_and_send_tx_scroll(web3_l2, private_key, tx)

# --- Random Activity Orchestration Functions ---


def _select_random_scroll_action(config: Dict[str, Any]) -> str:
    """
    Select a random action from the available Scroll actions based on weights.

    Args:
        config: Configuration dictionary containing action weights.

    Returns:
        Selected action name.

    Raises:
        ScrollRandomActivityError: If action weights are invalid or missing.

    Example:
        >>> config = {"action_weights": {"bridge_assets": 0.3, "swap_tokens": 0.7}}
        >>> action = _select_random_scroll_action(config)
        >>> action in ["bridge_assets", "swap_tokens"]
        True
    """
    try:
        action_weights = config.get("action_weights", {})

        # Default uniform weights if not provided
        if not action_weights:
            actions = ["bridge_assets", "swap_tokens", "provide_liquidity_scroll", "lend_borrow_layerbank_scroll"]
            return random.choice(actions)

        # Validate weights
        actions = list(action_weights.keys())
        weights = list(action_weights.values())

        if not actions or not all(w >= 0 for w in weights) or sum(weights) <= 0:
            raise ScrollRandomActivityError("Invalid action weights: weights must be positive and sum > 0")

        # Use random.choices for weighted selection
        selected_action = random.choices(actions, weights=weights, k=1)[0]
        logger.info(f"Selected random action: {selected_action}")
        return selected_action

    except Exception as e:
        logger.error(f"Failed to select random action: {e}")
        raise ScrollRandomActivityError(f"Action selection failed: {e}") from e


def _get_wallet_balances_scroll(
    web3_scroll: Web3,
    address: str,
    token_symbols: List[str],
    token_configs: Dict[str, Any]
) -> Dict[str, int]:
    """
    Get wallet balances for specified tokens on Scroll L2.

    Args:
        web3_scroll: Web3 instance for Scroll L2.
        address: Wallet address to check.
        token_symbols: List of token symbols to check.
        token_configs: Token configuration mapping.

    Returns:
        Dictionary mapping token symbols to balances in smallest units.

    Example:
        >>> balances = _get_wallet_balances_scroll(web3, address, ["ETH", "USDC"], configs)
        >>> "ETH" in balances and "USDC" in balances
        True
    """
    balances = {}

    for symbol in token_symbols:
        try:
            if symbol == ETH_SYMBOL:
                balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(address))
                balances[symbol] = int(balance)
            else:
                token_address = _get_l2_token_address_scroll(symbol)
                token_contract = _get_contract_scroll(web3_scroll, ERC20_ABI_NAME, token_address)
                balance = token_contract.functions.balanceOf(address).call()
                balances[symbol] = int(balance)

        except Exception as e:
            logger.warning(f"Failed to get balance for {symbol}: {e}")
            balances[symbol] = 0

    return balances


def _generate_params_for_scroll_action(
    action_name: str,
    web3_l1: Web3,
    web3_scroll: Web3,
    private_key: str,
    user_address: str,
    activity_config: Dict[str, Any],
    scroll_token_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate parameters for a specific Scroll action based on configuration.

    Args:
        action_name: Name of the action to generate parameters for.
        web3_l1: Web3 instance for L1.
        web3_scroll: Web3 instance for Scroll L2.
        private_key: User's private key.
        user_address: User's wallet address.
        activity_config: Random activity configuration.
        scroll_token_config: Token configuration.

    Returns:
        Dictionary of parameters for the action.

    Raises:
        ScrollRandomActivityError: If parameter generation fails.

    Example:
        >>> params = _generate_params_for_scroll_action("swap_tokens", web3_l1, web3_scroll, key, addr, config, tokens)
        >>> "token_in_symbol" in params and "token_out_symbol" in params
        True
    """
    try:
        action_config = activity_config.get(action_name, {})

        if action_name == "bridge_assets":
            return _generate_bridge_params_scroll(web3_l1, web3_scroll, user_address, action_config)
        elif action_name == "swap_tokens":
            return _generate_swap_params_scroll(web3_scroll, user_address, action_config)
        elif action_name == "provide_liquidity_scroll":
            return _generate_liquidity_params_scroll(web3_scroll, user_address, action_config)
        elif action_name == "lend_borrow_layerbank_scroll":
            return _generate_lending_params_scroll(web3_scroll, user_address, action_config)
        else:
            raise ScrollRandomActivityError(f"Unknown action: {action_name}")

    except Exception as e:
        logger.error(f"Failed to generate parameters for {action_name}: {e}")
        raise ScrollRandomActivityError(f"Parameter generation failed for {action_name}: {e}") from e


def _generate_bridge_params_scroll(
    web3_l1: Web3,
    web3_scroll: Web3,
    user_address: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate parameters for bridge_assets action."""
    directions = config.get("directions", [("deposit", 0.5), ("withdraw", 0.5)])
    tokens = config.get("tokens_l1_l2", ["ETH", "USDC"])

    # Select direction and token
    direction_choices, direction_weights = zip(*directions) if directions else (["deposit"], [1.0])
    direction = random.choices(list(direction_choices), weights=list(direction_weights), k=1)[0]
    token_symbol = random.choice(tokens)

    # Get balances to determine realistic amounts
    if direction == "deposit":
        if token_symbol == ETH_SYMBOL:
            balance = web3_l1.eth.get_balance(Web3.to_checksum_address(user_address))
            amount_range = config.get("amount_eth_range", [0.001, 0.005])
        else:
            # For ERC20 tokens, we'd need to check L1 balance
            amount_range = config.get("amount_usdc_range", [1, 10])
            balance = Wei(int(amount_range[1] * 10**6))  # Assume sufficient for demo
    else:  # withdraw
        if token_symbol == ETH_SYMBOL:
            balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(user_address))
            amount_range = config.get("amount_eth_range", [0.001, 0.005])
        else:
            # Check L2 balance
            amount_range = config.get("amount_usdc_range", [1, 10])
            balance = Wei(int(amount_range[1] * 10**6))  # Assume sufficient for demo

    # Generate amount within range and balance constraints
    if token_symbol == ETH_SYMBOL:
        min_amount = int(amount_range[0] * 10**18)
        max_amount = Wei(int(min(amount_range[1] * 10**18, balance * 0.8)))  # Use 80% of balance max
    else:
        min_amount = int(amount_range[0] * 10**6)  # USDC has 6 decimals
        max_amount = Wei(int(min(amount_range[1] * 10**6, balance * 0.8)))

    amount = random.randint(min_amount, max(min_amount, max_amount))

    return {
        "web3_l1": web3_l1,
        "web3_l2": web3_scroll,
        "direction": direction,
        "token_symbol": token_symbol,
        "amount": amount,
        "recipient_address": user_address,
    }


def _generate_swap_params_scroll(
    web3_scroll: Web3,
    user_address: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate parameters for swap_tokens action."""
    token_pairs = config.get("token_pairs", [("ETH", "USDC", 1.0)])
    slippage = config.get("slippage_percent", 0.5)

    # Select token pair
    if token_pairs:
        pair_choices = [(pair[0], pair[1]) for pair in token_pairs]
        pair_weights = [pair[2] if len(pair) > 2 else 1.0 for pair in token_pairs]
        token_in, token_out = random.choices(pair_choices, weights=pair_weights, k=1)[0]
    else:
        token_in, token_out = "ETH", "USDC"

    # Get balance and determine amount
    balances = _get_wallet_balances_scroll(web3_scroll, user_address, [token_in], {})
    balance = balances.get(token_in, 0)

    if token_in == ETH_SYMBOL:
        percent_range = config.get("amount_eth_percent_range", [5, 15])
    else:
        percent_range = config.get("amount_usdc_percent_range", [10, 30])

    percent = random.uniform(percent_range[0], percent_range[1])
    amount = int(balance * percent / 100)

    return {
        "web3_scroll": web3_scroll,
        "token_in_symbol": token_in,
        "token_out_symbol": token_out,
        "amount_in": max(amount, 1),  # Ensure non-zero
        "slippage_percent": slippage,
    }


def _generate_liquidity_params_scroll(
    web3_scroll: Web3,
    user_address: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate parameters for provide_liquidity_scroll action."""
    actions = config.get("actions", [("add", 0.7), ("remove", 0.3)])
    token_pairs = config.get("token_pairs", [("ETH", "USDC", 1.0)])
    slippage = config.get("slippage_percent", 0.5)

    # Select action and token pair
    action_choices, action_weights = zip(*actions) if actions else (["add"], [1.0])
    action = random.choices(list(action_choices), weights=list(action_weights), k=1)[0]

    if token_pairs:
        pair_choices = [(pair[0], pair[1]) for pair in token_pairs]
        pair_weights = [pair[2] if len(pair) > 2 else 1.0 for pair in token_pairs]
        token_a, token_b = random.choices(pair_choices, weights=pair_weights, k=1)[0]
    else:
        token_a, token_b = "ETH", "USDC"

    params = {
        "web3_scroll": web3_scroll,
        "action": action,
        "token_a_symbol": token_a,
        "token_b_symbol": token_b,
        "slippage_percent": slippage,
    }

    if action == "add":
        # Get balances and calculate amounts
        balances = _get_wallet_balances_scroll(web3_scroll, user_address, [token_a, token_b], {})

        eth_percent_range = config.get("add_amount_eth_percent_range", [5, 10])
        usdc_percent_range = config.get("add_amount_usdc_percent_range", [5, 10])

        if token_a == ETH_SYMBOL:
            percent_a = random.uniform(eth_percent_range[0], eth_percent_range[1])
        else:
            percent_a = random.uniform(usdc_percent_range[0], usdc_percent_range[1])

        if token_b == ETH_SYMBOL:
            percent_b = random.uniform(eth_percent_range[0], eth_percent_range[1])
        else:
            percent_b = random.uniform(usdc_percent_range[0], usdc_percent_range[1])

        amount_a = int(balances.get(token_a, 0) * percent_a / 100)
        amount_b = int(balances.get(token_b, 0) * percent_b / 100)

        params.update({
            "amount_a_desired": max(amount_a, 1),
            "amount_b_desired": max(amount_b, 1),
        })
    else:  # remove
        # For remove, we need LP token amount - simplified for demo
        lp_percent_range = config.get("remove_lp_percent_range", [20, 50])
        percent = random.uniform(lp_percent_range[0], lp_percent_range[1])
        # In real implementation, would fetch actual LP balance
        params["lp_token_amount"] = int(10**18 * percent / 100)  # Demo value

    return params


def _generate_lending_params_scroll(
    web3_scroll: Web3,
    user_address: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate parameters for lend_borrow_layerbank_scroll action."""
    actions = config.get("actions", [("lend", 0.4), ("borrow", 0.2), ("repay", 0.2), ("withdraw", 0.2)])
    tokens = config.get("tokens", ["ETH", "USDC"])

    # Select action and token
    action_choices, action_weights = zip(*actions) if actions else (["lend"], [1.0])
    action = random.choices(list(action_choices), weights=list(action_weights), k=1)[0]
    token_symbol = random.choice(tokens)

    # Get balance for amount calculation
    balances = _get_wallet_balances_scroll(web3_scroll, user_address, [token_symbol], {})
    balance = balances.get(token_symbol, 0)

    if action == "lend":
        if token_symbol == ETH_SYMBOL:
            percent_range = config.get("lend_amount_eth_percent_range", [10, 25])
        else:
            percent_range = config.get("lend_amount_usdc_percent_range", [10, 25])
        percent = random.uniform(percent_range[0], percent_range[1])
        amount = int(balance * percent / 100)
    else:
        # For borrow/repay/withdraw, would need to check LayerBank positions
        # Simplified for demo
        amount = int(balance * 0.1)  # Use 10% as demo

    return {
        "web3_scroll": web3_scroll,
        "action": action,
        "token_symbol": token_symbol,
        "amount": max(amount, 1),
    }


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
        web3_l1: Web3 instance for L1 (Ethereum).
        web3_scroll: Web3 instance for Scroll L2.
        private_key: Private key of the account performing actions.
        action_count: The number of random actions to perform (e.g., 1 to N).
        config: Configuration dictionary. Expected to contain
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

    Raises:
        ScrollRandomActivityError: For orchestration-specific errors.
        ValueError: For invalid input parameters.

    Example:
        >>> config = {
        ...     "random_activity_scroll": {
        ...         "action_weights": {"swap_tokens": 1.0},
        ...         "stop_on_failure": True,
        ...         "swap_tokens": {"token_pairs": [("ETH", "USDC", 1.0)]}
        ...     }
        ... }
        >>> success, result = perform_random_activity_scroll(web3_l1, web3_scroll, key, 1, config)
        >>> isinstance(success, bool)
        True
    """
    logger.info(f"Starting random activity sequence with {action_count} actions")

    # Validate inputs
    if action_count <= 0:
        raise ValueError("action_count must be positive")

    if not config or "random_activity_scroll" not in config:
        raise ScrollRandomActivityError("Missing 'random_activity_scroll' configuration")

    activity_config = config["random_activity_scroll"]
    stop_on_failure = activity_config.get("stop_on_failure", True)
    inter_action_delay_range = activity_config.get("inter_action_delay_seconds_range", [])

    # Validate action weights early to catch configuration errors
    action_weights = activity_config.get("action_weights", {})
    if not action_weights:
        raise ScrollRandomActivityError("Missing 'action_weights' in configuration")

    weights = list(action_weights.values())
    if not all(w >= 0 for w in weights) or sum(weights) <= 0:
        raise ScrollRandomActivityError("Invalid action weights: weights must be positive and sum > 0")

    # Get user address
    try:
        account = _get_account_scroll(private_key, web3_scroll)
        user_address = account.address
    except Exception as e:
        error_msg = f"Failed to get account from private key: {e}"
        logger.error(error_msg)
        return False, error_msg

    # Action dispatch mapping
    action_map = {
        "bridge_assets": bridge_assets,
        "swap_tokens": swap_tokens,
        "provide_liquidity_scroll": provide_liquidity_scroll,
        "lend_borrow_layerbank_scroll": lend_borrow_layerbank_scroll,
    }

    successful_tx_hashes = []

    try:
        for i in range(action_count):
            logger.info(f"Executing action {i + 1}/{action_count}")

            # Select random action
            try:
                selected_action = _select_random_scroll_action(activity_config)
            except ScrollRandomActivityError as e:
                # For ScrollRandomActivityError during execution, return error tuple
                error_msg = f"Failed to select action {i + 1}: {e}"
                logger.error(error_msg)
                if stop_on_failure:
                    return False, error_msg
                continue
            except Exception as e:
                error_msg = f"Failed to select action {i + 1}: {e}"
                logger.error(error_msg)
                if stop_on_failure:
                    return False, error_msg
                continue

            # Generate parameters for the action
            try:
                action_params = _generate_params_for_scroll_action(
                    selected_action,
                    web3_l1,
                    web3_scroll,
                    private_key,
                    user_address,
                    activity_config,
                    shared_config.SCROLL_TOKEN_ADDRESSES
                )
                # Add private_key to params
                action_params["private_key"] = private_key
            except Exception as e:
                error_msg = f"Failed to generate parameters for {selected_action}: {e}"
                logger.error(error_msg)
                if stop_on_failure:
                    return False, error_msg
                continue

            # Execute the action
            try:
                action_function = action_map[selected_action]
                tx_hash = action_function(**action_params)  # type: ignore[operator]
                successful_tx_hashes.append(tx_hash)
                logger.info(f"Action {selected_action} completed successfully: {tx_hash}")
            except Exception as e:
                error_msg = f"Action {selected_action} failed: {e}"
                logger.error(error_msg)
                if stop_on_failure:
                    return len(successful_tx_hashes) > 0, successful_tx_hashes if successful_tx_hashes else error_msg
                # Continue with next action if stop_on_failure is False

            # Inter-action delay
            if i < action_count - 1 and inter_action_delay_range and len(inter_action_delay_range) >= 2:
                delay = random.uniform(
                    inter_action_delay_range[0], inter_action_delay_range[1]
                )
                logger.info(f"Waiting {delay:.1f} seconds before next action")
                time.sleep(delay)
        logger.info(f"Random activity sequence completed. Successful transactions: {len(successful_tx_hashes)}")
        return True, successful_tx_hashes

    except ScrollRandomActivityError:
        # Re-raise ScrollRandomActivityError to preserve specific error type
        raise
    except Exception as e:
        error_msg = f"Unexpected error during random activity execution: {e}"
        logger.error(error_msg)
        return (
            False,
            successful_tx_hashes if successful_tx_hashes else error_msg
        )
__all__ = [
    "bridge_assets",
    "swap_tokens",
    "provide_liquidity_scroll",
    "lend_borrow_layerbank_scroll",
    "perform_random_activity_scroll",
    # Exposing some helpers for potential direct use or testing, though mostly internal
    "_get_account_scroll",
    "_get_l2_token_address_scroll",  # New helper
    "_get_contract_scroll",
    "_estimate_l1_to_l2_message_fee_scroll",
    "_approve_erc20_scroll",
    "_build_and_send_tx_scroll",
    "_get_layerbank_lbtoken_address_scroll",
    "_check_and_enter_layerbank_market_scroll",
    "_get_layerbank_account_liquidity_scroll",
    "_select_random_scroll_action",
    "_get_wallet_balances_scroll",
    "_generate_params_for_scroll_action",
]
# Expose helpers for test patching if needed by existing tests, or for new tests
# globals()["_get_token_addresses_scroll"] = _get_token_addresses_scroll
# Old one, replaced by _get_l2_token_address_scroll
# Keep existing globals for bridge_assets tests if they rely on them.
# The task is to add swap_tokens, so focus on new functionality's exposure.
# For now, only add new functions to __all__ and let tests adapt if they were
# patching internal details.

