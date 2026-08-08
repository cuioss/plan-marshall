#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioural regression suite for the lesson-store fail-open directions.

Each case here was run against the PRE-FIX code and observed to FAIL; each is
green against the post-fix code. That red-then-green observation is the point:
a regression test written only after the fix cannot prove it was ever guarding
anything.

The shared root cause is a store resolution whose *could-not-look* outcome was
indistinguishable from a real zero, so a stranded lesson reported as a clean
corpus. Two directions fall out of it, and both are covered:

- **could-not-look reports benign** — the site never reached the store but
  returned the same answer it gives for a store it read and found empty.
- **looked in the wrong store** — the site resolved through a cwd-keyed
  resolver, so it read or wrote a different, ephemeral corpus.

Every case states in its docstring the premise that distinguishes it from its
nearest sibling in the deliverable-1 unit suites, so no case here merely
restates an assertion made there. The site-by-site population and dispositions
live in
``marketplace/bundles/plan-marshall/skills/manage-lessons/standards/cwd-keyed-store-resolution-audit.md``.
"""

from argparse import Namespace
from unittest.mock import patch

from _lessons_helpers import cmd_list_stalled, cmd_restore_from_plan

from conftest import load_script_module

_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_fail_open_cmd_lifecycle'
)
cmd_delete_plan = _lifecycle.cmd_delete_plan


def _write_carried_lesson(plan_dir, lesson_id: str, body: str = 'Body.\n') -> None:
    """Write a relocated ``lesson-{id}.md`` into ``plan_dir``."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / f'lesson-{lesson_id}.md').write_text(
        f'id={lesson_id}\ncomponent=test\ncategory=bug\ncreated=2025-01-01\n\n'
        f'# Lesson {lesson_id}\n\n{body}',
        encoding='utf-8',
    )


def _write_plan_status(plan_dir, current_phase: str, phase_status: str, plan_source=None) -> None:
    """Write a minimal ``status.json`` beside a carried lesson.

    ``plan_source`` is omitted entirely when ``None`` — that unset shape is the
    live ``convert-to-plan`` case that case (b) reproduces.
    """
    import json

    metadata: dict = {}
    if plan_source is not None:
        metadata['plan_source'] = plan_source
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'current_phase': current_phase,
                'phases': [{'name': current_phase, 'status': phase_status}],
                'metadata': metadata,
            }
        ),
        encoding='utf-8',
    )


class TestOverridePredicateMirroring:
    """The override predicate is MIRRORED across its sites, not shared.

    ``_lessons_io.resolve_lesson_store`` decides ``override`` vs
    ``main_anchored`` by re-evaluating the condition
    ``marketplace_paths.resolve_main_anchored_path`` branches on
    (``PLAN_BASE_DIR`` set, or a ``file_ops.set_base_dir()`` override
    installed). The two are textually identical COPIES, not one shared
    predicate, so nothing structural stops them drifting apart — and the drift
    is silent in the worst way: the handle would report a provenance the
    returned path does not have, which is the resolved-value-for-a-substrate-we-
    did-not-reach failure the whole ``STORE_RESOLUTIONS`` contract exists to
    make impossible.

    These cases are the guard that keeps the copies honest — one per disjunct
    of the condition, plus the negative arm. Each asserts the two sites agree
    by comparing the handle's reported path against the resolver's own return,
    so a divergence in either copy fails here rather than surfacing as a
    mislabelled store much later.
    """

    def test_env_override_makes_both_sites_take_the_override_branch(
        self, tmp_path, monkeypatch
    ):
        """The ``PLAN_BASE_DIR`` disjunct: both sites read it, and agree."""
        import _lessons_io
        import file_ops
        from marketplace_paths import resolve_main_anchored_path

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None, raising=False)
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        store = _lessons_io.resolve_lesson_store()
        resolved = resolve_main_anchored_path(_lessons_io.DIR_LESSONS)

        assert store.resolution == 'override'
        assert resolved == tmp_path / _lessons_io.DIR_LESSONS
        assert store.path == resolved, (
            'The handle reported a different path than the resolver returned — '
            'the two copies of the override condition have drifted.'
        )

    def test_set_base_dir_override_makes_both_sites_take_the_override_branch(
        self, tmp_path, monkeypatch
    ):
        """The ``set_base_dir()`` disjunct, with ``PLAN_BASE_DIR`` unset.

        Covered separately because the condition is a two-term disjunction: a
        copy that dropped one term would still pass the env-var case above.
        """
        import _lessons_io
        import file_ops
        from marketplace_paths import resolve_main_anchored_path

        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', tmp_path, raising=False)

        store = _lessons_io.resolve_lesson_store()
        resolved = resolve_main_anchored_path(_lessons_io.DIR_LESSONS)

        assert store.resolution == 'override'
        assert store.path == resolved

    def test_no_override_makes_both_sites_take_the_main_anchored_branch(
        self, monkeypatch
    ):
        """The negative arm: neither term set, so both sites go to git.

        Without this the pair could agree only because both always report
        ``override`` — the arms must disagree with each other, or the mirroring
        assertion carries no information.
        """
        import _lessons_io
        import file_ops
        from marketplace_paths import (
            PLAN_DIR_NAME,
            main_checkout_root,
            resolve_main_anchored_path,
        )

        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None, raising=False)

        store = _lessons_io.resolve_lesson_store()
        resolved = resolve_main_anchored_path(_lessons_io.DIR_LESSONS)

        assert store.resolution == 'main_anchored'
        assert resolved == (
            main_checkout_root() / PLAN_DIR_NAME / 'local' / _lessons_io.DIR_LESSONS
        )
        assert store.path == resolved


class TestRestoreFromPlanWrongStoreArm:
    """(a) The wrong-store arm of ``restore-from-plan``."""

    def test_worktree_resident_plan_dir_is_not_reported_as_lesson_free(self, tmp_path):
        """A plan dir that EXISTS off the main-anchored root is not ``no_lesson_file``.

        **Observed RED against the pre-fix code**: it returned
        ``status: success`` with ``action: no_lesson_file``.

        **Distinguishing premise vs its deliverable-1 sibling**
        (``test_restore_from_plan.py::test_restore_from_plan_missing_plan_dir``):
        that case exercises the *absent-directory* arm — there is nothing
        anywhere to resolve. This case exercises the *wrong-store* arm: the plan
        directory exists on disk **and holds a lesson**, but it lives under a
        worktree-resident base rather than the main-anchored plans root the verb
        resolves. The two arms enter the same outcome from opposite premises, so
        a fix that corrected only the absence branch would still leave this one
        red.
        """
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)

        # The plan directory really exists — just not under the main-anchored
        # plans root the verb resolves through.
        worktree_plan_dir = tmp_path / 'worktree' / '.plan' / 'local' / 'plans' / 'live-plan'
        _write_carried_lesson(worktree_plan_dir, '2025-01-01-12-001')
        assert (worktree_plan_dir / 'lesson-2025-01-01-12-001.md').exists()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(main_base)}):
            result = cmd_restore_from_plan(Namespace(plan_id='live-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_unresolved'
        assert result['action'] == 'plan_dir_unresolved'
        assert result['action'] != 'no_lesson_file'
        assert result['restored_count'] == 0

        # The lesson is untouched in the store the verb did not reach.
        assert (worktree_plan_dir / 'lesson-2025-01-01-12-001.md').exists()


class TestListStalledUnsetPlanSourceArm:
    """(b) The population arm of ``list-stalled``."""

    def test_plan_with_unset_plan_source_is_reported(self, tmp_path):
        """A carried lesson is found even when ``plan_source`` was never written.

        **Observed RED against the pre-fix code**: ``stalled_count: 0`` — the
        plan was filtered out of the population before classification.

        **Distinguishing premise vs its deliverable-1 sibling**
        (``test_list_stalled.py::test_plan_with_unset_plan_source_is_reported``):
        the sibling writes an EMPTY-STRING ``plan_source`` through the suite's
        fixture helper, which always emits the key. This case reproduces the
        live ``convert-to-plan`` shape exactly — ``metadata`` carries no
        ``plan_source`` key at all — so it also covers the missing-key read
        path rather than only the empty-value one.
        """
        base = tmp_path / '.plan' / 'local'
        plan_dir = base / 'plans' / 'converted-plan'
        _write_carried_lesson(plan_dir, '2025-02-02-13-002')
        _write_plan_status(plan_dir, '5-execute', 'in_progress', plan_source=None)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(base)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['plans_root_state'] == 'present'
        assert result['stalled_count'] == 1
        assert result['stalled_plans'][0]['plan_id'] == 'converted-plan'


class TestListStalledDuplicationDirection:
    """(c) The inverse (duplication) direction of ``list-stalled``."""

    def test_duplicate_is_reported_distinctly_from_absence(self, tmp_path):
        """A carried id already in the corpus is its own outcome, not an absence.

        **Observed RED against the pre-fix code**: the verb had no duplication
        outcome at all — the payload carried no ``duplicate_count`` key, so the
        collision was invisible and a caller would drive
        ``restore-from-plan`` straight into ``destination_exists``.

        **Distinguishing premise vs its deliverable-1 sibling**
        (``test_list_stalled.py::test_duplicate_carried_lesson_is_reported_separately``):
        the sibling pins the duplicate row's SHAPE for a plan that is also
        stalled. This case pins the SEPARATION itself — a duplicate carried by a
        plan in a terminal phase, so ``stalled_count`` is 0 while
        ``duplicate_count`` is 1. Only this arrangement proves the duplication
        outcome is genuinely independent of the stalled classification rather
        than a field that merely rides along with it.
        """
        base = tmp_path / '.plan' / 'local'
        lessons_dir = base / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-03-03-14-003.md').write_text(
            'id=2025-03-03-14-003\n\n# Incumbent\n\nCorpus copy.\n', encoding='utf-8'
        )

        plan_dir = base / 'plans' / 'terminal-dup-plan'
        _write_carried_lesson(plan_dir, '2025-03-03-14-003')
        # Terminal phase → NOT stalled, so the two outcomes cannot be conflated.
        _write_plan_status(plan_dir, '6-finalize', 'done', plan_source='2025-03-03-14-003')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(base)}):
            result = cmd_list_stalled(Namespace())

        assert result['status'] == 'success'
        assert result['stalled_count'] == 0
        assert result['duplicate_count'] == 1
        duplicate = result['duplicate_lessons'][0]
        assert duplicate['plan_id'] == 'terminal-dup-plan'
        assert duplicate['lesson_id'] == '2025-03-03-14-003'


class TestDeletePlanCorpusLossDirection:
    """(e) The corpus-loss direction at the fourth store-resolution site."""

    def test_colliding_carried_lesson_survives_delete_plan(self, tmp_path, monkeypatch):
        """After ``delete-plan``, a colliding carried lesson is still readable somewhere.

        **Observed RED against the pre-fix code**: the collision was
        ``continue``-skipped in silence and the plan directory was deleted
        anyway, so the plan-local copy was destroyed and only the unrelated
        incumbent remained — the carried lesson's content was gone from disk.

        **Distinguishing premise vs its deliverable-1 siblings** (the outcome-code
        cases in ``test_manage_status_transition.py``): those assert the
        reported OUTCOME (``skipped_lessons``, ``lesson_carry_back_incomplete``).
        This case asserts **survival of the file's content** and makes no
        assertion about any outcome code. That is the only formulation that
        still fails if the fix reports the collision correctly but deletes the
        plan directory regardless — a report is not a rescue.
        """
        base = tmp_path / '.plan' / 'local'
        lessons_dir = base / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-04-04-15-004.md').write_text(
            'id=2025-04-04-15-004\n\n# Incumbent\n\nA DIFFERENT lesson body.\n', encoding='utf-8'
        )

        plan_dir = base / 'plans' / 'colliding-plan'
        carried_body = 'THE CARRIED BODY THAT MUST NOT VANISH.\n'
        _write_carried_lesson(plan_dir, '2025-04-04-15-004', body=carried_body)

        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        cmd_delete_plan(Namespace(plan_id='colliding-plan', no_restore_lessons=False))

        # The assertion is survival, not an outcome code: the carried body must
        # still be readable SOMEWHERE under the store after the call.
        surviving = [
            path.read_text(encoding='utf-8')
            for path in base.rglob('*.md')
        ]
        assert any(carried_body in text for text in surviving), (
            'The carried lesson body vanished from disk after delete-plan — the '
            'plan directory held the only copy and was deleted anyway.'
        )
