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


def _step_cases() -> list[dict[str, Any]]:
    """The per-step parametrization cases, over a roster proven non-empty.

    ``range(len(EXPECTED_STEPS))`` inlines to no case at all when the roster is
    empty, so the test would silently disappear rather than fail — the shape the
    R5 harness guard reports. The assertion is what makes the parametrization an
    observation instead of a conditional one.

    The return form is load-bearing twice over, and only one spelling satisfies
    both guards. It must be a transform that PRESERVES cardinality and carries the
    roster name through, so the assert and the return meet on the same name and R5
    reads the helper as guarded: a narrowing transform (``if`` clause, ``filter``)
    proves nothing about its result, and wrapping the roster in another call
    (``len``, ``enumerate``) makes the expression name that callee instead of the
    roster. ``list()`` is both cardinality-preserving and name-carrying, and it is
    also the form ruff's C416 requires over the equivalent comprehension.
    """
    assert EXPECTED_STEPS, 'the published roster must carry at least one step'
    return list(EXPECTED_STEPS)


class TestKeyedMapIsRead:
    """The keyed map is the live shape; an unread one reports a false clean."""

    def test_keyed_map_yields_what_the_list_shape_yielded(self) -> None:
        assert extract_project_steps(KEYED_CONFIG) == EXPECTED_STEPS

    @pytest.mark.parametrize('config', [KEYED_CONFIG, LEGACY_CONFIG], ids=['keyed-map', 'legacy-list'])
    def test_both_shapes_agree(self, config: dict[str, Any]) -> None:
        """The keyed map is a change of shape, not a change of meaning."""
        assert extract_project_steps(config) == extract_project_steps(LEGACY_CONFIG)

    @pytest.mark.parametrize('step', _step_cases())
    def test_zero_project_steps_is_unreachable_from_a_well_formed_keyed_map(self, step: dict[str, Any]) -> None:
        """No single declared project step may be dropped to nothing.

        Asserted per-entry rather than on the count so a regression names WHICH
        step stopped being read, instead of only how many are left.
        """
        notation = step['step']
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


def _parse(output: str) -> dict[str, Any]:
    from toon_parser import parse_toon

    return parse_toon(output)


#: The runtimes that cannot express a per-skill grant, keyed by pytest id. Each
#: must READ the roster before answering ``ensure-steps``: an op that answers
#: without reading reports a scan that never happened.
_UNGRANTABLE_RUNTIMES = {'opencode': OpenCodeRuntime, 'antigravity': AntigravityRuntime}


class TestEnsureStepsReadsTheRoster:
    """``permission ensure-steps`` on a target with no per-skill grant."""

    @pytest.fixture(params=list(_UNGRANTABLE_RUNTIMES), ids=list(_UNGRANTABLE_RUNTIMES))
    def runtime(self, request) -> Any:
        return _UNGRANTABLE_RUNTIMES[request.param]()

    def test_a_declared_roster_is_declined_not_reported_clean(self, runtime, tmp_path) -> None:
        """Project steps that cannot be granted are a no-op naming them, not ``success``."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(json.dumps(KEYED_CONFIG), encoding='utf-8')

        result = _parse(runtime.permission_ensure_steps(str(marshal), 'project', False))

        assert result['status'] == 'no-op', result
        assert f'{len(EXPECTED_STEPS)} project step(s) scanned' in result['reason']
        for step in EXPECTED_STEPS:
            assert step['skill'] in result['reason']

    def test_an_empty_roster_is_a_measured_zero(self, runtime, tmp_path) -> None:
        """No project steps is a genuine success, carrying the scanned count."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(json.dumps({'plan': {}}), encoding='utf-8')

        result = _parse(runtime.permission_ensure_steps(str(marshal), 'project', False))

        assert result['status'] == 'success', result
        assert result['steps_scanned'] == 0
        assert result['permissions_added'] == 0

    @pytest.mark.parametrize(
        'config',
        [
            pytest.param({'plan': []}, id='plan-not-a-map'),
            pytest.param({'plan': {'phase-5-execute': []}}, id='phase-not-a-map'),
            pytest.param({'plan': {'phase-5-execute': {'steps': 5}}}, id='steps-not-a-shape'),
        ],
    )
    def test_a_malformed_roster_is_an_error_not_a_measured_zero(self, runtime, tmp_path, config) -> None:
        """A readable marshal.json whose roster SHAPE is wrong is not "no project steps"."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(json.dumps(config), encoding='utf-8')

        result = _parse(runtime.permission_ensure_steps(str(marshal), 'project', False))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_marshal'

    def test_an_invalid_scope_is_refused_on_every_runtime(self, runtime, tmp_path) -> None:
        """Scope is validated alike on both targets, before any read."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text(json.dumps({'plan': {}}), encoding='utf-8')

        result = _parse(runtime.permission_ensure_steps(str(marshal), 'workspace', False))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_scope'

    def test_a_malformed_marshal_is_an_error_not_an_empty_roster(self, runtime, tmp_path) -> None:
        """A load failure must never read as "scanned, nothing declared"."""
        marshal = tmp_path / 'marshal.json'
        marshal.write_text('{not valid json', encoding='utf-8')

        result = _parse(runtime.permission_ensure_steps(str(marshal), 'project', False))

        assert result['status'] == 'error'
        assert result['error'] in ('invalid_marshal', 'marshal_not_found')


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
