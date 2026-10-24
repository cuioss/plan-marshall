#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Which copy of a staged spec ``resolve`` reads, and what it says about it.

With ``orchestrator.use_worktree`` on, every spec edit lives only in the shared
ledger worktree until a ledger land, so a lane that always reads the main
checkout can run a spec other than the one the orchestrator reports. ``resolve``
therefore takes ``--spec-from-ledger``: read the ledger worktree's copy first,
fall back to the main checkout's. The default is unchanged.

The two copies carry DIFFERENT deliverable titles in these fixtures, so an
assertion on the parsed output proves which BODY was read, not merely which path
was echoed back.

Every fixture keeps its state inside its own ``tmp_path``: ``PLAN_BASE_DIR``
anchors the main-checkout seam on the fixture's ``.plan`` (so the ledger worktree
resolves to ``{fixture}/.plan/worktrees/_orchestrator``) and ``PLAN_MARSHALL_HOME``
isolates the machine-global tier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conftest import get_scripts_dir, run_script

_SKILL_NAME = 'runbook-lane'
_SCRIPT = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'

SLUG = 'demo-epic'
SPEC_NAME = 'PLAN-LB-90-lane-reads-ledger-spec.md'
SPEC_REL = f'.plan/orchestrator/{SLUG}/plans/{SPEC_NAME}'

MAIN_TITLE = 'Main checkout deliverable'
LEDGER_TITLE = 'Ledger worktree deliverable'


def _spec_body(title: str) -> str:
    """A minimal staged spec whose ONLY observable content is its deliverable title."""
    return f'# staged spec\n\n## Deliverables\n\n1. **{title}**\n'


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _seed_project(root: Path, *, use_worktree: bool) -> None:
    """Seed the project surface ``resolve`` reads: the config and the architecture."""
    _write(
        root / '.plan' / 'marshal.json',
        json.dumps(
            {
                'orchestrator': {'use_worktree': use_worktree},
                'plan': {
                    'phase-6-finalize': {'steps': {'plan-marshall:automatic-review': {'required_bots': 'some-bot'}}}
                },
            }
        ),
    )
    architecture = root / '.plan' / 'project-architecture'
    _write(
        architecture / '_project.json',
        json.dumps({'name': 'test-project', 'modules': {'root-mod': {}, 'documentation': {}}}),
    )
    _write(
        architecture / 'root-mod' / 'derived.json',
        json.dumps(
            {
                'name': 'root-mod',
                'build_systems': ['pyproject'],
                'paths': {'module': '.'},
                'commands': {
                    'quality-gate': 'python3 .plan/execute-script.py build run --command-args "quality-gate"',
                    'module-tests': 'python3 .plan/execute-script.py build run --command-args "module-tests"',
                    'verify': 'python3 .plan/execute-script.py build run --command-args "verify"',
                },
            }
        ),
    )
    _write(
        architecture / 'documentation' / 'derived.json',
        json.dumps(
            {
                'name': 'documentation',
                'build_systems': ['documentation'],
                'paths': {'module': 'doc'},
                'files': {'doc': ['doc/usage.md']},
            }
        ),
    )


def _main_spec(root: Path) -> Path:
    return root / SPEC_REL


def _ledger_spec(root: Path) -> Path:
    """The ledger worktree's copy, at the path the store seam computes for the fixture.

    ``PLAN_BASE_DIR`` stands in for the main checkout's ``.plan/local``, so the
    worktree lands at ``{fixture}/.plan/worktrees/_orchestrator`` and its store at
    ``{worktree}/.plan``.
    """
    return root / '.plan' / 'worktrees' / '_orchestrator' / SPEC_REL


def _seed_copies(
    root: Path,
    *,
    use_worktree: bool,
    main_body: str | None,
    ledger_body: str | None,
) -> None:
    _seed_project(root, use_worktree=use_worktree)
    if main_body is not None:
        _write(_main_spec(root), main_body)
    if ledger_body is not None:
        _write(_ledger_spec(root), ledger_body)


def _env(root: Path) -> dict[str, str]:
    return {
        'PLAN_BASE_DIR': str(root / '.plan'),
        'PLAN_MARSHALL_HOME': str(root / '.machine-home'),
    }


def _run_resolve(root: Path, spec: str, *, from_ledger: bool = False) -> dict[str, Any]:
    """Invoke ``resolve`` through its real CLI, so a renamed flag is a red test."""
    argv = ['resolve', '--spec', spec, '--project-dir', str(root)]
    if from_ledger:
        argv.append('--spec-from-ledger')
    result = run_script(_SCRIPT, *argv, env_overrides=_env(root))
    assert result.success, f'resolve crashed: {result.stderr}'
    data: dict[str, Any] = result.toon()
    return data


def _titles(data: dict[str, Any]) -> list[str]:
    return [row['title'] for row in data['deliverables']]


# =============================================================================
# D1 — the parameter, and which copy it reads
# =============================================================================


def test_default_reads_the_main_checkout_copy(tmp_path: Path) -> None:
    """With the flag absent the lane reads the main checkout, exactly as before."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]


def test_spec_from_ledger_reads_the_worktree_copy(tmp_path: Path) -> None:
    """The flag reads the ledger worktree's body, not the main checkout's."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]
    assert data['spec'] == _ledger_spec(tmp_path).as_posix()


def test_spec_only_in_the_ledger_is_read_under_the_flag_and_refused_by_default(tmp_path: Path) -> None:
    """A worktree-only spec is exactly the case the flag exists for."""
    _seed_copies(tmp_path, use_worktree=True, main_body=None, ledger_body=_spec_body(LEDGER_TITLE))

    refused = _run_resolve(tmp_path, SPEC_REL)
    assert refused['status'] == 'error'
    assert refused['error'] == 'invalid_spec'

    data = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)
    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]


def test_the_ledger_copy_is_readable_by_its_own_absolute_path(tmp_path: Path) -> None:
    """A worktree path refused by default is readable under the flag."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    refused = _run_resolve(tmp_path, str(_ledger_spec(tmp_path)))
    assert refused['status'] == 'error'
    assert refused['error'] == 'spec_outside_orchestrator'

    data = _run_resolve(tmp_path, str(_ledger_spec(tmp_path)), from_ledger=True)
    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]


def test_flag_is_a_no_op_with_use_worktree_off(tmp_path: Path) -> None:
    """With no ledger worktree there is one copy, and the flag is not an error."""
    _seed_copies(tmp_path, use_worktree=False, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]
