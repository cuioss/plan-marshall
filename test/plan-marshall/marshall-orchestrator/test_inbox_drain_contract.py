#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests pinning the ``analyze`` verb's inbox-scan drain contract.

The contract sources are read-only for this module — it never writes them:

- ``marshall-orchestrator/workflow/analyze.md`` — the fourth input mode, the
  per-kind routing map, the landing branch's undiluted corroboration
  obligation, the four Step 5b dispositions, archive-on-consume (including the
  archive-FAILURE branch and its no-re-apply rule), and the widened
  ``## Output`` block.
- ``persona-marshall-orchestrator/standards/orchestration-model.md`` — the
  Ledger Write-Boundary's drain-surface anchor, plus the ordinal-drift guard
  over its ``analyze.md`` Step-N citations.

The routing assertion imports ``KINDS`` from ``_orchestrator_inbox`` — the
source of truth — rather than re-listing the enum as a literal. Adding a fourth
kind without giving it a routing branch therefore FAILS this test instead of
silently shipping an unrouted kind.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

_inbox = load_script_module(
    'plan-marshall', 'marshall-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)

#: Imported from the source of truth — never re-listed as a literal here.
KINDS = _inbox.KINDS

_PLAN_MARSHALL: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_ANALYZE: Path = _PLAN_MARSHALL / 'marshall-orchestrator' / 'workflow' / 'analyze.md'
_ORCHESTRATION_MODEL: Path = (
    _PLAN_MARSHALL / 'persona-marshall-orchestrator' / 'standards' / 'orchestration-model.md'
)

#: The four Step 5b dispositions, as the bolded table labels analyze.md carries.
DISPOSITIONS = ('Promote', 'Fold', 'Stage', 'Discard')

#: Matches an ``analyze.md`` Step-N citation, e.g. ``` `analyze.md` Step 2 ```.
_CITATION_RE = re.compile(r'analyze\.md`?\s+Step\s+(\d+[a-z]?)\b')

#: Matches a Step heading in analyze.md at either the ``###`` or ``####`` level.
_HEADING_RE = re.compile(r'^#{3,4} Step (\d+[a-z]?)\b', re.MULTILINE)


def _analyze_text() -> str:
    return _ANALYZE.read_text(encoding='utf-8')


def _model_text() -> str:
    return _ORCHESTRATION_MODEL.read_text(encoding='utf-8')


def _section(text: str, heading_prefix: str, source: str) -> str:
    """Return the body under the first heading starting with ``heading_prefix``.

    Collection stops at the next heading of the SAME level OR SHALLOWER (e.g. a
    ``##`` terminates a ``###`` section), so a nested subsection (``####`` under
    a ``###``) stays inside the returned body while a sibling or parent heading
    of the target does not bleed in.
    """
    level = heading_prefix.split(' ', 1)[0]
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(heading_prefix))
    except StopIteration:
        raise AssertionError(
            f'{source}: heading not found: {heading_prefix!r} — the drain contract '
            f'cannot be verified because the section it lives under is gone or renamed'
        ) from None
    collected: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.lstrip()
        hashes = len(stripped) - len(stripped.lstrip('#'))
        if 0 < hashes <= len(level) and stripped[hashes : hashes + 1] == ' ':
            break
        collected.append(line)
    return '\n'.join(collected)


def _rows(section: str, prefix: str) -> list[str]:
    """Return the section's table rows whose stripped form starts with ``prefix``.

    Rows are stripped BEFORE the prefix test because a markdown table nested
    inside a numbered list item is indented to the item's continuation column.
    A matcher anchored at column zero would silently find nothing there — it
    could only pass against an unindented table, which makes it a vacuous guard
    that never actually reads the contract it claims to pin.
    """
    return [
        stripped
        for stripped in (line.strip() for line in section.splitlines())
        if stripped.startswith(prefix)
    ]


def _drain_loop_section() -> str:
    return _section(_analyze_text(), '### Step 3: Classify the granularity', 'analyze.md')


def _archive_on_consume_item() -> str:
    """Return ALL of item 4, from its bolded label to the end of the Step 3 body.

    Wider than :func:`_archive_trigger_paragraph` on purpose: the archive-failure
    branch and its no-re-apply rule live in sub-items BELOW item 4's command
    fence, so a scope that stops at the fence cannot see them.
    """
    section = _drain_loop_section()
    marker = '**Archive on consume.**'
    start = section.find(marker)
    assert start != -1, (
        'analyze.md: the "**Archive on consume.**" item (item 4) was not found — '
        'the archive contract cannot be verified'
    )
    return section[start:]


def _archive_trigger_paragraph() -> str:
    """Return item 4's opening paragraph only — the label up to its command fence.

    This is the in-line index of the consuming/excluded disposition sets, so it
    is deliberately scoped ABOVE the fence and away from the sub-items.
    """
    match = re.search(
        r'\*\*Archive on consume\.\*\*(.*?)(?=```)', _drain_loop_section(), re.DOTALL
    )
    assert match, (
        'analyze.md: the "**Archive on consume.**" paragraph (item 4) was not '
        'found — the archive-trigger rule cannot be verified'
    )
    return match.group(1)


# =============================================================================
# (1) Four input modes, and the count-prose agrees
# =============================================================================


class TestFourInputModes:
    def test_analyze_declares_the_four_input_modes_heading(self):
        text = _analyze_text()

        assert '### The four input modes' in text, (
            'analyze.md: missing the "### The four input modes" heading — the '
            'inbox-scan mode is not declared as a first-class input mode'
        )

    def test_analyze_no_longer_carries_the_stale_three_mode_heading(self):
        text = _analyze_text()

        assert '### The three input modes' not in text, (
            'analyze.md: stale count-prose "### The three input modes" survives '
            'alongside the fourth mode — the heading count disagrees with the table'
        )

    def test_inputs_table_count_prose_says_four(self):
        section = _section(_analyze_text(), '## Inputs', 'analyze.md')

        assert 'four first-class input modes' in section, (
            'analyze.md: the ## Inputs table\'s "analysis input" row does not say '
            '"four first-class input modes" — the row still under-counts the modes'
        )

    def test_the_modes_table_carries_exactly_four_rows(self):
        section = _section(_analyze_text(), '### The four input modes', 'analyze.md')
        rows = _rows(section, '| **')

        assert len(rows) == 4, (
            f'analyze.md: the input-modes table has {len(rows)} mode rows, expected 4 — '
            f'the table and its "four input modes" heading disagree'
        )

    def test_the_inbox_scan_mode_row_is_present(self):
        section = _section(_analyze_text(), '### The four input modes', 'analyze.md')

        assert '**Inbox scan**' in section, (
            'analyze.md: the input-modes table has no "Inbox scan" row — the fourth '
            'mode is announced by the heading but never defined'
        )
        assert 'inbox/' in section, (
            'analyze.md: the Inbox scan row does not name the epic\'s inbox/ queue '
            'as its source'
        )


# =============================================================================
# (2) Every KINDS member has a named routing branch — no unrouted kind
# =============================================================================


class TestPerKindRouting:
    def test_the_routing_map_is_not_vacuous(self):
        assert KINDS, (
            '_orchestrator_inbox.KINDS is empty — the routing assertion below would '
            'pass vacuously without checking anything'
        )

    def test_every_kind_has_a_named_routing_branch(self):
        section = _section(
            _analyze_text(), '### Step 3: Classify the granularity', 'analyze.md'
        )

        for kind in sorted(KINDS):
            row = next(iter(_rows(section, f'| `{kind}` |')), None)
            assert row is not None, (
                f'analyze.md: the Step 3 drain-loop routing map has no branch for '
                f'kind {kind!r} — a message of that kind would be enumerated and '
                f'then left unrouted'
            )
            assert 'Step' in row, (
                f'analyze.md: the routing branch for kind {kind!r} names no target '
                f'Step — the branch is declared but points nowhere'
            )


# =============================================================================
# (3) Landing branch: lead-not-a-fact, and --set-row stays the sole stamper
# =============================================================================


class TestLandingBranch:
    def test_landing_branch_carries_the_corroboration_obligation(self):
        section = _section(_analyze_text(), '### Step 4:', 'analyze.md')

        assert 'lead, not a fact' in section, (
            'analyze.md: Step 4 does not state that an inbox landing message is a '
            '"lead, not a fact" — the ground-truth obligation reads as diluted for '
            'the inbox-scan source'
        )
        for claim in ('PR number', 'merge state', 'deliverable set'):
            assert claim in section, (
                f'analyze.md: Step 4 does not name the {claim!r} among the claims '
                f'corroborated against ground truth before the landing is recorded'
            )

    def test_landing_branch_keeps_set_row_as_the_stamping_mechanism(self):
        section = _section(_analyze_text(), '### Step 4:', 'analyze.md')

        assert 'queue --set-row' in section, (
            'analyze.md: Step 4 no longer names "queue --set-row" — the sole '
            'sanctioned landing-stamping mechanism is missing'
        )

    def test_the_whole_array_rewrite_is_still_forbidden_for_stamping(self):
        section = _section(_analyze_text(), '### Step 4:', 'analyze.md')

        assert 'MUST NOT be used to stamp a landing' in section, (
            'analyze.md: Step 4 no longer forbids the whole-array '
            '"manage-status update-field --field plans" rewrite for stamping a '
            'landing — the lost-update prohibition has been dropped'
        )


# =============================================================================
# (4) The four Step 5b dispositions
# =============================================================================


class TestDispositions:
    def test_every_disposition_is_named(self):
        section = _section(_analyze_text(), '### Step 5b:', 'analyze.md')

        for disposition in DISPOSITIONS:
            assert f'**{disposition}**' in section, (
                f'analyze.md: Step 5b does not name the {disposition!r} disposition — '
                f'a drained message could reach no recorded outcome'
            )

    def test_every_message_gets_exactly_one_recorded_disposition(self):
        section = _section(_analyze_text(), '### Step 5b:', 'analyze.md')

        assert 'exactly one recorded, auditable disposition' in section, (
            'analyze.md: Step 5b does not require exactly one recorded, auditable '
            'disposition per message — a message could be silently dropped'
        )
        assert '--store orchestrator' in section, (
            'analyze.md: Step 5b does not require a manage-logging decision line '
            'against the orchestrator store — the disposition would not be auditable'
        )


# =============================================================================
# (5) Archive-on-consume, strictly persist-then-archive
# =============================================================================


class TestArchiveOnConsume:
    def test_the_drain_archives_a_consumed_message(self):
        section = _section(
            _analyze_text(), '### Step 3: Classify the granularity', 'analyze.md'
        )

        assert 'inbox archive' in section, (
            'analyze.md: the Step 3 drain loop never names "inbox archive" — a '
            'consumed message would stay queued and be re-processed on re-scan'
        )

    def test_the_ordering_is_persist_then_archive(self):
        section = _section(
            _analyze_text(), '### Step 3: Classify the granularity', 'analyze.md'
        )

        assert 'persist-then-archive' in section, (
            'analyze.md: the Step 3 drain loop does not state the '
            '"persist-then-archive" ordering — an interrupted drain could retire a '
            'message whose disposition was never persisted'
        )

    def test_an_invalid_message_is_left_un_archived(self):
        section = _section(
            _analyze_text(), '### Step 3: Classify the granularity', 'analyze.md'
        )

        assert 'un-archived' in section, (
            'analyze.md: the Step 3 drain loop does not state that an invalid '
            'message is left un-archived — a malformed message could be consumed '
            'without ever being processed'
        )
        assert 'Open Defect' in section, (
            'analyze.md: the Step 3 drain loop does not record an invalid message '
            'as an Open Defect — the validator error code would go unrecorded'
        )

    def test_the_archive_trigger_covers_every_consuming_path(self):
        """A Step-5-absorbed finding (the ``observed`` disposition) must archive too.

        Regression guard for the gap where item 4 named only "Step 5b" and "Step
        4" as archive triggers: a ``kind: finding`` message Step 5 fully absorbed
        into a Watch or Open Defect (never escalated to Step 5b) matched neither
        named trigger and was never archived, contradicting the ``## Output``
        block's own ``observed`` disposition and its
        ``messages_archived + messages_invalid == messages_scanned`` invariant.
        """
        paragraph = _archive_trigger_paragraph()

        assert 'observed' in paragraph, (
            'analyze.md: the archive-on-consume trigger paragraph does not name '
            'the Step 5 "observed" absorption path — a finding fully absorbed by '
            'Step 5 (and never escalated to Step 5b) would match no archive '
            'trigger and stay queued forever, re-processed on every drain'
        )
        for target in ('Step 4', 'Step 5b'):
            assert target in paragraph, (
                f'analyze.md: the archive-on-consume trigger paragraph does not '
                f'name {target!r} as a consuming path'
            )

    def test_the_excluded_disposition_list_names_both_exclusions(self):
        """Item 4's in-line enumeration indexes the non-consuming dispositions.

        Once ``archive_failed`` joined ``drained[]`` it became a SECOND
        non-consuming disposition, so a list naming only ``invalid`` is an
        incomplete index of the set it indexes.
        """
        paragraph = _archive_trigger_paragraph()

        for excluded in ('invalid', 'archive_failed'):
            assert excluded in paragraph, (
                f'analyze.md: the archive-on-consume paragraph\'s excluded-'
                f'disposition list does not name {excluded!r} — the in-line '
                f'enumeration under-counts the non-consuming dispositions'
            )

    def test_the_archive_failure_branch_is_declared(self):
        item = _archive_on_consume_item()

        assert 'status: error' in item, (
            'analyze.md: item 4 declares no "status: error" branch for the '
            '"inbox archive" call — a refused archival would be indistinguishable '
            'from a successful one and the message silently re-processed'
        )
        assert 'Open Defect' in item, (
            'analyze.md: item 4\'s archive-failure branch does not record the '
            'failure as an Open Defect — the refusal would leave no ledger record'
        )
        for code in (
            'archive_conflict',
            'archive_dir_unavailable',
            'file_not_found',
            'invalid_message_name',
        ):
            assert code in item, (
                f'analyze.md: item 4\'s archive-failure branch does not name the '
                f'{code!r} error code among the refusals it records'
            )

    def test_a_failed_archival_is_never_re_applied_on_a_later_drain(self):
        item = _archive_on_consume_item()

        assert 'MUST NOT be re-applied' in item, (
            'analyze.md: item 4 does not forbid re-applying the persisted '
            'disposition of a message whose archival failed — every later drain '
            'would re-run its full branch'
        )
        assert '--as-name' in item, (
            'analyze.md: item 4 does not name the "inbox archive --as-name" '
            'recovery path the Open Defect is waiting on — the defect names no '
            'route out'
        )


# =============================================================================
# (6) The widened ## Output block
# =============================================================================


class TestOutputBlock:
    def test_output_declares_the_mode_discriminator(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        assert 'mode:' in section, (
            'analyze.md: the ## Output block declares no "mode" field — a consumer '
            'cannot tell the singular half from the plural half'
        )
        assert 'inbox_scan' in section, (
            'analyze.md: the ## Output block\'s mode field does not carry the '
            '"inbox_scan" value'
        )

    def test_output_declares_the_three_drain_counters(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        for field in ('messages_scanned', 'messages_archived', 'messages_invalid'):
            assert field in section, (
                f'analyze.md: the ## Output block declares no {field!r} field — the '
                f'drain result is not reportable'
            )

    def test_output_declares_the_drained_table(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        assert 'drained[' in section, (
            'analyze.md: the ## Output block declares no "drained[" table — the '
            'per-message outcomes have nowhere to ride under inbox scan'
        )

    def test_output_declares_the_archive_failed_counter(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        assert 'messages_archive_failed' in section, (
            'analyze.md: the ## Output block declares no "messages_archive_failed" '
            'counter — a refused archival is unreportable, so the accounting '
            'invariant stays a prose claim with no enforcing number'
        )

    def test_output_declares_the_archive_failed_disposition(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        assert '`archive_failed`' in section, (
            'analyze.md: the ## Output block does not declare "archive_failed" as a '
            'drained[] disposition — the per-message row cannot carry the outcome'
        )

    def test_output_states_the_widened_three_term_invariant(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        assert (
            'messages_archived + messages_invalid + messages_archive_failed '
            '== messages_scanned'
        ) in section, (
            'analyze.md: the ## Output block still states the two-term accounting '
            'invariant — a message left un-archived by a refused archival would '
            'read as an unexplained gap'
        )


# =============================================================================
# (7) Write-Boundary anchor + the ordinal-drift guard
# =============================================================================


class TestWriteBoundaryAnchor:
    def test_the_write_boundary_names_the_drain_surface(self):
        section = _section(_model_text(), '## Ledger Write-Boundary', 'orchestration-model.md')

        assert 'analyze.md' in section, (
            'orchestration-model.md: § Ledger Write-Boundary claims "the orchestrator '
            'drains" but names no drain surface — the claim is vacuous'
        )
        for verb in ('inbox list', 'inbox archive'):
            assert verb in section, (
                f'orchestration-model.md: § Ledger Write-Boundary does not name '
                f'"{verb}" — the drain claim is not anchored to a real invocation'
            )


class TestOrdinalDriftGuard:
    def test_the_guard_finds_citations_to_check(self):
        citations = _CITATION_RE.findall(_model_text())

        assert citations, (
            'orchestration-model.md: no "analyze.md Step N" citation found — the '
            'ordinal-drift guard below would pass vacuously without checking anything'
        )

    def test_every_analyze_step_citation_resolves_to_a_real_heading(self):
        citations = _CITATION_RE.findall(_model_text())
        headings = set(_HEADING_RE.findall(_analyze_text()))

        assert headings, (
            'analyze.md: no "### Step N" headings found — the ordinal-drift guard '
            'cannot resolve any citation'
        )
        for ordinal in citations:
            assert ordinal in headings, (
                f'orchestration-model.md cites analyze.md Step {ordinal}, but '
                f'analyze.md has no such Step heading (it has: '
                f'{", ".join(sorted(headings))}) — an ordinal drifted when the '
                f'workflow doc was edited'
            )
