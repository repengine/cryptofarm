import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from airdrops.protocols.hyperliquid import (
    spot_swap,
    stake_rotate,
    vault_cycle,
    evm_roundtrip,
    perform_random_onchain,
    _deposit_to_l1,
    _poll_l1_deposit_confirmation,
    _withdraw_from_l1,
    _poll_arbitrum_withdrawal_confirmation,
    _execute_stake_rotate,
    _execute_vault_cycle,
    _execute_spot_swap,
    _execute_evm_roundtrip,
    _execute_query_user_state,
    _execute_query_meta,
    _execute_query_all_mids,
    _execute_query_clearing_house_state,
)
import logging

# Suppress logging during tests for cleaner output
logging.basicConfig(level=logging.CRITICAL)


@pytest.fixture
def mock_exchange_agent():
    """Mock Hyperliquid Exchange agent."""
    mock_exchange = Mock()
    mock_exchange.order.return_value = {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }
    mock_exchange.unstake.return_value = {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }
    mock_exchange.stake.return_value = {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }
    mock_exchange.vault_transfer.return_value = {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }
    mock_exchange.withdraw.return_value = {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }
    mock_exchange.wallet = Mock()
    mock_exchange.wallet.address = "0x123456789abcdef"
    return mock_exchange


@pytest.fixture
def mock_info_agent():
    """Mock Hyperliquid Info agent."""
    mock_info = Mock()
    mock_info.meta.return_value = {
        "universe": [
            {"name": "ETH", "sz_decimals": 18},
            {"name": "USDC", "sz_decimals": 6},
            {"name": "BTC", "sz_decimals": 8},
        ]
    }
    mock_info.user_vault_equities.return_value = [
        {
            "vault_address": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
            "normalized_equity": "25.5",
        }
    ]
    mock_info.user_state.return_value = {
        "withdrawable": [
            {"coin": "USDC", "total": "100.0"},
            {"coin": "ETH", "total": "1.5"},
        ]
    }
    mock_info.user_staking_delegations.return_value = [
        {
            "validator": "0xvalidator1",
            "amount": "1000000000000000000",  # 1 ETH in wei
        }
    ]
    mock_info.validators.return_value = [
        {"address": "0xvalidator1"},
        {"address": "0xvalidator2"},
        {"address": "0xvalidator3"},
    ]
    mock_info.all_mids.return_value = {"ETH": "2000.0", "BTC": "50000.0"}
    mock_info.clearing_house_state.return_value = {"status": "active"}
    return mock_info


@pytest.fixture
def mock_web3():
    """Mock Web3 instance."""
    mock_w3 = Mock()
    mock_w3.eth = Mock()
    mock_w3.eth.get_transaction_count.return_value = 1
    mock_w3.to_wei.return_value = 2000000000  # 2 gwei
    mock_w3.eth.account = Mock()
    mock_w3.eth.send_raw_transaction.return_value = Mock()
    mock_w3.eth.send_raw_transaction.return_value.hex.return_value = "0xtxhash"
    mock_w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
    
    # Mock contract
    mock_contract = Mock()
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "from": "0x123",
        "nonce": 1,
        "gas": 100000,
        "maxFeePerGas": 2000000000,
        "maxPriorityFeePerGas": 1000000000,
        "chainId": 42161,
    }
    mock_contract.functions.balanceOf.return_value.call.return_value = 100000000  # 100 USDC
    mock_w3.eth.contract.return_value = mock_contract
    mock_w3.to_checksum_address.side_effect = lambda x: x
    
    return mock_w3


# Tests for spot_swap function (existing tests)
def test_spot_swap_sell_eth_market(mock_exchange_agent, mock_info_agent):
    """Test selling ETH for USDC with a market order."""
    from_token = "ETH"
    to_token = "USDC"
    amount_from = 0.01
    order_type = {"market": {}}

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    mock_info_agent.meta.assert_called_once()
    mock_exchange_agent.order.assert_called_once_with(
        asset=0,  # ETH is at index 0 in the mock universe
        is_buy=False,
        sz=0.01,
        limit_px="0",
        order_type={"market": {}},
        reduce_only=False,
    )
    assert response == {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }


def test_spot_swap_buy_btc_limit(mock_exchange_agent, mock_info_agent):
    """Test buying BTC with USDC with a limit order."""
    from_token = "USDC"
    to_token = "BTC"
    amount_from = 0.005
    order_type = {"limit": {"tif": "Gtc", "price": "70000"}}

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    mock_info_agent.meta.assert_called_once()
    mock_exchange_agent.order.assert_called_once_with(
        asset=2,  # BTC is at index 2 in the mock universe
        is_buy=True,
        sz=0.005,
        limit_px="70000",
        order_type={"limit": {"tif": "Gtc", "price": "70000"}},
        reduce_only=False,
    )
    assert response == {
        "status": "ok",
        "response": {"type": "ok", "data": {"status": "ok"}},
    }


def test_spot_swap_unsupported_pair(mock_exchange_agent, mock_info_agent):
    """Test swap between two non-USDC tokens (unsupported)."""
    from_token = "ETH"
    to_token = "BTC"
    amount_from = 0.01
    order_type = {"market": {}}

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    assert response["status"] == "error"
    assert "Direct non-USDC pair swaps are not supported." in response["message"]
    mock_exchange_agent.order.assert_not_called()


def test_spot_swap_invalid_from_token(mock_exchange_agent, mock_info_agent):
    """Test swap with an invalid from_token."""
    from_token = "XYZ"
    to_token = "USDC"
    amount_from = 100.0
    order_type = {"market": {}}

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    assert response["status"] == "error"
    assert "Token 'XYZ' not found." in response["message"]
    mock_exchange_agent.order.assert_not_called()


def test_spot_swap_invalid_to_token(mock_exchange_agent, mock_info_agent):
    """Test swap with an invalid to_token."""
    from_token = "USDC"
    to_token = "XYZ"
    amount_from = 100.0
    order_type = {"market": {}}

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    assert response["status"] == "error"
    assert "Token 'XYZ' not found." in response["message"]
    mock_exchange_agent.order.assert_not_called()


def test_spot_swap_exchange_exception(mock_exchange_agent, mock_info_agent):
    """Test spot swap when exchange.order() raises an exception."""
    from_token = "ETH"
    to_token = "USDC"
    amount_from = 0.01
    order_type = {"market": {}}

    # Make the exchange.order() method raise an exception
    mock_exchange_agent.order.side_effect = Exception("Exchange API error")

    response = spot_swap(
        mock_exchange_agent,
        mock_info_agent,
        from_token,
        to_token,
        amount_from,
        order_type,
    )

    assert response["status"] == "error"
    assert "Unexpected error" in response["message"]
    mock_info_agent.meta.assert_called_once()
    mock_exchange_agent.order.assert_called_once()


# Tests for stake_rotate function
def test_stake_rotate_success(mock_exchange_agent, mock_info_agent):
    """Test successful stake rotation."""
    current_validator = "0xvalidator1"
    new_validator = "0xvalidator2"
    amount_wei = 1000000000000000000  # 1 ETH

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        current_validator,
        new_validator,
        amount_wei,
    )

    assert result is True
    mock_exchange_agent.unstake.assert_called_once_with(
        validator_address=current_validator,
        amount_wei=amount_wei,
    )
    mock_exchange_agent.stake.assert_called_once_with(
        validator_address=new_validator,
        amount_wei=amount_wei,
    )


def test_stake_rotate_unstake_failure(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when unstaking fails."""
    current_validator = "0xvalidator1"
    new_validator = "0xvalidator2"
    amount_wei = 1000000000000000000

    # Make unstake fail
    mock_exchange_agent.unstake.return_value = {"status": "error"}

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        current_validator,
        new_validator,
        amount_wei,
    )

    assert result is False
    mock_exchange_agent.unstake.assert_called_once()
    mock_exchange_agent.stake.assert_not_called()


def test_stake_rotate_stake_failure(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when staking fails."""
    current_validator = "0xvalidator1"
    new_validator = "0xvalidator2"
    amount_wei = 1000000000000000000

    # Make stake fail
    mock_exchange_agent.stake.return_value = {"status": "error"}

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        current_validator,
        new_validator,
        amount_wei,
    )

    assert result is False
    mock_exchange_agent.unstake.assert_called_once()
    mock_exchange_agent.stake.assert_called_once()


def test_stake_rotate_exception(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when an exception occurs."""
    current_validator = "0xvalidator1"
    new_validator = "0xvalidator2"
    amount_wei = 1000000000000000000

    # Make unstake raise an exception
    mock_exchange_agent.unstake.side_effect = Exception("Network error")

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        current_validator,
        new_validator,
        amount_wei,
    )

    assert result is False


# Tests for vault_cycle function
@patch('time.sleep')
def test_vault_cycle_success(mock_sleep, mock_exchange_agent, mock_info_agent):
    """Test successful vault cycle."""
    user_address = "0x123456789abcdef"
    vault_address = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        user_address,
        vault_address,
        min_deposit_usd_units=20_000_000,
        max_deposit_usd_units=40_000_000,
        min_hold_seconds=1,
        max_hold_seconds=2,
    )

    assert result is True
    # Should call vault_transfer twice (deposit and withdraw)
    assert mock_exchange_agent.vault_transfer.call_count == 2
    mock_info_agent.user_vault_equities.assert_called_once_with(user_address)
    mock_sleep.assert_called_once()


def test_vault_cycle_deposit_failure(mock_exchange_agent, mock_info_agent):
    """Test vault cycle when deposit fails."""
    user_address = "0x123456789abcdef"
    vault_address = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

    # Make deposit fail
    mock_exchange_agent.vault_transfer.return_value = {"status": "error"}

    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        user_address,
        vault_address,
    )

    assert result is False
    mock_exchange_agent.vault_transfer.assert_called_once()


def test_vault_cycle_no_equity(mock_exchange_agent, mock_info_agent):
    """Test vault cycle when no equity is found for withdrawal."""
    user_address = "0x123456789abcdef"
    vault_address = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

    # Make user_vault_equities return empty list
    mock_info_agent.user_vault_equities.return_value = []

    with patch('time.sleep'):
        result = vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            user_address,
            vault_address,
            min_hold_seconds=1,
            max_hold_seconds=1,
        )

    assert result is False


def test_vault_cycle_zero_equity(mock_exchange_agent, mock_info_agent):
    """Test vault cycle when equity is zero."""
    user_address = "0x123456789abcdef"
    vault_address = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

    # Make user_vault_equities return zero equity
    mock_info_agent.user_vault_equities.return_value = [
        {
            "vault_address": vault_address,
            "normalized_equity": "0.0",
        }
    ]

    with patch('time.sleep'):
        result = vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            user_address,
            vault_address,
            min_hold_seconds=1,
            max_hold_seconds=1,
        )

    assert result is True  # Zero equity means nothing to withdraw, which is success


def test_vault_cycle_withdrawal_failure(mock_exchange_agent, mock_info_agent):
    """Test vault cycle when withdrawal fails."""
    user_address = "0x123456789abcdef"
    vault_address = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"

    # Make withdrawal fail
    def side_effect(*args, **kwargs):
        if kwargs.get('is_deposit', True):
            return {"status": "ok", "response": {"type": "ok", "data": {"status": "ok"}}}
        else:
            return {"status": "error"}
    
    mock_exchange_agent.vault_transfer.side_effect = side_effect

    with patch('time.sleep'):
        result = vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            user_address,
            vault_address,
            min_hold_seconds=1,
            max_hold_seconds=1,
        )

    assert result is False


# Tests for EVM roundtrip functions
def test_evm_roundtrip_success(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test successful EVM roundtrip."""
    user_evm_address = "0x123456789abcdef"
    arbitrum_private_key = "0xprivatekey"
    amount_usdc = 25.0

    with patch('airdrops.protocols.hyperliquid._deposit_to_l1', return_value=True), \
         patch('airdrops.protocols.hyperliquid._poll_l1_deposit_confirmation', return_value=True), \
         patch('airdrops.protocols.hyperliquid._withdraw_from_l1', return_value=True), \
         patch('airdrops.protocols.hyperliquid._poll_arbitrum_withdrawal_confirmation', return_value=True), \
         patch('time.sleep'):

        result = evm_roundtrip(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            user_evm_address,
            arbitrum_private_key,
            amount_usdc,
            l1_hold_duration_seconds=60,
        )

    assert result is True


def test_evm_roundtrip_minimum_amount_failure():
    """Test EVM roundtrip with amount below minimum."""
    result = evm_roundtrip(
        Mock(), Mock(), Mock(), "0x123", "0xkey", 4.0  # Below 5.0 minimum
    )
    assert result is False


def test_evm_roundtrip_deposit_failure(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test EVM roundtrip when deposit fails."""
    with patch('airdrops.protocols.hyperliquid._deposit_to_l1', return_value=False):
        result = evm_roundtrip(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            25.0,
        )
    assert result is False


def test_deposit_to_l1_success(mock_web3):
    """Test successful deposit to L1."""
    user_evm_address = "0x123456789abcdef"
    arbitrum_private_key = "0xprivatekey"
    amount_usdc = 25.0

    # Mock the signed transaction
    mock_signed_txn = Mock()
    mock_signed_txn.raw_transaction = b"raw_tx_data"
    mock_web3.eth.account.sign_transaction.return_value = mock_signed_txn

    result = _deposit_to_l1(
        mock_web3,
        user_evm_address,
        arbitrum_private_key,
        amount_usdc,
    )

    assert result is True
    mock_web3.eth.contract.assert_called_once()
    mock_web3.eth.account.sign_transaction.assert_called_once()
    mock_web3.eth.send_raw_transaction.assert_called_once()


def test_deposit_to_l1_transaction_failure(mock_web3):
    """Test deposit to L1 when transaction fails."""
    # Make transaction receipt show failure
    mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 0}

    mock_signed_txn = Mock()
    mock_signed_txn.raw_transaction = b"raw_tx_data"
    mock_web3.eth.account.sign_transaction.return_value = mock_signed_txn

    result = _deposit_to_l1(mock_web3, "0x123", "0xkey", 25.0)
    assert result is False


def test_deposit_to_l1_exception(mock_web3):
    """Test deposit to L1 when exception occurs."""
    mock_web3.eth.contract.side_effect = Exception("Contract error")

    result = _deposit_to_l1(mock_web3, "0x123", "0xkey", 25.0)
    assert result is False


def test_poll_l1_deposit_confirmation_success(mock_info_agent):
    """Test successful L1 deposit confirmation polling."""
    user_evm_address = "0x123456789abcdef"
    amount_usdc = 25.0

    # Mock initial and updated states
    initial_state = {"withdrawable": [{"coin": "USDC", "total": "100.0"}]}
    updated_state = {"withdrawable": [{"coin": "USDC", "total": "125.0"}]}
    
    mock_info_agent.user_state.side_effect = [initial_state, updated_state]

    with patch('time.sleep'), patch('time.time', side_effect=[0, 1, 2]):
        result = _poll_l1_deposit_confirmation(
            mock_info_agent,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds=1,
            timeout_seconds=300,
        )

    assert result is True


def test_poll_l1_deposit_confirmation_timeout(mock_info_agent):
    """Test L1 deposit confirmation polling timeout."""
    user_evm_address = "0x123456789abcdef"
    amount_usdc = 25.0

    # Mock state that never reaches expected balance
    state = {"withdrawable": [{"coin": "USDC", "total": "100.0"}]}
    mock_info_agent.user_state.return_value = state

    with patch('time.sleep'), patch('time.time', side_effect=[0, 301]):  # Timeout
        result = _poll_l1_deposit_confirmation(
            mock_info_agent,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds=1,
            timeout_seconds=300,
        )

    assert result is False


def test_withdraw_from_l1_success(mock_exchange_agent):
    """Test successful withdrawal from L1."""
    amount_usdc = 25.0

    result = _withdraw_from_l1(mock_exchange_agent, amount_usdc)

    assert result is True
    mock_exchange_agent.withdraw.assert_called_once_with(25000000, "USDC")


def test_withdraw_from_l1_failure(mock_exchange_agent):
    """Test withdrawal from L1 failure."""
    mock_exchange_agent.withdraw.return_value = {"status": "error"}

    result = _withdraw_from_l1(mock_exchange_agent, 25.0)
    assert result is False


def test_withdraw_from_l1_exception(mock_exchange_agent):
    """Test withdrawal from L1 when exception occurs."""
    mock_exchange_agent.withdraw.side_effect = Exception("Withdrawal error")

    result = _withdraw_from_l1(mock_exchange_agent, 25.0)
    assert result is False


def test_poll_arbitrum_withdrawal_confirmation_success(mock_web3):
    """Test successful Arbitrum withdrawal confirmation polling."""
    user_evm_address = "0x123456789abcdef"
    amount_usdc = 25.0

    # Mock initial and updated balances
    mock_contract = mock_web3.eth.contract.return_value
    mock_contract.functions.balanceOf.return_value.call.side_effect = [
        100000000,  # Initial: 100 USDC
        124000000,  # Updated: 124 USDC (25 - 1 fee)
    ]

    with patch('time.sleep'), patch('time.time', side_effect=[0, 1, 2]):
        result = _poll_arbitrum_withdrawal_confirmation(
            mock_web3,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds=1,
            timeout_seconds=300,
        )

    assert result is True


def test_poll_arbitrum_withdrawal_confirmation_timeout(mock_web3):
    """Test Arbitrum withdrawal confirmation polling timeout."""
    user_evm_address = "0x123456789abcdef"
    amount_usdc = 25.0

    # Mock balance that never increases enough
    mock_contract = mock_web3.eth.contract.return_value
    mock_contract.functions.balanceOf.return_value.call.return_value = 100000000

    with patch('time.sleep'), patch('time.time', side_effect=[0, 301]):  # Timeout
        result = _poll_arbitrum_withdrawal_confirmation(
            mock_web3,
            user_evm_address,
            amount_usdc,
            poll_interval_seconds=1,
            timeout_seconds=300,
        )

    assert result is False


# Tests for perform_random_onchain function
def test_perform_random_onchain_success(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test successful random onchain action."""
    config = {
        "action_weights": {"query_user_state": 10},
    }

    with patch('random.choices', return_value=["query_user_state"]):
        success, message = perform_random_onchain(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            config,
        )

    assert success is True
    assert "Successfully performed query_user_state" in message


def test_perform_random_onchain_no_weights():
    """Test random onchain action with no action weights."""
    config = {}

    success, message = perform_random_onchain(
        Mock(), Mock(), Mock(), "0x123", "0xkey", config
    )

    assert success is False
    assert "No action weights provided" in message


def test_perform_random_onchain_unknown_action(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test random onchain action with unknown action."""
    config = {
        "action_weights": {"unknown_action": 10},
    }

    with patch('random.choices', return_value=["unknown_action"]):
        success, message = perform_random_onchain(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            config,
        )

    assert success is False
    assert "Unknown action" in message


def test_perform_random_onchain_exception(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test random onchain action when exception occurs."""
    config = {
        "action_weights": {"query_user_state": 10},
    }

    with patch('random.choices', side_effect=Exception("Random error")):
        success, message = perform_random_onchain(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            config,
        )

    assert success is False
    assert "Failed to perform random action" in message


# Tests for execute functions
def test_execute_stake_rotate_success(mock_exchange_agent, mock_info_agent):
    """Test successful stake rotate execution."""
    config = {
        "stake_rotate_params": {
            "min_hype_percentage": 0.01,
            "max_hype_percentage": 0.1,
        }
    }

    with patch('random.choice') as mock_choice, \
         patch('random.uniform', return_value=0.05), \
         patch('airdrops.protocols.hyperliquid.stake_rotate', return_value=True):
        
        # Mock delegation and validator selection
        mock_choice.side_effect = [
            {"validator": "0xvalidator1", "amount": "1000000000000000000"},
            {"address": "0xvalidator2"},
        ]

        success, message = _execute_stake_rotate(
            mock_exchange_agent,
            mock_info_agent,
            "0x123",
            config,
        )

    assert success is True
    assert "Successfully rotated" in message


def test_execute_stake_rotate_no_delegations(mock_exchange_agent, mock_info_agent):
    """Test stake rotate execution with no delegations."""
    mock_info_agent.user_staking_delegations.return_value = []
    config = {"stake_rotate_params": {}}

    success, message = _execute_stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0x123",
        config,
    )

    assert success is False
    assert "No current delegations" in message


def test_execute_vault_cycle_success(mock_exchange_agent, mock_info_agent):
    """Test successful vault cycle execution."""
    config = {
        "vault_cycle_params": {
            "min_deposit_usd_units": 20_000_000,
            "max_deposit_usd_units": 40_000_000,
            "min_hold_seconds": 1,
            "max_hold_seconds": 2,
        },
        "hyperliquid_vault_address": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
    }

    with patch('airdrops.protocols.hyperliquid.vault_cycle', return_value=True):
        success, message = _execute_vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            "0x123",
            config,
        )

    assert success is True
    assert "Successfully completed vault cycle" in message


def test_execute_vault_cycle_failure(mock_exchange_agent, mock_info_agent):
    """Test vault cycle execution failure."""
    config = {
        "vault_cycle_params": {
            "min_deposit_usd_units": 20_000_000,
            "max_deposit_usd_units": 40_000_000,
            "min_hold_seconds": 1,
            "max_hold_seconds": 2,
        },
        "hyperliquid_vault_address": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
    }

    with patch('airdrops.protocols.hyperliquid.vault_cycle', return_value=False):
        success, message = _execute_vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            "0x123",
            config,
        )

    assert success is False
    assert "Failed to complete vault cycle" in message


def test_execute_spot_swap_success(mock_exchange_agent, mock_info_agent):
    """Test successful spot swap execution."""
    config = {
        "spot_swap_params": {
            "safe_pairs": [("USDC", "ETH")],
            "min_from_token_percentage": 0.01,
            "max_from_token_percentage": 0.05,
        }
    }

    with patch('random.choice', return_value=("USDC", "ETH")), \
         patch('random.uniform', return_value=0.02), \
         patch('airdrops.protocols.hyperliquid.spot_swap') as mock_spot_swap:
        
        mock_spot_swap.return_value = {"status": "ok"}

        success, message = _execute_spot_swap(
            mock_exchange_agent,
            mock_info_agent,
            config,
        )

    assert success is True
    assert "Successfully swapped" in message


def test_execute_spot_swap_insufficient_balance(mock_exchange_agent, mock_info_agent):
    """Test spot swap execution with insufficient balance."""
    config = {
        "spot_swap_params": {
            "safe_pairs": [("ETH", "USDC")],
            "min_from_token_percentage": 0.01,
            "max_from_token_percentage": 0.05,
        }
    }

    # Mock user state with zero ETH balance
    mock_info_agent.user_state.return_value = {
        "withdrawable": [{"coin": "USDC", "total": "100.0"}]
    }

    with patch('random.choice', return_value=("ETH", "USDC")):
        success, message = _execute_spot_swap(
            mock_exchange_agent,
            mock_info_agent,
            config,
        )

    assert success is False
    assert "Insufficient ETH balance" in message


def test_execute_spot_swap_error_response(mock_exchange_agent, mock_info_agent):
    """Test spot swap execution with error response."""
    config = {
        "spot_swap_params": {
            "safe_pairs": [("USDC", "ETH")],
            "min_from_token_percentage": 0.01,
            "max_from_token_percentage": 0.05,
        }
    }

    with patch('random.choice', return_value=("USDC", "ETH")), \
         patch('random.uniform', return_value=0.02), \
         patch('airdrops.protocols.hyperliquid.spot_swap') as mock_spot_swap:
        
        mock_spot_swap.return_value = {"status": "error", "message": "Swap failed"}

        success, message = _execute_spot_swap(
            mock_exchange_agent,
            mock_info_agent,
            config,
        )

    assert success is False
    assert "Spot swap failed" in message


def test_execute_evm_roundtrip_success(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test successful EVM roundtrip execution."""
    config = {
        "evm_roundtrip_params": {
            "min_amount_usdc": 5.0,
            "max_amount_usdc": 25.0,
            "min_l1_hold_seconds": 0,
            "max_l1_hold_seconds": 300,
        }
    }

    with patch('random.uniform', return_value=15.0), \
         patch('random.randint', return_value=60), \
         patch('airdrops.protocols.hyperliquid.evm_roundtrip', return_value=True):

        success, message = _execute_evm_roundtrip(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            config,
        )

    assert success is True
    assert "Successfully completed EVM roundtrip" in message


def test_execute_evm_roundtrip_failure(mock_exchange_agent, mock_info_agent, mock_web3):
    """Test EVM roundtrip execution failure."""
    config = {
        "evm_roundtrip_params": {
            "min_amount_usdc": 5.0,
            "max_amount_usdc": 25.0,
            "min_l1_hold_seconds": 0,
            "max_l1_hold_seconds": 300,
        }
    }

    with patch('random.uniform', return_value=15.0), \
         patch('random.randint', return_value=60), \
         patch('airdrops.protocols.hyperliquid.evm_roundtrip', return_value=False):

        success, message = _execute_evm_roundtrip(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x123",
            "0xkey",
            config,
        )

    assert success is False
    assert "Failed to complete EVM roundtrip" in message


def test_execute_query_user_state_success(mock_info_agent):
    """Test successful query user state execution."""
    success, message = _execute_query_user_state(mock_info_agent, "0x123")

    assert success is True
    assert "Successfully performed query_user_state" in message
    mock_info_agent.user_state.assert_called_once_with("0x123")


def test_execute_query_user_state_exception(mock_info_agent):
    """Test query user state execution with exception."""
    mock_info_agent.user_state.side_effect = Exception("API error")

    success, message = _execute_query_user_state(mock_info_agent, "0x123")

    assert success is False
    assert "Error executing query_user_state" in message


def test_execute_query_meta_success(mock_info_agent):
    """Test successful query meta execution."""
    success, message = _execute_query_meta(mock_info_agent)

    assert success is True
    assert "Successfully performed query_meta" in message
    mock_info_agent.meta.assert_called_once()


def test_execute_query_meta_exception(mock_info_agent):
    """Test query meta execution with exception."""
    mock_info_agent.meta.side_effect = Exception("API error")

    success, message = _execute_query_meta(mock_info_agent)

    assert success is False
    assert "Error executing query_meta" in message


def test_execute_query_all_mids_success(mock_info_agent):
    """Test successful query all mids execution."""
    success, message = _execute_query_all_mids(mock_info_agent)

    assert success is True
    assert "Successfully performed query_all_mids" in message
    mock_info_agent.all_mids.assert_called_once()


def test_execute_query_all_mids_exception(mock_info_agent):
    """Test query all mids execution with exception."""
    mock_info_agent.all_mids.side_effect = Exception("API error")

    success, message = _execute_query_all_mids(mock_info_agent)

    assert success is False
    assert "Error executing query_all_mids" in message


def test_execute_query_clearing_house_state_success(mock_info_agent):
    """Test successful query clearing house state execution."""
    success, message = _execute_query_clearing_house_state(mock_info_agent)

    assert success is True
    assert "Successfully performed query_clearing_house_state" in message
    mock_info_agent.clearing_house_state.assert_called_once()


def test_execute_query_clearing_house_state_exception(mock_info_agent):
    """Test query clearing house state execution with exception."""
    mock_info_agent.clearing_house_state.side_effect = Exception("API error")

    success, message = _execute_query_clearing_house_state(mock_info_agent)

    assert success is False
    assert "Error executing query_clearing_house_state" in message