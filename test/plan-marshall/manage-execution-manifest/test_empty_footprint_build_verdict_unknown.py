#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Compose-level regression: an unresolvable footprint must not drop the pre-push gate.

**The defect.** ``_resolve_plan_footprint`` collapsed two materially different
states into one empty list — "the worktree could not be resolved" and "the
worktree is resolvable and its diff is genuinely empty". ``should_execute_build``
then reported the POSITIVE verdict ``not_necessary`` for a footprint nobody had
ever observed, and the ``pre_push_quality_gate_inactive`` pre-filter dropped
``pre-push-quality-gate`` on that unsubstantiated answer. Absence of evidence was
read as evidence of absence, and a quality gate the operator never opted out of
vanished.

**The fix's shape** (ADR-009): the resolver returns ``None`` for unresolvable and
``[]`` for resolvable-and-empty, and the verdict vocabulary gains a third value
``unknown``. Only the positive ``not_necessary`` licenses dropping the gate;
``unknown`` KEEPS it and emits a diagnosable ``[STATUS]`` line, because an
operator who cannot tell "the verdict said build" from "the verdict could not be
substantiated" has no unknown-state visibility at all.

**Why every arm below is paired.** A test that only pins the ``unknown`` keep
would be satisfied by a pre-filter that had simply stopped dropping the gate
outright — which is a different defect, not a fix. Each arm therefore names the
one variable it changes and is paired with the opposite verdict reached by
changing only that variable:

- unresolvable footprint → ``unknown`` → KEPT, with the diagnosable line;
- resolvable-and-empty footprint → ``not_necessary`` → DROPPED, with the
  subtraction line;
- non-empty footprint over a registered glob → ``build`` → KEPT, with neither
  line.

The fixture's ``marshal.json`` deliberately carries NO ``lane`` pin on
``pre-push-quality-gate``. With a pin the ceremony gate would force the step in
or out and the pre-filter's verdict would never be what decided its fate — the
test would pass while proving nothing about the verdict at all.
"""

import contextlib
import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_empty_footprint_build_verdict_unknown',
)

cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Speed stub: the advisory per-step execution_tier stamp subprocesses
# ``architecture resolve`` once per canonical-verify step and is orthogonal to
# every assertion here. Scoped to THIS module's own composer copy.
_mem._resolve_step_execution_tier = lambda _canonical, _plan_id: 'per_task'

_QGATE_STEP = 'pre-push-quality-gate'
_PHASE_5_CSV = 'verify:quality-gate,verify:module-tests'

#: A footprint path that matches the seeded ``build.map`` glob, so the verdict
#: over it is the positive ``build``.
_BUILDABLE_FOOTPRINT = ['marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py']


def _candidates() -> list[str]:
    """Phase-6 candidates: the defaults plus the gate whose fate is under test."""
    return [*DEFAULT_PHASE_6_STEPS, _QGATE_STEP]


def _seed_marshal(candidates: list[str]) -> Path:
    """Write marshal.json with build_map globs and NO ceremony pin on the qgate.

    The ``build.map`` block must be present: with no registered globs the
    authority short-circuits to ``not_necessary`` for "project has no buildable
    file types", and the gate's fate would be settled before the footprint is
    ever consulted — the arms below would then all pass for the wrong reason.

    Every candidate seeds OWNERLESS (``None`` param object). That is the
    load-bearing half of the fixture: an operator ``lane`` on ``pre-push-quality-gate``
    resolves the ``qgate`` ceremony gate to ``always``/``never`` and overrides the
    pre-filter entirely.
    """
    from file_ops import get_marshal_path

    marshal = {
        'plan': {'phase-6-finalize': {'steps': dict.fromkeys(candidates)}},
        'build': {
            'map': {
                'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}],
            },
        },
    }
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _write_status_without_worktree(plan_context, plan_id: str) -> Path:
    """Seed a ``status.json`` whose ``metadata`` carries NO ``worktree_path``.

    This is the REAL early-compose shape, reached through the production
    resolvers rather than a stub: ``phase-4-plan`` composes before
    ``phase-5-execute`` Step 2.5 materialises the worktree, so the footprint is
    genuinely unresolvable and the verdict is genuinely ``unknown``.
    """
    status_path = Path(plan_context.plan_dir_for(plan_id)) / 'status.json'
    status_path.write_text(json.dumps({'metadata': {}}))
    return status_path


def _stub_footprint(monkeypatch, footprint: list[str] | None) -> None:
    """Pin BOTH footprint seams to the same three-state value, in lock-step.

    Two resolvers answer the same question independently: the composer's own
    ``_resolve_footprint`` (security-class gate, canonical-verify pre-filter, the
    build-verdict assertion) and ``extension_base._resolve_plan_footprint``
    (reached through ``should_execute_build``, which the pre-push gate delegates
    to). They are symmetric peers that must never disagree about one worktree, so
    both are pinned together.

    ``monkeypatch`` restores BOTH on teardown. That symmetry is deliberate:
    ``extension_base`` is a shared cross-skill module, so a stub restored on only
    one seam leaks process-wide and reaches unrelated test modules under xdist.
    """
    import extension_base

    def _resolve(_plan_id):
        return None if footprint is None else list(footprint)

    monkeypatch.setattr(_mem, '_resolve_footprint', _resolve)
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', _resolve)


@contextlib.contextmanager
def _capture_decision_log():
    """Capture ``_emit_decision_log`` messages; yield the growing message list."""
    captured: list[str] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda _plan_id, message: captured.append(message)
    try:
        yield captured
    finally:
        _mem._emit_decision_log = original


def _compose_ns(plan_id: str, candidates: list[str]) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=4,
        phase_5_steps=_PHASE_5_CSV,
        phase_6_steps=','.join(candidates),
        commit_and_push=None,
    )


def _manifest_phase_6_steps(result: dict) -> list[str]:
    manifest = read_manifest(result['plan_id'])
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


def _lines_naming(messages: list[str], fragment: str) -> list[str]:
    return [m for m in messages if fragment in m]


# =============================================================================
# The unresolvable footprint — verdict ``unknown``, gate KEPT, keep reported
# =============================================================================


class TestUnresolvableFootprintKeepsTheGate:
    """An unsubstantiated verdict must not read as a positive one."""

    def test_unknown_verdict_keeps_pre_push_quality_gate(self, plan_context):
        plan_id = 'verdict-unknown-keeps-gate'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        assert result['build_verdict_decision'] == 'unknown'
        assert result['pre_push_quality_gate_omitted'] is False
        assert _QGATE_STEP in _manifest_phase_6_steps(result)

    def test_the_keep_is_the_verdict_not_a_ceremony_pin(self, plan_context):
        """The fixture must not be quietly settling the question elsewhere.

        With a ``lane`` pin on the owning step the ``qgate`` ceremony gate would
        force the step in and the pre-filter's verdict would be irrelevant. This
        asserts the gate resolved to the deferring ``auto`` and that the ceremony
        transform added nothing — so the survival above is attributable to the
        ``unknown`` verdict alone.
        """
        plan_id = 'verdict-unknown-not-a-pin'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None
        assert result['ceremony_finalize_gates']['qgate'] == 'auto'
        assert result['ceremony_finalize_forced_in'] == []
        assert _QGATE_STEP in _manifest_phase_6_steps(result)

    def test_unknown_verdict_emits_the_diagnosable_status_line(self, plan_context):
        """A silent keep gives the operator no unknown-state visibility.

        The whole point of the third verdict value is that "the authority said
        build" and "the authority could not answer" are distinguishable in the
        decision log. Asserting the line is present — and that the SUBTRACTION
        line is absent — is what pins that distinction.
        """
        plan_id = 'verdict-unknown-logs'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)

        with _capture_decision_log() as messages:
            result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        kept_lines = _lines_naming(messages, 'kept pre-push-quality-gate on an unknown build verdict')
        assert len(kept_lines) == 1
        assert '[STATUS] pre_push_quality_gate_inactive' in kept_lines[0]
        # The verdict's OWN reason is threaded through, not one the emitter invented.
        assert 'unresolvable' in kept_lines[0]
        assert _lines_naming(messages, 'dropped pre-push-quality-gate') == []


# =============================================================================
# The resolvable-but-empty footprint — verdict ``not_necessary``, gate DROPPED
# =============================================================================


class TestResolvableEmptyFootprintStillDropsTheGate:
    """The paired opposite. Only the positive verdict licenses the subtraction.

    Without this class the module would be satisfied by a pre-filter that had
    stopped dropping the gate under every condition — an over-correction that
    keeps a gate the operator's own empty worktree says is pointless.
    """

    def test_empty_footprint_drops_pre_push_quality_gate(self, plan_context, monkeypatch):
        plan_id = 'verdict-empty-drops-gate'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)
        _stub_footprint(monkeypatch, [])

        result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        assert result['build_verdict_decision'] == 'not_necessary'
        assert result['pre_push_quality_gate_omitted'] is True
        assert _QGATE_STEP not in _manifest_phase_6_steps(result)

    def test_empty_footprint_emits_the_subtraction_line(self, plan_context, monkeypatch):
        plan_id = 'verdict-empty-logs'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)
        _stub_footprint(monkeypatch, [])

        with _capture_decision_log() as messages:
            result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        dropped_lines = _lines_naming(messages, 'dropped pre-push-quality-gate')
        assert len(dropped_lines) == 1
        assert '[STATUS] pre_push_quality_gate_inactive' in dropped_lines[0]
        assert _lines_naming(messages, 'kept pre-push-quality-gate on an unknown build verdict') == []

    def test_only_the_footprint_state_differs_between_the_two_verdicts(
        self, plan_context, monkeypatch
    ):
        """Hold everything fixed and vary only unresolvable-vs-empty.

        The single assertion proving the resolver's three-state return is what
        moves the verdict — not the marshal fixture, the candidate list, or the
        change type, all of which are identical across the two composes.
        """
        candidates = _candidates()
        _seed_marshal(candidates)

        _write_status_without_worktree(plan_context, 'verdict-pair-unresolvable')
        _stub_footprint(monkeypatch, None)
        unresolvable = cmd_compose(_compose_ns('verdict-pair-unresolvable', candidates))

        _write_status_without_worktree(plan_context, 'verdict-pair-empty')
        _stub_footprint(monkeypatch, [])
        empty = cmd_compose(_compose_ns('verdict-pair-empty', candidates))

        assert unresolvable is not None and empty is not None
        assert unresolvable['build_verdict_decision'] == 'unknown'
        assert empty['build_verdict_decision'] == 'not_necessary'
        assert _QGATE_STEP in _manifest_phase_6_steps(unresolvable)
        assert _QGATE_STEP not in _manifest_phase_6_steps(empty)


# =============================================================================
# The third verdict — a real footprint over a registered glob keeps the gate
# =============================================================================


class TestBuildVerdictKeepsTheGate:
    """The ordinary code-plan shape, included so all three values are exercised.

    ``unknown`` and ``build`` both keep the gate, and a detector that keyed on
    ``decision != 'not_necessary'`` versus one that keyed on the value would be
    indistinguishable without this arm plus the ``unknown`` arm above.
    """

    def test_non_empty_buildable_footprint_keeps_the_gate_silently(
        self, plan_context, monkeypatch
    ):
        plan_id = 'verdict-build-keeps-gate'
        candidates = _candidates()
        _seed_marshal(candidates)
        _write_status_without_worktree(plan_context, plan_id)
        _stub_footprint(monkeypatch, _BUILDABLE_FOOTPRINT)

        with _capture_decision_log() as messages:
            result = cmd_compose(_compose_ns(plan_id, candidates))

        assert result is not None and result['status'] == 'success'
        assert result['build_verdict_decision'] == 'build'
        assert result['pre_push_quality_gate_omitted'] is False
        assert _QGATE_STEP in _manifest_phase_6_steps(result)
        # Neither the subtraction line nor the unknown-keep line belongs here.
        assert _lines_naming(messages, 'pre_push_quality_gate_inactive') == []
