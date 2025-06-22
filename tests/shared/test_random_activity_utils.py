"""
Tests for random activity utility functions.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch

from airdrops.shared.random_activity_utils import (
    select_activity_by_weight,
    generate_random_amount,
    select_random_tokens,
)


class TestSelectActivityByWeight:
    """Test cases for select_activity_by_weight function."""

    def test_select_activity_by_weight_valid_input(self) -> None:
        """Test selecting activity with valid weighted input."""
        activities = [
            {'name': 'swap', 'weight': 50},
            {'name': 'lend', 'weight': 30},
            {'name': 'bridge', 'weight': 20}
        ]
        
        # Mock random.choices to return predictable result
        with patch('airdrops.shared.random_activity_utils.random.choices', return_value=['swap']):
            result = select_activity_by_weight(activities)
            assert result == 'swap'

    def test_select_activity_by_weight_single_activity(self) -> None:
        """Test selecting from single activity."""
        activities = [{'name': 'swap', 'weight': 100}]
        
        result = select_activity_by_weight(activities)
        assert result == 'swap'

    def test_select_activity_by_weight_empty_list(self) -> None:
        """Test error handling for empty activities list."""
        with pytest.raises(ValueError, match="Activities list cannot be empty"):
            select_activity_by_weight([])

    def test_select_activity_by_weight_missing_name_key(self) -> None:
        """Test error handling for missing 'name' key."""
        activities = [{'weight': 50}]
        
        with pytest.raises(ValueError, match="Each activity must have a 'name' key"):
            select_activity_by_weight(activities)

    def test_select_activity_by_weight_missing_weight_key(self) -> None:
        """Test error handling for missing 'weight' key."""
        activities = [{'name': 'swap'}]
        
        with pytest.raises(ValueError, match="Each activity must have a 'weight' key"):
            select_activity_by_weight(activities)

    def test_select_activity_by_weight_invalid_weight_zero(self) -> None:
        """Test error handling for zero weight."""
        activities = [{'name': 'swap', 'weight': 0}]
        
        with pytest.raises(ValueError, match="Activity weights must be positive numbers"):
            select_activity_by_weight(activities)

    def test_select_activity_by_weight_invalid_weight_negative(self) -> None:
        """Test error handling for negative weight."""
        activities = [{'name': 'swap', 'weight': -10}]
        
        with pytest.raises(ValueError, match="Activity weights must be positive numbers"):
            select_activity_by_weight(activities)

    def test_select_activity_by_weight_invalid_weight_type(self) -> None:
        """Test error handling for invalid weight type."""
        activities = [{'name': 'swap', 'weight': 'invalid'}]
        
        with pytest.raises(ValueError, match="Activity weights must be positive numbers"):
            select_activity_by_weight(activities)

    def test_select_activity_by_weight_non_dict_activity(self) -> None:
        """Test error handling for non-dictionary activity."""
        activities = ['invalid_activity']
        
        with pytest.raises(ValueError, match="Each activity must be a dictionary"):
            select_activity_by_weight(activities)  # type: ignore[arg-type]

    def test_select_activity_by_weight_distribution(self) -> None:
        """Test that weighted selection respects probability distribution."""
        activities = [
            {'name': 'high_weight', 'weight': 90},
            {'name': 'low_weight', 'weight': 10}
        ]
        
        # Run multiple selections and check distribution
        results = []
        for _ in range(100):
            result = select_activity_by_weight(activities)
            results.append(result)
        
        high_weight_count = results.count('high_weight')
        low_weight_count = results.count('low_weight')
        
        # High weight should be selected more often (allowing some variance)
        assert high_weight_count > low_weight_count


class TestGenerateRandomAmount:
    """Test cases for generate_random_amount function."""

    def test_generate_random_amount_valid_range(self) -> None:
        """Test generating amount within valid range."""
        min_amount = Decimal('0.01')
        max_amount = Decimal('1.00')
        decimals = 2
        
        result = generate_random_amount(min_amount, max_amount, decimals)
        
        assert isinstance(result, Decimal)
        assert min_amount <= result <= max_amount
        # Check decimal places - handle special values
        exponent = result.as_tuple().exponent
        if isinstance(exponent, int):
            assert exponent >= -decimals

    def test_generate_random_amount_equal_bounds(self) -> None:
        """Test generating amount when min equals max."""
        amount = Decimal('0.50')
        decimals = 2
        
        result = generate_random_amount(amount, amount, decimals)
        
        assert result == amount

    def test_generate_random_amount_zero_decimals(self) -> None:
        """Test generating amount with zero decimal places."""
        min_amount = Decimal('1')
        max_amount = Decimal('10')
        decimals = 0
        
        result = generate_random_amount(min_amount, max_amount, decimals)
        
        assert isinstance(result, Decimal)
        assert min_amount <= result <= max_amount
        assert result % 1 == 0  # Should be whole number

    def test_generate_random_amount_high_precision(self) -> None:
        """Test generating amount with high decimal precision."""
        min_amount = Decimal('0.000001')
        max_amount = Decimal('0.000010')
        decimals = 6
        
        result = generate_random_amount(min_amount, max_amount, decimals)
        
        assert isinstance(result, Decimal)
        assert min_amount <= result <= max_amount

    def test_generate_random_amount_invalid_range(self) -> None:
        """Test error handling when min > max."""
        min_amount = Decimal('1.00')
        max_amount = Decimal('0.50')
        decimals = 2
        
        with pytest.raises(ValueError, match="min_amount cannot be greater than max_amount"):
            generate_random_amount(min_amount, max_amount, decimals)

    def test_generate_random_amount_negative_decimals(self) -> None:
        """Test error handling for negative decimals."""
        min_amount = Decimal('0.01')
        max_amount = Decimal('1.00')
        decimals = -1
        
        with pytest.raises(ValueError, match="decimals must be non-negative"):
            generate_random_amount(min_amount, max_amount, decimals)

    def test_generate_random_amount_multiple_calls_different(self) -> None:
        """Test that multiple calls produce different results."""
        min_amount = Decimal('0.01')
        max_amount = Decimal('1.00')
        decimals = 4
        
        results = set()
        for _ in range(10):
            result = generate_random_amount(min_amount, max_amount, decimals)
            results.add(result)
        
        # Should have multiple different values (allowing for small chance of duplicates)
        assert len(results) > 1


class TestSelectRandomTokens:
    """Test cases for select_random_tokens function."""

    def test_select_random_tokens_valid_config(self) -> None:
        """Test selecting tokens from valid configuration."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'},
            'DAI': {'address': '0x789'},
            'WBTC': {'address': '0xabc'}
        }
        
        result = select_random_tokens(token_config, 2)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(token in token_config for token in result)
        assert len(set(result)) == 2  # Should be unique tokens

    def test_select_random_tokens_default_num_tokens(self) -> None:
        """Test selecting tokens with default num_tokens parameter."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'},
            'DAI': {'address': '0x789'}
        }
        
        result = select_random_tokens(token_config)
        
        assert len(result) == 2  # Default value

    def test_select_random_tokens_single_token(self) -> None:
        """Test selecting single token."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'}
        }
        
        result = select_random_tokens(token_config, 1)
        
        assert len(result) == 1
        assert result[0] in token_config

    def test_select_random_tokens_all_tokens(self) -> None:
        """Test selecting all available tokens."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'}
        }
        
        result = select_random_tokens(token_config, 2)
        
        assert len(result) == 2
        assert set(result) == set(token_config.keys())

    def test_select_random_tokens_empty_config(self) -> None:
        """Test error handling for empty token configuration."""
        with pytest.raises(ValueError, match="token_config cannot be empty"):
            select_random_tokens({}, 2)

    def test_select_random_tokens_zero_num_tokens(self) -> None:
        """Test error handling for zero num_tokens."""
        token_config = {'ETH': {'address': '0x123'}}
        
        with pytest.raises(ValueError, match="num_tokens must be positive"):
            select_random_tokens(token_config, 0)

    def test_select_random_tokens_negative_num_tokens(self) -> None:
        """Test error handling for negative num_tokens."""
        token_config = {'ETH': {'address': '0x123'}}
        
        with pytest.raises(ValueError, match="num_tokens must be positive"):
            select_random_tokens(token_config, -1)

    def test_select_random_tokens_too_many_requested(self) -> None:
        """Test error handling when requesting more tokens than available."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'}
        }
        
        with pytest.raises(ValueError, match="Cannot select 3 tokens from 2 available tokens"):
            select_random_tokens(token_config, 3)

    def test_select_random_tokens_uniqueness(self) -> None:
        """Test that selected tokens are unique."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'},
            'DAI': {'address': '0x789'},
            'WBTC': {'address': '0xabc'},
            'LINK': {'address': '0xdef'}
        }
        
        result = select_random_tokens(token_config, 3)
        
        assert len(result) == len(set(result))  # All tokens should be unique

    def test_select_random_tokens_randomness(self) -> None:
        """Test that multiple calls produce different combinations."""
        token_config = {
            'ETH': {'address': '0x123'},
            'USDC': {'address': '0x456'},
            'DAI': {'address': '0x789'},
            'WBTC': {'address': '0xabc'}
        }
        
        results = set()
        for _ in range(10):
            result = select_random_tokens(token_config, 2)
            results.add(result)
        
        # Should have multiple different combinations
        assert len(results) > 1