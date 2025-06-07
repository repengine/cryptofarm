import pytest
from unittest.mock import Mock
from airdrops.protocols.hyperliquid import spot_swap
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
    return mock_info


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
