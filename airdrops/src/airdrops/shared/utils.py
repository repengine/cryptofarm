from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.exceptions import TransactionNotFound, ContractCustomError, ContractLogicError
from web3.types import TxReceipt, Wei
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import Any, Dict, Optional
import time

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
    tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt
        except TransactionNotFound:
            time.sleep(1)
    return None

def get_contract_instance(w3: Web3, abi: list, address: str):
    """
    Returns a contract instance.
    """
    return w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)

def get_token_balance(w3: Web3, token_address: str, wallet_address: str) -> int:
    """
    Returns the token balance of a wallet.
    """
    token_contract = get_contract_instance(w3, [], token_address)  # Assuming standard ERC20 ABI
    return token_contract.functions.balanceOf(wallet_address).call()

def get_eth_balance(w3: Web3, wallet_address: str) -> int:
    """
    Returns the ETH balance of a wallet.
    """
    return w3.eth.get_balance(wallet_address)

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
    token_contract = get_contract_instance(w3, [], token_address)  # Assuming standard ERC20 ABI
    
    if nonce is None:
        nonce = w3.eth.get_transaction_count(account.address)

    transaction = token_contract.functions.approve(
        spender_address,
        amount
    ).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 100000,  # Placeholder, should estimate gas
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    return sign_and_send_transaction(w3, transaction, private_key)

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

def get_transaction_count(w3: Web3, address: str) -> int:
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

def to_checksum_address(address: str) -> str:
    """
    Converts an address to a checksum address.
    """
    return Web3.to_checksum_address(address)

def convert_to_ether(wei_value: int) -> float:
    """
    Converts Wei to Ether.
    """
    return Web3.from_wei(wei_value, 'ether')


def convert_to_wei(ether_value: float) -> int:
    """
    Converts Ether to Wei.
    """
    return Web3.to_wei(ether_value, 'ether')


def int_to_decimal_for_token(amount: int, decimals: int) -> float:
    """
    Converts an integer amount to a decimal representation based on token decimals.
    """
    return amount / (10 ** decimals)


def get_token_info(w3: Web3, token_address: str) -> Dict[str, Any]:
    """
    Retrieves token information (name, symbol, decimals).
    """
    token_contract = w3.eth.contract(
        address=w3.to_checksum_address(token_address),
        abi=[
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"}
        ]
    )
    name = token_contract.functions.name().call()
    symbol = token_contract.functions.symbol().call()
    decimals = token_contract.functions.decimals().call()
    return {"name": name, "symbol": symbol, "decimals": decimals}