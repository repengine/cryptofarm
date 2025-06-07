#!/usr/bin/env python3
"""Fix all flake8 long line issues in test_zksync.py."""


def fix_test_file():
    """Fix all long lines in test_zksync.py."""
    with open("tests/protocols/test_zksync.py", "r") as f:
        lines = f.readlines()

    # Process each line and fix long ones
    for i, line in enumerate(lines):

        # Skip if line is not too long
        if len(line.rstrip()) <= 79:
            continue

        # Fix specific patterns
        if (
            'mock_validate_config.assert_called_once_with(mock_config["random_activity"])'
            in line
        ):
            lines[i] = line.replace(
                'mock_validate_config.assert_called_once_with(mock_config["random_activity"])',
                'mock_validate_config.assert_called_once_with(\n            mock_config["random_activity"])',
            )
        elif (
            'mock_init_state.assert_called_once_with(mock_config["random_activity"])'
            in line
        ):
            lines[i] = line.replace(
                'mock_init_state.assert_called_once_with(mock_config["random_activity"])',
                'mock_init_state.assert_called_once_with(\n            mock_config["random_activity"])',
            )
        elif (
            'mock_validate_config.side_effect = ValueError("Invalid configuration")'
            in line
        ):
            lines[i] = line.replace(
                'mock_validate_config.side_effect = ValueError("Invalid configuration")',
                'mock_validate_config.side_effect = ValueError(\n            "Invalid configuration")',
            )
        elif (
            'mock_init_state.side_effect = ValueError("State initialization failed")'
            in line
        ):
            lines[i] = line.replace(
                'mock_init_state.side_effect = ValueError("State initialization failed")',
                'mock_init_state.side_effect = ValueError(\n            "State initialization failed")',
            )
        elif (
            'mock_select_action.side_effect = ValueError("Action selection failed")'
            in line
        ):
            lines[i] = line.replace(
                'mock_select_action.side_effect = ValueError("Action selection failed")',
                'mock_select_action.side_effect = ValueError(\n            "Action selection failed")',
            )
        elif (
            'mock_randomize_params.side_effect = ValueError("Parameter randomization failed")'
            in line
        ):
            lines[i] = line.replace(
                'mock_randomize_params.side_effect = ValueError("Parameter randomization failed")',
                'mock_randomize_params.side_effect = ValueError(\n            "Parameter randomization failed")',
            )
        elif (
            'mock_execute_action.side_effect = ValueError("Action execution failed")'
            in line
        ):
            lines[i] = line.replace(
                'mock_execute_action.side_effect = ValueError("Action execution failed")',
                'mock_execute_action.side_effect = ValueError(\n            "Action execution failed")',
            )
        elif (
            'mock_update_state.side_effect = ValueError("State update failed")' in line
        ):
            lines[i] = line.replace(
                'mock_update_state.side_effect = ValueError("State update failed")',
                'mock_update_state.side_effect = ValueError(\n            "State update failed")',
            )
        elif (
            "def test_validate_random_activity_config_missing_enabled(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_validate_random_activity_config_missing_enabled(self, mock_zksync_instance):",
                "def test_validate_random_activity_config_missing_enabled(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_validate_random_activity_config_missing_actions(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_validate_random_activity_config_missing_actions(self, mock_zksync_instance):",
                "def test_validate_random_activity_config_missing_actions(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_validate_random_activity_config_invalid_weights(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_validate_random_activity_config_invalid_weights(self, mock_zksync_instance):",
                "def test_validate_random_activity_config_invalid_weights(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_validate_random_activity_config_invalid_counts(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_validate_random_activity_config_invalid_counts(self, mock_zksync_instance):",
                "def test_validate_random_activity_config_invalid_counts(\n            self, mock_zksync_instance):",
            )
        elif (
            'with pytest.raises(ValueError, match="Invalid action count range"):'
            in line
        ):
            lines[i] = line.replace(
                'with pytest.raises(ValueError, match="Invalid action count range"):',
                'with pytest.raises(ValueError,\n                           match="Invalid action count range"):',
            )
        elif 'with pytest.raises(ValueError, match="Invalid action weights"):' in line:
            lines[i] = line.replace(
                'with pytest.raises(ValueError, match="Invalid action weights"):',
                'with pytest.raises(ValueError,\n                           match="Invalid action weights"):',
            )
        elif (
            "def test_init_random_activity_state_success(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_init_random_activity_state_success(self, mock_zksync_instance):",
                "def test_init_random_activity_state_success(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_select_random_action_success(self, mock_zksync_instance):" in line
        ):
            lines[i] = line.replace(
                "def test_select_random_action_success(self, mock_zksync_instance):",
                "def test_select_random_action_success(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_randomize_bridge_parameters(self, mock_zksync_instance):" in line
        ):
            lines[i] = line.replace(
                "def test_randomize_bridge_parameters(self, mock_zksync_instance):",
                "def test_randomize_bridge_parameters(\n            self, mock_zksync_instance):",
            )
        elif "def test_randomize_swap_parameters(self, mock_zksync_instance):" in line:
            lines[i] = line.replace(
                "def test_randomize_swap_parameters(self, mock_zksync_instance):",
                "def test_randomize_swap_parameters(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_randomize_lend_borrow_parameters(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_randomize_lend_borrow_parameters(self, mock_zksync_instance):",
                "def test_randomize_lend_borrow_parameters(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_execute_random_action_bridge_eth(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_execute_random_action_bridge_eth(self, mock_zksync_instance):",
                "def test_execute_random_action_bridge_eth(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_execute_random_action_swap_tokens(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_execute_random_action_swap_tokens(self, mock_zksync_instance):",
                "def test_execute_random_action_swap_tokens(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_execute_random_action_lend_borrow(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_execute_random_action_lend_borrow(self, mock_zksync_instance):",
                "def test_execute_random_action_lend_borrow(\n            self, mock_zksync_instance):",
            )
        elif (
            "def test_update_random_activity_state_bridge(self, mock_zksync_instance):"
            in line
        ):
            lines[i] = line.replace(
                "def test_update_random_activity_state_bridge(self, mock_zksync_instance):",
                "def test_update_random_activity_state_bridge(\n            self, mock_zksync_instance):",
            )
        elif (
            "mock_zksync_instance._randomize_bridge_parameters.assert_called_once_with(mock_config, mock_state)"
            in line
        ):
            lines[i] = line.replace(
                "mock_zksync_instance._randomize_bridge_parameters.assert_called_once_with(mock_config, mock_state)",
                "mock_zksync_instance._randomize_bridge_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
            )
        elif (
            "mock_zksync_instance._randomize_swap_parameters.assert_called_once_with(mock_config, mock_state)"
            in line
        ):
            lines[i] = line.replace(
                "mock_zksync_instance._randomize_swap_parameters.assert_called_once_with(mock_config, mock_state)",
                "mock_zksync_instance._randomize_swap_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
            )
        elif (
            "mock_zksync_instance._randomize_lend_borrow_parameters.assert_called_once_with(mock_config, mock_state)"
            in line
        ):
            lines[i] = line.replace(
                "mock_zksync_instance._randomize_lend_borrow_parameters.assert_called_once_with(mock_config, mock_state)",
                "mock_zksync_instance._randomize_lend_borrow_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
            )
        elif (
            'assert result == {"amount": Decimal("0.5"), "destination": "arbitrum"}'
            in line
        ):
            lines[i] = line.replace(
                'assert result == {"amount": Decimal("0.5"), "destination": "arbitrum"}',
                'assert result == {"amount": Decimal("0.5"),\n                         "destination": "arbitrum"}',
            )
        elif (
            'assert result == {"from_token": "ETH", "to_token": "USDC", "amount": 1.0}'
            in line
        ):
            lines[i] = line.replace(
                'assert result == {"from_token": "ETH", "to_token": "USDC", "amount": 1.0}',
                'assert result == {"from_token": "ETH", "to_token": "USDC",\n                         "amount": 1.0}',
            )
        elif (
            'assert result == {"action": "lend", "token": "USDC", "amount": 100.0}'
            in line
        ):
            lines[i] = line.replace(
                'assert result == {"action": "lend", "token": "USDC", "amount": 100.0}',
                'assert result == {"action": "lend", "token": "USDC",\n                         "amount": 100.0}',
            )
        elif (
            'mock_zksync_instance.bridge_eth.assert_called_once_with(Decimal("0.5"), "arbitrum")'
            in line
        ):
            lines[i] = line.replace(
                'mock_zksync_instance.bridge_eth.assert_called_once_with(Decimal("0.5"), "arbitrum")',
                'mock_zksync_instance.bridge_eth.assert_called_once_with(\n            Decimal("0.5"), "arbitrum")',
            )

    with open("tests/protocols/test_zksync.py", "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    fix_test_file()
    print("Fixed test file flake8 issues")
