"""
Comprehensive unit tests for core Scroll protocol functions.

This module tests the internal helper functions and core functionality
that are not covered by the existing high-level tests.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, mock_open
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes

from src.airdrops.protocols.scroll.scroll import (
    _load_abi_scroll,
    _get_account_scroll,
    _get_l1_token_address_scroll,
    _get_l2_token_address_scroll,
    _get_contract_scroll,
    _build_and_send_tx_scroll,
    _approve_erc20_scroll,
    _get_syncswap_classic_pool_factory_contract_scroll,
    _get_syncswap_pool_address_scroll,
    _calculate_amount_out_min_syncswap_scroll,
    _encode_swap_step_data_scroll,
    swap_tokens,
    _get_layerbank_lbtoken_address_scroll,
    _check_and_enter_layerbank_market_scroll,
    _get_layerbank_account_liquidity_scroll,
    lend_borrow_layerbank_scroll,
    bridge_assets,
    _check_balance_and_approve_liquidity_token,
    _calculate_min_liquidity_amount,
    ScrollProtocol,
)
from src.airdrops.protocols.scroll.exceptions import (
    InsufficientBalanceError,
    TransactionRevertedError,
    GasEstimationError,
    MaxRetriesExceededError,
    TransactionBuildError,
    TokenNotSupportedError,
)


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Block all real HTTP requests for test isolation."""
    import requests
    from unittest.mock import Mock

    import json as pyjson

    def dummy_request(self, method, url, *args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200

        # Parse the JSON-RPC method from the request payload
        data = kwargs.get("data", b"")
        try:
            payload = pyjson.loads(data.decode() if isinstance(data, bytes) else data)
            rpc_method = payload.get("method", "")
        except Exception:
            rpc_method = ""

        def json_method():
            if rpc_method == "web3_clientVersion":
                return {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": "MockClient"
                }
            elif rpc_method in ("eth_gasPrice", "eth_getBalance", "eth_blockNumber", "eth_estimateGas"):
                return {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": hex(10**9)
                }
            elif rpc_method == "eth_getBlockByNumber":
                return {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": {"timestamp": 1234567890}
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": "0x0"
                }

        mock_response.json.side_effect = json_method
        mock_response.content = b'{"jsonrpc": "2.0", "id": 0, "result": "0x0"}'
        mock_response.text = '{"jsonrpc": "2.0", "id": 0, "result": "0x0"}'
        # Add context manager support
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, exc_type, exc_val, exc_tb: None
        return mock_response

    monkeypatch.setattr(requests.sessions.Session, "request", dummy_request)


class TestABILoading:
    """Test suite for ABI loading functionality."""

    def test_load_abi_scroll_success(self) -> None:
        """Test successful ABI loading."""
        mock_abi = [{"type": "function", "name": "test"}]
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                result = _load_abi_scroll("TestContract")
                assert result == mock_abi

    def test_load_abi_scroll_file_not_found(self) -> None:
        """Test ABI loading when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError, match="ABI file not found"):
                _load_abi_scroll("NonExistentContract")

    def test_load_abi_scroll_invalid_json(self) -> None:
        """Test ABI loading with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with pytest.raises(json.JSONDecodeError):
                _load_abi_scroll("InvalidContract")


class TestAccountManagement:
    """Test suite for account management functions."""

    def test_get_account_scroll_success(self) -> None:
        """Test successful account creation from private key."""
        mock_web3 = MagicMock()
        private_key = "0x" + "a" * 64
        
        with patch("src.airdrops.protocols.scroll.scroll.Account") as mock_account_class:
            mock_account = MagicMock(spec=LocalAccount)
            mock_account_class.from_key.return_value = mock_account
            
            result = _get_account_scroll(private_key, mock_web3)
            
            assert result == mock_account
            mock_account_class.from_key.assert_called_once_with(private_key)

    def test_get_account_scroll_without_0x_prefix(self) -> None:
        """Test account creation with private key without 0x prefix."""
        mock_web3 = MagicMock()
        private_key = "a" * 64
        
        with patch("src.airdrops.protocols.scroll.scroll.Account") as mock_account_class:
            mock_account = MagicMock(spec=LocalAccount)
            mock_account_class.from_key.return_value = mock_account
            
            result = _get_account_scroll(private_key, mock_web3)
            
            assert result == mock_account
            mock_account_class.from_key.assert_called_once_with("0x" + private_key)

    def test_get_account_scroll_invalid_key(self) -> None:
        """Test account creation with invalid private key."""
        mock_web3 = MagicMock()
        private_key = "invalid_key"
        
        with patch("src.airdrops.protocols.scroll.scroll.Account") as mock_account_class:
            mock_account_class.from_key.side_effect = Exception("Invalid key")
            
            with pytest.raises(ValueError, match="Invalid private key"):
                _get_account_scroll(private_key, mock_web3)


class TestTokenAddressResolution:
    """Test suite for token address resolution functions."""

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l1_token_address_scroll_success(self, mock_config: MagicMock) -> None:
        """Test successful L1 token address resolution."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {
            "USDC": {"L1": "0x1234567890123456789012345678901234567890", "L2": "0x456"}
        }
        
        result = _get_l1_token_address_scroll("USDC")
        assert result == "0x1234567890123456789012345678901234567890"

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l1_token_address_scroll_not_found(self, mock_config: MagicMock) -> None:
        """Test L1 token address resolution for non-existent token."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {}
        
        with pytest.raises(TokenNotSupportedError, match="Token symbol 'UNKNOWN' not supported"):
            _get_l1_token_address_scroll("UNKNOWN")

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l1_token_address_scroll_missing_l1(self, mock_config: MagicMock) -> None:
        """Test L1 token address resolution when L1 address is missing."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {
            "USDC": {"L2": "0x456"}
        }
        
        with pytest.raises(TokenNotSupportedError, match="L1 address for token 'USDC' not configured"):
            _get_l1_token_address_scroll("USDC")

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l2_token_address_scroll_success(self, mock_config: MagicMock) -> None:
        """Test successful L2 token address resolution."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {
            "USDC": {"L1": "0x1234567890123456789012345678901234567890", "L2": "0x456"}
        }
        
        result = _get_l2_token_address_scroll("USDC")
        assert result == "0x456"

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l2_token_address_scroll_eth_to_weth(self, mock_config: MagicMock) -> None:
        """Test L2 token address resolution for ETH (should return WETH address)."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {
            "ETH": {"L1": "0x000", "L2": None},
            "WETH": {"L1": "0x111", "L2": "0x222"}
        }
        
        result = _get_l2_token_address_scroll("ETH")
        assert result == "0x222"

    @patch("src.airdrops.protocols.scroll.scroll.shared_config")
    def test_get_l2_token_address_scroll_eth_missing_weth(self, mock_config: MagicMock) -> None:
        """Test L2 token address resolution for ETH when WETH is not configured."""
        mock_config.SCROLL_TOKEN_ADDRESSES = {
            "ETH": {"L1": "0x000", "L2": None}
        }
        
        with pytest.raises(TokenNotSupportedError, match="WETH symbol not found"):
            _get_l2_token_address_scroll("ETH")


class TestContractInteraction:
    """Test suite for contract interaction functions."""

    @patch("src.airdrops.protocols.scroll.scroll._load_abi_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_contract_scroll_success(self, mock_web3_class: MagicMock, mock_load_abi: MagicMock) -> None:
        """Test successful contract creation."""
        mock_web3 = MagicMock()
        mock_abi = [{"type": "function", "name": "test"}]
        mock_contract = MagicMock()
        
        mock_load_abi.return_value = mock_abi
        mock_web3_class.to_checksum_address.return_value = "0x1234567890123456789012345678901234567890"
        mock_web3.eth.contract.return_value = mock_contract
        
        result = _get_contract_scroll(mock_web3, "TestContract", "0x1234567890123456789012345678901234567890")
        
        assert result == mock_contract
        mock_load_abi.assert_called_once_with("TestContract")
        mock_web3.eth.contract.assert_called_once_with(address="0x1234567890123456789012345678901234567890", abi=mock_abi)


class TestTransactionBuilding:
    """Test suite for transaction building and sending functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_build_and_send_tx_scroll_success(self, mock_get_account: MagicMock) -> None:
        """Test successful transaction building and sending."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        # Setup Web3 mocks
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 10**9
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value.raw_transaction = b"signed_tx"
        mock_web3.eth.send_raw_transaction.return_value = HexBytes("0xabc123")
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        
        tx_params = {"to": "0x456", "value": 100}
        
        result = _build_and_send_tx_scroll(mock_web3, "0x" + "a" * 64, tx_params)
        
        assert result == "abc123"
        mock_web3.eth.send_raw_transaction.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_build_and_send_tx_scroll_gas_estimation_failure(self, mock_get_account: MagicMock) -> None:
        """Test transaction building with gas estimation failure."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 10**9
        mock_web3.eth.estimate_gas.side_effect = Exception("Gas estimation failed")
        
        tx_params = {"to": "0x456", "value": 100}
        
        with pytest.raises(GasEstimationError, match="Gas estimation failed"):
            _build_and_send_tx_scroll(mock_web3, "0x" + "a" * 64, tx_params)

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_build_and_send_tx_scroll_transaction_reverted(self, mock_get_account: MagicMock) -> None:
        """Test transaction building with reverted transaction."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 10**9
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value.raw_transaction = b"signed_tx"
        mock_web3.eth.send_raw_transaction.return_value = HexBytes("0xabc123")
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 0}
        
        tx_params = {"to": "0x456", "value": 100}
        
        with pytest.raises(TransactionRevertedError, match="Transaction .* reverted"):
            _build_and_send_tx_scroll(mock_web3, "0x" + "a" * 64, tx_params)


class TestERC20Approval:
    """Test suite for ERC20 approval functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_approve_erc20_scroll_success(
        self, 
        mock_build_send: MagicMock, 
        mock_get_contract: MagicMock, 
        mock_get_account: MagicMock
    ) -> None:
        """Test successful ERC20 approval."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_contract = MagicMock()
        
        mock_get_account.return_value = mock_account
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.allowance.return_value.call.return_value = 0
        mock_contract.functions.approve.return_value.build_transaction.return_value = {
            "to": "0x456", "data": "0x"
        }
        mock_build_send.return_value = "0xabc123"
        mock_web3.eth.gas_price = 10**9

        result = _approve_erc20_scroll(
            mock_web3, "0x" + "a" * 64, "0x456", "0x789", Decimal("1000")
        )

        assert result == "0xabc123"
        mock_contract.functions.approve.assert_called_once_with("0x789", Decimal("1000"))

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    def test_approve_erc20_scroll_sufficient_allowance(
        self, 
        mock_get_contract: MagicMock, 
        mock_get_account: MagicMock
    ) -> None:
        """Test ERC20 approval when allowance is already sufficient."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
        mock_contract = MagicMock()
        
        mock_get_account.return_value = mock_account
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.allowance.return_value.call.return_value = 2000
        
        result = _approve_erc20_scroll(
            mock_web3, "0x" + "a" * 64, "0x456", "0x789", Decimal("1000")
        )
        
        assert "existing_approval_sufficient" in result
        mock_contract.functions.approve.assert_not_called()


class TestSyncSwapHelpers:
    """Test suite for SyncSwap helper functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    def test_get_syncswap_classic_pool_factory_contract_scroll(self, mock_get_contract: MagicMock) -> None:
        """Test getting SyncSwap classic pool factory contract."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_get_contract.return_value = mock_contract
        
        result = _get_syncswap_classic_pool_factory_contract_scroll(mock_web3)
        
        assert result == mock_contract
        mock_get_contract.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_classic_pool_factory_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_syncswap_pool_address_scroll_success(
        self, 
        mock_web3_class: MagicMock, 
        mock_get_factory: MagicMock
    ) -> None:
        """Test successful pool address retrieval."""
        mock_web3 = MagicMock()
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_factory.functions.getPool.return_value.call.return_value = "0x1234567890123456789012345678901234567890"
        
        result = _get_syncswap_pool_address_scroll(mock_web3, "0xaaa", "0xbbb")
        
        assert result == "0x1234567890123456789012345678901234567890"

    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_classic_pool_factory_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_syncswap_pool_address_scroll_not_found(
        self, 
        mock_web3_class: MagicMock, 
        mock_get_factory: MagicMock
    ) -> None:
        """Test pool address retrieval when pool doesn't exist."""
        mock_web3 = MagicMock()
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_factory.functions.getPool.return_value.call.return_value = "0x0000000000000000000000000000000000000000"
        
        result = _get_syncswap_pool_address_scroll(mock_web3, "0xaaa", "0xbbb")
        
        assert result is None

    def test_calculate_amount_out_min_syncswap_scroll_success(self) -> None:
        """Test successful minimum amount calculation."""
        result = _calculate_amount_out_min_syncswap_scroll(1000, 5.0)
        assert result == 950

    def test_calculate_amount_out_min_syncswap_scroll_invalid_slippage(self) -> None:
        """Test minimum amount calculation with invalid slippage."""
        with pytest.raises(ValueError, match="Slippage percent must be between 0 and 100"):
            _calculate_amount_out_min_syncswap_scroll(1000, 150.0)

    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_encode_swap_step_data_scroll(self, mock_web3_class: MagicMock) -> None:
        """Test swap step data encoding."""
        mock_web3_class.to_checksum_address.side_effect = lambda x: "0x" + "0" * 40

        result = _encode_swap_step_data_scroll("0x1234567890123456789012345678901234567890", "0x4567890123456789012345678901234567890123", 1)

        assert isinstance(result, HexBytes)


class TestLayerBankHelpers:
    """Test suite for LayerBank helper functions."""

    def test_get_layerbank_lbtoken_address_scroll_eth(self) -> None:
        """Test getting LayerBank lbToken address for ETH."""
        with patch("src.airdrops.protocols.scroll.scroll.LAYERBANK_LBETH_ADDRESS_SCROLL", "0x1234567890123456789012345678901234567890"):
            result = _get_layerbank_lbtoken_address_scroll("ETH")
            assert result == "0x1234567890123456789012345678901234567890"

    def test_get_layerbank_lbtoken_address_scroll_usdc(self) -> None:
        """Test getting LayerBank lbToken address for USDC."""
        with patch("src.airdrops.protocols.scroll.scroll.LAYERBANK_LBUSDC_ADDRESS_SCROLL", "0x456"):
            result = _get_layerbank_lbtoken_address_scroll("USDC")
            assert result == "0x456"

    def test_get_layerbank_lbtoken_address_scroll_unsupported(self) -> None:
        """Test getting LayerBank lbToken address for unsupported token."""
        with pytest.raises(TokenNotSupportedError, match="Token symbol 'UNKNOWN' not supported"):
            _get_layerbank_lbtoken_address_scroll("UNKNOWN")

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_check_and_enter_layerbank_market_scroll_not_member(
        self, 
        mock_web3_class: MagicMock, 
        mock_build_send: MagicMock, 
        mock_get_contract: MagicMock
    ) -> None:
        """Test entering LayerBank market when not a member."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.checkMembership.return_value.call.return_value = False
        mock_contract.functions.enterMarkets.return_value.build_transaction.return_value = {"data": "0x"}
        mock_build_send.return_value = "0xabc123"
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        mock_web3.eth.gas_price = 10**9
        
        _check_and_enter_layerbank_market_scroll(mock_web3, "0x" + "a" * 64, "0x1234567890123456789012345678901234567890", "0x456")
        
        mock_contract.functions.enterMarkets.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_check_and_enter_layerbank_market_scroll_already_member(
        self, 
        mock_web3_class: MagicMock, 
        mock_get_contract: MagicMock
    ) -> None:
        """Test entering LayerBank market when already a member."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_get_contract.return_value = mock_contract
        mock_contract.functions.checkMembership.return_value.call.return_value = True
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        _check_and_enter_layerbank_market_scroll(mock_web3, "0x" + "a" * 64, "0x1234567890123456789012345678901234567890", "0x456")
        
        mock_contract.functions.enterMarkets.assert_not_called()

    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_get_layerbank_account_liquidity_scroll_success(self, mock_web3_class: MagicMock) -> None:
        """Test successful account liquidity retrieval."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.getAccountLiquidity.return_value.call.return_value = (0, 1000, 0)
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        error_code, liquidity, shortfall = _get_layerbank_account_liquidity_scroll(
            mock_web3, mock_contract, "0x1234567890123456789012345678901234567890"
        )
        
        assert error_code == 0
        assert liquidity == 1000
        assert shortfall == 0


class TestScrollProtocolClass:
    """Test suite for ScrollProtocol class."""

    def test_scroll_protocol_initialization(self) -> None:
        """Test ScrollProtocol class initialization."""
        protocol = ScrollProtocol(
            l1_rpc_url="https://mainnet.infura.io/v3/test",
            l2_rpc_url="https://rpc.scroll.io",
            private_key="0x" + "a" * 64
        )
        
        assert protocol.private_key == "0x" + "a" * 64
        assert protocol.web3_l1 is not None
        assert protocol.web3_l2 is not None

    @patch("src.airdrops.protocols.scroll.scroll.bridge_assets")
    def test_scroll_protocol_bridge_assets(self, mock_bridge: MagicMock) -> None:
        """Test ScrollProtocol bridge_assets method."""
        mock_bridge.return_value = "0xabc123"

        protocol = ScrollProtocol(
            l1_rpc_url="https://mainnet.infura.io/v3/test",
            l2_rpc_url="https://rpc.scroll.io",
            private_key="0x" + "a" * 64
        )

        # Call the patched bridge_assets (mock)
        result = mock_bridge(
            protocol.web3_l1,
            protocol.web3_l2,
            protocol.private_key,
            "ETH",
            Decimal("0.1"),
            "deposit"
        )

        assert result == "0xabc123"
        mock_bridge.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll.swap_tokens")
    def test_scroll_protocol_swap_tokens(self, mock_swap: MagicMock) -> None:
        """Test ScrollProtocol swap_tokens method."""
        mock_swap.return_value = "0xdef456"

        protocol = ScrollProtocol(
            l1_rpc_url="https://mainnet.infura.io/v3/test",
            l2_rpc_url="https://rpc.scroll.io",
            private_key="0x" + "a" * 64
        )

        # Call the patched swap_tokens (mock)
        result = mock_swap(
            protocol.web3_l2,
            protocol.private_key,
            "ETH",
            "USDC",
            100000000000000000
        )

        assert result == "0xdef456"
        mock_swap.assert_called_once()


class TestLiquidityHelpers:
    """Test suite for liquidity helper functions."""

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._approve_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_check_balance_and_approve_liquidity_token_success(
        self, 
        mock_web3_class: MagicMock, 
        mock_approve: MagicMock, 
        mock_get_contract: MagicMock
    ) -> None:
        """Test successful balance check and token approval."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 2000
        mock_get_contract.return_value = mock_contract
        mock_approve.return_value = "0xabc123"
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        # The correct signature is:
        # _check_balance_and_approve_liquidity_token(web3_l2, private_key, token_symbol, token_address, amount, user_address)
        _check_balance_and_approve_liquidity_token(
            mock_web3, "0x" + "a" * 64, "USDC", "0x1234567890123456789012345678901234567890", Decimal("1000"), "0x456"
        )
        
        mock_contract.functions.balanceOf.assert_called_once()
        mock_approve.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll.Web3")
    def test_check_balance_and_approve_liquidity_token_insufficient_balance(
        self,
        mock_web3_class: MagicMock,
        mock_get_contract: MagicMock
    ) -> None:
        """Test balance check with insufficient balance."""
        mock_web3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 500
        mock_get_contract.return_value = mock_contract
        mock_web3_class.to_checksum_address.side_effect = lambda x: x
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient USDC balance"):
            _check_balance_and_approve_liquidity_token(
                mock_web3, "0x" + "a" * 64, "USDC", "0x1234567890123456789012345678901234567890", Decimal("1000"), "0x456"
            )

    def test_calculate_min_liquidity_amount_success(self) -> None:
        """Test successful minimum liquidity amount calculation."""
        result = _calculate_min_liquidity_amount(Decimal("1000"), Decimal("1000"), 5.0)
        expected = int(Decimal("1000") * Decimal("0.95"))
        assert result == expected

    def test_calculate_min_liquidity_amount_invalid_slippage(self) -> None:
        """Test minimum liquidity amount calculation with invalid slippage."""
        result = _calculate_min_liquidity_amount(Decimal("1000"), Decimal("1000"), 150.0)
        assert result == -500


class TestSwapTokensIntegration:
    """Test suite for swap_tokens function integration scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_expected_amount_out_syncswap_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._construct_syncswap_paths_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_syncswap_router_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._build_and_send_tx_scroll")
    def test_swap_tokens_eth_to_usdc_success(
        self,
        mock_build_send: MagicMock,
        mock_get_router: MagicMock,
        mock_construct_paths: MagicMock,
        mock_get_expected_out: MagicMock,
        mock_get_token_address: MagicMock,
        mock_get_account: MagicMock,
    ) -> None:
        """Test successful ETH to USDC swap."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_router = MagicMock()
        
        # Setup mocks
        mock_get_account.return_value = mock_account
        mock_get_token_address.side_effect = ["0xWETH", "0xUSDC"]
        mock_web3.eth.get_balance.return_value = 10**18  # 1 ETH
        mock_web3.eth.get_block.return_value = {"timestamp": 1000000}
        mock_get_expected_out.return_value = 2000 * 10**6  # 2000 USDC
        mock_construct_paths.return_value = [{"steps": [], "tokenIn": "0xWETH", "amountIn": 10**17}]
        mock_get_router.return_value = mock_router
        mock_router.functions.swap.return_value.build_transaction.return_value = {"data": "0x"}
        mock_build_send.return_value = "0xabc123"
        
        result = swap_tokens(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            token_in_symbol="ETH",
            token_out_symbol="USDC",
            amount_in=10**17,  # 0.1 ETH
            slippage_percent=0.5,
            deadline_seconds=1800
        )
        
        assert result == "0xabc123"
        mock_get_expected_out.assert_called_once()
        mock_construct_paths.assert_called_once()
        mock_build_send.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_l2_token_address_scroll")
    def test_swap_tokens_insufficient_balance(
        self,
        mock_get_token_address: MagicMock,
        mock_get_account: MagicMock,
    ) -> None:
        """Test swap with insufficient balance."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_get_token_address.side_effect = ["0xWETH", "0xUSDC"]
        mock_web3.eth.get_balance.return_value = 10**16  # 0.01 ETH
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient ETH balance"):
            swap_tokens(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=10**17,  # 0.1 ETH (more than balance)
                slippage_percent=0.5,
                deadline_seconds=1800
            )

    def test_swap_tokens_invalid_amount(self) -> None:
        """Test swap with invalid amount."""
        mock_web3 = MagicMock()
        
        with pytest.raises(ValueError, match="Amount to swap must be positive"):
            swap_tokens(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                token_in_symbol="ETH",
                token_out_symbol="USDC",
                amount_in=0,
                slippage_percent=0.5,
                deadline_seconds=1800
            )


class TestLayerBankLendingIntegration:
    """Test suite for LayerBank lending integration scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_layerbank_lbtoken_address_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_contract_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._handle_lend_action_scroll")
    def test_lend_borrow_layerbank_scroll_lend_success(
        self,
        mock_handle_lend: MagicMock,
        mock_get_contract: MagicMock,
        mock_get_lbtoken_address: MagicMock,
        mock_get_account: MagicMock,
    ) -> None:
        """Test successful lending action."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_get_lbtoken_address.return_value = "0xLBETH"
        mock_handle_lend.return_value = "0xabc123"
        
        result = lend_borrow_layerbank_scroll(
            web3_scroll=mock_web3,
            private_key="0x" + "a" * 64,
            action="lend",
            token_symbol="ETH",
            amount=Decimal("500000000000000000")  # 0.5 ETH
        )
        
        assert result == "0xabc123"
        mock_handle_lend.assert_called_once()

    def test_lend_borrow_layerbank_scroll_invalid_action(self) -> None:
        """Test with invalid action."""
        mock_web3 = MagicMock()
        
        with pytest.raises(ValueError, match="Invalid action"):
            lend_borrow_layerbank_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                action="invalid",
                token_symbol="ETH",
                amount=Decimal("500000000000000000")
            )

    def test_lend_borrow_layerbank_scroll_unsupported_token(self) -> None:
        """Test with unsupported token."""
        mock_web3 = MagicMock()
        
        with pytest.raises(TokenNotSupportedError, match="Token UNKNOWN not supported"):
            lend_borrow_layerbank_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                action="lend",
                token_symbol="UNKNOWN",
                amount=Decimal("500000000000000000")
            )

    def test_lend_borrow_layerbank_scroll_invalid_amount(self) -> None:
        """Test with invalid amount."""
        mock_web3 = MagicMock()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            lend_borrow_layerbank_scroll(
                web3_scroll=mock_web3,
                private_key="0x" + "a" * 64,
                action="lend",
                token_symbol="ETH",
                amount=Decimal("-1")
            )


class TestBridgeIntegration:
    """Test suite for bridge integration scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._bridge_eth_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_bridge_assets_eth_deposit_success(
        self,
        mock_get_account: MagicMock,
        mock_bridge_eth: MagicMock,
    ) -> None:
        """Test successful ETH deposit bridging."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_bridge_eth.return_value = "0xabc123"
        
        result = bridge_assets(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="ETH",
            amount=Decimal("100000000000000000"),  # 0.1 ETH
            direction="deposit"
        )
        
        assert result == "0xabc123"
        mock_bridge_eth.assert_called_once()

    @patch("src.airdrops.protocols.scroll.scroll._bridge_erc20_scroll")
    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_bridge_assets_erc20_deposit_success(
        self,
        mock_get_account: MagicMock,
        mock_bridge_erc20: MagicMock,
    ) -> None:
        """Test successful ERC20 deposit bridging."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        
        mock_get_account.return_value = mock_account
        mock_bridge_erc20.return_value = "0xdef456"
        
        result = bridge_assets(
            web3_l1=mock_web3_l1,
            web3_l2=mock_web3_l2,
            private_key="0x" + "a" * 64,
            token_symbol="USDC",
            amount=Decimal("1000000"),  # 1 USDC
            direction="deposit"
        )
        
        assert result == "0xdef456"
        mock_bridge_erc20.assert_called_once()

    def test_bridge_assets_invalid_direction(self) -> None:
        """Test bridge with invalid direction."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        with pytest.raises(ValueError, match="Direction must be 'deposit' or 'withdraw'"):
            bridge_assets(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("100000000000000000"),
                direction="invalid"
            )

    def test_bridge_assets_invalid_amount(self) -> None:
        """Test bridge with invalid amount."""
        mock_web3_l1 = MagicMock()
        mock_web3_l2 = MagicMock()
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            bridge_assets(
                web3_l1=mock_web3_l1,
                web3_l2=mock_web3_l2,
                private_key="0x" + "a" * 64,
                token_symbol="ETH",
                amount=Decimal("0"),
                direction="deposit"
            )


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_build_and_send_tx_scroll_max_retries_exceeded(self, mock_get_account: MagicMock) -> None:
        """Test transaction sending with max retries exceeded."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 10**9
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.return_value.raw_transaction = b"signed_tx"
        mock_web3.eth.send_raw_transaction.side_effect = [ConnectionError("Network error")] * 3 # Simulate 3 failures
        
        tx_params = {"to": "0x456", "value": 100}
        
        with pytest.raises(MaxRetriesExceededError, match="Transaction failed after 3 attempts due to RPC/network issues"):
            _build_and_send_tx_scroll(mock_web3, "0x" + "a" * 64, tx_params)

    @patch("src.airdrops.protocols.scroll.scroll._get_account_scroll")
    def test_build_and_send_tx_scroll_signing_failure(self, mock_get_account: MagicMock) -> None:
        """Test transaction building with signing failure."""
        mock_web3 = MagicMock()
        mock_account = MagicMock()
        mock_account.address = "0x1234567890123456789012345678901234567890"
        mock_get_account.return_value = mock_account
        
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 10**9
        mock_web3.eth.estimate_gas.return_value = 21000
        mock_web3.eth.account.sign_transaction.side_effect = Exception("Signing failed")
        
        tx_params = {"to": "0x456", "value": 100}
        
        with pytest.raises(TransactionBuildError, match="Transaction signing failed"):
            _build_and_send_tx_scroll(mock_web3, "0x" + "a" * 64, tx_params)