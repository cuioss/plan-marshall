# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java-cui:parse-rewrite-log domain-owned log-line parser.

Every WARN literal these tests assert against is DERIVED from the checked-in
provenance corpus (``fixtures/warn-corpus/rewrite-run-warnings.log``), never
hand-written. The corpus carries the upstream ``cui-open-rewrite`` #118 WARN
templates filled with the upstream test's asserted fixture values — see
``fixtures/warn-corpus/PROVENANCE.md``.

The derivation deliberately does NOT reuse ``FINDING_PATTERN`` (the regex under
test): it re-extracts each field with an independent string walk, so a
regression in ``FINDING_PATTERN`` cannot silently rewrite the expectations.
"""

import tempfile
from pathlib import Path
from types import SimpleNamespace

from conftest import load_script_module

_parse_rewrite_log = load_script_module('pm-dev-java-cui', 'parse-rewrite-log', 'parse_rewrite_log.py')

parse_rewrite_log = _parse_rewrite_log.parse_rewrite_log
parse_rewrite_log_file = _parse_rewrite_log.parse_rewrite_log_file
parse_finding_line = _parse_rewrite_log.parse_finding_line
cmd_parse = _parse_rewrite_log.cmd_parse
FINDING_PATTERN = _parse_rewrite_log.FINDING_PATTERN
RECIPE_LOG_PREFIX = _parse_rewrite_log.RECIPE_LOG_PREFIX

FIXTURE_DIR = Path(__file__).resolve().parent / 'fixtures' / 'warn-corpus'
FIXTURE_CORPUS = FIXTURE_DIR / 'rewrite-run-warnings.log'
FIXTURE_PROVENANCE = FIXTURE_DIR / 'PROVENANCE.md'

#: The literal prefix token the recipe emits, e.g. ``CUI_REWRITE-``.
PREFIX_TOKEN = f'{RECIPE_LOG_PREFIX}-'


def _independent_fields(line: str) -> dict:
    """Re-extract a finding's fields from a raw line by an independent string walk.

    Implemented WITHOUT ``FINDING_PATTERN`` so the expectations stay independent
    of the module under test. Locates the ``CUI_REWRITE-<id>: `` prefix as a
    substring (so a leading log layout is tolerated), then peels the fixed
    separators (`` at ``, ``:line:column``, `` by ``, `` : ``).
    """
    start = line.index(PREFIX_TOKEN)
    identifier = line[start + len(PREFIX_TOKEN): start + len(PREFIX_TOKEN) + 3]
    body = line[start:].split(': ', 1)[1]  # drop "CUI_REWRITE-<id>"
    after_at = body.split(' at ', 1)[1]  # "<path>:<line>:<col> by <recipe>: <message>"
    locator, after_by = after_at.split(' by ', 1)
    recipe, message = after_by.split(': ', 1)
    path, line_no, column = locator.rsplit(':', 2)
    return {
        'identifier': identifier,
        'path': path,
        'line': int(line_no),
        'column': int(column),
        'recipe': recipe,
        'message': message,
    }


def _corpus_text() -> str:
    return FIXTURE_CORPUS.read_text(encoding='utf-8')


def _corpus_finding_lines() -> list[str]:
    """Corpus lines that carry a finding, selected independently of the parser."""
    return [line for line in _corpus_text().splitlines() if PREFIX_TOKEN in line]


class TestCorpusDerivation:
    """Guards on the independently-derived corpus facts the rest of the module builds on."""

    def test_corpus_has_finding_lines(self):
        assert len(_corpus_finding_lines()) > 0

    def test_corpus_covers_both_classifications(self):
        identifiers = {_independent_fields(line)['identifier'] for line in _corpus_finding_lines()}
        assert '100' in identifiers
        assert '101' in identifiers

    def test_corpus_has_a_layout_prefixed_line(self):
        # At least one finding line does NOT start at the CUI_REWRITE prefix,
        # proving the substring (non-line-anchored) match requirement.
        assert any(line.index(PREFIX_TOKEN) > 0 for line in _corpus_finding_lines())

    def test_corpus_has_a_message_with_internal_separator(self):
        # At least one finding message contains ": ", proving greedy capture.
        assert any(': ' in _independent_fields(line)['message'] for line in _corpus_finding_lines())


class TestFieldExtraction:
    """Field extraction against the provenance corpus."""

    def test_total_findings_matches_corpus(self):
        result = parse_rewrite_log(_corpus_text())
        assert result['status'] == 'success'
        assert result['data']['total_findings'] == len(_corpus_finding_lines())

    def test_non_finding_lines_are_ignored(self):
        # The corpus carries [INFO]/BUILD lines that must never become findings.
        total_lines = len(_corpus_text().splitlines())
        assert total_lines > len(_corpus_finding_lines())

    def test_each_finding_matches_independent_extraction(self):
        findings = parse_rewrite_log(_corpus_text())['data']['findings']
        expected = [_independent_fields(line) for line in _corpus_finding_lines()]
        assert len(findings) == len(expected)
        for got, want in zip(findings, expected, strict=True):
            assert got['path'] == want['path']
            assert got['line'] == want['line']
            assert got['column'] == want['column']
            assert got['recipe'] == want['recipe']
            assert got['message'] == want['message']
            assert got['identifier'] == want['identifier']


class TestClassification:
    """Newly-detected vs pre-existing classification, keyed off the identifier."""

    def test_classification_counts_match_corpus(self):
        expected = [_independent_fields(line)['identifier'] for line in _corpus_finding_lines()]
        data = parse_rewrite_log(_corpus_text())['data']
        assert data['newly_detected_count'] == expected.count('100')
        assert data['pre_existing_count'] == expected.count('101')

    def test_identifier_100_is_newly_detected(self):
        findings = parse_rewrite_log(_corpus_text())['data']['findings']
        for finding in findings:
            if finding['identifier'] == '100':
                assert finding['classification'] == 'newly_detected'

    def test_identifier_101_is_pre_existing(self):
        findings = parse_rewrite_log(_corpus_text())['data']['findings']
        for finding in findings:
            if finding['identifier'] == '101':
                assert finding['classification'] == 'pre_existing'


class TestGreedyMessageCapture:
    """The message field is captured greedily to end-of-line, including internal ': '."""

    def test_message_with_internal_separator_is_not_truncated(self):
        findings = parse_rewrite_log(_corpus_text())['data']['findings']
        for line in _corpus_finding_lines():
            want = _independent_fields(line)
            if ': ' not in want['message']:
                continue
            match = next(f for f in findings if f['raw_line'] == line)
            assert match['message'] == want['message']
            assert ': ' in match['message']


class TestCrlfRobustness:
    """CRLF-terminated logs must not leave a trailing '\\r' in the greedy message capture."""

    def test_crlf_terminated_line_message_has_no_trailing_cr(self):
        # Build a CRLF corpus from the provenance finding lines; the greedy
        # end-of-line message group must not swallow the '\r'.
        crlf_text = '\r\n'.join(_corpus_finding_lines()) + '\r\n'
        findings = parse_rewrite_log(crlf_text)['data']['findings']

        assert findings, 'CRLF corpus must still yield findings'
        for finding in findings:
            assert not finding['message'].endswith('\r'), (
                f"message retained a trailing CR: {finding['message']!r}"
            )

    def test_crlf_and_lf_yield_identical_findings(self):
        # The same corpus lines under CRLF and LF must parse to the same messages.
        lines = _corpus_finding_lines()
        lf_findings = parse_rewrite_log('\n'.join(lines) + '\n')['data']['findings']
        crlf_findings = parse_rewrite_log('\r\n'.join(lines) + '\r\n')['data']['findings']

        assert [f['message'] for f in crlf_findings] == [f['message'] for f in lf_findings]


class TestSubstringMatch:
    """The prefix is matched as a substring anywhere in the line, never anchored at ^."""

    def test_layout_prefixed_line_still_parses(self):
        for line in _corpus_finding_lines():
            if line.index(PREFIX_TOKEN) == 0:
                continue
            finding = parse_finding_line(line)
            assert finding is not None
            assert finding['raw_line'] == line


class TestFormatDriftRegression:
    """Regression tests that fail loudly if the upstream #118 WARN shape drifts."""

    def test_every_corpus_finding_line_matches_the_parser(self):
        # If FINDING_PATTERN drifts away from the pinned corpus, this fails
        # rather than the parser silently reporting no findings.
        for line in _corpus_finding_lines():
            assert parse_finding_line(line) is not None, f'Corpus line no longer matched: {line}'

    def test_altered_prefix_no_longer_matches(self):
        line = _corpus_finding_lines()[0]
        drifted = line.replace(RECIPE_LOG_PREFIX, 'CUI_LEGACY')
        assert parse_finding_line(drifted) is None

    def test_altered_identifier_out_of_range_no_longer_matches(self):
        line = next(line for line in _corpus_finding_lines() if f'{PREFIX_TOKEN}100' in line)
        drifted = line.replace(f'{PREFIX_TOKEN}100', f'{PREFIX_TOKEN}102')
        assert parse_finding_line(drifted) is None

    def test_altered_template_verb_no_longer_matches(self):
        line = next(line for line in _corpus_finding_lines() if 'Finding detected at' in line)
        drifted = line.replace('Finding detected at', 'Finding located near')
        assert parse_finding_line(drifted) is None


class TestExitCodeContract:
    """cmd_parse exit-code contract: 0 = parsed, no finding; 1 = finding(s) or error."""

    @staticmethod
    def _run(log_file: str) -> int:
        args = SimpleNamespace(log_file=log_file, format='json')
        return int(cmd_parse(args))

    def test_corpus_with_findings_exits_non_zero(self):
        assert self._run(str(FIXTURE_CORPUS)) == 1

    def test_finding_free_log_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'clean.log'
            log.write_text('[INFO] BUILD SUCCESS\n[INFO] No recipes matched.\n')
            assert self._run(str(log)) == 0

    def test_missing_log_exits_non_zero(self):
        assert self._run('/nonexistent/path/does/not/exist.log') == 1


class TestParseFileErrors:
    """Error payloads from parse_rewrite_log_file."""

    def test_missing_file_returns_error(self):
        result = parse_rewrite_log_file('/nonexistent/path/does/not/exist.log')
        assert result['status'] == 'error'
        assert result['error'] == 'log_not_found'

    def test_empty_log_returns_zero_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'empty.log'
            log.write_text('')
            result = parse_rewrite_log_file(str(log))
            assert result['status'] == 'success'
            assert result['data']['total_findings'] == 0


class TestProvenanceDocument:
    """The provenance document records every required field."""

    def test_provenance_records_required_fields(self):
        provenance = FIXTURE_PROVENANCE.read_text(encoding='utf-8')
        assert 'cuioss/cui-open-rewrite' in provenance
        assert '#118' in provenance
        assert 'a0e21ac536460c841b2135ace15a6578ff481021' in provenance
        assert 'RecipeLogMessages.java' in provenance
        assert 'RecipeMarkerUtil' in provenance
        assert 'CUI_REWRITE' in provenance

    def test_provenance_names_the_format_drift_expectation(self):
        provenance = FIXTURE_PROVENANCE.read_text(encoding='utf-8').lower()
        assert 'drift' in provenance
