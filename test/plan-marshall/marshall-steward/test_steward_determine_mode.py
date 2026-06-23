#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the marshall-steward worktree refuse-or-scaffold guard.

``determine_mode.py`` exposes ``check_worktree_plan_local(repo_root, scaffold)``
and a ``check-worktree-plan-local`` subcommand that prevent a worktree
executor-gen from contaminating the main checkout's
``.plan/execute-script.py``. Before ``generate_executor --marketplace-root
<REPO_ROOT>`` runs from a worktree, the worktree MUST own its own
``.plan/local`` — otherwise generation climbs to main's ``.plan/local``.

This suite pins that contract:

- a worktree that already owns ``.plan/local`` proceeds (``ok``)
- a worktree lacking ``.plan/local`` refuses (``refuse``) without ``--scaffold``
- a worktree lacking ``.plan/local`` is scaffolded (``scaffolded``) with ``--scaffold``
- the main checkout (no ``worktrees`` path segment) is always a no-op (``ok``)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT  # type: ignore[import-not-found]

_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts'
)
_DETERMINE_MODE = _SCRIPTS_DIR / 'determine_mode.py'

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_dm = _load_module('_marshall_steward_determine_mode_guard', _DETERMINE_MODE)
check_worktree_plan_local = _dm.check_worktree_plan_local
is_worktree_repo_root = _dm.is_worktree_repo_root
discover_shipped_project_finalize_steps = _dm.discover_shipped_project_finalize_steps
detect_missing_project_finalize_steps = _dm.detect_missing_project_finalize_steps


def _make_worktree_root(tmp_path: Path) -> Path:
    """Build a path whose realised string contains ``/.plan/local/worktrees/``.

    The guard's worktree detection is purely path-based: the resolved
    repo-top-level path must carry the ``.plan/local/worktrees/`` segment.
    """
    root = tmp_path / 'main' / '.plan' / 'local' / 'worktrees' / 'my-plan'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_main_root(tmp_path: Path) -> Path:
    root = tmp_path / 'main-checkout'
    root.mkdir(parents=True, exist_ok=True)
    return root


# --- is_worktree_repo_root -------------------------------------------------


def test_is_worktree_repo_root_true_for_worktree_path(tmp_path: Path):
    """A path under ``.plan/local/worktrees/`` is recognised as a worktree."""
    root = _make_worktree_root(tmp_path)
    assert is_worktree_repo_root(root) is True


def test_is_worktree_repo_root_false_for_main_checkout(tmp_path: Path):
    """A path without the worktrees segment is the main checkout."""
    root = _make_main_root(tmp_path)
    assert is_worktree_repo_root(root) is False


# --- check_worktree_plan_local: function-level -----------------------------


def test_main_checkout_is_always_ok(tmp_path: Path):
    """The guard governs worktree generation only — main checkout is a no-op."""
    root = _make_main_root(tmp_path)
    # No .plan/local on the main checkout root; the guard must still return ok.
    status, plan_local = check_worktree_plan_local(root, scaffold=False)
    assert status == 'ok'
    assert plan_local == root / '.plan' / 'local'


def test_worktree_with_plan_local_proceeds(tmp_path: Path):
    """A worktree that already owns .plan/local proceeds (ok)."""
    root = _make_worktree_root(tmp_path)
    (root / '.plan' / 'local').mkdir(parents=True, exist_ok=True)

    status, plan_local = check_worktree_plan_local(root, scaffold=False)
    assert status == 'ok'
    assert plan_local.is_dir()


def test_worktree_without_plan_local_refuses(tmp_path: Path):
    """A worktree lacking .plan/local refuses when --scaffold is not given."""
    root = _make_worktree_root(tmp_path)
    assert not (root / '.plan' / 'local').exists()

    status, plan_local = check_worktree_plan_local(root, scaffold=False)
    assert status == 'refuse'
    # The guard did NOT create the directory.
    assert not plan_local.exists()


def test_worktree_without_plan_local_scaffolds(tmp_path: Path):
    """A worktree lacking .plan/local is scaffolded when --scaffold is given."""
    root = _make_worktree_root(tmp_path)
    assert not (root / '.plan' / 'local').exists()

    status, plan_local = check_worktree_plan_local(root, scaffold=True)
    assert status == 'scaffolded'
    assert plan_local.is_dir()


# --- check-worktree-plan-local: CLI / subcommand ---------------------------


def _run_cli(repo_root: Path, *extra: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(_DETERMINE_MODE), 'check-worktree-plan-local',
         '--repo-root', str(repo_root), *extra],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_cli_refuse_on_worktree_without_plan_local(tmp_path: Path):
    """CLI emits status: refuse and a detail message when generation is unsafe."""
    root = _make_worktree_root(tmp_path)
    out = _run_cli(root)
    assert 'status: refuse' in out
    assert 'is_worktree: true' in out
    assert 'detail:' in out
    assert not (root / '.plan' / 'local').exists()


def test_cli_scaffold_creates_plan_local(tmp_path: Path):
    """CLI --scaffold creates .plan/local and emits status: scaffolded."""
    root = _make_worktree_root(tmp_path)
    out = _run_cli(root, '--scaffold')
    assert 'status: scaffolded' in out
    assert (root / '.plan' / 'local').is_dir()


def test_cli_ok_on_main_checkout(tmp_path: Path):
    """CLI is a no-op on the main checkout (status: ok, is_worktree: false)."""
    root = _make_main_root(tmp_path)
    out = _run_cli(root)
    assert 'status: ok' in out
    assert 'is_worktree: false' in out


# =============================================================================
# check-missing-finalize-steps: project: step detection (D10)
# =============================================================================
#
# determine_mode.py's check-missing-finalize-steps now ALSO detects shipped
# project: finalize steps absent from phase-6-finalize.steps. A project: step is
# "shipped" when <project_root>/.claude/skills/finalize-step-<name>/SKILL.md
# exists; its notation is project:finalize-step-<name>. The detection surfaces
# the meta-project drift where a steward re-run would silently drop a
# hand-maintained project-local step.

_PROJECT_STEPS = (
    'pre-submission-self-review',
    'plugin-doctor',
    'deploy-target',
    'sync-plugin-cache',
)


def _ship_project_finalize_skills(project_root: Path, names) -> None:
    """Create `.claude/skills/finalize-step-<name>/SKILL.md` for each name."""
    for name in names:
        skill_dir = project_root / '.claude' / 'skills' / f'finalize-step-{name}'
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / 'SKILL.md').write_text(f'# finalize-step-{name}\n', encoding='utf-8')


def _write_finalize_steps_marshal(plan_dir: Path, steps: list[str]) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    marshal = {'plan': {'phase-6-finalize': {'steps': steps}}}
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def test_discover_shipped_project_finalize_steps_enumerates_skills(tmp_path: Path):
    """Each finalize-step-<name>/SKILL.md maps to project:finalize-step-<name>."""
    project_root = tmp_path / 'repo'
    project_root.mkdir()
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)

    shipped = discover_shipped_project_finalize_steps(project_root)

    assert shipped == sorted(f'project:finalize-step-{n}' for n in _PROJECT_STEPS)


def test_discover_shipped_returns_empty_without_claude_skills(tmp_path: Path):
    """A consumer project lacking .claude/skills/ ships no project: steps."""
    project_root = tmp_path / 'consumer'
    project_root.mkdir()
    assert discover_shipped_project_finalize_steps(project_root) == []


def test_discover_skips_finalize_dirs_without_skill_md(tmp_path: Path):
    """A finalize-step dir lacking SKILL.md is not a shipped step."""
    project_root = tmp_path / 'repo'
    (project_root / '.claude' / 'skills' / 'finalize-step-empty').mkdir(parents=True)
    assert discover_shipped_project_finalize_steps(project_root) == []


def test_all_project_steps_present_reports_clean(tmp_path: Path):
    """When every shipped project: step is in the array, nothing is missing."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    steps = [f'project:finalize-step-{n}' for n in _PROJECT_STEPS] + ['default:push']
    _write_finalize_steps_marshal(plan_dir, steps)

    missing = detect_missing_project_finalize_steps(plan_dir, project_root)
    assert missing == []


def test_dropped_project_step_is_reported(tmp_path: Path):
    """When a shipped project: step is absent from the array, it is reported."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    # Drop plugin-doctor + deploy-target from the configured steps.
    steps = [
        'project:finalize-step-pre-submission-self-review',
        'project:finalize-step-sync-plugin-cache',
        'default:push',
    ]
    _write_finalize_steps_marshal(plan_dir, steps)

    missing = detect_missing_project_finalize_steps(plan_dir, project_root)
    assert sorted(missing) == [
        'project:finalize-step-deploy-target',
        'project:finalize-step-plugin-doctor',
    ]


def test_missing_marshal_yields_empty_project_missing(tmp_path: Path):
    """No marshal.json → nothing to compare → empty (graceful)."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    plan_dir.mkdir(parents=True)
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    assert detect_missing_project_finalize_steps(plan_dir, project_root) == []


def _run_finalize_cli(plan_dir: Path, project_root: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(_DETERMINE_MODE), 'check-missing-finalize-steps',
         '--plan-dir', str(plan_dir), '--project-root', str(project_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_cli_reports_missing_project_steps(tmp_path: Path):
    """CLI emits status: missing + missing_project_finalize_steps for dropped steps."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    _write_finalize_steps_marshal(plan_dir, ['default:push'])

    out = _run_finalize_cli(plan_dir, project_root)
    assert 'status: missing' in out
    assert 'missing_project_finalize_steps:' in out
    assert 'project:finalize-step-plugin-doctor' in out


def test_cli_reports_ok_when_all_project_steps_present(tmp_path: Path):
    """CLI emits status: ok when every shipped project: step is configured."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    # Include every shipped project: step plus all built-in defaults so neither
    # detection set fires.
    from conftest import MARKETPLACE_ROOT as _MR  # type: ignore[import-not-found]
    _config_scripts = _MR / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
    if str(_config_scripts) not in sys.path:
        sys.path.insert(0, str(_config_scripts))
    from _config_defaults import BUILT_IN_FINALIZE_STEPS  # type: ignore[import-not-found]

    steps = list(BUILT_IN_FINALIZE_STEPS) + [
        f'project:finalize-step-{n}' for n in _PROJECT_STEPS
    ]
    _write_finalize_steps_marshal(plan_dir, steps)

    out = _run_finalize_cli(plan_dir, project_root)
    assert 'status: ok' in out
