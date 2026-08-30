#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``freshness notation crosscheck`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the notation cross-check on ``pre-commit-verify-freshness``.

The gate's primary predicate ("a ``kind=build`` row with ``status == 'success'``
and a matching ``worktree_sha`` exists") asserts a row EXISTS; it never asks
whether the row is evidence of a build THIS project performs. Those tests pin the
check that closes that gap, in BOTH directions — because a one-directional fix
trades one false signal for its mirror:

* **Refusal direction.** A matching row whose notation the project's
  architecture does not resolve is refused (``stale`` / ``notation_unrelated``).
  Against the pre-change gate the same ledger returned ``fresh`` with no
  indication anything was odd, which is what made the defect undetectable.
* **Acceptance direction.** A project that legitimately builds with several
  notations still passes, including when an unrelated row sits AHEAD of the
  related one in ledger file order — a first-match return would refuse it.

Three further properties are pinned by those tests because losing any would reintroduce a
defect this work exists to close:

* **The record names its evidence.** A ``fresh`` verdict carries the matched
  notation, the matched row's index in the ledger, its ``plan_id`` and its
  timestamp, plus the cross-check verdict and the resolved notation set. A pass
  is auditable rather than a bare assertion.
* **Structural stale verdicts stay stale.** A tree mutated after its last build
  is correctly ``stale``, and nothing in them re-stamps or relaxes the sha
  comparison to make it pass. Weakening that would reintroduce the false-green
  class the cross-check exists to close.
* **The check is not a no-op.** One case drives the gate with NO seam stubbed at
  all, so a resolver that stopped importing at runtime — or stopped resolving
  anything against a real tree — is a failure there rather than a permanent
  ``unverified`` pass that leaves every other case green. Its comparison target
  has its own coverage in
  ``test/plan-marshall/manage-architecture/test_project_build_notations.py``.

The resolver seam (``resolve_expected_notations``) is stubbed in most gate-level
cases so they neither depend on the working tree nor pay for a crawl; the
resolver's own outcome contract is exercised directly against
``_freshness_crosscheck``, and the live path has its own dedicated case.
"""


from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck as crosscheck
import pytest

from conftest import PROJECT_ROOT

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
    '_cmd_pre_commit_verify_freshness_crosscheck_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)


cmd_pre_commit_verify_freshness = _freshness_mod.cmd_pre_commit_verify_freshness


_CURRENT_SHA = 'a' * 64


_OTHER_SHA = 'b' * 64


_PYPROJECT = 'plan-marshall:build-pyproject:pyproject_build'


_MAVEN = 'plan-marshall:build-maven:maven'


_NPM = 'plan-marshall:build-npm:npm'


_GRADLE = 'plan-marshall:build-gradle:gradle'


# =============================================================================
# Fixture builders
# =============================================================================


def _build_entry(
    *,
    worktree_sha: str | None = _CURRENT_SHA,
    status: str | None = 'success',
    notation: str | None = _PYPROJECT,
    plan_id: str | None = 'crosscheck-test',
    timestamp_iso: str = '2026-06-11T12:00:00Z',
    args: str | None = 'run',
    outcome: dict | None = None,
) -> dict:
    """Construct a ``kind=build`` ledger row.

    ``notation=None`` omits the key entirely, modelling a row no dispatch
    boundary could have written (``build_record`` requires the field), which is
    the shape a hand-appended or test-authored row most easily takes.

    ``args`` defaults to the bare ``'run'`` these notation cases have always
    used. It carries no ``--command-args``, so the SCOPE cross-check reads such a
    row as unreadable and reports ``undetermined`` — which is exactly why the
    notation cases below are unaffected by that second dimension. A scope case
    passes a realistic argv through :func:`_args_for`.

    ``outcome`` is the wrapper's stdout TOON, omitted by default. The scope
    dimension reads ``tests_run`` / ``tests_population`` from it, and its ABSENCE
    is deliberately not a refusal: an unmeasured test count says nothing.
    """
    entry: dict = {
        'kind': 'build',
        'plan_id': plan_id,
        'args': args,
        'exit_code': 0,
        'worktree_sha': worktree_sha,
        'log_file': None,
        'timestamp_iso': timestamp_iso,
    }
    if notation is not None:
        entry['notation'] = notation
    if status is not None:
        entry['status'] = status
    if outcome is not None:
        entry['outcome'] = outcome
    return entry


def _args_for(command_args: str, *, plan_id: str = 'crosscheck-test') -> str:
    """Render the executor argv a ``kind=build`` row records for ``command_args``.

    Mirrors the real stamp — ``' '.join(script_args)`` over the executor argv —
    including the fact that the join is UNQUOTED, so a module-scoped
    ``--command-args "verify plan-marshall"`` lands as three bare tokens. Built
    here rather than hand-written per case so every scope test exercises the same
    shape the dispatch boundary actually writes.
    """
    return f'run --plan-id {plan_id} --command-args {command_args}'


def _outcome_for(tests_run: int | None, *, population: str = 'measured') -> dict:
    """Render the wrapper payload fragment the scope dimension reads.

    ``tests_run=None`` omits the key, modelling a payload whose test summary did
    not parse — the state that must NOT be read as zero.
    """
    outcome: dict = {'status': 'success', 'tests_population': population}
    if tests_run is not None:
        outcome['tests_run'] = tests_run
    return outcome


def _write_ledger(tmp_path: Path, entries: list[dict]) -> Path:
    ledger_path = tmp_path / 'change-ledger.jsonl'
    ledger_path.write_text(
        ''.join(json.dumps(entry, sort_keys=True) + '\n' for entry in entries),
        encoding='utf-8',
    )
    return ledger_path


def _write_status(plan_dir: Path) -> None:
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'metadata': {'worktree_path': ''}}),
        encoding='utf-8',
    )


def _stub_expected(monkeypatch, notations, reason=None) -> None:
    """Pin what the architecture resolves, without running the live crawl."""
    monkeypatch.setattr(
        crosscheck,
        'resolve_expected_notations',
        lambda _project_dir: (frozenset(notations), reason),
    )


def _required(
    *,
    analyses: set[str] | None = None,
    whole_tree: bool = True,
    modules: set[str] | None = None,
) -> crosscheck.RequiredCoverage:
    """Build the change-side coverage requirement a scope case is judged against.

    Defaults to the whole-tree, source-bearing change — every analysis required,
    only a whole-tree row adequate — because that is the state the observed
    ``858061bc`` false-green occurred in. A case narrowing the requirement says so
    explicitly.
    """
    vocabulary, reason = crosscheck.load_analysis_vocabulary()
    assert vocabulary is not None, reason
    if analyses is None:
        analyses = {vocabulary.compile, vocabulary.lint, vocabulary.test}
    return crosscheck.RequiredCoverage(
        analyses=frozenset(analyses),
        whole_tree=whole_tree,
        modules=frozenset(modules or set()),
    )


def _stub_required(monkeypatch, required, reason=None) -> None:
    """Pin what the CHANGE requires, without deriving a live plan footprint.

    Stubs the consumer's own resolution seam rather than the git/architecture
    calls beneath it, for the same reason ``_stub_expected`` stubs the resolver:
    the derivation has its own coverage, and a gate-level case should not pay for
    a footprint crawl to assert a verdict mapping.
    """
    monkeypatch.setattr(
        _freshness_mod,
        '_resolve_required_coverage',
        lambda _plan_id: (required, reason),
    )


def _run(plan_context, monkeypatch, tmp_path, entries, plan_id) -> dict:
    """Drive the real gate handler against a temp ledger and a pinned sha."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, entries)
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)
    result: dict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    return result


# =============================================================================
# Positive control: the WHOLE real path, no seam stubbed
# =============================================================================

class _FakeQueryModule:
    """Stand-in for ``_cmd_client_query`` exposing only the one function used.

    The cross-check imports ``resolve_project_build_notations`` in-function, so
    substituting the module in ``sys.modules`` exercises the real import path
    (including its failure branch) without running the architecture crawl.
    """

    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def resolve_project_build_notations(self, project_dir: str = '.'):
        del project_dir
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Reach the ledger scan on every case; the short-circuit has its own file."""
    monkeypatch.setattr(_freshness_mod, '_build_necessity_verdict', lambda _plan_id: {'decision': 'build'})
