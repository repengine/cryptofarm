"""
Tests for the airdrops.shared.utils module.
"""

import pytest
from decimal import Decimal

from airdrops.shared.utils import (  # type: ignore
    get_current_timestamp,
    convert_to_decimal,
    format_currency,
    generate_unique_id,
    load_config,
    save_config,
    ConfigError,
)
import json


def test_get_current_timestamp():
    """Test that get_current_timestamp returns a valid timestamp."""
    timestamp = get_current_timestamp()
    assert isinstance(timestamp, int)
    assert timestamp > 0  # Should be a positive integer


def test_convert_to_decimal_from_float():
    """Test converting a float to Decimal."""
    assert convert_to_decimal(123.45) == Decimal("123.45")
    assert convert_to_decimal(0.0) == Decimal("0")
    assert convert_to_decimal(-10.5) == Decimal("-10.5")


def test_convert_to_decimal_from_int():
    """Test converting an integer to Decimal."""
    assert convert_to_decimal(100) == Decimal("100")
    assert convert_to_decimal(0) == Decimal("0")
    assert convert_to_decimal(-5) == Decimal("-5")


def test_convert_to_decimal_from_str():
    """Test converting a string to Decimal."""
    assert convert_to_decimal("123.45") == Decimal("123.45")
    assert convert_to_decimal("0") == Decimal("0")
    assert convert_to_decimal("-10.5") == Decimal("-10.5")
    assert convert_to_decimal("1.23456789") == Decimal("1.23456789")


def test_convert_to_decimal_from_decimal():
    """Test converting an existing Decimal to Decimal (should return as is)."""
    dec_val = Decimal("99.99")
    assert convert_to_decimal(dec_val) is dec_val


def test_convert_to_decimal_invalid_type():
    """Test converting an invalid type to Decimal raises TypeError."""
    with pytest.raises(TypeError):
        convert_to_decimal([1, 2])
    with pytest.raises(TypeError):
        convert_to_decimal({"a": 1})


def test_convert_to_decimal_invalid_string():
    """Test converting an invalid string to Decimal raises InvalidOperation."""
    with pytest.raises(ValueError):  # Decimal raises InvalidOperation, which is a subclass of ValueError
        convert_to_decimal("abc")
    with pytest.raises(ValueError):
        convert_to_decimal("1.2.3")


def test_format_currency_default():
    """Test formatting currency with default precision."""
    assert format_currency(Decimal("123.456")) == "$123.46"
    assert format_currency(Decimal("100")) == "$100.00"
    assert format_currency(Decimal("0.999")) == "$1.00"
    assert format_currency(Decimal("0.001")) == "$0.00"


def test_format_currency_custom_precision():
    """Test formatting currency with custom precision."""
    assert format_currency(Decimal("123.45678"), precision=4) == "$123.4568"
    assert format_currency(Decimal("10"), precision=0) == "$10"


def test_format_currency_negative_value():
    """Test formatting negative currency values."""
    assert format_currency(Decimal("-123.45")) == "-$123.45"


def test_generate_unique_id():
    """Test that generate_unique_id produces unique strings."""
    ids = set()
    for _ in range(1000):
        new_id = generate_unique_id()
        assert new_id not in ids
        ids.add(new_id)
    assert len(ids) == 1000


def test_load_config_success(tmp_path):
    """Test successful loading of a valid config file."""
    config_data = {"key1": "value1", "key2": 123}
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)

    loaded_config = load_config(str(config_file))
    assert loaded_config == config_data


def test_load_config_file_not_found():
    """Test loading a non-existent config file."""
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config("non_existent_config.json")


def test_load_config_invalid_json(tmp_path):
    """Test loading a config file with invalid JSON."""
    config_file = tmp_path / "invalid_config.json"
    with open(config_file, "w") as f:
        f.write("{invalid json")

    with pytest.raises(ConfigError, match="Error parsing config file"):
        load_config(str(config_file))


def test_save_config_success(tmp_path):
    """Test successful saving of config data."""
    config_data = {"setting1": True, "setting2": [1, 2, 3]}
    config_file = tmp_path / "saved_config.json"

    save_config(config_data, str(config_file))

    assert config_file.exists()
    with open(config_file, "r") as f:
        loaded_data = json.load(f)
    assert loaded_data == config_data


def test_save_config_invalid_path():
    """Test saving config to an invalid path."""
    with pytest.raises(ConfigError, match="Error saving config file"):
        save_config({"a": 1}, "/non_existent_dir/config.json")
