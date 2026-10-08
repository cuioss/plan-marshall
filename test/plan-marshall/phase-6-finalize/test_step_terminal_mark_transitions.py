#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Derived guard: a finalize step's terminal marks carry ``--force`` where the transition table needs it.

``mark-step-done`` decides every outcome change against one table,
``_TRANSITIONS_LEGAL_WITHOUT_FORCE`` in ``manage-status/scripts/_cmd_mark_step.py``.
A retry (a stored ``failed``) and a re-fire (a stored ``loop_back``, or a stored
``done`` that is re-fired and aborts or loops back) are inside it and record
without the flag. Two pairs a finalize step can actually reach are outside it:

* ``skipped`` written over a stored ``done``;
* any other outcome written over a stored ``skipped``.

A terminal branch that can reach one of those pairs without ``--force`` returns
``error: conflict``, writes nothing, and leaves the dispatcher's post-dispatch
guard looking at a record that does not say what the step did. The reachable
case is a step the dispatcher's own Signal Gate recorded ``skipped`` and that a
later firing runs to completion: its ``done`` lands on the stored ``skipped``.

This module sweeps every step document the finalize registry discovers and
checks each terminal ``mark-step-done`` invocation against that rule:

(1) The examined population is **non-empty**, checked first and alone, and its
    size is published. Every later assertion would pass vacuously over an empty
    derivation.
(2) The dispatcher-recorded ``skipped`` set is **non-empty**. It is what makes
    rule (4) reachable at all, so a parse that silently returned nothing would
    turn the sweep into a check of rule (3) alone.
(3) An invocation writing ``skipped``, in a document that can also hold
    ``done``, carries ``--force``.
(4) An invocation writing any other outcome, in a document that can hold
    ``skipped``, carries ``--force``.

**Everything is derived, nothing is listed.** The step documents come from
``find_implementors()`` on the finalize-step extension point. A document's
outcome set is the union of the ``--outcome`` values its own invocations write,
plus ``skipped`` when the dispatcher itself records ``skipped`` for that step —
read off the dispatcher document's own ``mark-step-done --outcome skipped``
invocations rather than from a list here. A step added to the registry, or a
new dispatcher-side skip, is covered with no edit to this module, and no
cardinality literal is asserted.

The unit of analysis is one invocation block per call site, started at a shell
invocation line and extended across line continuations — the same boundary
``test_step_records_facts_contract_records.py`` pins, for the same reason: a
narrative sentence can name both the verb and an ``--outcome`` argument.

The mutation guards feed the offender predicate synthetic documents, so a
detector that stopped firing cannot read as a clean sweep.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT
from extension_discovery import find_implementors

#: The canonical ext-point whose implementors are the finalize step documents.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The dispatcher document. It is not a step document: it is read only for the
#: ``skipped`` records the dispatcher writes on a step's behalf.
_DISPATCHER_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'

_MARK_STEP_TOKEN = 'mark-step-done'
_SKIPPED = 'skipped'
_DONE = 'done'

#: A call-site block starts at a line that opens a ``python3`` command.
_INVOCATION_START = re.compile(r'^\s*python3\s')

#: The ``--outcome`` value of a block: a literal (``done``) or a brace template
#: naming alternatives (``{done|failed}``).
_OUTCOME_ARG = re.compile(r'--outcome\s+(\{[^}]*\}|[a-z_]+)')

#: The ``--step`` value of a block.
_STEP_ARG = re.compile(r'--step\s+(\S+)')

#: The bare ``--force`` flag. The lookarounds keep a longer flag that merely
#: starts with it (``--force-with-lease``) from counting.
_FORCE_FLAG = re.compile(r'(?<![\w-])--force(?![\w-])')

#: The registry prefix a built-in step carries in discovery and drops in the
#: manifest key the dispatcher writes under.
_DEFAULT_PREFIX = 'default:'


def _bare_step_key(name: str) -> str:
    """Reduce a step name to the manifest key form the dispatcher writes under."""
    return name[len(_DEFAULT_PREFIX) :] if name.startswith(_DEFAULT_PREFIX) else name


def _call_site_blocks(text: str) -> list[str]:
    """Return each terminal ``mark-step-done`` invocation as its own block."""
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        if not _INVOCATION_START.match(line):
            continue
        collected = [line]
        cursor = index
        while lines[cursor].rstrip().endswith('\\') and cursor + 1 < len(lines):
            cursor += 1
            collected.append(lines[cursor])
        block = '\n'.join(collected)
        if _MARK_STEP_TOKEN in block and _OUTCOME_ARG.search(block):
            blocks.append(block)
    return blocks


def _block_outcomes(block: str) -> set[str]:
    """The outcome values one block can write — one literal, or a template's alternatives."""
    match = _OUTCOME_ARG.search(block)
    if match is None:
        return set()
    raw = match.group(1)
    if raw.startswith('{'):
        return {part.strip() for part in raw.strip('{}').split('|') if part.strip()}
    return {raw}


def _block_carries_force(block: str) -> bool:
    return _FORCE_FLAG.search(block) is not None


def _dispatcher_skipped_steps(dispatcher_text: str) -> tuple[set[str], bool]:
    """Derive which steps the dispatcher itself records ``skipped`` for.

    Returns ``(named_steps, any_step)``. ``any_step`` is true when a dispatcher
    block writes ``skipped`` under a placeholder step (``{step_id}``): that
    record can land on every step, so every document can then hold ``skipped``.
    """
    named: set[str] = set()
    any_step = False
    for block in _call_site_blocks(dispatcher_text):
        if _SKIPPED not in _block_outcomes(block):
            continue
        step_match = _STEP_ARG.search(block)
        if step_match is None or '{' in step_match.group(1):
            any_step = True
            continue
        named.add(_bare_step_key(step_match.group(1)))
    return named, any_step


def _offending_blocks(text: str, *, dispatcher_records_skipped: bool) -> list[str]:
    """The predicate under test: blocks that can reach an unforced-illegal pair without ``--force``."""
    blocks = _call_site_blocks(text)
    document_outcomes: set[str] = set()
    for block in blocks:
        document_outcomes |= _block_outcomes(block)
    if dispatcher_records_skipped:
        document_outcomes.add(_SKIPPED)

    offenders = []
    for block in blocks:
        if _block_carries_force(block):
            continue
        outcomes = _block_outcomes(block)
        skipped_over_done = _SKIPPED in outcomes and _DONE in document_outcomes
        other_over_skipped = bool(outcomes - {_SKIPPED}) and _SKIPPED in document_outcomes
        if skipped_over_done or other_over_skipped:
            offenders.append(block)
    return offenders


def _step_records() -> list[dict]:
    """Every step document the finalize registry discovers, in a stable order."""
    return sorted(find_implementors(_EXT_POINT), key=lambda record: str(record['name']))


def _dispatcher_text() -> str:
    text: str = _DISPATCHER_DOC.read_text(encoding='utf-8')
    return text


def _records_skipped_for(record: dict) -> bool:
    named, any_step = _dispatcher_skipped_steps(_dispatcher_text())
    return any_step or _bare_step_key(str(record['name'])) in named


_RECORDS = _step_records()


def test_sweep_examines_a_non_empty_step_document_population(record_property):
    """(1) The registry resolves step documents, and the sweep says how many."""
    examined = len(_RECORDS)
    invocations = sum(len(_call_site_blocks(Path(record['path']).read_text(encoding='utf-8'))) for record in _RECORDS)
    record_property('examined_step_documents', examined)
    record_property('examined_terminal_invocations', invocations)

    assert examined > 0, (
        f'find_implementors({_EXT_POINT!r}) discovered no step document, so the '
        'sweep examined nothing and every per-document assertion in this module '
        'would pass vacuously.'
    )
    assert invocations > 0, (
        f'{examined} step document(s) were discovered but no terminal '
        'mark-step-done invocation parsed out of any of them, so the offender '
        'predicate was never given a block to judge.'
    )


def test_dispatcher_recorded_skipped_set_is_non_empty():
    """(2) The dispatcher-side ``skipped`` derivation resolves something."""
    named, any_step = _dispatcher_skipped_steps(_dispatcher_text())

    assert named or any_step, (
        f'No mark-step-done --outcome skipped invocation parsed out of {_DISPATCHER_DOC}. '
        'The dispatcher records skipped for its signal-gated steps, so an empty '
        'derivation means the parse broke and rule (4) below is unreachable.'
    )

    registry_keys = {_bare_step_key(str(record['name'])) for record in _RECORDS}
    unknown = sorted(named - registry_keys)
    assert not unknown, (
        'The dispatcher records skipped under step keys no registry document '
        f'answers to: {unknown}. The sweep would then never apply the skipped '
        f'rule to the document that needs it. Registry keys: {sorted(registry_keys)}'
    )


@pytest.mark.parametrize('record', _RECORDS, ids=[str(record['name']) for record in _RECORDS])
def test_terminal_marks_carry_force_where_the_transition_table_needs_it(record):
    """(3)/(4) No terminal invocation can reach an unforced-illegal pair without ``--force``."""
    text = Path(record['path']).read_text(encoding='utf-8')

    offenders = _offending_blocks(text, dispatcher_records_skipped=_records_skipped_for(record))

    assert not offenders, (
        f'{record["name"]} ({record["path"]}) has {len(offenders)} terminal '
        'mark-step-done invocation(s) that can write skipped over a stored done, '
        'or another outcome over a stored skipped, without --force. Those pairs '
        'are outside _TRANSITIONS_LEGAL_WITHOUT_FORCE, so the call returns '
        'error: conflict and writes nothing. Offending invocation(s):\n\n' + '\n\n'.join(offenders)
    )


_DONE_CALL = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
    '  --plan-id {plan_id} --phase 6-finalize --step synthetic-step --outcome done \\\n'
    '  --display-detail "synthetic done"'
)

_SKIPPED_CALL = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
    '  --plan-id {plan_id} --phase 6-finalize --step synthetic-step --outcome skipped \\\n'
    '  --display-detail "synthetic skip"'
)

_LOOP_BACK_CALL = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
    '  --plan-id {plan_id} --phase 6-finalize --step synthetic-step --outcome loop_back \\\n'
    '  --loop-back-target 6-finalize --display-detail "synthetic loop-back"'
)

_TEMPLATE_CALL = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \\\n'
    '  mark-step-done --plan-id {plan_id} --phase 6-finalize \\\n'
    '  --step synthetic-step \\\n'
    '  --outcome {done|failed} \\\n'
    '  --display-detail "{display_detail}"'
)

_PROSE_NAMING_BOTH_TOKENS = (
    'Every `--outcome done` branch below MUST capture the worktree HEAD SHA '
    'immediately before the `mark-step-done` call.'
)


def _forced(call: str) -> str:
    return call + ' \\\n  --force'


def test_predicate_flags_a_done_written_over_a_dispatcher_recorded_skipped():
    """Mutation guard for (4): the pre-fix shape of a signal-gated step is an offender."""
    offenders = _offending_blocks(_DONE_CALL, dispatcher_records_skipped=True)

    assert offenders == [_DONE_CALL], (
        'An unforced --outcome done in a document whose step the dispatcher '
        'records skipped was not reported, so rule (4) cannot fail and the sweep '
        'proves nothing about the signal-gated steps.'
    )


def test_predicate_flags_a_skipped_written_in_a_document_that_holds_done():
    """Mutation guard for (3) and (4): both directions of a done/skipped document."""
    document = f'{_DONE_CALL}\n\nSome prose between the two branches.\n\n{_SKIPPED_CALL}\n'

    offenders = _offending_blocks(document, dispatcher_records_skipped=False)

    assert offenders == [_DONE_CALL, _SKIPPED_CALL], (
        'A document whose own branches write both done and skipped must report '
        'BOTH unforced invocations: the skipped can land on a stored done and '
        f'the done on a stored skipped. Reported: {offenders}'
    )


def test_predicate_reads_a_brace_template_outcome():
    """A ``{done|failed}`` template is read as its alternatives, on a continuation-line verb."""
    assert _block_outcomes(_call_site_blocks(_TEMPLATE_CALL)[0]) == {'done', 'failed'}, (
        'A templated --outcome must expand to its alternatives; read as no '
        'outcome at all, the block would drop out of the sweep entirely.'
    )
    assert _offending_blocks(_TEMPLATE_CALL, dispatcher_records_skipped=True) == [_TEMPLATE_CALL]
    assert _offending_blocks(_TEMPLATE_CALL, dispatcher_records_skipped=False) == []


def test_predicate_clears_a_forced_invocation_and_ignores_a_longer_flag():
    """``--force`` clears the block; a flag that merely starts with it does not."""
    assert _offending_blocks(_forced(_DONE_CALL), dispatcher_records_skipped=True) == [], (
        'A forced invocation was reported as an offender, so the sweep would '
        'fail on exactly the documents that are correct.'
    )

    lease_only = _DONE_CALL + ' \\\n  --force-with-lease'
    assert _offending_blocks(lease_only, dispatcher_records_skipped=True) == [lease_only], (
        'A flag that only starts with --force was read as --force, so an '
        'unforced invocation carrying it would read as clean.'
    )


def test_predicate_leaves_retry_and_re_fire_documents_alone():
    """A done/loop_back document never recorded skipped needs no flag anywhere."""
    document = f'{_DONE_CALL}\n\n{_LOOP_BACK_CALL}\n'

    assert _offending_blocks(document, dispatcher_records_skipped=False) == [], (
        'done and loop_back over one another are re-fire transitions inside the '
        'unforced table; reporting them would demand --force where the tool '
        'needs none.'
    )


def test_call_site_boundary_rejects_prose_naming_both_tokens():
    """A sentence naming the verb and an ``--outcome`` argument is not an invocation."""
    assert _MARK_STEP_TOKEN in _PROSE_NAMING_BOTH_TOKENS
    assert _OUTCOME_ARG.search(_PROSE_NAMING_BOTH_TOKENS) is not None

    assert _call_site_blocks(_PROSE_NAMING_BOTH_TOKENS) == [], (
        'A narrative sentence parsed as a terminal call site. It carries no '
        '--force, so a signal-gated document would be reported as an offender '
        'on the strength of its own prose.'
    )


def test_dispatcher_skipped_derivation_reads_named_and_placeholder_steps():
    """Mutation guard for (2): a literal step is named, a placeholder step widens to all."""
    named_only = _SKIPPED_CALL.replace('synthetic-step', 'default:synthetic-step')
    assert _dispatcher_skipped_steps(named_only) == ({'synthetic-step'}, False)

    placeholder = _SKIPPED_CALL.replace('synthetic-step', '{step_id}')
    assert _dispatcher_skipped_steps(placeholder) == (set(), True)

    assert _dispatcher_skipped_steps(_DONE_CALL) == (set(), False), (
        'A dispatcher block that does not write skipped must contribute nothing.'
    )
