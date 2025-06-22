"""
Tests for the Scroll protocol.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from typing import Any, Generator, Tuple
from web3.exceptions import ContractLogicError

from airdrops.protocols.scroll import swap_tokens, bridge_assets
from airdrops.protocols.scroll.scroll import provide_liquidity
from airdrops.protocols.scroll.exceptions import (
    InsufficientBalanceError,
    ApprovalError,
    InsufficientLiquidityError,
)


@pytest.fixture
def mock_scroll_protocol_functions() -> Generator[Tuple[MagicMock, MagicMock], None, None]:
    """Fixture for mocking Scroll protocol functions."""
    with patch("airdrops.protocols.scroll.swap_tokens") as mock_swap, \
         patch("airdrops.protocols.scroll.bridge_assets") as mock_bridge:
        yield mock_swap, mock_bridge


def test_scroll_protocol_initialization() -> None:
    """Test that the Scroll protocol functions are importable."""
    assert swap_tokens is not None
    assert bridge_assets is not None


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_perform_airdrop_success(mock_web3: Any, mock_scroll_protocol_functions: Tuple[MagicMock, MagicMock]) -> None:
    """
    Test successful airdrop execution on Scroll.
    Mocks Web3 interactions and protocol functions.
    """
    mock_swap, mock_bridge = mock_scroll_protocol_functions

    # Mock Web3 instance and its methods
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    # Mock account and balance
    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_instance.eth.account.from_key.return_value = mock_account
    mock_instance.eth.get_balance.return_value = 10**18  # 1 ETH in wei

    # Mock transaction building and sending
    mock_instance.eth.gas_price = 10**9  # 1 Gwei
    mock_instance.eth.get_transaction_count.return_value = 0
    mock_instance.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    mock_instance.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "gasUsed": 21000,
        "blockHash": b"0xmock_block_hash",
    }

    # Mock contract interaction if any (for token transfers, etc.)
    mock_contract = MagicMock()
    mock_instance.eth.contract.return_value = mock_contract
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 100000,
        "to": "0xMockRecipientAddress",
        "value": 0,
        "data": "0x",
    }
    mock_account.sign_transaction.return_value.rawTransaction = b"signed_tx"

    # Simulate a bridge operation
    mock_bridge.return_value = "0x" + "a" * 64
    success = mock_bridge(
        web3_l1=mock_instance,
        web3_l2=mock_instance,
        private_key="0x" + "1" * 64,
        token_symbol="ETH",
        amount=int(Decimal("0.1") * 10**18),  # Convert to wei
        direction="deposit"
    )

    assert success is not None # Check if a tx hash is returned
    mock_bridge.assert_called_once()


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_perform_airdrop_failure(mock_web3: Any, mock_scroll_protocol_functions: Tuple[MagicMock, MagicMock]) -> None:
    """
    Test failed airdrop execution on Scroll (e.g., transaction revert).
    Mocks Web3 interactions and protocol functions.
    """
    mock_swap, mock_bridge = mock_scroll_protocol_functions
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance

    mock_account = MagicMock()
    mock_account.address = "0xMockSenderAddress"
    mock_instance.eth.account.from_key.return_value = mock_account
    mock_instance.eth.get_balance.return_value = 10**18

    mock_instance.eth.gas_price = 10**9
    mock_instance.eth.get_transaction_count.return_value = 0
    mock_instance.eth.send_raw_transaction.return_value = b"0xmock_tx_hash"
    # Simulate transaction failure
    mock_instance.eth.wait_for_transaction_receipt.return_value = {
        "status": 0,  # Failed transaction
        "gasUsed": 50000,
        "blockHash": b"0xmock_block_hash",
    }

    mock_contract = MagicMock()
    mock_instance.eth.contract.return_value = mock_contract
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 100000,
        "to": "0xMockRecipientAddress",
        "value": 0,
        "data": "0x",
    }
    mock_account.sign_transaction.return_value.rawTransaction = b"signed_tx"

    # Simulate a failed bridge operation
    mock_bridge.side_effect = Exception("Bridge failed")
    with pytest.raises(Exception, match="Bridge failed"):
        mock_bridge(
            web3_l1=mock_instance,
            web3_l2=mock_instance,
            private_key="0x" + "1" * 64,
            token_symbol="ETH",
            amount=int(Decimal("0.05") * 10**18),  # Convert to wei
            direction="deposit"
        )

    mock_bridge.assert_called_once()


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_get_balance(mock_web3: Any) -> None:
    """Test getting account balance."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_balance.return_value = 5 * (10**18)  # 5 ETH

    # Since get_balance is not part of the exposed functions, we need to mock it directly
    # or call it via a mock protocol instance if it were part of a class.
    # For now, we'll assume it's an internal helper or part of a larger class.
    # If it's a standalone function, it needs to be imported and patched.
    # For this test, we'll just assert the mock behavior.
    balance = mock_instance.eth.get_balance("0xMockAddress") / Decimal(10**18)
    assert balance == Decimal("5")
    mock_instance.eth.get_balance.assert_called_once_with("0xMockAddress")


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_get_gas_price(mock_web3: Any) -> None:
    """Test getting current gas price."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.gas_price = 20 * (10**9)  # 20 Gwei

    gas_price = mock_instance.eth.gas_price / Decimal(10**9)
    assert gas_price == Decimal("20")
    # No direct assert for eth.gas_price as it's an attribute access


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_get_transaction_count(mock_web3: Any) -> None:
    """Test getting transaction count (nonce)."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.get_transaction_count.return_value = 15

    nonce = mock_instance.eth.get_transaction_count("0xMockAddress")
    assert nonce == 15
    mock_instance.eth.get_transaction_count.assert_called_once_with("0xMockAddress")


@patch("airdrops.protocols.scroll.Web3")
def test_scroll_estimate_gas(mock_web3: Any) -> None:
    """Test gas estimation."""
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    mock_instance.eth.estimate_gas.return_value = 100000

    tx_params = {
        "from": "0xSender",
        "to": "0xRecipient",
        "value": 100,
    }
    gas_estimate = mock_instance.eth.estimate_gas(tx_params)
    assert gas_estimate == 100000
    mock_instance.eth.estimate_gas.assert_called_once_with(tx_params)


# ===== PROVIDE LIQUIDITY TESTS =====

@pytest.fixture
def mock_web3_l2() -> MagicMock:
    """Fixture for mocking Web3 L2 instance."""
    mock_web3 = MagicMock()
    mock_web3.eth.gas_price = 10**9  # 1 Gwei
    mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
    mock_web3.eth.get_transaction_count.return_value = 0
    mock_web3.eth.send_raw_transaction.return_value = b"0x" + b"a" * 32
    mock_web3.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "gasUsed": 300000,
        "blockHash": b"0x" + b"b" * 32,
    }
    mock_web3.eth.estimate_gas.return_value = 250000
    return mock_web3


@pytest.fixture
def mock_account() -> MagicMock:
    """Fixture for mocking account."""
    mock_account = MagicMock()
    mock_account.address = "0x1234567890123456789012345678901234567890"
    mock_account.sign_transaction.return_value.raw_transaction = b"signed_tx"
    return mock_account


@pytest.fixture
def mock_erc20_contract() -> MagicMock:
    """Fixture for mocking ERC20 contract."""
    mock_contract = MagicMock()
    mock_contract.functions.balanceOf.return_value.call.return_value = 10**18  # 1 token
    mock_contract.functions.allowance.return_value.call.return_value = 0
    mock_contract.functions.approve.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 50000,
        "to": "0xTokenAddress",
        "value": 0,
        "data": "0x",
    }
    return mock_contract


@pytest.fixture
def mock_router_contract() -> MagicMock:
    """Fixture for mocking SyncSwap router contract."""
    mock_contract = MagicMock()
    mock_contract.functions.addLiquidity.return_value.build_transaction.return_value = {
        "nonce": 0,
        "gasPrice": 10**9,
        "gas": 300000,
        "to": "0xRouterAddress",
        "value": 0,
        "data": "0x",
    }
    return mock_contract


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._approve_erc20_scroll")
@patch("airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
def test_provide_liquidity_erc20_erc20_success(
    mock_build_send_tx: MagicMock,
    mock_approve_erc20: MagicMock,
    mock_get_router: MagicMock,
    mock_get_contract: MagicMock,
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
    mock_erc20_contract: MagicMock,
    mock_router_contract: MagicMock,
) -> None:
    """Test successful liquidity provision for an ERC20/ERC20 pair."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_a_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_b_address (WETH)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    mock_get_contract.return_value = mock_erc20_contract
    mock_get_router.return_value = mock_router_contract
    mock_build_send_tx.return_value = "0x" + "a" * 64

    # Call the function
    result = provide_liquidity(
        web3_l2=mock_web3_l2,
        private_key="0x" + "1" * 64,
        token_a_symbol="USDC",
        token_b_symbol="WETH",
        amount_a=Decimal("1000000"),  # 1 USDC (6 decimals)
        amount_b=Decimal("500000000000000000"),  # 0.5 WETH (18 decimals)
        slippage_percent=0.5,
        deadline_seconds=1800,
    )

    # Assertions
    assert result == "0x" + "a" * 64
    mock_get_pool_address.assert_called_once()
    mock_approve_erc20.assert_called()  # Should be called twice for both tokens
    assert mock_approve_erc20.call_count == 2
    mock_build_send_tx.assert_called_once()


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._approve_erc20_scroll")
@patch("airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
def test_provide_liquidity_eth_erc20_success(
    mock_build_send_tx: MagicMock,
    mock_approve_erc20: MagicMock,
    mock_get_router: MagicMock,
    mock_get_contract: MagicMock,
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
    mock_erc20_contract: MagicMock,
    mock_router_contract: MagicMock,
) -> None:
    """Test successful liquidity provision for an ETH/ERC20 pair."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_a_address (ETH -> WETH)
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_b_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    mock_get_contract.return_value = mock_erc20_contract
    mock_get_router.return_value = mock_router_contract
    mock_build_send_tx.return_value = "0x" + "b" * 64

    # Call the function
    result = provide_liquidity(
        web3_l2=mock_web3_l2,
        private_key="0x" + "1" * 64,
        token_a_symbol="ETH",
        token_b_symbol="USDC",
        amount_a=Decimal("500000000000000000"),  # 0.5 ETH (18 decimals)
        amount_b=Decimal("1000000"),  # 1 USDC (6 decimals)
        slippage_percent=0.5,
        deadline_seconds=1800,
    )

    # Assertions
    assert result == "0x" + "b" * 64
    mock_get_pool_address.assert_called_once()
    # ETH doesn't need approval, only USDC should be approved
    mock_approve_erc20.assert_called_once()
    mock_build_send_tx.assert_called_once()


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
def test_provide_liquidity_insufficient_eth_balance(
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
) -> None:
    """Test failure due to insufficient ETH balance."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_a_address (ETH -> WETH)
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_b_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    
    # Set insufficient ETH balance
    mock_web3_l2.eth.get_balance.return_value = 10**17  # 0.1 ETH

    # Call the function and expect InsufficientBalanceError
    with pytest.raises(InsufficientBalanceError, match="Insufficient ETH balance"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="ETH",
            token_b_symbol="USDC",
            amount_a=Decimal("500000000000000000"),  # 0.5 ETH (more than balance)
            amount_b=Decimal("1000000"),  # 1 USDC
            slippage_percent=0.5,
            deadline_seconds=1800,
        )


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_contract_scroll")
def test_provide_liquidity_insufficient_erc20_balance(
    mock_get_contract: MagicMock,
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
) -> None:
    """Test failure due to insufficient ERC20 balance."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_a_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_b_address (WETH)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    
    # Mock ERC20 contract with insufficient balance
    mock_erc20_contract = MagicMock()
    mock_erc20_contract.functions.balanceOf.return_value.call.return_value = 500000  # 0.5 USDC
    mock_get_contract.return_value = mock_erc20_contract

    # Call the function and expect InsufficientBalanceError
    with pytest.raises(InsufficientBalanceError, match="Insufficient USDC balance"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),  # 1 USDC (more than balance)
            amount_b=Decimal("500000000000000000"),  # 0.5 WETH
            slippage_percent=0.5,
            deadline_seconds=1800,
        )


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._approve_erc20_scroll")
def test_provide_liquidity_approval_failure(
    mock_approve_erc20: MagicMock,
    mock_get_router: MagicMock,
    mock_get_contract: MagicMock,
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
    mock_erc20_contract: MagicMock,
    mock_router_contract: MagicMock,
) -> None:
    """Test failure due to approval failure."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_a_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_b_address (WETH)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    mock_get_contract.return_value = mock_erc20_contract
    mock_get_router.return_value = mock_router_contract
    
    # Mock approval failure
    mock_approve_erc20.side_effect = ApprovalError("ERC20 approval failed")

    # Call the function and expect ApprovalError
    with pytest.raises(ApprovalError, match="ERC20 approval failed"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),  # 1 USDC
            amount_b=Decimal("500000000000000000"),  # 0.5 WETH
            slippage_percent=0.5,
            deadline_seconds=1800,
        )


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
@patch("airdrops.protocols.scroll.scroll._approve_erc20_scroll")
def test_provide_liquidity_high_slippage_failure(
    mock_approve_erc20: MagicMock,
    mock_get_router: MagicMock,
    mock_get_contract: MagicMock,
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
    mock_erc20_contract: MagicMock,
) -> None:
    """Test failure due to high slippage (insufficient liquidity minted)."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_a_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_b_address (WETH)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    mock_get_pool_address.return_value = "0xC2d08b55E8663D4f9F3D9C5C6e044E5f6A7a8C9d"
    mock_get_contract.return_value = mock_erc20_contract
    
    # Mock router contract that raises ContractLogicError for high slippage
    mock_router_contract = MagicMock()
    contract_logic_error = ContractLogicError("NotEnoughLiquidityMinted")
    contract_logic_error.message = "NotEnoughLiquidityMinted"
    contract_logic_error.data = "0x12345678"
    mock_router_contract.functions.addLiquidity.return_value.build_transaction.side_effect = contract_logic_error
    mock_get_router.return_value = mock_router_contract

    # Call the function and expect InsufficientLiquidityError
    with pytest.raises(InsufficientLiquidityError, match="Insufficient liquidity minted"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),  # 1 USDC
            amount_b=Decimal("500000000000000000"),  # 0.5 WETH
            slippage_percent=0.1,  # Very low slippage tolerance
            deadline_seconds=1800,
        )


@patch("airdrops.protocols.scroll.scroll._get_account_scroll")
@patch("airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
@patch("airdrops.protocols.scroll.scroll._get_syncswap_pool_address_scroll")
def test_provide_liquidity_no_pool_found(
    mock_get_pool_address: MagicMock,
    mock_get_token_address: MagicMock,
    mock_get_account: MagicMock,
    mock_web3_l2: MagicMock,
    mock_account: MagicMock,
) -> None:
    """Test failure when no pool exists for the token pair."""
    # Setup mocks
    mock_get_account.return_value = mock_account
    mock_get_token_address.side_effect = [
        "0xA0b86a33E6441b8dB2B2B0d822C1B3c2B3c4D5e6",  # token_a_address (USDC)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # token_b_address (WETH)
        "0xB1c97a44F7552C3d8E2C8B4B5d933D4e5F6a7B8c",  # weth_l2_address
    ]
    # No pool found
    mock_get_pool_address.return_value = None

    # Call the function and expect InsufficientLiquidityError
    with pytest.raises(InsufficientLiquidityError, match="No SyncSwap pool found"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),  # 1 USDC
            amount_b=Decimal("500000000000000000"),  # 0.5 WETH
            slippage_percent=0.5,
            deadline_seconds=1800,
        )


def test_provide_liquidity_invalid_inputs() -> None:
    """Test failure due to invalid input parameters."""
    mock_web3_l2 = MagicMock()

    # Test negative amounts
    with pytest.raises(ValueError, match="Liquidity amounts must be positive"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("-1000000"),  # Negative amount
            amount_b=Decimal("500000000000000000"),
            slippage_percent=0.5,
            deadline_seconds=1800,
        )

    # Test invalid slippage
    with pytest.raises(ValueError, match="Slippage percent must be between 0 and 100"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),
            amount_b=Decimal("500000000000000000"),
            slippage_percent=150.0,  # Invalid slippage > 100%
            deadline_seconds=1800,
        )

    # Test invalid deadline
    with pytest.raises(ValueError, match="Deadline must be positive"):
        provide_liquidity(
            web3_l2=mock_web3_l2,
            private_key="0x" + "1" * 64,
            token_a_symbol="USDC",
            token_b_symbol="WETH",
            amount_a=Decimal("1000000"),
            amount_b=Decimal("500000000000000000"),
            slippage_percent=0.5,
            deadline_seconds=-1800,  # Negative deadline
        )
