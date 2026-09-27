#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Contract tests for the finalize orchestration routing split.

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
- **The verdict is resolved at Step 3 entry, not inside a step's gate** — the
  ``a0`` resolution block precedes the ``FOR each step_id`` loop and sits outside
  the item-4b lessons-capture gate, so item 1's resumable skip of an
  already-``done`` lessons-capture cannot starve the later consumers of it.
- **emit-landing fails closed** — its Step 0 guard records ``loop_back`` (never
  ``skipped``) on an empty epic, and ``archive-plan`` is ordered after it and
  declares ``destroys: plan-directory``, so that record is what keeps the
  irreversible archive unreached.
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
import extension_discovery
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module
from extension_discovery import find_implementors

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox')
classify_source_id = _inbox.classify_source_id

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_FINALIZE = _PLAN_MARSHALL / 'phase-6-finalize'
_FINALIZE_SKILL = _FINALIZE / 'SKILL.md'
_LESSONS_CAPTURE = _FINALIZE / 'workflow' / 'lessons-capture.md'
_LESSONS_INTEGRATION = _FINALIZE / 'standards' / 'lessons-integration.md'
_PREFERENCE_EMITTER = _FINALIZE / 'standards' / 'finalize-step-preference-emitter.md'
_EMIT_LANDING = _FINALIZE / 'standards' / 'emit-landing.md'
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


#: The label of the Step 3 entry orchestration-resolution block.
_A0_LABEL = 'a0. Resolve orchestration context'

#: The line that opens the Step 3 per-step dispatch loop.
_FOR_LOOP = 'FOR each step_id in manifest.phase_6.steps:'

#: The bounds of the item-4b lessons-capture Signal Gate inside the loop.
_ITEM_4B_START = '4b. Lessons-capture Signal Gate'
_ITEM_4B_END = '4c. Adr-propose Signal Gate'

#: The executor form of the detection call — a prose mention of the verb is not a call.
_DETECT_CALL = 'plan-orchestrator:orchestrator inbox detect'


def _a0_block(text: str) -> str:
    """The Step 3 entry resolution block: from its label up to the FOR loop line.

    Ending the span at the loop line makes the extraction itself fail when the
    block no longer precedes the loop.
    """
    return _between(text, _A0_LABEL, _FOR_LOOP)


def _item_4b(text: str) -> str:
    return _between(text, _ITEM_4B_START, _ITEM_4B_END)


def _resolution_placement_violations(text: str) -> list[str]:
    """The placement predicate under test: why the resolution is NOT at Step 3 entry.

    Factored out so the mutation guard drives the SAME predicate the assertions
    use. An empty list means the ``a0`` block precedes the dispatch loop, occurs
    exactly once, and item 4b neither carries the block nor issues the detection
    call itself.
    """
    violations: list[str] = []
    label_at = text.find(_A0_LABEL)
    loop_at = text.find(_FOR_LOOP)
    if label_at == -1:
        violations.append('resolution block label absent')
    if loop_at == -1:
        violations.append('dispatch loop line absent')
    if label_at != -1 and loop_at != -1 and label_at > loop_at:
        violations.append('resolution block follows the dispatch loop')
    if text.count(_A0_LABEL) != 1:
        violations.append(f'resolution block label occurs {text.count(_A0_LABEL)} times')
    start = text.find(_ITEM_4B_START)
    end = text.find(_ITEM_4B_END, start + 1) if start != -1 else -1
    if start == -1 or end == -1:
        violations.append('item 4b span absent')
    else:
        item = text[start:end]
        if _A0_LABEL in item:
            violations.append('resolution block sits inside item 4b')
        if _DETECT_CALL in item:
            violations.append('item 4b issues the detection call itself')
    return violations


def _frontmatter_order_and_destroys() -> dict[str, tuple[object, list[str]]]:
    """Every discovered finalize step's ``(order, destroys)`` pair, off its own frontmatter."""
    out: dict[str, tuple[object, list[str]]] = {}
    for record in find_implementors(_EXT_POINT):
        fields = extension_discovery._read_frontmatter_fields(Path(str(record.get('path', ''))), ('destroys',))
        declared = fields.get('destroys')
        destroys = [] if declared is None else list(declared) if isinstance(declared, list) else [declared]
        out[str(record.get('name', ''))] = (record.get('order'), destroys)
    return out


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


_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

_BUILT_IN_SOURCE = 'built-in'

_TABLE_START = '### Built-in Step Dispatch Table'

_TABLE_END = '### Interface Contract for External Steps'


def _built_in_records() -> list[dict]:
    """The authoritative built-in step records, straight from discovery."""
    return [record for record in find_implementors(_EXT_POINT) if record.get('source') == _BUILT_IN_SOURCE]


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
    return sorted(record['name'] for record in _built_in_records() if record['name'] not in row_names)


class TestDetectionSeam:
    def test_should_classify_the_pointer_shape_phase_1_init_emits(self):
        pointer = '.plan/orchestrator/truthful-signals/plans/PLAN-55-inbox.md'

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
        pointer = '.plan/orchestrator/../../etc/plans/PLAN-1.md'

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

    def test_dispatcher_issues_both_seam_calls_inside_the_step_3_entry_block(self):
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert 'request read --plan-id {plan_id} --section source_id' in block
        assert _DETECT_CALL in block

    def test_dispatcher_parses_the_detection_token(self):
        # Anchored to the a0 block so the assertion cannot pass on a stray
        # match elsewhere in the SKILL body.
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert '`detection`' in block
        assert 'detection={detection}' in block

    def test_dispatcher_warns_on_an_unrecognised_pointer(self):
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert 'detection == unrecognised_id' in block
        assert '--level WARNING' in block
        # The obligation is to name the pointer, not merely to log something.
        assert '{source_id}' in block


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


class TestResolutionAtStep3Entry:
    """(a) The orchestration verdict is resolved once at Step 3 entry, outside every step's gate.

    Resolved inside item 4b, the verdict was unreachable whenever item 1's
    resumable check SKIPped an already-``done`` lessons-capture, or the manifest
    omitted lessons-capture — exactly the re-entries on which emit-landing then
    saw an empty epic.
    """

    def test_resolution_block_precedes_the_for_loop_and_sits_outside_item_4b(self):
        assert _resolution_placement_violations(_read(_FINALIZE_SKILL)) == []

    def test_placement_predicate_rejects_the_block_moved_back_into_item_4b(self):
        """Mutation guard: re-nesting the block inside item 4b must be caught."""
        text = _read(_FINALIZE_SKILL)
        block = _a0_block(text)
        mutated = text.replace(block, '', 1).replace(_ITEM_4B_START, _ITEM_4B_START + '\n' + block, 1)

        assert 'resolution block sits inside item 4b' in _resolution_placement_violations(mutated)

    def test_placement_predicate_rejects_a_detection_call_inside_item_4b(self):
        """Mutation guard: a second detection call issued from the gate must be caught."""
        text = _read(_FINALIZE_SKILL)
        mutated = text.replace(_ITEM_4B_START, _ITEM_4B_START + '\n' + _DETECT_CALL, 1)

        assert 'item 4b issues the detection call itself' in _resolution_placement_violations(mutated)

    def test_block_states_it_runs_on_every_entry_independent_of_resumable_skip(self):
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert 'independent of every step\'s resumable skip' in block
        assert 'every re-entry' in block

    def test_block_names_the_detect_seam_as_the_sole_classifier(self):
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert '`orchestrator inbox detect` is the sole classifier' in block
        # The transition mailbox probe's verdict is explicitly excluded as an input.
        assert '`probe:` classification is never an input' in block

    def test_the_write_site_list_is_recorded_at_the_resolution_site(self):
        block = _a0_block(_read(_FINALIZE_SKILL))

        assert 'default:lessons-capture' in block
        assert 'plan-marshall:plan-retrospective' in block
        assert 'default:finalize-step-preference-emitter' in block
        # Plan 302 D1: the terminal emission step is the fourth epic-inbox write-site.
        assert 'default:emit-landing' in block
        assert 'MUST be added to this list' in block


class TestShortCircuitCarveOut:
    def _item_4b(self) -> str:
        return _item_4b(_read(_FINALIZE_SKILL))

    def test_resolution_is_documented_as_running_before_the_short_circuit(self):
        """(b) item 4b reads the held verdict and still states the ordering claim."""
        item = self._item_4b()

        assert 'runs BEFORE the three-zero short-circuit' in item
        assert 'issues no resolution call of its own' in item

    def test_short_circuit_fires_regardless_of_orchestration(self):
        """Plan 302 D1: the carve-out that dispatched lessons-capture at
        zero-signals-orchestrated to emit the landing is removed — the landing is
        the dedicated emit-landing step's now, so the short-circuit fires on zero
        signals whether or not the run is orchestrated."""
        item = self._item_4b()

        assert 'fires on zero signals **regardless of orchestration**' in item
        assert 'no longer carries an orchestration carve-out' in item
        assert '`default:emit-landing` terminal step' in item

    def test_short_circuit_condition_is_not_gated_on_orchestration(self):
        item = self._item_4b()

        assert 'When `signal_1_count == 0 AND signal_2_count == 0 AND signal_3_count == 0`' in item
        # The old orchestrated-gated condition is gone.
        assert 'orchestrated == false AND signal_1_count' not in item

    def test_both_runtime_inputs_appear_in_the_forwarded_block(self):
        item = self._item_4b()

        assert 'orchestrated: {true|false}' in item
        assert 'epic: {slug|""}' in item

    def test_body_declares_both_runtime_inputs(self):
        text = _read(_LESSONS_CAPTURE)

        assert '- `orchestrated` — bool;' in text
        assert '- `epic` — string;' in text
        assert 'MUST NOT re-issue either call' in text


class TestEmitLandingEmptyEpicFailsClosed:
    """(c) + (d) An empty epic on a present emit-landing step loops back, never skips.

    A ``skipped`` record does not stop the finalize loop, so ``archive-plan`` —
    ordered after ``emit-landing`` and declaring ``destroys: plan-directory`` —
    would run next and delete the only copy of the run's facts. The ``loop_back``
    record is what keeps archive unreached, and (d) pins the ordering fact that
    makes that true.
    """

    _STEP_0_START = '### Step 0: Defensive orchestration guard'
    _STEP_0_END = '### Step 1:'

    def _step_0(self) -> str:
        return _between(_read(_EMIT_LANDING), self._STEP_0_START, self._STEP_0_END)

    def test_step_0_records_loop_back_to_finalize(self):
        step = self._step_0()

        assert '--outcome loop_back' in step
        assert '--loop-back-target 6-finalize' in step
        assert 'work_performed=false' in step

    def test_step_0_warning_names_the_contradiction(self):
        step = self._step_0()

        assert '--level WARNING' in step
        assert 'orchestration verdict contradiction' in step

    def test_no_skipped_outcome_call_remains_in_emit_landing(self):
        assert '--outcome skipped' not in _read(_EMIT_LANDING)

    def test_archive_plan_destroys_the_plan_directory_after_emit_landing(self):
        declared = _frontmatter_order_and_destroys()
        assert 'default:emit-landing' in declared, 'emit-landing is not a discovered finalize step'
        assert 'default:archive-plan' in declared, 'archive-plan is not a discovered finalize step'

        landing_order, _ = declared['default:emit-landing']
        archive_order, archive_destroys = declared['default:archive-plan']

        assert 'plan-directory' in archive_destroys
        assert isinstance(landing_order, int) and isinstance(archive_order, int)
        assert archive_order > landing_order, (
            f'archive-plan (order {archive_order}) must run after emit-landing (order '
            f'{landing_order}); only then is emit-landing\'s loop_back record what keeps '
            'the destroying archive step unreached.'
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

        unresolved = [step for step in _manifest_core.DEFAULT_PHASE_6_STEPS if step not in known]

        assert unresolved == [], (
            'These default candidate steps resolve to no discovered step doc, so '
            'composing with the defaults would seed a step the dispatcher cannot '
            f'route: {unresolved}. Known canonical keys: {sorted(known)}'
        )

    def test_default_set_is_written_in_ascending_frontmatter_order(self):
        known = self._order_by_canonical_key()
        resolved = [(step, known[step]) for step in _manifest_core.DEFAULT_PHASE_6_STEPS if step in known]

        orders = [order for _, order in resolved]

        assert orders == sorted(orders), (
            'DEFAULT_PHASE_6_STEPS is no longer written in ascending frontmatter '
            'order. Its own comment states the sequence is kept in lock-step with '
            "each step doc's order fact, so a sequence that disagrees reads as a "
            'second, competing statement of the pipeline order. Resolved '
            f'(step, order) pairs as written: {resolved}'
        )


class TestCanonicalDestroysDeclarationsExist:
    """The two `destroys` declarations both normative documents anchor the vocabulary on.

    `finalize-step-order-bands.md` § "`reads` and `destroys`" and
    `ext-point-finalize-step.md`'s `destroys` row each introduce the vocabulary by naming
    the same two declarations as its worked anchors. Both documents therefore assert a fact
    about frontmatter, and until this class existed nothing checked either one: deleting a
    `destroys:` block left both standards describing a capability with no instance, and the
    ordering obligation each anchor encodes — do not order a reader of X after the step that
    destroys X — would have been silently unenforceable.

    The declarations are read straight off each step's own discovered doc, so the assertion
    tracks the frontmatter rather than a second transcription of it.
    """

    #: step id → (artifact it destroys, the ordering obligation the declaration serves).
    _ANCHORS = {
        'default:archive-plan': (
            'plan-directory',
            'archive-plan moves the plan directory, so every step that reads plan state must be ordered before it',
        ),
        'default:branch-cleanup': (
            'worktree',
            'the merge gate removes the linked worktree, so every step that reads the '
            'worktree must be ordered before it',
        ),
    }

    def _destroys_by_name(self) -> dict[str, list[str]]:
        """Every discovered step's `destroys:` declaration, read off its own frontmatter."""
        out: dict[str, list[str]] = {}
        for record in find_implementors(_EXT_POINT):
            fields = extension_discovery._read_frontmatter_fields(Path(str(record.get('path', ''))), ('destroys',))
            declared = fields.get('destroys')
            if declared is None:
                continue
            out[str(record.get('name', ''))] = list(declared) if isinstance(declared, list) else [declared]
        return out

    def test_discovery_is_non_empty(self):
        """Anti-vacuity: an empty discovery would make every assertion below trivial."""
        assert find_implementors(_EXT_POINT), (
            f'find_implementors({_EXT_POINT!r}) resolved no finalize steps, so the '
            '`destroys` anchor assertions would have nothing to read.'
        )

    def test_each_canonical_anchor_declares_its_artifact(self):
        declared = self._destroys_by_name()

        for step, (artifact, obligation) in self._ANCHORS.items():
            assert step in declared, (
                f'{step} declares no `destroys:` frontmatter. Two normative documents — '
                'extension-api/standards/finalize-step-order-bands.md § "`reads` and '
                '`destroys`" and ext-point-finalize-step.md\'s `destroys` row — introduce '
                f'the vocabulary by naming this declaration as an anchor, and it serves a '
                f'real ordering obligation: {obligation}. Removing it leaves both standards '
                'describing a capability with no instance.'
            )
            assert artifact in declared[step], (
                f'{step} declares `destroys: {declared[step]}`, which does not name '
                f'{artifact!r}. Both standards anchor the vocabulary on exactly that token, '
                f'and the obligation it encodes is: {obligation}.'
            )
