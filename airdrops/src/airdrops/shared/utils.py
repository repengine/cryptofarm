from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt, Wei, Nonce, Address, ChecksumAddress, ENS  # type: ignore
from web3.contract import Contract
from eth_account import Account
from eth_account.signers.local import LocalAccount
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, List, Union
import time
import uuid
import json
import os


def get_web3_provider(rpc_url: str, chain_id: int) -> Web3:
    """
    Initializes and returns a Web3 provider.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if chain_id in [42161, 100, 10, 59144]:  # Arbitrum, Gnosis, Optimism, Linea
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def sign_and_send_transaction(
    w3: Web3,
    transaction: Dict[str, Any],
    private_key: str,
    timeout: int = 120
) -> Optional[Dict[str, Any]]:
    """
    Signs and sends a transaction, waiting for the receipt.
    """
    account: LocalAccount = Account.from_key(private_key)
    signed_transaction = account.sign_transaction(transaction)
    tx_hash = w3.eth.send_raw_transaction(
        signed_transaction.rawTransaction  # type: ignore[attr-defined]
    )

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt  # type: ignore[return-value]
        except TransactionNotFound:
            time.sleep(1)
    return None


def get_contract_instance(w3: Web3, abi: List[Any], address: str) -> Contract:
    """
    Returns a contract instance.
    """
    return w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)


def get_token_balance(w3: Web3, token_address: str, wallet_address: str) -> int:
    """
    Returns the token balance of a wallet.
    """
    token_contract = get_contract_instance(
        w3,
        [],
        token_address  # Assuming standard ERC20 ABI
    )
    balance = token_contract.functions.balanceOf(w3.to_checksum_address(wallet_address)).call()
    return int(balance)


def get_eth_balance(w3: Web3, wallet_address: str) -> int:
    """
    Returns the ETH balance of a wallet.
    """
    return w3.eth.get_balance(w3.to_checksum_address(wallet_address))


def approve_token(
    w3: Web3,
    token_address: str,
    spender_address: str,
    amount: int,
    private_key: str,
    nonce: Optional[int] = None
) -> Optional[TxReceipt]:
    """
    Approves a token for spending by a given spender address.
    """
    account: LocalAccount = Account.from_key(private_key)
    token_contract = get_contract_instance(
        w3,
        [],
        token_address  # Assuming standard ERC20 ABI
    )
    if nonce is None:
        nonce = w3.eth.get_transaction_count(account.address)

    transaction = token_contract.functions.approve(
        spender_address,
        amount
    ).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 100000,  # Placeholder, should estimate gas
        'gasPrice': w3.eth.gas_price,
        'nonce': Nonce(nonce),  # Cast nonce to Nonce
    })
    result = sign_and_send_transaction(
        w3,
        transaction,  # type: ignore[arg-type]
        private_key
    )
    return result  # type: ignore[return-value]


def estimate_gas_price(w3: Web3) -> Wei:
    """
    Estimates the current gas price.
    """
    return w3.eth.gas_price


def get_latest_block_number(w3: Web3) -> int:
    """
    Returns the latest block number.
    """
    return w3.eth.block_number


def get_transaction_count(w3: Web3, address: Union[Address, ChecksumAddress, ENS]) -> int:
    """
    Returns the transaction count for an address.
    """
    return w3.eth.get_transaction_count(address)


def hex_to_int(hex_str: str) -> int:
    """
    Converts a hexadecimal string to an integer.
    """
    return int(hex_str, 16)


def int_to_hex(int_val: int) -> str:
    """
    Converts an integer to a hexadecimal string.
    """
    return hex(int_val)


def to_checksum_address(address: str) -> ChecksumAddress:
    """
    Converts an address to a checksum address.
    """
    return Web3.to_checksum_address(address)


def convert_to_ether(wei_value: int) -> float:
    """
    Converts Wei to Ether.
    """
    return float(Web3.from_wei(wei_value, 'ether'))


def convert_to_wei(ether_value: float) -> int:
    """
    Converts Ether to Wei.
    """
    return Web3.to_wei(ether_value, 'ether')


def int_to_decimal_for_token(amount: int, decimals: int) -> Decimal:
    """
    Converts an integer amount to a decimal representation based on token decimals.
    """
    return Decimal(amount) / (Decimal(10) ** decimals)


def convert_to_decimal(value: Any) -> Decimal:
    """
    Converts a given value to a Decimal type.

    Args:
        value: The value to convert to Decimal.

    Returns:
        Decimal: The converted Decimal value.

    Raises:
        TypeError: If the value type cannot be converted to Decimal.
        ValueError: If the string representation is invalid for Decimal conversion.

    Example:
        >>> convert_to_decimal(123.45)
        Decimal('123.45')
        >>> convert_to_decimal("99.99")
        Decimal('99.99')
    """
    # Return the same object if it's already a Decimal
    if isinstance(value, Decimal):
        return value

    # Check for invalid types that can't be converted
    if isinstance(value, (list, dict, tuple, set)):
        raise TypeError(f"Cannot convert {type(value).__name__} to Decimal")

    try:
        return Decimal(str(value))
    except InvalidOperation as e:
        raise ValueError(f"Invalid value for Decimal conversion: {value}") from e


def get_token_info(w3: Web3, token_address: str) -> Dict[str, Any]:
    """
    Retrieves token information (name, symbol, decimals).
    """
    token_contract = w3.eth.contract(
        address=w3.to_checksum_address(token_address),
        abi=[
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
    )
    name = token_contract.functions.name().call()
    symbol = token_contract.functions.symbol().call()
    decimals = token_contract.functions.decimals().call()
    return {"name": name, "symbol": symbol, "decimals": decimals}


def get_current_timestamp() -> int:
    """
    Returns the current Unix timestamp in seconds.

    Returns:
        int: Current Unix timestamp in seconds.

    Example:
        >>> timestamp = get_current_timestamp()
        >>> isinstance(timestamp, int)
        True
    """
    return int(time.time())


class ConfigError(Exception):
    """
    Exception raised for configuration-related errors.

    This exception is raised when there are issues loading, parsing,
    or saving configuration files.
    """
    pass


def format_currency(
    amount: Union[Decimal, float, int],
    currency_symbol: str = "$",
    precision: int = 2
) -> str:
    """
    Formats a numeric value as a currency string.

    Args:
        amount: The numeric value to format.
        currency_symbol: The currency symbol to use (default: "$").
        precision: Number of decimal places to show (default: 2).

    Returns:
        str: Formatted currency string.

    Example:
        >>> format_currency(Decimal("123.456"))
        '$123.46'
        >>> format_currency(Decimal("123.45678"), precision=4)
        '$123.4568'
        >>> format_currency(Decimal("-123.45"))
        '-$123.45'
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    # Handle negative values
    if amount < 0:
        return f"-{currency_symbol}{abs(amount):.{precision}f}"

    return f"{currency_symbol}{amount:.{precision}f}"


def generate_unique_id() -> str:
    """
    Generates a unique identifier string.

    Returns:
        str: A unique identifier string.

    Example:
        >>> uid = generate_unique_id()
        >>> isinstance(uid, str)
        True
        >>> len(uid) > 0
        True
    """
    return str(uuid.uuid4())


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads configuration from a JSON file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dict[str, Any]: The loaded configuration data.

    Raises:
        ConfigError: If the file doesn't exist or contains invalid JSON.

    Example:
        >>> # Assuming config.json exists with {"key": "value"}
        >>> config = load_config("config.json")
        >>> isinstance(config, dict)
        True
    """
    try:
        if not os.path.exists(config_path):
            raise ConfigError(f"Config file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            result: Dict[str, Any] = json.load(f)
            return result
    except json.JSONDecodeError as e:
        raise ConfigError(f"Error parsing config file {config_path}: {e}") from e
    except IOError as e:
        raise ConfigError(f"Error reading config file {config_path}: {e}") from e


def save_config(config_data: Dict[str, Any], config_path: str) -> None:
    """
    Saves configuration data to a JSON file.

    Args:
        config_data: The configuration data to save.
        config_path: Path where to save the configuration file.

    Raises:
        ConfigError: If there's an error saving the file.

    Example:
        >>> config = {"setting": "value"}
        >>> save_config(config, "config.json")
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except (IOError, OSError) as e:
        raise ConfigError(f"Error saving config file {config_path}: {e}") from e


__all__ = [
    "get_web3_provider",
    "sign_and_send_transaction",
    "get_contract_instance",
    "get_token_balance",
    "get_eth_balance",
    "approve_token",
    "estimate_gas_price",
    "get_latest_block_number",
    "get_transaction_count",
    "hex_to_int",
    "int_to_hex",
    "to_checksum_address",
    "convert_to_ether",
    "convert_to_wei",
    "int_to_decimal_for_token",
    "convert_to_decimal",
    "get_token_info",
    "get_current_timestamp",
    "format_currency",
    "generate_unique_id",
    "load_config",
    "save_config",
    "ConfigError",
]
