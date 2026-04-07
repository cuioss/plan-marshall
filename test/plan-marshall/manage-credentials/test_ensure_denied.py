#!/usr/bin/env python3
"""Tests for _cred_ensure_denied.py module.

Tests deny rule management and settings file manipulation.
"""

import json
from pathlib import Path
from unittest.mock import patch

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-credentials', 'credentials.py')


class TestEnsureDeniedRules:
    """Tests for deny rule content."""

    def test_deny_rules_cover_both_path_forms(self):
        """Deny rules must include both ~ and absolute path forms."""
        from _cred_ensure_denied import DENY_RULES  # type: ignore[import-not-found]

        tilde_rules = [r for r in DENY_RULES if '~/' in r]
        abs_rules = [r for r in DENY_RULES if str(Path.home()) in r]
        assert len(tilde_rules) > 0, 'Must have tilde-form rules'
        assert len(abs_rules) > 0, 'Must have absolute-path-form rules'

    def test_deny_rules_cover_read_tool(self):
        """Deny rules must cover Read tool access."""
        from _cred_ensure_denied import DENY_RULES  # type: ignore[import-not-found]

        read_rules = [r for r in DENY_RULES if r.startswith('Read(')]
        assert len(read_rules) >= 2, 'Must have Read() deny rules (tilde + abs)'

    def test_deny_rules_cover_common_bash_commands(self):
        """Deny rules must cover cat, head, tail, etc."""
        from _cred_ensure_denied import DENY_RULES  # type: ignore[import-not-found]

        bash_commands = ['cat', 'head', 'tail', 'less', 'more', 'cp', 'grep', 'base64']
        for cmd in bash_commands:
            matching = [r for r in DENY_RULES if f'Bash({cmd} ' in r]
            assert len(matching) >= 1, f'Missing deny rule for Bash({cmd})'


class TestEnsureDeniedCLI:
    """Tests for ensure-denied subcommand."""

    def test_ensure_denied_adds_rules(self, tmp_path):
        """ensure-denied adds deny rules to settings file."""
        settings_file = tmp_path / '.claude' / 'settings.json'
        settings_file.parent.mkdir(parents=True)
        settings_data = {'permissions': {'allow': [], 'deny': [], 'ask': []}}
        settings_file.write_text(json.dumps(settings_data))

        with patch('permission_common.get_settings_path', return_value=settings_file):
            with patch('permission_common.load_settings_path', return_value=dict(settings_data)):
                with patch('permission_common.save_settings') as mock_save:
                    from argparse import Namespace

                    from _cred_ensure_denied import run_ensure_denied  # type: ignore[import-not-found]

                    result = run_ensure_denied(Namespace(target='project'))
                    assert result == 0
                    assert mock_save.called

    def test_ensure_denied_idempotent(self, tmp_path):
        """Running ensure-denied twice doesn't duplicate rules."""
        from _cred_ensure_denied import DENY_RULES  # type: ignore[import-not-found]

        settings = {'permissions': {'allow': [], 'deny': list(DENY_RULES), 'ask': []}}

        with patch('permission_common.get_settings_path', return_value=tmp_path / 'settings.json'):
            with patch('permission_common.load_settings_path', return_value=settings):
                with patch('permission_common.save_settings'):
                    from argparse import Namespace

                    from _cred_ensure_denied import run_ensure_denied  # type: ignore[import-not-found]

                    run_ensure_denied(Namespace(target='project'))
                    assert len(settings['permissions']['deny']) == len(DENY_RULES)
