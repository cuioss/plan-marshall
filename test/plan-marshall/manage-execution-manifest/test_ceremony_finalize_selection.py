#!/usr/bin/env python3
"""Tests for the ``ceremony_finalize_selection`` post-matrix transform.

The transform applies the three ``ceremony_policy.finalize`` run-at-all gates
(``self_review`` / ``qgate`` / ``plugin_doctor``, each ``always|never|auto``)
to the matrix-produced ``phase_6.steps``:

- ``auto`` (the default) defers to the existing machinery — no-op.
- ``never`` drops the gate's finalize step.
- ``always`` force-includes the gate's finalize step, re-adding it even when the
  ``scope_gated_finalize`` pre-filter dropped it.

The transform NEVER touches ``automated-review`` — the bot-review invariant
(``bot_enforcement_guard``) is orthogonal and preserved. Override rows
(``ceremony_policy.overrides[]``) win over the section values, matched on plan
facts (``scope_estimate`` / ``plan_source`` / ``change_type``).

The actual implemented ``ceremony_policy.finalize`` contract is three
independent ``always|never|auto`` gates (introduced in D3, schema owned by
``manage-config/standards/data-model.md``). The TASK-17 planning description
named stale ``full|light|none`` placeholder values; these tests cover the real
per-gate contract per the task's stated intent ("the composer honours
ceremony_policy.finalize deterministically").
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext  # noqa: F401  (re-exported for fixture discovery)

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script_ceremony_finalize', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess in tests.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_commit_push_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_bot_enforcement_guard_remediated = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_scope_gated_finalize_subtraction = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_ceremony_finalize_selection = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_candidate_source = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_simplify_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_execution_tier_routing = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Helpers
# =============================================================================

# The full candidate set including the three ceremony-gated finalize steps in
# their canonical (project-prefixed / bare) form. The composer strips the
# `default:` prefix at intake but preserves `project:` prefixes verbatim.
_CEREMONY_FINALIZE_STEPS = [
    'pre-push-quality-gate',
    'project:finalize-step-pre-submission-self-review',
    'project:finalize-step-plugin-doctor',
]


def _phase_6_with_ceremony_steps() -> str:
    """Default phase-6 candidates plus the three ceremony-gated finalize steps."""
    steps = list(DEFAULT_PHASE_6_STEPS) + _CEREMONY_FINALIZE_STEPS
    return ','.join(steps)


def _compose_ns(
    plan_id: str = 'ceremony-test',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_strategy: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps if phase_6_steps is not None else _phase_6_with_ceremony_steps(),
        commit_strategy=commit_strategy,
    )


def _seed_marshal(
    ceremony_finalize: dict[str, str] | None = None,
    overrides: list[dict] | None = None,
    ci_provider: str | None = None,
) -> Path:
    """Write a marshal.json carrying a ``ceremony_policy`` block for the test."""
    from file_ops import get_marshal_path  # type: ignore[import-not-found]

    marshal: dict = {
        'plan': {
            'phase-6-finalize': {
                # activation_globs matches the stubbed footprint so the
                # pre_push_quality_gate_inactive pre-filter does NOT drop the
                # qgate step in the `auto` baseline (lets us isolate the
                # ceremony transform's behaviour).
                'pre_push_quality_gate': {'activation_globs': ['**/*.py']},
            }
        },
    }
    ceremony: dict = {}
    if ceremony_finalize is not None:
        ceremony['finalize'] = ceremony_finalize
    if overrides is not None:
        ceremony['overrides'] = overrides
    if ceremony:
        marshal['ceremony_policy'] = ceremony
    if ci_provider:
        marshal['ci'] = {'provider': ci_provider}

    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _stub_footprint(footprint: list[str]) -> None:
    """Stub ``_resolve_footprint`` so activation pre-filters see the given set."""
    _mem._resolve_footprint = lambda plan_id: list(footprint)


def _manifest_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose; return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


def _bare(steps: list[str]) -> set[str]:
    """Strip the ``default:`` / ``project:`` prefix from each step for membership checks."""
    out: set[str] = set()
    for s in steps:
        for prefix in ('default:', 'project:'):
            if s.startswith(prefix):
                s = s[len(prefix) :]
                break
        out.add(s)
    return out


_FOOTPRINT = ['marketplace/bundles/x/skills/y/foo.py']


@pytest.fixture(autouse=True)
def _restore_footprint_resolver():
    """Snapshot + restore ``_resolve_footprint`` so a stub never leaks across tests."""
    original = _mem._resolve_footprint
    yield
    _mem._resolve_footprint = original


# =============================================================================
# Test: auto (default) — no-op
# =============================================================================


class TestCeremonyFinalizeAuto:
    """All three gates default to ``auto`` → the transform is a no-op."""

    def test_absent_ceremony_block_is_no_op(self, plan_context):
        _seed_marshal()  # no ceremony_policy block at all
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-absent'))

        assert result is not None
        assert result['status'] == 'success'
        gates = result['ceremony_finalize_gates']
        assert gates == {'self_review': 'auto', 'qgate': 'auto', 'plugin_doctor': 'auto'}
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_explicit_auto_gates_are_no_op(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'auto', 'qgate': 'auto', 'plugin_doctor': 'auto'}
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-explicit'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        # On a multi_module feature plan (Row 7 default, no scope gate), the
        # three ceremony steps survive the matrix untouched.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-pre-submission-self-review' in bare
        assert 'pre-push-quality-gate' in bare
        assert 'finalize-step-plugin-doctor' in bare


# =============================================================================
# Test: never — force-drop
# =============================================================================


class TestCeremonyFinalizeNever:
    """``never`` drops the gate's finalize step from phase_6.steps."""

    def test_never_drops_each_gate_step(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'never', 'qgate': 'never', 'plugin_doctor': 'never'}
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-all'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-pre-submission-self-review' not in bare
        assert 'pre-push-quality-gate' not in bare
        assert 'finalize-step-plugin-doctor' not in bare
        forced_out = set(result['ceremony_finalize_forced_out'])
        assert 'project:finalize-step-pre-submission-self-review' in forced_out
        assert 'pre-push-quality-gate' in forced_out
        assert 'project:finalize-step-plugin-doctor' in forced_out

    def test_never_is_no_op_when_step_already_absent(self, plan_context):
        # Candidate set EXCLUDES plugin_doctor; never plugin_doctor is a no-op.
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',')
                      if s != 'project:finalize-step-plugin-doctor']
        _seed_marshal(ceremony_finalize={'plugin_doctor': 'never'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-never-absent', phase_6_steps=','.join(candidates))
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_out'] == []

    def test_never_preserves_automated_review(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'never', 'qgate': 'never', 'plugin_doctor': 'never'},
            ci_provider='github',
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-bot'))

        assert result is not None
        assert result['status'] == 'success'
        # The bot-review invariant is orthogonal — automated-review stays.
        assert 'automated-review' in _bare(_manifest_phase_6_steps(result))


# =============================================================================
# Test: always — force-include (overriding scope_gated_finalize)
# =============================================================================


class TestCeremonyFinalizeAlways:
    """``always`` re-adds the gate's step even when a pre-filter dropped it."""

    def test_always_readds_steps_dropped_by_surgical_scope_gate(self, plan_context):
        # On surgical scope, scope_gated_finalize drops self_review and
        # plugin_doctor (and plan-retrospective). `always` must re-add both.
        _seed_marshal(
            ceremony_finalize={'self_review': 'always', 'plugin_doctor': 'always'}
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-surgical',
                scope_estimate='surgical',
                change_type='bug_fix',
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-pre-submission-self-review' in bare
        assert 'finalize-step-plugin-doctor' in bare
        forced_in = set(result['ceremony_finalize_forced_in'])
        assert 'project:finalize-step-pre-submission-self-review' in forced_in
        assert 'project:finalize-step-plugin-doctor' in forced_in

    def test_always_readds_qgate_dropped_by_inactive_prefilter(self, plan_context):
        # Empty footprint → pre_push_quality_gate_inactive drops the qgate step.
        # `always` re-adds it regardless.
        _seed_marshal(ceremony_finalize={'qgate': 'always'})
        _stub_footprint([])

        result = cmd_compose(_compose_ns(plan_id='ceremony-always-qgate'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-push-quality-gate' in _bare(_manifest_phase_6_steps(result))
        assert 'pre-push-quality-gate' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        _seed_marshal(ceremony_finalize={'self_review': 'always'})
        _stub_footprint(_FOOTPRINT)

        # multi_module feature → self_review survives the matrix already present.
        result = cmd_compose(_compose_ns(plan_id='ceremony-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-pre-submission-self-review' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        _seed_marshal(ceremony_finalize={'plugin_doctor': 'always'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-order',
                scope_estimate='surgical',
                change_type='bug_fix',
            )
        )

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        # The re-added step must precede archive-plan (plan-mutating tail).
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'finalize-step-plugin-doctor' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('finalize-step-plugin-doctor') < bare_seq.index('archive-plan')


# =============================================================================
# Test: overrides — condition-scoped rows win over section values
# =============================================================================


class TestCeremonyFinalizeOverrides:
    """``overrides[]`` rows matched on plan facts win over the section gate value."""

    def test_matching_override_forces_never(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'always'},
            overrides=[
                {'when': {'scope_estimate': 'surgical'}, 'set': {'finalize.self_review': 'never'}}
            ],
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-override-match',
                scope_estimate='surgical',
                change_type='bug_fix',
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # Override wins: self_review resolves to never despite the section's always.
        assert result['ceremony_finalize_gates']['self_review'] == 'never'
        assert 'finalize-step-pre-submission-self-review' not in _bare(_manifest_phase_6_steps(result))

    def test_non_matching_override_is_inert(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'auto'},
            overrides=[
                {'when': {'scope_estimate': 'broad'}, 'set': {'finalize.self_review': 'never'}}
            ],
        )
        _stub_footprint(_FOOTPRINT)

        # Plan is multi_module, not broad → override does not match.
        result = cmd_compose(_compose_ns(plan_id='ceremony-override-nomatch'))

        assert result is not None
        assert result['ceremony_finalize_gates']['self_review'] == 'auto'

    def test_empty_when_matches_every_plan(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'plugin_doctor': 'auto'},
            overrides=[{'when': {}, 'set': {'finalize.plugin_doctor': 'never'}}],
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-override-empty-when'))

        assert result is not None
        assert result['ceremony_finalize_gates']['plugin_doctor'] == 'never'
        assert 'finalize-step-plugin-doctor' not in _bare(_manifest_phase_6_steps(result))

    def test_later_override_row_wins(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'qgate': 'auto'},
            overrides=[
                {'when': {}, 'set': {'finalize.qgate': 'always'}},
                {'when': {}, 'set': {'finalize.qgate': 'never'}},
            ],
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-override-lastwins'))

        assert result is not None
        # Last matching row wins → never.
        assert result['ceremony_finalize_gates']['qgate'] == 'never'


# =============================================================================
# Test: determinism — same inputs → same selection
# =============================================================================


class TestCeremonyFinalizeDeterminism:
    """Re-composing with identical inputs yields an identical ceremony selection."""

    def test_repeated_compose_is_deterministic(self, plan_context):
        _seed_marshal(
            ceremony_finalize={'self_review': 'always', 'qgate': 'never', 'plugin_doctor': 'auto'}
        )
        _stub_footprint(_FOOTPRINT)

        ns1 = _compose_ns(plan_id='ceremony-determinism', scope_estimate='surgical', change_type='bug_fix')
        first = cmd_compose(ns1)
        steps_first = _manifest_phase_6_steps(first)

        ns2 = _compose_ns(plan_id='ceremony-determinism', scope_estimate='surgical', change_type='bug_fix')
        second = cmd_compose(ns2)
        steps_second = _manifest_phase_6_steps(second)

        assert steps_first == steps_second
        assert first['ceremony_finalize_gates'] == second['ceremony_finalize_gates']
        assert first['ceremony_finalize_forced_in'] == second['ceremony_finalize_forced_in']
        assert first['ceremony_finalize_forced_out'] == second['ceremony_finalize_forced_out']
