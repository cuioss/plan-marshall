#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A malformed task/deliverable number must not take the mechanical Q-Gate down.

Task records come off disk as JSON, so ``number`` and ``deliverable`` may be
absent, null, or a string. Every check in ``_cmd_qgate_mechanical`` read them
with a bare ``int(...)`` / ``task['number']``, which raises ``KeyError`` /
``TypeError`` / ``ValueError`` on exactly such a record.

**The failure direction is what makes this worth pinning.** Several of those
raises sat on the branch that REPORTS a finding — ``f'...TASK-{t["number"]:03d}
references unknown deliverable'`` — so the gate crashed precisely when it had a
defect to emit, and ran clean when it had none. A checker that fails only while
failing is a fail-open wearing a traceback, and it is the shape these closure
checks exist to prevent, committed against itself.

The fix routes every conversion through ``_qgate_closure._as_int`` — the module's
existing guard — and DROPS the unusable record from whatever map it would have
keyed. Dropping is the honest move: a record with no usable identity cannot be a
graph node, cannot be a deliverable reference, and cannot be attributed to.

Each class below carries a positive control alongside the malformed cases. A
guard that silenced the check entirely would pass every "does not raise"
assertion, so each class also proves the check still FIRES on a well-formed
record.
"""

from __future__ import annotations

from typing import Any

import pytest

from conftest import PROJECT_ROOT, load_script_module

_qgate = load_script_module(
    'plan-marshall', 'manage-tasks', '_cmd_qgate_mechanical.py', '_cmd_qgate_mechanical_number_guards'
)

_check_coverage = _qgate._check_coverage
_check_skill_resolution = _qgate._check_skill_resolution
_check_acyclic = _qgate._check_acyclic
_check_files_exist = _qgate._check_files_exist
_check_keyword_drift = _qgate._check_keyword_drift
_task_number = _qgate._task_number

#: A real repository file, so ``files_exist``'s existence predicate passes for a
#: well-formed control and the only variable is the malformed number.
_REAL_FILE = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
_ABSENT_FILE = 'marketplace/bundles/plan-marshall/skills/manage-tasks/no-such-file.md'

#: Every shape a JSON-sourced number field can arrive in and not be a number.
#: ``True`` is included deliberately: ``isinstance(True, int)`` is True in
#: Python, so a bool would otherwise convert to ``1`` and be attributed to
#: TASK-001 — a real record silently wearing another task's identity.
_UNUSABLE = [
    pytest.param(None, id='null'),
    pytest.param('', id='empty_string'),
    pytest.param('holistic', id='non_numeric_string'),
    pytest.param(True, id='bool'),
    pytest.param({'n': 1}, id='dict'),
    pytest.param([1], id='list'),
]

_ABSENT = object()


def _task(
    number: Any,
    *,
    deliverable: Any = 1,
    profile: str = 'implementation',
    targets: list[str] | None = None,
    skills: list[str] | None = None,
    domain: str = 'plan-marshall-plugin-dev',
    description: str = '',
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    """Build a task record, omitting ``number`` entirely when it is ``_ABSENT``."""
    task: dict[str, Any] = {
        'title': 'T',
        'profile': profile,
        'deliverable': deliverable,
        'domain': domain,
        'description': description,
        'skills': skills if skills is not None else [],
        'depends_on': depends_on if depends_on is not None else [],
        'steps': [{'number': i + 1, 'target': t, 'intent': 'read'} for i, t in enumerate(targets or [])],
    }
    if number is not _ABSENT:
        task['number'] = number
    return task


def _deliverable(number: Any, *, title: str = 'D') -> dict[str, Any]:
    return {'number': number, 'title': title, 'affected_files': [], 'survey_scope': [], 'mutation_scope': []}


def _no_emit() -> list[dict[str, str]]:
    """A fresh persist-failure sink; ``emit=False`` means nothing is ever appended."""
    return []


# =============================================================================
# _task_number — the display-side guard
# =============================================================================


class TestTaskNumberGuard:
    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_unusable_values_render_as_the_impossible_zero(self, value):
        """``0`` renders ``TASK-000``, which is not a real task id.

        The record is malformed and the finding says so by naming an impossible
        number, rather than silently attributing the defect to another task.
        """
        assert _task_number(_task(value)) == 0

    def test_an_absent_number_renders_as_zero(self):
        assert _task_number(_task(_ABSENT)) == 0

    @pytest.mark.parametrize(('value', 'expected'), [(7, 7), ('7', 7), (' 7 ', 7)])
    def test_usable_values_are_preserved(self, value, expected):
        """Positive control: the guard must not flatten a real number to zero."""
        assert _task_number(_task(value)) == expected


# =============================================================================
# coverage
# =============================================================================


class TestCoverageDropsUnusableRecords:
    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_a_task_with_an_unusable_deliverable_is_dropped_not_flagged(self, value):
        """It is not a deliverable reference at all, so it is not an orphan.

        Reporting "references unknown deliverable None" would misattribute a
        malformed record as a real coverage defect.

        ``_check_coverage`` counts BOTH directions into one ``failed`` total —
        uncovered deliverables and orphan tasks — so the well-formed task
        covering deliverable 1 is load-bearing, not scenery: without it the
        deliverable would go uncovered and contribute a finding of its own,
        and the resulting ``failed == 1`` could not distinguish that from the
        malformed record being flagged as an orphan. Covering it isolates the
        one direction under test, so ``failed == 0`` means exactly "the dropped
        record produced no finding".
        """
        tasks = [_task(1, deliverable=1), _task(2, deliverable=value)]
        deliverables = [_deliverable(1)]

        failed, emitted = _check_coverage('p', tasks, deliverables, _no_emit(), emit=False)

        assert failed == 0
        assert emitted == 0

    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_a_deliverable_with_an_unusable_number_is_dropped(self, value):
        """A deliverable with no usable number cannot be covered or referenced."""
        tasks = [_task(1, deliverable=1)]
        deliverables = [_deliverable(1), _deliverable(value)]

        failed, _emitted = _check_coverage('p', tasks, deliverables, _no_emit(), emit=False)

        assert failed == 0, 'the unusable deliverable must be dropped, not reported as uncovered'

    def test_an_uncovered_deliverable_is_still_reported(self):
        """Positive control — the guard must not silence the check."""
        tasks = [_task(1, deliverable=1)]
        deliverables = [_deliverable(1), _deliverable(2)]

        failed, _emitted = _check_coverage('p', tasks, deliverables, _no_emit(), emit=False)

        assert failed == 1

    def test_an_orphan_task_is_still_reported_with_a_usable_number(self):
        """Positive control for the other direction.

        TASK-001 covers deliverable 1 so the only finding this can produce is
        the orphan one — see the isolation note on the dropped-record case
        above. Without it the uncovered deliverable would contribute a second
        finding and ``failed`` would no longer identify WHICH direction fired.
        """
        tasks = [_task(1, deliverable=1), _task(3, deliverable=99)]
        deliverables = [_deliverable(1)]

        failed, _emitted = _check_coverage('p', tasks, deliverables, _no_emit(), emit=False)

        assert failed == 1

    def test_the_holistic_sentinel_is_still_exempt(self):
        """``deliverable == 0`` is the holistic-task carve-out, unchanged."""
        tasks = [_task(1, deliverable=0)]
        deliverables = [_deliverable(1)]

        failed, _emitted = _check_coverage('p', tasks, deliverables, _no_emit(), emit=False)

        assert failed == 1, 'only the uncovered deliverable — the holistic task is not an orphan'


# =============================================================================
# acyclic
# =============================================================================


class TestAcyclicDropsUnnumberedTasks:
    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_an_unnumbered_task_does_not_manufacture_a_cycle(self, value):
        """The denominator is the NUMBERED population, not the raw task list.

        A task with no usable number has no identity to be a graph node under, so
        it is excluded from the graph. Comparing ``visited`` against the raw
        ``len(tasks)`` after dropping it would report a phantom cycle for every
        dropped record — a fabricated finding on a plan with an acyclic graph.
        """
        tasks = [_task(1), _task(2, depends_on=['TASK-1']), _task(value)]

        failed, emitted = _check_acyclic('p', tasks, _no_emit(), emit=False)

        assert failed == 0, 'dropping an unnumbered task must not read as an unvisited cycle member'
        assert emitted == 0

    def test_a_real_cycle_is_still_detected(self):
        """Positive control — the guard must not disarm cycle detection."""
        tasks = [_task(1, depends_on=['TASK-2']), _task(2, depends_on=['TASK-1'])]

        failed, _emitted = _check_acyclic('p', tasks, _no_emit(), emit=False)

        assert failed == 1

    def test_a_dependency_on_an_unnumbered_task_is_not_an_edge(self):
        """An edge needs two identified endpoints; a dangling one is reported elsewhere."""
        tasks = [_task(_ABSENT), _task(2, depends_on=['TASK-1'])]

        failed, _emitted = _check_acyclic('p', tasks, _no_emit(), emit=False)

        assert failed == 0


# =============================================================================
# skill_resolution / files_exist / keyword_drift — the display-side call sites
# =============================================================================


class TestDisplaySiteCallersDoNotRaise:
    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_skill_resolution_reports_a_malformed_task(self, value):
        """The finding fires and renders; before the guard this raised instead."""
        tasks = [_task(value, domain='', skills=['not a valid shape'])]

        failed, _emitted = _check_skill_resolution('p', tasks, _no_emit(), emit=False)

        assert failed == 2, 'both the missing domain and the malformed skill shape are reported'

    def test_skill_resolution_is_clean_for_a_well_formed_task(self):
        tasks = [_task(1, skills=['plan-marshall:manage-tasks'])]

        failed, _emitted = _check_skill_resolution('p', tasks, _no_emit(), emit=False)

        assert failed == 0

    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_files_exist_reports_an_absent_target_on_a_malformed_task(self, value):
        tasks = [_task(value, targets=[_ABSENT_FILE])]

        failed, _emitted = _check_files_exist('p', tasks, PROJECT_ROOT, _no_emit(), emit=False)

        assert failed == 1

    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_files_exist_is_clean_for_a_present_target(self, value):
        """A malformed number must not turn a passing existence check into a finding."""
        tasks = [_task(value, targets=[_REAL_FILE])]

        failed, _emitted = _check_files_exist('p', tasks, PROJECT_ROOT, _no_emit(), emit=False)

        assert failed == 0

    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_keyword_drift_reports_a_malformed_task(self, value):
        """'CI' appears in the description and nowhere in the deliverable haystack."""
        tasks = [_task(value, deliverable=1, description='Wire the CI gate')]
        deliverables = [_deliverable(1)]

        failed, _emitted = _check_keyword_drift('p', tasks, deliverables, {}, _no_emit(), emit=False)

        assert failed == 1

    @pytest.mark.parametrize('value', _UNUSABLE)
    def test_keyword_drift_skips_a_task_whose_deliverable_is_unusable(self, value):
        """With no resolvable parent there is no haystack to compare against."""
        tasks = [_task(1, deliverable=value, description='Wire the CI gate')]
        deliverables = [_deliverable(1)]

        failed, _emitted = _check_keyword_drift('p', tasks, deliverables, {}, _no_emit(), emit=False)

        assert failed == 0

    def test_keyword_drift_is_clean_when_the_deliverable_mentions_the_keyword(self):
        """Positive control: the prose haystack is consulted, so no drift fires."""
        tasks = [_task(1, deliverable=1, description='Wire the CI gate')]
        deliverables = [_deliverable(1)]

        failed, _emitted = _check_keyword_drift('p', tasks, deliverables, {1: 'the CI gate'}, _no_emit(), emit=False)

        assert failed == 0
