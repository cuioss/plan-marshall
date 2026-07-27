#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression coverage for the composer's declared-step contracts.

Deliverable 1's tests pin the composer's helpers at the unit boundary. This
module exercises the same two defects from the USER-VISIBLE angle: it drives the
real ``cmd_compose`` / ``cmd_lanes_preview`` entry points over seeded marshal
fixtures and reads the result back from the PERSISTED ``execution.toon``, never
from in-memory composer internals. Three regression families:

(a) an operator-declared ``lane: minimal`` on ``plan-marshall:plan-retrospective``
    survives a ``single_module`` compose (declared-lane immunity);
(b) the composed ``phase_6.steps`` is in ascending frontmatter ``order``, asserted
    specifically for the BARE ``finalize-step-preference-emitter`` id placed
    before ``branch-cleanup``;
(c) ``cmd_lanes_preview`` membership equals ``cmd_compose`` membership for the
    same posture and marshal seed.

**Non-vacuity evidence.** Each family carries its discriminator IN-TEST rather
than relying on an out-of-band "ran it against the old code" claim: every test
that asserts the fixed behaviour is paired with an assertion that pins the
pre-fix behaviour on the same inputs — the undeclared-lane compose still drops
the step (a), the legacy ``_check_ascending_order`` still reports nothing on the
pinned list while the new gate rejects it (b), and the raw lane projection still
differs in sequence from the preview (c). A test whose discriminator also passed
before the fix would be vacuous; these cannot, because the paired assertions
observe the two behaviours diverging inside one run.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

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
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_declared_contract_regression', 'manage-execution-manifest.py')
_mem._log_decision = lambda *a, **kw: None

cmd_compose = _mem.cmd_compose
cmd_lanes_preview = _mem.cmd_lanes_preview
read_manifest = _mem.read_manifest

_RETROSPECTIVE = 'plan-marshall:plan-retrospective'
_EMITTER = 'finalize-step-preference-emitter'


# =============================================================================
# Fixtures — seed a real marshal.json; the composer prefers it over the CSV
# =============================================================================


def _seed_marshal(steps: dict[str, dict | None]) -> None:
    """Write a marshal.json whose ``phase-6-finalize.steps`` map IS the candidate list.

    Key insertion order is the seed execution order, and each value is the step's
    nested param object — the channel a per-element ``lane`` override rides.
    """
    from file_ops import get_marshal_path

    marshal = {'plan': {'phase-6-finalize': {'steps': steps}}}
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def _write_execution_profile(plan_context, plan_id: str, posture: str) -> None:
    """Seed ``status.metadata.execution_profile`` so the lane cutoff is deterministic."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': posture}}, indent=2),
        encoding='utf-8',
    )


def _compose_ns(
    plan_id: str,
    scope_estimate: str = 'multi_module',
    change_type: str = 'bug_fix',
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=4,
        phase_5_steps='verify:quality-gate',
        phase_6_steps=None,  # marshal.json is authoritative
        commit_and_push=None,
    )


def _persisted_phase_6_steps(plan_id: str) -> list[str]:
    """Read the step list back from the PERSISTED manifest, not the compose result."""
    manifest = read_manifest(plan_id)
    assert manifest is not None, f'no manifest persisted for {plan_id}'
    return list(manifest['phase_6']['steps'])


# =============================================================================
# (a) Declared-lane immunity survives a single_module compose
# =============================================================================


class TestDeclaredLaneSurvivesScopeGate:
    """An operator's ``lane: minimal`` reaches the composed manifest."""

    _STEPS_WITH_LANE: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'plan-marshall:plan-retrospective': {'lane': 'minimal'},
        'default:branch-cleanup': None,
        'default:archive-plan': None,
    }
    _STEPS_WITHOUT_LANE: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'plan-marshall:plan-retrospective': None,
        'default:branch-cleanup': None,
        'default:archive-plan': None,
    }

    def test_declared_lane_minimal_survives_single_module_compose(self, plan_context):
        """The regression: the step is emitted despite the single_module scope gate.

        Pre-fix, ``_apply_scope_gated_finalize`` dropped
        ``plan-marshall:plan-retrospective`` unconditionally on a single_module
        plan, at a stage BEFORE lane resolution — and since the step is not one of
        the four ceremony gates, no re-add path existed, so the declared lane was
        structurally unreachable.
        """
        _seed_marshal(self._STEPS_WITH_LANE)
        result = cmd_compose(_compose_ns('dsc-immune', scope_estimate='single_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-immune')
        assert result['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_dropped'] == []

    def test_discriminator_undeclared_lane_is_still_dropped(self, plan_context):
        """Non-vacuity: the SAME compose without the declaration still drops the step.

        This is the pre-fix behaviour, still live for an undeclared step. If the
        immunity test above passed for any reason other than the declaration, this
        assertion would fail too — the pair can only both hold when the
        declaration is what makes the difference.
        """
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        result = cmd_compose(_compose_ns('dsc-nodecl', scope_estimate='single_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE not in _persisted_phase_6_steps('dsc-nodecl')
        assert result['scope_gated_finalize_dropped'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_immune'] == []

    def test_surgical_scope_also_honours_the_declaration(self, plan_context):
        """The immunity is a property of the declaration, not of one scope value."""
        _seed_marshal(self._STEPS_WITH_LANE)
        result = cmd_compose(_compose_ns('dsc-immune-surgical', scope_estimate='surgical'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-immune-surgical')

    def test_non_scope_gated_plan_keeps_the_step_either_way(self, plan_context):
        """A multi_module plan never reaches the drop set — the gate is scope-entered."""
        _seed_marshal(self._STEPS_WITHOUT_LANE)
        result = cmd_compose(_compose_ns('dsc-multi', scope_estimate='multi_module'))

        assert result is not None and result['status'] == 'success'
        assert _RETROSPECTIVE in _persisted_phase_6_steps('dsc-multi')
        assert result['scope_gated_finalize_dropped'] == []


# =============================================================================
# (b) Ascending frontmatter order in the composed manifest
# =============================================================================


class TestComposedPhase6IsAscending:
    """The composed ``phase_6.steps`` is in ascending frontmatter ``order``."""

    #: Seeded in the DEFECTIVE sequence: the emitter (order 61) is appended after
    #: branch-cleanup (order 70) and archive-plan (order 1000), reproducing what
    #: ``manage-config sync-defaults`` produces when it back-fills a default-on
    #: step by appending it. The emitter is seeded with its BARE id — never the
    #: ``default:``-prefixed form.
    _INVERTED_SEED: dict[str, dict | None] = {
        'default:create-pr': None,
        'default:lessons-capture': None,
        'default:branch-cleanup': None,
        'default:archive-plan': None,
        _EMITTER: None,
    }

    def test_emitter_is_emitted_before_branch_cleanup(self, plan_context):
        """The originating symptom: a source-mutating step must precede the merge gate.

        ``finalize-step-preference-emitter`` declares ``mutates_source: true`` and
        ``order: 61``; ``branch-cleanup`` (order 70) is the merge gate. A compose
        that emits the emitter after the merge gate would run a source mutation
        against an already-merged branch.
        """
        _seed_marshal(self._INVERTED_SEED)
        result = cmd_compose(_compose_ns('dsc-order-emitter'))

        assert result is not None and result['status'] == 'success'
        steps = _persisted_phase_6_steps('dsc-order-emitter')
        assert _EMITTER in steps and 'branch-cleanup' in steps
        assert steps.index(_EMITTER) < steps.index('branch-cleanup')

    def test_emitter_is_carried_as_the_bare_id(self, plan_context):
        """The fixture and the emitted manifest both use the BARE id."""
        _seed_marshal(self._INVERTED_SEED)
        cmd_compose(_compose_ns('dsc-order-bare'))

        steps = _persisted_phase_6_steps('dsc-order-bare')
        assert _EMITTER in steps
        assert f'default:{_EMITTER}' not in steps
        assert not any(s.startswith('default:') for s in steps)

    def test_whole_composed_list_is_ascending(self, plan_context):
        """The invariant over the entire persisted list, not just the one pair."""
        _seed_marshal(self._INVERTED_SEED)
        cmd_compose(_compose_ns('dsc-order-whole'))

        steps = _persisted_phase_6_steps('dsc-order-whole')
        assert _mem.check_emitted_steps_ascending_order(steps) is None
        # archive-plan (order 1000) is the terminal barrier.
        assert steps[-1] == 'archive-plan'

    def test_discriminator_unverifiable_order_is_rejected_where_the_legacy_walk_passed(
        self, plan_context, monkeypatch
    ):
        """Non-vacuity: the pre-fix and post-fix verdicts diverge inside one run.

        With the emitter's ``order:`` unreadable, the composer's sort PINS it at
        its seeded index (after the merge gate) and the legacy
        ``_check_ascending_order`` reports NO offender — the precise silent pass
        that let the defect ship. The compose must now fail loud instead. Both
        halves are asserted here, so the test cannot pass under the old behaviour.
        """
        import _manifest_validation as _mv

        real_read = _mv._read_frontmatter_order
        monkeypatch.setattr(
            _mv,
            '_read_frontmatter_order',
            lambda path: None if path.name == f'{_EMITTER}.md' else real_read(path),
        )

        # Pre-fix verdict on the pinned list: silent pass.
        pinned = _mv._sort_steps_by_frontmatter_order(
            ['create-pr', 'branch-cleanup', _EMITTER, 'archive-plan']
        )
        assert pinned.index(_EMITTER) > pinned.index('branch-cleanup')
        assert _mv._check_ascending_order(pinned) is None

        # Post-fix verdict on the same inputs, through the real entry point.
        _seed_marshal(self._INVERTED_SEED)
        result = cmd_compose(_compose_ns('dsc-order-unverifiable'))

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'phase_6_order_violation'
        assert result['step_id'] == _EMITTER
        assert result['reason'] == 'unresolvable_order'
        # A rejected compose persists nothing.
        assert read_manifest('dsc-order-unverifiable') is None


# =============================================================================
# (c) Preview membership agrees with compose membership
# =============================================================================


class TestPreviewAgreesWithCompose:
    """``lanes preview`` and ``compose`` report the same steps for the same seed."""

    #: Every member's fate is decided by marshal configuration alone — none is in
    #: the plan-input-dependent family — so the preview can reach the composer's
    #: verdict exactly and the advisory must come back empty.
    #:
    #: Deliberately SCRAMBLED relative to frontmatter order (the merge/archive tail
    #: is seeded first) so the sequence assertions below are not satisfied by an
    #: already-ordered seed.
    _CONFIG_DECIDED_SEED: dict[str, dict | None] = {
        'default:branch-cleanup': None,   # order 70
        'default:archive-plan': None,     # order 1000
        'default:create-pr': None,        # order 20
        'default:ci-verify': None,        # order 22
        'default:lessons-capture': None,
        _EMITTER: None,                   # order 61
    }

    def test_preview_membership_equals_compose_membership(self, plan_context):
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree', 'full')

        compose_result = cmd_compose(_compose_ns('dsc-agree'))
        assert compose_result is not None and compose_result['status'] == 'success'
        composed = _persisted_phase_6_steps('dsc-agree')

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree', phase_6_steps=None))
        assert preview is not None and preview['status'] == 'success'
        previewed = preview['lanes']['full']['phase_6_steps']

        assert set(previewed) == set(composed)

    def test_preview_sequence_equals_compose_sequence(self, plan_context):
        """Agreement covers ORDER too — the divergence this reconciliation closed.

        The preview applies the composer's frontmatter-order sort, so an inverted
        seed renders identically on both surfaces.
        """
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree-seq', 'full')

        cmd_compose(_compose_ns('dsc-agree-seq'))
        composed = _persisted_phase_6_steps('dsc-agree-seq')
        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree-seq', phase_6_steps=None))

        assert preview['lanes']['full']['phase_6_steps'] == composed

    def test_discriminator_raw_lane_projection_alone_would_disagree(self, plan_context):
        """Non-vacuity: the unsorted projection the preview USED to return differs.

        Pre-fix the preview returned ``_apply_lane_resolution``'s output verbatim,
        which preserves the seed sequence. Asserting that the raw projection does
        NOT match the composed sequence — while the preview does — shows the
        agreement is produced by the reconciliation, not by the seed happening to
        be ordered already.
        """
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        _write_execution_profile(plan_context, 'dsc-agree-discriminator', 'full')

        cmd_compose(_compose_ns('dsc-agree-discriminator'))
        composed = _persisted_phase_6_steps('dsc-agree-discriminator')

        candidates = [_mem.canonicalize_step_key(k) for k in self._CONFIG_DECIDED_SEED]
        raw_kept, _dropped, _warnings = _mem._apply_lane_resolution(
            candidates, 'full', None, 'dsc-agree-discriminator'
        )
        assert raw_kept != composed, 'seed must be inverted for this discriminator to bite'

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-agree-discriminator', phase_6_steps=None))
        assert preview['lanes']['full']['phase_6_steps'] == composed

    def test_config_decided_seed_reports_an_empty_advisory(self, plan_context):
        """No member's fate needs a plan input, so the preview claims full agreement."""
        _seed_marshal(self._CONFIG_DECIDED_SEED)
        preview = cmd_lanes_preview(Namespace(plan_id='dsc-advisory-empty', phase_6_steps=None))

        assert preview is not None
        assert preview['plan_input_dependent_steps'] == []

    def test_plan_input_dependent_member_is_named(self, plan_context):
        """A member the preview cannot decide for is named rather than silently shown."""
        seed = dict(self._CONFIG_DECIDED_SEED)
        seed['default:pre-submission-self-review'] = None
        _seed_marshal(seed)

        preview = cmd_lanes_preview(Namespace(plan_id='dsc-advisory-named', phase_6_steps=None))

        assert preview is not None
        assert 'pre-submission-self-review' in preview['plan_input_dependent_steps']
