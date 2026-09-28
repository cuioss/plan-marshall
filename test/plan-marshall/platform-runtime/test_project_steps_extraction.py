# SPDX-License-Identifier: FSL-1.1-ALv2
"""The shared ``project:{skill}`` step reader (``runtime_base.extract_project_steps``).

Governs the reader every runtime delegates to, and the keyed-map ``steps`` shape
the live marshal.json actually writes. The regression this module exists for is
a SILENCE, not a wrong value: a reader that only understood the legacy list
shape returned an empty scan against a real marshal.json, and an empty scan is
byte-identical to "scanned, and this marshal.json declares no project steps". A
permission surface could therefore report a clean coverage scan while having
read nothing.

marshal.json is shared and target-neutral, so the same reader must serve every
target. The cross-runtime agreement cases below are the guard on that: a
per-runtime reader is free to drift, and each drift is again silent.
"""

from __future__ import annotations

import json
from typing import Any

import claude_runtime
import pytest
from antigravity_runtime import AntigravityRuntime
from opencode_runtime import OpenCodeRuntime
from runtime_base import PROJECT_STEP_PHASES, extract_project_steps

from conftest import PROJECT_ROOT

# ⛔ Vacuity guard — the roster is production's, so an empty one would make the
# roster assertions below vacuous and `assert declared` unreachable.
assert PROJECT_STEP_PHASES, 'runtime_base.PROJECT_STEP_PHASES is empty'


def _keyed(steps: list[str]) -> dict[str, Any]:
    """Build ``plan.{phase}.steps`` in the shape the live marshal.json writes.

    A step carries parameters, so ``steps`` is a KEYED MAP of
    ``{step-notation: {params}}`` rather than a bare list of notations.
    """
    return {notation: {'lane': 'minimal'} for notation in steps}


KEYED_CONFIG: dict[str, Any] = {
    'plan': {
        'phase-5-execute': {
            'steps': _keyed(['default:push', 'project:finalize-step-plugin-doctor', 'project:ci-verify']),
        },
        'phase-6-finalize': {
            'steps': _keyed(['project:finalize-step-deploy-target', 'default:create-pr']),
        },
    }
}

LEGACY_CONFIG: dict[str, Any] = {
    'plan': {
        'phase-5-execute': {
            'steps': ['default:push', 'project:finalize-step-plugin-doctor', 'project:ci-verify'],
        },
        'phase-6-finalize': {
            'steps': ['project:finalize-step-deploy-target', 'default:create-pr'],
        },
    }
}

EXPECTED_STEPS: list[dict[str, str]] = [
    {
        'skill': 'finalize-step-plugin-doctor',
        'step': 'project:finalize-step-plugin-doctor',
        'phase': 'phase-5-execute',
    },
    {'skill': 'ci-verify', 'step': 'project:ci-verify', 'phase': 'phase-5-execute'},
    {
        'skill': 'finalize-step-deploy-target',
        'step': 'project:finalize-step-deploy-target',
        'phase': 'phase-6-finalize',
    },
]


def _runtimes() -> list[Any]:
    return [
        claude_runtime._extract_project_steps,
        OpenCodeRuntime().permission_extract_project_steps,
        AntigravityRuntime().permission_extract_project_steps,
    ]


def _step_indices() -> list[int]:
    """The per-step parametrization cases, over a roster proven non-empty.

    ``range(len(EXPECTED_STEPS))`` inlines to no case at all when the roster is
    empty, so the test would silently disappear rather than fail — the shape the
    R5 harness guard reports. The assertion is what makes the parametrization an
    observation instead of a conditional one.
    """
    assert EXPECTED_STEPS, 'the published roster must carry at least one step'
    return list(range(len(EXPECTED_STEPS)))


class TestKeyedMapIsRead:
    """The keyed map is the live shape; an unread one reports a false clean."""

    def test_keyed_map_yields_what_the_list_shape_yielded(self) -> None:
        assert extract_project_steps(KEYED_CONFIG) == EXPECTED_STEPS

    @pytest.mark.parametrize('config', [KEYED_CONFIG, LEGACY_CONFIG], ids=['keyed-map', 'legacy-list'])
    def test_both_shapes_agree(self, config: dict[str, Any]) -> None:
        """The keyed map is a change of shape, not a change of meaning."""
        assert extract_project_steps(config) == extract_project_steps(LEGACY_CONFIG)

    @pytest.mark.parametrize('index', _step_indices())
    def test_zero_project_steps_is_unreachable_from_a_well_formed_keyed_map(self, index: int) -> None:
        """No single declared project step may be dropped to nothing.

        Asserted per-entry rather than on the count so a regression names WHICH
        step stopped being read, instead of only how many are left.
        """
        notation = EXPECTED_STEPS[index]['step']
        config: dict[str, Any] = {
            'plan': {'phase-5-execute': {'steps': _keyed(['default:push', notation])}},
        }
        assert extract_project_steps(config) == [
            {'skill': notation[len('project:') :], 'step': notation, 'phase': 'phase-5-execute'}
        ]

    def test_roster_is_the_published_one(self) -> None:
        """Only the roster's phases are scanned — a reader cannot widen itself."""
        config = {
            'plan': {
                'phase-1-init': {'steps': _keyed(['project:init-step'])},
                'phase-5-execute': {'steps': _keyed(['project:execute-step'])},
            }
        }
        assert [step['step'] for step in extract_project_steps(config)] == ['project:execute-step']
        assert set(PROJECT_STEP_PHASES) == {'phase-5-execute', 'phase-6-finalize'}


class TestCrossRuntimeAgreement:
    """marshal.json is target-neutral, so one input must give one answer."""

    @pytest.mark.parametrize('config', [KEYED_CONFIG, LEGACY_CONFIG], ids=['keyed-map', 'legacy-list'])
    def test_all_three_runtimes_return_equal_results(self, config: dict[str, Any]) -> None:
        results = [reader(config) for reader in _runtimes()]
        assert all(result == results[0] for result in results)
        assert results[0] == EXPECTED_STEPS

    def test_antigravity_evaluates_its_input(self) -> None:
        """Antigravity reads the marshal file; it must not return a constant.

        An empty list read as "scanned and found nothing" on a target that
        never scanned, so a constant return was indistinguishable from a real
        clean result on every input at once.
        """
        reader = AntigravityRuntime().permission_extract_project_steps
        assert reader(KEYED_CONFIG) == EXPECTED_STEPS
        assert reader({'plan': {'phase-5-execute': {'steps': _keyed(['default:push'])}}}) == []


class TestNonProjectAndMalformedEntries:
    def test_non_project_notations_are_not_steps(self) -> None:
        config = {'plan': {'phase-5-execute': {'steps': _keyed(['default:push', 'plan-marshall:plan-retrospective'])}}}
        assert extract_project_steps(config) == []

    def test_bare_project_prefix_names_no_skill(self) -> None:
        """``project:`` with nothing after it has no skill to grant."""
        assert extract_project_steps(
            {'plan': {'phase-5-execute': {'steps': _keyed(['project:', 'project:real-skill'])}}}
        ) == [{'skill': 'real-skill', 'step': 'project:real-skill', 'phase': 'phase-5-execute'}]

    @pytest.mark.parametrize(
        'config',
        [
            pytest.param({'error': 'marshal.json not found'}, id='failed-load'),
            pytest.param({}, id='empty'),
            pytest.param({'plan': []}, id='plan-not-a-map'),
            pytest.param({'plan': {'phase-5-execute': []}}, id='phase-not-a-map'),
            pytest.param({'plan': {'phase-5-execute': {'steps': 5}}}, id='steps-not-a-shape'),
        ],
    )
    def test_unreadable_shapes_yield_no_steps_rather_than_raising(self, config: dict[str, Any]) -> None:
        """One unexpected shape must not take down every permission op."""
        assert extract_project_steps(config) == []


class TestLiveMarshalJson:
    """The live marshal.json is the input whose shape the defect hid behind."""

    def test_live_marshal_json_declares_project_steps_and_the_reader_finds_them(self) -> None:
        """Read the file this repo actually ships, not a fixture standing in for it.

        ``.plan/marshal.json`` is tracked, so its ``steps`` shape is a fact about
        the repository rather than about one developer's local config. That shape
        is precisely what the list-only readers could not read, and no synthetic
        fixture states it as strongly as the file itself.
        """
        config = json.loads((PROJECT_ROOT / '.plan' / 'marshal.json').read_text(encoding='utf-8'))
        declared = {
            notation
            for phase in PROJECT_STEP_PHASES
            for notation in (config.get('plan', {}).get(phase, {}).get('steps') or {})
            if isinstance(notation, str) and notation.startswith('project:')
        }
        assert declared, 'the live marshal.json declares no project steps; this test no longer covers the defect'
        assert {step['step'] for step in extract_project_steps(config)} == declared
