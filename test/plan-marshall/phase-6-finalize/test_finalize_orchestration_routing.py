#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the finalize orchestration routing split (deliverable 3).

Named for the finalize *routing split* rather than for one step, because it pins
BOTH lesson-emitting write-sites. In orchestration context every finalize step
that emits lesson-shaped output routes to the epic's ``inbox/`` OUTBOX and makes
zero global-lessons-store writes; a non-orchestrated plan's finalize behaviour is
untouched.

Covered:

- **Detection reuses the shipped seam** — ``classify_source_id`` over the pointer
  shape ``phase-1-init`` emits.
- **Zero global-store writes at BOTH write-sites** — the orchestrated branch of
  ``workflow/lessons-capture.md`` AND of ``plan-retrospective/SKILL.md`` Step 5b.
  Both assertions are required: with only the first, the criterion is a vacuous
  guard that passes green while the retrospective path leaks.
- **The write-site set is closed** — a sweep over every registered
  ``phase-6-finalize`` step body. **Scope**: the sweep covers the registered
  finalize step set only (``marshal.json`` -> ``plan.phase-6-finalize.steps``).
  It fails when a future FINALIZE step gains an unbranched ``manage-lessons add``
  call site. The two out-of-scope mid-flight call sites (``phase-4-plan/SKILL.md``
  and ``execute-task/SKILL.md``, which fire in phases 4 and 5 before the plan has
  a landing to report) are known and deliberately excluded — a green sweep means
  no *registered finalize step* leaks the global store, NOT that the global store
  is unreachable from an orchestrated plan generally.
- **Retrospective input contract**, **non-orchestrated path unchanged**, and the
  **short-circuit carve-out**.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

_inbox = load_script_module(
    'plan-marshall', 'marshall-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
classify_source_id = _inbox.classify_source_id

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_FINALIZE = _PLAN_MARSHALL / 'phase-6-finalize'
_FINALIZE_SKILL = _FINALIZE / 'SKILL.md'
_LESSONS_CAPTURE = _FINALIZE / 'workflow' / 'lessons-capture.md'
_LESSONS_INTEGRATION = _FINALIZE / 'standards' / 'lessons-integration.md'
_RETROSPECTIVE = _PLAN_MARSHALL / 'plan-retrospective' / 'SKILL.md'
_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'

#: The exact executor invocation form of a global-lessons-store write.
_ADD_CALL = re.compile(r'manage-lessons:manage-lessons\s+add\b')

#: The per-module architecture-hints write the orchestrated branch also forbids.
_ENRICH_CALL = re.compile(r'architecture\s+enrich\b')

#: The inbox write verb the orchestrated branch uses instead.
_INBOX_WRITE = re.compile(r'orchestrator\s+inbox\s+write\b')


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _between(text: str, start_marker: str, end_marker: str) -> str:
    """Return the text between two literal markers (both must be present)."""
    start = text.find(start_marker)
    assert start != -1, f'start marker not found: {start_marker!r}'
    end = text.find(end_marker, start + len(start_marker))
    assert end != -1, f'end marker not found: {end_marker!r}'
    return text[start:end]


def _registered_finalize_steps() -> list[str]:
    data = json.loads(_read(_MARSHAL_JSON))
    return list(data['plan']['phase-6-finalize']['steps'].keys())


def _step_documents(step_key: str) -> list[Path]:
    """Resolve a registered finalize step key to its on-disk body document(s)."""
    if step_key.startswith('project:'):
        name = step_key.split(':', 1)[1]
        return [PROJECT_ROOT / '.claude' / 'skills' / name / 'SKILL.md']
    if step_key.startswith('default:'):
        name = step_key.split(':', 1)[1]
        return [
            _FINALIZE / 'standards' / f'{name}.md',
            _FINALIZE / 'workflow' / f'{name}.md',
        ]
    bundle, skill = step_key.split(':', 1)
    return [MARKETPLACE_ROOT / bundle / 'skills' / skill / 'SKILL.md']


# =============================================================================
# Detection reuses the shipped seam
# =============================================================================


class TestDetectionSeam:
    def test_should_classify_the_pointer_shape_phase_1_init_emits(self):
        pointer = '.plan/local/orchestrator/truthful-signals/plans/PLAN-55-inbox.md'

        verdict = classify_source_id(pointer)

        assert (verdict.orchestrated, verdict.epic) == (True, 'truthful-signals')
        assert verdict.detection == 'orchestrated'

    def test_should_reject_a_plain_text_description(self):
        assert classify_source_id('make finalize talk to the epic') == (
            False,
            None,
            None,
            'not_orchestrator_pointer',
        )

    def test_should_reject_an_unrelated_path(self):
        assert classify_source_id('doc/adr/ADR-002.adoc') == (
            False,
            None,
            None,
            'not_orchestrator_pointer',
        )

    def test_should_reject_a_traversal_attempt(self):
        pointer = '.plan/local/orchestrator/../../etc/plans/PLAN-1.md'

        assert classify_source_id(pointer) == (
            False,
            None,
            None,
            'not_orchestrator_pointer',
        )

    def test_dispatcher_uses_the_same_two_call_seam(self):
        text = _read(_FINALIZE_SKILL)

        assert 'request read --plan-id {plan_id} --section source_id' in text
        assert 'orchestrator inbox detect' in text

    def test_dispatcher_parses_the_detection_token(self):
        # Anchored to the a0 block so the assertion cannot pass on a stray
        # match elsewhere in the SKILL body.
        block = _between(
            _read(_FINALIZE_SKILL),
            'a0. Resolve orchestration context',
            'a. Compute three signal counts',
        )

        assert '`detection`' in block
        assert 'detection={detection}' in block

    def test_dispatcher_warns_on_an_unrecognised_pointer(self):
        block = _between(
            _read(_FINALIZE_SKILL),
            'a0. Resolve orchestration context',
            'a. Compute three signal counts',
        )

        assert 'detection == unrecognised_id' in block
        assert '--level WARNING' in block
        # The obligation is to name the pointer, not merely to log something.
        assert '{source_id}' in block


# =============================================================================
# Zero global-store writes at BOTH write-sites
# =============================================================================


class TestZeroGlobalStoreWritesLessonsCapture:
    def _branch(self) -> str:
        """The emission region — every invocation the orchestrated branch issues."""
        return _between(
            _read(_LESSONS_CAPTURE),
            '#### Orchestrated emission contract',
            '### Non-orchestrated execution',
        )

    def _declaration(self) -> str:
        """The branch-selection prose that states what the branch may NOT call."""
        return _between(
            _read(_LESSONS_CAPTURE),
            '### Orchestration branch (evaluate FIRST)',
            '#### Orchestrated emission contract',
        )

    def test_orchestrated_branch_makes_no_global_lessons_write(self):
        assert _ADD_CALL.search(self._branch()) is None
        assert 'zero** `manage-lessons add` calls' in self._declaration()

    def test_orchestrated_branch_makes_no_architecture_enrich_call(self):
        """Both halves are required, and neither is redundant.

        The regex half proves the emission region issues no enrich call; the
        declaration half proves the branch-selection prose SAYS so. Without the
        prose half the guard goes vacuous the moment the region is renamed or
        split — the regex would then search an empty span and pass.

        The declaration now states the fact for the WHOLE body rather than for the
        orchestrated branch alone: the step is ``post_run_review: true``, so no
        branch of it can reach the hints store (see the KNOWLEDGE routing section,
        which files the hint as owed instead of writing it).
        """
        assert _ENRICH_CALL.search(self._branch()) is None
        assert 'No branch of this body calls `architecture enrich`' in self._declaration()

    def test_declaration_leaves_the_non_orchestrated_path_unchanged(self):
        declaration = self._declaration()

        assert '**`orchestrated: false`**' in declaration
        assert 'unchanged' in declaration

    def test_orchestrated_branch_uses_the_inbox_write_verb(self):
        assert _INBOX_WRITE.search(self._branch()) is not None

    def test_orchestrated_branch_covers_landing_and_candidate_lesson(self):
        branch = self._branch()

        assert 'kind: landing' in branch
        assert 'kind: candidate-lesson' in branch

    def test_orchestrated_branch_emits_one_landing_unconditionally(self):
        branch = self._branch()

        assert 'unconditionally' in branch
        assert 'zero signals' in branch

    def test_orchestrated_branch_performs_no_classification(self):
        assert 'no** global-vs-epic classification' in self._branch()

    def test_branch_b4_and_output_field_are_declared(self):
        text = _read(_LESSONS_CAPTURE)

        assert '**Branch B4 — routed to epic inbox' in text
        assert 'inbox_messages_written: {N}' in text
        assert 'inbox message(s) -> epic {epic}' in text

    def test_output_declares_the_b4_consumer_rule(self):
        text = _read(_LESSONS_CAPTURE)

        assert 'non-zero `inbox_messages_written`' in text
        assert 'leaves both `0`' in text


class TestZeroGlobalStoreWritesRetrospective:
    def _branch(self) -> str:
        return _between(
            _read(_RETROSPECTIVE),
            '**`orchestrated: true` — route to the epic inbox.**',
            '**`orchestrated: false` — unchanged.**',
        )

    def test_orchestrated_branch_makes_no_global_lessons_write(self):
        assert _ADD_CALL.search(self._branch()) is None

    def test_orchestrated_branch_uses_the_inbox_write_verb(self):
        assert _INBOX_WRITE.search(self._branch()) is not None

    def test_orchestrated_branch_routes_every_proposal_as_candidate_lesson(self):
        assert '--kind candidate-lesson' in self._branch()

    def test_orchestrated_branch_documents_dedup_not_running_with_reason(self):
        branch = self._branch()

        assert "Step 5a's dedup classification does NOT run" in branch
        assert 'cross-plan context' in branch

    def test_orchestrated_branch_documents_no_already_closed_deletion(self):
        branch = self._branch()

        assert 'No `already_closed` deletion happens on this branch' in branch
        assert 'corpus mutation the orchestrator owns' in branch

    def test_prohibited_actions_carry_the_branch_specific_prohibition(self):
        text = _read(_RETROSPECTIVE)

        assert 'Never call `manage-lessons add` in orchestration context' in text

    def test_enforcement_execution_mode_names_the_inbox_route(self):
        text = _read(_RETROSPECTIVE)

        assert 'to the epic inbox as `kind: candidate-lesson` messages' in text


class TestBothWriteSitesNamedInOneStandard:
    def test_standard_names_both_write_sites(self):
        text = _read(_LESSONS_INTEGRATION)

        assert '## Recording Lessons' in text
        assert '### Orchestration context' in text
        assert 'lessons-capture.md' in text
        assert 'plan-retrospective/SKILL.md' in text

    def test_standard_defers_classification_to_the_orchestrator(self):
        text = _read(_LESSONS_INTEGRATION)

        assert 'deferred to the orchestrator-side pickup' in text
        assert 'cross-plan context' in text


# =============================================================================
# The write-site set is closed (registered finalize step set only)
# =============================================================================


class TestWriteSiteSetIsClosed:
    def test_every_registered_step_key_resolves_to_a_body_document(self):
        unresolved = [
            step
            for step in _registered_finalize_steps()
            if not any(doc.is_file() for doc in _step_documents(step))
        ]

        # `lessons-capture` and friends resolve via standards/ OR workflow/; a key
        # that resolves to neither means the sweep below would silently skip it.
        assert unresolved == []

    def test_no_registered_finalize_step_writes_the_global_store_unbranched(self):
        leaking: list[str] = []
        for step in _registered_finalize_steps():
            for doc in _step_documents(step):
                if not doc.is_file():
                    continue
                text = _read(doc)
                if _ADD_CALL.search(text) is None:
                    continue
                branched = 'orchestrated' in text and _INBOX_WRITE.search(text)
                if not branched:
                    leaking.append(step)

        assert leaking == []

    def test_the_two_out_of_scope_call_sites_are_not_finalize_steps(self):
        registered = set(_registered_finalize_steps())

        assert 'plan-marshall:phase-4-plan' not in registered
        assert 'plan-marshall:execute-task' not in registered


# =============================================================================
# Retrospective input contract
# =============================================================================


class TestRetrospectiveInputContract:
    def test_input_contract_declares_both_forwarded_inputs(self):
        text = _read(_RETROSPECTIVE)

        assert '| `orchestrated` | bool | No |' in text
        assert '| `epic` | string | No |' in text

    def test_input_contract_carries_the_must_not_recompute_obligation(self):
        text = _read(_RETROSPECTIVE)

        assert 'MUST NOT recompute it' in text

    def test_user_invocable_mode_self_resolves_through_the_same_seam(self):
        text = _read(_RETROSPECTIVE)

        assert 'user-invocable live mode' in text
        assert 'never a third detector' in text

    def test_archived_mode_exclusion_is_stated_with_its_rationale(self):
        text = _read(_RETROSPECTIVE)

        assert 'Archived mode is out of scope and unchanged' in text
        assert 'already-landed plan' in text
        assert 'may itself be archived' in text

    def test_dispatcher_forwards_both_inputs_on_the_retrospective_dispatch(self):
        text = _read(_FINALIZE_SKILL)
        block = _between(
            text,
            'The same two orchestration fields are ALSO forwarded on the',
            'Continue to item 5',
        )

        assert 'plan-marshall:plan-retrospective' in block
        assert 'orchestrated: {true|false}' in block
        assert 'epic: {slug|""}' in block


# =============================================================================
# Non-orchestrated path unchanged
# =============================================================================


class TestNonOrchestratedPathUnchanged:
    def test_lessons_capture_keeps_the_three_gate_policy_reference(self):
        text = _read(_LESSONS_CAPTURE)

        assert 'lesson-creation-policy.md' in text
        assert 'Gate 1 (dedup against the existing corpus), Gate 2' in text

    def test_lessons_capture_keeps_the_three_step_path_allocate_flow(self):
        text = _read(_LESSONS_CAPTURE)

        assert 'manage-lessons:manage-lessons add' in text
        assert 'Step 2 — Stage the body via the Write tool' in text
        assert 'manage-lessons:manage-lessons set-body' in text

    def test_lessons_capture_keeps_the_exact_branch_display_details(self):
        text = _read(_LESSONS_CAPTURE)

        for detail in (
            '"{N} lesson(s) recorded ({lesson_ids})"',
            '"no lessons recorded"',
            '"folded into existing lesson/plan, no new lesson"',
            # Branch B3 no longer routes the fact to architecture — a
            # post-merge-ordered step cannot reach the hints store, so the hint is
            # FILED AS OWED and the detail reports what was actually done.
            '"{N} owed architecture hint(s) filed"',
        ):
            assert detail in text, detail

    def test_lessons_capture_keeps_the_actionable_knowledge_partition(self):
        """The partition survives, and KNOWLEDGE routes to the OWED-hint artifact.

        Anchored on the route rather than on ``_ENRICH_CALL`` matching somewhere in
        the document: the body now FORBIDS that call, so its only remaining
        occurrences are the prose forbidding it — a regex that matches the
        prohibition would report the route as present no matter what the route
        became.
        """
        text = _read(_LESSONS_CAPTURE)

        assert 'Classify each candidate signal: ACTIONABLE vs KNOWLEDGE' in text
        assert 'The hints store is unreachable from here, so the hint is OWED, not written.' in text
        assert 'Owed architecture hint: {module}' in text

    def test_retrospective_keeps_the_step_5a_dedup_gate(self):
        text = _read(_RETROSPECTIVE)

        assert 'Step 5b: Record (gated by 5a)' in text
        assert 'Only `status: new` proposals reach `manage-lessons add`' in text

    def test_retrospective_keeps_new_merge_into_already_closed_handling(self):
        branch = _between(
            _read(_RETROSPECTIVE),
            '**`orchestrated: false` — unchanged.**',
            '## Related',
        )

        assert '`merge_into` proposals are applied via `Edit`' in branch
        assert '`already_closed` proposals are surfaced in the report' in branch


# =============================================================================
# Short-circuit carve-out
# =============================================================================


class TestShortCircuitCarveOut:
    def _item_4b(self) -> str:
        return _between(
            _read(_FINALIZE_SKILL),
            '4b. Lessons-capture Signal Gate',
            '4c. Adr-propose Signal Gate',
        )

    def test_orchestration_resolution_precedes_the_short_circuit(self):
        item = self._item_4b()

        assert item.index('a0. Resolve orchestration context') < item.index(
            'b. Three-zero short-circuit'
        )

    def test_resolution_is_documented_as_running_before_the_short_circuit(self):
        assert 'runs BEFORE the three-zero short-circuit' in self._item_4b()

    def test_short_circuit_is_stated_as_not_firing_when_orchestrated(self):
        item = self._item_4b()

        assert 'the three-zero short-circuit does NOT fire' in item
        assert 'owes its epic a `kind: landing` message' in item

    def test_short_circuit_condition_is_gated_on_not_orchestrated(self):
        assert 'When `orchestrated == false AND signal_1_count == 0' in self._item_4b()

    def test_both_runtime_inputs_appear_in_the_forwarded_block(self):
        item = self._item_4b()

        assert 'orchestrated: {true|false}' in item
        assert 'epic: {slug|""}' in item

    def test_the_two_write_site_list_is_recorded_at_the_resolution_site(self):
        item = self._item_4b()

        assert 'default:lessons-capture' in item
        assert 'plan-marshall:plan-retrospective' in item
        assert 'MUST be added to this list' in item

    def test_body_declares_both_runtime_inputs(self):
        text = _read(_LESSONS_CAPTURE)

        assert '- `orchestrated` — bool;' in text
        assert '- `epic` — string;' in text
        assert 'MUST NOT re-issue either call' in text
