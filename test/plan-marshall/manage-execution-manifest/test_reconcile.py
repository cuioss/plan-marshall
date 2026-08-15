#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest ``reconcile`` subcommand.

The execution manifest is a write-time snapshot: ``compose`` freezes the
phase-6 step list at outline time and ``phase-6-finalize`` consumes it verbatim
much later. A SELF-MODIFYING plan can invalidate its own frozen view in between
— it deletes a finalize step's standards doc and sweeps ``marshal.json``, and
its own already-frozen manifest still names the step.

Before ``reconcile`` the only comparison at finalize entry was
``validate-loadable``, which HARD-ABORTS on any unloadable step. That is the
wrong direction for exactly the population that produces the divergence: it
blocks a self-modifying plan from finalizing its own legitimate work.

``reconcile`` splits the two cases that ``validate-loadable`` conflated, and
that split IS the settled fail-direction:

- unloadable AND gone from live config  → **stale**: the frozen view is merely
  behind, live config agrees the step is gone. Drop it and carry on.
- unloadable AND still in live config    → **broken**: the original motivating
  failure (the doc was deleted without sweeping ``marshal.json``). Still fails
  loud, with the canonical actionable message.

Backfill is the mirror direction and is deliberately NARROW: only a live
candidate that did not exist in the candidate set ``compose`` selected FROM is
owed. A candidate the decision matrix deliberately dropped must NOT be
re-added, which is why ``compose`` now snapshots ``phase_6.candidate_steps``.
Without that snapshot (a manifest frozen before the field existed) backfill is
reported INDETERMINATE rather than guessed.
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


_mem = _load_module('_mem_reconcile', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_reconcile = _mem.cmd_reconcile
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

_mem._log_decision = lambda *a, **kw: None

# ``_emit_decision_log`` shells out to the executor, which no test may depend
# on — but stubbing it to a bare no-op would make emission UNOBSERVABLE, and
# "does a dry run write an audit record?" is exactly a question these tests must
# be able to ask. Record instead of discarding.
_EMITTED: list[tuple[str, str]] = []
_mem._emit_decision_log = lambda plan_id, message, *a, **kw: _EMITTED.append((plan_id, message))


# =============================================================================
# Helpers
# =============================================================================


def _write_marshal(fixture_dir: Path, phase_6_steps: list[str]) -> None:
    """Seed marshal.json with ``phase_6_steps`` as the LIVE candidate set."""
    data: dict = {
        'plan': {'phase-6-finalize': {'steps': {step: {} for step in phase_6_steps}}},
        'build': {},
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(data), encoding='utf-8')


def _reconcile_ns(plan_id: str, apply: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, apply=apply)


def _emitted_for(plan_id: str) -> list[str]:
    """Decision-log messages emitted for ``plan_id`` since the last reset."""
    return [message for pid, message in _EMITTED if pid == plan_id]


def _seed_manifest(
    plan_id: str,
    frozen: list[str],
    candidate_steps: list[str] | None = None,
) -> None:
    """Write a manifest directly, so the frozen view is exactly ``frozen``.

    Writing it rather than composing it is deliberate: the divergence under
    test is between a manifest frozen EARLIER and config as it is NOW, which a
    single in-test compose cannot produce.
    """
    phase_6: dict = {'steps': list(frozen), 'step_params': dict.fromkeys(frozen)}
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


# A step id that resolves to no standards doc — the "deleted doc" stand-in.
GHOST = 'ghost-step-deleted-by-this-plan'
# Two real built-in steps whose standards docs exist in the source tree.
REAL_A = 'push'
REAL_B = 'archive-plan'


# =============================================================================
# The drop direction — a frozen step live config has also dropped
# =============================================================================


class TestStaleStepIsDroppedNotFailed:
    def test_frozen_step_absent_from_live_config_is_reported_stale(
        self, plan_context
    ):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-stale', [REAL_A, GHOST, REAL_B], candidate_steps=[REAL_A, GHOST, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-stale'))
        assert result is not None
        assert result['status'] == 'success', (
            'a frozen step that live config has ALSO dropped must reconcile, '
            f'not fail: {result}'
        )
        assert result['stale'] == [GHOST]
        assert result['broken'] == []

    def test_apply_drops_the_stale_step_from_the_manifest(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-apply', [REAL_A, GHOST, REAL_B], candidate_steps=[REAL_A, GHOST, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-apply', apply=True))
        assert result['status'] == 'success'
        assert result['applied'] is True

        persisted = read_manifest('rec-apply')
        assert GHOST not in persisted['phase_6']['steps']
        assert REAL_A in persisted['phase_6']['steps']
        assert REAL_B in persisted['phase_6']['steps']

    def test_apply_prunes_the_dropped_step_params_entry(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-params', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-params', apply=True))

        persisted = read_manifest('rec-params')
        assert GHOST not in persisted['phase_6']['step_params'], (
            'a dropped step must not keep a params snapshot behind'
        )

    def test_dry_run_does_not_write(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-dry', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-dry'))
        assert result['applied'] is False
        assert GHOST in read_manifest('rec-dry')['phase_6']['steps'], (
            'reconcile without --apply is a report, not a mutation'
        )

    def test_dry_run_emits_no_decision_log_line(self, plan_context):
        """A dry run must not write an audit record for a change it did not make.

        The decision log is a record of subtractions that HAPPENED. Emitting
        from a dry run both mutates a file the verb promises not to touch and
        asserts a drop that never occurred — a false audit trail, which is
        worse than none.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-dry-log', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-dry-log'))
        assert _emitted_for('rec-dry-log') == [], (
            'a dry run emitted a decision-log line: '
            f'{_emitted_for("rec-dry-log")}'
        )

    def test_apply_emits_one_decision_log_line_per_dropped_step(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-apply-log', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-apply-log', apply=True))
        messages = _emitted_for('rec-apply-log')
        assert len(messages) == 1
        assert 'frozen_manifest_stale' in messages[0]
        assert GHOST in messages[0]


# =============================================================================
# The fail-loud direction — live config still wants a step whose doc is gone
# =============================================================================


class TestBrokenStepStillFailsLoud:
    def test_unloadable_step_still_in_live_config_is_an_error(self, plan_context):
        """The ORIGINAL motivating failure keeps its hard fail.

        The plan deleted the standards doc but did NOT sweep marshal.json, so
        live config still schedules a step that cannot run. Reconciling that
        away would silently drop work the project still asks for.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest('rec-broken', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-broken'))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'unreconcilable_step'
        assert result['broken'] == [GHOST]

    def test_broken_step_message_is_the_canonical_actionable_phrasing(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [GHOST])
        _seed_manifest('rec-broken-msg', [GHOST], candidate_steps=[GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-broken-msg'))
        assert 'missing standards file' in result['message']
        assert 'deleted the file without sweeping' in result['message']

    def test_broken_step_is_not_applied(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest('rec-broken-apply', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-broken-apply', apply=True))
        assert GHOST in read_manifest('rec-broken-apply')['phase_6']['steps'], (
            'a failing reconcile must write nothing'
        )


# =============================================================================
# The backfill direction — narrow by construction
# =============================================================================


class TestBackfillIsNarrow:
    def test_candidate_new_since_compose_is_backfilled(self, plan_context):
        """REAL_B entered live config AFTER this manifest was composed."""
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-backfill', [REAL_A], candidate_steps=[REAL_A])

        result = cmd_reconcile(_reconcile_ns('rec-backfill', apply=True))
        assert result['status'] == 'success'
        assert result['backfill'] == [REAL_B]
        assert REAL_B in read_manifest('rec-backfill')['phase_6']['steps']

    def test_matrix_dropped_candidate_is_not_re_added(self, plan_context):
        """The decision matrix saw REAL_B and dropped it — that must stand.

        This is the whole reason ``candidate_steps`` is snapshotted. Without
        it, "in live config but not in the manifest" would re-add every step
        the matrix deliberately subtracted, defeating the composer.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-matrix', [REAL_A], candidate_steps=[REAL_A, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-matrix', apply=True))
        assert result['backfill'] == []
        assert REAL_B not in read_manifest('rec-matrix')['phase_6']['steps'], (
            'a candidate the matrix already considered and dropped must not '
            'be resurrected by reconcile'
        )

    def test_absent_candidate_snapshot_reports_indeterminate(self, plan_context):
        """A manifest frozen before ``candidate_steps` existed cannot be diffed.

        Fail closed: report that backfill could not be determined rather than
        guessing a set that would re-add matrix-dropped steps.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-legacy', [REAL_A], candidate_steps=None)

        result = cmd_reconcile(_reconcile_ns('rec-legacy', apply=True))
        assert result['status'] == 'success'
        assert result['backfill_determinable'] is False
        assert result['backfill'] == []
        assert REAL_B not in read_manifest('rec-legacy')['phase_6']['steps']

    def test_drop_still_works_without_a_candidate_snapshot(self, plan_context):
        """The drop direction needs no snapshot — only loadability and live config."""
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-legacy-drop', [REAL_A, GHOST], candidate_steps=None)

        result = cmd_reconcile(_reconcile_ns('rec-legacy-drop', apply=True))
        assert result['stale'] == [GHOST]
        assert GHOST not in read_manifest('rec-legacy-drop')['phase_6']['steps']


# =============================================================================
# Key canonicalization across the frozen/live boundary
# =============================================================================


class TestPrefixedFrozenIdsCompareCanonically:
    def test_prefixed_frozen_step_is_not_dropped_when_live_lists_it_bare(
        self, plan_context
    ):
        """A hand-edited manifest may carry `default:`-prefixed ids.

        SKILL.md explicitly sanctions editing execution.toon directly, so the
        frozen list can hold a prefixed id while the live candidate set is
        boundary-normalized. Comparing raw would read the prefixed id as absent
        from live config and drop a step live config still schedules.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest(
            'rec-prefixed', [REAL_A, f'default:{GHOST}'], candidate_steps=[REAL_A, GHOST]
        )

        result = cmd_reconcile(_reconcile_ns('rec-prefixed'))
        assert result['status'] == 'error', (
            'live config still lists the step, so a prefixed frozen id must be '
            'BROKEN (fail loud), never silently dropped as stale'
        )
        assert result['error'] == 'unreconcilable_step'

    def test_prefixed_frozen_step_is_not_backfilled_as_a_duplicate(self, plan_context):
        """A prefixed frozen id must not read as "absent from the manifest"."""
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-dup', [REAL_A, f'default:{REAL_B}'], candidate_steps=[REAL_A])

        result = cmd_reconcile(_reconcile_ns('rec-dup', apply=True))
        assert result['backfill'] == [], (
            f'{REAL_B} is already in the manifest under a prefixed id; '
            'backfilling it would duplicate the step'
        )


# =============================================================================
# Fail-closed when live config cannot be read at all
# =============================================================================


class TestUnreadableLiveConfigFailsClosed:
    def test_no_marshal_treats_unloadable_as_broken(self, plan_context):
        """With no live config there is no evidence the step was dropped.

        Absence of evidence is not evidence of absence: without a live
        candidate set the run cannot tell "config dropped it" from "config
        still wants it", so it keeps today's hard fail rather than inventing a
        clean verdict.
        """
        _seed_manifest('rec-nomarshal', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-nomarshal'))
        assert result['status'] == 'error'
        assert result['error'] == 'unreconcilable_step'
        assert result['candidate_source'] == 'unavailable'


# =============================================================================
# The no-divergence case
# =============================================================================


class TestConvergedManifestIsANoop:
    def test_converged_manifest_reports_no_changes(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-noop', [REAL_A, REAL_B], candidate_steps=[REAL_A, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-noop', apply=True))
        assert result['status'] == 'success'
        assert result['stale'] == []
        assert result['broken'] == []
        assert result['backfill'] == []
        assert result['reconciled'] is False, (
            'a converged manifest is not a reconciliation'
        )

    def test_missing_manifest_returns_file_not_found(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        result = cmd_reconcile(_reconcile_ns('rec-absent'))
        assert result is None or result.get('error') == 'file_not_found'


# =============================================================================
# compose writes the candidate snapshot reconcile depends on
# =============================================================================


class TestComposeSnapshotsCandidateSteps:
    def test_compose_records_the_candidate_set_it_selected_from(self, plan_context):
        cmd_compose(
            Namespace(
                plan_id='rec-compose',
                change_type='feature',
                track='complex',
                scope_estimate='multi_module',
                recipe_key=None,
                affected_files_count=5,
                phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
                phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
                commit_and_push=None,
            )
        )
        manifest = read_manifest('rec-compose')
        candidates = manifest['phase_6'].get('candidate_steps')
        assert candidates, 'compose must snapshot the phase-6 candidate set'
        selected = manifest['phase_6']['steps']
        assert set(selected).issubset(set(candidates)), (
            'every selected step must come from the recorded candidate set'
        )
