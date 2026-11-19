#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the ``analyze`` false-claim paragraph.

``analyze`` Step 4 re-reads the four review-and-Sonar numbers from the provider
and records a difference as a **false claim**. That rule is head-bound: the
landing's numbers are the merge gate's read on the head, which is how
``plan-orchestrator/standards/landing-payload-spec.md`` defines every one of
them, so a re-read compared against the same head is the only basis on which a
difference can mean "the landing asserted a state the provider does not show".

Two shapes would break that: a re-read scoped to "the PR's current state", and an
exemption for a difference "caused by activity after the merge". Both make the
rule undecidable from the data the drain reads — the re-read reports counts, not
timestamps, so the drain cannot tell a post-merge change from a wrong claim —
and both contradict the standard the paragraph is written against.

The paragraph's second half is a parser clause. ``runbook_lane review-gate``
fetches the provider's comment data itself, in-process, through
``fetch_pr_comments_data``; it shells out to no ``ci pr comments`` call. The
clause that named that subcommand was stale, and the pin here reads the script
so the claim cannot drift back into prose nobody re-checks.

Every DETECTOR below is paired with a matched control that plants its violation in
a temporary tree and shows the same detector firing; a presence check whose
detector cannot fire is covered by its absence-shaped control. A detector with no
control passes by never being able to fail, which is the shape this file exists
against.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

_PLAN_ORCHESTRATOR = Path(MARKETPLACE_ROOT) / 'plan-marshall' / 'skills' / 'plan-orchestrator'
_ANALYZE_MD: Path = _PLAN_ORCHESTRATOR / 'workflow' / 'analyze.md'
_LANDING_SPEC: Path = _PLAN_ORCHESTRATOR / 'standards' / 'landing-payload-spec.md'
_REVIEW_GATE_SCRIPT: Path = (
    Path(MARKETPLACE_ROOT) / 'plan-marshall' / 'skills' / 'runbook-lane' / 'scripts' / 'runbook_lane.py'
)

#: The paragraph this file governs, bounded by its own opening and the next
#: Step 4 paragraph. Bounded rather than document-wide: the words "current state"
#: and "merge" are ordinary elsewhere in the document, and a document-wide
#: absence check would either fail on legitimate wording or force it out.
_PARAGRAPH_START = (
    '**The four review-and-Sonar numbers are re-read from the provider, and a difference is a false claim.**'
)
_PARAGRAPH_END = '**Parse the `steps` fact'

#: The head-bound reading the paragraph must state.
_HEAD_BOUND_MARKER = 'on the merged head'

#: The wording that scopes the re-read to the live PR instead of the head, and the
#: exemption that lets a difference pass unexplained. Each is a violation on its own.
_LIVE_STATE_MARKERS: tuple[str, ...] = ("PR's current state", 'current state')
_EXEMPTION_MARKERS: tuple[str, ...] = ('after the merge', 'not the state at merge time')

#: The stale parser clause, and the shape that replaces it: the provider's own
#: single in-process read.
_STALE_PARSER_CLAUSE = 'ci pr comments'
_PROVIDER_READ_MARKERS: tuple[str, ...] = ("provider's own single", "provider's single")

#: The merge-gate read the standard defines each number as.

#: The review gate's own data fetch, read from the script rather than trusted from
#: the prose beside it.
_REVIEW_READ_FUNCTION = 'def _read_review_surfaces('
_IN_PROCESS_FETCH = 'fetch_pr_comments_data('
#: The precise shape of a shelled-out read: a call on the subprocess module. The
#: bare word would also fire on an explanatory docstring sentence, and the import
#: alone misses the module-level-import-then-call shape this repository uses.
_SUBPROCESS_MARKER = 'subprocess.'
_CI_SUBCOMMAND_LITERAL = "'pr comments'"


def _read(path: Path) -> str:
    assert path.is_file(), f'the contract source is missing: {path}'
    return path.read_text(encoding='utf-8')


def _between(text: str, start_marker: str, end_marker: str, source: str) -> str:
    start = text.find(start_marker)
    assert start != -1, f'{source}: the paragraph {start_marker!r} was not found'
    tail = text[start + len(start_marker) :]
    end = tail.find(end_marker)
    assert end != -1, f'{source}: the paragraph {start_marker!r} has no closing marker {end_marker!r}'
    return tail[:end]


def _false_claim_paragraph(text: str) -> str:
    return _between(text, _PARAGRAPH_START, _PARAGRAPH_END, 'analyze.md Step 4')


def _normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', text.replace('**', '').replace('`', '')).strip()


def _exemption_markers(text: str) -> list[str]:
    """Every post-merge-exemption marker the paragraph carries."""
    normalized = _normalized(text)
    return [marker for marker in _EXEMPTION_MARKERS if marker in normalized]


def _live_state_markers(text: str) -> list[str]:
    """Every live-PR-state marker the paragraph carries."""
    normalized = _normalized(text)
    return [marker for marker in _LIVE_STATE_MARKERS if marker in normalized]


def _names_the_provider_read(text: str) -> bool:
    normalized = _normalized(text)
    return any(marker in normalized for marker in _PROVIDER_READ_MARKERS)


def _carries_stale_parser_clause(text: str) -> bool:
    return _STALE_PARSER_CLAUSE in text


#: Every metric the false-claim paragraph compares, with the semantics its own
#: standard row must state. Per metric, never one combined substring: a single
#: head-bound row would otherwise satisfy the check for all four.
_STANDARD_METRICS: tuple[tuple[str, str], ...] = (
    ('unresolved_review_threads', 'on the head'),
    ('review_body_findings_total', 'on the head'),
    ('review_body_findings_handled', 'carry a disposition'),
    ('sonar_open_new_issues', 'merge head'),
)


def _standard_rows(text: str, metric: str) -> list[str]:
    """Every standard row that defines ``metric`` — one in the key table, plus the
    Sonar section's own table where that metric has a second carrier."""
    rows = [line for line in text.splitlines() if line.startswith(f'| `{metric}`')]
    assert rows, f'landing-payload-spec.md carries no `{metric}` row'
    return rows


def _review_read_block(script: str) -> str:
    """The review gate's own data-read function, from its ``def`` to the next one."""
    start = script.find(_REVIEW_READ_FUNCTION)
    assert start != -1, f'runbook_lane.py carries no {_REVIEW_READ_FUNCTION!r} — the parser pin cannot be read'
    tail = script[start:]
    end = tail.find('\ndef ', 1)
    return tail[: end if end != -1 else len(tail)]


def _reads_the_provider_in_process(block: str) -> bool:
    return _IN_PROCESS_FETCH in block and _SUBPROCESS_MARKER not in block


def _shells_out_to_the_comments_subcommand(block: str) -> bool:
    return _CI_SUBCOMMAND_LITERAL in block


# =============================================================================
# (D1) The paragraph is head-bound again, with no post-merge exemption
# =============================================================================


class TestFalseClaimIsHeadBound:
    def test_the_paragraph_reads_the_numbers_on_the_merged_head(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))

        assert _HEAD_BOUND_MARKER in _normalized(paragraph), (
            'the false-claim paragraph no longer reads the review numbers on the merged head — a '
            're-read against the live PR cannot be compared with a claim defined at the head'
        )

    def test_the_paragraph_carries_no_post_merge_exemption(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))

        offenders = _exemption_markers(paragraph)
        assert offenders == [], (
            f'the false-claim paragraph exempts a difference {offenders} from being a false claim — the '
            're-read reports counts, not timestamps, so the drain cannot decide that exemption, and the '
            'paragraph still calls a difference a false claim in its next sentence'
        )

    def test_the_paragraph_scopes_the_re_read_to_the_head_not_the_live_pr(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))

        offenders = _live_state_markers(paragraph)
        assert offenders == [], (
            f'the false-claim paragraph scopes the re-read to {offenders}, contradicting the head-bound '
            'definition its own standard carries'
        )

    def test_a_planted_live_state_wording_is_detected(self, tmp_path):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))
        fixture = tmp_path / 'live-state.md'
        fixture.write_text(
            paragraph.replace('on the merged head', "against the PR's current state"),
            encoding='utf-8',
        )

        assert _live_state_markers(_read(fixture)), 'a live-PR-state scope must be reported'

    def test_a_planted_post_merge_exemption_is_detected(self, tmp_path):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))
        fixture = tmp_path / 'exemption.md'
        fixture.write_text(
            f'{paragraph} A difference caused by activity after the merge is not a false claim.\n',
            encoding='utf-8',
        )

        assert _exemption_markers(_read(fixture)), 'a post-merge exemption must be reported'

    def test_the_unmodified_paragraph_is_clean_under_both_detectors(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))

        assert _live_state_markers(paragraph) == []
        assert _exemption_markers(paragraph) == []


# =============================================================================
# (D1) The paragraph and the landing standard define the values the same way
# =============================================================================


class TestTheStandardAgrees:
    def test_the_standard_defines_the_numbers_as_the_merge_gates_read_on_the_head(self):
        spec = _read(_LANDING_SPEC)

        for metric, phrase in _STANDARD_METRICS:
            for row in _standard_rows(spec, metric):
                assert phrase in row, (
                    f'the `{metric}` row no longer states {phrase!r} — the analyze paragraph would be '
                    f'head-bound against a standard that says something else. Row read: {row!r}'
                )

    def test_a_row_redefined_on_the_live_pr_state_is_detected(self, tmp_path):
        spec = _read(_LANDING_SPEC)
        fixture = tmp_path / 'live-state-spec.md'
        fixture.write_text(
            spec.replace('the merge gate read on the head', "the merge gate read against the PR's current state", 1),
            encoding='utf-8',
        )

        offenders = [
            metric
            for metric, phrase in _STANDARD_METRICS
            if not all(phrase in row for row in _standard_rows(_read(fixture), metric))
        ]

        assert 'unresolved_review_threads' in offenders, 'a row scoped to the live PR state must be reported'


# =============================================================================
# (D1) The parser clause names the provider read, not a stale CI subcommand
# =============================================================================


class TestTheParserClause:
    def test_the_paragraph_names_the_provider_read_instead_of_the_stale_subcommand(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))

        assert not _carries_stale_parser_clause(paragraph), (
            f'the paragraph still says the numbers come from `{_STALE_PARSER_CLAUSE}` — review-gate '
            'fetches the provider data itself, in-process'
        )
        assert _names_the_provider_read(paragraph), (
            "the paragraph does not name the provider's own single read as the parser's source"
        )

    def test_a_planted_stale_subcommand_is_detected(self, tmp_path):
        section = _false_claim_paragraph(_read(_ANALYZE_MD))
        planted = section
        for marker in _PROVIDER_READ_MARKERS:
            planted = planted.replace(marker, f'`{_STALE_PARSER_CLAUSE}`')
        fixture = tmp_path / 'stale.md'
        fixture.write_text(planted, encoding='utf-8')

        read_back = _read(fixture)

        assert _carries_stale_parser_clause(read_back), 'a stale subcommand clause must be reported'
        assert not _names_the_provider_read(read_back), (
            'the provider-read detector must stop firing when the phrase is gone'
        )

    def test_the_review_gate_reads_the_provider_in_process(self):
        block = _review_read_block(_read(_REVIEW_GATE_SCRIPT))

        assert _reads_the_provider_in_process(block), (
            'review-gate no longer fetches the provider comment data in-process — the analyze '
            "paragraph's parser clause and the script have drifted apart"
        )
        assert not _shells_out_to_the_comments_subcommand(block), (
            'review-gate shells out to a `pr comments` call, so the paragraph correction would be wrong'
        )

    def test_a_planted_subprocess_read_is_detected(self, tmp_path):
        block = _review_read_block(_read(_REVIEW_GATE_SCRIPT))
        shelled = tmp_path / 'shelled-out.py'
        shelled.write_text(block.replace(_IN_PROCESS_FETCH, "run_ci('pr comments')"), encoding='utf-8')
        subprocess_use = tmp_path / 'subprocess-use.py'
        subprocess_use.write_text(
            block.replace('    try:\n', "    subprocess.run(['gh', 'api'])\n\n    try:\n", 1),
            encoding='utf-8',
        )

        assert not _reads_the_provider_in_process(_read(shelled)), 'a shelled-out read must not read as in-process'
        assert _shells_out_to_the_comments_subcommand(_read(shelled)), 'a carved command list must be reported'
        assert not _reads_the_provider_in_process(_read(subprocess_use)), 'a subprocess call must be reported'
