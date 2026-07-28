#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end landing suite for the retired ``enabled_bots`` auto-map.

Cross-cutting counterpart to ``test_upgrade.py``, which owns the pure
:func:`migrate_bot_lists` function's four input states. This suite pins the
LANDING — that a project which only ever configured the legacy single list still
has the SAME bots gating the participation quorum after the migration runs, and
that re-running the upgrade never disturbs a settled value.

Two properties, both end-to-end from a project fixture through the migration and
into ``review_completeness``:

1. **Semantics survive the migration.** Every bot on the legacy list was awaited,
   and awaiting is exactly what ``required`` means — so the legacy bots must still
   gate ``participation_complete`` afterwards, with none silently demoted to
   optional (where its silence would stop blocking).
2. **The migration is self-disarming.** A second run leaves the migrated values
   untouched, and a subsequent operator answer is never re-seeded over.

Every expectation is DERIVED from the fixture's own legacy value — never a
literal — so changing the fixture cannot leave a stale expectation passing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conftest import get_script_path

_STEWARD_SCRIPTS = get_script_path('plan-marshall', 'marshall-steward', 'upgrade.py').parent
_AR_SCRIPTS = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py').parent

for _dir in (_STEWARD_SCRIPTS, _AR_SCRIPTS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import bot_registry  # noqa: E402
import review_completeness as rc  # noqa: E402
import upgrade  # noqa: E402

_AUTOMATIC_REVIEW_STEP_ID = 'plan-marshall:automatic-review'

# The fixture's legacy configuration. Every expectation below is derived from THIS
# value rather than restated, so the suite cannot drift away from its own fixture.
_LEGACY_BOTS = 'coderabbit,sourcery'


def _legacy_project_config() -> dict:
    """A marshal.json carrying ONLY the retired single-list knob."""
    return {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    _AUTOMATIC_REVIEW_STEP_ID: {
                        'enabled_bots': _LEGACY_BOTS,
                        'review_bot_buffer_seconds': 180,
                    }
                }
            }
        }
    }


def _expected_required() -> list[str]:
    """The bots the legacy list awaited, derived from the fixture value."""
    return [b.strip() for b in _LEGACY_BOTS.split(',') if b.strip()]


def _step_params(config: dict) -> dict:
    params: dict = config['plan']['phase-6-finalize']['steps'][_AUTOMATIC_REVIEW_STEP_ID]
    return params


class TestLegacySemanticsSurviveTheMigration:
    """The same bots still gate the quorum after the auto-map runs."""

    def test_legacy_bots_land_on_required_not_optional(self):
        """Awaiting is what ``required`` means, so the legacy list seeds required.

        Seeding OPTIONAL instead would silently drop every legacy bot's gating
        power — the config would look migrated while the quorum quietly stopped
        blocking on the bots the project had always awaited.
        """
        config = _legacy_project_config()
        report = upgrade.migrate_bot_lists(_step_params(config))

        assert report['state'] == 'migrated'
        assert report['required_bots'] == _LEGACY_BOTS
        assert report['optional_bots'] == ''

    def test_the_same_bots_still_gate_the_quorum_end_to_end(self, plan_context):
        """Drive the migrated values into the real predicate and compare gating.

        The end-to-end assertion: with none of the legacy bots proven, every one
        of them still blocks after the migration — exactly as it did when the
        single list awaited them.
        """
        plan_id = 'lbm-gating-preserved'
        plan_context.plan_dir_for(plan_id)

        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)

        required = [b.strip() for b in params['required_bots'].split(',') if b.strip()]
        optional = [b.strip() for b in params['optional_bots'].split(',') if b.strip()]
        assert required == _expected_required()

        result = rc.check_completeness(plan_id, required, optional_bots=optional)

        assert result['participation_complete'] is False
        assert result['unproven_bots'] == _expected_required()

    def test_no_legacy_bot_is_silently_demoted_to_non_gating(self, plan_context):
        """The counterpart: prove each legacy bot individually still blocks.

        A per-bot sweep rather than an aggregate, so a migration that demoted ONE
        bot to optional cannot hide behind a still-false aggregate verdict driven
        by its siblings.
        """
        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)
        required = [b.strip() for b in params['required_bots'].split(',') if b.strip()]

        for index, bot in enumerate(required):
            plan_id = f'lbm-demotion-{index}'
            plan_context.plan_dir_for(plan_id)
            # Prove every OTHER bot, so only this one can be the blocker.
            proven = {
                other: bot_registry.participation_evidence(other)[0]
                for other in required
                if other != bot
            }

            result = rc.check_completeness(plan_id, required, participated_bots=proven)

            assert result['participation_complete'] is False, bot
            assert result['unproven_bots'] == [bot]

    def test_the_retired_key_is_removed_not_merely_shadowed(self):
        """A surviving ``enabled_bots`` would be a second, stale source of truth."""
        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)

        assert 'enabled_bots' not in params

    def test_provenance_records_that_this_was_not_an_operator_answer(self):
        """``migrated`` is distinct from ``answered`` — the operator was never asked.

        The distinction is what lets a later operator answer overwrite a migrated
        value while leaving an answered one alone.
        """
        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)

        assert params['bot_lists_provenance'] == 'migrated'


class TestSelfDisarming:
    """Re-running the upgrade is always safe."""

    def test_second_run_leaves_migrated_values_untouched(self):
        """The migration disarms itself once the legacy key is gone."""
        config = _legacy_project_config()
        params = _step_params(config)

        first = upgrade.migrate_bot_lists(params)
        after_first = dict(params)

        second = upgrade.migrate_bot_lists(params)

        assert first['state'] == 'migrated'
        assert second['state'] == 'noop'
        assert params == after_first

    def test_repeated_runs_converge(self):
        """Idempotence beyond the second run — no slow drift across upgrades."""
        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)
        settled = dict(params)

        for _ in range(3):
            report = upgrade.migrate_bot_lists(params)
            assert report['state'] == 'noop'
            assert params == settled

    def test_a_subsequent_operator_answer_is_never_re_seeded_over(self):
        """The operator's answer wins, and a later upgrade does not overwrite it.

        This is the property that makes the migration safe to leave wired into the
        upgrade verb permanently: once a human has answered, no amount of
        re-running can revert their answer to the legacy mapping.
        """
        config = _legacy_project_config()
        params = _step_params(config)
        upgrade.migrate_bot_lists(params)

        # The operator answers, deliberately reclassifying one bot as optional.
        legacy_bots = _expected_required()
        params['required_bots'] = legacy_bots[0]
        params['optional_bots'] = ','.join(legacy_bots[1:])
        params['bot_lists_provenance'] = 'answered'
        answered = dict(params)

        for _ in range(3):
            upgrade.migrate_bot_lists(params)

        assert params == answered

    def test_an_operator_answer_predating_the_migration_wins(self):
        """A legacy key alongside an existing answer discards the LEGACY value.

        The operator answered before the upgrade ran, so their answer is kept and
        only the stale legacy key is dropped — provenance is NOT downgraded.
        """
        config = _legacy_project_config()
        params = _step_params(config)
        params['required_bots'] = _expected_required()[0]
        params['bot_lists_provenance'] = 'answered'

        report = upgrade.migrate_bot_lists(params)

        assert report['state'] == 'operator_answer_kept'
        assert report['discarded_legacy'] == _LEGACY_BOTS
        assert params['required_bots'] == _expected_required()[0]
        assert params['bot_lists_provenance'] == 'answered'
        assert 'enabled_bots' not in params


class TestLiveConfigVerb:
    """The CLI verb against a real marshal.json on disk."""

    @staticmethod
    def _stage_marshal_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict) -> Path:
        """Write ``config`` to a sandbox marshal.json and point the loader at it.

        ``_config_core.MARSHAL_PATH`` is resolved ONCE at import time, so a bare
        ``chdir`` into a staged project does not redirect the loader — the verb
        would keep reading (and writing) whatever path the process started with.
        Re-binding the module attribute is what makes this an end-to-end test of the
        real read-modify-write rather than a test of a path that is never read.
        """
        import _config_core

        marshal = tmp_path / '.plan' / 'marshal.json'
        marshal.parent.mkdir(parents=True, exist_ok=True)
        marshal.write_text(json.dumps(config), encoding='utf-8')
        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', marshal)
        return marshal

    @pytest.fixture
    def legacy_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Stage a project whose marshal.json carries only the legacy knob."""
        return self._stage_marshal_json(tmp_path, monkeypatch, _legacy_project_config())

    def test_verb_writes_the_migrated_config_back_to_disk(self, legacy_project: Path):
        """The end-to-end landing: the file on disk carries the two-list model."""
        import argparse

        result = upgrade.cmd_migrate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'migrated'

        persisted = _step_params(json.loads(legacy_project.read_text(encoding='utf-8')))
        assert persisted['required_bots'] == _LEGACY_BOTS
        assert persisted['optional_bots'] == ''
        assert 'enabled_bots' not in persisted

    def test_verb_is_a_noop_success_on_a_project_without_the_step(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A project with no automatic-review step configured is not a failure."""
        import argparse

        self._stage_marshal_json(tmp_path, monkeypatch, {'plan': {}})

        result = upgrade.cmd_migrate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'

    def test_verb_is_a_noop_success_on_an_uninitialized_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """No marshal.json at all is a typed no-op, never an escaping FileNotFoundError.

        The migration runs as a sub-step of the steward upgrade flow, which can be
        pointed at a project that was never initialized. An un-initialized project
        has no legacy ``enabled_bots`` value to migrate, so the honest answer is a
        no-op success — not a traceback out of a CLI verb.
        """
        import argparse

        import _config_core

        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', tmp_path / '.plan' / 'marshal.json')

        result = upgrade.cmd_migrate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'
        assert 'marshal.json' in result['detail']
