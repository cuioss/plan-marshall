#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""In-process ``main()`` dispatch tests for manage-lessons.py."""


import sys
import pytest
from conftest import load_script_module
from _manage_lessons_main_dispatch_fixtures import _mod


def test_restore_from_plan_help_names_every_restore_action(monkeypatch, capsys):
    """The published help must name every ``RESTORE_ACTIONS`` member.

    The subcommand help is where a CLI caller learns the closed ``action``
    vocabulary, and nothing else reads the help string and the frozenset
    together — so a value added to (or renamed in) ``RESTORE_ACTIONS`` without a
    matching help edit leaves the published contract stale and silently wrong.

    Population-derived: the expected members are read from the module rather
    than re-listed here, so the guard cannot pass by agreeing with a stale copy
    of the vocabulary.

    Scope, stated plainly: argparse renders a subcommand's ``help=`` string only
    in the PARENT parser's listing, so the assertion ranges over the whole
    rendered help rather than the ``restore-from-plan`` entry alone. Two members
    (``restore_incomplete``, ``plan_dir_unresolved``) are named nowhere else, so
    a dropped restore help string still fails here — but a member that another
    subcommand's help happens to mention would not be caught by this guard.
    """
    lessons_query = load_script_module(
        'plan-marshall', 'manage-lessons', '_lessons_query.py', '_dispatch_lessons_query'
    )
    actions = lessons_query.RESTORE_ACTIONS
    assert actions, 'RESTORE_ACTIONS is empty — the check below would be vacuous.'

    monkeypatch.setattr(sys, 'argv', ['manage-lessons.py', '--help'])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    assert exc.value.code == 0
    help_text = capsys.readouterr().out

    missing = sorted(action for action in actions if action not in help_text)
    assert not missing, (
        f'The manage-lessons help does not name {missing} from RESTORE_ACTIONS '
        f'({sorted(actions)}) — the restore-from-plan help string and the closed '
        f'vocabulary have drifted apart.'
    )
