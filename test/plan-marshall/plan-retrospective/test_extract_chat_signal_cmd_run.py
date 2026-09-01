# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI contract tests for the ``extract-chat-signal.py`` consumer.

The consumer's surface is ``run --session-id X [--read-budget-bytes N]``.
These tests pin the parser contract — required ``--session-id``, the integer
byte budget with its 2 MiB default, ``allow_abbrev=False``, and the required
``run`` subcommand — driven through the script's own parser via ``parse_ns``
and ``run_script``.
"""

from __future__ import annotations

import pytest
from _extract_chat_signal_fixtures import _mod

from conftest import (
    MARKETPLACE_ROOT,
    parse_ns,
    run_script,
)  # noqa: E402

BUNDLE = 'plan-marshall'
SKILL = 'plan-retrospective'
SCRIPT = 'extract-chat-signal.py'
SCRIPT_PATH = MARKETPLACE_ROOT / BUNDLE / 'skills' / SKILL / 'scripts' / SCRIPT

SESSION_ID = '22222222-2222-2222-2222-222222222201'


class TestParser:
    def test_session_id_is_required(self):
        from _extract_chat_signal_fixtures import SESSION_ID as _sid

        args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--session-id', _sid)
        assert args.session_id == _sid

    def test_missing_session_id_rejected(self):
        with pytest.raises(SystemExit):
            parse_ns(BUNDLE, SKILL, SCRIPT, 'run')

    def test_default_read_budget_is_set(self):
        args = parse_ns(BUNDLE, SKILL, SCRIPT, 'run', '--session-id', SESSION_ID)
        assert args.read_budget_bytes == _mod.DEFAULT_READ_BUDGET_BYTES

    def test_read_budget_override(self):
        args = parse_ns(
            BUNDLE,
            SKILL,
            SCRIPT,
            'run',
            '--session-id',
            SESSION_ID,
            '--read-budget-bytes',
            '5000',
        )
        assert args.read_budget_bytes == 5000

    def test_non_integer_read_budget_rejected(self):
        with pytest.raises(SystemExit):
            parse_ns(
                BUNDLE,
                SKILL,
                SCRIPT,
                'run',
                '--session-id',
                SESSION_ID,
                '--read-budget-bytes',
                '1.5',
            )

    def test_run_subcommand_is_required(self):
        with pytest.raises(SystemExit):
            parse_ns(BUNDLE, SKILL, SCRIPT)


class TestCliSurface:
    def test_flag_abbreviations_are_rejected(self, tmp_path):
        """``allow_abbrev=False`` is a script-architecture requirement.

        Accepting ``--session`` widens the CLI to a prefix the contract does
        not publish. Driven through the real CLI, because ``parse_ns``
        intercepts at the parse call and never exercises abbreviation.
        """
        full = run_script(SCRIPT_PATH, 'run', '--session-id', SESSION_ID)
        assert full.success, full.stderr

        abbreviated = run_script(SCRIPT_PATH, 'run', '--session', SESSION_ID)
        assert not abbreviated.success
        assert abbreviated.returncode != 0

    def test_missing_required_session_id_rejected(self):
        result = run_script(SCRIPT_PATH, 'run')
        assert not result.success
        assert result.returncode != 0

    def test_top_level_abbreviation_rejected(self):
        result = run_script(SCRIPT_PATH, '--hel')
        assert not result.success
        assert result.returncode != 0
