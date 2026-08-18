#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract guard for the finalize-step ``requires_prompt_fields`` obligation.

A finalize step is dispatched with a prompt body that carries a **generic**
five-field contract — ``name``, ``plan_id``, ``skills[]``, one of
``workflow``/``instructions``, ``WORKTREE``. Some steps need MORE: a
workflow-specific runtime input their body reads as a ``{placeholder}`` token.
``default:pre-submission-self-review`` is the motivating instance — it declares
its ``candidates`` field **Required** and carries it in its own dispatch body.

The defect this pins is a **producerless contract row**: the declaration (a
step marks a field Required) and the carriage (that field in the step's dispatch
body) are two edits in two places, and *nothing at runtime fails when they
disagree*. A step could declare a Required field its dispatch body never sends,
or send a field it never declared, and the dispatcher would forward a
silently-wrong prompt body.

The generic dispatch template is **not** limited to the five: its
``<plus every step-specific field the step declares in requires_prompt_fields>``
slot exists precisely to forward a step's declared extras, and the dispatcher is
instructed to forward every declared field. A declaration is therefore not, on
its own, evidence that a step needs a dispatch body of its own.

The fix declares a ``requires_prompt_fields`` frontmatter obligation per step —
the step-specific fields, beyond the exempt set below, the step needs — and this
module pins that declaration against every surface that can carry or state it:

(1) The derived declaring population is **non-empty** — checked first and alone,
    because every ∃-direction assertion would pass vacuously against an empty
    derivation.
(2) It covers the known instance, ``default:pre-submission-self-review``, and its
    declaration names ``candidates``.
(3) **No orphan declaration** (∃-direction, over declaring steps that HAVE their
    own ``prompt:`` block): every declared field appears in that block. The
    direction is CONDITIONAL on the step having such a block, because a step
    dispatched through the generic template has no own block for the field to
    appear in and the template carries the declared field regardless — an
    unconditional ∃-direction would reject the very extension slot the template
    provides.
(4) **No undeclared field** (∀-direction, over EVERY discovered step): every
    field a step's ``prompt:`` body carries beyond the exempt set is a member of
    that step's declaration. This direction shares the ∃-direction's reach: a
    step with no own block carries nothing here, so it says nothing about such a
    step.
(5) **The input table** — the surface ``ext-point-finalize-step.md`` names as the
    declaration site — is the THIRD scope: the non-exempt keys a step's
    prompt-body-field table marks Required must EQUAL its
    ``requires_prompt_fields``. This is the only direction that reaches a step
    dispatched through the generic template, which is most of the population.
(6) *(coverage)* The scopes' populations are published side by side, so a reader
    can see how far (3)/(4) reach rather than inferring whole-population
    coverage from their quantifiers.
(7) *(control)* A step whose dispatch body carries only exempt fields
    (``default:finalize-step-simplify``, which carries ``instructions`` in place
    of ``workflow`` — the XOR-alternative in the contract, not a step-specific
    field) is NOT flagged. A guard that mis-classified the ``instructions``
    alternative as a step-specific field would break that step while passing
    (1)-(6); this control is what forbids that over-broad fix.

Every assertion is **population-derived**: the step set comes from
``find_implementors()`` and the obligation from each doc's own frontmatter, so a
step that declares ``requires_prompt_fields`` later is covered with no edit here.

Every regex/parse detector carries a mutation guard asserting it fires on the
exact text it targets — a synthetic generic block, a synthetic instructions
block, a synthetic candidates block, and an injected divergence. Without them a
broken parser would make the corresponding assertion vacuously green — the
recurring failure shape in this codebase.
"""

from __future__ import annotations

import re
from pathlib import Path

import extension_discovery
from extension_discovery import find_implementors

#: The canonical ext-point whose implementors carry the obligation.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the obligation declaration.
_FIELD_KEY = 'requires_prompt_fields'

#: The generic dispatch contract — the field names every dispatch may carry. The
#: contract requires EXACTLY ONE of workflow/instructions per dispatch, so both
#: are contract names. Authoritative source: agents/execution-context.md
#: § "Input — Prompt-Body Contract".
_CONTRACT_FIELDS = frozenset(
    {'name', 'plan_id', 'skills', 'workflow', 'instructions', 'WORKTREE'}
)

#: Runtime inputs the DISPATCHER fills from its own run state at the dispatch
#: site — the phase that dispatched, the producer that raised the round, the
#: session under analysis, the loop iteration. They are exempt for a mechanical
#: reason rather than a stylistic one: a step never carries a dispatcher-inserted
#: field in its own body, so a declaration naming one could not satisfy the
#: ∃-direction, which looks for the field exactly there. ``caller_phase`` is
#: additionally declared by ext-point-execution-context-workflow.md as "the
#: optional 6th-field extension of the canonical 5-field contract", so treating
#: it as step-specific would contradict a contract that already names it generic.
_DISPATCHER_SUPPLIED_FIELDS = frozenset(
    {'caller_phase', 'iteration', 'producer', 'session_id'}
)

#: The ONE exempt set every assertion in this module uses. A prompt-body field
#: outside it — carried in a step's own block, or marked Required in a step's
#: input table — is a step-specific field the step must declare. Keeping a single
#: named set is the point: two competing "six generic names" lists were what let
#: the guard and the workflow contract disagree about ``caller_phase``.
_EXEMPT_FIELDS = _CONTRACT_FIELDS | _DISPATCHER_SUPPLIED_FIELDS

#: The known step whose candidates field is the motivating instance (n=1 today).
_KNOWN_STEP = 'default:pre-submission-self-review'
_KNOWN_FIELD = 'candidates'

#: The control step — carries `instructions` (a contract field), so it has a
#: non-trivial dispatch block but NO step-specific field. Kept distinct from the
#: declaring population so the control anchors the over-broad-fix guard on a real
#: block.
_CONTROL_STEP = 'default:finalize-step-simplify'

#: A dispatch block opens at a ``prompt: |`` scalar header.
_PROMPT_START = re.compile(r'^(\s*)prompt:\s*\|\s*$')

#: One top-level prompt-body field key. A bracketed index is stripped so the key
#: normalizes to its bare name — a digit index (``skills[2]:``) OR a placeholder
#: (``skills[N]:``, as the generic templates write it) both reduce to ``skills``.
#: A list item (``- item``) never matches — it does not start with a word char.
_FIELD_LINE = re.compile(r'^(\s*)([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]*\])?:')

#: A fenced-code delimiter ends a prompt block (the block lives inside a ```text
#: fence and its scalar bodies never open a nested fence).
_FENCE = re.compile(r'^\s*```')


# ---------------------------------------------------------------------------
# Declaration derivation (never hardcoded)
# ---------------------------------------------------------------------------


def _declared_prompt_fields(doc_path: Path) -> list[str]:
    """Read the ``requires_prompt_fields`` obligation off one step doc.

    Reuses ``_read_frontmatter_fields`` — the same extraction primitive the
    registry uses for every other implementor field — rather than standing up a
    second frontmatter parser that could drift from the one the registry reads.
    """
    fields = extension_discovery._read_frontmatter_fields(doc_path, (_FIELD_KEY,))
    value = fields.get(_FIELD_KEY)
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _declaring_records() -> list[dict]:
    """Every discovered step doc that declares a ``requires_prompt_fields`` list."""
    records = []
    for record in find_implementors(_EXT_POINT):
        declared = _declared_prompt_fields(Path(record['path']))
        if declared:
            records.append({**record, 'prompt_fields': declared})
    return records


def _declaring_names() -> set[str]:
    return {record['name'] for record in _declaring_records()}


def _record_for(step_name: str) -> dict:
    """Resolve one implementor record by step name (path is never hardcoded)."""
    for record in find_implementors(_EXT_POINT):
        if record['name'] == step_name:
            return record
    raise AssertionError(
        f'{step_name} is not a discovered finalize-step implementor, so the '
        f'anchor assertion has nothing to read.'
    )


# ---------------------------------------------------------------------------
# Prompt-block parsing — the carried side of the contract
# ---------------------------------------------------------------------------


def _prompt_blocks(text: str) -> list[str]:
    """Return each ``prompt: |`` block body in a doc as its own string.

    A block starts on the line AFTER a ``prompt: |`` header and runs while lines
    are blank OR indented deeper than that header; a fenced-code delimiter, or a
    dedent to the header's indent (or less), ends it. Blank lines and a deeper
    block scalar (``candidates: |`` / ``instructions: |`` content) stay inside
    the block — the field-extraction step below discards the scalar content by
    indentation, not by block boundary.
    """
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        match = _PROMPT_START.match(line)
        if not match:
            continue
        prompt_indent = len(match.group(1))
        body: list[str] = []
        for candidate in lines[index + 1:]:
            if candidate.strip() == '':
                body.append(candidate)
                continue
            if _FENCE.match(candidate):
                break
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= prompt_indent:
                break
            body.append(candidate)
        blocks.append('\n'.join(body))
    return blocks


def _block_prompt_fields(block: str) -> set[str]:
    """The top-level prompt-body field NAMES a block declares.

    Only lines at the block's MINIMUM (top-level) indent are fields; deeper lines
    are block-scalar content (a ``candidates: |`` or ``instructions: |`` body,
    which may itself contain ``key: value`` prose such as ``Scope: {scope}``) and
    are excluded by the indentation test. A ``- item`` list entry never matches
    ``_FIELD_LINE``.
    """
    lines = [line for line in block.splitlines() if line.strip()]
    if not lines:
        return set()
    field_indent = min(len(line) - len(line.lstrip()) for line in lines)
    fields: set[str] = set()
    for line in lines:
        if len(line) - len(line.lstrip()) != field_indent:
            continue
        match = _FIELD_LINE.match(line)
        if match:
            fields.add(match.group(2))
    return fields


def _step_specific_fields(doc_path: Path) -> set[str]:
    """Union of step-specific prompt-body fields carried across a doc's blocks.

    Every field carried in any ``prompt: |`` block of the doc, MINUS the generic
    contract fields — so the result is exactly the fields the step must declare
    in ``requires_prompt_fields``.
    """
    text = doc_path.read_text(encoding='utf-8')
    carried: set[str] = set()
    for block in _prompt_blocks(text):
        carried |= _block_prompt_fields(block)
    return carried - _EXEMPT_FIELDS


# ---------------------------------------------------------------------------
# Detection cores — pure, so the mutation guards can drive them synthetically
# ---------------------------------------------------------------------------


def _orphans(declared: set[str], carried: set[str]) -> list[str]:
    """∃-direction offenders: declared fields no dispatch body carries."""
    return sorted(field for field in declared if field not in carried)


def _undeclared(declared: set[str], carried: set[str]) -> list[str]:
    """∀-direction offenders: carried step-specific fields not declared."""
    return sorted(field for field in carried if field not in declared)


# ---------------------------------------------------------------------------
# (1) the derivation resolves something
# ---------------------------------------------------------------------------


def test_declared_population_is_non_empty():
    """(1) Checked first and alone — every ∃-direction assertion depends on it."""
    declaring = _declaring_names()

    assert declaring, (
        f'No discovered finalize step declares a {_FIELD_KEY} obligation. The '
        f'∃-direction assertions would pass vacuously against an empty '
        f'population, so this is checked separately. Either no step doc carries '
        f'the frontmatter key, or find_implementors({_EXT_POINT!r}) discovered '
        f'no step docs at all.'
    )


def test_at_least_one_declaring_doc_has_a_parseable_dispatch_block():
    """Vacuity guard for the CONDITIONAL ∃-direction.

    (3) skips a declaring step with no ``prompt:`` block of its own, because such
    a step is dispatched through the generic template and the template carries the
    declared field. That makes the direction conditional, and a conditional
    direction whose condition NEVER holds asserts nothing at all — so at least one
    declaring doc must have a block for (3) to be exercised against.

    The older form of this guard required EVERY declaring doc to have a block. That
    was the ∃-direction's unconditional shape restated as a precondition, and it
    rejected a step declaring a field it lets the generic template carry — which
    is the supported case, not a defect.
    """
    with_blocks = [
        record['name']
        for record in _declaring_records()
        if _prompt_blocks(Path(record['path']).read_text(encoding='utf-8'))
    ]

    assert with_blocks, (
        f'No step declaring {_FIELD_KEY} has a `prompt: |` dispatch block of its '
        f'own, so the conditional ∃-direction (3) skips every step and asserts '
        f'nothing. Either the block parser broke, or the declaring population is '
        f'entirely generic-template-dispatched — in which case (3) is inert and '
        f'the input-table direction (5) is the only live declaration check.'
    )


# ---------------------------------------------------------------------------
# (2) the obligation covers the known instance
# ---------------------------------------------------------------------------


def test_population_contains_the_known_instance():
    """(2) The motivating case — candidates on pre-submission-self-review."""
    declaring = _declaring_names()

    assert _KNOWN_STEP in declaring, (
        f'{_KNOWN_STEP} declares {_KNOWN_FIELD} Required in its input table and '
        f'carries it in its own dispatch body, but it declares no {_FIELD_KEY} '
        f'obligation — so the declaration↔carriage link is unenforced for the '
        f'exact instance this contract exists to close. Declaring steps: '
        f'{sorted(declaring)}'
    )

    record = next(r for r in _declaring_records() if r['name'] == _KNOWN_STEP)
    assert _KNOWN_FIELD in record['prompt_fields'], (
        f'{_KNOWN_STEP} declares {_FIELD_KEY} but it does not list '
        f'{_KNOWN_FIELD!r}. Declared: {record["prompt_fields"]}'
    )


# ---------------------------------------------------------------------------
# (3)/(4) declaration-vs-carriage over a step's OWN dispatch body
# ---------------------------------------------------------------------------


def test_no_orphan_prompt_field_declaration():
    """(3) ∃-direction, over declaring steps that have their own dispatch body.

    A step WITH its own ``prompt:`` block has chosen to carry its extras there, so
    a declared field missing from that block is a real divergence. A step WITHOUT
    one is dispatched through the generic template, whose
    ``<plus every step-specific field …>`` slot carries the declared field and
    whose paragraph instructs the dispatcher to forward every declared field — so
    it has no own block for the field to be missing from, and flagging it would
    reject the supported case. Such a step is covered by (5) instead, against the
    input table.
    """
    offenders = []
    for record in _declaring_records():
        doc_path = Path(record['path'])
        if not _prompt_blocks(doc_path.read_text(encoding='utf-8')):
            continue  # generic-template dispatch — covered by (5), not here.
        carried = _step_specific_fields(doc_path)
        orphans = _orphans(set(record['prompt_fields']), carried)
        if orphans:
            offenders.append(f"{record['name']}: {orphans}")

    assert not offenders, (
        f'These steps have their own `prompt: |` dispatch body and declare '
        f'{_FIELD_KEY} that the body does not carry. A step that keeps its own '
        f'dispatch body is responsible for carrying every field it declares '
        f'there; only a step dispatched through the generic template may leave '
        f'the carriage to the template: {offenders}'
    )


def test_no_undeclared_prompt_field():
    """(4) ∀-direction: every carried step-specific field is declared."""
    offenders = []
    for record in find_implementors(_EXT_POINT):
        declared = set(_declared_prompt_fields(Path(record['path'])))
        carried = _step_specific_fields(Path(record['path']))
        undeclared = _undeclared(declared, carried)
        if undeclared:
            offenders.append(f"{record['name']}: {undeclared}")

    assert not offenders, (
        f'These steps carry prompt-body fields beyond the exempt set that '
        f'their {_FIELD_KEY} frontmatter does not declare, so the carriage has '
        f'drifted past the contract the frontmatter publishes: {offenders}'
    )


# ---------------------------------------------------------------------------
# (5) the input table — the surface the ext-point names as the declaration site
# ---------------------------------------------------------------------------
#
# ext-point-finalize-step.md § "Step-specific prompt-body fields" defines the
# declaration as "a field the step's input table marks Required", yet both
# directions above read carriage from ``prompt:`` blocks — which most implementors
# do not have. This scope reads the surface the contract actually names, and is
# the only one that reaches a generic-template-dispatched step.

#: The repository-wide convention header for a prompt-body-field input table. The
#: discriminator is the FIRST header cell, not the presence of a `Required` column:
#: a CLI `| Parameter | Required | … |` table also carries one, and folding its
#: rows in would flag every documented flag as an undeclared prompt-body field.
_INPUT_TABLE_HEADER = 'prompt-body field'

#: The `Required` cell values that mark a row as a required prompt-body field.
#: `Conditional` and `No` rows are NOT required, so they carry no declaration
#: obligation and are excluded.
_REQUIRED_AFFIRMATIVE = frozenset({'yes'})


def _table_cells(line: str) -> list[str]:
    """Split one markdown table row into stripped cells."""
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split('|')]


def _is_delimiter_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r':?-{2,}:?', cell) for cell in cells)


def _normalize_key(cell: str) -> str:
    """A table row's key cell reduced to a bare field name.

    Strips markdown code fencing and emphasis, then drops any bracketed index so
    ``skills[]`` normalizes to ``skills`` exactly as the block parser does.
    """
    key = cell.strip().strip('*').strip('`').strip()
    return re.sub(r'\[[^\]]*\]$', '', key)


def _required_table_keys(doc_path: Path) -> set[str]:
    """The keys a doc's prompt-body-field table(s) mark Required.

    The ``Required`` column is located by PARSING THE HEADER, never by assuming a
    position: a table that adds a column before it would otherwise be read off by
    one, silently reading descriptions as required-ness.
    """
    keys: set[str] = set()
    lines = doc_path.read_text(encoding='utf-8').split('\n')
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith('|') or index + 1 >= len(lines):
            index += 1
            continue
        header = _table_cells(lines[index])
        delimiter = _table_cells(lines[index + 1])
        if len(delimiter) != len(header) or not _is_delimiter_row(delimiter):
            index += 1
            continue
        row_index = index + 2
        if header[0].strip().strip('*').lower() == _INPUT_TABLE_HEADER:
            required_at = next(
                (
                    position
                    for position, cell in enumerate(header)
                    if cell.strip().strip('*').lower() == 'required'
                ),
                None,
            )
            if required_at is not None:
                while row_index < len(lines) and lines[row_index].strip().startswith('|'):
                    row = _table_cells(lines[row_index])
                    if len(row) > required_at and (
                        row[required_at].strip().strip('*').lower() in _REQUIRED_AFFIRMATIVE
                    ):
                        keys.add(_normalize_key(row[0]))
                    row_index += 1
        else:
            while row_index < len(lines) and lines[row_index].strip().startswith('|'):
                row_index += 1
        index = row_index
    return keys


def _table_step_specific_keys(doc_path: Path) -> set[str]:
    """The Required input-table keys that are step-specific (outside the exempt set)."""
    return _required_table_keys(doc_path) - _EXEMPT_FIELDS


def test_input_table_parser_reads_the_known_instance():
    """Vacuity guard for (5): the parser must find the one real declaring row.

    A parser that matched no table would make (5) green over an empty extraction
    for every step — the exact shape that lets a contract guard assert nothing.
    """
    record = _record_for(_KNOWN_STEP)
    doc_path = Path(record['path'])

    assert _KNOWN_FIELD in _required_table_keys(doc_path), (
        f"{_KNOWN_STEP}'s input table marks {_KNOWN_FIELD!r} Required, but the "
        f'parser extracted {sorted(_required_table_keys(doc_path))}. Every (5) '
        f'assertion would be over an empty set.'
    )
    assert _table_step_specific_keys(doc_path) == {_KNOWN_FIELD}, (
        f'Expected exactly {{{_KNOWN_FIELD!r}}} step-specific in the real table; '
        f'parsed {sorted(_table_step_specific_keys(doc_path))}.'
    )


def test_input_table_required_column_is_located_by_header_not_position(tmp_path: Path):
    """The `Required` column is found by name, and a CLI table is not folded in.

    Two mis-parses this forbids: reading a fixed column index (a table that gains a
    column before `Required` would then read descriptions as required-ness), and
    treating any table with a `Required` column as a prompt-body-field table (a CLI
    `| Parameter | Required | … |` table has one, and folding it in would flag every
    documented flag as an undeclared prompt-body field).
    """
    doc = tmp_path / 'synthetic_input_table.md'
    doc.write_text(
        '| Prompt-body field | Type | Required | Description |\n'
        '|---|---|:--------:|---|\n'
        '| `candidates` | toon | Yes | the surfaced candidates |\n'
        '| `optional_one` | str | No | not required |\n'
        '\n'
        '| Parameter | Required | Description |\n'
        '|---|---|---|\n'
        '| `--session-id` | Yes | a CLI flag, not a prompt-body field |\n',
        encoding='utf-8',
    )

    assert _required_table_keys(doc) == {'candidates'}, (
        'The parser did not locate the `Required` column by header, or it folded '
        f'the CLI table in. Parsed: {sorted(_required_table_keys(doc))}'
    )


def test_input_table_required_keys_equal_the_declaration():
    """(5) Per step, the table's step-specific Required keys EQUAL the declaration.

    Both directions at once, over the whole discovered population: a Required
    non-exempt row with no matching ``requires_prompt_fields`` entry is a field the
    dispatcher was never told to forward, and a declared field with no Required row
    is an obligation the step's own documented interface does not state.
    """
    offenders = []
    for record in find_implementors(_EXT_POINT):
        doc_path = Path(record['path'])
        declared = set(_declared_prompt_fields(doc_path))
        tabled = _table_step_specific_keys(doc_path)
        if declared != tabled:
            offenders.append(
                f"{record['name']}: declared={sorted(declared)} table={sorted(tabled)}"
            )

    assert not offenders, (
        f'These steps\' input tables and {_FIELD_KEY} declarations disagree. The '
        f'input table is the surface ext-point-finalize-step.md names as the '
        f'declaration site, so a Required non-exempt row with no declaration is a '
        f'field the dispatcher is never told to forward, and a declaration with no '
        f'Required row states an obligation the step\'s documented interface does '
        f'not: {offenders}'
    )


def test_the_three_scopes_publish_their_populations():
    """(6) State how far each scope reaches, rather than implying full coverage.

    (3) and (4) read a step's own ``prompt:`` block, which most implementors do not
    have — so their quantifiers span a small minority. (5) reads the input table and
    spans every discovered step. Publishing the three counts is what keeps a green
    from reading as whole-population coverage of declaration-versus-carriage.
    """
    records = find_implementors(_EXT_POINT)
    with_own_block = [
        record['name']
        for record in records
        if _prompt_blocks(Path(record['path']).read_text(encoding='utf-8'))
    ]

    assert records, 'no finalize steps discovered'
    assert with_own_block, (
        'No discovered step has its own `prompt:` block, so (3) and (4) reach '
        'nothing at all.'
    )
    assert len(with_own_block) < len(records), (
        f'Every discovered step ({len(records)}) now has its own dispatch block, '
        f'so the coverage asymmetry this test publishes no longer exists and the '
        f'module docstring\'s account of (3)/(4) reach must be re-derived. '
        f'With a block: {sorted(with_own_block)}'
    )


# ---------------------------------------------------------------------------
# (7) control — the over-broad-fix guard, on a real instructions-based dispatch
# ---------------------------------------------------------------------------


def test_contract_only_dispatch_is_not_flagged():
    """(7) A step carrying only exempt fields dispatches unchanged.

    ``finalize-step-simplify`` carries ``instructions`` in place of ``workflow``
    — the XOR-alternative in the dispatch contract, NOT a step-specific field
    (its block still has five field lines). A guard that mis-classified the
    ``instructions`` alternative as a step-specific field would break this step
    while passing (1)-(6); this control forbids that over-broad fix.
    """
    record = _record_for(_CONTROL_STEP)
    carried = _step_specific_fields(Path(record['path']))

    assert carried == set(), (
        f'{_CONTROL_STEP} was read as carrying step-specific field(s) {sorted(carried)}, '
        f'but every field it carries is exempt (it uses `instructions` in place of '
        f'`workflow`). Flagging it would make the guard over-broad — rejecting a '
        f'legitimate contract-only dispatch.'
    )

    assert _CONTROL_STEP not in _declaring_names(), (
        f'{_CONTROL_STEP} carries no step-specific field, so it must NOT declare '
        f'a {_FIELD_KEY} obligation. Declaring it would be an orphan declaration.'
    )


#: A dispatch carrying ``caller_phase`` — the field two documents disagreed about.
#: ``ext-point-execution-context-workflow.md`` declares it "the optional 6th-field
#: extension of the canonical 5-field contract", while the guard's own generic-name
#: list omitted it, so a step carrying it would have been flagged as carrying an
#: undeclared step-specific field. The exempt set settles that in favour of the
#: contract that already names it generic; this synthetic pins the settlement.
_SYNTH_CALLER_PHASE = (
    'Task: plan-marshall:{target}\n'
    '  prompt: |\n'
    '    name: verification-feedback\n'
    '    plan_id: {plan_id}\n'
    '    skills[N]:\n'
    '    - plan-marshall:manage-findings\n'
    '    workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md\n'
    '    producer: finalize-feedback\n'
    '    caller_phase: phase-6-finalize\n'
    '    WORKTREE: {worktree_path}\n'
)


def test_dispatcher_supplied_fields_are_not_step_specific():
    """A block carrying `caller_phase` (and its siblings) carries nothing step-specific.

    These are filled by the dispatcher from its own run state at the dispatch site,
    so a step never carries one in its own body and could never satisfy the
    ∃-direction for a declaration naming one. Treating them as step-specific would
    demand exactly such an unsatisfiable declaration.
    """
    carried = _synthetic_carried(_SYNTH_CALLER_PHASE)

    assert carried == set(), (
        f'The dispatch carrying dispatcher-supplied fields parsed as carrying '
        f'step-specific field(s) {sorted(carried)}. Every one of '
        f'{sorted(_DISPATCHER_SUPPLIED_FIELDS)} is exempt.'
    )

    # The block genuinely CONTAINS them — otherwise the assertion above is vacuous.
    parsed = set()
    for block in _prompt_blocks(_SYNTH_CALLER_PHASE):
        parsed |= _block_prompt_fields(block)
    assert {'caller_phase', 'producer'} <= parsed, (
        f'The fixture does not actually carry the fields under test; parsed '
        f'{sorted(parsed)}. The exemption assertion above would prove nothing.'
    )


# ---------------------------------------------------------------------------
# Mutation guards — one per detector, each fired against its exact text
# ---------------------------------------------------------------------------


#: A generic five-field workflow-doc dispatch — carries NO step-specific field.
_SYNTH_GENERIC = (
    'Task: plan-marshall:{target}\n'
    '  prompt: |\n'
    '    name: some-step\n'
    '    plan_id: {plan_id}\n'
    '    skills[N]:\n'
    '    - plan-marshall:persona-plan-marshall-agent\n'
    '    workflow: plan-marshall:phase-6-finalize/workflow/some-step.md\n'
    '    WORKTREE: {worktree_path}\n'
)

#: An ``instructions`` dispatch whose scalar body itself contains a ``key:``
#: line (``Scope: {scope}``) — the parser must not mistake it for a top-level
#: field. Mirrors finalize-step-simplify's shape.
_SYNTH_INSTRUCTIONS = (
    'Task: plan-marshall:{target}\n'
    '  prompt: |\n'
    '    name: finalize-step-simplify\n'
    '    plan_id: {plan_id}\n'
    '    skills[2]:\n'
    '    - plan-marshall:persona-plan-marshall-agent\n'
    '    - plan-marshall:ref-code-quality\n'
    '    instructions: |\n'
    '      Review the plan surface.\n'
    '      Scope: {scope} (changeset = diff hunks).\n'
    '    WORKTREE: {worktree_path}\n'
)

#: A six-field dispatch carrying the step-specific ``candidates`` field, whose
#: scalar body is a ``{candidates_toon}`` placeholder. Mirrors the real
#: pre-submission-self-review Step 2 block.
_SYNTH_CANDIDATES = (
    'Task: plan-marshall:{target}\n'
    '  prompt: |\n'
    '    name: pre-submission-self-review\n'
    '    plan_id: {plan_id}\n'
    '    skills: []\n'
    '    workflow: plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md\n'
    '\n'
    '    candidates: |\n'
    '      {candidates_toon}\n'
    '\n'
    '    WORKTREE: {worktree_path}\n'
)


def _synthetic_carried(block_text: str) -> set[str]:
    """Step-specific fields of a single synthetic block (no file I/O)."""
    carried: set[str] = set()
    for block in _prompt_blocks(block_text):
        carried |= _block_prompt_fields(block)
    return carried - _EXEMPT_FIELDS


def test_parser_reads_the_real_candidates_field():
    """The parser extracts exactly ``candidates`` from the REAL dispatch block —
    so (2)/(3) assert over a truly-carried field, not a mis-parse."""
    record = _record_for(_KNOWN_STEP)
    carried = _step_specific_fields(Path(record['path']))

    assert carried == {_KNOWN_FIELD}, (
        f'Expected the real {_KNOWN_STEP} dispatch body to carry exactly '
        f'{{{_KNOWN_FIELD!r}}} beyond the generic contract; parsed {sorted(carried)}. '
        f'A mis-parse here would make (2)/(3) vacuous or wrong.'
    )


def test_generic_block_carries_no_step_specific_field():
    """Guards (5): a five-field generic block must read as zero extras, or the
    control would pass vacuously."""
    assert _synthetic_carried(_SYNTH_GENERIC) == set(), (
        'The five-field generic dispatch parsed as carrying a step-specific '
        f'field: {sorted(_synthetic_carried(_SYNTH_GENERIC))}'
    )


def test_instructions_block_carries_no_step_specific_field():
    """Guards (5): ``instructions`` is a contract field, and a ``key:`` line
    INSIDE its scalar body (``Scope:``) must not be mis-read as a field."""
    carried = _synthetic_carried(_SYNTH_INSTRUCTIONS)

    assert carried == set(), (
        f'The instructions dispatch parsed as carrying step-specific field(s) '
        f'{sorted(carried)}. Either `instructions` leaked out of the contract '
        f'set, or a `key:` line inside its scalar body (e.g. `Scope:`) was '
        f'mis-read as a top-level field.'
    )


def test_candidates_block_carries_exactly_candidates():
    """Guards (2)/(3)/(4): the synthetic candidates block reads as exactly one
    step-specific field, and the ``{candidates_toon}`` scalar line is excluded."""
    assert _synthetic_carried(_SYNTH_CANDIDATES) == {'candidates'}, (
        f'The candidates dispatch parsed as {sorted(_synthetic_carried(_SYNTH_CANDIDATES))}, '
        f'not exactly {{"candidates"}}'
    )


def test_orphan_detection_fires_on_an_injected_divergence():
    """Guards (3): the ∃-direction core flags a declared-but-not-carried field.

    This is the injected-divergence demonstration made permanent — a step that
    declares ``candidates`` AND a phantom ``ghost`` while its dispatch body
    carries only ``candidates`` is flagged for ``ghost``, and a matched control
    (declare only what is carried) is NOT flagged. A guard never seen to fire is
    indistinguishable from one that cannot.
    """
    carried = _synthetic_carried(_SYNTH_CANDIDATES)  # -> {'candidates'}

    diverged = _orphans({'candidates', 'ghost'}, carried)
    assert diverged == ['ghost'], (
        f'The ∃-direction core did not flag the injected phantom field; got '
        f'{diverged}. If it cannot fire, the whole contract is inert.'
    )

    matched = _orphans({'candidates'}, carried)
    assert matched == [], (
        f'The ∃-direction core flagged a field that IS carried; got {matched}. '
        f'A guard that fires on a correct declaration is a false positive.'
    )


def test_undeclared_detection_fires_on_an_injected_divergence():
    """Guards (4): the ∀-direction core flags a carried-but-not-declared field."""
    carried = _synthetic_carried(_SYNTH_CANDIDATES)  # -> {'candidates'}

    diverged = _undeclared(set(), carried)
    assert diverged == ['candidates'], (
        f'The ∀-direction core did not flag the undeclared carried field; got '
        f'{diverged}.'
    )

    matched = _undeclared({'candidates'}, carried)
    assert matched == [], (
        f'The ∀-direction core flagged a field that IS declared; got {matched}.'
    )


def test_block_parser_isolates_two_adjacent_dispatches():
    """Guards the unit of analysis: two ``prompt: |`` blocks parse as two, so a
    doc showing an illustrative generic dispatch beside its own real one does not
    let the generic block's fields leak into the real one's field set."""
    doc = _SYNTH_GENERIC + '\n```\n\nThen the real dispatch:\n\n```text\n' + _SYNTH_CANDIDATES

    blocks = _prompt_blocks(doc)
    assert len(blocks) == 2, f'Expected two isolated prompt blocks, got {len(blocks)}'
    assert _block_prompt_fields(blocks[0]) - _EXEMPT_FIELDS == set()
    assert _block_prompt_fields(blocks[1]) - _EXEMPT_FIELDS == {'candidates'}


def test_field_parser_strips_any_bracketed_skills_index():
    """The field regex must strip
    ANY bracketed index — a digit ``[2]`` OR a placeholder ``[N]`` (the form the
    generic templates write) — so the header normalizes to ``skills`` instead of
    silently dropping the field. A ``\\d*``-only index matched ``[2]`` but not
    ``[N]``, contradicting the documented behaviour and passing only because
    ``skills`` is a contract field the step-specific subtraction discards anyway.
    """
    for header in ('skills[N]', 'skills[2]', 'skills[]', 'skills'):
        block = f'    name: s\n    {header}:\n    - x\n    WORKTREE: .'
        fields = _block_prompt_fields(block)
        assert 'skills' in fields, (
            f'`{header}:` did not normalize to the `skills` field; parsed '
            f'{sorted(fields)}. A bracketed index of any form must be stripped.'
        )
