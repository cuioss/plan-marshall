#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the finalize orchestration routing split (deliverable 3).

Named for the finalize *routing split* rather than for one step, because it pins
EVERY lesson-emitting write-site. In orchestration context every finalize step
that emits lesson-shaped output routes to the epic's ``inbox/`` OUTBOX and makes
zero global-lessons-store writes; a non-orchestrated plan's finalize behaviour is
untouched.

Covered:

- **Detection reuses the shipped seam** — ``classify_source_id`` over the pointer
  shape ``phase-1-init`` emits.
- **Zero global-store writes at EVERY write-site** — the orchestrated branch of
  ``workflow/lessons-capture.md``, of ``plan-retrospective/SKILL.md`` Step 5b, AND
  of ``standards/finalize-step-preference-emitter.md`` Step 4. Every assertion is
  required: with only the first, the criterion is a vacuous guard that passes green
  while a sibling path leaks — which is exactly how the preference-emitter site went
  unnoticed until the registered-step sweep below caught it.
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
- **The routing registries are derived, not hand-maintained** — the SKILL.md
  "Built-in Step Dispatch Table" and ``_manifest_core.DEFAULT_PHASE_6_STEPS`` are
  both restatements of the same authoritative source (each step doc's own
  frontmatter, read through ``find_implementors``). Nothing structurally prevents
  either from drifting from it, so both are pinned here: the table's row SET and
  its per-row DOCUMENT PATHS, and the default candidate tuple's membership and
  ascending-``order`` sequence. Drift then fails at quality-gate rather than
  silently at dispatch.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import _manifest_core
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module
from extension_discovery import find_implementors

_inbox = load_script_module(
    'plan-marshall', 'marshall-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
classify_source_id = _inbox.classify_source_id

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_FINALIZE = _PLAN_MARSHALL / 'phase-6-finalize'
_FINALIZE_SKILL = _FINALIZE / 'SKILL.md'
_LESSONS_CAPTURE = _FINALIZE / 'workflow' / 'lessons-capture.md'
_LESSONS_INTEGRATION = _FINALIZE / 'standards' / 'lessons-integration.md'
_PREFERENCE_EMITTER = _FINALIZE / 'standards' / 'finalize-step-preference-emitter.md'
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


class TestZeroGlobalStoreWritesPreferenceEmitter:
    """The third write-site: the owed-hint filing in Step 4.

    Mirrors ``TestZeroGlobalStoreWritesRetrospective`` in shape, and keeps BOTH
    halves of the no-global-write assertion for the same anti-vacuity reason
    ``test_orchestrated_branch_makes_no_architecture_enrich_call`` does: the regex
    half proves the emission region issues no ``manage-lessons add``, the
    declaration half proves the branch-selection prose SAYS so. Without the prose
    half the guard goes vacuous the moment the region is renamed or split — the
    regex would then search an empty span and pass.
    """

    def _declaration(self) -> str:
        """The branch-selection prose that states what the branch may NOT call."""
        return _between(
            _read(_PREFERENCE_EMITTER),
            '#### Orchestration branch (evaluate FIRST)',
            '##### Orchestrated emission contract',
        )

    def _branch(self) -> str:
        """The emission region — every invocation the orchestrated branch issues."""
        return _between(
            _read(_PREFERENCE_EMITTER),
            '##### Orchestrated emission contract',
            '##### Non-orchestrated filing',
        )

    def _non_orchestrated(self) -> str:
        return _between(
            _read(_PREFERENCE_EMITTER),
            '##### Non-orchestrated filing',
            '### Step 5: Mark step done',
        )

    def test_orchestrated_branch_makes_no_global_lessons_write(self):
        assert _ADD_CALL.search(self._branch()) is None
        assert 'zero** `manage-lessons add` calls' in self._declaration()

    def test_orchestrated_branch_uses_the_inbox_write_verb(self):
        assert _INBOX_WRITE.search(self._branch()) is not None

    def test_orchestrated_branch_routes_every_owed_hint_as_candidate_lesson(self):
        assert '--kind candidate-lesson' in self._branch()

    def test_orchestrated_branch_emits_no_landing_message(self):
        # The one landing per orchestrated run is lessons-capture's; a second one
        # from here would put two landings on a single run.
        assert 'emits NO `kind: landing` message' in self._branch()

    def test_declaration_leaves_the_non_orchestrated_path_unchanged(self):
        declaration = self._declaration()

        assert '**`orchestrated: false`**' in declaration
        assert 'unchanged' in declaration

    def test_non_orchestrated_filing_still_writes_the_global_store(self):
        # Positive control. Without it the branch could satisfy every assertion
        # above by deleting the global-store route outright rather than branching
        # around it — that would break every non-orchestrated plan silently.
        assert _ADD_CALL.search(self._non_orchestrated()) is not None

    def test_inputs_declare_both_runtime_inputs_as_forwarded(self):
        text = _read(_PREFERENCE_EMITTER)

        assert '- `orchestrated` — bool;' in text
        assert '- `epic` — string;' in text
        assert 'MUST NOT re-issue either resolution call' in text


class TestEveryWriteSiteNamedInOneStandard:
    def test_standard_names_every_write_site(self):
        text = _read(_LESSONS_INTEGRATION)

        assert '## Recording Lessons' in text
        assert '### Orchestration context' in text
        assert 'lessons-capture.md' in text
        assert 'plan-retrospective/SKILL.md' in text
        assert 'finalize-step-preference-emitter.md' in text

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

    def test_the_write_site_list_is_recorded_at_the_resolution_site(self):
        item = self._item_4b()

        assert 'default:lessons-capture' in item
        assert 'plan-marshall:plan-retrospective' in item
        assert 'default:finalize-step-preference-emitter' in item
        assert 'MUST be added to this list' in item

    def test_body_declares_both_runtime_inputs(self):
        text = _read(_LESSONS_CAPTURE)

        assert '- `orchestrated` — bool;' in text
        assert '- `epic` — string;' in text
        assert 'MUST NOT re-issue either call' in text


# =============================================================================
# The routing registries are derived, not hand-maintained
#
# Two restatements of one authoritative source (each step doc's frontmatter,
# read through ``find_implementors``): the SKILL.md Built-in Step Dispatch Table
# and ``_manifest_core.DEFAULT_PHASE_6_STEPS``. Neither is generated, so each is
# pinned to the source here.
# =============================================================================

#: The ext-point whose implementors ARE the authoritative finalize step set.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The discovery ``source`` value that means "built-in finalize step". It is the
#: table's membership rule: the table routes exactly the built-in steps, while
#: ``project:`` steps route through the Interface Contract section and genuinely
#: opt-in ``bundle:skill`` steps (``source: bundle-optional``) route as typed
#: SKILL steps.
_BUILT_IN_SOURCE = 'built-in'

#: Section markers bounding the dispatch table inside SKILL.md.
_TABLE_START = '### Built-in Step Dispatch Table'
_TABLE_END = '### Interface Contract for External Steps'


def _built_in_records() -> list[dict]:
    """The authoritative built-in step records, straight from discovery."""
    return [
        record
        for record in find_implementors(_EXT_POINT)
        if record.get('source') == _BUILT_IN_SOURCE
    ]


def _dispatch_table_rows() -> list[tuple[str, str]]:
    """Parse the Built-in Step Dispatch Table into ``(step_name, doc_path)`` pairs.

    Reads the live SKILL.md rather than a fixture, so the guard observes the
    table a dispatcher would actually consult. The header and separator rows are
    dropped by requiring the first cell to be backtick-quoted, which every data
    row is and neither structural row is.
    """
    block = _between(_read(_FINALIZE_SKILL), _TABLE_START, _TABLE_END)
    rows: list[tuple[str, str]] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if len(cells) < 2 or not cells[0].startswith('`'):
            continue
        rows.append((cells[0].strip('`'), cells[1].strip('`')))
    return rows


def _missing_from_table(row_names: set[str]) -> list[str]:
    """The membership predicate under test: which built-in steps the table omits.

    Factored out so the mutation guard drives the SAME predicate the assertion
    uses — a guard that re-implemented the check would prove nothing about the
    check that actually runs.
    """
    return sorted(
        record['name']
        for record in _built_in_records()
        if record['name'] not in row_names
    )


class TestBuiltInStepDispatchTableMatchesDiscovery:
    """Pins the SKILL.md table (finding 9fdfcf) to the discovered step set.

    The compose-time step-resolution gate already fails loud with
    ``unresolvable_step`` when a built-in's standards doc is MISSING, so a
    deleted doc cannot reach dispatch. The residual this class covers is
    narrower and genuinely uncovered: a row naming a doc path that MOVED, and a
    row set that has diverged from the authoritative step set in either
    direction.
    """

    def test_table_is_non_empty(self):
        """Anti-vacuity: every assertion below is over the parsed rows.

        A parser that silently returned nothing — because the section was
        renamed or the table reformatted — would make the set comparison
        trivially satisfiable from one side, so emptiness is rejected on its own
        before anything else is asserted.
        """
        assert _dispatch_table_rows(), (
            f'No data rows parsed between {_TABLE_START!r} and {_TABLE_END!r} in '
            f'{_FINALIZE_SKILL}. Every assertion in this class reads those rows, '
            'so an empty parse would make them vacuous.'
        )

    def test_discovery_finds_built_in_steps(self):
        """Anti-vacuity for the other side of the comparison."""
        assert _built_in_records(), (
            f'find_implementors({_EXT_POINT!r}) discovered no records with '
            f'source == {_BUILT_IN_SOURCE!r}, so the table has nothing to be '
            'compared against.'
        )

    def test_table_rows_are_exactly_the_discovered_built_in_steps(self):
        row_names = {name for name, _ in _dispatch_table_rows()}
        discovered = {record['name'] for record in _built_in_records()}

        assert row_names == discovered, (
            'The Built-in Step Dispatch Table has drifted from the discovered '
            'built-in step set. Missing rows (the step exists but the table '
            f'does not route it): {sorted(discovered - row_names)}. Stale rows '
            '(the table routes a step discovery does not know about): '
            f'{sorted(row_names - discovered)}'
        )

    def test_table_has_no_duplicate_rows(self):
        names = [name for name, _ in _dispatch_table_rows()]

        assert len(names) == len(set(names)), (
            'The table lists a step more than once. Two rows for one step can '
            'disagree on the document path, and the set comparison above cannot '
            f'see the duplication: {sorted({n for n in names if names.count(n) > 1})}'
        )

    def test_each_row_document_path_is_the_discovered_document(self):
        """The MOVED-doc residual: a row path that resolves elsewhere, or nowhere.

        Compared against the discovered record's own ``path``, not merely
        against "some file exists there" — a row pointing at a real but
        different document is exactly as wrong as one pointing at nothing, and
        an existence-only check would pass it.
        """
        discovered_paths = {
            record['name']: Path(record['path']).resolve()
            for record in _built_in_records()
        }

        mismatches = []
        for name, doc in _dispatch_table_rows():
            expected = discovered_paths.get(name)
            if expected is None:
                continue  # Reported by the set comparison above.
            actual = (_FINALIZE / doc).resolve()
            if actual != expected:
                mismatches.append(f'{name}: table says {doc} -> {actual}, discovery says {expected}')

        assert mismatches == [], (
            'These table rows name a document that is not the step\'s '
            'authoritative doc. A moved doc is the residual the compose-time '
            'unresolvable_step gate does NOT cover, because that gate fires on a '
            f'missing built-in, not on a mis-pointed table row: {mismatches}'
        )

    def test_each_row_is_independently_load_bearing(self):
        """Mutation guard: dropping any ONE row is detected on its own.

        Removing a single row from the parsed set must make the membership
        predicate report exactly that step. This proves the check is sensitive
        to each row independently, so a table that silently lost one row while
        keeping the rest could never read as green — a claim a single set
        equality cannot make about itself.

        The population is derived inside the test body rather than at
        parametrize time on purpose: a collection-time derivation that resolved
        to nothing would produce zero test cases and report green, which is the
        same vacuity this guard exists to rule out.
        """
        row_names = {name for name, _ in _dispatch_table_rows()}
        required = [record['name'] for record in _built_in_records()]
        assert required, 'Precondition failed — see test_discovery_finds_built_in_steps.'

        undetected = []
        for omitted in required:
            assert omitted in row_names, (
                f'Mutation guard precondition failed: {omitted} is not a table '
                'row, so removing it proves nothing. Fix the table first.'
            )
            if _missing_from_table(row_names - {omitted}) != [omitted]:
                undetected.append(omitted)

        assert undetected == [], (
            'The membership predicate did not isolate these steps when each was '
            'removed on its own. A predicate that cannot detect every row '
            'independently can pass while silently missing one: '
            f'{undetected}'
        )


class TestDefaultPhase6StepsMatchesDiscovery:
    """Pins ``_manifest_core.DEFAULT_PHASE_6_STEPS`` (finding 455b62 item 1).

    The tuple is a candidate SET default, deliberately narrower than the
    discovered step set — so membership is asserted as containment, not
    equality. What IS asserted exactly is the tuple's ORDER: its own comment
    states it is written in ascending frontmatter ``order`` and kept in lock-step
    with it, and that claim had nothing enforcing it.
    """

    def _order_by_canonical_key(self) -> dict[str, int]:
        return {
            _manifest_core.canonicalize_step_key(record['name']): record['order']
            for record in find_implementors(_EXT_POINT)
            if isinstance(record.get('order'), int)
        }

    def test_default_set_is_non_empty(self):
        """Anti-vacuity — an empty tuple would satisfy both assertions below."""
        assert _manifest_core.DEFAULT_PHASE_6_STEPS

    def test_every_default_step_resolves_to_a_discovered_step(self):
        known = self._order_by_canonical_key()

        unresolved = [
            step for step in _manifest_core.DEFAULT_PHASE_6_STEPS if step not in known
        ]

        assert unresolved == [], (
            'These default candidate steps resolve to no discovered step doc, so '
            'composing with the defaults would seed a step the dispatcher cannot '
            f'route: {unresolved}. Known canonical keys: {sorted(known)}'
        )

    def test_default_set_is_written_in_ascending_frontmatter_order(self):
        known = self._order_by_canonical_key()
        resolved = [
            (step, known[step])
            for step in _manifest_core.DEFAULT_PHASE_6_STEPS
            if step in known
        ]

        orders = [order for _, order in resolved]

        assert orders == sorted(orders), (
            'DEFAULT_PHASE_6_STEPS is no longer written in ascending frontmatter '
            'order. Its own comment states the sequence is kept in lock-step with '
            'each step doc\'s order fact, so a sequence that disagrees reads as a '
            'second, competing statement of the pipeline order. Resolved '
            f'(step, order) pairs as written: {resolved}'
        )
