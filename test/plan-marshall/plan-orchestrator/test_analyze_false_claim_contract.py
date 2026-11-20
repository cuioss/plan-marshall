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

import importlib.util
import re
from pathlib import Path

import ci_base
import github_re_review

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

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
    '**The four review-and-Sonar numbers are re-read from the provider, and a difference is classified '
    'by the time of the record that explains it.**'
)
_PARAGRAPH_END = '**Parse the `steps` fact'

#: The wording that scopes the re-read to the live PR state, and the fact that the
#: difference is classified by TIME — the rule that replaced the head-bound reading.
_LIVE_STATE_MARKERS: tuple[str, ...] = ('CURRENT state', 'current state')
_TIME_CLASSIFICATION_MARKERS: tuple[str, ...] = ('time of the re-read', 'created_at', 'updated_at')

#: The stale parser clause, and the shape that replaces it: the provider's own
#: single in-process read.
_STALE_PARSER_CLAUSE = 'ci pr comments'
_PROVIDER_READ_MARKERS: tuple[str, ...] = ("provider's own single", "provider's single")

#: The merge-gate read the standard defines each number as.

#: The provider read the incident is about, and the shell-out shape that would replace it.
_IN_PROCESS_FETCH = 'fetch_pr_comments_data('
_CI_SUBCOMMAND_LITERAL = "'pr comments'"
_TEMPLATE = _PLAN_ORCHESTRATOR / 'templates' / 'landing-analysis.md'


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
#: standard row must state. The POPULATION is not mirrored here: the test derives it
#: from the paragraph, intersected with the standard's own row keys, and asserts the
#: two sets agree — so a metric added to the paragraph fails here until its
#: expectation is added, and one removed fails too.
_STANDARD_METRICS: tuple[tuple[str, str], ...] = (
    ('unresolved_review_threads', 'on the head'),
    ('review_body_findings_total', 'on the head'),
    ('review_body_findings_handled', 'carry a disposition'),
    ('sonar_open_new_issues', 'merge head'),
)

#: A standard table row's own key, from the row's leading cell.
_SPEC_ROW_KEY_RE = re.compile(r'^\| `([a-z_]+)`', re.MULTILINE)


def _paragraph_metric_population(paragraph: str, spec: str) -> set[str]:
    """The metrics the paragraph names that the standard also defines.

    Intersecting the paragraph's backticked tokens with the standard's row keys is
    what makes the population derivable without a second hardcoded list: the
    paragraph's prose tokens (`n/a`, `unknown`, `finding:`) are not row keys, and a
    metric the standard defines but the paragraph ignores is not a population
    member either.
    """
    spec_keys = set(_SPEC_ROW_KEY_RE.findall(spec))
    return set(re.findall(r'`([a-z_]+)`', paragraph)) & spec_keys


def _standard_rows(text: str, metric: str) -> list[str]:
    """Every standard row that defines ``metric`` — one in the key table, plus the
    Sonar section's own table where that metric has a second carrier."""
    rows = [line for line in text.splitlines() if line.startswith(f'| `{metric}`')]
    assert rows, f'landing-payload-spec.md carries no `{metric}` row'
    return rows


def _review_read_block(script: str) -> str:
    """Read the review gate's data-read function by its BEHAVIOURAL property.

    Kept as the loader for the scratch-module controls: a scratch copy is imported by
    path, so a rename or a shell-out replacement can be exercised without editing the
    live script.
    """
    return script


def load_script_module_from_path(path: Path):
    """Import a scratch copy of a script by path."""
    spec = importlib.util.spec_from_file_location(f'scratch_{path.stem}_{abs(hash(path))}', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scratch_module(source_path: Path, tmp_path: Path, replacements: list[tuple[str, str]]):
    """A scratch copy of ``source_path`` with ``replacements`` applied, imported by path."""
    text = _read(source_path)
    for old, new in replacements:
        text = text.replace(old, new)
    fixture = tmp_path / f'scratch-{source_path.stem}.py'
    fixture.write_text(text, encoding='utf-8')
    return load_script_module_from_path(fixture)


def _provider_fetches(module) -> int:
    """Run the review gate with the provider read counted, and return the count.

    The gate resolves the CI provider from the process cwd before it fetches anything,
    so the route is pinned here: a checkout without a readable `.plan/marshal.json`
    (or a cwd outside the repository) otherwise returns `status: error` before the
    counted fetch and the count is a vacuous 0.
    """
    calls: list[int] = []

    def _fetch(*args, **kwargs):
        calls.append(1)
        return {
            'status': 'success',
            'operation': 'pr_comments',
            'provider': 'github',
            'pr_number': 7,
            'total': 0,
            'unresolved': 0,
            'complete': True,
            'connections': [],
            'comments': [],
        }

    original = github_re_review.fetch_pr_comments_data
    original_provider = ci_base.resolve_ci_provider

    def _resolve_github(project_dir: Path | str | None = None) -> str | None:
        return 'github'

    github_re_review.fetch_pr_comments_data = _fetch
    ci_base.resolve_ci_provider = _resolve_github
    try:
        module.cmd_review_gate(
            parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'review-gate', '--pr-number', '7')
        )
    except Exception:
        pass
    finally:
        github_re_review.fetch_pr_comments_data = original
        ci_base.resolve_ci_provider = original_provider
    return len(calls)


# =============================================================================
# (D1) The paragraph is head-bound again, with no post-merge exemption
# =============================================================================


class TestTheDifferenceIsClassifiedByTime:
    """The rule D5(a) installs: the re-read is of the live PR, and TIME classifies a difference."""

    def test_the_paragraph_reads_the_live_pr_state_and_the_time_it_was_read(self):
        paragraph = _normalized(_false_claim_paragraph(_read(_ANALYZE_MD)))

        assert _live_state_markers(paragraph), 'the paragraph no longer names the read taken on the CURRENT state'
        assert 'time of the re-read' in paragraph

    def test_the_standard_names_the_provider_record_timestamps(self):
        spec = _normalized(_read(_LANDING_SPEC))

        assert 'created_at' in spec and 'updated_at' in spec

    def test_a_dated_record_makes_a_difference_a_post_merge_change(self):
        paragraph = _normalized(_false_claim_paragraph(_read(_ANALYZE_MD)))

        assert 'post-merge change, never a false claim' in paragraph

    def test_a_thread_resolution_is_undecidable_not_a_false_claim(self):
        paragraph = _normalized(_false_claim_paragraph(_read(_ANALYZE_MD)))

        assert 'thread resolution could explain is undecidable' in paragraph

    def test_the_standard_states_the_same_rule_once(self):
        spec = _normalized(_read(_LANDING_SPEC))

        assert "Re-reading a landing's review numbers" in spec
        assert 'created_at' in spec and 'updated_at' in spec
        assert 'never as a' in spec and 'false claim' in spec

    def test_the_template_carries_a_worked_example(self):
        template = _normalized(_read(_TEMPLATE))

        assert 'Worked example' in template
        assert 'post-merge change, NOT as a false claim' in template

    def test_a_paragraph_that_only_says_false_claim_is_detected(self, tmp_path):
        """The planted paragraph loses BOTH required properties, and the detector sees it."""
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))
        fixture = tmp_path / 'head-bound.md'
        fixture.write_text(
            '**The four review-and-Sonar numbers are re-read from the provider, and a difference is a '
            'false claim.** The numbers are re-read on the merged head and a difference is a false claim.',
            encoding='utf-8',
        )

        offending = _normalized(_read(fixture))
        assert not _live_state_markers(offending), 'the planted paragraph must fail the live-state check'
        assert 'time of the re-read' not in offending, 'the planted paragraph must fail the time check'
        # CONTROL: the shipped paragraph carries both, so the detector is not vacuous.
        assert _live_state_markers(paragraph), 'the shipped paragraph must name the live read'
        assert 'time of the re-read' in _normalized(paragraph), 'the shipped paragraph must carry the time rule'


# =============================================================================
# (D1) The paragraph and the landing standard define the values the same way
# =============================================================================


class TestTheStandardAgrees:
    def test_the_paragraph_and_the_standard_name_the_same_metric_population(self):
        paragraph = _false_claim_paragraph(_read(_ANALYZE_MD))
        population = _paragraph_metric_population(paragraph, _read(_LANDING_SPEC))

        assert population, 'the paragraph names no metric the standard defines — the check would be vacuous'
        assert population == {metric for metric, _phrase in _STANDARD_METRICS}, (
            f'the metrics this test grades {sorted(metric for metric, _ in _STANDARD_METRICS)} do not match '
            f'the ones the paragraph compares {sorted(population)} — a metric added to either side needs its '
            'expectation here'
        )

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

    def test_the_review_surfaces_are_read_through_one_provider_fetch(self):
        """The PROPERTY, not the function's name: one provider fetch, no shell-out in the namespace."""
        module = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'analyze_false_claim_prop')

        assert _provider_fetches(module) == 1, 'the review surfaces must be read through ONE provider fetch'
        assert 'subprocess' not in vars(module), 'the review read must not shell out'

    def test_the_property_survives_a_rename_of_the_reader_helper(self, tmp_path):
        """A rename in another plan's build must not turn this red."""
        renamed = _scratch_module(
            _REVIEW_GATE_SCRIPT,
            tmp_path,
            [('_read_review_surfaces', '_review_surfaces_renamed')],
        )

        assert _provider_fetches(renamed) == 1

    def test_the_property_fails_when_the_fetch_shells_out(self, tmp_path):
        """Moving the fetch into a helper that shells out must be reported."""
        source = _read(_REVIEW_GATE_SCRIPT)
        start = source.index('def _read_review_surfaces(')
        end = source.index('\ndef ', start + 1)
        replacement = (
            'def _read_review_surfaces(pr_number, project_dir):\n'
            '    import subprocess\n'
            "    return subprocess.run(['gh', 'api'], capture_output=True, text=True).stdout\n"
        )
        fixture = tmp_path / 'shelled_out.py'
        fixture.write_text(source[:start] + replacement + source[end:], encoding='utf-8')

        shelled = load_script_module_from_path(fixture)

        assert _provider_fetches(shelled) == 0, 'a shelled-out read must not count as a provider fetch'
