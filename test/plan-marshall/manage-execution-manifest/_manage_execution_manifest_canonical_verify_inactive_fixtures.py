#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the canonical-verify footprint pre-filter (inactive case).

``_apply_canonical_verify_inactive`` is the generic, canonical-agnostic
footprint pre-filter: it drops a composed phase-5 ``default:verify:{canonical}``
step when its derived role is a footprint-gated role (``integration`` / ``e2e``)
AND the live, non-empty footprint carries no path of that role. The gate is
driven entirely by the ``_CANONICAL_TO_ROLE`` derivation and the
``_FOOTPRINT_GATED_CANONICAL_ROLES`` membership table — there is no per-canonical
branch in the code path.

Safety against no-evidence footprints: BOTH an UNRESOLVABLE footprint (``None``
— the normal case during early compose at phase-4-plan, before the worktree is
materialised) and a resolvable-but-EMPTY footprint (``[]``) make the pre-filter a
no-op, so every canonical survives. The gate only fires against a NON-empty
footprint that genuinely lacks the gating role's paths — the one state that is
real evidence the role has no paths.

The two no-op states reach the same outcome here but for different reasons, and
the distinction is load-bearing rather than cosmetic: ``[]`` is a substantiated
"nothing changed", while ``None`` is "we could not look". This pre-filter treats
both as no evidence and subtracts nothing, which is why an unresolvable footprint
must not be silently normalised to ``[]`` on the way in — a consumer that DOES
distinguish them (the build verdict) would then read a positive answer off a
state nobody observed.

These tests drive ``_apply_canonical_verify_inactive`` directly with a
monkeypatched ``_resolve_footprint`` so the prefilter logic is exercised
deterministically without a live worktree or git history. ``_footprint_has_role``
is also covered directly.

Green-report binding pins (D2 hardening): ``summarize_refires`` proves the
verdict-artifact population — ``skipped`` rows never fold into firings, so a
canonical that never executed cannot authorise green — and the refire
arithmetic the triage-iteration bound consumes. The uncommitted-work half is
pinned through ``post_run_source_guard check --fail-on-dirty`` on a hermetic
tmp git repository: a dirty tree blocks (non-zero exit) while the default
stays advisory.
"""

# Tier 2 direct imports, resolved by (bundle, skill, script).

import subprocess
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_canonical_inactive'
)
_apply_canonical_verify_inactive = _mem._apply_canonical_verify_inactive
_footprint_has_role = _mem._footprint_has_role
_FOOTPRINT_GATED_CANONICAL_ROLES = _mem._FOOTPRINT_GATED_CANONICAL_ROLES
_summarize_refires = _mem.summarize_refires

_guard_script = get_script_path('plan-marshall', 'phase-6-finalize', 'post_run_source_guard.py')


_PLAN_ID = 'canonical-inactive'


def _patch_footprint(monkeypatch, footprint: list[str] | None) -> None:
    """Force ``_resolve_footprint`` to return ``footprint`` for any plan id.

    ``footprint`` is the resolver's three-state return verbatim: ``None``
    (unresolvable), ``[]`` (resolvable and genuinely empty), or a path list.
    ``None`` is deliberately not collapsed into ``[]`` — the pre-filter must be
    handed the real state so its handling of each can be asserted separately.
    """
    monkeypatch.setattr(
        _mem,
        '_resolve_footprint',
        lambda plan_id: None if footprint is None else list(footprint),
    )


def _execution_row(step_id: str, outcome: str) -> dict:
    """One ``execution_log[]`` row in the shape ``record-step`` appends.

    Token columns carry the unmeasured token — the writer's output when the
    caller passes no measurement — so the firing derivation is exercised on
    the inline-build shape, not on a measured population.
    """
    return {
        'step_id': step_id,
        'phase': '5-execute',
        'outcome': outcome,
        'total_tokens': 'unmeasured',
        'tool_uses': 'unmeasured',
        'duration_ms': 'unmeasured',
    }


def _entry_for(steps: list[dict], step_id: str) -> dict:
    """The single per-step entry for ``step_id`` — the derivation emits one."""
    matches = [entry for entry in steps if entry['step_id'] == step_id]
    assert len(matches) == 1
    return matches[0]


def _git(repo: Path, *args: str) -> None:
    """Run one git command against ``repo`` with a pinned, hermetic identity.

    Identity and signing travel per-invocation so the fixture behaves
    identically on a developer machine with a global gitconfig and on a bare
    CI runner with none.
    """
    subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


@pytest.fixture
def dirty_repo(tmp_path: Path) -> Path:
    """A real git repository with one committed tracked file, then dirtied.

    The worktree starts with exactly one dirty tracked path, so the guard's
    verdict population is fully determined by this fixture.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    target = repo / 'src' / 'tracked.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('print("seed")\n', encoding='utf-8')
    _git(repo, 'add', 'src/tracked.py')
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    target.write_text('print("dirty")\n', encoding='utf-8')
    return repo


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    """A real git repository with one committed tracked file and no dirt."""
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    target = repo / 'src' / 'tracked.py'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('print("seed")\n', encoding='utf-8')
    _git(repo, 'add', 'src/tracked.py')
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo
