"""
Tests for zkSync protocol interfaces to achieve 100% coverage.

This module tests the protocol interfaces defined in the interfaces.py module.
"""

from typing import Any
from decimal import Decimal

from src.airdrops.protocols.zksync.interfaces import IZkSyncProtocol


class MockZkSyncProtocol:
    """Mock implementation of IZkSyncProtocol for testing."""
    
    def __init__(self, web3_l1: Any, web3_l2: Any, private_key: str) -> None:
        """Initialize the mock ZkSync protocol instance."""
        self.web3_l1 = web3_l1
        self.web3_l2 = web3_l2
        self.private_key = private_key
    
    def bridge_assets(
        self,
        web3_l1: Any,
        web3_l2: Any,
        private_key: str,
        token_symbol: str,
        amount: Decimal,
        direction: str
    ) -> str:
        """Mock bridge assets implementation."""
        return f"0x{'a' * 64}"
    
    def swap_tokens(
        self,
        web3: Any,
        private_key: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> str:
        """Mock swap tokens implementation."""
        return f"0x{'b' * 64}"


class TestIZkSyncProtocol:
    """Test the IZkSyncProtocol interface."""

    def test_protocol_interface_compliance(self):
        """Test that MockZkSyncProtocol implements IZkSyncProtocol interface."""
        mock_web3_l1 = object()
        mock_web3_l2 = object()
        private_key = "0x" + "1" * 64
        
        # Create instance
        protocol = MockZkSyncProtocol(mock_web3_l1, mock_web3_l2, private_key)
        
        # Test initialization
        assert protocol.web3_l1 is mock_web3_l1
        assert protocol.web3_l2 is mock_web3_l2
        assert protocol.private_key == private_key

    def test_bridge_assets_interface(self):
        """Test bridge_assets method interface."""
        protocol = MockZkSyncProtocol(object(), object(), "0x" + "1" * 64)
        
        result = protocol.bridge_assets(
            web3_l1=object(),
            web3_l2=object(),
            private_key="0x" + "2" * 64,
            token_symbol="ETH",
            amount=Decimal("0.1"),
            direction="deposit"
        )
        
        assert isinstance(result, str)
        assert result.startswith("0x")
        assert len(result) == 66  # 0x + 64 hex chars

    def test_swap_tokens_interface(self):
        """Test swap_tokens method interface."""
        protocol = MockZkSyncProtocol(object(), object(), "0x" + "1" * 64)
        
        result = protocol.swap_tokens(
            web3=object(),
            private_key="0x" + "2" * 64,
            token_in="ETH",
            token_out="USDC",
            amount_in=Decimal("0.1"),
            min_amount_out=Decimal("180"),
            deadline=1234567890
        )
        
        assert isinstance(result, str)
        assert result.startswith("0x")
        assert len(result) == 66  # 0x + 64 hex chars

    def test_protocol_interface_typing(self):
        """Test that the interface can be used for type checking."""
        def process_protocol(protocol: IZkSyncProtocol) -> str:
            """Function that accepts any IZkSyncProtocol implementation."""
            return protocol.bridge_assets(
                web3_l1=object(),
                web3_l2=object(),
                private_key="0x" + "3" * 64,
                token_symbol="USDC",
                amount=Decimal("100"),
                direction="withdraw"
            )
        
        mock_protocol = MockZkSyncProtocol(object(), object(), "0x" + "1" * 64)
        result = process_protocol(mock_protocol)
        
        assert isinstance(result, str)
        assert result.startswith("0x")

    def test_interface_docstring_example(self):
        """Test the example from the interface docstring."""
        def process_zksync_operations(protocol: IZkSyncProtocol) -> None:
            """Type-safe usage of any ZkSync protocol implementation."""
            tx_hash = protocol.bridge_assets(
                web3_l1=object(),
                web3_l2=object(),
                private_key="0x" + "4" * 64,
                token_symbol="ETH",
                amount=Decimal("0.1"),
                direction="deposit"
            )
            assert tx_hash.startswith("0x")
        
        mock_protocol = MockZkSyncProtocol(object(), object(), "0x" + "1" * 64)
        # Should not raise any type errors
        process_zksync_operations(mock_protocol)