# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``migrate-review-steps`` sub-step of the marshall-steward upgrade.

The retired structural self-review finalize step was split into the functional
review and the code review, each switched by its own setting. The migration
replaces the retired entry in ``plan.phase-6-finalize.steps`` in place by the two
successors and carries its setting to both. This module is one of the four files
that name the retired step id and the retired ``self_review`` key — every mention
here is a migration INPUT, never a live step id or a live gate key.

The fixtures are exhaustive over the input shapes the request names: the retired
entry with a lane and a retired param, with ``lane: minimal``, with ``lane: off``,
with a legacy ``self_review`` run-at-all value, in both spellings at once, absent,
already migrated, beside a successor the operator already configured, and named
only in ``removed_steps``.
Exactly two of them — the absent and the already-migrated configuration — are
no-ops; every other one reports a migration.

The setting a successor ends up with is checked against the composer's own
gate-reading tables (``_manifest_rules``), not against a restated mapping, so the
claim "both settings resolve to off" is a statement about what the composer will
actually do with the migrated config.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _manifest_rules
import pytest
import upgrade
from _config_defaults import OPERATOR_REMOVED_STEPS_KEY
from toon_parser import parse_toon

_LEGACY = 'default:pre-submission-self-review'
_LEGACY_BARE = 'pre-submission-self-review'
_FUNCTIONAL = 'default:functional-review'
_CODE = 'default:code-review'

#: The two settings, by gate key, and the step that owns each — read off the
#: composer so a rename of either owner cannot leave this suite checking a step
#: the composer no longer reads.
_SETTINGS = ('functional_review', 'code_review')


def _section(steps: dict, removed: list[str] | None = None) -> dict:
    section: dict = {'steps': steps}
    if removed is not None:
        section[OPERATOR_REMOVED_STEPS_KEY] = removed
    return section


def _resolved_setting(section: dict, gate: str) -> str:
    """The ceremony decision the composer derives for ``gate`` from the migrated section."""
    owner = _manifest_rules._CEREMONY_GATE_OWNER_STEP[gate]
    lane = (section['steps'].get(owner) or {}).get('lane')
    if not isinstance(lane, str):
        return _manifest_rules._CEREMONY_FINALIZE_DEFAULT
    return _manifest_rules._LANE_TO_CEREMONY_VALUE.get(lane, _manifest_rules._CEREMONY_FINALIZE_DEFAULT)


def test_the_two_settings_are_owned_by_the_two_successors():
    """Premise of every setting assertion below, asserted rather than assumed."""
    assert {_manifest_rules._CEREMONY_GATE_OWNER_STEP[gate] for gate in _SETTINGS} == {_FUNCTIONAL, _CODE}


# =============================================================================
# The input shapes
# =============================================================================


def test_retired_entry_with_lane_and_retired_param_is_replaced_in_place():
    """Both successors, lane carried, the retired param dropped, position kept."""
    section = _section(
        {
            'default:finalize-step-security-audit': {'lane': 'full'},
            _LEGACY: {'drop_review_on_scope_gate': False, 'lane': 'standard'},
            'default:architecture-refresh': {'lane': 'minimal'},
        }
    )

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert list(section['steps']) == [
        'default:finalize-step-security-audit',
        _FUNCTIONAL,
        _CODE,
        'default:architecture-refresh',
    ]
    assert section['steps'][_FUNCTIONAL] == {'lane': 'standard'}
    assert section['steps'][_CODE] == {'lane': 'standard'}
    assert report['replaced'] == [_LEGACY]
    assert report['added'] == [_FUNCTIONAL, _CODE]
    assert report['dropped_params'] == ['drop_review_on_scope_gate=false']


def test_retired_entry_with_lane_minimal_forces_both_reviews_in():
    section = _section({_LEGACY: {'lane': 'minimal'}})

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert section['steps'] == {_FUNCTIONAL: {'lane': 'minimal'}, _CODE: {'lane': 'minimal'}}
    assert {gate: _resolved_setting(section, gate) for gate in _SETTINGS} == dict.fromkeys(_SETTINGS, 'always')


def test_legacy_self_review_never_turns_both_settings_off():
    """The retired run-at-all value is the same setting in its old spelling."""
    section = _section({_LEGACY: {'self_review': 'never', 'lane': 'standard'}})

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert {gate: _resolved_setting(section, gate) for gate in _SETTINGS} == dict.fromkeys(_SETTINGS, 'never')
    assert report['dropped_params'] == ['lane="standard"'], 'the overridden lane is reported, never lost silently'


def test_legacy_self_review_agreeing_with_the_lane_reports_nothing():
    """Control for the test above: a self_review value mapping to the entry's own lane drops nothing."""
    section = _section({_LEGACY: {'self_review': 'never', 'lane': 'off'}})

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert report['dropped_params'] == []


def test_lane_off_wins_over_a_legacy_self_review_always_in_one_entry():
    """``off`` wins inside one entry as it does across entries; the losing self_review is reported."""
    section = _section({_LEGACY: {'lane': 'off', 'self_review': 'always'}})

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert {gate: _resolved_setting(section, gate) for gate in _SETTINGS} == dict.fromkeys(_SETTINGS, 'never')
    assert report['dropped_params'] == ['self_review="always"']


def test_lane_off_in_one_spelling_survives_a_legacy_always_beside_it():
    """The reported failure shape: an entry's off lane must not lose to its own self_review: always."""
    section = _section(
        {_LEGACY: {'lane': 'off', 'self_review': 'always'}, _LEGACY_BARE: {'lane': 'standard'}},
    )

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert sorted(report['dropped_params']) == ['lane="standard"', 'self_review="always"']


def test_legacy_self_review_always_replaces_a_non_off_lane_and_reports_it():
    """Away from ``off`` the mapped self_review value wins, and the lane it replaced is reported."""
    section = _section({_LEGACY: {'lane': 'standard', 'self_review': 'always'}})

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'minimal'}, _CODE: {'lane': 'minimal'}}
    assert report['dropped_params'] == ['lane="standard"']


def test_legacy_self_review_auto_leaves_the_carried_lane_in_force():
    """Control for the test above: ``auto`` maps to no lane, so the carried one stands."""
    section = _section({_LEGACY: {'self_review': 'auto', 'lane': 'minimal'}})

    upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'minimal'}, _CODE: {'lane': 'minimal'}}


def test_retired_entry_with_lane_off_turns_both_settings_off():
    section = _section({_LEGACY_BARE: {'lane': 'off'}})

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert report['replaced'] == [_LEGACY_BARE]
    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert {gate: _resolved_setting(section, gate) for gate in _SETTINGS} == dict.fromkeys(_SETTINGS, 'never')


@pytest.mark.parametrize(
    'steps',
    [
        {_LEGACY: {'lane': 'standard', 'drop_review_on_scope_gate': True}, _LEGACY_BARE: {'lane': 'off'}},
        {_LEGACY_BARE: {'lane': 'off'}, _LEGACY: {'lane': 'standard', 'drop_review_on_scope_gate': True}},
    ],
    ids=['off-on-second-key', 'off-on-first-key'],
)
def test_both_retired_spellings_merge_and_an_off_lane_on_either_wins(steps):
    """No retired entry's setting is lost: ``off`` wins, the losing lane and every other param are reported."""
    section = _section(steps)

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'off'}, _CODE: {'lane': 'off'}}
    assert {gate: _resolved_setting(section, gate) for gate in _SETTINGS} == dict.fromkeys(_SETTINGS, 'never')
    assert sorted(report['replaced']) == sorted([_LEGACY, _LEGACY_BARE])
    assert sorted(report['dropped_params']) == ['drop_review_on_scope_gate=true', 'lane="standard"']


def test_both_retired_spellings_without_a_conflict_carry_the_shared_lane():
    """Control for the test above: equal lanes are carried once and nothing is reported as dropped."""
    section = _section({_LEGACY: {'lane': 'minimal'}, _LEGACY_BARE: {'lane': 'minimal'}})

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'minimal'}, _CODE: {'lane': 'minimal'}}
    assert report['dropped_params'] == []


def test_absent_retired_entry_is_a_noop():
    steps = {'default:push': {'lane': 'minimal'}}
    section = _section(dict(steps))

    report = upgrade.migrate_review_steps(section)

    assert report == {'state': 'noop'}
    assert section == {'steps': steps}


def test_already_migrated_configuration_is_a_noop():
    """A second run over its own output changes nothing — the migration self-disarms."""
    section = _section({_LEGACY: {'lane': 'standard'}}, removed=[_LEGACY])

    first = upgrade.migrate_review_steps(section)
    after_first = json.loads(json.dumps(section))
    second = upgrade.migrate_review_steps(section)

    assert first['state'] == 'migrated'
    assert second == {'state': 'noop'}
    assert section == after_first


def test_operator_configured_successor_wins():
    """A successor the operator already configured keeps its own params and position."""
    section = _section(
        {
            _FUNCTIONAL: {'lane': 'full'},
            _LEGACY: {'lane': 'standard', 'drop_review_on_scope_gate': True},
            'default:push': {'lane': 'minimal'},
        }
    )

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert report['kept'] == [_FUNCTIONAL]
    assert report['added'] == [_CODE]
    assert section['steps'] == {
        _FUNCTIONAL: {'lane': 'full'},
        _CODE: {'lane': 'standard'},
        'default:push': {'lane': 'minimal'},
    }
    assert list(section['steps']) == [_FUNCTIONAL, _CODE, 'default:push']


def test_both_successors_configured_only_removes_the_retired_entry():
    """With both successors present nothing is inserted; the retired lane is reported as dropped, not lost."""
    section = _section({_FUNCTIONAL: {'lane': 'standard'}, _CODE: {'lane': 'standard'}, _LEGACY: {'lane': 'off'}})

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert report['added'] == []
    assert report['kept'] == [_FUNCTIONAL, _CODE]
    assert report['carried'] == []
    assert report['dropped_params'] == ['lane="off"']
    assert section['steps'] == {_FUNCTIONAL: {'lane': 'standard'}, _CODE: {'lane': 'standard'}}


def test_one_successor_configured_carries_and_drops_nothing_extra():
    """Control for the test above: with a successor inserted the lane is carried, not reported as dropped."""
    section = _section({_FUNCTIONAL: {'lane': 'standard'}, _LEGACY: {'lane': 'off'}})

    report = upgrade.migrate_review_steps(section)

    assert report['added'] == [_CODE]
    assert report['carried'] == ['lane=off']
    assert report['dropped_params'] == []


@pytest.mark.parametrize(
    ('params', 'expected_dropped'),
    [
        ({'self_review': 'off', 'lane': 'standard'}, ['self_review="off"']),
        ({'lane': 3}, ['lane=3']),
        ({'lane': ''}, ['lane=""']),
    ],
    ids=['unknown-self-review-value', 'non-string-lane', 'empty-lane'],
)
def test_unusable_lane_or_self_review_values_are_reported_as_dropped(params, expected_dropped):
    """A setting the migration cannot map is reported, never discarded silently."""
    section = _section({_LEGACY: params})

    report = upgrade.migrate_review_steps(section)

    assert report['dropped_params'] == expected_dropped


def test_the_carried_lane_is_never_also_reported_as_dropped():
    """A lane one entry lost but another carried to the win is carried, not reported as dropped."""
    section = _section(
        {_LEGACY: {'lane': 'standard'}, _LEGACY_BARE: {'lane': 'standard', 'self_review': 'always'}},
    )

    report = upgrade.migrate_review_steps(section)

    assert section['steps'] == {_FUNCTIONAL: {'lane': 'standard'}, _CODE: {'lane': 'standard'}}
    assert report['dropped_params'] == ['lane="minimal"']


def test_both_successors_configured_reports_each_dropped_setting_once():
    """With both successors configured the carried lane is reported as dropped exactly once."""
    section = _section(
        {
            _FUNCTIONAL: {'lane': 'full'},
            _CODE: {'lane': 'full'},
            _LEGACY: {'lane': 'standard'},
            _LEGACY_BARE: {'lane': 'standard', 'self_review': 'always'},
        }
    )

    report = upgrade.migrate_review_steps(section)

    assert sorted(report['dropped_params']) == ['lane="minimal"', 'lane="standard"']


def test_legacy_self_review_auto_is_not_reported_as_dropped():
    """Control for the test above: ``auto`` is a recognised value that maps to no lane."""
    section = _section({_LEGACY: {'self_review': 'auto'}})

    report = upgrade.migrate_review_steps(section)

    assert report['dropped_params'] == []


def test_retired_id_in_removed_steps_is_replaced_by_both_new_ids():
    """A review the operator removed stays removed under its new names."""
    section = _section({'default:push': {'lane': 'minimal'}}, removed=['default:adr-propose', _LEGACY])

    report = upgrade.migrate_review_steps(section)

    assert report['state'] == 'migrated'
    assert report['removed_steps_rewritten'] is True
    assert report['replaced'] == []
    assert section[OPERATOR_REMOVED_STEPS_KEY] == ['default:adr-propose', _FUNCTIONAL, _CODE]
    assert section['steps'] == {'default:push': {'lane': 'minimal'}}


# =============================================================================
# The verb against a real marshal.json on disk
# =============================================================================


def _stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict) -> Path:
    """Write ``config`` to a sandbox marshal.json and point the loader at it.

    ``_config_core.MARSHAL_PATH`` is resolved once at import time, so the module
    attribute is re-bound rather than relying on a ``chdir``.
    """
    import _config_core

    marshal = tmp_path / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    marshal.write_text(json.dumps(config, indent=2), encoding='utf-8')
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', marshal)
    return marshal


def _config(steps: dict) -> dict:
    return {'plan': {'phase-6-finalize': {'steps': steps}}}


class TestMigrateReviewStepsVerb:
    def test_verb_migrates_the_file_and_a_rerun_leaves_it_byte_identical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        marshal = _stage(tmp_path, monkeypatch, _config({_LEGACY: {'lane': 'standard'}}))

        first = upgrade.cmd_migrate_review_steps(argparse.Namespace())
        written = marshal.read_bytes()
        second = upgrade.cmd_migrate_review_steps(argparse.Namespace())

        assert first['status'] == 'success'
        assert first['state'] == 'migrated'
        steps = json.loads(written)['plan']['phase-6-finalize']['steps']
        assert steps == {_FUNCTIONAL: {'lane': 'standard'}, _CODE: {'lane': 'standard'}}
        assert second['state'] == 'noop'
        assert marshal.read_bytes() == written

    def test_a_noop_never_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        marshal = _stage(tmp_path, monkeypatch, _config({'default:push': {'lane': 'minimal'}}))
        before = marshal.read_bytes()

        result = upgrade.cmd_migrate_review_steps(argparse.Namespace())

        assert result['state'] == 'noop'
        assert marshal.read_bytes() == before

    def test_verb_is_a_noop_on_an_uninitialized_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import _config_core

        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', tmp_path / '.plan' / 'marshal.json')

        result = upgrade.cmd_migrate_review_steps(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'
        assert 'marshal.json' in result['detail']

    def test_verb_is_a_noop_without_a_finalize_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _stage(tmp_path, monkeypatch, {'plan': {}})

        result = upgrade.cmd_migrate_review_steps(argparse.Namespace())

        assert result['state'] == 'noop'
        assert 'phase-6-finalize' in result['detail']

    def test_verb_is_reachable_from_the_constructed_argv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """The CLI entry point routes ``migrate-review-steps`` to the verb."""
        _stage(tmp_path, monkeypatch, _config({_LEGACY: {'lane': 'off'}}))
        monkeypatch.setattr(sys, 'argv', ['upgrade', 'migrate-review-steps'])

        with pytest.raises(SystemExit) as excinfo:
            upgrade.main()
        parsed = parse_toon(capsys.readouterr().out)

        assert int(excinfo.value.code or 0) == 0
        assert parsed['operation'] == 'migrate-review-steps'
        assert parsed['state'] == 'migrated'
