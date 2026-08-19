#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage change ledger`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import get_script_path

_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'tracked.txt').write_text('original\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


def _run(env, *args: str):
    """Invoke the ledger CLI in the repo cwd with the isolated PLAN_BASE_DIR."""
    from conftest import run_script

    return run_script(
        _SCRIPT,
        *args,
        cwd=str(env.repo),
        env_overrides=env.overrides,
    )


def _read_ledger(ledger_path: Path) -> list[dict]:
    """Parse the on-disk JSONL ledger into a list of dicts."""
    return [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
