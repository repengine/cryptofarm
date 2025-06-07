#!/usr/bin/env python3
"""Fix remaining flake8 issues in zksync.py and test_zksync.py."""

import re


def fix_zksync_remaining():
    """Fix remaining long lines in zksync.py."""
    with open("src/airdrops/protocols/zksync/zksync.py", "r") as f:
        lines = f.readlines()

    # Fix specific lines by line number
    fixes = {
        1997: '    logger.info("Validating random activity configuration: %s",\n',
        1998: "                config)\n",
        2011: "        raise ValueError(\n",
        2012: '            "Random activity is disabled in configuration")\n',
        2123: "    logger.debug(\"Selected action '%s' with weight %s\",\n",
        2124: "                 action, weight)\n",
        2178: '    logger.debug("Generated swap parameters: %s",\n',
        2179: "                 swap_parameters)\n",
        2354: '        logger.debug("Updated state after %s: %s",\n',
        2355: "                     action, new_state)\n",
    }

    # Apply line-specific fixes
    for line_num, replacement in fixes.items():
        if line_num <= len(lines):
            # Check if this is a line we need to replace
            line = lines[line_num - 1]
            if 'logger.info("Validating random activity configuration' in line:
                lines[line_num - 1] = (
                    '    logger.info("Validating random activity configuration: %s",\n'
                )
                lines.insert(line_num, "                config)\n")
            elif 'raise ValueError("Random activity is disabled' in line:
                lines[line_num - 1] = "        raise ValueError(\n"
                lines.insert(
                    line_num,
                    '            "Random activity is disabled in configuration")\n',
                )
            elif 'logger.debug("Selected action' in line:
                lines[line_num - 1] = (
                    "    logger.debug(\"Selected action '%s' with weight %s\",\n"
                )
                lines.insert(line_num, "                 action, weight)\n")
            elif 'logger.debug("Generated swap parameters' in line:
                lines[line_num - 1] = (
                    '    logger.debug("Generated swap parameters: %s",\n'
                )
                lines.insert(line_num, "                 swap_parameters)\n")
            elif 'logger.debug("Updated state after' in line:
                lines[line_num - 1] = (
                    '        logger.debug("Updated state after %s: %s",\n'
                )
                lines.insert(line_num, "                     action, new_state)\n")

    with open("src/airdrops/protocols/zksync/zksync.py", "w") as f:
        f.writelines(lines)


def fix_test_remaining():
    """Fix remaining long lines in test_zksync.py."""
    with open("tests/protocols/test_zksync.py", "r") as f:
        content = f.read()

    # Fix long lines with specific patterns
    patterns = [
        # Function definitions
        (
            r"def test_validate_random_activity_config_missing_enabled\(self, mock_zksync_instance\):",
            "def test_validate_random_activity_config_missing_enabled(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_validate_random_activity_config_missing_actions\(self, mock_zksync_instance\):",
            "def test_validate_random_activity_config_missing_actions(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_validate_random_activity_config_invalid_weights\(self, mock_zksync_instance\):",
            "def test_validate_random_activity_config_invalid_weights(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_validate_random_activity_config_invalid_counts\(self, mock_zksync_instance\):",
            "def test_validate_random_activity_config_invalid_counts(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_init_random_activity_state_success\(self, mock_zksync_instance\):",
            "def test_init_random_activity_state_success(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_select_random_action_success\(self, mock_zksync_instance\):",
            "def test_select_random_action_success(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_randomize_bridge_parameters\(self, mock_zksync_instance\):",
            "def test_randomize_bridge_parameters(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_randomize_swap_parameters\(self, mock_zksync_instance\):",
            "def test_randomize_swap_parameters(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_randomize_lend_borrow_parameters\(self, mock_zksync_instance\):",
            "def test_randomize_lend_borrow_parameters(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_execute_random_action_bridge_eth\(self, mock_zksync_instance\):",
            "def test_execute_random_action_bridge_eth(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_execute_random_action_swap_tokens\(self, mock_zksync_instance\):",
            "def test_execute_random_action_swap_tokens(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_execute_random_action_lend_borrow\(self, mock_zksync_instance\):",
            "def test_execute_random_action_lend_borrow(\n            self, mock_zksync_instance):",
        ),
        (
            r"def test_update_random_activity_state_bridge\(self, mock_zksync_instance\):",
            "def test_update_random_activity_state_bridge(\n            self, mock_zksync_instance):",
        ),
        # Assert calls
        (
            r'mock_validate_config\.assert_called_once_with\(mock_config\["random_activity"\]\)',
            'mock_validate_config.assert_called_once_with(\n            mock_config["random_activity"])',
        ),
        (
            r'mock_init_state\.assert_called_once_with\(mock_config\["random_activity"\]\)',
            'mock_init_state.assert_called_once_with(\n            mock_config["random_activity"])',
        ),
        # Side effects
        (
            r'mock_validate_config\.side_effect = ValueError\("Invalid configuration"\)',
            'mock_validate_config.side_effect = ValueError(\n            "Invalid configuration")',
        ),
        (
            r'mock_init_state\.side_effect = ValueError\("State initialization failed"\)',
            'mock_init_state.side_effect = ValueError(\n            "State initialization failed")',
        ),
        (
            r'mock_select_action\.side_effect = ValueError\("Action selection failed"\)',
            'mock_select_action.side_effect = ValueError(\n            "Action selection failed")',
        ),
        (
            r'mock_randomize_params\.side_effect = ValueError\("Parameter randomization failed"\)',
            'mock_randomize_params.side_effect = ValueError(\n            "Parameter randomization failed")',
        ),
        (
            r'mock_execute_action\.side_effect = ValueError\("Action execution failed"\)',
            'mock_execute_action.side_effect = ValueError(\n            "Action execution failed")',
        ),
        (
            r'mock_update_state\.side_effect = ValueError\("State update failed"\)',
            'mock_update_state.side_effect = ValueError(\n            "State update failed")',
        ),
        # Pytest raises
        (
            r'with pytest\.raises\(ValueError, match="Invalid action count range"\):',
            'with pytest.raises(ValueError,\n                           match="Invalid action count range"):',
        ),
        (
            r'with pytest\.raises\(ValueError, match="Invalid action weights"\):',
            'with pytest.raises(ValueError,\n                           match="Invalid action weights"):',
        ),
        # Very long assert calls
        (
            r"mock_zksync_instance\._randomize_bridge_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "mock_zksync_instance._randomize_bridge_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
        ),
        (
            r"mock_zksync_instance\._randomize_swap_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "mock_zksync_instance._randomize_swap_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
        ),
        (
            r"mock_zksync_instance\._randomize_lend_borrow_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "mock_zksync_instance._randomize_lend_borrow_parameters.\\\n            assert_called_once_with(mock_config, mock_state)",
        ),
        # Assert statements
        (
            r'assert result == \{"amount": Decimal\("0\.5"\), "destination": "arbitrum"\}',
            'assert result == {"amount": Decimal("0.5"),\n                         "destination": "arbitrum"}',
        ),
        (
            r'assert result == \{"from_token": "ETH", "to_token": "USDC", "amount": 1\.0\}',
            'assert result == {"from_token": "ETH", "to_token": "USDC",\n                         "amount": 1.0}',
        ),
        (
            r'assert result == \{"action": "lend", "token": "USDC", "amount": 100\.0\}',
            'assert result == {"action": "lend", "token": "USDC",\n                         "amount": 100.0}',
        ),
        (
            r'mock_zksync_instance\.bridge_eth\.assert_called_once_with\(Decimal\("0\.5"\), "arbitrum"\)',
            'mock_zksync_instance.bridge_eth.assert_called_once_with(\n            Decimal("0.5"), "arbitrum")',
        ),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    with open("tests/protocols/test_zksync.py", "w") as f:
        f.write(content)


if __name__ == "__main__":
    fix_zksync_remaining()
    fix_test_remaining()
    print("Fixed remaining flake8 issues")
