#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression: the PLAN-31 docs-only freshness deadlock.

THE DEADLOCK. A plan whose manifest composes the full build/verify list but
whose actual footprint turns out to be markdown-only could not reach push:

1. The footprint touches no ``build.map`` glob, so no build is necessary and
   none runs — therefore no ``kind=build`` change-ledger entry is ever stamped.
2. The pre-commit freshness gate demanded such an entry before permitting the
   phase transition, and its exemptions keyed on the MANIFEST'S SHAPE — empty
   ``verification_steps`` (``documentation_only``) or an all-``quality-gate``
   list (``lint_only``).
3. PLAN-31's manifest matched NEITHER shape: it carried ``module-tests`` and
   ``coverage``. So no exemption applied, the demanded ledger entry could never
   exist, and the gate reported ``stale`` forever.

The plan was wedged between two mechanisms that each decided build necessity
from a different input — the footprint on one side, the step list's shape on the
other. Consolidating both onto the single ``build-decision`` authority resolves
it: the gate now asks the authority whether a build was needed AT ALL, and a
``not_necessary`` verdict means no entry could legally exist, so none is demanded.

FIXTURE PROVENANCE. ``_PLAN_31_VERIFICATION_STEPS`` below is PLAN-31's REAL
composed shape, read verbatim — not a hand-built approximation — from the
archived plan's own manifest artifact:

    plan id : 2026-07-21-orchestrator-dispatch-ruleset  (WS-10 PLAN-31,
              "orchestrator dispatch ruleset", shipped as PR #968)
    artifact: .plan/local/archived-plans/2026-07-21-orchestrator-dispatch-ruleset/
              execution.toon
    field   : phase_5.verification_steps

A future reader can re-derive it by reading that field from that file. Using the
real shape matters: a hand-built fixture would be free to accidentally match one
of the retired shape exemptions and so would never have reproduced the deadlock.

SCOPE. This is deliberately a DISTINCT file from the per-site tests of the
migration (``test_pre_commit_verify_freshness.py``) and of the compose-time
assertion (``test_build_verdict_contradiction_guard.py``). Each of those proves
its own site behaves; none of them proves the sites AGREE end to end, which is
precisely where the deadlock lived. This file asserts the reachable end state
positively — the gate returns ``fresh`` for the authority's stated reason — and
that no build is invoked anywhere along that path.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from toon_parser import serialize_toon

from conftest import PROJECT_ROOT

_MANAGE_TASKS_SCRIPTS = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_freshness = _load_module(
    '_cmd_pre_commit_verify_freshness_plan31_regression',
    _MANAGE_TASKS_SCRIPTS / '_cmd_pre_commit_verify_freshness.py',
)
cmd_pre_commit_verify_freshness = _freshness.cmd_pre_commit_verify_freshness

# PLAN-31's real composed phase_5.verification_steps — see FIXTURE PROVENANCE.
# Note what it is NOT: not empty (so the retired ``documentation_only``
# exemption could not fire) and not all-quality-gate (so the retired
# ``lint_only`` exemption could not fire either). That is the whole reason
# PLAN-31 deadlocked where other docs-only plans did not.
_PLAN_31_VERIFICATION_STEPS = [
    'verify:quality-gate',
    'verify:module-tests',
    'verify:coverage',
]

# A markdown-only footprint: real changed files, none of them buildable.
_MARKDOWN_ONLY_FOOTPRINT = [
    'marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md',
    'marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md',
]

# The verdict build-decision returns for that footprint: build globs ARE
# registered (this is a Python project), the footprint IS non-empty, and it
# intersects none of them.
_NOT_NECESSARY_VERDICT = {
    'decision': 'not_necessary',
    'reason': 'plan footprint touches no build_map glob — only non-buildable files changed',
}

_WORKTREE_SHA = 'f' * 64


def _seed_plan(plan_context, plan_id: str) -> None:
    """Materialize the plan dir with PLAN-31's manifest shape on disk.

    The manifest is written even though the freshness gate no longer reads it —
    that is the point. Its presence proves the gate reaches ``fresh`` DESPITE a
    manifest whose shape matched no retired exemption.
    """
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'worktree_path': ''}}),
        encoding='utf-8',
    )
    manifest = {
        'manifest_version': 1,
        'plan_id': plan_id,
        'phase_5': {
            'early_terminate': False,
            'verification_steps': _PLAN_31_VERIFICATION_STEPS,
        },
        'phase_6': {'steps': ['push', 'create-pr', 'archive-plan']},
    }
    (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')


def _stub_authority(monkeypatch, verdict: dict, calls: list) -> None:
    """Point the gate's consult at ``verdict`` and record its call arguments."""
    import extension_base

    def _record(canonical_command, plan_id, *args, **kwargs):
        calls.append((canonical_command, plan_id))
        return verdict

    monkeypatch.setattr(extension_base, 'should_execute_build', _record)


def _forbid_builds(monkeypatch, invoked: list) -> None:
    """Fail loudly if anything on the gate's path shells out to a build.

    The deadlock's resolution must come from ASKING the authority, never from
    running a build to manufacture the missing ledger entry. Trapping
    ``subprocess.run`` / ``Popen`` turns "no build was invoked" into an asserted
    property rather than an assumption.
    """
    import subprocess

    def _boom(*args, **kwargs):
        invoked.append(args[0] if args else kwargs.get('args'))
        raise AssertionError(f'a subprocess was invoked on the freshness path: {invoked[-1]!r}')

    monkeypatch.setattr(subprocess, 'run', _boom)
    monkeypatch.setattr(subprocess, 'Popen', _boom)


def test_plan31_docs_only_footprint_reaches_fresh(plan_context, monkeypatch, tmp_path) -> None:
    """THE regression: PLAN-31's manifest + a markdown-only footprint reaches ``fresh``.

    Asserted positively — the gate arrives at the permitted state and names the
    authority's own reason for it — rather than merely asserting that nothing
    raised. An absence-of-exception assertion would also pass against a gate
    that returned ``stale``, which is the exact bug.
    """
    plan_id = 'plan31-docs-only-deadlock'
    _seed_plan(plan_context, plan_id)
    calls: list = []
    _stub_authority(monkeypatch, _NOT_NECESSARY_VERDICT, calls)
    # No ledger entry exists, and none can: no build ever ran.
    monkeypatch.setattr(_freshness, 'compute_worktree_sha', lambda root: _WORKTREE_SHA)
    monkeypatch.setattr(_freshness, 'resolve_ledger_path', lambda: tmp_path / 'absent.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))

    # The permitted end state — the plan can transition and reach push.
    assert result['status'] == 'fresh', result
    assert result['plan_id'] == plan_id
    # Sourced from the authority's verdict, verbatim — not a reason the gate
    # invented, and emphatically not one of the retired shape-derived names.
    assert result['reason'] == _NOT_NECESSARY_VERDICT['reason']
    assert result['reason'] not in ('documentation_only', 'lint_only')


def test_the_manifest_shape_matched_no_retired_exemption(plan_context) -> None:
    """Guard the fixture itself: PLAN-31's shape must remain deadlock-shaped.

    If a future edit trimmed this list to empty or to all-``quality-gate``, the
    regression above would still pass — but for the wrong reason, since either
    shape would have satisfied a retired exemption and so would never have
    deadlocked. This keeps the fixture honest about what it reproduces.
    """
    assert _PLAN_31_VERIFICATION_STEPS, 'empty list would have matched documentation_only'
    non_lint = [
        step
        for step in _PLAN_31_VERIFICATION_STEPS
        if step.rsplit(':', 1)[-1] != 'quality-gate'
    ]
    assert non_lint, 'all-quality-gate list would have matched lint_only'


def test_no_build_is_invoked_on_the_freshness_path(plan_context, monkeypatch, tmp_path) -> None:
    """The resolution is a question to the authority, not a build run to satisfy the gate."""
    plan_id = 'plan31-no-build-invoked'
    _seed_plan(plan_context, plan_id)
    calls: list = []
    invoked: list = []
    _stub_authority(monkeypatch, _NOT_NECESSARY_VERDICT, calls)
    monkeypatch.setattr(_freshness, 'compute_worktree_sha', lambda root: _WORKTREE_SHA)
    monkeypatch.setattr(_freshness, 'resolve_ledger_path', lambda: tmp_path / 'absent.jsonl')
    _forbid_builds(monkeypatch, invoked)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))

    assert result['status'] == 'fresh', result
    assert invoked == []


def test_the_authority_is_consulted_command_free(plan_context, monkeypatch, tmp_path) -> None:
    """"Did this plan need a build at all?" is plan-wide — no command is nominated.

    Nominating a representative canonical (the retired ``'quality-gate'``) would
    reintroduce the premise that build necessity varies by command, which is
    what let a second oracle exist in the first place.
    """
    plan_id = 'plan31-command-free-consult'
    _seed_plan(plan_context, plan_id)
    calls: list = []
    _stub_authority(monkeypatch, _NOT_NECESSARY_VERDICT, calls)
    monkeypatch.setattr(_freshness, 'compute_worktree_sha', lambda root: _WORKTREE_SHA)
    monkeypatch.setattr(_freshness, 'resolve_ledger_path', lambda: tmp_path / 'absent.jsonl')

    cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))

    assert calls == [(None, plan_id)]


def test_a_buildable_footprint_with_the_same_manifest_still_blocks(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Non-vacuity: the SAME manifest still blocks when a build genuinely was needed.

    Identical PLAN-31 step list, identical missing ledger entry — only the
    verdict differs. This proves the ``fresh`` above comes from the footprint
    verdict and not from the gate having been loosened into a rubber stamp,
    which would be a far worse defect than the deadlock it replaced.
    """
    plan_id = 'plan31-buildable-still-blocks'
    _seed_plan(plan_context, plan_id)
    calls: list = []
    _stub_authority(monkeypatch, {'decision': 'build'}, calls)
    monkeypatch.setattr(_freshness, 'compute_worktree_sha', lambda root: _WORKTREE_SHA)
    monkeypatch.setattr(_freshness, 'resolve_ledger_path', lambda: tmp_path / 'absent.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))

    assert result['status'] in ('stale', 'undecidable'), result
    assert result.get('reason') != _NOT_NECESSARY_VERDICT['reason']
