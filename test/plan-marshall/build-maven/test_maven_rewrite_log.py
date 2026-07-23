#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the additive OpenRewrite log-parse consumption (_maven_cmd_rewrite_log).

Covers the three fail-closed verdicts of the build-maven Signal B consumer:
- ``observed``       — the build reached rewrite:run and the verb resolves.
- ``not_observed``   — the build never reached rewrite:run (never a false clean).
- ``domain_inactive``— the verb resolves to null (never a false clean).

The observed fixture's #118 WARN lines are copied verbatim from deliverable 1's
provenance corpus — the SINGLE format source of truth — and a cross-check test
pins that identity so the two never drift.
"""

from pathlib import Path

from conftest import load_script_module

_rewrite_log = load_script_module(
    'plan-marshall', 'build-maven', '_maven_cmd_rewrite_log.py', '_maven_cmd_rewrite_log'
)

reached_rewrite_run = _rewrite_log.reached_rewrite_run
consume_rewrite_log = _rewrite_log.consume_rewrite_log
resolve_domain_verb = _rewrite_log.resolve_domain_verb
VERDICT_OBSERVED = _rewrite_log.VERDICT_OBSERVED
VERDICT_NOT_OBSERVED = _rewrite_log.VERDICT_NOT_OBSERVED
VERDICT_DOMAIN_INACTIVE = _rewrite_log.VERDICT_DOMAIN_INACTIVE

# The domain-owned parser (deliverable 1) — imported here only to drive the
# observed-case dispatch against the fixture without the executor subprocess.
_parser = load_script_module(
    'pm-dev-java-cui', 'parse-rewrite-log', 'parse_rewrite_log.py', 'parse_rewrite_log'
)

TEST_DATA_DIR = Path(__file__).parent / 'fixtures' / 'log-test-data'
OBSERVED_LOG = TEST_DATA_DIR / 'rewrite-run-observed.log'
NOT_OBSERVED_LOG = TEST_DATA_DIR / 'rewrite-run-not-observed.log'
DRYRUN_ADVISORY_LOG = TEST_DATA_DIR / 'rewrite-run-dryrun-advisory.log'

#: Deliverable 1's provenance corpus — the single format source of truth for the
#: #118 WARN lines. parents[2] is the test/ root.
D1_CORPUS = (
    Path(__file__).resolve().parents[2]
    / 'pm-dev-java-cui'
    / 'parse-rewrite-log'
    / 'fixtures'
    / 'warn-corpus'
    / 'rewrite-run-warnings.log'
)

_PREFIX_TOKEN = 'CUI_REWRITE-'


def _corpus_finding_lines(path: Path) -> list[str]:
    """Return the lines of ``path`` that carry a #118 WARN finding."""
    return [line for line in path.read_text(encoding='utf-8').splitlines() if _PREFIX_TOKEN in line]


def _real_dispatch(notation: str, log_file: str) -> dict:
    """Dispatch stand-in that runs the real domain parser directly against the log.

    Avoids the executor subprocess while still exercising the genuine parser, so
    the observed-case assertions rest on real #118 parsing, not a canned payload.
    """
    return dict(_parser.parse_rewrite_log_file(log_file))


def _exploding_resolver():
    raise AssertionError('resolve_verb must not be called when rewrite:run was not reached')


def _exploding_dispatch(notation: str, log_file: str) -> dict:
    raise AssertionError('dispatch must not be called on a domain-inactive resolution')


class TestReachedRewriteRun:
    """The rewrite:run boundary detector."""

    def test_observed_log_reached_rewrite_run(self):
        assert reached_rewrite_run(OBSERVED_LOG.read_text(encoding='utf-8')) is True

    def test_not_observed_log_did_not_reach_rewrite_run(self):
        assert reached_rewrite_run(NOT_OBSERVED_LOG.read_text(encoding='utf-8')) is False

    def test_short_prefix_banner_form_matches(self):
        # The older/prefix banner form ``--- rewrite:run (default-cli) @ app ---``.
        assert reached_rewrite_run('[INFO] --- rewrite:run (default-cli) @ my-app ---') is True

    def test_unrelated_log_does_not_match(self):
        assert reached_rewrite_run('[INFO] --- maven-compiler-plugin:3.11.0:compile ---') is False

    def test_dryrun_advisory_prose_does_not_match(self):
        # OpenRewrite dryRun mode emits advisory prose carrying the literal
        # ``rewrite:run`` but no goal-execution banner — it must NOT be mistaken
        # for a real run (ADR-009 fail-closed).
        assert reached_rewrite_run("[INFO] Run 'mvn rewrite:run' to apply the fixes.") is False
        assert reached_rewrite_run('[INFO] ...or run `mvn rewrite:run` again.') is False

    def test_dryrun_advisory_fixture_did_not_reach_rewrite_run(self):
        assert reached_rewrite_run(DRYRUN_ADVISORY_LOG.read_text(encoding='utf-8')) is False


class TestObservedVerdict:
    """A build that reached rewrite:run with an active domain yields structured findings."""

    def test_observed_yields_structured_findings(self):
        result = consume_rewrite_log(
            str(OBSERVED_LOG),
            resolve_verb=lambda: 'pm-dev-java-cui:parse-rewrite-log',
            dispatch=_real_dispatch,
        )
        rewrite_log = result['rewrite_log']
        assert rewrite_log['verdict'] == VERDICT_OBSERVED
        assert rewrite_log['total_findings'] == len(_corpus_finding_lines(OBSERVED_LOG))
        assert rewrite_log['total_findings'] > 0

    def test_observed_findings_carry_all_fields(self):
        result = consume_rewrite_log(
            str(OBSERVED_LOG),
            resolve_verb=lambda: 'pm-dev-java-cui:parse-rewrite-log',
            dispatch=_real_dispatch,
        )
        for finding in result['rewrite_log']['findings']:
            assert set(finding.keys()) >= {'path', 'line', 'column', 'recipe', 'message', 'classification'}

    def test_observed_classifies_newly_detected_and_pre_existing(self):
        result = consume_rewrite_log(
            str(OBSERVED_LOG),
            resolve_verb=lambda: 'pm-dev-java-cui:parse-rewrite-log',
            dispatch=_real_dispatch,
        )
        rewrite_log = result['rewrite_log']
        assert rewrite_log['newly_detected_count'] > 0
        assert rewrite_log['pre_existing_count'] > 0


class TestNotObservedVerdict:
    """A build that never reached rewrite:run yields not_observed — never a false clean."""

    def test_not_observed_verdict(self):
        result = consume_rewrite_log(str(NOT_OBSERVED_LOG), resolve_verb=_exploding_resolver)
        rewrite_log = result['rewrite_log']
        assert rewrite_log['verdict'] == VERDICT_NOT_OBSERVED

    def test_not_observed_is_never_clean(self):
        result = consume_rewrite_log(str(NOT_OBSERVED_LOG), resolve_verb=_exploding_resolver)
        rewrite_log = result['rewrite_log']
        # The verdict is an explicit third state, not a vacuous positive.
        assert rewrite_log['verdict'] != 'clean'
        assert rewrite_log['total_findings'] == 0
        assert rewrite_log['findings'] == []

    def test_not_observed_short_circuits_before_resolution(self):
        # _exploding_resolver raises if called; reaching here proves the
        # not-reached branch short-circuits before verb resolution.
        consume_rewrite_log(str(NOT_OBSERVED_LOG), resolve_verb=_exploding_resolver)

    def test_dryrun_advisory_yields_not_observed(self):
        # A dryRun-only build never executed the run goal: the advisory prose
        # carrying ``rewrite:run`` must not flip the verdict to observed.
        result = consume_rewrite_log(str(DRYRUN_ADVISORY_LOG), resolve_verb=_exploding_resolver)
        rewrite_log = result['rewrite_log']
        assert rewrite_log['verdict'] == VERDICT_NOT_OBSERVED
        assert rewrite_log['verdict'] != VERDICT_OBSERVED
        assert rewrite_log['total_findings'] == 0
        assert rewrite_log['findings'] == []


class TestDomainInactiveVerdict:
    """A null verb resolution yields domain_inactive — a first-class skip, never a false clean."""

    def test_domain_inactive_verdict(self):
        result = consume_rewrite_log(
            str(OBSERVED_LOG),
            resolve_verb=lambda: None,
            dispatch=_exploding_dispatch,
        )
        rewrite_log = result['rewrite_log']
        assert rewrite_log['verdict'] == VERDICT_DOMAIN_INACTIVE

    def test_domain_inactive_is_never_clean(self):
        result = consume_rewrite_log(
            str(OBSERVED_LOG),
            resolve_verb=lambda: None,
            dispatch=_exploding_dispatch,
        )
        rewrite_log = result['rewrite_log']
        assert rewrite_log['verdict'] != 'clean'
        assert rewrite_log['total_findings'] == 0
        assert rewrite_log['findings'] == []

    def test_domain_inactive_does_not_dispatch_the_parser(self):
        # _exploding_dispatch raises if called; reaching here proves no dispatch
        # happens on a null-on-absent resolution.
        consume_rewrite_log(str(OBSERVED_LOG), resolve_verb=lambda: None, dispatch=_exploding_dispatch)


class TestSingleFormatSourceOfTruth:
    """The observed fixture's WARN lines are the D1 provenance corpus, verbatim."""

    def test_observed_fixture_carries_every_corpus_finding_line(self):
        observed_text = OBSERVED_LOG.read_text(encoding='utf-8')
        corpus_lines = _corpus_finding_lines(D1_CORPUS)
        assert corpus_lines, 'D1 corpus must carry finding lines'
        for line in corpus_lines:
            assert line in observed_text, f'Corpus WARN line missing from observed fixture: {line}'

    def test_observed_fixture_finding_count_matches_corpus(self):
        assert len(_corpus_finding_lines(OBSERVED_LOG)) == len(_corpus_finding_lines(D1_CORPUS))


class TestResolveDomainVerb:
    """Null-on-absent resolution of the verb across configured domains."""

    def test_resolves_notation_when_a_domain_declares_the_verb(self, monkeypatch, tmp_path):
        import file_ops

        marshal = tmp_path / 'marshal.json'
        marshal.write_text(
            '{"skill_domains": {"java-cui": {"bundle": "pm-dev-java-cui", '
            '"workflow_skill_extensions": {"rewrite-log-parse": "pm-dev-java-cui:parse-rewrite-log"}}}}'
        )
        monkeypatch.setattr(file_ops, 'get_marshal_path', lambda: marshal)

        assert resolve_domain_verb() == 'pm-dev-java-cui:parse-rewrite-log'

    def test_returns_none_when_no_domain_declares_the_verb(self, monkeypatch, tmp_path):
        import file_ops

        marshal = tmp_path / 'marshal.json'
        marshal.write_text('{"skill_domains": {"java": {"bundle": "pm-dev-java"}}}')
        monkeypatch.setattr(file_ops, 'get_marshal_path', lambda: marshal)

        assert resolve_domain_verb() is None

    def test_returns_none_when_marshal_absent(self, monkeypatch, tmp_path):
        import file_ops

        monkeypatch.setattr(file_ops, 'get_marshal_path', lambda: tmp_path / 'nonexistent.json')

        assert resolve_domain_verb() is None
