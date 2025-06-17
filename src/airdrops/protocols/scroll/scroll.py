"""
Scroll Protocol Module.

This module provides functionalities to interact with the Scroll network,
including bridging ETH and ERC20 tokens between Ethereum (L1) and Scroll (L2),
and swapping tokens on SyncSwap DEX (L2).
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Any, cast, Sequence, List
from requests.exceptions import ConnectionError, Timeout

from eth_abi.abi import encode as abi_encode
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
    ScrollLendingError,
    InsufficientCollateralError,
    RepayAmountExceedsDebtError,
    LayerBankComptrollerRejectionError,
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


def _get_l1_token_address_scroll(token_symbol: str) -> str:
    """
    Get L1 address for a token symbol from shared config.

    Args:
    token_symbol: Token symbol (e.g., "USDC").

    Returns:
    L1 token address as a string.

    Raises:
    TokenNotSupportedError: If token symbol is not configured or L1 address
            is missing.
    """
    if token_symbol not in shared_config.SCROLL_TOKEN_ADDRESSES:
        logger.error(f"Token symbol '{token_symbol}' not found in configuration.")
        raise TokenNotSupportedError(f"Token symbol '{token_symbol}' not supported.")
    token_config_entry = shared_config.SCROLL_TOKEN_ADDRESSES[token_symbol]
    token_info: Dict[str, Any] = cast(Dict[str, Any], token_config_entry)
    l1_address = token_info.get("L1")
    if l1_address is None:
        logger.error(f"L1 address for token '{token_symbol}' is not configured.")
        raise TokenNotSupportedError(
            f"L1 address for token '{token_symbol}' not configured."
        )
    return cast(str, l1_address)


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
            from_addr_str = (
                from_address.hex()
                if isinstance(from_address, bytes)
                else str(from_address)
            )
            to_addr_str = (
                to_address.hex() if isinstance(to_address, bytes) else str(to_address)
            )
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

        except (ConnectionError, TimeoutError, Timeout) as e:
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
                    last_exception = TransactionBuildError(
                        f"Transaction re-signing failed before retry: {sign_e}"
                    )
                    break
        except TransactionRevertedError:
            raise
        except Exception as e:
            last_exception = e
            logger.error(
                f"An unexpected error occurred during transaction processing "
                f"(attempt {attempt + 1}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

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

    logger.error(
        "Transaction processing finished in an unexpected state (no success, "
        "no explicit error after retries."
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
            "scroll_l1_gas_oracle",
            SCROLL_L1_GAS_ORACLE_ADDRESS
        )
        fee = oracle.functions.estimateCrossDomainMessageFee(l2_gas_limit).call()
        return int(fee)
    except Exception as e:
        logger.error(f"Failed to estimate L1->L2 message fee: {e}")
        raise GasEstimationError(f"Failed to estimate L1->L2 message fee: {e}")


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
        token0_checksum = Web3.to_checksum_address(token0_address)
        token1_checksum = Web3.to_checksum_address(token1_address)

        pool_address_any = factory.functions.getPool(
            token0_checksum, token1_checksum
        ).call()
        pool_address = cast(str, pool_address_any)
        if pool_address == ZERO_ADDRESS:
            pool_address_reversed_any = factory.functions.getPool(
                token1_checksum, token0_checksum
            ).call()
            pool_address_reversed = cast(str, pool_address_reversed_any)
            if pool_address_reversed != ZERO_ADDRESS:
                return pool_address_reversed
            logger.info(
                f"No SyncSwap Classic pool found for {token0_checksum} and "
                f"{token1_checksum}"
            )
            return None
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
    sender_address: str,
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
            logger.info(
                f"Direct pool {direct_pool_address} quote: {expected_out} of "
                f"{token_out_address}"
            )
            return cast(int, expected_out)
        except Exception as e:
            logger.warning(
                f"Failed to get quote from direct pool {direct_pool_address}: {e}"
            )

    if (
        token_in_address != weth_address
        and token_out_address != weth_address
    ):
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
    token_in_start_address: str,
    token_out_final_address: str,
    amount_in_start: int,
    final_recipient_address: str,
    weth_address: str,
    router_contract: Contract,
    actual_token_out_symbol: str,
) -> List[Dict[str, Any]]:
    """
    Constructs the 'paths' parameter for SyncSwap router's swap function.
    Handles direct (A->B) and single-hop via WETH (A->WETH->B).
    """
    logger.info(
        f"Constructing SyncSwap path: {token_in_start_address} -> "
        f"{token_out_final_address} for amount {amount_in_start}"
    )
    paths: List[Dict[str, Any]] = []

    try:
        vault_address = router_contract.functions.vault().call()
        logger.info(f"SyncSwap Vault address: {vault_address}")
    except Exception as e:
        logger.error(f"Could not fetch vault address from SyncSwap Router: {e}")
        raise ScrollSwapError(
            f"Could not fetch vault address from SyncSwap Router: {e}"
        )

    direct_pool_address = _get_syncswap_pool_address_scroll(
        web3_scroll, token_in_start_address, token_out_final_address
    )
    if direct_pool_address:
        logger.info(f"Direct path found via pool: {direct_pool_address}")
        withdraw_mode: int
        if actual_token_out_symbol == ETH_SYMBOL:
            withdraw_mode = 1
        elif token_out_final_address == weth_address:
            withdraw_mode = 2
        else:
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
        pool2_address = _get_syncswap_pool_address_scroll(
            web3_scroll, weth_address, token_out_final_address
        )

        if pool1_address and pool2_address:
            logger.info(
                f"Found WETH hop: Pool1 ({token_in_start_address}->WETH): "
                f"{pool1_address}, Pool2 (WETH->{token_out_final_address}): "
                f"{pool2_address}"
            )
            step1_data = _encode_swap_step_data_scroll(
                token_in_start_address, vault_address, 2
            )
            step1 = {
                "pool": Web3.to_checksum_address(pool1_address),
                "data": step1_data,
                "callback": ZERO_ADDRESS,
                "callbackData": HexBytes("0x"),
            }

            final_withdraw_mode: int
            if actual_token_out_symbol == ETH_SYMBOL:
                final_withdraw_mode = 1
            elif token_out_final_address == weth_address:
                final_withdraw_mode = 2
            else:
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
    recipient_address = sender_address

    weth_l2_address = _get_l2_token_address_scroll(WETH_SYMBOL)

    token_in_address_actual: str
    is_eth_input = False
    if token_in_symbol == ETH_SYMBOL:
        token_in_address_actual = weth_l2_address
        is_eth_input = True
        eth_balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(sender_address))
        if eth_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient ETH balance for swap: have {eth_balance}, "
                f"need {amount_in}"
            )
    else:
        token_in_address_actual = _get_l2_token_address_scroll(token_in_symbol)
        token_in_contract = _get_contract_scroll(
            web3_scroll, ERC20_ABI_NAME, token_in_address_actual
        )
        erc20_balance = token_in_contract.functions.balanceOf(
            Web3.to_checksum_address(sender_address)
        ).call()
        if erc20_balance < amount_in:
            raise InsufficientBalanceError(
                f"Insufficient {token_in_symbol} balance for swap: "
                f"have {erc20_balance}, need {amount_in}"
            )

    token_out_address_actual: str
    if token_out_symbol == ETH_SYMBOL:
        token_out_address_actual = weth_l2_address
    else:
        token_out_address_actual = _get_l2_token_address_scroll(token_out_symbol)

    current_block = web3_scroll.eth.get_block("latest")
    deadline = current_block["timestamp"] + deadline_seconds

    router_contract = _get_syncswap_router_contract_scroll(web3_scroll)

    try:
        expected_amount_out = _get_expected_amount_out_syncswap_scroll(
            web3_scroll,
            token_in_address_actual,
            token_out_address_actual,
            amount_in,
            sender_address,
            weth_l2_address,
        )
    except InsufficientLiquidityError as e:
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

    try:
        swap_paths = _construct_syncswap_paths_scroll(
            web3_scroll,
            token_in_address_actual,
            token_out_address_actual,
            amount_in,
            recipient_address,
            weth_l2_address,
            router_contract,
            token_out_symbol,
        )
    except InsufficientLiquidityError as e:
        logger.error(f"Path construction failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Error constructing swap paths: {e}")
        raise ScrollSwapError(f"Could not construct swap paths: {e}") from e

    tx_value = Wei(amount_in) if is_eth_input else Wei(0)

    swap_tx_params_dict: TxParams = {
        "from": sender_address,
        "to": SYNC_SWAP_ROUTER_ADDRESS_SCROLL,
        "value": tx_value,
        "gas": Wei(DEFAULT_SWAP_L2_GAS_LIMIT),
    }

    logger.info(
        f"Preparing swap transaction with router.swap(): paths={swap_paths}, "
        f"amountOutMin={amount_out_min}, deadline={deadline}"
    )

    try:
        swap_function: ContractFunction = router_contract.functions.swap(
            swap_paths, amount_out_min, deadline
        )
        built_swap_tx = swap_function.build_transaction(swap_tx_params_dict)
        logger.info(f"Built swap transaction: {built_swap_tx}")

        return _build_and_send_tx_scroll(web3_scroll, private_key, built_swap_tx)

    except ContractLogicError as e:
        logger.error(f"SyncSwap contract logic error: {e.message} - Data: {e.data}")
        if "TooLittleReceived" in str(e) or (
            e.data and "0x087229a4" in e.data
        ):
            raise InsufficientLiquidityError(
                f"Swap likely to result in too little received (slippage or "
                f"liquidity: {e.message}",
                tx_data=e.data
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
    comptroller_contract = _get_contract_scroll(
        web3_scroll, LAYERBANK_COMPTROLLER_ABI_NAME,
        LAYERBANK_COMPTROLLER_ADDRESS_SCROLL
    )

    try:
        is_member = comptroller_contract.functions.checkMembership(
            Web3.to_checksum_address(user_address), Web3.to_checksum_address(lbtoken_address)
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
    """
    try:
        result = comptroller_contract.functions.getAccountLiquidity(
            Web3.to_checksum_address(user_address)
        ).call()
        error_code, liquidity_usd, shortfall_usd = result
        return int(error_code), int(liquidity_usd), int(shortfall_usd)
    except Exception as e:
        logger.error(f"Failed to get account liquidity for {user_address}: {e}")
        raise ScrollLendingError(f"Failed to get account liquidity: {e}") from e


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
    """
    logger.info(f"Initiating LayerBank {action}: {amount} {token_symbol}")

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

    lbtoken_address = _get_layerbank_lbtoken_address_scroll(token_symbol)
    lbtoken_contract = _get_contract_scroll(
        web3_scroll, LAYERBANK_LBTOKEN_ABI_NAME, lbtoken_address
    )

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
        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }

        if token_symbol == "ETH":
            eth_balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(user_address))
            if eth_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient ETH balance: have {eth_balance}, need {amount}"
                )

            tx_params["value"] = Wei(amount)
            mint_tx = lbtoken_contract.functions.mint().build_transaction(tx_params)

        else:  # USDC
            usdc_contract = _get_contract_scroll(
                web3_scroll, ERC20_ABI_NAME, SCROLL_USDC_TOKEN_ADDRESS
            )
            usdc_balance = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(user_address)
            ).call()
            if usdc_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient USDC balance: have {usdc_balance}, need {amount}"
                )

            _approve_erc20_scroll(
                web3_scroll, private_key, SCROLL_USDC_TOKEN_ADDRESS,
                lbtoken_address, amount
            )

            tx_params["value"] = Wei(0)  # No ETH sent with ERC20 mint
            mint_tx = lbtoken_contract.functions.mint(amount).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_scroll, private_key, mint_tx)

    except InsufficientBalanceError:
        raise
    except ApprovalError:
        raise
    except TransactionRevertedError:
        raise
    except Exception as e:
        logger.error(f"Failed to lend {amount} {token_symbol} on LayerBank: {e}")
        raise ScrollLendingError(f"Failed to lend on LayerBank: {e}") from e


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
        # Check lbToken balance
        lb_balance = lbtoken_contract.functions.balanceOf(
            Web3.to_checksum_address(user_address)
        ).call()
        if lb_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient lbToken balance to withdraw: have {lb_balance}, need {amount}"
            )

        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }

        # Redeem exact amount of underlying tokens
        redeem_tx = lbtoken_contract.functions.redeemUnderlying(
            amount
        ).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_scroll, private_key, redeem_tx)

    except InsufficientBalanceError:
        raise
    except TransactionRevertedError:
        raise
    except Exception as e:
        logger.error(f"Failed to withdraw {amount} {token_symbol} from LayerBank: {e}")
        raise ScrollLendingError(f"Failed to withdraw from LayerBank: {e}") from e


def _handle_borrow_action_scroll(
    web3_scroll: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    user_address: str,
    lbtoken_contract: Contract,
    comptroller_contract: Contract,
    lbtoken_address: str,
) -> str:
    """Handle borrow action for LayerBank."""
    logger.info(f"Borrowing {amount} {token_symbol} from LayerBank")

    try:
        # Ensure user has entered the market for this lbToken
        _check_and_enter_layerbank_market_scroll(
            web3_scroll, private_key, lbtoken_address, user_address
        )

        # Check account liquidity before borrowing
        error_code, liquidity_usd, shortfall_usd = \
            _get_layerbank_account_liquidity_scroll(
                web3_scroll, comptroller_contract, user_address
            )

        if shortfall_usd > 0:
            raise InsufficientCollateralError(
                f"Account is in shortfall by {shortfall_usd} USD. Cannot borrow."
            )

        # Convert borrow amount to underlying token amount if necessary (e.g., for ETH)
        # LayerBank's borrow function expects the amount of the underlying token.
        # No conversion needed if 'amount' is already in underlying token units.

        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }

        borrow_tx = lbtoken_contract.functions.borrow(amount).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_scroll, private_key, borrow_tx)

    except InsufficientCollateralError:
        raise
    except TransactionRevertedError as e:
        # Check for specific LayerBank Comptroller rejection codes
        if e.receipt and e.receipt.get("status") == 0:
            # Attempt to decode revert reason if available
            # This is a generic check, specific decoding might require more ABI
            # if e.tx_hash:
            #     try:
            #         # This is complex and often requires an archive node
            #         # or specific RPC methods. For now, we'll rely on
            #         # common error messages or data patterns.
            #         pass
            #     except Exception:
            #         pass  # Ignore if trace fails

            # Common LayerBank revert reasons (example, actual codes vary)
            if "COMPTROLLER_REJECTION" in str(e.args[0]) or (e.data and "0x" in e.data):
                raise LayerBankComptrollerRejectionError(
                    f"LayerBank Comptroller rejected borrow: {e.args[0]}"
                ) from e
        raise ScrollLendingError(f"Failed to borrow on LayerBank: {e}") from e
    except Exception as e:
        logger.error(f"Failed to borrow {amount} {token_symbol} on LayerBank: {e}")
        raise ScrollLendingError(f"Failed to borrow on LayerBank: {e}") from e


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
        # Get current borrow balance
        borrow_balance = lbtoken_contract.functions.borrowBalanceCurrent(
            Web3.to_checksum_address(user_address)
        ).call()
        logger.info(f"Current borrow balance for {token_symbol}: {borrow_balance}")

        if amount > borrow_balance:
            raise RepayAmountExceedsDebtError(
                f"Repay amount {amount} exceeds current borrow debt {borrow_balance}."
            )

        tx_params: TxParams = {
            "from": user_address,
            "gasPrice": web3_scroll.eth.gas_price,
        }

        if token_symbol == "ETH":
            eth_balance = web3_scroll.eth.get_balance(Web3.to_checksum_address(user_address))
            if eth_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient ETH balance to repay: have {eth_balance}, need {amount}"
                )
            tx_params["value"] = Wei(amount)
            repay_tx = lbtoken_contract.functions.repayBorrow().build_transaction(tx_params)
        else:  # USDC
            usdc_contract = _get_contract_scroll(
                web3_scroll, ERC20_ABI_NAME, SCROLL_USDC_TOKEN_ADDRESS
            )
            usdc_balance = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(user_address)
            ).call()
            if usdc_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient USDC balance to repay: have {usdc_balance}, "
                    f"need {amount}"
                )

            _approve_erc20_scroll(
                web3_scroll, private_key, SCROLL_USDC_TOKEN_ADDRESS,
                lbtoken_contract.address, amount
            )
            repay_tx = lbtoken_contract.functions.repayBorrow(
                amount
            ).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_scroll, private_key, repay_tx)

    except (InsufficientBalanceError, RepayAmountExceedsDebtError):
        raise
    except ApprovalError:
        raise
    except TransactionRevertedError:
        raise
    except Exception as e:
        logger.error(f"Failed to repay {amount} {token_symbol} on LayerBank: {e}")
        raise ScrollLendingError(f"Failed to repay on LayerBank: {e}") from e


def bridge_assets(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    direction: str,
    l2_gas_limit: int = DEFAULT_L2_GAS_LIMIT,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridges ETH or ERC20 tokens between L1 (Ethereum) and L2 (Scroll).

    Args:
    web3_l1: Web3 instance for L1 (Ethereum).
    web3_l2: Web3 instance for L2 (Scroll).
    private_key: Private key of the account.
    token_symbol: Symbol of the token to bridge (e.g., "ETH", "USDC").
    amount: Amount of token to bridge (in Wei for ETH, smallest unit for ERC20).
    direction: "deposit" (L1 to L2) or "withdraw" (L2 to L1).
    l2_gas_limit: Gas limit for the L2 transaction (for deposits).
    l2_gas_price: Gas price for the L2 transaction (for deposits).

    Returns:
    Transaction hash of the bridge operation.

    Raises:
    ScrollBridgeError: For general bridging errors.
    InsufficientBalanceError: If account balance is insufficient.
    TokenNotSupportedError: If token symbol is not configured.
    ApprovalError: If ERC20 approval fails.
    GasEstimationError: If gas estimation fails.
    TransactionRevertedError: If the transaction is reverted.
    ValueError: For invalid inputs.
    """
    logger.info(
        f"Initiating Scroll bridge: {amount} {token_symbol} {direction}."
    )

    if direction not in ("deposit", "withdraw"):
        raise ValueError("Direction must be 'deposit' or 'withdraw'.")
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    account_l1 = _get_account_scroll(private_key, web3_l1)
    account_l2 = _get_account_scroll(private_key, web3_l2)
    l1_address = account_l1.address
    l2_address = account_l2.address

    if token_symbol == ETH_SYMBOL:
        return _bridge_eth_scroll(
            web3_l1,
            web3_l2,
            private_key,
            amount,
            direction,
            Web3.to_checksum_address(l1_address),
            Web3.to_checksum_address(l2_address),
            l2_gas_limit,
            l2_gas_price,
        )
    else:
        return _bridge_erc20_scroll(
            web3_l1,
            web3_l2,
            private_key,
            token_symbol,
            amount,
            direction,
            Web3.to_checksum_address(l1_address),
            Web3.to_checksum_address(l2_address),
            l2_gas_limit,
            l2_gas_price,
        )


def _bridge_eth_scroll(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    amount: int,
    direction: str,
    l1_address: str,
    l2_address: str,
    l2_gas_limit: int,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridge ETH between L1 and L2.
    """
    logger.info(f"Bridging ETH: {amount} {direction} from {l1_address} to {l2_address}")

    if direction == "deposit":
        # L1 to L2 ETH deposit
        l1_gateway_router = _get_contract_scroll(
            web3_l1, L1_GATEWAY_ROUTER_ABI_NAME, SCROLL_L1_GATEWAY_ROUTER_ADDRESS
        )
        l2_gas_price_actual = l2_gas_price or web3_l2.eth.gas_price
        message_fee = _estimate_l1_to_l2_message_fee_scroll(
            web3_l1, l2_gas_limit, l2_gas_price_actual
        )
        total_value = amount + message_fee

        # Check L1 balance
        l1_balance = web3_l1.eth.get_balance(Web3.to_checksum_address(l1_address))
        if l1_balance < total_value:
            raise InsufficientBalanceError(
                f"Insufficient L1 ETH balance for deposit: have {l1_balance}, "
                f"need {total_value} (amount + message_fee)"
            )

        tx_params: TxParams = {
            "from": l1_address,
            "value": Wei(total_value),
            "gasPrice": web3_l1.eth.gas_price,
        }
        deposit_tx = l1_gateway_router.functions.depositETH(
            amount, l2_gas_limit, l2_address
        ).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_l1, private_key, deposit_tx)

    elif direction == "withdraw":
        # L2 to L1 ETH withdrawal
        l2_gateway_router = _get_contract_scroll(
            web3_l2, L2_GATEWAY_ROUTER_ABI_NAME, SCROLL_L2_GATEWAY_ROUTER_ADDRESS
        )

        # Check L2 balance
        l2_balance = web3_l2.eth.get_balance(Web3.to_checksum_address(l2_address))
        if l2_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L2 ETH balance for withdrawal: have {l2_balance}, "
                f"need {amount}"
            )

        withdraw_tx_params: TxParams = {
            "from": l2_address,
            "value": Wei(amount),
            "gasPrice": web3_l2.eth.gas_price,
        }
        withdraw_tx = l2_gateway_router.functions.withdrawETH(
            amount, l1_address
        ).build_transaction(withdraw_tx_params)

        return _build_and_send_tx_scroll(web3_l2, private_key, withdraw_tx)
    return ""


def _bridge_erc20_scroll(
    web3_l1: Web3,
    web3_l2: Web3,
    private_key: str,
    token_symbol: str,
    amount: int,
    direction: str,
    l1_address: str,
    l2_address: str,
    l2_gas_limit: int,
    l2_gas_price: Optional[int] = None,
) -> str:
    """
    Bridge ERC20 tokens between L1 and L2.
    """
    logger.info(f"Bridging ERC20 {token_symbol}: {amount} {direction}.")

    l1_token_address = _get_l1_token_address_scroll(token_symbol)
    l2_token_address = _get_l2_token_address_scroll(token_symbol)

    if direction == "deposit":
        # L1 to L2 ERC20 deposit
        l1_gateway_router = _get_contract_scroll(
            web3_l1, L1_GATEWAY_ROUTER_ABI_NAME, SCROLL_L1_GATEWAY_ROUTER_ADDRESS
        )
        l1_token_contract = _get_contract_scroll(
            web3_l1, ERC20_ABI_NAME, l1_token_address
        )

        # Check L1 ERC20 balance
        l1_erc20_balance = l1_token_contract.functions.balanceOf(
            Web3.to_checksum_address(l1_address)
        ).call()
        if l1_erc20_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L1 {token_symbol} balance for deposit: have "
                f"{l1_erc20_balance}, need {amount}"
            )

        # Approve L1 Gateway Router to spend ERC20
        _approve_erc20_scroll(
            web3_l1, private_key, l1_token_address,
            SCROLL_L1_GATEWAY_ROUTER_ADDRESS, amount
        )

        l2_gas_price_actual = l2_gas_price or web3_l2.eth.gas_price
        message_fee = _estimate_l1_to_l2_message_fee_scroll(
            web3_l1, l2_gas_limit, l2_gas_price_actual
        )

        tx_params: TxParams = {
            "from": l1_address,
            "value": Wei(message_fee),  # Message fee is sent with ETH
            "gasPrice": web3_l1.eth.gas_price,
        }
        deposit_tx = l1_gateway_router.functions.depositERC20(
            l1_token_address, amount, l2_gas_limit, l2_address
        ).build_transaction(tx_params)

        return _build_and_send_tx_scroll(web3_l1, private_key, deposit_tx)

    elif direction == "withdraw":
        # L2 to L1 ERC20 withdrawal
        l2_gateway_router = _get_contract_scroll(
            web3_l2, L2_GATEWAY_ROUTER_ABI_NAME, SCROLL_L2_GATEWAY_ROUTER_ADDRESS
        )
        l2_token_contract = _get_contract_scroll(
            web3_l2, ERC20_ABI_NAME, l2_token_address
        )

        # Check L2 ERC20 balance
        l2_erc20_balance = l2_token_contract.functions.balanceOf(
            Web3.to_checksum_address(l2_address)
        ).call()
        if l2_erc20_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient L2 {token_symbol} balance for withdrawal: have "
                f"{l2_erc20_balance}, need {amount}"
            )

        # Approve L2 Gateway Router to spend ERC20
        _approve_erc20_scroll(
            web3_l2, private_key, l2_token_address,
            SCROLL_L2_GATEWAY_ROUTER_ADDRESS, amount
        )

        erc20_withdraw_tx_params: TxParams = {
            "from": l2_address,
            "gasPrice": web3_l2.eth.gas_price,
        }
        withdraw_tx = l2_gateway_router.functions.withdrawERC20(
            l2_token_address, amount, l1_address
        ).build_transaction(erc20_withdraw_tx_params)

        return _build_and_send_tx_scroll(web3_l2, private_key, withdraw_tx)
    return ""
