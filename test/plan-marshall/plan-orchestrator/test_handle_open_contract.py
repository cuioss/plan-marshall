#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting contract suite for the `handle-open` verb.

The `handle-open` verb is prose: a routing row, a workflow document and a
contract section in the orchestration standard. There is no script seam a test
can invoke, so the contract is pinned where it actually lives — in the documents
— and every pin is paired with a MATCHED CONTROL that plants the violation in a
temporary tree and shows the same detector firing. A detector with no control
would pass by never being able to fail, which is exactly the shape this plan is
written against.

Every governed population is derived at test time and every count-bearing
assertion publishes it: the workflow directory is enumerated from disk, the
marketplace markdown tree is scanned for the cap definition, and the step
sequence is read out of the document rather than restated as a constant.

The pins, one group each:

- **(a) Step order** — the workflow's `### Step N:` headings are complete and
  ordered from 1.
- **(b) Threshold surface** — the document reads the knob, carries the
  fail-closed sentence, and states no seeded default figure of its own (the
  default lives in `DEFAULT_ORCHESTRATOR`, restated only by the data-model
  table).
- **(c) Presentation** — no `AskUserQuestion` fenced block, and the
  plain-text, one-item-per-turn shape named.
- **(d) Prohibitions** — all eight prohibitions of the contract's decision-acts
  bullet appear in the workflow by name.
- **(d2) Single definition** — the confidence-cap rule is defined in exactly one
  marketplace document (the standard) and xref'd by the workflow.
- **(e) Reporting** — the Output block carries a per-source population line.
- **(f) Dispatch** — the dispatch resolves on `orchestrator.analyze` and names
  the concrete `--workflow` document the leaf loads.
- **(g) Contract presence** — the standard carries the `Handle-Open Contract`
  heading, the persona names the one exception, and the router routes the verb.
- **(h) Decision semantics** — Step 6 keeps the reworded invalidation sentence and
  the item-number ordering, and states no reopen or supersede act of its own: the
  contract carries four bounded decision acts, and a reopen rule would need its own
  act, its own Idempotence carve-out and its own Output row.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

_BUNDLE = Path(MARKETPLACE_ROOT) / 'plan-marshall' / 'skills'
WORKFLOW_DIR: Path = _BUNDLE / 'plan-orchestrator' / 'workflow'
WORKFLOW_DOC: Path = WORKFLOW_DIR / 'handle-open.md'
ROUTER: Path = _BUNDLE / 'plan-orchestrator' / 'SKILL.md'
STANDARD: Path = _BUNDLE / 'persona-plan-orchestrator' / 'standards' / 'orchestration-model.md'
PERSONA: Path = _BUNDLE / 'persona-plan-orchestrator' / 'SKILL.md'

#: The contract section the workflow xrefs and never restates.
CONTRACT_HEADING = 'Handle-Open Contract'

#: The concrete document the analysis leaf loads, as the dispatch resolve's
#: `--workflow` names it. A placeholder (`{the doc the leaf loads}`) would satisfy
#: the flag-presence pin while leaving the [DISPATCH] record unable to say what
#: the leaf read.
DISPATCH_WORKFLOW_DOC = 'plan-marshall:plan-orchestrator/workflow/handle-open.md'

#: The knob the threshold is read through.
KNOB = 'decision_confidence_threshold'

#: The seeded figure, DERIVED from the constant that owns it rather than pinned as
#: a literal. A hard-coded `90` here would silently stop guarding the moment the
#: seed changed — and the pin's whole subject is that the workflow must not
#: restate whatever the seed says.
_config_defaults_mod = load_script_module(
    'plan-marshall',
    'manage-config',
    '_config_defaults.py',
    module_name='_config_defaults_for_handle_open_contract_test',
)
SEEDED_FIGURE = _config_defaults_mod.DEFAULT_ORCHESTRATOR.get(KNOB)
SEEDED_FIGURE_RE = re.compile(rf'\b{SEEDED_FIGURE}\b') if isinstance(SEEDED_FIGURE, int) else None

#: The canonical prohibition population is read OUT of the contract's decision-acts
#: bullet at test time, never mirrored here, and the read is SCOPED to that bullet:
#: a `NEVER **…**` phrase in another section is not a handle-open prohibition and
#: must not be able to satisfy (or inflate) this population.
_CONTRACT_PROHIBITION_RE = re.compile(r'NEVER \*\*(?P<phrase>[^*]+)\*\*')
_DECISION_ACTS_START = '- **Decision acts.**'
_DECISION_ACTS_END = '\n- **Presentation.**'


def _decision_acts_bullet(text: str) -> str:
    """The contract's decision-acts bullet alone, or ``''`` when it is absent."""
    start = text.find(_DECISION_ACTS_START)
    if start < 0:
        return ''
    end = text.find(_DECISION_ACTS_END, start)
    return text[start:end] if end >= 0 else text[start:]


def _contract_prohibitions(text: str) -> list[str]:
    """Every prohibition the decision-acts bullet states, lowercased."""
    return [
        f'never {phrase.strip().lower()}' for phrase in _CONTRACT_PROHIBITION_RE.findall(_decision_acts_bullet(text))
    ]


#: The one-sentence form of the confidence-cap rule. Its DEFINITION belongs to
#: the standard alone; any second carrier is a duplicate definition of one
#: concept, which the plan's Standing Constraints forbid.
#:
#: ⚠ Stated boundary: this is a LEXICAL detector. It catches the rule stated in
#: the project's own vocabulary (a claim that is not re-read "caps the item"), not
#: an arbitrary paraphrase of it. What keeps the boundary from being the whole
#: guard is that the workflow also has to carry the contract xref and must not
#: carry this marker, so a re-wording would have to be a deliberate restatement
#: rather than a copy.
CAP_DEFINITION_MARKER = 'caps the item'

_STEP_HEADING_RE = re.compile(r'^### Step (\d+):', re.MULTILINE)
_FENCE_RE = re.compile(r'```[^\n]*\n([\s\S]*?)```')
_FAIL_CLOSED_RE = re.compile(r'cannot be read[\s\S]{0,240}?resolves to `?100`?', re.IGNORECASE)
_POPULATION_LINE_RE = re.compile(
    r'^sources\[[A-Za-z]+\]\{[^}]*\bpopulation\b[^}]*\bitems\b[^}]*\}:',
    re.MULTILINE,
)
_DISPATCH_RE = re.compile(r'effort resolve-target --role orchestrator\.analyze[^`\n]*')


# =============================================================================
# Detectors — every one takes the text it governs, so a control can plant a
# violation in a fixture rather than mutating the live tree.
# =============================================================================


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _normalized(text: str) -> str:
    """Strip markdown emphasis and collapse whitespace, lowercased."""
    return re.sub(r'\s+', ' ', text.replace('**', '').replace('`', '')).strip().lower()


def _step_numbers(text: str) -> list[int]:
    return [int(number) for number in _STEP_HEADING_RE.findall(text)]


def _steps_are_complete_and_ordered(numbers: list[int]) -> bool:
    return numbers == list(range(1, len(numbers) + 1))


def _fenced_blocks(text: str) -> list[str]:
    return _FENCE_RE.findall(text)


def _askuserquestion_blocks(text: str) -> list[str]:
    return [block for block in _fenced_blocks(text) if 'AskUserQuestion' in block]


def _names_plain_text_one_per_turn(text: str) -> bool:
    lowered = text.lower()
    return 'plain text' in lowered and 'one item per turn' in lowered


def _names_knob(text: str) -> bool:
    return KNOB in text


def _carries_fail_closed_sentence(text: str) -> bool:
    return bool(_FAIL_CLOSED_RE.search(text))


def _restates_seeded_default(text: str) -> bool:
    """Whether the text restates the seeded figure of the knob.

    Returns ``False`` when no integer seed is resolvable. That is a guard for a
    FUTURE removal of the knob from ``DEFAULT_ORCHESTRATOR`` (the tree would then
    have no figure for the workflow to restate); the base-sha run does not reach
    it, because the module itself does not exist at that commit.
    """
    return bool(SEEDED_FIGURE_RE.search(text)) if SEEDED_FIGURE_RE is not None else False


def _missing_prohibitions(text: str, prohibitions: tuple[str, ...] | list[str]) -> list[str]:
    normalized = _normalized(text)
    return [prohibition for prohibition in prohibitions if prohibition not in normalized]


def _carries_per_source_population(text: str) -> bool:
    return bool(_POPULATION_LINE_RE.search(text))


def _cap_definition_carriers(root: Path) -> list[Path]:
    """Every markdown document under ``root`` that carries the cap definition."""
    return [
        path
        for path in sorted(root.rglob('*.md'))
        if CAP_DEFINITION_MARKER in path.read_text(encoding='utf-8', errors='ignore')
    ]


def _dispatch_invocations(text: str) -> list[str]:
    return _DISPATCH_RE.findall(text)


def _has_section_heading(text: str, heading: str) -> bool:
    return any(line.strip() == f'## {heading}' for line in text.splitlines())


def _xrefs_contract_without_restating_the_cap(text: str) -> bool:
    """Whether the text names the contract section and carries no cap marker."""
    return CONTRACT_HEADING in text and CAP_DEFINITION_MARKER not in text


def _persona_names_the_exception(text: str) -> bool:
    """Attribute 9 names `handle-open` and xrefs the contract anchor."""
    for line in text.splitlines():
        if line.startswith('9. '):
            return 'handle-open' in line and CONTRACT_HEADING in line
    return False


_ROUTER_ROW_RE = re.compile(r'^\|\s*`handle-open`\s*\|\s*`workflow/handle-open\.md`\s*\|', re.MULTILINE)


def _routes_the_workflow_doc(text: str) -> bool:
    """Whether the Verb Routing table carries the `handle-open` → doc row."""
    return bool(_ROUTER_ROW_RE.search(text))


#: The four facts a real dispatch resolve carries. `--workflow` is the one that
#: makes the seam emit the [DISPATCH] record; the other three identify the caller
#: and state that an epic is not a plan.
DISPATCH_REQUIRED_FACTS: tuple[str, ...] = (
    '--role orchestrator.analyze',
    '--plan-id none',
    '--caller plan-marshall:persona-plan-orchestrator',
    '--workflow',
)


def _missing_dispatch_facts(invocation: str) -> list[str]:
    return [fact for fact in DISPATCH_REQUIRED_FACTS if fact not in invocation]


# =============================================================================
# (a) Step order
# =============================================================================


class TestWorkflowStepOrder:
    def test_the_document_exists_among_the_workflow_docs(self):
        # Existence only: whether the router ROUTES it is a separate pin
        # (`TestContractPresence::test_the_router_routes_the_verb`), so a
        # name that claims both would overstate what this one proves.
        workflow_docs = {path.name for path in WORKFLOW_DIR.glob('*.md')}

        assert workflow_docs, f'no workflow document enumerated under {WORKFLOW_DIR}'
        assert WORKFLOW_DOC.name in workflow_docs, (
            f'{WORKFLOW_DOC.name} is not among the {len(workflow_docs)} workflow document(s) on disk: '
            f'{sorted(workflow_docs)}'
        )

    def test_the_steps_are_complete_and_ordered(self):
        numbers = _step_numbers(_read(WORKFLOW_DOC))

        assert numbers, 'the workflow document carries no `### Step N:` heading at all'
        assert _steps_are_complete_and_ordered(numbers), (
            f'the workflow steps are not 1..N in order: {numbers} — a dropped or renumbered step '
            'would produce exactly this gap'
        )

    def test_a_dropped_step_is_detected(self, tmp_path):
        fixture = tmp_path / 'dropped-step.md'
        fixture.write_text(
            '### Step 1: first\n\n### Step 3: third\n',
            encoding='utf-8',
        )

        numbers = _step_numbers(_read(fixture))

        assert numbers == [1, 3]
        assert not _steps_are_complete_and_ordered(numbers), (
            'a document numbering 1 then 3 was read as complete and ordered'
        )


# =============================================================================
# (b) Threshold surface
# =============================================================================


class TestThresholdSurface:
    def test_the_document_reads_the_threshold_through_the_knob(self):
        text = _read(WORKFLOW_DOC)

        assert _names_knob(text), f'the workflow document never names the {KNOB!r} knob'

    def test_a_document_that_never_names_the_knob_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-knob.md'
        fixture.write_text('Read the configured threshold and compare.\n', encoding='utf-8')

        assert not _names_knob(_read(fixture))

    def test_the_document_carries_the_fail_closed_sentence(self):
        assert _carries_fail_closed_sentence(_read(WORKFLOW_DOC)), (
            'the workflow document does not state that an unreadable threshold (or an out-of-range '
            'argument) resolves to 100 for the run — an unreadable setting must never license a '
            'decision'
        )

    def test_the_document_states_no_seeded_default_figure(self):
        assert not _restates_seeded_default(_read(WORKFLOW_DOC)), (
            'the workflow document restates the seeded default figure; the default lives in '
            'DEFAULT_ORCHESTRATOR and is restated only by the data-model table'
        )

    def test_the_seeded_figure_is_resolved_from_the_constant(self):
        # Non-vacuity: a renamed or removed seed would turn the pin above into a
        # check that can never fire, which is the silent-retirement shape.
        assert isinstance(SEEDED_FIGURE, int), (
            f'DEFAULT_ORCHESTRATOR carries no integer {KNOB!r}, so the no-restatement pin guards nothing'
        )
        assert 0 <= SEEDED_FIGURE <= 100, f'the seeded figure {SEEDED_FIGURE} is outside the knob range'

    def test_a_hard_coded_default_is_detected(self, tmp_path):
        # The planted figure is INTERPOLATED from the constant, never typed: a
        # literal here would go stale with the seed and make this control fail
        # for the wrong reason the moment the seed moved.
        fixture = tmp_path / 'hard-coded-default.md'
        fixture.write_text(
            f'The threshold defaults to {SEEDED_FIGURE} and is read from the {KNOB} knob. '
            'A threshold that cannot be read resolves to `100` for the run.\n',
            encoding='utf-8',
        )

        text = _read(fixture)

        assert _restates_seeded_default(text), 'the detector missed a hard-coded default figure'

    def test_a_document_without_the_fail_closed_sentence_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-fail-closed.md'
        fixture.write_text(f'Read the {KNOB} knob and compare.\n', encoding='utf-8')

        assert not _carries_fail_closed_sentence(_read(fixture))


# =============================================================================
# (c) Presentation
# =============================================================================


class TestPresentation:
    def test_no_fenced_block_carries_an_askuserquestion_call(self):
        text = _read(WORKFLOW_DOC)

        blocks = _fenced_blocks(text)
        offenders = _askuserquestion_blocks(text)

        assert blocks, 'the workflow document carries no fenced block at all — the scan is vacuous'
        assert offenders == [], (
            f'{len(offenders)} of {len(blocks)} fenced block(s) carry an AskUserQuestion call; this '
            'verb presents in plain text and never through the question tool'
        )

    def test_the_plain_text_one_per_turn_shape_is_named(self):
        assert _names_plain_text_one_per_turn(_read(WORKFLOW_DOC)), (
            'the workflow document does not name the plain-text, one-item-per-turn presentation'
        )

    def test_a_planted_askuserquestion_block_is_detected(self, tmp_path):
        fixture = tmp_path / 'planted.md'
        fixture.write_text(
            'Ask the operator:\n\n```text\nAskUserQuestion({question: "pick one"})\n```\n',
            encoding='utf-8',
        )

        assert len(_askuserquestion_blocks(_read(fixture))) == 1

    def test_a_document_without_the_presentation_shape_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-shape.md'
        fixture.write_text('Present the items in plain text.\n', encoding='utf-8')

        assert not _names_plain_text_one_per_turn(_read(fixture))


# =============================================================================
# (d) Prohibitions, named in both the contract and the workflow
# =============================================================================


class TestProhibitions:
    def test_the_contract_states_a_non_empty_prohibition_population(self):
        prohibitions = _contract_prohibitions(_read(STANDARD))

        assert prohibitions, 'the contract states no prohibition in its decision-acts bullet — the population is empty'
        assert len(set(prohibitions)) == len(prohibitions), f'the contract states a prohibition twice: {prohibitions}'

    def test_the_workflow_names_every_prohibition_by_name(self):
        text = _read(WORKFLOW_DOC)
        prohibitions = _contract_prohibitions(_read(STANDARD))

        missing = _missing_prohibitions(text, prohibitions)

        assert missing == [], (
            f'{len(missing)} of {len(prohibitions)} prohibitions are not named by the workflow document: {missing}'
        )

    def test_a_prohibition_outside_the_decision_acts_bullet_is_not_counted(self, tmp_path):
        # The scope control: the extraction reads the decision-acts bullet ONLY, so
        # a `NEVER **…**` phrase in another section neither satisfies the population
        # check nor inflates it.
        fixture = tmp_path / 'scoped-contract.md'
        fixture.write_text(
            '- **Decision acts.** It NEVER **stages a plan**.\n'
            '- **Presentation.** It NEVER **uses the question tool**.\n',
            encoding='utf-8',
        )

        prohibitions = _contract_prohibitions(_read(fixture))

        assert prohibitions == ['never stages a plan'], f'an out-of-bullet phrase was counted: {prohibitions}'

    def test_a_dropped_prohibition_is_detected(self, tmp_path):
        prohibitions = _contract_prohibitions(_read(STANDARD))
        complete = _normalized(_read(WORKFLOW_DOC))
        dropped = prohibitions[2]
        assert dropped in complete, 'the fixture source was supposed to carry the prohibition being dropped'

        seeded = complete.replace(dropped, '')
        fixture = tmp_path / 'dropped-prohibition.md'
        fixture.write_text(seeded, encoding='utf-8')

        missing = _missing_prohibitions(_read(fixture), prohibitions)

        assert missing == [dropped], f'the detector reported {missing} for a single dropped prohibition'


# =============================================================================
# (d2) One definition of the confidence-cap rule
# =============================================================================


class TestSingleCapDefinition:
    def test_the_marketplace_population_is_non_empty_and_contains_the_standard(self):
        population = _cap_definition_carriers(Path(MARKETPLACE_ROOT))

        assert population, 'no marketplace document carries the cap definition — the scan is vacuous'
        assert population == [STANDARD], (
            f'of the marketplace markdown tree, these documents carry the confidence-cap definition: '
            f'{[str(path) for path in population]} — exactly one carrier is allowed, and it is the standard'
        )

    def test_the_workflow_xrefs_the_contract_instead_of_restating_the_cap(self):
        assert _xrefs_contract_without_restating_the_cap(_read(WORKFLOW_DOC)), (
            f'the workflow document does not xref the {CONTRACT_HEADING!r} section by name, or it '
            'restates the confidence-cap rule instead of xrefing it'
        )

    def test_a_workflow_that_does_not_xref_the_contract_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-xref.md'
        fixture.write_text('A rule that caps the item, with no section named.\n', encoding='utf-8')

        assert not _xrefs_contract_without_restating_the_cap(_read(fixture))

    def test_a_workflow_that_xrefs_and_does_not_restate_is_accepted(self, tmp_path):
        # The negative half of the control above: a well-formed xref must read as
        # conforming, so the detector is not merely rejecting everything.
        fixture = tmp_path / 'clean-xref.md'
        fixture.write_text(f'See § {CONTRACT_HEADING} for the rule.\n', encoding='utf-8')

        assert _xrefs_contract_without_restating_the_cap(_read(fixture))

    def test_a_second_definition_is_detected(self, tmp_path):
        (tmp_path / 'standard.md').write_text('A claim re-read nowhere caps the item.', encoding='utf-8')
        (tmp_path / 'second.md').write_text('A duplicated rule that also caps the item.', encoding='utf-8')

        carriers = _cap_definition_carriers(tmp_path)

        assert [path.name for path in carriers] == ['second.md', 'standard.md'], (
            f'a second definition was not detected: {[path.name for path in carriers]}'
        )


# =============================================================================
# (e) Reporting
# =============================================================================


class TestReporting:
    def test_the_output_block_carries_a_per_source_population_line(self):
        text = _read(WORKFLOW_DOC)

        assert _carries_per_source_population(text), (
            'the Output block carries no `sources[...]{...,population,...,items,...}` line, so a '
            'source holding nothing and a source that could not be read are not distinguishable'
        )

    def test_a_missing_population_line_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-population.md'
        fixture.write_text(
            '```toon\nstatus: success\nsources[S]{source,state}:\n  Open Defects,read\n```\n',
            encoding='utf-8',
        )

        assert not _carries_per_source_population(_read(fixture))


# =============================================================================
# (f) Dispatch surface and workflow document
# =============================================================================


class TestDispatchPin:
    def test_the_dispatch_resolves_on_the_analyze_surface_and_names_its_document(self):
        invocations = _dispatch_invocations(_read(WORKFLOW_DOC))

        matching = [text for text in invocations if DISPATCH_WORKFLOW_DOC in text]

        assert len(matching) == 1, (
            f'the workflow carries {len(matching)} dispatch invocation(s) naming `--workflow '
            f'{DISPATCH_WORKFLOW_DOC}` across {len(invocations)} invocation(s) — the analysis dispatch '
            'must name the document the leaf loads, concretely'
        )
        missing = _missing_dispatch_facts(matching[0])

        assert missing == [], f'the analysis dispatch omits {missing}: {matching[0]!r}'

    def test_a_placeholder_workflow_argument_is_detected(self, tmp_path):
        fixture = tmp_path / 'placeholder.md'
        fixture.write_text(
            'Resolve via `manage-config effort resolve-target --role orchestrator.analyze --plan-id none '
            '--caller plan-marshall:persona-plan-orchestrator --workflow {the doc the leaf loads}`.\n',
            encoding='utf-8',
        )

        invocations = _dispatch_invocations(_read(fixture))

        assert len(invocations) == 1
        assert DISPATCH_WORKFLOW_DOC not in invocations[0]

    def test_a_dispatch_missing_a_required_fact_is_detected(self, tmp_path):
        # The four-fact loop's control: a whole-looking invocation that resolves
        # the right surface on the right document but drops `--caller` leaves no
        # attributable [DISPATCH] record and must be reported.
        fixture = tmp_path / 'missing-caller.md'
        fixture.write_text(
            'Resolve via `manage-config effort resolve-target --role orchestrator.analyze --plan-id none '
            f'--workflow {DISPATCH_WORKFLOW_DOC}`.\n',
            encoding='utf-8',
        )

        invocation = _dispatch_invocations(_read(fixture))[0]

        assert _missing_dispatch_facts(invocation) == ['--caller plan-marshall:persona-plan-orchestrator']


# =============================================================================
# (g) Contract presence across the three documents
# =============================================================================


class TestContractPresence:
    def test_the_standard_carries_the_contract_heading(self):
        assert _has_section_heading(_read(STANDARD), CONTRACT_HEADING), (
            f'the standard carries no `## {CONTRACT_HEADING}` section'
        )

    def test_the_persona_names_the_one_exception(self):
        assert _persona_names_the_exception(_read(PERSONA)), (
            "the persona's identity attribute 9 does not name `handle-open` and xref the contract"
        )

    def test_the_router_routes_the_verb(self):
        assert _routes_the_workflow_doc(_read(ROUTER)), (
            'the Verb Routing table carries no `handle-open` row pointing at workflow/handle-open.md'
        )

    def test_a_router_without_the_row_is_detected(self, tmp_path):
        fixture = tmp_path / 'router.md'
        fixture.write_text(
            '| Verb | Workflow doc | Purpose |\n|------|--------------|---------|\n'
            '| `cleanup` | `workflow/cleanup.md` | Reconcile the corpus |\n',
            encoding='utf-8',
        )

        assert not _routes_the_workflow_doc(_read(fixture))

    def test_a_missing_section_heading_is_detected(self, tmp_path):
        fixture = tmp_path / 'no-section.md'
        fixture.write_text(f'## {CONTRACT_HEADING} Annex\n\n## Other\n', encoding='utf-8')

        assert not _has_section_heading(_read(fixture), CONTRACT_HEADING)

    def test_a_persona_without_the_exception_is_detected(self, tmp_path):
        fixture = tmp_path / 'persona.md'
        fixture.write_text(
            '9. **Decision surfacing.** Genuine forks are surfaced via `AskUserQuestion`.\n',
            encoding='utf-8',
        )

        assert not _persona_names_the_exception(_read(fixture))


# =============================================================================
# (h) Decision semantics — the reworded sentence stays, no reopen act appears
# =============================================================================

_STEP6_START = '### Step 6:'
_STEP7_START = '### Step 7:'
_IDEMPOTENCE_START = '## Idempotence'
_OUTPUT_START = '## Output'

#: The sentence the PLAN-LB-165 reword introduced, whose "its" ambiguity it fixes:
#: the analysis that changes is THE ITEM's, not the other item's.
_REWORDED_SENTENCE = "An item whose analysis is changed by another item's decision is re-analysed"

#: The item-number ordering, kept as a stand-alone statement.
_ORDERING_SENTENCE = 'Decisions are applied in item-number order.'

#: Vocabulary that would state a reopen/supersede act. None of it belongs in a
#: workflow whose contract carries four bounded decision acts and no reopen row.
_REOPEN_VOCABULARY: tuple[str, ...] = ('supersed', 'reopen')


def _decision_semantics_block(text: str) -> str:
    """Step 6's own text, from its heading to Step 7's."""
    return _between_bounded(text, _STEP6_START, _STEP7_START, 'handle-open.md')


def _between_bounded(text: str, start_marker: str, end_marker: str, source: str) -> str:
    start = text.find(start_marker)
    assert start != -1, f'{source}: the block {start_marker!r} was not found'
    tail = text[start + len(start_marker) :]
    end = tail.find(end_marker)
    assert end != -1, f'{source}: the block {start_marker!r} has no closing marker {end_marker!r}'
    return tail[:end]


def _reopen_vocabulary(text: str) -> list[str]:
    """Every reopen/supersede marker the text carries, casefolded."""
    lowered = text.casefold()
    return [marker for marker in _REOPEN_VOCABULARY if marker in lowered]


def _names_reworded_sentence(text: str) -> bool:
    return _normalized(_REWORDED_SENTENCE) in _normalized(text)


def _idempotence_block(text: str) -> str:
    return _between_bounded(text, _IDEMPOTENCE_START, _OUTPUT_START, 'handle-open.md')


class TestStepSixDecisionSemantics:
    def test_the_reworded_invalidation_sentence_stays(self):
        block = _decision_semantics_block(_read(WORKFLOW_DOC))

        assert _names_reworded_sentence(block), (
            "Step 6 no longer carries the reworded sentence — 'another item's decision' must stay "
            'attributable to the item whose analysis changed'
        )

    def test_step_six_states_no_reopen_or_supersede_act(self):
        block = _decision_semantics_block(_read(WORKFLOW_DOC))

        offenders = _reopen_acts(block)
        assert offenders == [], (
            f'Step 6 states a reopen/supersede act ({offenders}) that the contract does not carry: no '
            'decision act, no Idempotence carve-out and no Output row admit it'
        )

    def test_the_item_number_ordering_stays_as_a_stand_alone_sentence(self):
        text = _read(WORKFLOW_DOC)
        block = _decision_semantics_block(text)

        assert _ORDERING_SENTENCE in block, 'Step 6 no longer states that decisions are applied in item-number order'
        assert '; an item decided earlier' not in text, (
            'the item-number ordering still carries a reopen clause after it'
        )

    def test_the_idempotence_rule_still_forbids_a_second_decision(self):
        block = _idempotence_block(_read(WORKFLOW_DOC))

        assert 'is not decided again' in block, (
            'the Idempotence rule no longer says a decided item is not decided again — the sentence '
            'that would need a carve-out for a reopen act is gone'
        )

    def test_the_contract_states_no_reopen_act(self):
        prohibitions = _contract_prohibitions(_read(STANDARD))
        decision_acts = _decision_acts_bullet(_read(STANDARD)).casefold()

        assert prohibitions, 'the contract states no prohibition in its decision-acts bullet'
        assert _reopen_vocabulary(decision_acts) == [], (
            'the handle-open contract states a reopen/supersede act — a reopen rule exists only if the '
            'contract gains the act, its Idempotence carve-out and its Output row in the same plan'
        )

    def test_a_planted_reopen_clause_is_detected(self, tmp_path):
        text = _read(WORKFLOW_DOC)
        planted = text.replace(
            _ORDERING_SENTENCE,
            f'{_ORDERING_SENTENCE}; an item decided earlier that a later decision invalidates is reopened '
            'by recording a new decision entry that supersedes the previous one.',
        )
        fixture = tmp_path / 'planted-reopen.md'
        fixture.write_text(planted, encoding='utf-8')

        assert _reopen_vocabulary(_decision_semantics_block(_read(fixture))), 'a planted reopen act must be reported'

    def test_a_removed_reworded_sentence_is_detected(self, tmp_path):
        text = _read(WORKFLOW_DOC)
        fixture = tmp_path / 'no-reword.md'
        fixture.write_text(
            text.replace(_REWORDED_SENTENCE, 'An item changed by a decision is re-analysed'), encoding='utf-8'
        )

        assert not _names_reworded_sentence(_decision_semantics_block(_read(fixture))), (
            'a removed reworded sentence must be reported'
        )


#: A POSITIVE reopen/supersede act, in the shapes the contract forbids. `supersed` and
#: `reopen` are the stems the old pin looked for; the rest are acts worded around them,
#: which the same rule forbids.
_REOPEN_ACT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r'\bsupersed\w*',
        r'\breopen\w*',
        r'\bre-?decid\w*',
        r'\bdecided\s+afresh\b',
        r'\bdecided\s+again\b',
        r'\ba\s+fresh\s+decision\b',
        r'\bnew\s+decision\s+(?:entry\s+)?replaces\b',
        r'\b(?:void|undo)\w*\s+(?:the|that)\s+decision\b',
    )
)

#: A negation, which turns a mention of the vocabulary into a prohibition rather than an
#: act. The lane's own text says a later decision "does not reopen" an earlier one.
_NEGATION_RE = re.compile(
    r'\b(?:not|never|no|cannot|without|refuses?|forb(?:id|ids|idden))\b',
    re.IGNORECASE,
)


def _reopen_acts(text: str) -> list[str]:
    """Every POSITIVE reopen act the text states; a negated mention is a prohibition."""
    acts: list[str] = []
    for sentence in re.split(r'(?<=[.!?:])\s+', text):
        if _NEGATION_RE.search(sentence):
            continue
        for pattern in _REOPEN_ACT_PATTERNS:
            match = pattern.search(sentence)
            if match is not None:
                acts.append(match.group(0).casefold())
    return acts


class TestNoReopenActAnywhereInTheDocument:
    """The no-reopen rule is a property of the WHOLE document, not of Step 6.

    A reopen act worded around the old stems, a `Reopen` bullet outside Step 6, and an
    Idempotence carve-out all passed the narrower pin. Each shape is planted and shown
    to be detected.
    """

    def test_the_whole_document_states_no_reopen_act(self):
        assert _reopen_acts(_read(WORKFLOW_DOC)) == [], (
            'handle-open.md states a reopen act; the contract has no reopen act, so no workflow '
            'section may describe one'
        )

    def test_a_reopen_act_outside_step_six_is_detected(self, tmp_path):
        text = _read(WORKFLOW_DOC)
        fixture = tmp_path / 'planted-outside-step-six.md'
        fixture.write_text(
            text + '\n- **Reopen** — a decided item can be decided again when a later analysis changes.\n',
            encoding='utf-8',
        )

        assert _reopen_acts(_read(fixture)), 'a Reopen bullet outside Step 6 must be detected'

    def test_a_reopen_act_worded_without_the_stems_is_detected(self, tmp_path):
        text = _read(WORKFLOW_DOC)
        fixture = tmp_path / 'planted-worded-around.md'
        fixture.write_text(
            text.replace(
                _ORDERING_SENTENCE,
                f'{_ORDERING_SENTENCE} An item decided earlier is decided afresh when a later decision invalidates it.',
            ),
            encoding='utf-8',
        )

        assert _reopen_acts(_read(fixture)), 'an act worded around the stems must be detected'

    def test_the_idempotence_rule_carries_no_carve_out(self):
        block = _normalized(_idempotence_block(_read(WORKFLOW_DOC)))

        assert 'is not decided again' in block
        assert not re.search(r'\b(?:except|unless|however|other than)\b', block), (
            'the Idempotence rule now carves out an exception: a second decision would then be legal'
        )
