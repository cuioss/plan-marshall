#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract guard for the finalize-step ``records_facts`` obligation.

A finalize step used to persist its outcome as ``outcome`` plus a free-text
``display_detail``. Prose is not queryable, so a retrospective could not ask
"did this rebase replay anything?" or "did this step scan at all?" of a
sentence — and two live defects followed from that:

* **Defect A — the fixed literal.** ``branch-cleanup``'s Branch A emitted the
  hardcoded string ``"rebased onto base, merged, cleanup complete"`` on every
  run, so a cleanup whose rebase was a **no-op** still recorded a sentence
  claiming it rebased. The claim was unfalsifiable because nothing structured
  backed it.
* **Defect C — the collapsed zero.** ``sonar-roundtrip`` recorded the same
  ``done`` for "scanned, found zero new-code issues" and for "never scanned"
  (Sonar unconfigured). The two are opposite facts wearing one outcome.

The fix declares a ``records_facts`` frontmatter obligation per step and wires
``mark-step-done --fact KEY=VALUE`` at each terminal call site, so
``display_detail`` becomes a *rendering* of recorded facts rather than their
sole record. These tests pin that contract:

(1) The derived obligation population is **non-empty** — checked first and
    alone, because every later assertion would pass vacuously against an empty
    derivation.
(2) It covers both Watch-entry-named steps,
    ``default:finalize-step-sync-baseline`` and ``default:branch-cleanup``.
(3) It covers ``default:sonar-roundtrip`` (the operator-added third step).
(4) **No orphan declaration** (∃-direction): every declared key appears as a
    ``--fact {key}=`` argument in at least one terminal call-site block of that
    doc.
(5) **No undeclared record** (∀-direction): every ``--fact {key}=`` wired at any
    terminal call-site block is a member of that doc's declaration.
(6) Every step declaring ``work_performed`` carries ``--fact work_performed=``
    on **every** ``--outcome done`` call-site block — the one deliberate
    exception to the honest-subset rule, since absence of that key alone would
    be ambiguous between "did no work" and "the wiring forgot the fact".
(7) Every step declaring ``work_performed`` has at least one ``done`` call site
    recording it **false**. A step where the fact is always ``true`` cannot
    distinguish the two states the fact exists to separate.
(8) *(targeted anchor)* ``branch-cleanup`` Branch A no longer carries the
    unparameterized Defect-A literal.
(9) *(targeted anchor)* ``sonar-roundtrip`` Branch C records
    ``work_performed=false`` and **none** of the three scan facts — the
    Defect-C distinction.

Assertions (1)-(7) are **population-derived**: the step set comes from
``find_implementors()`` and the obligation from each doc's own frontmatter, so a
step that declares ``records_facts`` later is covered with no edit here.
Assertions (8) and (9) are targeted anchors on the two named defects and are
labelled as such — they name specific branches on purpose.

The unit of analysis is deliberately **one terminal ``mark-step-done``
invocation block per call site**, never a doc-wide blob: ``branch-cleanup`` has
four ``--outcome done`` branches plus a ``loop_back`` call, and
``sonar-roundtrip`` has three ``done`` branches plus an ``--outcome failed``
call. A doc-wide scan would let Branch A borrow Branch B's facts and read as
green — which is precisely the honest-subset property these tests exist to
check. ``test_call_site_split_isolates_each_invocation`` guards that split.

Every regex detector carries a mutation guard asserting it fires on the exact
pre-fix text it targets. Without them a typo'd pattern would make the
corresponding assertion vacuously green — the recurring failure shape in this
codebase.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import extension_discovery
from extension_discovery import find_implementors

#: The canonical ext-point whose implementors carry the obligation.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The frontmatter key that IS the obligation declaration.
_FACT_KEY = 'records_facts'

#: The one cross-cutting fact with a fixed key and a ∀-done-branches rule.
_WORK_PERFORMED = 'work_performed'

#: Steps named by the originating Watch entry. Kept distinct from the
#: operator-added third so (2) anchors on the real Watch-entry population
#: rather than on whatever the obligation set happens to contain.
_WATCH_ENTRY_STEPS = (
    'default:finalize-step-sync-baseline',
    'default:branch-cleanup',
)

#: Operator-added, NOT a Watch-entry member — asserted separately by (3).
_OPERATOR_ADDED_STEP = 'default:sonar-roundtrip'

#: The three sonar scan facts Branch C must NOT record (assertion 9).
_SONAR_SCAN_FACTS = ('count_status', 'new_code_issue_count', 'issues_fetched')

#: Defect-A: the unparameterized literal Branch A used to emit unconditionally.
_BRANCH_A_FIXED_LITERAL = 'rebased onto base, merged, cleanup complete'

#: A terminal call site is a ``mark-step-done`` invocation carrying an outcome.
_MARK_STEP_TOKEN = 'mark-step-done'

#: One ``--fact KEY=VALUE`` argument. Value stops at whitespace, so a trailing
#: line-continuation backslash is never absorbed into it.
_FACT_ARG = re.compile(r'--fact\s+([A-Za-z_][A-Za-z0-9_]*)=(\S*)')

#: The ``--outcome`` value of a call-site block.
_OUTCOME_ARG = re.compile(r'--outcome\s+([a-z_]+)')


# ---------------------------------------------------------------------------
# Population derivation (never hardcoded)
# ---------------------------------------------------------------------------


def _declared_facts(doc_path: Path) -> list[str]:
    """Read the ``records_facts`` obligation off one discovered step doc.

    Reuses ``_read_frontmatter_fields`` — the same extraction primitive
    ``_build_implementor_record`` uses for every other implementor field —
    rather than standing up a second frontmatter parser that could drift from
    the one the registry itself reads.
    """
    fields = extension_discovery._read_frontmatter_fields(doc_path, (_FACT_KEY,))
    value = fields.get(_FACT_KEY)
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _declaring_records() -> list[dict]:
    """Every discovered step doc that declares a ``records_facts`` obligation."""
    records = []
    for record in find_implementors(_EXT_POINT):
        facts = _declared_facts(Path(record['path']))
        if facts:
            records.append({**record, 'facts': facts})
    return records


def _declaring_names() -> set[str]:
    return {record['name'] for record in _declaring_records()}


def _record_for(step_name: str) -> dict:
    """Resolve one declaring record by step name (path is never hardcoded)."""
    for record in _declaring_records():
        if record['name'] == step_name:
            return record
    raise AssertionError(
        f'{step_name} declares no {_FACT_KEY} obligation, so the anchor '
        f'assertion has nothing to read. Declaring steps: {sorted(_declaring_names())}'
    )


# ---------------------------------------------------------------------------
# Call-site block parsing — one block per invocation, never a doc-wide blob
# ---------------------------------------------------------------------------


def _call_site_blocks(text: str) -> list[str]:
    """Return each terminal ``mark-step-done`` invocation as its OWN block.

    A block starts at the line carrying the ``mark-step-done`` token and
    extends across shell line-continuations (``\\``), so each invocation's
    ``--outcome`` and ``--fact`` arguments stay bound to that invocation alone.
    Prose mentions of the verb are excluded by requiring an ``--outcome``
    argument: a sentence naming the call is not a call site.
    """
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        if _MARK_STEP_TOKEN not in line:
            continue
        collected = [line]
        cursor = index
        while lines[cursor].rstrip().endswith('\\') and cursor + 1 < len(lines):
            cursor += 1
            collected.append(lines[cursor])
        block = '\n'.join(collected)
        if _OUTCOME_ARG.search(block):
            blocks.append(block)
    return blocks


def _block_outcome(block: str) -> str | None:
    match = _OUTCOME_ARG.search(block)
    return match.group(1) if match else None


def _block_facts(block: str) -> dict[str, str]:
    return dict(_FACT_ARG.findall(block))


def _doc_blocks(record: dict) -> list[str]:
    return _call_site_blocks(Path(record['path']).read_text(encoding='utf-8'))


# ---------------------------------------------------------------------------
# (1) the derivation resolves something
# ---------------------------------------------------------------------------


def test_declared_obligation_population_is_non_empty():
    """(1) Checked first and alone — everything below depends on it."""
    declaring = _declaring_names()

    assert declaring, (
        f'No discovered finalize step declares a {_FACT_KEY} obligation. Every '
        f'assertion in this module would pass vacuously against an empty '
        f'population, so this is checked separately. Either no step doc carries '
        f'the frontmatter key, or find_implementors({_EXT_POINT!r}) discovered '
        f'no step docs at all.'
    )


def test_every_declaring_doc_has_parseable_terminal_call_sites():
    """Vacuity guard: a doc whose call sites do not parse would pass (4)-(7) free."""
    offenders = [
        record['name'] for record in _declaring_records() if not _doc_blocks(record)
    ]

    assert not offenders, (
        f'These steps declare {_FACT_KEY} but no terminal mark-step-done call '
        f'site parsed out of their doc body, so the wiring assertions below '
        f'would be vacuous for them: {offenders}'
    )


# ---------------------------------------------------------------------------
# (2)/(3) the obligation covers the named steps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('step_name', _WATCH_ENTRY_STEPS)
def test_obligation_covers_watch_entry_step(step_name):
    """(2) Parametrized per step so dropping exactly one fails identifiably."""
    declaring = _declaring_names()

    assert step_name in declaring, (
        f'{step_name} is a Watch-entry-named step whose prose-only record is '
        f'the defect this contract fixes, but it declares no {_FACT_KEY} '
        f'obligation. Declaring steps: {sorted(declaring)}'
    )


def test_obligation_covers_the_operator_added_step():
    """(3) sonar-roundtrip — the operator-added third, not a Watch-entry member."""
    declaring = _declaring_names()

    assert _OPERATOR_ADDED_STEP in declaring, (
        f'{_OPERATOR_ADDED_STEP} must declare a {_FACT_KEY} obligation: its '
        f'"scanned, zero issues" and "never scanned" branches are otherwise the '
        f'same record. Declaring steps: {sorted(declaring)}'
    )


# ---------------------------------------------------------------------------
# (4)/(5) declaration-vs-wiring, the only two detector directions
# ---------------------------------------------------------------------------


def test_no_orphan_declaration():
    """(4) ∃-direction: each declared key is wired at >=1 terminal call site."""
    offenders = []
    for record in _declaring_records():
        wired = set()
        for block in _doc_blocks(record):
            wired.update(_block_facts(block))
        orphans = [key for key in record['facts'] if key not in wired]
        if orphans:
            offenders.append(f"{record['name']}: {orphans}")

    assert not offenders, (
        'These steps declare fact keys that no terminal mark-step-done call site '
        'actually records — a declared-but-unwired obligation, which buys the '
        f'consumer nothing: {offenders}'
    )


def test_no_undeclared_record():
    """(5) ∀-direction: every wired key is a member of the declaration."""
    offenders = []
    for record in _declaring_records():
        declared = set(record['facts'])
        for block in _doc_blocks(record):
            undeclared = [key for key in _block_facts(block) if key not in declared]
            if undeclared:
                offenders.append(f"{record['name']}: {undeclared}")

    assert not offenders, (
        'These steps wire --fact keys that their records_facts frontmatter does '
        'not declare, so the wiring has drifted past the contract the frontmatter '
        f'publishes: {offenders}'
    )


# ---------------------------------------------------------------------------
# (6)/(7) the work_performed exception
# ---------------------------------------------------------------------------


def test_work_performed_is_recorded_on_every_done_call_site():
    """(6) The one key whose absence on a branch would be ambiguous."""
    offenders = []
    for record in _declaring_records():
        if _WORK_PERFORMED not in record['facts']:
            continue
        for block in _doc_blocks(record):
            if _block_outcome(block) != 'done':
                continue
            if _WORK_PERFORMED not in _block_facts(block):
                offenders.append(f"{record['name']}: {block.splitlines()[0].strip()}")

    assert not offenders, (
        f'These --outcome done call sites omit --fact {_WORK_PERFORMED}=. For a '
        f'step that declares the key, EVERY done call site must record it (true '
        f'or false, never omitted) — absence would otherwise be ambiguous between '
        f'"this branch did no work" and "the wiring forgot the fact", which is '
        f'the exact ambiguity the fact removes: {offenders}'
    )


def test_work_performed_has_a_false_carrier_on_every_declaring_step():
    """(7) A key that is always ``true`` cannot separate the two states."""
    offenders = []
    for record in _declaring_records():
        if _WORK_PERFORMED not in record['facts']:
            continue
        values = {
            _block_facts(block).get(_WORK_PERFORMED)
            for block in _doc_blocks(record)
            if _block_outcome(block) == 'done'
        }
        if 'false' not in values:
            offenders.append(f"{record['name']}: recorded values {sorted(v for v in values if v)}")

    assert not offenders, (
        f'These steps declare {_WORK_PERFORMED} but no --outcome done call site '
        f'records it false. The key exists precisely because a done branch is '
        f'reachable WITHOUT the step having performed its characteristic work; '
        f'if every branch reports true, the declaration distinguishes nothing: '
        f'{offenders}'
    )


# ---------------------------------------------------------------------------
# (8) targeted anchor — Defect A, the branch-cleanup fixed literal
# ---------------------------------------------------------------------------


def test_branch_cleanup_no_longer_carries_the_fixed_literal():
    """(8) TARGETED ANCHOR (not population-derived): the Defect-A literal is gone."""
    record = _record_for('default:branch-cleanup')
    body = Path(record['path']).read_text(encoding='utf-8')

    assert _BRANCH_A_FIXED_LITERAL not in body, (
        f'branch-cleanup still emits the unparameterized literal '
        f'{_BRANCH_A_FIXED_LITERAL!r}. That sentence claims a rebase on every '
        f'run, including a run whose rebase was a no-op — Defect A. The rebase '
        f'claim must be rendered from the recorded action fact instead.'
    )


# ---------------------------------------------------------------------------
# (9) targeted anchor — Defect C, the sonar-roundtrip no-scan branch
# ---------------------------------------------------------------------------


def _sonar_branch_c_block() -> str:
    """The sonar-roundtrip no-scan call site, identified by its rendered detail."""
    record = _record_for(_OPERATOR_ADDED_STEP)
    candidates = [
        block for block in _doc_blocks(record) if 'Sonar not configured' in block
    ]
    assert len(candidates) == 1, (
        f'Expected exactly one sonar-roundtrip "Sonar not configured" call-site '
        f'block (Branch C); found {len(candidates)}. The anchor cannot identify '
        f'the branch it asserts over.'
    )
    return candidates[0]


def test_sonar_branch_c_records_only_that_no_work_was_performed():
    """(9) TARGETED ANCHOR (not population-derived): the Defect-C distinction."""
    facts = _block_facts(_sonar_branch_c_block())

    assert facts.get(_WORK_PERFORMED) == 'false', (
        f'sonar-roundtrip Branch C performed no scan, so it must record '
        f'--fact {_WORK_PERFORMED}=false. Recorded: {facts}'
    )

    leaked = [key for key in _SONAR_SCAN_FACTS if key in facts]
    assert not leaked, (
        f'sonar-roundtrip Branch C records scan facts {leaked} despite never '
        f'scanning. Recording them here would collapse "no scan performed" back '
        f'into "scan performed, zero new-code issues" — Defect C exactly. '
        f'Recorded: {facts}'
    )


# ---------------------------------------------------------------------------
# Mutation guards — one per detector, each fired against its pre-fix text
# ---------------------------------------------------------------------------


#: The exact pre-fix Branch A call site from branch-cleanup.md (Defect A).
_PRE_FIX_BRANCH_A = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
    '  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \\\n'
    '  --display-detail "rebased onto base, merged, cleanup complete"'
)

#: The exact pre-fix Branch C call site from sonar-roundtrip.md (Defect C).
_PRE_FIX_SONAR_BRANCH_C = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
    '  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \\\n'
    '  --display-detail "Sonar not configured" \\\n'
    '  --head-at-completion {sha}'
)


def test_fixed_literal_detector_fires_on_the_pre_fix_branch_a():
    """Guards (8): a typo'd literal would make the assertion vacuously green."""
    assert _BRANCH_A_FIXED_LITERAL in _PRE_FIX_BRANCH_A, (
        'The Defect-A literal detector does not match the known pre-fix Branch A '
        'text, so assertion (8) proves nothing'
    )

    post_fix = '  --display-detail "{rendered_detail}"'
    assert _BRANCH_A_FIXED_LITERAL not in post_fix


def test_fact_and_outcome_detectors_fire_on_the_pre_fix_call_sites():
    """Guards (4)/(5)/(6)/(7)/(9): the pre-fix shape wired NO facts at all."""
    for label, pre_fix in (
        ('branch-cleanup Branch A', _PRE_FIX_BRANCH_A),
        ('sonar-roundtrip Branch C', _PRE_FIX_SONAR_BRANCH_C),
    ):
        blocks = _call_site_blocks(pre_fix)
        assert len(blocks) == 1, (
            f'Call-site parse failed on the known pre-fix {label} invocation; '
            f'got {len(blocks)} blocks'
        )
        assert _block_outcome(blocks[0]) == 'done', (
            f'Outcome detector failed to read --outcome done from the pre-fix '
            f'{label} invocation, so assertions (6)/(7) would be vacuous'
        )
        assert _block_facts(blocks[0]) == {}, (
            f'Fact detector reported facts on the pre-fix {label} invocation, '
            f'which wired none — assertions (4)/(6)/(9) would be vacuous'
        )

    post_fix = (
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
        '  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \\\n'
        '  --fact work_performed=false \\\n'
        '  --display-detail "Sonar not configured, no scan performed"'
    )
    assert _block_facts(_call_site_blocks(post_fix)[0]) == {'work_performed': 'false'}, (
        'Fact detector failed to read a real --fact argument'
    )


def test_call_site_split_isolates_each_invocation():
    """Guards the unit of analysis: per call site, never one doc-wide blob.

    A doc-wide scan would let one branch borrow another branch's facts, so the
    honest-subset assertions (4)/(6)/(9) would pass on a doc where every fact
    sits on a single branch. This guard pins that two adjacent invocations parse
    as two blocks with independent outcomes and independent fact sets.
    """
    doc = (
        'Branch one:\n\n```bash\n'
        'python3 x mark-step-done \\\n'
        '  --outcome done \\\n'
        '  --fact work_performed=true\n'
        '```\n\nBranch two:\n\n```bash\n'
        'python3 x mark-step-done \\\n'
        '  --outcome failed \\\n'
        '  --fact count_status=undecidable\n'
        '```\n'
    )

    blocks = _call_site_blocks(doc)

    assert len(blocks) == 2, f'Expected two isolated call-site blocks, got {len(blocks)}'
    assert [_block_outcome(block) for block in blocks] == ['done', 'failed']
    assert _block_facts(blocks[0]) == {'work_performed': 'true'}
    assert _block_facts(blocks[1]) == {'count_status': 'undecidable'}


def test_prose_mentions_are_not_counted_as_call_sites():
    """Guards the call-site definition: a sentence naming the verb is not one.

    Without this the ``--outcome done`` requirement in (6) could be satisfied —
    or spuriously violated — by narrative text that merely discusses the call.
    """
    prose = (
        'The dispatcher marks this step failed via `manage-status mark-step-done` '
        'before continuing with the next manifest step.'
    )

    assert _call_site_blocks(prose) == []
