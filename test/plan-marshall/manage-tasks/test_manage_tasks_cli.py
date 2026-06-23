#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py CLI plumbing (subprocess Tier-3 tests).

Split from test_manage_tasks.py: covers --help, missing subcommand, legacy
add removal, and the prepare-add → commit-add CLI roundtrip.
"""

from pathlib import Path

from _helpers import SCRIPT_PATH
from conftest import run_script


def test_cli_missing_subcommand_exits_2():
    """Missing subcommand exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 2


def test_cli_help_exits_0():
    """--help exits with code 0."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.returncode == 0
    assert 'manage implementation tasks' in result.stdout.lower()


def test_cli_legacy_add_subcommand_removed():
    """The legacy `add` subcommand has been removed (argparse error)."""
    result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan')
    assert result.returncode == 2


def test_cli_prepare_add_then_commit_add_roundtrip(plan_context):
    """End-to-end CLI: prepare-add → write TOON → commit-add creates TASK-001."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    prep = run_script(
        SCRIPT_PATH,
        'prepare-add',
        '--plan-id',
        'cli-add-roundtrip',
    )
    assert prep.success, f'prepare-add failed: {prep.stderr}'
    prep_data = parse_toon(prep.stdout)
    assert prep_data['status'] == 'success'
    scratch_path = Path(prep_data['path'])

    scratch_path.parent.mkdir(parents=True, exist_ok=True)
    scratch_path.write_text(
        'title: CLI Roundtrip\n'
        'deliverable: 1\n'
        'domain: java\n'
        'description: Roundtrip test\n'
        'steps:\n'
        '  - src/main/java/X.java (write-new)\n'
        'depends_on: none\n',
        encoding='utf-8',
    )

    commit = run_script(
        SCRIPT_PATH,
        'commit-add',
        '--plan-id',
        'cli-add-roundtrip',
    )
    assert commit.success, f'commit-add failed: {commit.stderr}'
    commit_data = parse_toon(commit.stdout)
    assert commit_data['status'] == 'success'
    assert commit_data['file'] == 'TASK-001.json'
    assert not scratch_path.exists()


def test_cli_commit_add_without_prepare_fails(plan_context):
    """commit-add without a prior prepare-add returns an error."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    result = run_script(
        SCRIPT_PATH,
        'commit-add',
        '--plan-id',
        'cli-add-missing',
    )
    data = parse_toon(result.stdout) if result.stdout else {}
    assert not result.success or data.get('status') == 'error'
