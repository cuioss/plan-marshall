#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage change ledger`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Unit tests for the unified ``manage-change-ledger`` CLI — the first-class
``worktree-sha`` + ``append`` + ``query`` API over the one append-only
change-ledger.

The script is the executor-callable surface; tests drive it through its real
entry point with :func:`conftest.run_script` so the argparse wiring, the TOON
output contract, and the deterministic ``_ledger_core`` read/write/construct
path are all exercised end-to-end. Every invocation runs inside a REAL
``git init`` repo staged under a unique ``tmp_path`` (so the shared
``compute_worktree_sha`` helper resolves a HEAD) and routes the ledger file under
an isolated ``PLAN_BASE_DIR`` (so ``get_tracked_config_dir`` resolves the
fixture, never the real ``.plan/`` tree).

Coverage:

* ``append --kind build`` — stamps ``kind``/``worktree_sha``/``timestamp_iso``
  plus the build fields (including the truthful ``status`` outcome —
  ``success`` / ``error`` / ``timeout`` / ``killed``) and appends one JSONL
  line;
* the three wrapper-reported ``kind=build`` fields — ``command``,
  ``duration_seconds`` and ``outcome`` — asserted on ``build_record`` TOGETHER
  with the unchanged ``args``, so the executor-argv layer and the
  wrapper-resolved-command layer stay distinguishable; plus the payload-less
  default (all three ``None``) and the CLI second-writer row that exercises it;
* ``append --kind change`` — stamps the change fields, storing
  ``commit_sha``/``changed_paths`` verbatim;
* the never-null ``plan_id`` contract, asserted AT THE VERB for both
  ``--kind build`` and ``--kind job``: an omitted ``--plan-id`` is recorded as
  the ``NO_PLAN`` sentinel, a supplied one is stored verbatim, and the
  ``_ledger_core`` constructors declare ``plan_id: str`` with the ``| None``
  union removed;
* ``query`` — round-trips both entries; ``--kind`` filters; an empty ledger
  yields ``count: 0``;
* worktree_sha currency — the stored hash matches the ``worktree-sha`` verb's
  output for the same tree; a pre-computed ``--worktree-sha`` is honoured;
* TOON output shape — ``status``/``kind``/``worktree_sha``/``ledger_path`` keys
  on append, ``status``/``count``/``ledger_path`` on query;
* error paths — missing ``--notation``/``--exit-code``/``--status`` (build),
  missing ``--commit-sha`` / deliverable id (change), an unknown ``--status``
  value (argparse choices rejection), and ``worktree-sha`` in a non-git
  directory (``head_unresolvable``).
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
