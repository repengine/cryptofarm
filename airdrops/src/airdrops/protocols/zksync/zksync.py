import random
import time
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from web3 import Web3
from web3.contract.contract import Contract, ContractFunction

from airdrops.shared.connection_manager import ConnectionManager
from airdrops.shared.constants import (
    NATIVE_ETH_ADDRESS,
    ZERO_ADDRESS,
    ZKSYNC_ERA_CHAIN_ID,
)
from airdrops.shared.logger import logger
from airdrops.shared.transaction_utils import (
    build_and_send_transaction,
    send_signed_transaction,
)
from airdrops.shared.utils import (
    convert_to_wei,
    get_token_info,
    int_to_decimal_for_token,
)

# --- Constants for zkSync Era ---
DEFAULT_L2_GAS_LIMIT = 1000000  # Placeholder, adjust as needed
DEFAULT_L2_GAS_PER_PUBDATA_BYTE_LIMIT = 800  # Placeholder, adjust as needed

ZKSYNC_ERA_BRIDGE_ADDRESS = "0x32400084C286Cf3E17e7B677ea9583e60a000324"
ZKSYNC_ERA_WETH_GATEWAY_ADDRESS = "0x72eF506370076208a9a6fC82d3530587090B949d"
ZKSYNC_ERA_LENDING_POOL_ADDRESS = "0x69FA688f1Dc42A6b5063058284e5389D8901d57e"
ZKSYNC_ERA_LENDING_POOL_ADDRESS_PROVIDER = (
    "0xa97684efaac4d0963bc9fda6be23127dff70e6df"
)
ZKSYNC_ERA_LENDING_ORACLE_ADDRESS = "0x54586BfC86d607397216C6B8B748d07593c2a0B8"
ZKSYNC_ERA_LENDING_A_TOKEN_ADDRESS = "0x69FA688f1Dc42A6b5063058284e5389D8901d57e"
ZKSYNC_ERA_LENDING_VARIABLE_DEBT_TOKEN_ADDRESS = (
    "0x69FA688f1Dc42A6b5063058284e5389D8901d57e"
)
ZKSYNC_ERA_LENDING_STABLE_DEBT_TOKEN_ADDRESS = (
    "0x69FA688f1Dc42A6b5063058284e5389D8901d57e"
)
ZKSYNC_ERA_LENDING_ORACLE_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "asset", "type": "address"}],
        "name": "getAssetPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def _get_web3_instance(config: Dict[str, Any], network_name: str) -> Web3:
    """Returns a Web3 instance for the given network."""
    connection_manager = ConnectionManager(config)
    return connection_manager.get_web3(network_name)


def _get_contract(w3: Web3, address: str, abi: List[Dict[str, Any]]) -> Contract:
    """Returns a contract instance."""
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def _get_l1_bridge_abi() -> List[Dict[str, Any]]:  # Renamed
    """Get minimal ABI for zkSync Era Bridge contract."""
    return [
        {
            "inputs": [
                {"internalType": "address", "name": "_l1Token", "type": "address"},
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                {"internalType": "address", "name": "_to", "type": "address"},
                {"internalType": "uint256", "name": "_l2GasLimit", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "_l2GasPerPubdataByteLimit",
                    "type": "uint256",
                },
                {
                    "internalType": "bytes[]",
                    "name": "_factoryDeps",
                    "type": "bytes[]",
                },
                {
                    "internalType": "address",
                    "name": "_refundRecipient",
                    "type": "address",
                },
            ],
            "name": "requestL2Transaction",
            "outputs": [
                {"internalType": "bytes32", "name": "txHash", "type": "bytes32"}
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "_l1Token", "type": "address"},
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                {"internalType": "address", "name": "_to", "type": "address"},
                {"internalType": "uint256", "name": "_l2GasLimit", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "_l2GasPerPubdataByteLimit",
                    "type": "uint256",
                },
                {
                    "internalType": "bytes[]",
                    "name": "_factoryDeps",
                    "type": "bytes[]",
                },
                {
                    "internalType": "address",
                    "name": "_refundRecipient",
                    "type": "address",
                },
                {"internalType": "bytes", "name": "_data", "type": "bytes"},
            ],
            "name": "requestL2Transaction",
            "outputs": [
                {"internalType": "bytes32", "name": "txHash", "type": "bytes32"}
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "_l2Token", "type": "address"},
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            ],
            "name": "withdraw",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]


def _get_l2_bridge_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for zkSync Era L2 Bridge contract."""
    return _get_l1_bridge_abi()  # Assuming same ABI for now, adjust if needed


def _get_erc20_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for ERC20 token."""
    return [
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "payable": False,
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [
                {"name": "_owner", "type": "address"},
                {"name": "_spender", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function",
        },
    ]


def _get_weth_gateway_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for WETH Gateway contract."""
    return [
        {
            "inputs": [
                {"internalType": "address", "name": "pool", "type": "address"},
                {"internalType": "address", "name": "onBehalfOf", "type": "address"},
                {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
            ],
            "name": "depositETH",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "pool", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "address", "name": "to", "type": "address"},
            ],
            "name": "withdrawETH",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "pool", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "interestRateMode",
                    "type": "uint256",
                },
                {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
            ],
            "name": "borrowETH",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "pool", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "interestRateMode",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            ],
            "name": "repayETH",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
    ]


def _get_eralend_weth_gateway_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for EraLend WETH Gateway contract."""
    return _get_weth_gateway_abi()  # Assuming same ABI for now, adjust if needed


def _get_eralend_lending_pool_abi() -> List[Dict[str, Any]]:
    """Get minimal ABI for EraLend Lending Pool contract."""
    return [
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "address", "name": "onBehalfOf", "type": "address"},
                {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
            ],
            "name": "supply",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "address", "name": "to", "type": "address"},
            ],
            "name": "withdraw",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "interestRateMode",
                    "type": "uint256",
                },
                {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
                {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            ],
            "name": "borrow",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "interestRateMode",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            ],
            "name": "repay",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "bool", "name": "useAsCollateral", "type": "bool"},
            ],
            "name": "setUserUseReserveAsCollateral",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]


def _build_and_send_lending_transaction(
    w3_l2: Web3,
    contract_function: ContractFunction,
    transaction_params: Dict[str, Any],
    private_key: str,
    user_address: str,
    action_name: str,
) -> Tuple[bool, str]:
    """Builds and sends a lending protocol transaction."""
    try:
        tx_hash = build_and_send_transaction(
            w3_l2, contract_function.build_transaction(transaction_params), private_key
        )
        logger.info(f"Successfully executed {action_name} transaction: {tx_hash.hash.hex()}")
        return True, tx_hash.hash.hex()
    except Exception as e:
        logger.error(f"Failed to execute {action_name} transaction: {e}")
        return False, str(e)


def _execute_lending_action(
    user_address: str,
    private_key: str,
    action: str,
    token_address: str,
    amount: int,
    lending_protocol_name: str,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Executes a lending action (supply, withdraw, borrow, repay, set_collateral)."""
    lending_config = config["networks"]["zksync"]["lending_protocols"].get(
        lending_protocol_name
    )
    if not lending_config:
        return False, f"Lending protocol {lending_protocol_name} not configured."

    w3_l2 = _get_web3_instance(config, "zksync")
    lending_pool_address = lending_config.get("lending_pool_manager")
    weth_gateway_address = lending_config.get("weth_gateway")

    if not lending_pool_address:
        return False, "Lending pool manager address not found in config."

    lending_pool_contract = _get_contract(
        w3_l2, lending_pool_address, _get_eralend_lending_pool_abi()
    )
    weth_gateway_contract = (
        _get_contract(w3_l2, weth_gateway_address, _get_weth_gateway_abi())
        if weth_gateway_address
        else None
    )

    if action == "supply":
        return _execute_supply_action(
            w3_l2,
            lending_pool_contract,
            weth_gateway_contract,
            user_address,
            private_key,
            token_address,
            amount,
            config,
        )
    elif action == "withdraw":
        return _execute_withdraw_action(
            w3_l2,
            lending_pool_contract,
            weth_gateway_contract,
            user_address,
            private_key,
            token_address,
            amount,
            config,
        )
    elif action == "borrow":
        return _execute_borrow_action(
            w3_l2,
            lending_pool_contract,
            weth_gateway_contract,
            user_address,
            private_key,
            token_address,
            amount,
            config,
        )
    elif action == "repay":
        return _execute_repay_action(
            w3_l2,
            lending_pool_contract,
            weth_gateway_contract,
            user_address,
            private_key,
            token_address,
            amount,
            config,
        )
    elif action == "set_collateral":
        return _execute_set_collateral_action(
            lending_pool_contract,
            user_address,
            private_key,
            token_address,
            bool(amount),  # Convert int (0 or 1) to bool
        )
    else:
        return False, f"Unsupported lending action: {action}"


def _handle_token_approval(
    w3: Web3,
    token_address: str,
    user_address: str,
    private_key: str,
    spender_address: str,
    amount: int,
) -> Tuple[bool, str]:
    """Handles ERC20 token approval for a spender."""
    if token_address == NATIVE_ETH_ADDRESS:
        return True, "ETH does not require approval."

    token_contract = _get_contract(w3, token_address, _get_erc20_abi())
    current_allowance = token_contract.functions.allowance(
        user_address, spender_address
    ).call()

    if current_allowance >= amount:
        logger.info(
            f"Allowance for {token_address} to {spender_address} is sufficient."
        )
        return True, "Allowance sufficient."

    logger.info(
        f"Approving {spender_address} for {amount} of {token_address}..."
    )
    try:
        approve_tx = token_contract.functions.approve(
            spender_address, amount
        ).build_transaction(
            {
                "from": user_address,
                "chainId": ZKSYNC_ERA_CHAIN_ID,
                "nonce": w3.eth.get_transaction_count(user_address),
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_tx = w3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Approval transaction successful: {tx_hash.hex()}")
        return True, tx_hash.hex()
    except Exception as e:
        logger.error(f"Token approval failed: {e}")
        return False, str(e)


def _execute_supply_action(
    w3_l2: Web3,
    lending_pool_contract: Contract,
    weth_gateway_contract: Contract | None,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Executes a supply action."""
    if token_address == NATIVE_ETH_ADDRESS:
        if not weth_gateway_contract:
            return False, "WETH Gateway contract not configured for ETH supply."
        contract_function = weth_gateway_contract.functions.depositETH(
            lending_pool_contract.address,
            user_address,
            0,
        )
        transaction_params = {"from": user_address, "value": amount}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "supply ETH",
        )
    else:
        # ERC20 token supply
        success, approval_result = _handle_token_approval(
            w3_l2,
            token_address,
            user_address,
            private_key,
            lending_pool_contract.address,
            amount,
        )
        if not success:
            return False, f"Approval failed: {approval_result}"

        contract_function = lending_pool_contract.functions.supply(
            token_address, amount, user_address, 0
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "supply ERC20",
        )


def _execute_withdraw_action(
    w3_l2: Web3,
    lending_pool_contract: Contract,
    weth_gateway_contract: Contract | None,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Executes a withdraw action."""
    if token_address == NATIVE_ETH_ADDRESS:
        if not weth_gateway_contract:
            return False, "WETH Gateway contract not configured for ETH withdrawal."
        contract_function = weth_gateway_contract.functions.withdrawETH(
            lending_pool_contract.address, amount, user_address
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "withdraw ETH",
        )
    else:
        contract_function = lending_pool_contract.functions.withdraw(
            token_address, amount, user_address
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "withdraw ERC20",
        )


def _execute_borrow_action(
    w3_l2: Web3,
    lending_pool_contract: Contract,
    weth_gateway_contract: Contract | None,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Executes a borrow action."""
    interest_rate_mode = 2  # Variable rate
    referral_code = 0
    if token_address == NATIVE_ETH_ADDRESS:
        if not weth_gateway_contract:
            return False, "WETH Gateway contract not configured for ETH borrow."
        contract_function = weth_gateway_contract.functions.borrowETH(
            lending_pool_contract.address,
            amount,
            interest_rate_mode,
            referral_code,
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "borrow ETH",
        )
    else:
        contract_function = lending_pool_contract.functions.borrow(
            token_address,
            amount,
            interest_rate_mode,
            referral_code,
            user_address,
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "borrow ERC20",
        )


def _execute_repay_action(
    w3_l2: Web3,
    lending_pool_contract: Contract,
    weth_gateway_contract: Contract | None,
    user_address: str,
    private_key: str,
    token_address: str,
    amount: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """Executes a repay action."""
    interest_rate_mode = 2  # Variable rate
    if token_address == NATIVE_ETH_ADDRESS:
        if not weth_gateway_contract:
            return False, "WETH Gateway contract not configured for ETH repay."
        contract_function = weth_gateway_contract.functions.repayETH(
            lending_pool_contract.address,
            amount,
            interest_rate_mode,
            user_address,
        )
        transaction_params = {"from": user_address, "value": amount}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "repay ETH",
        )
    else:
        success, approval_result = _handle_token_approval(
            w3_l2,
            token_address,
            user_address,
            private_key,
            lending_pool_contract.address,
            amount,
        )
        if not success:
            return False, f"Approval failed: {approval_result}"

        contract_function = lending_pool_contract.functions.repay(
            token_address,
            amount,
            interest_rate_mode,
            user_address,
        )
        transaction_params = {"from": user_address}
        return _build_and_send_lending_transaction(
            w3_l2,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "repay ERC20",
        )


def _execute_set_collateral_action(
    lending_pool_contract: Contract,
    user_address: str,
    private_key: str,
    token_address: str,
    use_as_collateral: bool,
) -> Tuple[bool, str]:
    """Executes a set_collateral action."""
    w3_l2 = lending_pool_contract.w3
    contract_function = lending_pool_contract.functions.setUserUseReserveAsCollateral(
        token_address, use_as_collateral
    )
    transaction_params = {"from": user_address}
    return _build_and_send_lending_transaction(
        w3_l2,
        contract_function,
        transaction_params,
        private_key,
        user_address,
        f"set collateral {token_address} to {use_as_collateral}",
    )


def _execute_l2_to_l1_withdrawal(
    w3_l2: Web3,
    bridge_contract: Contract,
    user_address: str,
    private_key: str,
    amount_wei: int,
) -> Tuple[bool, str]:
    """Executes an L2 to L1 withdrawal."""
    try:
        transaction = _build_l2_withdrawal_transaction(
            w3_l2, bridge_contract, user_address, amount_wei
        )
        tx_hash = send_signed_transaction(w3_l2, transaction, private_key)
        logger.info(
            f"Successfully initiated L2 to L1 withdrawal for "
            f"{Web3.from_wei(amount_wei, 'ether')} ETH. "
            f"Transaction hash: {tx_hash.hex()}"
        )
        return True, tx_hash.hex()
    except Exception as e:
        logger.error(f"Failed to withdraw ETH from L2 to L1: {e}")
        return False, str(e)


def _get_initial_onchain_state(
    user_address: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retrieves the initial on-chain state for the user's address on zkSync Era.
    This includes ETH and specified ERC20 token balances.
    """
    w3_l2 = _get_web3_instance(config, "zksync")
    state: Dict[str, Any] = {"balances": {}}

    # Get ETH balance
    eth_balance_wei = w3_l2.eth.get_balance(user_address)
    state["balances"][NATIVE_ETH_ADDRESS] = eth_balance_wei
    logger.info(
        f"Initial ETH balance for {user_address}: "
        f"{Web3.from_wei(eth_balance_wei, 'ether')} ETH"
    )

    # Get ERC20 token balances
    tokens_to_track = config["random_activity"]["initial_state_fetch"].get(
        "tokens_to_track_balance", []
    )
    for token_symbol in tokens_to_track:
        if token_symbol == "ETH":
            continue  # Already handled

        token_info = get_token_info(token_symbol, config)
        if not token_info:
            logger.warning(f"Token {token_symbol} not found in config.")
            continue

        token_address = token_info.get("address")
        if not token_address:
            logger.warning(f"Address for token {token_symbol} not found in config.")
            continue

        try:
            token_contract = _get_contract(w3_l2, token_address, _get_erc20_abi())
            balance_wei = token_contract.functions.balanceOf(user_address).call()
            state["balances"][token_address] = balance_wei
            logger.info(
                f"Initial {token_symbol} balance for {user_address}: "
                f"{int_to_decimal_for_token(balance_wei, token_info['decimals'])} "
                f"{token_symbol}"
            )
        except Exception as e:
            logger.error(
                f"Could not fetch balance for {token_symbol} ({token_address}): {e}"
            )
            continue
    return state


def _validate_bridge_inputs(
    user_address: str,
    private_key: str,
    amount_eth: Decimal,
    to_l2: bool,
    config: Dict[str, Any],
) -> None:
    """
    Validates inputs for a bridge action, raising ValueError on failure.

    Args:
        user_address: The user's wallet address.
        private_key: The private key of the user's wallet.
        amount_eth: The amount of ETH to bridge.
        to_l2: True to bridge from L1 to L2, False for L2 to L1.
        config: The configuration dictionary.

    Raises:
        ValueError: If any validation fails.
    """
    if not config:
        raise ValueError("Configuration dictionary is required.")
    if "networks" not in config or not isinstance(config["networks"], dict):
        raise ValueError("Config must contain a 'networks' dictionary.")
    if "ethereum" not in config["networks"] or "zksync" not in config["networks"]:
        raise ValueError(
            "Config 'networks' must contain 'ethereum' and 'zksync' keys."
        )
    if not Web3.is_checksum_address(user_address):
        raise ValueError(f"Invalid user address: {user_address}")
    if not isinstance(private_key, str) or not private_key.startswith("0x") or len(private_key) != 66:
        raise ValueError("Invalid private key format.")
    if not isinstance(amount_eth, Decimal) or amount_eth <= Decimal(0):
        raise ValueError("Amount must be a positive Decimal.")


def _determine_swap_path(
    w3: Web3,
    token_in: str,
    token_out: str,
    dex_name: str,
    config: Dict[str, Any],
) -> List[str]:
    """
    Determines the swap path for a given token pair and DEX.

    Args:
        w3: Web3 instance.
        token_in: The input token address.
        token_out: The output token address.
        dex_name: The name of the DEX.
        config: The configuration dictionary.

    Returns:
        A list of token addresses representing the swap path.

    Raises:
        ValueError: If WETH address is not found in config when needed.
    """
    logger.info(f"Determining swap path for {token_in} -> {token_out} on {dex_name}")

    # For many DEXs on zkSync, if ETH is involved, it must be wrapped (WETH).
    if token_in == NATIVE_ETH_ADDRESS or token_out == NATIVE_ETH_ADDRESS:
        weth_address = config.get("tokens", {}).get("WETH", {}).get("address")
        if not weth_address:
            raise ValueError("WETH address not found in config for ETH swap.")

        path_token_in = weth_address if token_in == NATIVE_ETH_ADDRESS else token_in
        path_token_out = weth_address if token_out == NATIVE_ETH_ADDRESS else token_out
        path = [path_token_in, path_token_out]
    else:
        # Direct token-to-token swap
        path = [token_in, token_out]

    logger.info(f"Determined swap path: {path}")
    return path


def _randomize_bridge_parameters(
    user_address: str, state: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Randomizes parameters for a bridge action."""
    bridge_config = config["random_activity"]["bridge_eth"]
    min_amount_eth = Decimal(str(bridge_config["min_amount_eth"]))
    max_amount_eth = Decimal(str(bridge_config["max_amount_eth"]))
    to_l2_probability = bridge_config["to_l2_probability"]

    # Ensure min_amount_eth and max_amount_eth are in wei for calculation
    min_amount_wei = convert_to_wei(min_amount_eth)
    max_amount_wei = convert_to_wei(max_amount_eth)

    # Get current ETH balance in wei from the state
    current_eth_balance_wei = state["balances"].get(NATIVE_ETH_ADDRESS, 0)

    if current_eth_balance_wei == 0:
        logger.warning("No ETH balance to bridge.")
        return {}

    # Calculate a random amount within the configured range, not exceeding balance
    # Ensure the random amount is within the min/max and also less than or equal
    # to the current balance.
    # Convert to int for random.randint, then back to Decimal for consistency
    # with other Decimal amounts.
    # If the effective range is empty, return an empty dict
    if int(min_amount_wei) > int(min(max_amount_wei, current_eth_balance_wei)):
        logger.warning("Min bridge amount is greater than available balance or max amount.")
        return {}
    amount_to_bridge_wei = random.randint(
        int(min_amount_wei), int(min(max_amount_wei, current_eth_balance_wei))
    )
    amount_eth = Web3.from_wei(amount_to_bridge_wei, "ether")

    to_l2 = random.random() < to_l2_probability

    return {"amount_eth": amount_eth, "to_l2": to_l2}


def _randomize_swap_parameters(
    swap_config: Dict[str, Any], state: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Randomizes parameters for a swap action."""
    tokens = swap_config["tokens"]
    dexs = swap_config["dexs"]
    slippage_bps = swap_config["slippage_bps"]

    # Filter tokens to only include those with a positive balance
    available_tokens = [
        t for t in tokens if state["balances"].get(
            get_token_info(t, config)["address"], 0
        ) > 0
    ]

    if len(available_tokens) < 2:
        logger.warning("Not enough tokens with balance to perform a swap.")
        return {}

    token_in_symbol = random.choice(available_tokens)
    token_out_symbol = random.choice([t for t in tokens if t != token_in_symbol])

    token_in_info = get_token_info(token_in_symbol, config)
    token_out_info = get_token_info(token_out_symbol, config)

    if not token_in_info or not token_out_info:
        logger.error("Could not get token info for swap.")
        return {}

    token_in_address = token_in_info["address"]
    token_out_address = token_out_info["address"]

    # Use a portion of the available balance for the swap
    amount_in_wei = state["balances"].get(token_in_address, 0) // 2
    if amount_in_wei == 0:
        logger.warning(f"No balance for {token_in_symbol} to swap.")
        return {}

    dex_name = random.choice(dexs)

    return {
        "token_in_address": token_in_address,
        "token_out_address": token_out_address,
        "amount_in": amount_in_wei,
        "dex_name": dex_name,
        "slippage_bps": slippage_bps,
    }


def _randomize_lend_borrow_parameters(
    state: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Randomizes parameters for a lend/borrow action."""
    lend_borrow_config = config["random_activity"]["lend_borrow"]
    actions = lend_borrow_config["actions"]
    feasible_actions = []

    for action_type in actions:
        if action_type == "supply":  # Can supply any token if balance > 0
            for token_symbol, token_info in config["tokens"].items():
                token_address = token_info.get("address")
                if token_symbol == "ETH":
                    token_address = NATIVE_ETH_ADDRESS
                if token_address and state["balances"].get(token_address, 0) > 0:
                    feasible_actions.append(
                        {
                            "action": "supply",
                            "token_address": token_address,
                            "amount": state["balances"][token_address] // 2,
                            "lending_protocol_name": random.choice(
                                lend_borrow_config.get("protocols", ["eralend"])
                            ),
                        }
                    )
        elif action_type == "withdraw":
            # Can withdraw if there's a supplied position (simplified)
            # Simulate having a position
            if random.random() < 0.5:
                for token_symbol, token_info in config["tokens"].items():
                    token_address = token_info.get("address")
                    if token_symbol == "ETH":
                        token_address = NATIVE_ETH_ADDRESS
                    if token_address:
                        feasible_actions.append(
                            {
                                "action": "withdraw",
                                "token_address": token_address,
                                "amount": random.randint(1, 100) * 10**6,
                                "lending_protocol_name": random.choice(
                                    lend_borrow_config.get("protocols", ["eralend"])
                                ),
                            }
                        )
        elif action_type == "borrow":
            # Can borrow if collateral is supplied (simplified)
            # Simulate having collateral
            if random.random() < 0.5:
                for token_symbol, token_info in config["tokens"].items():
                    token_address = token_info.get("address")
                    if token_symbol == "ETH":
                        token_address = NATIVE_ETH_ADDRESS
                    if token_address:
                        feasible_actions.append(
                            {
                                "action": "borrow",
                                "token_address": token_address,
                                "amount": random.randint(1, 50) * 10**6,
                                "lending_protocol_name": random.choice(
                                    lend_borrow_config.get("protocols", ["eralend"])
                                ),
                            }
                        )
        elif action_type == "repay":
            # Can repay if there's a borrowed position (simplified)
            # Simulate having a borrowed position
            if random.random() < 0.5:
                for token_symbol, token_info in config["tokens"].items():
                    token_address = token_info.get("address")
                    if token_symbol == "ETH":
                        token_address = NATIVE_ETH_ADDRESS
                    if token_address:
                        feasible_actions.append(
                            {
                                "action": "repay",
                                "token_address": token_address,
                                "amount": random.randint(1, 50) * 10**6,
                                "lending_protocol_name": random.choice(
                                    lend_borrow_config.get("protocols", ["eralend"])
                                ),
                            }
                        )
        elif action_type == "set_collateral":
            # Can set collateral if there's a supplied position (simplified)
            # Simulate having a supplied position
            if random.random() < 0.5:
                for token_symbol, token_info in config["tokens"].items():
                    token_address = token_info.get("address")
                    if token_symbol == "ETH":
                        token_address = NATIVE_ETH_ADDRESS
                    if token_address:
                        feasible_actions.append(
                            {
                                "action": "set_collateral",
                                "token_address": token_address,
                                "amount": random.choice([True, False]),
                                "lending_protocol_name": random.choice(
                                    lend_borrow_config.get("protocols", ["eralend"])
                                ),
                            }
                        )

    if not feasible_actions:
        logger.warning("No feasible lend/borrow actions based on current state.")
        return {}

    return random.choice(feasible_actions)


def _select_action_type(action_weights: Dict[str, float]) -> str:
    """Placeholder for selecting action type based on weights."""
    if not action_weights:
        raise ValueError("Action weights cannot be empty.")
    pass
    return random.choices(
        list(action_weights.keys()), weights=list(action_weights.values()), k=1
    )[0]


def _validate_random_activity_config(config: Dict[str, Any]) -> bool:
    """Placeholder for validating random activity config."""
    if not config:
        return False
    # Basic validation for random_activity section
    if "random_activity" not in config:
        return False
    activity_config = config["random_activity"]
    if not all(
        k in activity_config for k in ["min_actions", "max_actions", "action_types"]
    ):
        return False
    if not isinstance(activity_config["action_types"], list) or not (
        activity_config["action_types"]
    ):
        return False
    pass
    return True


def _check_action_feasibility(
    action_type: str, params: Dict[str, Any], state: Dict[str, Any]
) -> bool:
    """Checks if a randomized action is feasible given the current state."""
    if action_type == "bridge_eth":
        amount_eth = params["amount_eth"]
        amount_wei = convert_to_wei(amount_eth)
        current_eth_balance_wei = state["balances"].get(NATIVE_ETH_ADDRESS, 0)
        return current_eth_balance_wei >= amount_wei
    elif action_type == "swap_tokens":
        token_in_address = params["token_in_address"]
        amount_in = params["amount_in"]
        current_token_in_balance = state["balances"].get(token_in_address, 0)
        return current_token_in_balance >= amount_in
    elif action_type == "lend_borrow":
        # For lend/borrow, feasibility is handled during randomization
        # based on simulated positions/balances.
        return True
    return False


def _update_internal_state(
    state: Dict[str, Any], action_result: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Updates the internal state based on the result of an action."""
    new_state = state.copy()
    action_type = action_result["action_type"]
    success = action_result["success"]

    if not success:
        logger.warning(f"Action {action_type} failed, state not updated.")
        return new_state

    if action_type == "bridge_eth":
        amount_eth = action_result["amount_eth"]
        amount_wei = convert_to_wei(amount_eth)
        if action_result["to_l2"]:
            # ETH moved from L1 to L2 (simulated)
            # For now, we only track L2 balances, so this means an increase
            new_state["balances"][NATIVE_ETH_ADDRESS] = (
                new_state["balances"].get(NATIVE_ETH_ADDRESS, 0) + amount_wei
            )
        else:
            # ETH moved from L2 to L1 (simulated)
            new_state["balances"][NATIVE_ETH_ADDRESS] = max(
                0, new_state["balances"].get(NATIVE_ETH_ADDRESS, 0) - amount_wei
            )
        logger.info(
            f"State updated after bridge: ETH balance now "
            f"{Web3.from_wei(new_state['balances'][NATIVE_ETH_ADDRESS], 'ether')} ETH"
        )
    elif action_type == "swap_tokens":
        token_in_address = action_result["token_in_address"]
        amount_in = action_result["amount_in"]
        token_out_address = action_result["token_out_address"]
        # For simplicity, assume a 1:1 swap for state update,
        # in reality, this would depend on actual swap output.
        # Deduct token_in amount
        new_state["balances"][token_in_address] = max(
            0, new_state["balances"].get(token_in_address, 0) - amount_in
        )
        # Add token_out amount (simplified)
        new_state["balances"][token_out_address] = (
            new_state["balances"].get(token_out_address, 0) + amount_in
        )
        logger.info(
            f"State updated after swap: {token_in_address} balance now "
            f"{new_state['balances'][token_in_address]}, "
            f"{token_out_address} balance now "
            f"{new_state['balances'][token_out_address]}"
        )
    elif action_type == "lend_borrow":
        action = action_result["action"]
        token_address = action_result["token_address"]
        amount = action_result["amount"]

        if action == "supply":
            new_state["balances"][token_address] = max(
                0, new_state["balances"].get(token_address, 0) - amount
            )
            logger.info(
                f"State updated after supply: {token_address} balance now "
                f"{new_state['balances'][token_address]}"
            )
        elif action == "withdraw":
            new_state["balances"][token_address] = (
                new_state["balances"].get(token_address, 0) + amount
            )
            logger.info(
                f"State updated after withdraw: {token_address} balance now "
                f"{new_state['balances'][token_address]}"
            )
        elif action == "borrow":
            new_state["balances"][token_address] = (
                new_state["balances"].get(token_address, 0) + amount
            )
            logger.info(
                f"State updated after borrow: {token_address} balance now "
                f"{new_state['balances'][token_address]}"
            )
        elif action == "repay":
            new_state["balances"][token_address] = max(
                0, new_state["balances"].get(token_address, 0) - amount
            )
            logger.info(
                f"State updated after repay: {token_address} balance now "
                f"{new_state['balances'][token_address]}"
            )
        elif action == "set_collateral":
            logger.info(
                f"State updated after set_collateral: {token_address} "
                f"useAsCollateral set to {action_result['amount']}"
            )

    return new_state


def _execute_single_action(
    action_type: str,
    user_address: str,
    private_key: str,
    params: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Executes a single action."""
    action_functions = {
        "bridge_eth": bridge_eth,
        "swap_tokens": swap_tokens,
        "lend_borrow": lend_borrow,
    }
    func = action_functions.get(action_type)

    if not func:
        return {
            "success": False,
            "action_type": action_type,
            "error": "Unknown action type",
        }

    # Call the function with the correct arguments
    if action_type == "bridge_eth":
        success, result = func(
            user_address=user_address,
            private_key=private_key,
            amount_eth=Decimal(str(params["amount_eth"])),
            to_l2=params["to_l2"],
            config=config,
        )
    elif action_type == "swap_tokens":
        success, result = func(
            user_address=user_address,
            private_key=private_key,
            token_in_address=params["token_in_address"],
            token_out_address=params["token_out_address"],
            amount_in=params["amount_in"],
            dex_name=params["dex_name"],
            slippage_bps=params["slippage_bps"],
            config=config,
        )
    else:
        # Placeholder for lend_borrow and other actions
        success, result = func(user_address, private_key, **params, config=config)

    return {"success": success, "action_type": action_type, "result": result, **params}


def perform_random_activity(
    user_address: str, private_key: str, config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Performs a sequence of random activities on zkSync Era.
    Activities include bridging ETH, swapping tokens, and lending/borrowing.
    """
    activity_config = config["random_activity"]
    
    # Check if random activity is enabled
    if not activity_config.get("enabled", True):
        logger.info("Random activity is disabled in config.")
        return []
    
    num_actions = random.randint(
        activity_config["min_actions"], activity_config["max_actions"]
    )
    action_types = activity_config["action_types"]
    action_results: List[Dict[str, Any]] = []

    # Get initial on-chain state
    current_state = _get_initial_onchain_state(user_address, config)
    if not current_state:
        logger.error("Failed to get initial on-chain state. Aborting random activity.")
        return []

    for i in range(num_actions):
        logger.info(f"Performing action {i + 1}/{num_actions}...")
        action_type = random.choice(action_types)
        params: Dict[str, Any] = {}

        if action_type == "bridge_eth":
            params = _randomize_bridge_parameters(user_address, current_state, config)
        elif action_type == "swap_tokens":
            params = _randomize_swap_parameters(
                config["random_activity"]["swap_tokens"], current_state, config
            )
        elif action_type == "lend_borrow":
            params = _randomize_lend_borrow_parameters(current_state, config)

        if not params or not _check_action_feasibility(
            action_type, params, current_state
        ):
            logger.warning(f"Skipping {action_type} due to infeasible parameters.")
            continue

        result = _execute_single_action(
            action_type, user_address, private_key, params, config
        )
        action_results.append(result)

        # Update internal state based on successful action
        if result["success"]:
            current_state = _update_internal_state(current_state, result, config)

        time.sleep(
            random.randint(activity_config["min_delay"], activity_config["max_delay"])
        )

    return action_results


def _estimate_l1_gas(
    w3_l1: Web3,
    bridge_contract: Contract,
    user_address: str,
    amount_wei: int,
    l2_gas_limit: int,
    l2_gas_per_pubdata_byte_limit: int,
) -> int:
    """Estimates L1 gas for a deposit transaction."""
    try:
        # Create a dummy transaction to estimate gas
        dummy_tx = bridge_contract.functions.requestL2Transaction(
            ZERO_ADDRESS,
            amount_wei,
            Web3.to_checksum_address(user_address),
            l2_gas_limit,
            l2_gas_per_pubdata_byte_limit,
            [],
            Web3.to_checksum_address(user_address),
        ).build_transaction(
            {
                "from": user_address,
                "value": amount_wei,
                "chainId": ZKSYNC_ERA_CHAIN_ID,  # This should be L1 chain ID
                "nonce": w3_l1.eth.get_transaction_count(user_address),
                "gasPrice": w3_l1.eth.gas_price,
            }
        )
        return w3_l1.eth.estimate_gas(dummy_tx)
    except Exception as e:
        logger.warning(f"L1 gas estimation failed: {e}, using default")
        return 200000  # Default L1 gas limit


def _build_l1_deposit_transaction(
    w3_l1: Web3,
    bridge_contract: Contract,
    user_address: str,
    amount_wei: int,
    l2_gas_limit: int,
    l2_gas_per_pubdata_byte_limit: int,
) -> Dict[str, Any]:
    """Builds a transaction for depositing ETH from L1 to L2."""
    try:
        # Estimate gas for L1 transaction
        estimated_gas = _estimate_l1_gas(
            w3_l1,
            bridge_contract,
            user_address,
            amount_wei,
            l2_gas_limit,
            l2_gas_per_pubdata_byte_limit,
        )
        gas_limit = int(estimated_gas * 1.2)  # Add a buffer
    except Exception as e:
        logger.warning(f"Gas estimation failed: {e}, using default")
        gas_limit = 200000  # Default L1 gas limit

    return bridge_contract.functions.requestL2Transaction(
        ZERO_ADDRESS,
        amount_wei,
        Web3.to_checksum_address(user_address),
        l2_gas_limit,
        l2_gas_per_pubdata_byte_limit,
        [],
        Web3.to_checksum_address(user_address),
    ).build_transaction(
        {
            "from": user_address,
            "value": amount_wei,
            "chainId": ZKSYNC_ERA_CHAIN_ID,  # This should be L1 chain ID
            "nonce": w3_l1.eth.get_transaction_count(user_address),
            "gasPrice": w3_l1.eth.gas_price,
            "gas": gas_limit,
        }
    )


def _build_l2_withdrawal_transaction(
    w3_l2: Web3, bridge_contract: Contract, user_address: str, amount_wei: int
) -> Dict[str, Any]:
    """Builds a transaction for withdrawing ETH from L2 to L1."""
    try:
        # Estimate gas for L2
        estimated_gas = bridge_contract.functions.withdraw(
            NATIVE_ETH_ADDRESS, amount_wei
        ).estimate_gas(
            {
                "from": user_address,
                "chainId": ZKSYNC_ERA_CHAIN_ID,
                "nonce": w3_l2.eth.get_transaction_count(user_address),
                "gasPrice": w3_l2.eth.gas_price,
            }
        )
        gas_limit = int(estimated_gas * 1.5)  # L2 gas multiplier
    except Exception as e:
        logger.warning(f"Gas estimation failed: {e}, using default")
        gas_limit = 100000  # Default L2 gas limit

    return bridge_contract.functions.withdraw(
        NATIVE_ETH_ADDRESS, amount_wei
    ).build_transaction(
        {
            "from": user_address,
            "chainId": ZKSYNC_ERA_CHAIN_ID,
            "nonce": w3_l2.eth.get_transaction_count(user_address),
            "gasPrice": w3_l2.eth.gas_price,
            "gas": gas_limit,
        }
    )


def _build_and_send_swap_transaction(
    w3: Web3,
    contract_function: ContractFunction,
    transaction_params: Dict[str, Any],
    private_key: str,
    user_address: str,
    action_name: str,
) -> Tuple[bool, str]:
    """Builds and sends a swap transaction."""
    try:
        tx_hash = build_and_send_transaction(
            w3, contract_function.build_transaction(transaction_params), private_key
        )
        logger.info(f"Successfully executed {action_name} transaction: {tx_hash.hash.hex()}")
        return True, tx_hash.hash.hex()
    except Exception as e:
        logger.error(f"Failed to execute {action_name} transaction: {e}")
        return False, str(e)


def _execute_syncswap_swap(
    w3: Web3,
    router_contract: Contract,
    user_address: str,
    private_key: str,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    slippage_bps: int,
) -> Tuple[bool, str]:
    """Executes a SyncSwap swap."""
    try:
        path = [token_in_address, token_out_address] # Simplified path for now
        # Get expected amount out
        amounts_out = router_contract.functions.getAmountsOut(amount_in, path).call()
        amount_out_min = int(amounts_out[-1] * (10000 - slippage_bps) / 10000)

        # Determine the swap function based on token types
        if token_in_address == NATIVE_ETH_ADDRESS:
            # Swapping ETH for ERC20
            contract_function = router_contract.functions.swapExactETHForTokens(
                amount_out_min,
                path,
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address, "value": amount_in}
        elif token_out_address == NATIVE_ETH_ADDRESS:
            # Swapping ERC20 for ETH
            contract_function = router_contract.functions.swapExactTokensForETH(
                amount_in,
                amount_out_min,
                path,
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address}
        else:
            # Swapping ERC20 for ERC20
            contract_function = router_contract.functions.swapExactTokensForTokens(
                amount_in,
                amount_out_min,
                path,
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address}

        return _build_and_send_swap_transaction(
            w3,
            contract_function,
            transaction_params,
            private_key,
            user_address,
            "SyncSwap",
        )
    except Exception as e:
        logger.error(f"SyncSwap failed: {e}")
        return False, str(e)


def bridge_eth(
    user_address: str,
    private_key: str,
    amount_eth: Decimal,
    to_l2: bool,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Bridges ETH between L1 and L2 on zkSync Era.
    Args:
        user_address (str): The user's wallet address.
        private_key (str): The private key of the user's wallet.
        amount_eth (Decimal): The amount of ETH to bridge.
        to_l2 (bool): True to bridge from L1 to L2, False to bridge from L2 to L1.
        config (Dict[str, Any]): Configuration dictionary.
    Returns:
        Tuple[bool, str]: True if successful, False otherwise, and a message.
    """
    amount_wei = convert_to_wei(amount_eth)

    if to_l2:
        w3_l1 = _get_web3_instance(config, "ethereum")
        bridge_contract = _get_contract(
            w3_l1, ZKSYNC_ERA_BRIDGE_ADDRESS, _get_l1_bridge_abi()
        )

        # These gas limits are placeholders and should be estimated dynamically
        l2_gas_limit = 1000000
        l2_gas_per_pubdata_byte_limit = 800

        try:
            transaction = _build_l1_deposit_transaction(
                w3_l1,
                bridge_contract,
                user_address,
                amount_wei,
                l2_gas_limit,
                l2_gas_per_pubdata_byte_limit,
            )
            tx_hash = send_signed_transaction(w3_l1, transaction, private_key)
            logger.info(
                f"Successfully initiated L1 to L2 bridge for {amount_eth} ETH. "
                f"Transaction hash: {tx_hash.hex()}"
            )
            return True, tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to bridge ETH from L1 to L2: {e}")
            return False, str(e)
    else:
        w3_l2 = _get_web3_instance(config, "zksync")
        bridge_contract = _get_contract(
            w3_l2,
            ZKSYNC_ERA_BRIDGE_ADDRESS,
            _get_l2_bridge_abi(),  # Using _get_l2_bridge_abi() now
        )

        try:
            transaction = _build_l2_withdrawal_transaction(
                w3_l2, bridge_contract, user_address, amount_wei
            )
            tx_hash = send_signed_transaction(w3_l2, transaction, private_key)
            logger.info(
                f"Successfully initiated L2 to L1 withdrawal for {amount_eth} ETH. "
                f"Transaction hash: {tx_hash.hex()}"
            )
            return True, tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to withdraw ETH from L2 to L1: {e}")
            return False, str(e)


def swap_tokens(
    user_address: str,
    private_key: str,
    token_in_address: str,
    token_out_address: str,
    amount_in: int,
    dex_name: str,
    slippage_bps: int,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Performs a token swap on a specified DEX on zkSync Era.
    Args:
        user_address (str): The user's wallet address.
        private_key (str): The private key of the user's wallet.
        token_in_address (str): Address of the token to swap from.
        token_out_address (str): Address of the token to swap to.
        amount_in (int): Amount of token_in (in wei) to swap.
        dex_name (str): Name of the DEX to use (e.g., "syncswap").
        slippage_bps (int): Slippage in basis points (e.g., 50 for 0.5%).
        config (Dict[str, Any]): Configuration dictionary.
    Returns:
        Tuple[bool, str]: True if successful, False otherwise, and a message.
    """
    w3 = _get_web3_instance(config, "zksync")

    dex_config = config["networks"]["zksync"]["dexs"].get(dex_name)
    if not dex_config:
        return False, f"DEX {dex_name} not configured."

    router_address = dex_config.get("router_address")
    router_abi = dex_config.get("router_abi")

    if not router_address or not router_abi:
        return False, f"Router address or ABI not found for DEX {dex_name}."

    router_contract = _get_contract(w3, router_address, router_abi)

    # Handle token approval for token_in if it's an ERC20
    success, approval_result = _handle_token_approval(
        w3, token_in_address, user_address, private_key, router_address, amount_in
    )
    if not success:
        return False, f"Token approval failed: {approval_result}"

    # Determine the swap function based on DEX and token types
    # This is a simplified example; real DEX integrations are more complex
    try:
        if token_in_address == NATIVE_ETH_ADDRESS:
            # Swapping ETH for ERC20
            # Assuming a function like swapExactETHForTokens
            contract_function = router_contract.functions.swapExactETHForTokens(
                int(amount_in * (1 - slippage_bps / 10000)),  # minAmountOut
                [NATIVE_ETH_ADDRESS, token_out_address],
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address, "value": amount_in}
        elif token_out_address == NATIVE_ETH_ADDRESS:
            # Swapping ERC20 for ETH
            # Assuming a function like swapExactTokensForETH
            contract_function = router_contract.functions.swapExactTokensForETH(
                amount_in,
                int(amount_in * (1 - slippage_bps / 10000)),  # minAmountOut
                [token_in_address, NATIVE_ETH_ADDRESS],
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address}
        else:
            # Swapping ERC20 for ERC20
            # Assuming a function like swapExactTokensForTokens
            contract_function = router_contract.functions.swapExactTokensForTokens(
                amount_in,
                int(amount_in * (1 - slippage_bps / 10000)),  # minAmountOut
                [token_in_address, token_out_address],
                Web3.to_checksum_address(user_address),
                int(time.time()) + 300,  # deadline 5 minutes from now
            )
            transaction_params = {"from": user_address}

        tx_hash = build_and_send_transaction(
            w3, contract_function.build_transaction(transaction_params), private_key
        )
        logger.info(
            f"Successfully swapped {amount_in} of {token_in_address} for "
            f"{token_out_address} on {dex_name}. Transaction hash: {tx_hash.hex()}"
        )
        return True, tx_hash.hex()
    except Exception as e:
        logger.error(f"Failed to perform swap on {dex_name}: {e}")
        return False, str(e)


def lend_borrow(
    user_address: str,
    private_key: str,
    action: str,
    token_address: str,
    amount: int,
    lending_protocol_name: str,
    config: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Performs a lending or borrowing action on a specified protocol on zkSync Era.
    Args:
        user_address (str): The user's wallet address.
        private_key (str): The private key of the user's wallet.
        action (str): The lending action to perform (e.g., "supply", "withdraw",
                      "borrow", "repay", "set_collateral").
        token_address (str): The address of the token involved.
        amount (int): The amount of token (in wei) for the action.
                      For "set_collateral", this is a boolean (1 for True, 0 for False).
        lending_protocol_name (str): The name of the lending protocol (e.g., "eralend").
        config (Dict[str, Any]): Configuration dictionary.
    Returns:
        Tuple[bool, str]: True if successful, False otherwise, and a message.
    """
    return _execute_lending_action(
        user_address,
        private_key,
        action,
        token_address,
        amount,
        lending_protocol_name,
        config,
    )
