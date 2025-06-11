import pytest
from unittest.mock import Mock, patch
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
    mock_exchange.wallet.address = "0x1234567890123456789012345678901234567890"
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
            "amount": "1000000000000000000",
        }
    ]
    mock_info.validators.return_value = [
        {"address": "0xvalidator1"},
        {"address": "0xvalidator2"},
        {"address": "0xvalidator3"},
    ]
    mock_info.all_mids.return_value = {"ETH": "3000.0", "BTC": "70000.0"}
    mock_info.clearing_house_state.return_value = {"status": "ok"}
    return mock_info


@pytest.fixture
def mock_web3():
    """Mock Web3 instance."""
    mock_w3 = Mock()
    mock_w3.eth.get_transaction_count.return_value = 1
    mock_w3.to_wei.return_value = 2000000000
    mock_w3.eth.account.sign_transaction.return_value = Mock(
        raw_transaction=b"signed_tx"
    )
    mock_w3.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x123abc")
    mock_w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}

    mock_contract = Mock()
    mock_contract.functions.transfer.return_value.build_transaction.return_value = {
        "from": "0x1234567890123456789012345678901234567890",
        "nonce": 1,
        "gas": 100000,
        "maxFeePerGas": 2000000000,
        "maxPriorityFeePerGas": 1000000000,
        "chainId": 42161,
    }
    mock_contract.functions.balanceOf.return_value.call.return_value = 100000000
    mock_w3.eth.contract.return_value = mock_contract
    mock_w3.to_checksum_address.side_effect = lambda x: x

    return mock_w3


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
        asset=0,
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
        asset=2,
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


def test_stake_rotate_success(mock_exchange_agent, mock_info_agent):
    """Test successful stake rotation."""
    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0xvalidator1",
        "0xvalidator2",
        1000000000000000000,
    )

    assert result is True
    mock_exchange_agent.unstake.assert_called_once_with(
        validator_address="0xvalidator1",
        amount_wei=1000000000000000000,
    )
    mock_exchange_agent.stake.assert_called_once_with(
        validator_address="0xvalidator2",
        amount_wei=1000000000000000000,
    )


def test_stake_rotate_unstake_failure(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when unstake fails."""
    mock_exchange_agent.unstake.return_value = {"status": "error"}

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0xvalidator1",
        "0xvalidator2",
        1000000000000000000,
    )

    assert result is False
    mock_exchange_agent.unstake.assert_called_once()
    mock_exchange_agent.stake.assert_not_called()


def test_stake_rotate_stake_failure(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when stake fails."""
    mock_exchange_agent.stake.return_value = {"status": "error"}

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0xvalidator1",
        "0xvalidator2",
        1000000000000000000,
    )

    assert result is False
    mock_exchange_agent.unstake.assert_called_once()
    mock_exchange_agent.stake.assert_called_once()


def test_stake_rotate_exception(mock_exchange_agent, mock_info_agent):
    """Test stake rotation when exception occurs."""
    mock_exchange_agent.unstake.side_effect = Exception("API error")

    result = stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0xvalidator1",
        "0xvalidator2",
        1000000000000000000,
    )

    assert result is False


@patch('time.sleep')
def test_vault_cycle_success(mock_sleep, mock_exchange_agent, mock_info_agent):
    """Test successful vault cycle."""
    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        min_deposit_usd_units=20_000_000,
        max_deposit_usd_units=40_000_000,
        min_hold_seconds=1,
        max_hold_seconds=2,
    )

    assert result is True
    assert mock_exchange_agent.vault_transfer.call_count == 2
    mock_info_agent.user_vault_equities.assert_called_once()
    mock_sleep.assert_called_once()


@patch('time.sleep')
def test_vault_cycle_deposit_failure(
    mock_sleep, mock_exchange_agent, mock_info_agent
):
    """Test vault cycle when deposit fails."""
    mock_exchange_agent.vault_transfer.return_value = {"status": "error"}

    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
    )

    assert result is False
    mock_exchange_agent.vault_transfer.assert_called_once()
    mock_sleep.assert_not_called()


@patch('time.sleep')
def test_vault_cycle_no_equity(mock_sleep, mock_exchange_agent, mock_info_agent):
    """Test vault cycle when no equity found."""
    mock_info_agent.user_vault_equities.return_value = []

    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        min_hold_seconds=1,
        max_hold_seconds=2,
    )

    assert result is False
    mock_sleep.assert_called_once()


@patch('time.sleep')
def test_vault_cycle_zero_equity(
    mock_sleep, mock_exchange_agent, mock_info_agent
):
    """Test vault cycle when equity is zero."""
    mock_info_agent.user_vault_equities.return_value = [
        {
            "vault_address": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
            "normalized_equity": "0.0",
        }
    ]

    result = vault_cycle(
        mock_exchange_agent,
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        min_hold_seconds=1,
        max_hold_seconds=2,
    )

    assert result is True
    mock_sleep.assert_called_once()


@patch('airdrops.protocols.hyperliquid._poll_arbitrum_withdrawal_confirmation')
@patch('airdrops.protocols.hyperliquid._withdraw_from_l1')
@patch('time.sleep')
@patch('airdrops.protocols.hyperliquid._poll_l1_deposit_confirmation')
@patch('airdrops.protocols.hyperliquid._deposit_to_l1')
def test_evm_roundtrip_success(
    mock_deposit, mock_poll_deposit, mock_sleep, mock_withdraw,
    mock_poll_withdraw, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test successful EVM roundtrip."""
    mock_deposit.return_value = True
    mock_poll_deposit.return_value = True
    mock_withdraw.return_value = True
    mock_poll_withdraw.return_value = True

    result = evm_roundtrip(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        25.0,
        l1_hold_duration_seconds=60,
    )

    assert result is True
    mock_deposit.assert_called_once()
    mock_poll_deposit.assert_called_once()
    mock_sleep.assert_called_once_with(60)
    mock_withdraw.assert_called_once()
    mock_poll_withdraw.assert_called_once()


def test_evm_roundtrip_amount_too_low(
    mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test EVM roundtrip with amount below minimum."""
    result = evm_roundtrip(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        4.0,
    )

    assert result is False


@patch('airdrops.protocols.hyperliquid._deposit_to_l1')
def test_evm_roundtrip_deposit_failure(
    mock_deposit, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test EVM roundtrip when deposit fails."""
    mock_deposit.return_value = False

    result = evm_roundtrip(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        25.0,
    )

    assert result is False


def test_deposit_to_l1_success(mock_web3):
    """Test successful deposit to L1."""
    result = _deposit_to_l1(
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        25.0,
    )

    assert result is True
    mock_web3.eth.contract.assert_called_once()
    mock_web3.eth.send_raw_transaction.assert_called_once()


def test_deposit_to_l1_transaction_failure(mock_web3):
    """Test deposit to L1 when transaction fails."""
    mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 0}

    result = _deposit_to_l1(
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        25.0,
    )

    assert result is False


def test_deposit_to_l1_exception(mock_web3):
    """Test deposit to L1 when exception occurs."""
    mock_web3.eth.contract.side_effect = Exception("Web3 error")

    result = _deposit_to_l1(
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        25.0,
    )

    assert result is False


@patch('time.sleep')
@patch('time.time')
def test_poll_l1_deposit_confirmation_success(
    mock_time, mock_sleep, mock_info_agent
):
    """Test successful L1 deposit confirmation."""
    mock_time.side_effect = iter([0, 10, 20])
    mock_info_agent.user_state.side_effect = [
        {"withdrawable": [{"coin": "USDC", "total": "100.0"}]},
        {"withdrawable": [{"coin": "USDC", "total": "125.0"}]},
    ]

    result = _poll_l1_deposit_confirmation(
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        25.0,
        10,
        300,
    )

    assert result is True


@patch('time.sleep')
@patch('time.time')
def test_poll_l1_deposit_confirmation_timeout(
    mock_time, mock_sleep, mock_info_agent
):
    """Test L1 deposit confirmation timeout."""
    mock_time.side_effect = iter(i * 10 for i in range(32))
    mock_info_agent.user_state.return_value = {
        "withdrawable": [{"coin": "USDC", "total": "100.0"}]
    }

    result = _poll_l1_deposit_confirmation(
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        25.0,
        10,
        300,
    )

    assert result is False


def test_withdraw_from_l1_success(mock_exchange_agent):
    """Test successful withdrawal from L1."""
    result = _withdraw_from_l1(mock_exchange_agent, 25.0)

    assert result is True
    mock_exchange_agent.withdraw.assert_called_once_with(25000000, "USDC")


def test_withdraw_from_l1_failure(mock_exchange_agent):
    """Test withdrawal from L1 failure."""
    mock_exchange_agent.withdraw.return_value = {"status": "error"}

    result = _withdraw_from_l1(mock_exchange_agent, 25.0)

    assert result is False


def test_withdraw_from_l1_exception(mock_exchange_agent):
    """Test withdrawal from L1 when exception occurs."""
    mock_exchange_agent.withdraw.side_effect = Exception("API error")

    result = _withdraw_from_l1(mock_exchange_agent, 25.0)

    assert result is False


@patch('time.sleep')
@patch('time.time')
def test_poll_arbitrum_withdrawal_confirmation_success(
    mock_time, mock_sleep, mock_web3
):
    """Test successful Arbitrum withdrawal confirmation."""
    mock_time.side_effect = iter([0, 10, 20])

    mock_contract = mock_web3.eth.contract.return_value
    mock_contract.functions.balanceOf.return_value.call.side_effect = [
        100000000,
        124000000,
    ]

    result = _poll_arbitrum_withdrawal_confirmation(
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        25.0,
        10,
        300,
    )

    assert result is True


@patch('time.sleep')
@patch('time.time')
def test_poll_arbitrum_withdrawal_confirmation_timeout(
    mock_time, mock_sleep, mock_web3
):
    """Test Arbitrum withdrawal confirmation timeout."""
    mock_time.side_effect = iter(i * 10 for i in range(32))
    mock_contract = mock_web3.eth.contract.return_value
    mock_contract.functions.balanceOf.return_value.call.return_value = 100000000

    result = _poll_arbitrum_withdrawal_confirmation(
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        25.0,
        10,
        300,
    )

    assert result is False


@patch('random.choices')
def test_perform_random_onchain_stake_rotate(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with stake_rotate action."""
    mock_choices.return_value = ["stake_rotate"]

    config = {
        "action_weights": {"stake_rotate": 10},
        "stake_rotate_params": {
            "min_hype_percentage": 0.01,
            "max_hype_percentage": 0.1,
        },
    }

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully rotated" in message


@patch('random.choices')
def test_perform_random_onchain_vault_cycle(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with vault_cycle action."""
    mock_choices.return_value = ["vault_cycle"]

    config = {
        "action_weights": {"vault_cycle": 10},
        "vault_cycle_params": {
            "min_deposit_usd_units": 20_000_000,
            "max_deposit_usd_units": 40_000_000,
            "min_hold_seconds": 1,
            "max_hold_seconds": 2,
        },
    }

    with patch('time.sleep'):
        success, message = perform_random_onchain(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x1234567890123456789012345678901234567890",
            "0xprivatekey",
            config,
        )

    assert success is True
    assert "Successfully completed vault cycle" in message


@patch('random.choices')
def test_perform_random_onchain_spot_swap(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with spot_swap action."""
    mock_choices.return_value = ["spot_swap"]

    config = {
        "action_weights": {"spot_swap": 10},
        "spot_swap_params": {
            "safe_pairs": [("USDC", "ETH")],
            "min_from_token_percentage": 0.01,
            "max_from_token_percentage": 0.05,
        },
    }

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully swapped" in message


@patch('random.choices')
def test_perform_random_onchain_query_user_state(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with query_user_state action."""
    mock_choices.return_value = ["query_user_state"]

    config = {"action_weights": {"query_user_state": 10}}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully performed query_user_state" in message


@patch('random.choices')
def test_perform_random_onchain_query_meta(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with query_meta action."""
    mock_choices.return_value = ["query_meta"]

    config = {"action_weights": {"query_meta": 10}}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully performed query_meta" in message


@patch('random.choices')
def test_perform_random_onchain_query_all_mids(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with query_all_mids action."""
    mock_choices.return_value = ["query_all_mids"]

    config = {"action_weights": {"query_all_mids": 10}}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully performed query_all_mids" in message


@patch('random.choices')
def test_perform_random_onchain_query_clearing_house_state(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with query_clearing_house_state action."""
    mock_choices.return_value = ["query_clearing_house_state"]

    config = {"action_weights": {"query_clearing_house_state": 10}}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is True
    assert "Successfully performed query_clearing_house_state" in message


def test_perform_random_onchain_no_weights(
    mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with no action weights."""
    config = {}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is False
    assert "No action weights provided" in message


@patch('random.choices')
def test_perform_random_onchain_unknown_action(
    mock_choices, mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test perform_random_onchain with unknown action."""
    mock_choices.return_value = ["unknown_action"]

    config = {"action_weights": {"unknown_action": 10}}

    success, message = perform_random_onchain(
        mock_exchange_agent,
        mock_info_agent,
        mock_web3,
        "0x1234567890123456789012345678901234567890",
        "0xprivatekey",
        config,
    )

    assert success is False
    assert "Unknown action: unknown_action" in message


def test_execute_stake_rotate_no_delegations(
    mock_exchange_agent, mock_info_agent
):
    """Test _execute_stake_rotate with no delegations."""
    mock_info_agent.user_staking_delegations.return_value = []

    success, message = _execute_stake_rotate(
        mock_exchange_agent,
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
        {"stake_rotate_params": {}},
    )

    assert success is False
    assert "No current delegations" in message


def test_execute_vault_cycle_success(mock_exchange_agent, mock_info_agent):
    """Test _execute_vault_cycle success."""
    config = {
        "vault_cycle_params": {
            "min_deposit_usd_units": 20_000_000,
            "max_deposit_usd_units": 40_000_000,
            "min_hold_seconds": 1,
            "max_hold_seconds": 2,
        }
    }

    with patch('time.sleep'):
        success, message = _execute_vault_cycle(
            mock_exchange_agent,
            mock_info_agent,
            "0x1234567890123456789012345678901234567890",
            config,
        )

    assert success is True
    assert "Successfully completed vault cycle" in message


def test_execute_spot_swap_insufficient_balance(
    mock_exchange_agent, mock_info_agent
):
    """Test _execute_spot_swap with insufficient balance."""
    mock_info_agent.user_state.return_value = {
        "withdrawable": [{"coin": "USDC", "total": "0.0"}]
    }

    config = {
        "spot_swap_params": {
            "safe_pairs": [("USDC", "ETH")],
            "min_from_token_percentage": 0.01,
            "max_from_token_percentage": 0.05,
        }
    }

    success, message = _execute_spot_swap(
        mock_exchange_agent, mock_info_agent, config
    )

    assert success is False
    assert "Insufficient USDC balance" in message


def test_execute_evm_roundtrip_success(
    mock_exchange_agent, mock_info_agent, mock_web3
):
    """Test _execute_evm_roundtrip success."""
    config = {
        "evm_roundtrip_params": {
            "min_amount_usdc": 5.0,
            "max_amount_usdc": 25.0,
            "min_l1_hold_seconds": 0,
            "max_l1_hold_seconds": 300,
        }
    }

    with patch('airdrops.protocols.hyperliquid.evm_roundtrip', return_value=True):
        success, message = _execute_evm_roundtrip(
            mock_exchange_agent,
            mock_info_agent,
            mock_web3,
            "0x1234567890123456789012345678901234567890",
            "0xprivatekey",
            config,
        )

    assert success is True
    assert "Successfully completed EVM roundtrip" in message


def test_execute_query_user_state_success(mock_info_agent):
    """Test _execute_query_user_state success."""
    success, message = _execute_query_user_state(
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
    )

    assert success is True
    assert "Successfully performed query_user_state" in message


def test_execute_query_meta_success(mock_info_agent):
    """Test _execute_query_meta success."""
    success, message = _execute_query_meta(mock_info_agent)

    assert success is True
    assert "Successfully performed query_meta" in message


def test_execute_query_all_mids_success(mock_info_agent):
    """Test _execute_query_all_mids success."""
    success, message = _execute_query_all_mids(mock_info_agent)

    assert success is True
    assert "Successfully performed query_all_mids" in message


def test_execute_query_clearing_house_state_success(mock_info_agent):
    """Test _execute_query_clearing_house_state success."""
    success, message = _execute_query_clearing_house_state(mock_info_agent)

    assert success is True
    assert "Successfully performed query_clearing_house_state" in message


def test_execute_query_user_state_exception(mock_info_agent):
    """Test _execute_query_user_state with exception."""
    mock_info_agent.user_state.side_effect = Exception("API error")

    success, message = _execute_query_user_state(
        mock_info_agent,
        "0x1234567890123456789012345678901234567890",
    )

    assert success is False
    assert "Error executing query_user_state" in message


def test_execute_query_meta_exception(mock_info_agent):
    """Test _execute_query_meta with exception."""
    mock_info_agent.meta.side_effect = Exception("API error")

    success, message = _execute_query_meta(mock_info_agent)

    assert success is False
    assert "Error executing query_meta" in message


def test_execute_query_all_mids_exception(mock_info_agent):
    """Test _execute_query_all_mids with exception."""
    mock_info_agent.all_mids.side_effect = Exception("API error")

    success, message = _execute_query_all_mids(mock_info_agent)

    assert success is False
    assert "Error executing query_all_mids" in message


def test_execute_query_clearing_house_state_exception(mock_info_agent):
    """Test _execute_query_clearing_house_state with exception."""
    mock_info_agent.clearing_house_state.side_effect = Exception("API error")

    success, message = _execute_query_clearing_house_state(mock_info_agent)

    assert success is False
    assert "Error executing query_clearing_house_state" in message
