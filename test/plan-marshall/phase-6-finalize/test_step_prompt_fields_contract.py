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
silently-wrong prompt body. The generic dispatch template carries only the five
generic fields and **structurally cannot** send a step-specific one — so a step
that declares a step-specific field yet relies on that template is broken with
no signal.

The fix declares a ``requires_prompt_fields`` frontmatter obligation per step —
the list of step-specific fields (beyond the generic contract) the step's own
``prompt:`` dispatch body carries — and this module pins the declaration-versus-
carriage agreement in BOTH directions, mirroring
``test_step_records_facts_contract.py``:

(1) The derived declaring population is **non-empty** — checked first and alone,
    because every ∃-direction assertion would pass vacuously against an empty
    derivation.
(2) It covers the known instance, ``default:pre-submission-self-review``, and its
    declaration names ``candidates``.
(3) **No orphan declaration** (∃-direction): every field in a step's
    ``requires_prompt_fields`` appears in that step's own ``prompt:`` dispatch
    body. A field declared Required but left to the generic template — which
    cannot carry it — is the exact failure this catches.
(4) **No undeclared field** (∀-direction, over EVERY discovered step): every
    field a step's ``prompt:`` body carries beyond the generic contract is a
    member of that step's declaration.
(5) *(control)* A step whose dispatch body carries only generic-contract fields
    (``default:finalize-step-simplify``, which carries ``instructions`` in place
    of ``workflow`` — the XOR-alternative in the contract, not a step-specific
    field) is NOT flagged. A guard that mis-classified the ``instructions``
    alternative as a step-specific field would break that step while passing
    (1)-(4); this control is what forbids that over-broad fix.

Assertions (1)-(4) are **population-derived**: the step set comes from
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

#: The generic dispatch contract — every prompt-body field a step may carry
#: WITHOUT declaring it in requires_prompt_fields. The dispatch contract requires
#: EXACTLY ONE of workflow/instructions per dispatch, so both are contract names;
#: a field OUTSIDE this set is a step-specific field. Authoritative source:
#: agents/execution-context.md § "Input — Prompt-Body Contract".
_CONTRACT_FIELDS = frozenset(
    {'name', 'plan_id', 'skills', 'workflow', 'instructions', 'WORKTREE'}
)

#: The known step whose candidates field is the motivating instance (n=1 today).
_KNOWN_STEP = 'default:pre-submission-self-review'
_KNOWN_FIELD = 'candidates'

#: The control step — carries `instructions` (a contract field), so it has a
#: non-trivial dispatch block but NO step-specific field. Kept distinct from the
#: declaring population so (5) anchors the over-broad-fix guard on a real block.
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
    return carried - _CONTRACT_FIELDS


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


def test_every_declaring_doc_has_a_parseable_dispatch_block():
    """Vacuity guard: a declaring doc with no parseable prompt block would pass
    the ∃-direction assertion free."""
    offenders = [
        record['name']
        for record in _declaring_records()
        if not _prompt_blocks(Path(record['path']).read_text(encoding='utf-8'))
    ]

    assert not offenders, (
        f'These steps declare {_FIELD_KEY} but no `prompt: |` dispatch block '
        f'parsed out of their doc body, so the ∃-direction assertion would be '
        f'vacuous for them (a declared field cannot be found carried in a block '
        f'that does not exist): {offenders}'
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
# (3)/(4) declaration-vs-carriage, the only two detector directions
# ---------------------------------------------------------------------------


def test_no_orphan_prompt_field_declaration():
    """(3) ∃-direction: each declared field is carried in the step's own body."""
    offenders = []
    for record in _declaring_records():
        carried = _step_specific_fields(Path(record['path']))
        orphans = _orphans(set(record['prompt_fields']), carried)
        if orphans:
            offenders.append(f"{record['name']}: {orphans}")

    assert not offenders, (
        f'These steps declare {_FIELD_KEY} that no `prompt: |` dispatch body in '
        f'their own doc actually carries. A field declared Required but left to '
        f'the generic template is broken — the generic template carries only the '
        f'five generic fields and cannot send a step-specific one: {offenders}'
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
        f'These steps carry prompt-body fields beyond the generic contract that '
        f'their {_FIELD_KEY} frontmatter does not declare, so the carriage has '
        f'drifted past the contract the frontmatter publishes: {offenders}'
    )


# ---------------------------------------------------------------------------
# (5) control — the over-broad-fix guard, on a real instructions-based dispatch
# ---------------------------------------------------------------------------


def test_contract_only_dispatch_is_not_flagged():
    """(5) A step carrying only generic-contract fields dispatches unchanged.

    ``finalize-step-simplify`` carries ``instructions`` in place of ``workflow``
    — the XOR-alternative in the dispatch contract, NOT a step-specific field
    (its block still has five field lines). A guard that mis-classified the
    ``instructions`` alternative as a step-specific field would break this step
    while passing (1)-(4); this control forbids that over-broad fix.
    """
    record = _record_for(_CONTROL_STEP)
    carried = _step_specific_fields(Path(record['path']))

    assert carried == set(), (
        f'{_CONTROL_STEP} was read as carrying step-specific field(s) {sorted(carried)}, '
        f'but every field it carries is a generic-contract field (it uses '
        f'`instructions` in place of `workflow`). Flagging it would make the '
        f'guard over-broad — rejecting a legitimate contract-only dispatch.'
    )

    assert _CONTROL_STEP not in _declaring_names(), (
        f'{_CONTROL_STEP} carries no step-specific field, so it must NOT declare '
        f'a {_FIELD_KEY} obligation. Declaring it would be an orphan declaration.'
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
    return carried - _CONTRACT_FIELDS


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
    assert _block_prompt_fields(blocks[0]) - _CONTRACT_FIELDS == set()
    assert _block_prompt_fields(blocks[1]) - _CONTRACT_FIELDS == {'candidates'}


def test_field_parser_strips_any_bracketed_skills_index():
    """Regression pin (cuioss-review-bot, PR #1197): the field regex must strip
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
