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


class TestShortCircuitCarveOut:
    def _item_4b(self) -> str:
        return _between(
            _read(_FINALIZE_SKILL),
            '4b. Lessons-capture Signal Gate',
            '4c. Adr-propose Signal Gate',
        )

    def test_orchestration_resolution_precedes_the_short_circuit(self):
        item = self._item_4b()

        assert item.index('a0. Resolve orchestration context') < item.index('b. Three-zero short-circuit')

    def test_resolution_is_documented_as_running_before_the_short_circuit(self):
        assert 'runs BEFORE the three-zero short-circuit' in self._item_4b()

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

    def test_the_write_site_list_is_recorded_at_the_resolution_site(self):
        item = self._item_4b()

        assert 'default:lessons-capture' in item
        assert 'plan-marshall:plan-retrospective' in item
        assert 'default:finalize-step-preference-emitter' in item
        # Plan 302 D1: the terminal emission step is the fourth epic-inbox write-site.
        assert 'default:emit-landing' in item
        assert 'MUST be added to this list' in item

    def test_body_declares_both_runtime_inputs(self):
        text = _read(_LESSONS_CAPTURE)

        assert '- `orchestrated` — bool;' in text
        assert '- `epic` — string;' in text
        assert 'MUST NOT re-issue either call' in text


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
