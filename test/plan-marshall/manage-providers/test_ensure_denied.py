#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _cred_ensure_denied.py module.

Tests deny rule management and settings file manipulation.
"""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')


@pytest.fixture
def real_home_deny_rules(monkeypatch):
    """Rebuild ``_cred_ensure_denied.DENY_RULES`` against the REAL home path.

    The absolute-form rules derive from ``_providers_core.CREDENTIALS_DIR``,
    which the autouse ``_credentials_dir_sandbox`` redirects to a tmp dir for
    every test. These deny rules exist to protect the REAL
    ``~/.plan-marshall/credentials``, so pin ``CREDENTIALS_DIR`` back to the
    real home path and reload the module (no write — ``DENY_RULES`` is pure
    strings) before yielding the rebuilt list, then revert in teardown so the
    module-level reload never leaks into subsequent tests.
    """
    import _cred_ensure_denied
    import _providers_core

    sandboxed_dir = _providers_core.CREDENTIALS_DIR
    real_dir = Path.home() / '.plan-marshall' / 'credentials'
    monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', real_dir)
    importlib.reload(_cred_ensure_denied)
    try:
        yield _cred_ensure_denied.DENY_RULES
    finally:
        monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', sandboxed_dir)
        importlib.reload(_cred_ensure_denied)


class TestEnsureDeniedRules:
    """Tests for deny rule content."""

    def test_deny_rules_cover_both_path_forms(self, real_home_deny_rules):
        """Deny rules must include both ~ and absolute path forms."""
        tilde_rules = [r for r in real_home_deny_rules if '~/' in r]
        abs_rules = [r for r in real_home_deny_rules if str(Path.home()) in r]
        assert len(tilde_rules) > 0, 'Must have tilde-form rules'
        assert len(abs_rules) > 0, 'Must have absolute-path-form rules'

    def test_deny_rules_cover_read_tool(self):
        """Deny rules must cover Read tool access."""
        from _cred_ensure_denied import DENY_RULES

        read_rules = [r for r in DENY_RULES if r.startswith('Read(')]
        assert len(read_rules) >= 2, 'Must have Read() deny rules (tilde + abs)'

    def test_deny_rules_cover_common_bash_commands(self):
        """Deny rules must cover cat, head, tail, etc."""
        from _cred_ensure_denied import DENY_RULES

        bash_commands = ['cat', 'head', 'tail', 'less', 'more', 'cp', 'grep', 'base64']
        for cmd in bash_commands:
            matching = [r for r in DENY_RULES if f'Bash({cmd} ' in r]
            assert len(matching) >= 1, f'Missing deny rule for Bash({cmd})'

    def test_no_rule_names_the_retired_old_path(self, real_home_deny_rules):
        """No deny rule may name the retired ``~/.plan-marshall-credentials`` path.

        Every rule must name the NEW ``.plan-marshall/credentials`` surface and
        none may name the retired ``.plan-marshall-credentials`` basename.
        """
        for rule in real_home_deny_rules:
            assert '.plan-marshall-credentials' not in rule, f'Retired path in rule: {rule}'
        # The new distinctive path segment IS present (python3 -c substring vector).
        assert any('.plan-marshall/credentials' in r for r in real_home_deny_rules)


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

                    from _cred_ensure_denied import run_ensure_denied

                    result = run_ensure_denied(Namespace(target='project'))
                    assert result == 0
                    assert mock_save.called

    def test_ensure_denied_idempotent(self, tmp_path):
        """Running ensure-denied twice doesn't duplicate rules."""
        from _cred_ensure_denied import DENY_RULES

        settings = {'permissions': {'allow': [], 'deny': list(DENY_RULES), 'ask': []}}

        with patch('permission_common.get_settings_path', return_value=tmp_path / 'settings.json'):
            with patch('permission_common.load_settings_path', return_value=settings):
                with patch('permission_common.save_settings'):
                    from argparse import Namespace

                    from _cred_ensure_denied import run_ensure_denied

                    run_ensure_denied(Namespace(target='project'))
                    assert len(settings['permissions']['deny']) == len(DENY_RULES)
