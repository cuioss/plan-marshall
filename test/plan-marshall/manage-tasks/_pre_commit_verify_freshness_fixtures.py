#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``pre commit verify freshness`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

The subcommand answers a single deterministic question — "does the unified
change-ledger contain a ``kind=build`` entry with ``status == 'success'`` whose
``worktree_sha`` equals the CURRENT working-tree currency hash?" — and returns
one of three statuses (``fresh``, ``stale``, ``undecidable``) for the
orchestrator to consume as a fail-closed gate. Matching on ``status`` rather
than ``exit_code`` is load-bearing: the build wrapper exits 0 on timeout, so an
exit-code predicate would launder a build that never finished into a false
``fresh`` (regression covered in the sibling modules). See
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness" for the contract.

Before that question is asked at all, the gate consults the single build/no-build
authority (``extension_base.should_execute_build``, the ``manage-config
build-decision`` verb) COMMAND-FREE. A ``not_necessary`` verdict means no
``kind=build`` entry could ever legally exist for this footprint, so the gate
short-circuits to ``fresh`` carrying the verdict's OWN ``reason`` verbatim. The
gate derives no build-necessity signal of its own — it neither reads the
manifest's step shapes nor owns an exemption vocabulary. See ADR-004 §
"Amendment: ``build-decision`` is the sole build/no-build authority".

The freshness primitive is the change-ledger lookup, NOT a file-mtime heuristic.
Tests stub the three module-level boundary functions the command uses:

- ``compute_worktree_sha`` — the working-tree currency hash. Stubbed to a
  deterministic literal so the lookup match is exercised without standing up a
  real git worktree. Returning ``None`` exercises the ``head_unresolvable``
  fail-closed path.
- ``resolve_ledger_path`` — the tracked-config-dir ledger location. Stubbed to a
  temp JSONL file so the test controls the ledger entries directly.
- ``_build_necessity_verdict`` — the command-free consult of the sole authority.
  An autouse fixture pins it to ``build`` so every ledger-scan case reaches the
  scan; the build-necessity cases override it explicitly.

Together they make the gate's three-way decision (``fresh`` / ``stale`` /
``undecidable``) deterministic and isolated from git, the real ledger, and the
live project footprint.
"""


from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import _freshness_crosscheck as _crosscheck_mod
import pytest
from toon_parser import serialize_toon

from conftest import PROJECT_ROOT

# Load the cmd module via importlib (mirrors the qgate-mechanical test bootstrap).
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_freshness_mod = _load_module(
    '_cmd_pre_commit_verify_freshness_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)


cmd_pre_commit_verify_freshness = _freshness_mod.cmd_pre_commit_verify_freshness


# Captured BEFORE the autouse stub fixture can replace it: the cases that
# exercise the real consult (its call shape and its fail-closed except-branch)
# restore this, not whatever the fixture currently holds.
_REAL_BUILD_NECESSITY_VERDICT = _freshness_mod._build_necessity_verdict


# The current-sha literal the stubbed ``compute_worktree_sha`` returns. A
# ``kind=build`` entry whose ``worktree_sha`` matches this is a fresh build.
_CURRENT_SHA = 'a' * 64


_OTHER_SHA = 'b' * 64


# The notation set the pinned cross-check resolver reports for every case here.
# It holds each build notation this file's fixtures stamp, so the cross-check
# corroborates them and the cases exercise the gate's own logic rather than the
# cross-check's refusal branch (which has its own file).
_RESOLVED_NOTATIONS = frozenset(
    {
        'plan-marshall:build-pyproject:pyproject_build',
        'plan-marshall:build-maven:maven',
        'plan-marshall:build-npm:npm',
    }
)


# =============================================================================
# Fixture builders
# =============================================================================


def _write_status(plan_dir: Path, *, worktree_path: str = '') -> Path:
    """Write a minimal ``status.json`` for the plan.

    The gate no longer READS this file for its worktree root — that resolution
    moved behind ``file_ops.resolve_plan_context`` (stubbed at the single
    ``_query_worktree_path`` seam by each sibling module's autouse fixture). The file is
    still written so each case has a well-formed plan directory, and its
    ``metadata.worktree_path`` is deliberately left as a DECOY: nothing here may
    change the resolved root, which is exactly what
    ``test_worktree_root_ignores_status_metadata`` pins.
    """
    status = {
        'plan_id': plan_dir.name,
        'metadata': {'worktree_path': worktree_path},
    }
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps(status), encoding='utf-8')
    return status_path


def _build_entry(
    *,
    worktree_sha: str | None = _CURRENT_SHA,
    exit_code: int = 0,
    status: str | None = 'success',
    notation: str = 'plan-marshall:build-pyproject:pyproject_build',
    plan_id: str | None = 'freshness-test',
    timestamp_iso: str = '2026-06-11T12:00:00Z',
) -> dict:
    """Construct a ``kind=build`` ledger record dict.

    Mirrors the GATE-RELEVANT SUBSET of the shape produced by
    ``_ledger_core.build_record`` — deliberately not the whole record. The
    constructor also emits ``command``, ``duration_seconds`` and ``outcome``
    (the wrapper-reported fields), which this helper omits because the gate's
    PRIMARY predicate filters on ``kind``, ``status`` and ``worktree_sha`` only
    — never ``exit_code`` or ``plan_id``, and never any of those three. The
    extra fields are parameterised or omitted here to prove that tier/tool
    agnosticism, so a row that lacks them must still be gated identically.
    ``notation`` IS read, but only after the primary predicate has matched, by
    the cross-check that compares it against the architecture-resolved
    notations; it never widens or narrows the primary match itself.
    ``status=None`` omits the key entirely, modelling a pre-change row (which
    must fail closed to ``stale``).
    """
    entry = {
        'kind': 'build',
        'notation': notation,
        'plan_id': plan_id,
        'args': 'run',
        'exit_code': exit_code,
        'worktree_sha': worktree_sha,
        'log_file': None,
        'timestamp_iso': timestamp_iso,
    }
    if status is not None:
        entry['status'] = status
    return entry


def _change_entry(*, worktree_sha: str = _CURRENT_SHA) -> dict:
    """Construct a ``kind=change`` ledger record dict (must NOT satisfy the gate)."""
    return {
        'kind': 'change',
        'deliverable_id': 'D1',
        'commit_sha': 'c' * 40,
        'changed_paths': ['src.py'],
        'worktree_sha': worktree_sha,
        'timestamp_iso': '2026-06-11T11:00:00Z',
    }


def _write_ledger(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a JSONL change-ledger file with the given entries and return its path."""
    ledger_path = tmp_path / 'change-ledger.jsonl'
    lines = [json.dumps(entry, sort_keys=True) for entry in entries]
    ledger_path.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    return ledger_path


def _write_manifest(plan_dir: Path, *, verification_steps: list[str]) -> Path:
    """Write an ``execution.toon`` manifest whose ``phase_5.verification_steps`` is set.

    The manifest is NO LONGER an input to the freshness gate — it is written here
    only as a decoy, so the tests can prove the gate ignores it. The retired
    implementation read this file and inferred build necessity from the SHAPE of
    the step list (empty -> ``documentation_only``, all-``quality-gate`` ->
    ``lint_only``); the gate now consults the sole build/no-build authority
    instead, so neither shape may change its outcome.
    """
    manifest = {
        'manifest_version': 1,
        'plan_id': plan_dir.name,
        'phase_5': {
            'early_terminate': len(verification_steps) == 0,
            'verification_steps': verification_steps,
        },
        'phase_6': {'steps': []},
    }
    manifest_path = plan_dir / 'execution.toon'
    manifest_path.write_text(serialize_toon(manifest), encoding='utf-8')
    return manifest_path


def _stub_worktree_sha(monkeypatch, sha: str | None) -> None:
    """Patch ``compute_worktree_sha`` so no real git worktree is required."""
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda root: sha)


def _stub_ledger_path(monkeypatch, ledger_path: Path) -> None:
    """Patch ``resolve_ledger_path`` so the gate reads the test's temp ledger."""
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)


def _stub_expected_notations(monkeypatch, notations: frozenset[str]) -> None:
    """Patch the notation cross-check's resolver to a fixed, non-empty set.

    Patches ``_freshness_crosscheck.resolve_expected_notations`` — the seam the
    cross-check consults — rather than the cross-check itself, so the real
    corroborate/refute comparison still executes against a pinned expectation.
    """
    monkeypatch.setattr(
        _crosscheck_mod, 'resolve_expected_notations', lambda _project_dir: (notations, None)
    )


def _stub_verdict(monkeypatch, verdict: dict) -> None:
    """Patch the command-free build-necessity consult to a fixed verdict.

    The real consult resolves the LIVE project footprint via git, which would make
    every case here depend on the checkout's working state. Pinning the verdict
    isolates the gate's own logic — the branch it takes on each verdict — from the
    authority's internals, which are covered by the authority's own tests.
    """
    monkeypatch.setattr(_freshness_mod, '_build_necessity_verdict', lambda _plan_id: verdict)


# =============================================================================
# Resolver-migration contract
# =============================================================================
#
# The gate's worktree root used to come from a private ``_resolve_worktree_root``
# that hand-read ``status.metadata.worktree_path`` through a private
# ``_read_status_metadata``. Both are gone: the root now comes from the ONE
# resolver. The three cases pin the routing, the sentinel carve-out, and
# the deliberately-preserved non-fatal fallback.


def _capture_worktree_root(monkeypatch) -> list[Path]:
    """Capture the root the gate hands to ``compute_worktree_sha``."""
    seen: list[Path] = []

    def _record(root):
        seen.append(root)
        return _CURRENT_SHA

    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', _record)
    return seen


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Default every case to a ``build`` verdict so the ledger scan is reached.

    A ``build`` verdict is the pass-through: the gate falls straight to the ledger
    scan, which is what the bulk of this file exercises. Cases that exercise the
    short-circuit override this with an explicit ``_stub_verdict`` call.
    """
    _stub_verdict(monkeypatch, {'decision': 'build'})


@pytest.fixture(autouse=True)
def _expected_notations_resolve(monkeypatch):
    """Pin the notation cross-check's resolved set for every case in this file.

    The real resolver runs the live architecture crawl against the checkout,
    which would make every case here depend on the working tree AND pay for a
    crawl per test. Pinning the set to the notations this file's fixtures use
    isolates the gate's own logic from the resolver's; the resolver's own
    behaviour — including what it does when resolution fails — is covered in
    ``test_freshness_notation_crosscheck*.py``.
    """
    _stub_expected_notations(monkeypatch, _RESOLVED_NOTATIONS)
