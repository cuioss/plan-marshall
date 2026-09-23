#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests pinning the ``analyze`` verb's inbox-scan drain contract.

The contract sources are read-only for this module — it never writes them:

- ``plan-orchestrator/workflow/analyze.md`` — the fourth input mode, the
  per-kind routing map, the landing branch's undiluted corroboration
  obligation, the four Step 5b dispositions, archive-on-consume (including the
  archive-FAILURE branch and its no-re-apply rule), and the widened
  ``## Output`` block.
- ``persona-plan-orchestrator/standards/orchestration-model.md`` — the
  Ledger Write-Boundary's drain-surface anchor, plus the ordinal-drift guard
  over its ``analyze.md`` Step-N citations.

The routing assertion imports ``KINDS`` from ``_orchestrator_inbox`` — the
source of truth — rather than re-listing the enum as a literal. Adding a fourth
kind without giving it a routing branch therefore FAILS this test instead of
silently shipping an unrouted kind.

The module additionally carries the READ side of the channel — the plan-side
``inbox read`` verb — as behavioural assertions driven through the
``orchestrator.py`` CLI with constructed argv at the subprocess boundary
(``run_script``) under ``PLAN_BASE_DIR`` isolation (``plan_context``):

- **Fail-open**: each of the four failure modes — absent epic tree, absent
  mailbox directory, unlistable mailbox, and a message that is unreadable or
  malformed — returns ``status: success`` carrying a discriminator, never an
  error and never a fault. The four are swept as a DERIVED set rather than
  asserted one at a time, so a fifth failure mode cannot be added without a
  case.
- **Fail-open is not vacuous-green**: the *looked, found nothing* zero and each
  *could not look* zero are separately representable, and a mailbox holding only
  unreadable mail is distinguishable from an empty one. The could-not-look set
  is derived from the state vocabulary by subtraction, never re-listed.
- **One address, no second resolver**: the path a read resolves is asserted to
  be the directory the paired ``inbox write --target-plan`` actually delivered
  into — derived from the write's own reported path rather than re-composed
  here, which is what makes it a symmetry check instead of a restatement.
- **Identifier validation stays fail-CLOSED**, pinned by a matched control
  against the fail-open cases, so the bounded exception cannot silently widen
  into "this verb never errors".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from _ledger_fixtures import write_ledger

from conftest import MARKETPLACE_ROOT, get_script_path, load_script_module, run_script

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox')

#: Imported from the source of truth — never re-listed as a literal here.
KINDS = _inbox.KINDS

#: The read verb's state vocabulary and its could-not-look half, both imported
#: from the source of truth. The second is DERIVED there by subtracting the one
#: enumerated state from the whole tuple, so a state added to the vocabulary
#: joins the could-not-look set automatically rather than defaulting into the
#: looked-and-found-nothing reading that a hand-maintained list here would give
#: it.
MAILBOX_STATES = _inbox.MAILBOX_STATES
MAILBOX_COULD_NOT_LOOK_STATES = _inbox.MAILBOX_COULD_NOT_LOOK_STATES
MAILBOX_STATE_PRESENT = _inbox.MAILBOX_STATE_PRESENT

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

#: The epic, the addressed plan, and the sending plan for the read-side cases.
READ_EPIC = 'drain-read-epic'
READER = 'reader-plan'
READ_SENDER = 'sender-plan'

_PLAN_MARSHALL: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_ANALYZE: Path = _PLAN_MARSHALL / 'plan-orchestrator' / 'workflow' / 'analyze.md'
_ORCHESTRATION_MODEL: Path = _PLAN_MARSHALL / 'persona-plan-orchestrator' / 'standards' / 'orchestration-model.md'
_ORCHESTRATOR_SKILL: Path = _PLAN_MARSHALL / 'plan-orchestrator' / 'SKILL.md'

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
    return [stripped for stripped in (line.strip() for line in section.splitlines()) if stripped.startswith(prefix)]


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
    match = re.search(r'\*\*Archive on consume\.\*\*(.*?)(?=```)', _drain_loop_section(), re.DOTALL)
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
        assert 'inbox/' in section, "analyze.md: the Inbox scan row does not name the epic's inbox/ queue as its source"


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
        section = _section(_analyze_text(), '### Step 3: Classify the granularity', 'analyze.md')

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
        section = _section(_analyze_text(), '### Step 3: Classify the granularity', 'analyze.md')

        assert 'inbox archive' in section, (
            'analyze.md: the Step 3 drain loop never names "inbox archive" — a '
            'consumed message would stay queued and be re-processed on re-scan'
        )

    def test_the_ordering_is_persist_then_archive(self):
        section = _section(_analyze_text(), '### Step 3: Classify the granularity', 'analyze.md')

        assert 'persist-then-archive' in section, (
            'analyze.md: the Step 3 drain loop does not state the '
            '"persist-then-archive" ordering — an interrupted drain could retire a '
            'message whose disposition was never persisted'
        )

    def test_an_invalid_message_is_left_un_archived(self):
        section = _section(_analyze_text(), '### Step 3: Classify the granularity', 'analyze.md')

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
                f'analyze.md: the archive-on-consume trigger paragraph does not name {target!r} as a consuming path'
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
                f"analyze.md: the archive-on-consume paragraph's excluded-"
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
            "analyze.md: item 4's archive-failure branch does not record the "
            'failure as an Open Defect — the refusal would leave no ledger record'
        )
        for code in (
            'archive_conflict',
            'archive_dir_unavailable',
            'file_not_found',
            'invalid_message_name',
        ):
            assert code in item, (
                f"analyze.md: item 4's archive-failure branch does not name the "
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
            'analyze.md: the ## Output block\'s mode field does not carry the "inbox_scan" value'
        )

    def test_output_declares_the_three_drain_counters(self):
        section = _section(_analyze_text(), '## Output', 'analyze.md')

        for field in ('messages_scanned', 'messages_archived', 'messages_invalid'):
            assert field in section, (
                f'analyze.md: the ## Output block declares no {field!r} field — the drain result is not reportable'
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

        assert ('messages_archived + messages_invalid + messages_archive_failed == messages_scanned') in section, (
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
            'analyze.md: no "### Step N" headings found — the ordinal-drift guard cannot resolve any citation'
        )
        for ordinal in citations:
            assert ordinal in headings, (
                f'orchestration-model.md cites analyze.md Step {ordinal}, but '
                f'analyze.md has no such Step heading (it has: '
                f'{", ".join(sorted(headings))}) — an ordinal drifted when the '
                f'workflow doc was edited'
            )


# =============================================================================
# (8) Owed-landing: queued-but-unlanded reads owed, unknown reads no-news
# =============================================================================


class TestOwedLanding:
    def test_queued_landing_for_live_plan_reads_owed(self):
        verdict = _inbox.classify_owed_landing({'plan-a'}, {'plan-a'})

        assert verdict['state'] == 'owed'
        assert verdict['owed_plans'] == ['plan-a']
        assert verdict['awaiting_plans'] == []

    def test_live_plan_without_landing_reads_awaiting_not_no_news(self):
        verdict = _inbox.classify_owed_landing({'plan-a'}, set())

        assert verdict['state'] == 'no-news'
        assert verdict['awaiting_plans'] == ['plan-a']
        assert verdict['owed_plans'] == []

    def test_unknown_plan_with_no_queue_reads_no_news(self):
        verdict = _inbox.classify_owed_landing(set(), set())

        assert verdict['state'] == 'no-news'
        assert verdict['owed_plans'] == []
        assert verdict['awaiting_plans'] == []

    def test_queue_reconciliation_runs_both_directions(self):
        report = _inbox.reconcile_queue_vs_landings({'plan-a', 'plan-b'}, {'plan-b', 'plan-c'})

        assert report['queue_without_landing'] == ['plan-a']
        assert report['landing_without_queue'] == ['plan-c']
        assert report['queue_without_landing_count'] == 1
        assert report['landing_without_queue_count'] == 1

    def test_surface_delta_rides_beside_counts(self):
        delta = _inbox.compute_surface_delta({'a.py'}, {'a.py', 'b.py'})

        assert delta['state'] == 'expansion_detected'
        assert delta['added'] == ['b.py']
        assert delta['declared_count'] == 1
        assert delta['realized_count'] == 2


# =============================================================================
# (9) Dedup-at-drain: duplicate candidates file once, recurrence counted
# =============================================================================

_aggregate = load_script_module('plan-marshall', 'manage-lessons', '_lessons_aggregate.py', 'lessons_aggregate_drain')


class TestDedupAtDrain:
    def test_duplicate_candidates_file_once_with_recurrence(self):
        corpus = {
            '2026-09-01-01-001': {
                'component': 'plan-marshall:phase-5-execute',
                'standards_dir': '',
                'body': 'Canonical body about drain state.',
                'title': 'Drain state',
                'recurrence_count': 0,
            },
        }
        candidates = [
            {
                'id': '2026-09-02-01-001',
                'component': 'plan-marshall:phase-5-execute',
                'standards_dir': '',
                'body': 'Canonical body about drain state retold.',
                'title': 'Drain state again',
                'recurrence_count': 0,
            },
        ]
        plan = _aggregate.deduplicate_candidates_at_drain(candidates, corpus)

        assert plan['groups_evaluated'] >= 1
        assert plan['to_file'] == [] or '2026-09-02-01-001' in plan['to_file']
        total_recurrence = sum(plan['recurrences'].values())
        assert total_recurrence >= 1

    def test_distinct_candidates_both_file(self):
        plan = _aggregate.deduplicate_candidates_at_drain(
            [
                {
                    'id': '2026-09-03-01-001',
                    'component': 'plan-marshall:phase-5-execute',
                    'standards_dir': '',
                    'body': 'First distinct body with no shared signals.',
                    'title': 'First',
                    'recurrence_count': 0,
                },
                {
                    'id': '2026-09-03-01-002',
                    'component': 'plan-marshall:manage-tasks',
                    'standards_dir': 'other-dir',
                    'body': 'Second distinct body with no shared signals.',
                    'title': 'Second',
                    'recurrence_count': 0,
                },
            ],
            {},
        )

        assert sorted(plan['to_file']) == ['2026-09-03-01-001', '2026-09-03-01-002']

    def test_corpus_only_group_counts_no_recurrence(self):
        """Corpus lessons grouped without any candidate count no recurrence.

        Recurrence is a drain-time candidate signal: pre-existing corpus
        lessons grouped together register nothing against each other.
        """
        corpus = {
            '2026-09-01-01-001': {
                'component': 'plan-marshall:phase-5-execute',
                'standards_dir': '',
                'body': 'Canonical body about drain state.',
                'title': 'Drain state',
                'recurrence_count': 0,
            },
            '2026-09-01-01-002': {
                'component': 'plan-marshall:phase-5-execute',
                'standards_dir': '',
                'body': 'Canonical body about drain state retold.',
                'title': 'Drain state again',
                'recurrence_count': 0,
            },
        }
        plan = _aggregate.deduplicate_candidates_at_drain([], corpus)

        assert plan['to_file'] == []
        assert sum(plan['recurrences'].values()) == 0


# =============================================================================
# (10) Queue availability: unreadable reads unavailable, never empty
# =============================================================================


class TestQueueAvailability:
    def test_unreadable_queue_marks_unavailable(self):
        report = _inbox._reconcile_queue_with_availability(set(), {'plan-c'}, False)

        assert report['queue_readable'] is False

    def test_readable_queue_marks_readable(self):
        report = _inbox._reconcile_queue_with_availability({'plan-a'}, set(), True)

        assert report['queue_readable'] is True
        assert report['queue_without_landing'] == ['plan-a']


# =============================================================================
# (11) The plan-side read verb — fail-open, and never vacuously green
# =============================================================================


def _env(plan_context) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}


def _epic_dir(plan_context, slug: str = READ_EPIC) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _mailbox_dir(plan_context, plan_id: str = READER, slug: str = READ_EPIC) -> Path:
    return _epic_dir(plan_context, slug) / 'inbox' / 'to' / plan_id


def _scaffold(plan_context, slug: str = READ_EPIC):
    return run_script(SCRIPT_PATH, 'scaffold', '--slug', slug, env_overrides=_env(plan_context))


def _mark_running(plan_context, plan_id: str = READER, slug: str = READ_EPIC) -> None:
    """Make the epic's queue read ``plan_id`` as running, so a write DELIVERS.

    The machine authority the write-side routing decision consults; without it
    every write would queue and the mailbox would never be populated. Seeded as a
    per-concern ledger through ``_ledger_fixtures.write_ledger``: the queue row is
    keyed by a spec id and carries ``plan_id`` as the plan it runs under.
    """
    write_ledger(
        _epic_dir(plan_context, slug),
        {
            'kind': 'orchestrator',
            'phase': 'orchestrating',
            'plans': [{'id': 'PLAN-01', 'status': 'running', 'plan_marshall_plan_id': plan_id}],
            'resume_anchor': '',
        },
    )


def _payload(tmp_path: Path, body: str = 'an advisory for the running plan', name: str = 'p.md') -> str:
    path = tmp_path / name
    path.write_text(body, encoding='utf-8')
    return str(path)


def _write_argv(slug: str, sender: str, kind: str, payload_file: str) -> list[str]:
    return [
        'inbox',
        'write',
        '--slug',
        slug,
        '--sender-type',
        'plan',
        '--sender-id',
        sender,
        '--kind',
        kind,
        '--payload-file',
        payload_file,
    ]


def _deliver(
    plan_context,
    payload_file: str,
    target_plan: str = READER,
    slug: str = READ_EPIC,
    kind: str = 'finding',
    sender: str = READ_SENDER,
):
    """Write a message AIMED at ``target_plan`` — the delivery route."""
    argv = _write_argv(slug, sender, kind, payload_file) + ['--target-plan', target_plan]
    return run_script(SCRIPT_PATH, *argv, env_overrides=_env(plan_context))


def _queue_write(
    plan_context,
    payload_file: str,
    slug: str = READ_EPIC,
    kind: str = 'finding',
    sender: str = READ_SENDER,
):
    """Write an ordinary epic-addressed message — identical argv WITHOUT the aim."""
    return run_script(SCRIPT_PATH, *_write_argv(slug, sender, kind, payload_file), env_overrides=_env(plan_context))


def _read(plan_context, plan_id: str = READER, slug: str = READ_EPIC):
    return run_script(
        SCRIPT_PATH,
        'inbox',
        'read',
        '--slug',
        slug,
        '--plan-id',
        plan_id,
        env_overrides=_env(plan_context),
    )


def _malformed_message(sender: str = READ_SENDER, epic: str = READ_EPIC) -> str:
    """A message whose only defect is an unsupported ``envelope_version``."""
    return (
        'envelope_version=99\n'
        'sender_type=plan\n'
        f'sender_id={sender}\n'
        f'epic={epic}\n'
        'kind=finding\n'
        'created=2020-01-01T00:00:00Z\n'
        '\n'
        'payload prose\n'
    )


def _arrange_no_epic(plan_context) -> None:
    """Nothing at all — the epic was never scaffolded."""


def _arrange_no_mailbox(plan_context) -> None:
    """The epic exists; nothing was ever delivered to this plan."""
    _scaffold(plan_context)


def _arrange_unlistable_mailbox(plan_context) -> None:
    """The mailbox PATH exists but cannot be listed — it is a file, not a directory.

    Chosen over a permission bit because it is deterministic on every platform
    and is never a no-op for a privileged test runner.
    """
    _scaffold(plan_context)
    mailbox = _mailbox_dir(plan_context)
    mailbox.parent.mkdir(parents=True, exist_ok=True)
    mailbox.write_text('not a directory\n', encoding='utf-8')


def _arrange_unreadable_message(plan_context) -> None:
    """A delivered message whose bytes are not UTF-8."""
    _scaffold(plan_context)
    mailbox = _mailbox_dir(plan_context)
    mailbox.mkdir(parents=True, exist_ok=True)
    (mailbox / f'{READ_SENDER}-001.md').write_bytes(b'\xff\xfe not valid utf-8 \xff')


def _arrange_malformed_envelope(plan_context) -> None:
    """A delivered message that reads cleanly but fails envelope validation."""
    _scaffold(plan_context)
    mailbox = _mailbox_dir(plan_context)
    mailbox.mkdir(parents=True, exist_ok=True)
    (mailbox / f'{READ_SENDER}-001.md').write_text(_malformed_message(), encoding='utf-8')


#: The read verb's failure-mode population, keyed by the name the contract uses
#: for each. The parametrized sweeps below derive their cases from this table
#: rather than restating them, so a mode cannot be exercised in one sweep and
#: forgotten in another.
FAIL_OPEN_ARRANGEMENTS = {
    'absent epic tree': _arrange_no_epic,
    'absent mailbox directory': _arrange_no_mailbox,
    'unlistable mailbox': _arrange_unlistable_mailbox,
    'unreadable message': _arrange_unreadable_message,
    'malformed envelope': _arrange_malformed_envelope,
}

#: The subset of the table above whose arrangements leave the mailbox
#: UNENUMERATED, mapped to the discriminator each one must publish. Kept beside
#: the arrangement table so the two cannot drift, and checked for exhaustiveness
#: against the imported vocabulary rather than trusted as written.
FAIL_OPEN_EXPECTED_STATE = {
    'absent epic tree': 'no_epic',
    'absent mailbox directory': 'no_mailbox',
    'unlistable mailbox': 'unreadable',
}


class TestMailboxStateVocabulary:
    """Binding-site non-vacuity guards for every derived sweep below."""

    def test_the_state_vocabulary_is_not_vacuous(self):
        assert MAILBOX_STATES, '_orchestrator_inbox.MAILBOX_STATES is empty — every state assertion below is vacuous'
        assert MAILBOX_COULD_NOT_LOOK_STATES, (
            'the could-not-look set is empty — a read that looked at nothing would satisfy every assertion below'
        )

    def test_exactly_one_state_means_the_mailbox_was_enumerated(self):
        assert MAILBOX_STATE_PRESENT in MAILBOX_STATES
        assert set(MAILBOX_STATES) - MAILBOX_COULD_NOT_LOOK_STATES == {MAILBOX_STATE_PRESENT}, (
            'more than one state reads as "the mailbox was enumerated" — a could-not-look '
            'zero would be indistinguishable from a looked-and-found-nothing zero'
        )

    def test_the_arrangement_table_covers_every_named_failure_mode(self):
        assert set(FAIL_OPEN_ARRANGEMENTS) == {
            'absent epic tree',
            'absent mailbox directory',
            'unlistable mailbox',
            'unreadable message',
            'malformed envelope',
        }, 'the fail-open arrangement table has drifted — the parametrized sweeps would silently shrink with it'

    def test_the_could_not_look_cases_cover_the_whole_could_not_look_vocabulary(self):
        """Derived completeness: a new state cannot ship without a case.

        The expectation set is compared against the vocabulary IMPORTED from the
        source of truth, so adding a member to ``MAILBOX_STATES`` without giving
        it an arrangement fails here rather than passing unnoticed.
        """
        assert set(FAIL_OPEN_EXPECTED_STATE.values()) == set(MAILBOX_COULD_NOT_LOOK_STATES), (
            'the could-not-look arrangements no longer cover the whole vocabulary — '
            'a state ships with no test exercising it'
        )


class TestReadIsFailOpen:
    """Every read-side failure returns success carrying a discriminator."""

    @pytest.mark.parametrize('mode', sorted(FAIL_OPEN_ARRANGEMENTS))
    def test_every_failure_mode_returns_success_with_a_discriminator(self, mode, plan_context):
        FAIL_OPEN_ARRANGEMENTS[mode](plan_context)

        result = _read(plan_context)
        data = result.toon()

        assert result.returncode == 0, mode
        assert data['status'] == 'success', (
            f'{mode!r} made the plan-side read FAULT — a mailbox is an advisory side '
            f'channel, so an advisory that could not be read must never block the reading plan'
        )
        assert data['mailbox_state'] in MAILBOX_STATES, mode

    @pytest.mark.parametrize('mode', sorted(FAIL_OPEN_EXPECTED_STATE))
    def test_each_could_not_look_mode_names_its_own_discriminator(self, mode, plan_context):
        FAIL_OPEN_ARRANGEMENTS[mode](plan_context)

        data = _read(plan_context).toon()

        assert data['mailbox_state'] == FAIL_OPEN_EXPECTED_STATE[mode], mode
        assert data['mailbox_state'] in MAILBOX_COULD_NOT_LOOK_STATES, mode
        assert data['count'] == 0, mode

    def test_an_unreadable_message_rides_a_row_rather_than_faulting(self, plan_context):
        _arrange_unreadable_message(plan_context)

        data = _read(plan_context).toon()

        assert data['status'] == 'success'
        assert data['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert data['invalid_count'] == 1
        assert [row['error'] for row in data['messages']] == ['unreadable']

    def test_a_malformed_envelope_rides_a_row_rather_than_faulting(self, plan_context):
        _arrange_malformed_envelope(plan_context)

        data = _read(plan_context).toon()

        assert data['status'] == 'success'
        assert data['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert data['invalid_count'] == 1
        assert [row['error'] for row in data['messages']] == ['unknown_envelope_version']

    def test_a_valid_message_survives_beside_a_broken_one(self, plan_context, tmp_path):
        """One bad message never truncates the read.

        Matched positive half of the two rows above: without it, an
        ``invalid_count: 1`` payload would be equally explained by the
        enumeration stopping at the broken message.
        """
        _scaffold(plan_context)
        _mark_running(plan_context)
        _deliver(plan_context, _payload(tmp_path, 'good body'))
        (_mailbox_dir(plan_context) / f'{READ_SENDER}-002.md').write_text(_malformed_message(), encoding='utf-8')

        data = _read(plan_context).toon()

        assert data['count'] == 2
        assert data['live_count'] == 1
        assert data['invalid_count'] == 1


class TestReadZerosStayDistinguishable:
    """Fail-open is not vacuous-green: the zeros do not share a representation."""

    def test_looked_and_found_nothing_is_distinct_from_could_not_look(self, plan_context):
        # A matched pair whose two arms differ ONLY in whether the mailbox
        # directory exists. BOTH report count 0, so the count alone decides
        # nothing — the discriminator is what separates them, which is precisely
        # the claim.
        _scaffold(plan_context)
        could_not_look = _read(plan_context).toon()
        _mailbox_dir(plan_context).mkdir(parents=True)

        looked = _read(plan_context).toon()

        assert could_not_look['count'] == 0
        assert looked['count'] == 0
        assert could_not_look['mailbox_state'] in MAILBOX_COULD_NOT_LOOK_STATES
        assert looked['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert could_not_look['mailbox_state'] != looked['mailbox_state'], (
            'a mailbox that could not be looked at reports the same state as one that '
            'was looked at and held nothing — the fail-open read renders as a confident empty'
        )

    def test_a_mailbox_holding_only_broken_mail_is_not_an_empty_mailbox(self, plan_context):
        # The third zero: mail IS addressed here, but none of it is actionable.
        # Reading live_count alone would call this empty and claim a clean read
        # over messages that were never understood.
        _arrange_unreadable_message(plan_context)

        data = _read(plan_context).toon()

        assert data['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert data['live_count'] == 0
        assert data['count'] == 1
        assert data['invalid_count'] == 1


class TestReadResolvesTheDeliveryAddress:
    """One address rule: the read resolves exactly where the write delivered."""

    def test_a_delivered_message_is_returned_to_the_addressed_plan(self, plan_context, tmp_path):
        _scaffold(plan_context)
        _mark_running(plan_context)
        written = _deliver(plan_context, _payload(tmp_path, 'the advisory body')).toon()

        data = _read(plan_context).toon()

        assert written['destination'] == 'mailbox'
        assert data['status'] == 'success'
        assert data['mailbox_state'] == MAILBOX_STATE_PRESENT
        assert data['count'] == 1
        assert data['live_count'] == 1
        assert [row['name'] for row in data['messages']] == [written['message']]

    def test_the_read_resolves_the_directory_the_write_delivered_into(self, plan_context, tmp_path):
        # Derived from the write's OWN reported path rather than re-composed
        # here: a locally rebuilt expected path would only prove this test can
        # spell the layout, not that the two SIDES agree. Agreement is the
        # claim — one address rule, no second resolver.
        _scaffold(plan_context)
        _mark_running(plan_context)
        written = _deliver(plan_context, _payload(tmp_path)).toon()

        data = _read(plan_context).toon()

        assert data['mailbox_dir'] == str(Path(written['path']).parent), (
            'the plan-side read resolves a different directory than the write delivered '
            'into — the channel has grown a second address resolver'
        )

    def test_a_queued_message_is_not_visible_to_a_mailbox_read(self, plan_context, tmp_path):
        # Matched negative control for the round trip above: identical argv
        # except that this write carries no --target-plan, so it QUEUES. Without
        # it, a passing read would be equally explained by the verb returning
        # every message in the epic rather than only those addressed to the plan.
        _scaffold(plan_context)
        _mark_running(plan_context)
        _queue_write(plan_context, _payload(tmp_path))

        data = _read(plan_context).toon()

        assert data['status'] == 'success'
        assert data['count'] == 0
        assert data['mailbox_state'] == 'no_mailbox'

    def test_a_read_of_another_plan_id_does_not_see_this_plans_mail(self, plan_context, tmp_path):
        # The mailboxes are per addressee. Both arms run against the same epic
        # and the same delivered message, differing only in the plan id read.
        _scaffold(plan_context)
        _mark_running(plan_context)
        _deliver(plan_context, _payload(tmp_path))

        mine = _read(plan_context, READER).toon()
        theirs = _read(plan_context, 'some-other-plan').toon()

        assert mine['count'] == 1
        assert theirs['count'] == 0
        assert theirs['mailbox_state'] == 'no_mailbox'

    def test_the_read_leaves_every_non_mailbox_path_byte_identical(self, plan_context, tmp_path):
        # The read reaches the one mailbox address and nothing else in the epic
        # tree: a mailbox read is a read of messages addressed to that plan,
        # never of the epic's own state.
        _scaffold(plan_context)
        _mark_running(plan_context)
        root = _epic_dir(plan_context)
        seeded = {
            'epic.md': '# Epic\n',
            'workstreams/WS-01-a.md': 'charter\n',
            'plans/PLAN-01-a.md': 'spec\n',
            'landings/PLAN-01.md': 'landing\n',
        }
        for rel, content in seeded.items():
            (root / rel).write_text(content, encoding='utf-8')
        delivered = _deliver(plan_context, _payload(tmp_path)).toon()
        assert delivered['destination'] == 'mailbox', 'the setup did not deliver, so the read would reach nothing'
        # The ledger files are part of the epic's own state the read must not touch.
        ledger_files = ['status.json', 'resume_anchor.md', 'queue/PLAN-01.json']
        ledger_before = {rel: (root / rel).read_bytes() for rel in ledger_files}

        _read(plan_context)

        for rel, content in seeded.items():
            assert (root / rel).read_text(encoding='utf-8') == content, rel
        for rel, content_bytes in ledger_before.items():
            assert (root / rel).read_bytes() == content_bytes, rel


class TestReadIdentifierValidationStaysFailClosed:
    """The bounded exception: a nonsense ADDRESS still errors.

    Matched control for the fail-open sweep above. Without it, "this verb never
    returns an error" would describe the code equally well, and the path-safety
    guarantee on the two values that become path components would have no test
    standing behind it. An unsafe identifier is a caller supplying a nonsense
    address, not an advisory that could not be read.
    """

    def test_an_unsafe_slug_is_refused(self, plan_context):
        _scaffold(plan_context)

        data = _read(plan_context, slug='../evil').toon()

        assert data['status'] == 'error'
        assert data['error'] == 'invalid_slug'

    def test_an_unsafe_plan_id_is_refused(self, plan_context):
        _scaffold(plan_context)

        data = _read(plan_context, plan_id='../evil').toon()

        assert data['status'] == 'error'
        assert data['error'] == 'invalid_target_plan'


class TestReadDocContract:
    def test_the_skill_documents_the_read_verb(self):
        section = _section(_ORCHESTRATOR_SKILL.read_text(encoding='utf-8'), '### inbox read', 'SKILL.md')

        assert 'inbox/to/' in section
        assert '--plan-id' in section

    def test_the_skill_documents_every_mailbox_state(self):
        """The documented surface names every state the verb can publish."""
        section = _section(_ORCHESTRATOR_SKILL.read_text(encoding='utf-8'), '### inbox read', 'SKILL.md')

        for state in MAILBOX_STATES:
            assert f'`{state}`' in section, (
                f'SKILL.md § inbox read does not document the {state!r} mailbox state — '
                f'a discriminator the verb publishes has no documented meaning'
            )

    def test_the_write_boundary_records_the_mailbox_read_direction(self):
        section = _section(_model_text(), '## Ledger Write-Boundary', 'orchestration-model.md')

        assert 'inbox read' in section, (
            'orchestration-model.md: § Ledger Write-Boundary describes the mailbox '
            'direction but names no read invocation — the claim is unanchored'
        )
        assert 'never reads the ledger' in section
