#!/usr/bin/env python3
"""Fix flake8 issues in zksync.py and test_zksync.py for random activity implementation."""

import re


def fix_zksync_file():
    """Fix flake8 issues in zksync.py."""
    with open("src/airdrops/protocols/zksync/zksync.py", "r") as f:
        content = f.read()

    # Fix line 1371-1372, 1376 - break long lines
    content = re.sub(
        r'        logger\.info\("Performing random activity with config: %s", config\)',
        '        logger.info("Performing random activity with config: %s",\n'
        "                    config)",
        content,
    )

    content = re.sub(
        r'        logger\.info\("Random activity completed successfully\. Actions performed: %s", actions_performed\)',
        '        logger.info("Random activity completed successfully. "\n'
        '                    "Actions performed: %s", actions_performed)',
        content,
    )

    content = re.sub(
        r'        logger\.error\("Random activity failed after %d actions: %s", len\(actions_performed\), str\(e\)\)',
        '        logger.error("Random activity failed after %d actions: %s",\n'
        "                     len(actions_performed), str(e))",
        content,
    )

    # Fix line 1773 - add blank line before function
    content = re.sub(
        r"(\n)def _validate_random_activity_config\(",
        r"\n\ndef _validate_random_activity_config(",
        content,
    )

    # Fix line 1996 - break long line
    content = re.sub(
        r'    logger\.info\("Validating random activity configuration: %s", config\)',
        '    logger.info("Validating random activity configuration: %s",\n'
        "                config)",
        content,
    )

    # Fix line 2010 - break long line
    content = re.sub(
        r'        raise ValueError\("Random activity is disabled in configuration"\)',
        "        raise ValueError(\n"
        '            "Random activity is disabled in configuration")',
        content,
    )

    # Fix line 2122 - break long line
    content = re.sub(
        r'    logger\.debug\("Selected action \'%s\' with weight %s", action, weight\)',
        "    logger.debug(\"Selected action '%s' with weight %s\",\n"
        "                 action, weight)",
        content,
    )

    # Fix line 2177 - break long line
    content = re.sub(
        r'    logger\.debug\("Generated swap parameters: %s", swap_parameters\)',
        '    logger.debug("Generated swap parameters: %s",\n'
        "                 swap_parameters)",
        content,
    )

    # Fix line 2353 - break long line
    content = re.sub(
        r'        logger\.debug\("Updated state after %s: %s", action, new_state\)',
        '        logger.debug("Updated state after %s: %s",\n'
        "                     action, new_state)",
        content,
    )

    # Remove whitespace from blank lines
    content = re.sub(r"\n[ \t]+\n", "\n\n", content)

    with open("src/airdrops/protocols/zksync/zksync.py", "w") as f:
        f.write(content)


def fix_test_file():
    """Fix flake8 issues in test_zksync.py."""
    with open("tests/protocols/test_zksync.py", "r") as f:
        content = f.read()

    # Fix long lines by breaking them appropriately
    fixes = [
        # Line 1554-1555
        (
            r'        mock_validate_config\.assert_called_once_with\(mock_config\["random_activity"\]\)',
            "        mock_validate_config.assert_called_once_with(\n"
            '            mock_config["random_activity"])',
        ),
        (
            r'        mock_init_state\.assert_called_once_with\(mock_config\["random_activity"\]\)',
            "        mock_init_state.assert_called_once_with(\n"
            '            mock_config["random_activity"])',
        ),
        # Line 1575-1576
        (
            r'        mock_validate_config\.side_effect = ValueError\("Invalid configuration"\)',
            "        mock_validate_config.side_effect = ValueError(\n"
            '            "Invalid configuration")',
        ),
        (
            r'        mock_init_state\.side_effect = ValueError\("State initialization failed"\)',
            "        mock_init_state.side_effect = ValueError(\n"
            '            "State initialization failed")',
        ),
        # Line 1580-1582
        (
            r'        mock_select_action\.side_effect = ValueError\("Action selection failed"\)',
            "        mock_select_action.side_effect = ValueError(\n"
            '            "Action selection failed")',
        ),
        (
            r'        mock_randomize_params\.side_effect = ValueError\("Parameter randomization failed"\)',
            "        mock_randomize_params.side_effect = ValueError(\n"
            '            "Parameter randomization failed")',
        ),
        (
            r'        mock_execute_action\.side_effect = ValueError\("Action execution failed"\)',
            "        mock_execute_action.side_effect = ValueError(\n"
            '            "Action execution failed")',
        ),
        # Line 1588
        (
            r'        mock_update_state\.side_effect = ValueError\("State update failed"\)',
            "        mock_update_state.side_effect = ValueError(\n"
            '            "State update failed")',
        ),
        # Line 1591-1592
        (
            r"    def test_validate_random_activity_config_missing_enabled\(self, mock_zksync_instance\):",
            "    def test_validate_random_activity_config_missing_enabled(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_validate_random_activity_config_missing_actions\(self, mock_zksync_instance\):",
            "    def test_validate_random_activity_config_missing_actions(\n"
            "            self, mock_zksync_instance):",
        ),
        # Line 1605-1606
        (
            r"    def test_validate_random_activity_config_invalid_weights\(self, mock_zksync_instance\):",
            "    def test_validate_random_activity_config_invalid_weights(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_validate_random_activity_config_invalid_counts\(self, mock_zksync_instance\):",
            "    def test_validate_random_activity_config_invalid_counts(\n"
            "            self, mock_zksync_instance):",
        ),
        # Line 1610, 1613
        (
            r'        with pytest\.raises\(ValueError, match="Invalid action count range"\):',
            "        with pytest.raises(ValueError,\n"
            '                           match="Invalid action count range"):',
        ),
        (
            r'        with pytest\.raises\(ValueError, match="Invalid action weights"\):',
            "        with pytest.raises(ValueError,\n"
            '                           match="Invalid action weights"):',
        ),
        # Continue with other long lines...
        (
            r"    def test_init_random_activity_state_success\(self, mock_zksync_instance\):",
            "    def test_init_random_activity_state_success(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_select_random_action_success\(self, mock_zksync_instance\):",
            "    def test_select_random_action_success(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_randomize_bridge_parameters\(self, mock_zksync_instance\):",
            "    def test_randomize_bridge_parameters(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_randomize_swap_parameters\(self, mock_zksync_instance\):",
            "    def test_randomize_swap_parameters(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_randomize_lend_borrow_parameters\(self, mock_zksync_instance\):",
            "    def test_randomize_lend_borrow_parameters(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_execute_random_action_bridge_eth\(self, mock_zksync_instance\):",
            "    def test_execute_random_action_bridge_eth(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_execute_random_action_swap_tokens\(self, mock_zksync_instance\):",
            "    def test_execute_random_action_swap_tokens(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_execute_random_action_lend_borrow\(self, mock_zksync_instance\):",
            "    def test_execute_random_action_lend_borrow(\n"
            "            self, mock_zksync_instance):",
        ),
        (
            r"    def test_update_random_activity_state_bridge\(self, mock_zksync_instance\):",
            "    def test_update_random_activity_state_bridge(\n"
            "            self, mock_zksync_instance):",
        ),
        # Line 1759-1761 - very long lines
        (
            r"        mock_zksync_instance\._randomize_bridge_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "        mock_zksync_instance._randomize_bridge_parameters.\\\n"
            "            assert_called_once_with(mock_config, mock_state)",
        ),
        (
            r"        mock_zksync_instance\._randomize_swap_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "        mock_zksync_instance._randomize_swap_parameters.\\\n"
            "            assert_called_once_with(mock_config, mock_state)",
        ),
        (
            r"        mock_zksync_instance\._randomize_lend_borrow_parameters\.assert_called_once_with\(mock_config, mock_state\)",
            "        mock_zksync_instance._randomize_lend_borrow_parameters.\\\n"
            "            assert_called_once_with(mock_config, mock_state)",
        ),
        # Line 1771, 1776
        (
            r'        assert result == \{"amount": Decimal\("0\.5"\), "destination": "arbitrum"\}',
            '        assert result == {"amount": Decimal("0.5"),\n'
            '                         "destination": "arbitrum"}',
        ),
        (
            r'        assert result == \{"from_token": "ETH", "to_token": "USDC", "amount": 1\.0\}',
            '        assert result == {"from_token": "ETH", "to_token": "USDC",\n'
            '                         "amount": 1.0}',
        ),
        # Line 1791, 1793
        (
            r'        assert result == \{"action": "lend", "token": "USDC", "amount": 100\.0\}',
            '        assert result == {"action": "lend", "token": "USDC",\n'
            '                         "amount": 100.0}',
        ),
        (
            r'        mock_zksync_instance\.bridge_eth\.assert_called_once_with\(Decimal\("0\.5"\), "arbitrum"\)',
            "        mock_zksync_instance.bridge_eth.assert_called_once_with(\n"
            '            Decimal("0.5"), "arbitrum")',
        ),
    ]

    for old, new in fixes:
        content = re.sub(re.escape(old), new, content)

    # Remove whitespace from blank lines
    content = re.sub(r"\n[ \t]+\n", "\n\n", content)

    with open("tests/protocols/test_zksync.py", "w") as f:
        f.write(content)


if __name__ == "__main__":
    fix_zksync_file()
    fix_test_file()
    print("Fixed flake8 issues in both files")
