#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``reconcile`` resolves EXTERNAL steps, and the handshake renders a bad task graph.

Two surfaces that failed the same way — a check that could not see the thing it
was named for — and are fixed the same way: by asking the question the consumer
actually depends on.

**reconcile partitioned on LOADABILITY.** ``_check_step_loadable``
short-circuits every external (``project:`` / ``bundle:skill``) step to
``loadable: true`` — it asserts built-in standards-file presence and nothing
else. So the external half of ``reconcile`` was vacuous: a ``project:`` skill the
plan had just renamed, or a ``bundle:skill`` id naming no discovered
implementor, reported fine and was RETAINED. The verb passed over exactly the
frozen-view divergence it exists to catch, and finalize failed later at dispatch
instead. It now runs ``_check_step_resolvable`` — the same gate ``compose``
already applies — so one definition of "this id resolves to something" governs
both verbs.

**A non-string entry was FILTERED, not rejected.** The comprehension dropped it
silently, and under ``--apply`` the write-back of ``retained + backfill`` then
removed it from the manifest for good — an entry ERASED by a verb whose contract
is to report what it changed, with no decision-log record because it never
reached the ``stale`` bucket.

**``TaskGraphInvalid`` had no handler.** ``cmd_capture`` handled its four sibling
capture-time exceptions and not this one, so a cycle or a dangling ``depends_on``
propagated out and ``file_ops.safe_main`` rendered it ``error: internal_error``.
The boundary still failed closed — nothing was persisted — but the operator was
told only that something broke internally, never that TASK-2 depends on a task
that does not exist. The structured fields were computed and thrown away.
"""

# ruff: noqa: I001

from pathlib import Path
import json
from argparse import Namespace

import pytest

from conftest import load_script_module

import _handshake_commands
from _invariants import TaskGraphInvalid

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_external_steps'
)
cmd_reconcile = _mem.cmd_reconcile
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest

_mem._log_decision = lambda *a, **kw: None
_mem._emit_decision_log = lambda *a, **kw: None


# A real built-in step whose standards doc exists in the source tree.
REAL_A = 'push'
# An external id naming no discovered ext-point-finalize-step implementor. This
# is the shape the loadability check reported as `loadable: true`.
GHOST_BUNDLE_SKILL = 'no-such-bundle:no-such-finalize-step'
# A project-local step whose `.claude/skills/{name}/SKILL.md` does not exist.
GHOST_PROJECT = 'project:no-such-project-step'


def _write_marshal(fixture_dir: Path, phase_6_steps: list[str]) -> None:
    """Seed marshal.json with ``phase_6_steps`` as the LIVE candidate set."""
    data: dict = {
        'plan': {'phase-6-finalize': {'steps': {step: {} for step in phase_6_steps}}},
        'build': {},
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(data), encoding='utf-8')


def _seed_manifest(plan_id: str, frozen: list, candidate_steps: list | None = None) -> None:
    """Write a manifest directly so the frozen view is exactly ``frozen``."""
    phase_6: dict = {'steps': list(frozen), 'step_params': {}}
    if candidate_steps is not None:
        phase_6['candidate_steps'] = list(candidate_steps)
    write_manifest(
        plan_id,
        {
            'manifest_version': 1,
            'plan_id': plan_id,
            'phase_5': {'early_terminate': False, 'verification_steps': [], 'envelope_count': 1},
            'phase_6': phase_6,
        },
    )


def _ns(plan_id: str, apply: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, apply=apply)


# =============================================================================
# reconcile resolves external steps instead of waving them through
# =============================================================================


class TestExternalStepsAreResolved:
    @pytest.mark.parametrize('ghost', [GHOST_BUNDLE_SKILL, GHOST_PROJECT])
    def test_unresolvable_external_step_absent_from_live_config_is_stale(self, plan_context, ghost):
        """Live config agrees the step is gone, so the frozen view is merely behind.

        Under the loadability check this step reported ``loadable: true`` and was
        RETAINED — the bucket it belongs in was unreachable for every external id.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-ext-stale', [REAL_A, ghost], candidate_steps=[REAL_A, ghost])

        result = cmd_reconcile(_ns('rec-ext-stale'))

        assert result['status'] == 'success'
        assert result['stale'] == [ghost]
        assert result['broken'] == []

    @pytest.mark.parametrize('ghost', [GHOST_BUNDLE_SKILL, GHOST_PROJECT])
    def test_unresolvable_external_step_still_in_live_config_fails_loud(self, plan_context, ghost):
        """Live config still schedules it, so reconciling it away would drop real work."""
        _write_marshal(plan_context.fixture_dir, [REAL_A, ghost])
        _seed_manifest('rec-ext-broken', [REAL_A, ghost], candidate_steps=[REAL_A, ghost])

        result = cmd_reconcile(_ns('rec-ext-broken'))

        assert result['status'] == 'error'
        assert result['error'] == 'unreconcilable_step'
        assert result['broken'] == [ghost]

    @pytest.mark.parametrize('ghost', [GHOST_BUNDLE_SKILL, GHOST_PROJECT])
    def test_a_broken_external_step_writes_nothing(self, plan_context, ghost):
        _write_marshal(plan_context.fixture_dir, [REAL_A, ghost])
        _seed_manifest('rec-ext-nowrite', [REAL_A, ghost], candidate_steps=[REAL_A, ghost])

        cmd_reconcile(_ns('rec-ext-nowrite', apply=True))

        assert ghost in read_manifest('rec-ext-nowrite')['phase_6']['steps']

    def test_an_unresolvable_external_candidate_is_not_backfilled(self, plan_context):
        """Backfill uses resolvability too — otherwise it ADDS a guaranteed failure.

        The candidate is new since compose (absent from ``candidate_steps``), so
        the narrowing rule would admit it; only the resolvability test keeps a
        step finalize cannot dispatch out of the manifest.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST_BUNDLE_SKILL])
        _seed_manifest('rec-ext-backfill', [REAL_A], candidate_steps=[REAL_A])

        result = cmd_reconcile(_ns('rec-ext-backfill', apply=True))

        assert result['backfill'] == []
        assert GHOST_BUNDLE_SKILL not in read_manifest('rec-ext-backfill')['phase_6']['steps']


# =============================================================================
# A non-string phase_6.steps entry is REJECTED, naming its index
# =============================================================================


class TestNonStringEntryIsRejected:
    @pytest.mark.parametrize(
        ('entry', 'type_name'),
        [
            pytest.param(None, 'NoneType', id='null'),
            pytest.param(7, 'int', id='int'),
            pytest.param({'step': REAL_A}, 'dict', id='dict'),
            pytest.param([REAL_A], 'list', id='list'),
        ],
    )
    def test_non_string_entry_is_invalid_manifest(self, plan_context, entry, type_name):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-nonstring', [REAL_A, entry], candidate_steps=[REAL_A])

        result = cmd_reconcile(_ns('rec-nonstring'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_manifest'
        assert result['offending_index'] == 1
        assert type_name in result['message']

    def test_the_offending_index_is_the_entrys_real_position(self, plan_context):
        """The index is the only handle a malformed entry has — it has no step id.

        Pinned at a non-zero, non-final position so an implementation returning a
        constant, the first index, or the last one cannot pass.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-nonstring-idx', [REAL_A, REAL_A, None, REAL_A], candidate_steps=[REAL_A])

        result = cmd_reconcile(_ns('rec-nonstring-idx'))

        assert result['offending_index'] == 2

    def test_apply_does_not_erase_the_malformed_entry(self, plan_context):
        """The regression: ``--apply`` used to write it out of existence silently."""
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-nonstring-apply', [REAL_A, None], candidate_steps=[REAL_A])

        cmd_reconcile(_ns('rec-nonstring-apply', apply=True))

        persisted = read_manifest('rec-nonstring-apply')['phase_6']['steps']
        assert len(persisted) == 2, f'the malformed entry was erased by a refusing run: {persisted}'


# =============================================================================
# TaskGraphInvalid is rendered, not swallowed as internal_error
# =============================================================================


_CYCLE = ['TASK-1', 'TASK-2', 'TASK-1']
_DANGLING = [{'task': 'TASK-3', 'missing': 'TASK-99'}]


@pytest.fixture
def graph_invalid(monkeypatch):
    """Make ``capture_all`` raise the way a cyclic / dangling task graph does.

    Patched at ``capture_all`` rather than driven through real task files: the
    graph detection itself is already covered, and what is under test here is
    the HANDLER — that the exception is caught at all, and that its structured
    fields reach the payload instead of being discarded.
    """
    monkeypatch.setattr(_handshake_commands, '_load_status_metadata', lambda plan_id: {})

    def _raise(*_args, **_kwargs):
        raise TaskGraphInvalid(cycle=list(_CYCLE), dangling=[dict(row) for row in _DANGLING])

    monkeypatch.setattr(_handshake_commands, 'capture_all', _raise)


def _assert_task_graph_payload(result: dict, phase: str) -> None:
    """Both verbs render ONE shape — the operator sees the same envelope either way."""
    assert result['status'] == 'error'
    assert result['error'] == 'task_graph_invalid'
    assert result['phase'] == phase
    assert result['cycle'] == _CYCLE
    assert result['dangling'] == _DANGLING
    assert 'task_graph_valid failed' in result['message']


class TestTaskGraphInvalidIsStructured:
    def test_capture_renders_the_cycle_payload(self, graph_invalid):
        args = Namespace(plan_id='tg-capture', phase='4-plan', override=False, reason=None)

        result = _handshake_commands.cmd_capture(args)

        _assert_task_graph_payload(result, '4-plan')

    def test_verify_renders_the_same_payload(self, graph_invalid, monkeypatch):
        """``cmd_verify`` treats it as a REFUSAL, not as drift.

        Unlike ``PhaseStepsIncomplete`` / ``BlockingFindingsPresent`` — whose
        observed values ARE meaningful column readings and are rendered as drift
        against the baseline — a bad graph aborts ``capture_all`` before any
        observed row exists, so there is nothing to diff.
        """
        monkeypatch.setattr(_handshake_commands, 'get_row', lambda plan_id, phase: {'phase': phase, 'override': False})
        args = Namespace(plan_id='tg-verify', phase='5-execute', strict=True)

        result = _handshake_commands.cmd_verify(args)

        _assert_task_graph_payload(result, '5-execute')
        assert result['status'] != 'drift'
        assert 'diffs' not in result

    def test_no_row_is_persisted_on_the_capture_refusal(self, graph_invalid, monkeypatch):
        """The refusal must return BEFORE ``upsert_row`` — a bad graph writes nothing."""
        written: list = []
        monkeypatch.setattr(_handshake_commands, 'upsert_row', lambda plan_id, row: written.append((plan_id, row)))
        args = Namespace(plan_id='tg-norow', phase='4-plan', override=False, reason=None)

        _handshake_commands.cmd_capture(args)

        assert written == []

    def test_a_dangling_only_graph_still_renders(self, monkeypatch):
        """A dangling reference with no cycle carries an empty ``cycle`` list.

        Pinned so the payload cannot be passing because both fields happen to be
        populated in the fixture above.
        """
        monkeypatch.setattr(_handshake_commands, '_load_status_metadata', lambda plan_id: {})

        def _raise(*_args, **_kwargs):
            raise TaskGraphInvalid(cycle=[], dangling=[{'task': 'TASK-3', 'missing': 'TASK-99'}])

        monkeypatch.setattr(_handshake_commands, 'capture_all', _raise)
        args = Namespace(plan_id='tg-dangling', phase='4-plan', override=False, reason=None)

        result = _handshake_commands.cmd_capture(args)

        assert result['error'] == 'task_graph_invalid'
        assert result['cycle'] == []
        assert result['dangling'] == [{'task': 'TASK-3', 'missing': 'TASK-99'}]
