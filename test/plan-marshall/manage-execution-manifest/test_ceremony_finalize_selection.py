#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``ceremony_finalize_selection`` post-matrix transform.

The transform applies the four finalize ceremony gates (``self_review`` /
``qgate`` / ``simplify`` / ``security_audit``) to the matrix-produced
``phase_6.steps``. Each gate is governed by its owning finalize step's
per-element ``lane`` override (``steps[<owner>].lane`` ∈ ``off``/``minimal``/
``auto``), which ``_read_finalize_gates`` maps to the run-at-all decision the
transform consumes:

- lane ``auto`` (or absent) → ``auto`` (the default) defers to the existing
  machinery — no-op.
- lane ``off`` → ``never`` drops the gate's finalize step.
- lane ``minimal`` → ``always`` force-includes the gate's finalize step, re-adding
  it even when the ``scope_gated_finalize`` pre-filter dropped it.

The transform NEVER touches ``automatic-review`` — the bot-review invariant is
orthogonal and preserved.

Every ceremony gate's ``lane`` override folds under its owning finalize step's
nested param object in ``plan.phase-6-finalize.steps``: ``qgate`` →
``default:pre-push-quality-gate``; ``self_review`` →
``default:pre-submission-self-review`` (which also owns the
``drop_review_on_scope_gate`` escape hatch); ``simplify`` →
``default:finalize-step-simplify``; ``security_audit`` →
``default:finalize-step-security-audit``. There is no flat phase-level ``qgate``
sibling. The internal transform name retains the ``ceremony_finalize`` prefix for
continuity.
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
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None
_mem._log_scope_gated_finalize_subtraction = lambda *a, **kw: None
_mem._log_ceremony_finalize_selection = lambda *a, **kw: None
_mem._log_candidate_source = lambda *a, **kw: None
_mem._log_prefilter_omitted = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None

# =============================================================================
# Helpers
# =============================================================================

# The full candidate set including the ceremony-gated finalize steps in
# their canonical (project-prefixed / bare) form. The composer strips the
# `default:` prefix at intake but preserves `project:` prefixes verbatim.
_CEREMONY_FINALIZE_STEPS = [
    'pre-push-quality-gate',
    'default:pre-submission-self-review',
]


def _phase_6_with_ceremony_steps() -> str:
    """Default phase-6 candidates plus the ceremony-gated finalize steps."""
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
    commit_and_push: str | None = None,
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
        commit_and_push=commit_and_push,
    )


# Owning finalize step id for each step-folded knob. Every ceremony gate is
# owned — ``qgate`` now rides ``default:pre-push-quality-gate``'s ``lane`` override
# (there is no flat phase-level ``qgate`` sibling).
_GATE_OWNER_STEP = {
    'qgate': 'default:pre-push-quality-gate',
    'simplify': 'default:finalize-step-simplify',
    'security_audit': 'default:finalize-step-security-audit',
    'self_review': 'default:pre-submission-self-review',
    'drop_review_on_scope_gate': 'default:pre-submission-self-review',
}

# The four ceremony gates whose value is written as the owning step's ``lane``
# override (``off``/``minimal``/``auto``). Every other step-folded knob (e.g.
# ``drop_review_on_scope_gate``) is written under its own param key verbatim.
_CEREMONY_LANE_GATES = frozenset({'qgate', 'self_review', 'simplify', 'security_audit'})


def _seed_marshal(
    finalize_gates: dict[str, object] | None = None,
    ci_provider: str | None = None,
    candidates: list[str] | None = None,
) -> Path:
    """Write a marshal.json carrying the phase-6-finalize gates at their homes.

    Every ceremony gate (``qgate`` / ``self_review`` / ``simplify`` /
    ``security_audit``) is written as its owning finalize step's ``lane`` override
    (``off``/``minimal``/``auto``) nested under the step's param object in
    ``plan.phase-6-finalize.steps`` (the id-keyed map the reader consumes via
    ``_read_step_owned_knob``); ``drop_review_on_scope_gate`` writes under its own
    param key. There is no flat phase-level ``qgate`` sibling. Callers pass
    ``finalize_gates`` values in the ``lane`` vocabulary.

    Because the composer treats a marshal.json ``steps`` map as the AUTHORITATIVE
    phase-6 candidate list (preferred over the ``--phase-6-steps`` CSV), the
    ``steps`` map written here must carry the FULL candidate set — every candidate
    becomes a key, and the folded knobs nest onto their owning steps. ``candidates``
    defaults to the standard ceremony candidate set used by ``_compose_ns``; tests
    that compose with a custom candidate list pass the matching list here so the
    seeded ``steps`` map and the composed candidate list stay in sync.
    """
    from file_ops import get_marshal_path

    if candidates is None:
        candidates = _phase_6_with_ceremony_steps().split(',')

    def _strip_default(step_id: str) -> str:
        return step_id[len('default:') :] if step_id.startswith('default:') else step_id

    phase_6: dict = {}
    if finalize_gates is not None:
        # Resolve each step-folded gate to its owning step's FULL-prefixed id and
        # collect the nested knob params. A ceremony gate writes its value under the
        # owning step's ``lane`` param; any other knob writes under its own key. A
        # gate whose owner is absent from the candidate list is a no-op (mirrors the
        # runtime: an absent step owns no params to read).
        owned_params: dict[str, dict] = {}
        stripped_candidates = {_strip_default(c) for c in candidates}
        for gate, value in finalize_gates.items():
            owner = _GATE_OWNER_STEP.get(gate)
            if owner is None:
                phase_6[gate] = value
                continue
            if _strip_default(owner) not in stripped_candidates:
                continue
            param_key = 'lane' if gate in _CEREMONY_LANE_GATES else gate
            owned_params.setdefault(owner, {})[param_key] = value

        # Build the FULL candidate keyed-map IN ORDER so the composer's candidate
        # list AND its execution order are unchanged. A candidate that owns nested
        # knobs is written under the owner's FULL-prefixed key at the same
        # position (the composer strips ``default:`` at intake, so the candidate
        # list is unaffected); every other candidate seeds as None (ownerless).
        owner_by_stripped = {_strip_default(o): o for o in owned_params}
        steps: dict[str, dict | None] = {}
        for candidate in candidates:
            owner_key = owner_by_stripped.get(_strip_default(candidate))
            if owner_key is not None:
                steps[owner_key] = owned_params[owner_key]
            else:
                steps[candidate] = None
        phase_6['steps'] = steps

    # Pre-push-quality-gate activation derives from build.map globs
    # (D7/D8). The `**/*.py` build_map glob matches the stubbed footprint so the
    # pre_push_quality_gate_inactive pre-filter does NOT drop the qgate step in
    # the `auto` baseline (lets us isolate the ceremony transform's behaviour).
    marshal: dict = {
        'plan': {'phase-6-finalize': phase_6},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    if ci_provider:
        marshal['providers'] = [
            {'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}
        ]

    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _stub_footprint(footprint: list[str]) -> None:
    """Stub the footprint seams so activation pre-filters see the given set.

    Two pre-filters resolve the live footprint through different seams: the
    self-review pre-filter reads the manifest module's ``_resolve_footprint``,
    while the pre-push-quality-gate pre-filter delegates to
    ``extension_base.should_execute_build``, which resolves the footprint via the
    extension_base module's ``_resolve_plan_footprint``. Stub BOTH so the test
    footprint drives every activation decision.
    """
    import extension_base

    _mem._resolve_footprint = lambda plan_id: list(footprint)
    extension_base._resolve_plan_footprint = lambda plan_id: list(footprint)


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
    """All gates default to ``auto`` → the transform is a no-op."""

    def test_absent_ceremony_block_is_no_op(self, plan_context):
        _seed_marshal()  # no finalize gate overrides at all
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-absent'))

        assert result is not None
        assert result['status'] == 'success'
        gates = result['ceremony_finalize_gates']
        assert gates == {
            'self_review': 'auto',
            'qgate': 'auto',
            'simplify': 'auto',
            'security_audit': 'auto',
        }
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_explicit_auto_gates_are_no_op(self, plan_context):
        _seed_marshal(
            finalize_gates={
                'self_review': 'auto',
                'qgate': 'auto',
                'simplify': 'auto',
                'security_audit': 'auto',
            }
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-auto-explicit'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        # On a multi_module feature plan (Row 7 default, no scope gate), the
        # ceremony steps survive the matrix untouched. The default:-prefixed
        # candidate survives and is normalized to its bare
        # pre-submission-self-review form.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'pre-submission-self-review' in bare
        assert 'pre-push-quality-gate' in bare


# =============================================================================
# Test: never — force-drop
# =============================================================================


class TestCeremonyFinalizeNever:
    """``never`` drops the gate's finalize step from phase_6.steps."""

    def test_never_drops_each_gate_step(self, plan_context):
        _seed_marshal(
            finalize_gates={'self_review': 'off', 'qgate': 'off'}
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-all'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'pre-submission-self-review' not in bare
        assert 'pre-push-quality-gate' not in bare
        forced_out = set(result['ceremony_finalize_forced_out'])
        assert 'pre-submission-self-review' in forced_out
        assert 'pre-push-quality-gate' in forced_out

    def test_never_is_no_op_when_step_already_absent(self, plan_context):
        # Candidate set EXCLUDES self_review; never self_review is a no-op.
        candidates = [s for s in _phase_6_with_ceremony_steps().split(',')
                      if s != 'default:pre-submission-self-review']
        # The seeded steps map IS the candidate list, so it must match the
        # composed candidate set (self_review owner excluded).
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-never-absent', phase_6_steps=','.join(candidates))
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_out'] == []

    def test_never_preserves_automated_review(self, plan_context):
        _seed_marshal(
            finalize_gates={'self_review': 'off', 'qgate': 'off'},
            ci_provider='github',
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-never-bot'))

        assert result is not None
        assert result['status'] == 'success'
        # The bot-review invariant is orthogonal — automatic-review stays.
        assert 'automatic-review' in _bare(_manifest_phase_6_steps(result))


# =============================================================================
# Test: always — force-include (overriding scope_gated_finalize)
# =============================================================================


class TestCeremonyFinalizeAlways:
    """``always`` re-adds the gate's step even when a pre-filter dropped it."""

    def test_always_readds_steps_dropped_by_surgical_scope_gate(self, plan_context):
        # On surgical scope, scope_gated_finalize drops self_review
        # (and plan-retrospective). `always` must re-add it via the canonical
        # default:pre-submission-self-review insertion form.
        _seed_marshal(
            finalize_gates={'self_review': 'minimal'}
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
        assert 'pre-submission-self-review' in bare
        forced_in = set(result['ceremony_finalize_forced_in'])
        assert 'default:pre-submission-self-review' in forced_in

    def test_always_readds_qgate_dropped_by_inactive_prefilter(self, plan_context):
        # Empty footprint → pre_push_quality_gate_inactive drops the qgate step.
        # `always` re-adds it regardless.
        _seed_marshal(finalize_gates={'qgate': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(_compose_ns(plan_id='ceremony-always-qgate'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-push-quality-gate' in _bare(_manifest_phase_6_steps(result))
        assert 'pre-push-quality-gate' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        _seed_marshal(finalize_gates={'self_review': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        # multi_module feature → self_review survives the matrix already present.
        result = cmd_compose(_compose_ns(plan_id='ceremony-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'pre-submission-self-review' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        _seed_marshal(finalize_gates={'self_review': 'minimal'})
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
        assert 'pre-submission-self-review' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('pre-submission-self-review') < bare_seq.index('archive-plan')


# =============================================================================
# Test: generic consuming-project self_review form (default:pre-submission-self-review)
# =============================================================================


class TestCeremonyFinalizeGenericSelfReviewForm:
    """A consuming project lists the GENERIC ``default:pre-submission-self-review``
    step (not the meta-project ``project:``-prefixed wrapper). The composer
    `_strip_default_prefix`-normalizes it to bare ``pre-submission-self-review``
    at intake, so the ``self_review`` gate's match-set MUST recognize that bare
    form — otherwise ``never`` cannot drop it and ``always`` re-inserts a
    duplicate. Regression for the match-set that omitted the normalized form
    after the canonical insertion form was generalized to ``default:``.
    """

    def _generic_candidates(self) -> list[str]:
        # The generic consuming-project self-review form. The ``self_review`` gate
        # value is read from the ``default:pre-submission-self-review`` owner —
        # which IS this generic form — so listing it once serves as both the
        # candidate and the knob owner in the seeded steps map.
        return list(DEFAULT_PHASE_6_STEPS) + [
            'pre-push-quality-gate',
            'default:pre-submission-self-review',
        ]

    def test_never_drops_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-never-generic',
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # The normalized bare form must be dropped by `never`.
        assert 'pre-submission-self-review' not in _bare(_manifest_phase_6_steps(result))

    def test_always_does_not_duplicate_generic_default_form(self, plan_context):
        candidates = self._generic_candidates()
        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-always-generic',
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # `always` must see the already-present normalized form and NOT re-insert
        # a duplicate. Count raw occurrences (a set would mask the duplicate).
        steps = _manifest_phase_6_steps(result)
        occurrences = sum(
            1 for s in steps
            if next(iter(_bare([s]))) == 'pre-submission-self-review'
        )
        assert occurrences == 1
        assert 'default:pre-submission-self-review' not in result['ceremony_finalize_forced_in']


# =============================================================================
# Test: simplify gate — symmetric peer of the other three finalize gates
# =============================================================================


class TestCeremonyFinalizeSimplify:
    """The ``simplify`` gate forces ``finalize-step-simplify`` in/out, with
    ``auto`` deferring to the matrix-time ``simplify_inactive`` pre-filter. It is
    the symmetric peer of the other two finalize gates (self_review / qgate).

    ``finalize-step-simplify`` is a member of ``DEFAULT_PHASE_6_STEPS``; the
    ``simplify_inactive`` pre-filter keeps it only when
    ``change_type ∈ {feature, bug_fix, tech_debt, enhancement}`` AND
    ``affected_files > 0``. The default ``_compose_ns``
    (``change_type='feature'``, ``affected_files_count=5``) therefore keeps the
    step in the ``auto`` baseline. ``analysis`` / ``verification`` are the
    still-excluded change types used as the canonical 'gate fails' fixtures.
    """

    def test_auto_defers_to_prefilter_keep_branch(self, plan_context):
        # change_type=feature, files>0 → simplify_inactive keeps the step;
        # auto is a no-op, so it survives.
        _seed_marshal(finalize_gates={'simplify': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-auto-keep'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['simplify'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))

    def test_auto_defers_to_prefilter_drop_branch(self, plan_context):
        # change_type=analysis is outside the simplify activation set
        # ({feature, bug_fix, tech_debt, enhancement}) → the simplify_inactive
        # pre-filter drops the step; auto does NOT re-add it. On a multi_module
        # analysis plan (Row 7 default) the rest of phase_6 is retained.
        _seed_marshal(finalize_gates={'simplify': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-simplify-auto-drop', change_type='analysis')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['simplify'] == 'auto'
        # auto never force-includes — the pre-filter's drop stands.
        assert 'finalize-step-simplify' not in result['ceremony_finalize_forced_in']
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))

    def test_never_drops_simplify_step(self, plan_context):
        # Baseline keeps the step (feature + files>0); never must drop it.
        _seed_marshal(finalize_gates={'simplify': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-never'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in result['ceremony_finalize_forced_out']

    def test_never_is_no_op_when_already_dropped_by_prefilter(self, plan_context):
        # analysis change_type → simplify_inactive already dropped the step;
        # never simplify is then a no-op (no double-drop, no forced_out entry).
        _seed_marshal(finalize_gates={'simplify': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-simplify-never-absent', change_type='analysis')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' not in result['ceremony_finalize_forced_out']
        assert 'finalize-step-simplify' not in _bare(_manifest_phase_6_steps(result))

    def test_always_readds_simplify_dropped_by_prefilter(self, plan_context):
        # analysis change_type → simplify_inactive drops the step; always
        # must re-add it regardless, overriding the pre-filter.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-simplify-always-readd', change_type='analysis')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        # feature + files>0 → the step survives the matrix; always is a no-op.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-simplify-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-simplify' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        # analysis drops the step; always re-adds it before the
        # plan-mutating tail.
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-simplify-always-order', change_type='analysis')
        )

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'finalize-step-simplify' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('finalize-step-simplify') < bare_seq.index('archive-plan')


# =============================================================================
# Test: security_audit gate — symmetric peer of the other three finalize gates
# =============================================================================


class TestCeremonyFinalizeSecurityAudit:
    """The ``security_audit`` gate forces ``finalize-step-security-audit`` in/out,
    with ``auto`` deferring to the matrix-time ``security_audit_inactive``
    pre-filter. It is the symmetric peer of the other three finalize gates
    (self_review / qgate / simplify).

    ``finalize-step-security-audit`` is a member of ``DEFAULT_PHASE_6_STEPS``; the
    ``security_audit_inactive`` pre-filter keeps it only when
    ``change_type ∈ {feature, bug_fix, tech_debt, enhancement}`` AND
    ``affected_files > 0`` (the same gate as ``simplify_inactive``). The default
    ``_compose_ns`` (``change_type='feature'``, ``affected_files_count=5``)
    therefore keeps the step in the ``auto`` baseline. ``analysis`` /
    ``verification`` are the still-excluded change types used as the canonical
    'gate fails' fixtures.
    """

    def test_auto_defers_to_prefilter_keep_branch(self, plan_context):
        # change_type=feature, files>0 → security_audit_inactive keeps the step;
        # auto is a no-op, so it survives.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-auto-keep'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_auto_defers_to_prefilter_drop_branch(self, plan_context):
        # change_type=analysis is outside the security_audit activation set
        # ({feature, bug_fix, tech_debt, enhancement}) → the
        # security_audit_inactive pre-filter drops the step; auto does NOT
        # re-add it.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-secaudit-auto-drop', change_type='analysis')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        # auto never force-includes — the pre-filter's drop stands.
        assert 'finalize-step-security-audit' not in result['ceremony_finalize_forced_in']
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))

    def test_never_drops_security_audit_step(self, plan_context):
        # Baseline keeps the step (feature + files>0); never must drop it.
        _seed_marshal(finalize_gates={'security_audit': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-never'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-security-audit' in result['ceremony_finalize_forced_out']

    def test_never_is_no_op_when_already_dropped_by_prefilter(self, plan_context):
        # analysis change_type → security_audit_inactive already dropped the
        # step; never security_audit is then a no-op (no double-drop, no
        # forced_out entry).
        _seed_marshal(finalize_gates={'security_audit': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-never-absent', change_type='analysis'
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' not in result['ceremony_finalize_forced_out']
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))

    def test_always_readds_security_audit_dropped_by_prefilter(self, plan_context):
        # analysis change_type → security_audit_inactive drops the step; always
        # must re-add it regardless, overriding the pre-filter.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-readd', change_type='analysis'
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-security-audit' in result['ceremony_finalize_forced_in']

    def test_always_is_no_op_when_step_already_present(self, plan_context):
        # feature + files>0 → the step survives the matrix; always is a no-op.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-always-present'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_always_inserts_before_plan_mutating_tail(self, plan_context):
        # analysis drops the step; always re-adds it before the
        # plan-mutating tail.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-order', change_type='analysis'
            )
        )

        assert result is not None
        steps = _manifest_phase_6_steps(result)
        bare_seq = [next(iter(_bare([s]))) for s in steps]
        assert 'finalize-step-security-audit' in bare_seq
        assert 'archive-plan' in bare_seq
        assert bare_seq.index('finalize-step-security-audit') < bare_seq.index('archive-plan')


# =============================================================================
# Test: enhancement gate activation — enhancement is code-touching by definition
# =============================================================================


class TestEnhancementGateActivation:
    """``enhancement`` is a member of the code-touching activation set
    ``{feature, bug_fix, tech_debt, enhancement}``: with ``affected_files > 0``
    the ``simplify_inactive`` / ``security_audit_inactive`` pre-filters KEEP both
    ceremony steps, so a full-posture enhancement plan composes with
    ``finalize-step-simplify`` AND ``finalize-step-security-audit`` present —
    via the pre-filter keep branch, not a force-add."""

    def test_full_posture_enhancement_plan_keeps_both_ceremony_steps(self, plan_context):
        plan_id = 'ceremony-enhancement-activation'
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(_compose_ns(plan_id=plan_id, change_type='enhancement'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in bare
        assert 'finalize-step-security-audit' in bare
        # auto gates deferred — nothing was force-added; the pre-filters kept both.
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []

    def test_enhancement_with_zero_files_still_drops_both_ceremony_steps(self, plan_context):
        # The second gate leg is unchanged: affected_files_count == 0 drops the
        # steps regardless of the code-touching change type.
        _seed_marshal()
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-enhancement-zero-files',
                change_type='enhancement',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' not in bare


# =============================================================================
# Test: determinism — same inputs → same selection
# =============================================================================


class TestCeremonyFinalizeDeterminism:
    """Re-composing with identical inputs yields an identical ceremony selection."""

    def test_repeated_compose_is_deterministic(self, plan_context):
        _seed_marshal(
            finalize_gates={'self_review': 'minimal', 'qgate': 'off', 'simplify': 'auto'}
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


# =============================================================================
# Test: adr-propose rides the ceremony transform untouched
#
# adr-propose is NOT a ceremony-gated step — it carries no ceremony_policy gate
# and is never force-dropped or force-added by the ceremony transform. It must
# survive the matrix + ceremony selection across the change-type rows in the
# same way lessons-capture does (its post-run-review sibling).
# =============================================================================


class TestCeremonyFinalizeAdrPropose:
    """adr-propose survives the ceremony transform across change-type rows."""

    @pytest.mark.parametrize(
        'change_type,scope_estimate',
        [
            ('feature', 'multi_module'),
            ('bug_fix', 'surgical'),
            ('tech_debt', 'surgical'),
            ('enhancement', 'single_module'),
        ],
    )
    def test_adr_propose_survives_ceremony_across_change_types(
        self, plan_context, change_type, scope_estimate
    ):
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint(_FOOTPRINT)

        # plan_id rejects underscores; derive a hyphenated slug from the params.
        slug = f'{change_type}-{scope_estimate}'.replace('_', '-')
        result = cmd_compose(
            _compose_ns(
                plan_id=f'ceremony-adr-{slug}',
                change_type=change_type,
                scope_estimate=scope_estimate,
            )
        )

        assert result is not None and result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        # adr-propose is present and rides alongside its post-run-review sibling.
        assert 'adr-propose' in bare
        assert 'lessons-capture' in bare
        # The ceremony transform never touches adr-propose (not a ceremony gate).
        assert 'adr-propose' not in result['ceremony_finalize_forced_in']
        assert 'adr-propose' not in result['ceremony_finalize_forced_out']

    def test_adr_propose_not_force_dropped_when_gates_set_to_never(self, plan_context):
        """Setting every ceremony gate to ``never`` drops only the ceremony
        steps — adr-propose is not a ceremony gate, so it survives."""
        _seed_marshal(
            finalize_gates={'self_review': 'off', 'qgate': 'off', 'simplify': 'off'}
        )
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-adr-never'))

        assert result is not None and result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'adr-propose' in bare
        assert 'adr-propose' not in result['ceremony_finalize_forced_out']


# =============================================================================
# Test: compose-time immune-off floor (D2)
#
# A hand-written ``lane: off`` on a ``class: core`` / ``derived-state`` finalize
# step is IMMUNE — the composer ignores the weakening ``off`` and KEEPS the step
# at its class-default (``minimal``) tier, surfacing an informational warning in
# ``lane_warnings``. A ``lane: off`` on a ``class: adversarial`` / ``prunable``
# step remains a real opt-out that DROPS it. The retired "off honored-but-warning"
# drop of a floor element is gone. Composed under each pruning posture
# (``minimal`` / ``auto``); ``full`` is a no-op lane pass (verified separately).
# =============================================================================


# Canned lane blocks keyed by step id, mirroring the real frontmatter classes of
# the mandatory finalize ceremony floor plus two opt-out peers. The blocks are
# monkeypatched onto ``_resolve_element_lane`` so the immune-off behaviour is
# exercised deterministically without depending on the shipped frontmatter.
_IMMUNE_OFF_LANE_BLOCKS = {
    'push': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'create-pr': {'class': 'core', 'tier': 'minimal', 'cost_size': 'M'},
    'ci-verify': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'branch-cleanup': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'record-metrics': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'archive-plan': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
    'project:finalize-step-deploy-target': {'class': 'derived-state', 'tier': 'minimal', 'cost_size': 'XS'},
    'project:finalize-step-sync-plugin-cache': {'class': 'derived-state', 'tier': 'minimal', 'cost_size': 'XS'},
    'sonar-roundtrip': {'class': 'adversarial', 'tier': 'auto', 'cost_size': 'L'},
    'plan-marshall:plan-retrospective': {'class': 'prunable', 'tier': 'auto', 'cost_size': 'L'},
}

# The mandatory floor: every ``core`` / ``derived-state`` step named in the D2
# success criteria. Immune to a weakening ``off``.
_IMMUNE_FLOOR_STEPS = [
    'push',
    'create-pr',
    'ci-verify',
    'branch-cleanup',
    'record-metrics',
    'archive-plan',
    'project:finalize-step-deploy-target',
    'project:finalize-step-sync-plugin-cache',
]

# The opt-out peers: a ``lane: off`` here is honoured (drops cleanly).
_OPT_OUT_STEPS = ['sonar-roundtrip', 'plan-marshall:plan-retrospective']


def _patch_immune_off_lanes(monkeypatch):
    """Monkeypatch ``_resolve_element_lane`` to the canned immune-off blocks."""
    monkeypatch.setattr(
        _mem, '_resolve_element_lane', lambda step: _IMMUNE_OFF_LANE_BLOCKS.get(step)
    )


def _write_execution_profile(plan_context, plan_id, profile):
    """Seed ``{plan_dir}/status.json`` with ``metadata.execution_profile``."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': profile}}, indent=2),
        encoding='utf-8',
    )


def _seed_marshal_lane_overrides(candidates, off_steps):
    """Write a marshal.json whose phase-6 steps map carries per-step ``lane`` overrides.

    Every candidate becomes a key in the AUTHORITATIVE ``plan.phase-6-finalize.steps``
    map (the composer prefers it over the CSV). A step in ``off_steps`` carries a
    hand-written ``{'lane': 'off'}`` param; every other step seeds as ``None``.
    """
    from file_ops import get_marshal_path

    steps = {c: ({'lane': 'off'} if c in off_steps else None) for c in candidates}
    marshal = {
        'plan': {'phase-6-finalize': {'steps': steps}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


class TestCeremonyFinalizeImmuneOff:
    """A hand-written floor ``off`` is neutralised; an opt-out ``off`` still drops."""

    @pytest.mark.parametrize('posture', ['minimal', 'auto'])
    def test_floor_off_is_immune_kept_with_warning(self, plan_context, monkeypatch, posture):
        _patch_immune_off_lanes(monkeypatch)
        candidates = _IMMUNE_FLOOR_STEPS + _OPT_OUT_STEPS
        # Every step (floor AND opt-out) carries a hand-written lane: off.
        _seed_marshal_lane_overrides(candidates, off_steps=candidates)
        _stub_footprint(_FOOTPRINT)
        plan_id = f'immune-off-{posture}'
        _write_execution_profile(plan_context, plan_id, posture)

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        assert result['execution_profile'] == posture

        # Every mandatory floor step survives despite its hand-written off.
        composed = _bare(_manifest_phase_6_steps(result))
        for step in _IMMUNE_FLOOR_STEPS:
            assert next(iter(_bare([step]))) in composed, f'{step} must survive a floor off'

        # The opt-out peers with off are dropped (never kept).
        for step in _OPT_OUT_STEPS:
            assert step in result['lane_dropped']
            assert next(iter(_bare([step]))) not in composed

        # Each floor step surfaces an immune informational warning.
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        for step in _IMMUNE_FLOOR_STEPS:
            assert step in warned
            assert 'immune' in warned[step]

        # The retired "honored-but-warning" drop semantic is gone.
        assert all('honored' not in w['warning'] for w in result['lane_warnings'])
        # An opt-out drop never carries a warning (a clean opt-out).
        for step in _OPT_OUT_STEPS:
            assert step not in warned

    def test_full_posture_is_noop_no_lane_pruning(self, plan_context, monkeypatch):
        """Under ``full`` the lane pass is a no-op — nothing is dropped or warned,
        even with hand-written floor / opt-out offs."""
        _patch_immune_off_lanes(monkeypatch)
        candidates = _IMMUNE_FLOOR_STEPS + _OPT_OUT_STEPS
        _seed_marshal_lane_overrides(candidates, off_steps=candidates)
        _stub_footprint(_FOOTPRINT)
        plan_id = 'immune-off-full'
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        assert result['execution_profile'] == 'full'
        assert result['lane_dropped'] == []
        assert result['lane_warnings'] == []

    def test_opt_out_off_drop_is_attributable_to_off_under_auto(self, plan_context, monkeypatch):
        """Under ``auto`` an adversarial (tier-auto) step is KEPT without an override
        but DROPPED once a hand-written ``off`` is set — the drop is the off, not the
        posture cutoff."""
        _patch_immune_off_lanes(monkeypatch)
        candidates = [
            'push', 'create-pr', 'ci-verify', 'branch-cleanup',
            'record-metrics', 'archive-plan', 'sonar-roundtrip',
        ]

        # Baseline: no override → sonar-roundtrip (tier auto) survives auto posture.
        _seed_marshal_lane_overrides(candidates, off_steps=[])
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, 'immune-off-baseline', 'auto')
        baseline = cmd_compose(
            _compose_ns(
                plan_id='immune-off-baseline',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )
        assert baseline is not None and baseline['status'] == 'success'
        assert 'sonar-roundtrip' in _bare(_manifest_phase_6_steps(baseline))
        assert 'sonar-roundtrip' not in baseline['lane_dropped']

        # With off → the adversarial step drops cleanly (no warning).
        _seed_marshal_lane_overrides(candidates, off_steps=['sonar-roundtrip'])
        _write_execution_profile(plan_context, 'immune-off-optout', 'auto')
        dropped = cmd_compose(
            _compose_ns(
                plan_id='immune-off-optout',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )
        assert dropped is not None and dropped['status'] == 'success'
        assert 'sonar-roundtrip' in dropped['lane_dropped']
        assert 'sonar-roundtrip' not in _bare(_manifest_phase_6_steps(dropped))
        assert all(w['step'] != 'sonar-roundtrip' for w in dropped['lane_warnings'])
