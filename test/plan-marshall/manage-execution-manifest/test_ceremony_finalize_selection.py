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
nested param object in ``phase-6-finalize.steps``: ``qgate`` →
``default:pre-push-quality-gate``; ``self_review`` →
``default:pre-submission-self-review``; ``simplify`` →
``default:finalize-step-simplify``; ``security_audit`` →
``default:finalize-step-security-audit``. There is no flat phase-level ``qgate``
sibling. The internal transform name retains the ``ceremony_finalize`` prefix for
continuity.

**Two declaration channels, one merged source.** That ``steps[<owner>].lane``
override is resolved from the MERGED plan-local-over-marshal step map, not from
marshal.json alone: a plan-scoped answer persisted to that plan's
``status.metadata.finalize_step_overrides`` governs the ceremony gate exactly as
a project-wide marshal declaration does. The obligation is a SYMMETRIC PAIR — the
same merged map feeds ``_read_step_owned_knob`` (this transform's run-at-all
knob) and ``_lane_override_for`` (the scope gate's declared-lane immunity
predicate) — so a declaration can never reach one reader and be invisible to the
other. ``TestCeremonyFinalizePlanLocalChannel`` asserts the two channels resolve
identically, which is the assertion that fails if the two readers ever diverge
again.

``always`` is the only path that RE-ADDS a step a pre-filter already dropped, and
it covers only these four gates. It is not the only way an operator declaration
survives an implicit gate: ``scope_gated_finalize``'s declared-lane immunity keeps
a step carrying an explicit non-``auto`` ``lane`` from being dropped at all. That
mechanism (prevent the drop) is distinct from this one (undo the drop), and it is
the only one available to the steps this transform does not cover — see
``test_decision_rules.py`` for its coverage.
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
#
# Every assignment MUST name an emitter that still exists: ``setattr`` on a module
# succeeds for a name that was never defined, so a stale entry would silently
# re-create a removed attribute instead of failing loudly.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_kept_unknown = lambda *a, **kw: None
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
}

# The four ceremony gates whose value is written as the owning step's ``lane``
# override (``off``/``minimal``/``auto``). Any other step-folded knob a caller
# passes is written under its own param key verbatim.
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
    ``_read_step_owned_knob``); any other step-folded knob writes under its own
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


def _stub_footprint(footprint: list[str] | None) -> None:
    """Stub the footprint seams so activation pre-filters see the given state.

    Two seams resolve the live footprint independently: the composer's own
    ``_mem._resolve_footprint`` (the canonical-verify pre-filter, the
    security-class gate and the build-verdict assertion) and
    ``extension_base._resolve_plan_footprint`` (via ``should_execute_build``,
    which the pre-push-quality-gate pre-filter delegates to). Stub BOTH so the
    test state drives every activation decision, and keep them in lock-step —
    they are symmetric peers that must never disagree about the same worktree.

    ``footprint`` carries the resolvers' three-state return verbatim: ``None``
    (unresolvable — no evidence), ``[]`` (resolvable and genuinely empty), or a
    non-empty path list.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

    _mem._resolve_footprint = _resolve
    extension_base._resolve_plan_footprint = _resolve


def _manifest_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose; return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


def _lane_dropped_reasons(result: dict) -> dict[str, str]:
    """Index the ``lane_dropped`` subtraction records by step id.

    ``lane_dropped`` carries ``{step, reason}`` records rather than bare ids, so
    each drop names WHY it happened — an explicit ``off`` opt-out versus an
    effective tier above the posture cutoff. Indexing by step keeps the
    membership assertions readable while making the reason available to the
    tests that need to distinguish the two.
    """
    return {record['step']: record['reason'] for record in result['lane_dropped']}


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
    """Snapshot + restore BOTH footprint seams so a stub never leaks across tests.

    ``_stub_footprint`` replaces two module attributes, so restoring only
    ``_mem._resolve_footprint`` left ``extension_base._resolve_plan_footprint``
    pinned for the rest of the worker process. Because ``extension_base`` is a
    shared cross-skill module, that leak reached UNRELATED test modules — a
    sibling asserting the real resolver's return observed this file's stub
    instead. Both seams are snapshotted and restored, symmetrically with the pair
    that ``_stub_footprint`` sets.
    """
    import extension_base

    original = _mem._resolve_footprint
    original_plan_footprint = extension_base._resolve_plan_footprint
    yield
    _mem._resolve_footprint = original
    extension_base._resolve_plan_footprint = original_plan_footprint


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

    def test_self_review_survives_surgical_scope_gate_via_declared_lane_immunity(self, plan_context):
        """A ``minimal`` self_review gate keeps the step on a surgical plan — by
        IMMUNITY at the scope gate, not by an ``always`` re-add.

        Setting the gate to ``minimal`` writes ``lane: minimal`` on
        ``default:pre-submission-self-review``, which is an explicit non-``auto``
        lane declaration. ``scope_gated_finalize`` therefore never drops the step,
        so by the time the ceremony transform runs there is nothing to re-add and
        ``always`` is correctly a no-op. The operator-visible outcome — the step
        runs — is unchanged; the mechanism that delivers it moved one stage
        earlier, from undoing the drop to preventing it.
        """
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
        # Kept by the scope gate's declared-lane immunity...
        assert 'pre-submission-self-review' in result['scope_gated_finalize_immune']
        assert 'pre-submission-self-review' not in result['scope_gated_finalize_dropped']
        # ...so the ceremony transform had nothing to re-add.
        assert 'pre-submission-self-review' not in result['ceremony_finalize_forced_in']

    def test_always_still_readds_a_step_the_scope_gate_dropped(self, plan_context):
        """``always`` remains the re-add path when the step carries NO lane declaration.

        Immunity only covers a step the operator declared a non-``auto`` lane for.
        Here the ``self_review`` gate is forced in through the ceremony channel
        while the owning step declares no lane, so ``scope_gated_finalize`` drops
        it on a surgical plan and the ``always`` transform genuinely re-adds it —
        the mechanism the immunity test above does NOT exercise.
        """
        # Candidate set WITHOUT the self-review owner, so the step is absent from
        # the seeded steps map (and therefore carries no lane declaration) and the
        # ceremony gate must insert it.
        candidates = [
            s for s in _phase_6_with_ceremony_steps().split(',')
            if s != 'default:pre-submission-self-review'
        ]
        _seed_marshal(candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        # Force the gate value directly — the owning step is absent from the map,
        # so `_seed_marshal` cannot fold the knob onto it.
        # ``_read_finalize_gates`` takes the plan id so it can resolve the gate's
        # lane from the MERGED plan-local-over-marshal step map; the stub accepts
        # (and ignores) it.
        original_gates = _mem._read_finalize_gates
        _mem._read_finalize_gates = lambda _plan_id: {
            'self_review': 'always', 'qgate': 'auto', 'simplify': 'auto', 'security_audit': 'auto',
        }
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id='ceremony-always-readd',
                    scope_estimate='surgical',
                    change_type='bug_fix',
                    phase_6_steps=','.join(candidates),
                )
            )
        finally:
            _mem._read_finalize_gates = original_gates

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in _bare(_manifest_phase_6_steps(result))
        # The canonical insertion form is BARE (aligned with the compose-time
        # canonical-step-key gate) — no `default:`-prefixed id is re-inserted.
        assert 'pre-submission-self-review' in result['ceremony_finalize_forced_in']

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
    `canonicalize_step_key`-normalizes it to bare ``pre-submission-self-review``
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
        assert 'pre-submission-self-review' not in result['ceremony_finalize_forced_in']


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
    with ``auto`` deferring to the matrix-time ``security_class_inactive``
    pre-filter. The CEREMONY gate is still the symmetric peer of the other three
    (self_review / qgate / simplify); the PRE-FILTER it defers to is not — that one
    shares no helper with ``simplify_inactive`` and reads no ``change_type``.

    ``finalize-step-security-audit`` is a member of ``DEFAULT_PHASE_6_STEPS`` and of
    the security class (frontmatter ``persona: persona-security-expert``). The
    ``security_class_inactive`` pre-filter drops it ONLY when
    ``affected_files_count == 0`` AND the live footprint is empty. The default
    ``_compose_ns`` (``affected_files_count=5``) with the non-empty ``_FOOTPRINT``
    stub therefore keeps the step in the ``auto`` baseline for EVERY change type —
    ``analysis`` and ``verification`` are no longer 'gate fails' fixtures, because
    that is exactly the regression this gate closes. The canonical 'gate fails'
    fixture is now ``affected_files_count=0`` together with ``_stub_footprint([])``.
    """

    def test_auto_defers_to_prefilter_keep_branch(self, plan_context):
        # files>0 → security_class_inactive keeps the step (the gate has no
        # change_type leg); auto is a no-op, so it survives.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-secaudit-auto-keep'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert result['ceremony_finalize_forced_out'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_auto_keeps_the_step_for_an_excluded_change_type(self, plan_context):
        # ⭐ The regression: change_type='analysis' used to drop the step. It must
        # not — the plan declares 5 affected files, so there is a change surface to
        # audit, and security_class_inactive reads no change_type at all.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(
            _compose_ns(plan_id='ceremony-secaudit-auto-excluded-type', change_type='analysis')
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert result['security_class_omitted'] == []
        # Kept by the pre-filter, not force-added by the ceremony gate.
        assert result['ceremony_finalize_forced_in'] == []
        assert 'finalize-step-security-audit' in _bare(_manifest_phase_6_steps(result))

    def test_auto_defers_to_prefilter_drop_branch(self, plan_context):
        # The only drop condition: no declared affected files AND an empty live
        # footprint → security_class_inactive drops the step; auto does NOT re-add it.
        _seed_marshal(finalize_gates={'security_audit': 'auto'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-auto-drop',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['ceremony_finalize_gates']['security_audit'] == 'auto'
        assert [r['step'] for r in result['security_class_omitted']] == [
            'finalize-step-security-audit'
        ]
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
        # No change surface at all → security_class_inactive already dropped the
        # step; never security_audit is then a no-op (no double-drop, no
        # forced_out entry).
        _seed_marshal(finalize_gates={'security_audit': 'off'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-never-absent',
                change_type='feature',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert 'finalize-step-security-audit' not in result['ceremony_finalize_forced_out']
        assert 'finalize-step-security-audit' not in _bare(_manifest_phase_6_steps(result))

    def test_always_readds_security_audit_dropped_by_prefilter(self, plan_context):
        # No change surface at all → security_class_inactive drops the step; always
        # must re-add it regardless, overriding the pre-filter.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-readd',
                change_type='feature',
                affected_files_count=0,
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
        # No change surface drops the step; always re-adds it before the
        # plan-mutating tail.
        _seed_marshal(finalize_gates={'security_audit': 'minimal'})
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-secaudit-always-order',
                change_type='feature',
                affected_files_count=0,
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
    """``enhancement`` is a member of ``simplify_inactive``'s code-touching
    activation set ``{feature, bug_fix, tech_debt, enhancement}``: with
    ``affected_files > 0`` that pre-filter KEEPS ``finalize-step-simplify``, and
    ``security_class_inactive`` independently keeps
    ``finalize-step-security-audit``, so a full-posture enhancement plan composes
    with both present — via the pre-filter keep branch, not a force-add.

    The zero-files case is where the two gates diverge, and that divergence is the
    out-of-scope-sibling proof: ``simplify_inactive`` still drops on
    ``affected_files_count == 0`` alone, while ``security_class_inactive`` needs an
    empty live footprint as well."""

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

    def test_enhancement_with_zero_files_drops_simplify_but_keeps_security_audit(
        self, plan_context
    ):
        # simplify_inactive's second leg is unchanged: affected_files_count == 0
        # drops finalize-step-simplify regardless of the code-touching change type.
        # security_class_inactive does NOT drop on that leg alone — the live
        # footprint is non-empty, so there is still a change surface to audit.
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
        assert result['simplify_omitted'] is True
        assert result['security_class_omitted'] == []
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' in bare

    def test_enhancement_with_zero_files_and_empty_footprint_drops_both(self, plan_context):
        # Both legs of security_class_inactive fail → the security step drops too.
        # This is the only shape that removes it.
        _seed_marshal()
        _stub_footprint([])

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-enhancement-zero-files-empty-footprint',
                change_type='enhancement',
                affected_files_count=0,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['simplify_omitted'] is True
        assert [r['step'] for r in result['security_class_omitted']] == [
            'finalize-step-security-audit'
        ]
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' not in bare


# =============================================================================
# Test: the plan-local declaration channel governs the ceremony gate
#
# THE R2 SYMMETRIC-PAIR REGRESSION. Two independent readers resolve the same
# ``steps[<step>].lane`` field: ``_read_step_owned_knob`` (behind
# ``_read_finalize_gates`` — each ceremony gate's run-at-all decision) and
# ``_lane_override_for`` (behind ``_has_declared_lane_override`` — the scope
# gate's declared-lane immunity predicate). Before the fix only the SECOND read
# the plan-local channel, so an operator's plan-scoped answer could grant
# scope-gate immunity while leaving the ceremony gate deaf to it — the step was
# spared one subtraction and silently taken by another.
#
# Both now consume ONE merged plan-local-over-marshal map. The assertions below
# are written as EQUIVALENCE between the two channels rather than as two
# independent expectations: a plan-local declaration must produce the same
# outcome a marshal declaration does. That framing is what fails if either reader
# regresses to a marshal-only source, because the two channels would then
# diverge even though each still "works" on its own.
# =============================================================================


def _write_plan_local_overrides(plan_context, plan_id: str, overrides: dict) -> Path:
    """Seed ``status.metadata.finalize_step_overrides`` for ``plan_id``."""
    plan_dir = Path(plan_context.plan_dir_for(plan_id))
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps({'metadata': {'finalize_step_overrides': overrides}}))
    return status_path


class TestCeremonyFinalizePlanLocalChannel:
    """A plan-local ``lane`` governs the ceremony gate exactly as a marshal one does."""

    _SELF_REVIEW_OWNER = 'default:pre-submission-self-review'

    def _compose_with(self, plan_id: str, candidates: list[str]):
        return cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

    def test_plan_local_off_drops_the_gate_step_like_a_marshal_off(self, plan_context):
        """``lane: off`` in either channel resolves the gate to ``never``.

        Asserted as an equivalence: the plan-local compose and the marshal compose
        must reach the SAME gate value and the same composed step list.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _stub_footprint(_FOOTPRINT)

        # Channel A — plan-local only; marshal declares nothing.
        _seed_marshal(candidates=candidates)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-off', {self._SELF_REVIEW_OWNER: {'lane': 'off'}}
        )
        plan_local = self._compose_with('ceremony-plan-local-off', candidates)

        # Channel B — marshal only; the plan declares nothing.
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        marshal = self._compose_with('ceremony-marshal-off', candidates)

        assert plan_local is not None and marshal is not None
        assert plan_local['ceremony_finalize_gates']['self_review'] == 'never'
        assert (
            plan_local['ceremony_finalize_gates']['self_review']
            == marshal['ceremony_finalize_gates']['self_review']
        )
        assert 'pre-submission-self-review' not in _bare(_manifest_phase_6_steps(plan_local))
        assert _bare(_manifest_phase_6_steps(plan_local)) == _bare(_manifest_phase_6_steps(marshal))

    def test_plan_local_minimal_forces_the_gate_in_like_a_marshal_minimal(self, plan_context):
        """``lane: minimal`` in either channel resolves the gate to ``always``."""
        candidates = _phase_6_with_ceremony_steps().split(',')
        _stub_footprint(_FOOTPRINT)

        _seed_marshal(candidates=candidates)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-min', {self._SELF_REVIEW_OWNER: {'lane': 'minimal'}}
        )
        plan_local = self._compose_with('ceremony-plan-local-min', candidates)

        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        marshal = self._compose_with('ceremony-marshal-min', candidates)

        assert plan_local is not None and marshal is not None
        assert plan_local['ceremony_finalize_gates']['self_review'] == 'always'
        assert (
            plan_local['ceremony_finalize_gates']['self_review']
            == marshal['ceremony_finalize_gates']['self_review']
        )

    def test_plan_local_declaration_also_grants_scope_gate_immunity(self, plan_context):
        """ONE declaration reaches BOTH readers — the symmetric-pair obligation.

        The assertion that pins the defect directly. A plan-local ``lane`` must
        simultaneously (a) resolve the ceremony gate and (b) appear in
        ``scope_gated_finalize_immune``. If only the immunity predicate saw the
        plan-local channel — the pre-fix state — the step would be spared the
        scope gate and then dropped by a ceremony gate that never heard about the
        declaration, which is a silent subtraction of an explicitly-declared step.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-immune', {self._SELF_REVIEW_OWNER: {'lane': 'off'}}
        )

        result = cmd_compose(
            _compose_ns(
                plan_id='ceremony-plan-local-immune',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        # Reader 1 — the scope gate's immunity predicate saw the declaration.
        assert 'pre-submission-self-review' in result['scope_gated_finalize_immune']
        assert 'pre-submission-self-review' not in result['scope_gated_finalize_dropped']
        # Reader 2 — the ceremony gate saw the SAME declaration.
        assert result['ceremony_finalize_gates']['self_review'] == 'never'

    def test_plan_local_overlays_a_marshal_declaration_on_the_same_step(self, plan_context):
        """Precedence is plan-local ▸ marshal, applied per step key."""
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(finalize_gates={'self_review': 'minimal'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)
        _write_plan_local_overrides(
            plan_context, 'ceremony-plan-local-wins', {self._SELF_REVIEW_OWNER: {'lane': 'off'}}
        )

        result = self._compose_with('ceremony-plan-local-wins', candidates)

        assert result is not None
        # marshal said minimal (always); the plan-local off wins → never.
        assert result['ceremony_finalize_gates']['self_review'] == 'never'

    def test_absent_plan_local_map_leaves_the_marshal_declaration_intact(self, plan_context):
        """The merge is an OVERLAY, not a replacement — no plan-local map is a no-op.

        The negative case: a merge that returned only the plan-local map would
        silently discard every project-wide declaration for any plan that has none
        of its own, and every positive test above would still pass.
        """
        candidates = _phase_6_with_ceremony_steps().split(',')
        _seed_marshal(finalize_gates={'self_review': 'off'}, candidates=candidates)
        _stub_footprint(_FOOTPRINT)

        result = self._compose_with('ceremony-no-plan-local', candidates)

        assert result is not None
        assert result['ceremony_finalize_gates']['self_review'] == 'never'


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

        # The opt-out peers with off are dropped (never kept), and each drop is
        # recorded with a reason naming the explicit opt-out rather than the
        # posture cutoff — the two are different facts about the same removal.
        lane_dropped = _lane_dropped_reasons(result)
        for step in _OPT_OUT_STEPS:
            assert step in lane_dropped
            assert "'off'" in lane_dropped[step]
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
        assert 'sonar-roundtrip' not in _lane_dropped_reasons(baseline)

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
        reasons = _lane_dropped_reasons(dropped)
        assert 'sonar-roundtrip' in reasons
        # The recorded reason attributes the drop to the explicit off, not the
        # posture — which is exactly what this test's name claims and what the
        # bare-id list could never express.
        assert "'off'" in reasons['sonar-roundtrip']
        assert 'posture cutoff' not in reasons['sonar-roundtrip']
        assert 'sonar-roundtrip' not in _bare(_manifest_phase_6_steps(dropped))
        assert all(w['step'] != 'sonar-roundtrip' for w in dropped['lane_warnings'])


# =============================================================================
# Test: ceremony pre-filter drop of an operator-selected step surfaces a
# lane_warnings[] entry (second producer on the lane_warnings channel)
#
# The API-Sheriff live case: full posture (operator keeps everything), a ceremony
# pre-filter fires, and the drop was previously SILENT — the lane said "keep", yet
# the step vanished with only the omission field as evidence. The composer now
# appends a {step, warning} entry naming the ceremony pre-filter — not the lane —
# as the remover. The per-pre-filter omission fields are unchanged in meaning:
# ``simplify_omitted`` is a boolean, ``security_class_omitted`` a {step, reason} list.
# =============================================================================


class TestCeremonyPrefilterLaneWarnings:
    """A fired ceremony pre-filter over an operator-selected step warns via lane_warnings."""

    def test_warning_emitted_when_prefilter_drops_posture_included_step(self, plan_context):
        # Full posture keeps everything, so both ceremony steps are
        # operator-selected. Zero affected files AND an empty footprint is the one
        # shape that fires BOTH pre-filters at once.
        plan_id = 'ceremony-prefilter-warning'
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint([])
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(
            _compose_ns(plan_id=plan_id, change_type='analysis', affected_files_count=0)
        )

        assert result is not None
        assert result['status'] == 'success'
        # Each pre-filter's own omission signal, unchanged in meaning.
        assert result['simplify_omitted'] is True
        assert [r['step'] for r in result['security_class_omitted']] == [
            'finalize-step-security-audit'
        ]
        # The silent-drop scenario now yields a non-empty lane_warnings naming
        # the ceremony pre-filter as the remover for BOTH dropped steps.
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' in warned
        assert 'finalize-step-security-audit' in warned
        assert 'ceremony pre-filter' in warned['finalize-step-simplify']
        assert 'ceremony pre-filter' in warned['finalize-step-security-audit']
        # Each warning must name the gate that ACTUALLY fired. The two pre-filters
        # no longer share a condition, so a shared message would misreport the
        # security-class drop as change_type-gated. A substring check on the common
        # prefix alone cannot catch that — assert the discriminating clause, and
        # assert the wrong one is absent.
        assert 'change_type/affected_files gate' in warned['finalize-step-simplify']
        assert 'zero-change-surface gate' not in warned['finalize-step-simplify']
        assert 'zero-change-surface gate' in warned['finalize-step-security-audit']
        assert 'change_type' not in warned['finalize-step-security-audit']
        # The steps are genuinely gone from the composed list.
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' not in bare
        assert 'finalize-step-security-audit' not in bare

    def test_no_warning_when_step_never_a_candidate(self, plan_context):
        # The ceremony steps are absent from the candidate set → the pre-filter
        # never fires (a no-op over an absent step) → no warning entry.
        plan_id = 'ceremony-prefilter-no-candidate'
        candidates = [
            s for s in _phase_6_with_ceremony_steps().split(',')
            if s not in ('finalize-step-simplify', 'finalize-step-security-audit')
        ]
        # finalize_gates={} still seeds the authoritative steps map from the
        # candidate list (no gate overrides).
        _seed_marshal(finalize_gates={}, candidates=candidates)
        _stub_footprint([])
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='analysis',
                affected_files_count=0,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        # Pre-filters are no-ops over an absent step.
        assert result['simplify_omitted'] is False
        assert result['security_class_omitted'] == []
        warned_steps = {w['step'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' not in warned_steps
        assert 'finalize-step-security-audit' not in warned_steps

    def test_no_warning_when_always_gate_readds_the_step(self, plan_context):
        # The simplify gate `always` (lane: minimal) re-adds the step the
        # pre-filter dropped — the step IS present, so no ceremony-pre-filter
        # warning fires for it. The security step is kept by its own pre-filter
        # (the non-empty footprint is a change surface), so it does not warn either.
        plan_id = 'ceremony-prefilter-always-readd'
        _seed_marshal(finalize_gates={'simplify': 'minimal'})
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(_compose_ns(plan_id=plan_id, change_type='analysis'))

        assert result is not None
        assert result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'finalize-step-simplify' in bare
        assert 'finalize-step-security-audit' in bare
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        assert 'finalize-step-simplify' not in warned
        assert 'finalize-step-security-audit' not in warned
