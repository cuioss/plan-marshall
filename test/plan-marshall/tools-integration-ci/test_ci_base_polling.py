#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Polling cluster — wait_for_status_flip, pull_request_runs, adaptive wait, issue wait_for_close."""

import argparse
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import ci_base
import pytest
from _merge_shaped_roster import PROVIDERS, registry_keys
from _resolve_project_dir_fixtures import worktree_query_result
from ci_base import (
    BODY_KIND_ISSUE_COMMENT,
    BODY_KIND_ISSUE_CREATE,
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    CI_LOG_TRUNCATE_LINES,
    DEFAULT_CI_INTERVAL,
    DEFAULT_CI_TIMEOUT,
    VALID_BODY_KINDS,
    add_head_arg,
    add_pr_create_args,
    build_parser,
    compute_elapsed,
    compute_total_elapsed,
    delete_consumed_body,
    enrich_failing_checks_with_logs,
    get_body_path,
    get_default_cwd,
    get_known_subcommands,
    normalize_issue_ref,
    poll_until,
    prepare_body,
    read_and_consume_body,
    register_subcommands,
    run_cli,
    set_default_cwd,
    truncate_log_content,
)

from conftest import PROJECT_ROOT

# =============================================================================
# Shared constants tests
# =============================================================================


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Return every option string declared directly on *parser*."""
    return {opt for action in parser._actions for opt in action.option_strings}


def _parser_paths(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()) -> dict[int, str]:
    """Map ``id(sub_parser)`` -> its space-joined command path, for every node under *parser*."""
    paths: dict[int, str] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                path = (*prefix, name)
                paths[id(sub)] = ' '.join(path)
                paths.update(_parser_paths(sub, path))
    return paths


@pytest.fixture
def plan_base_env(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at a temporary directory so get_plan_dir is sandboxed.

    Also seeds an initialized plan directory for the conventional ``my-plan``
    plan_id used by the body-store happy-path tests. The
    ``ci_base.prepare_body`` script-side guard requires the plan dir to contain a ``status.json`` sentinel before any
    scratch path is materialised; without this seed every existing
    prepare-body test would fail.

    Tests that exercise the guard's rejection path (unknown plan_id, plan
    dir missing status.json) deliberately use a DIFFERENT plan_id so the
    seed below does not satisfy the guard for them.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'my-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return tmp_path


class _FakeCompletedProcess:
    """Minimal stand-in for subprocess.CompletedProcess for run_cli tests."""

    def __init__(self, returncode: int = 0, stdout: str = '', stderr: str = ''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def _reset_default_cwd():
    """Save/restore the module-global _DEFAULT_CWD around each test."""
    previous = get_default_cwd()
    yield
    set_default_cwd(previous)


@pytest.fixture
def _capture_subprocess_run(monkeypatch):
    """Replace ci_base.subprocess.run with a capturing stub.

    Returns the list that will be populated with each call's kwargs. run_cli
    always calls subprocess.run via the ci_base module import, so patching the
    attribute on the module object is sufficient.
    """
    calls: list[dict] = []

    def fake_run(cmd, **kwargs):
        calls.append({'cmd': cmd, **kwargs})
        return _FakeCompletedProcess(returncode=0, stdout='ok', stderr='')

    monkeypatch.setattr(ci_base.subprocess, 'run', fake_run)
    return calls


def _documented_checks_verbs() -> set[str]:
    """Return the ``checks`` sub-verbs the leaf-command reference documents.

    Raises:
        AssertionError: if the reference yielded no row at all. An empty derivation
            is the vacuity this guard exists to catch — the equality assertion that
            consumes it would otherwise compare the live parser against an empty
            set and fail for the wrong reason, or (had it been a subset check) pass
            over nothing.
    """
    text = _LEAF_COMMAND_REFERENCE.read_text(encoding='utf-8')
    verbs = {match.group('verb') for match in _CHECKS_ROW.finditer(text)}
    assert verbs, (
        f'no `checks {{verb}}` table row was derived from {_LEAF_COMMAND_REFERENCE} — '
        f'the documented population is vacuous, so it cannot pin the live parser'
    )
    return verbs


def _registered_pr_verbs() -> set[str]:
    """Return every ``pr`` sub-verb some CI provider registers.

    Derived from the providers' ``handlers: HandlerMap`` registry literals — the
    closed population — never from a ``def cmd_pr_`` scan, which is a sample.

    Raises:
        AssertionError: if no ``('pr', verb)`` key was derived at all. An empty
            derivation is the vacuity every guard below would otherwise pass over.
    """
    verbs = {
        key[1]
        for text in _PROVIDER_OPS_TEXT.values()
        for key in registry_keys(text)
        if len(key) == 2 and key[0] == 'pr'
    }
    assert verbs, (
        f'no ("pr", verb) registry key was derived from {sorted(_PROVIDER_OPS_TEXT)} — '
        f'the registered population is vacuous, so it cannot pin any documentation'
    )
    return verbs


def _documented_pr_verbs(document: Path) -> set[str]:
    """Return the ``pr`` sub-verbs ``document`` carries a table row for.

    Raises:
        AssertionError: if the document yielded no row at all — the same vacuity
            guard ``_documented_checks_verbs`` applies, for the same reason.
    """
    verbs = {match.group('verb') for match in _PR_ROW.finditer(document.read_text(encoding='utf-8'))}
    assert verbs, (
        f'no `pr {{verb}}` table row was derived from {document} — the documented '
        f'population is vacuous, so it cannot pin the registered verb set'
    )
    return verbs


@pytest.fixture(autouse=False)
def _reset_subcommand_cache():
    """Reset ci_base._KNOWN_SUBCOMMANDS_CACHE around each test.

    The subcommand registry is module-level state — tests that call
    ``register_subcommands`` or that trigger ``get_known_subcommands``
    would otherwise pollute later tests in the session.  This fixture
    saves and restores the cache value so each test starts clean.
    """
    previous = ci_base._KNOWN_SUBCOMMANDS_CACHE
    ci_base._KNOWN_SUBCOMMANDS_CACHE = None
    yield
    ci_base._KNOWN_SUBCOMMANDS_CACHE = previous


def _failing_check(name: str, run_id: str, *, job_name: str | None = None) -> dict:
    """Build a minimal failing-check entry for the enrich hook."""
    return {
        'name': name,
        'job_name': job_name if job_name is not None else name,
        'workflow_name': 'ci',
        'conclusion': 'failure',
        'run_id': run_id,
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/x',
        'head_sha': 'cafef00d',
        'pr_number': 7,
    }


def _mq_wait_ns(*, adaptive: bool, timeout):
    """Build the minimal namespace ``_run_checks_wait`` reads (adaptive, timeout)."""
    return argparse.Namespace(adaptive=adaptive, timeout=timeout)


_NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)


_GO_ZERO = '0001-01-01T00:00:00Z'


def test_ci_wait_for_status_flip_registered():
    """`checks wait-for-status-flip` subcommand must be registered under the checks subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '42'])
    assert args.command == 'checks'
    assert args.checks_command == 'wait-for-status-flip'
    assert args.pr_number == 42


def test_ci_wait_for_status_flip_requires_pr_number():
    """`checks wait-for-status-flip` must exit when --pr-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['checks', 'wait-for-status-flip'])


def test_ci_wait_for_status_flip_defaults():
    """--timeout and --interval default to module constants; --expected defaults to 'any'."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '7'])
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL
    assert args.expected == 'any'


def test_ci_wait_for_status_flip_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'checks',
            'wait-for-status-flip',
            '--pr-number',
            '7',
            '--timeout',
            '600',
            '--interval',
            '15',
        ]
    )
    assert args.timeout == 600
    assert args.interval == 15


@pytest.mark.parametrize('expected', ['success', 'failure', 'any'])
def test_ci_wait_for_status_flip_accepts_valid_expected_values(expected):
    """--expected accepts success, failure, and any."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '7', '--expected', expected])
    assert args.expected == expected


def test_ci_wait_for_status_flip_rejects_invalid_expected_value():
    """--expected must reject values outside the success|failure|any choice set."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'checks',
                'wait-for-status-flip',
                '--pr-number',
                '7',
                '--expected',
                'pending',
            ]
        )


# =============================================================================
# checks pull-request-runs argparse tests
# =============================================================================
#
# Registered alongside its ``checks`` siblings and named in kebab-case to match
# them. The verb carries the PR-wide ``not_triggered`` observable — whether any
# pull_request-event workflow run exists for the PR at all.

#: The independent authority the registered ``checks`` verb set is pinned against.
#: Its own preamble declares each group table a COMPLETE index of that group's
#: registered sub-verbs, which is what makes an equality comparison against it
#: meaningful rather than merely conventional.
_LEAF_COMMAND_REFERENCE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-integration-ci'
    / 'standards'
    / 'leaf-command-reference.md'
)

#: A ``checks {verb}`` row of that reference's group table: the backticked command
#: opening a table row's leading cell. Anchored at the line start and requiring the
#: leading pipe, so a ``ci checks status`` shown inside a fenced example is prose
#: and never joins the documented population.
_CHECKS_ROW = re.compile(r'^\|\s*`checks (?P<verb>[a-z][a-z0-9-]*)`\s*\|', re.MULTILINE)


def test_ci_pull_request_runs_registered():
    """`checks pull-request-runs` must be registered under the checks subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'pull-request-runs', '--pr-number', '42'])
    assert args.command == 'checks'
    assert args.checks_command == 'pull-request-runs'
    assert args.pr_number == 42


def test_ci_pull_request_runs_requires_pr_number():
    """`checks pull-request-runs` must exit when --pr-number is omitted.

    A defaulted PR selector would let the verb answer about a different PR — or
    none — while still reporting a confident observable.
    """
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['checks', 'pull-request-runs'])


def test_ci_pull_request_runs_takes_no_wait_arguments():
    """The verb is a point-in-time READ, so it declares no --timeout / --interval.

    Its siblings that poll declare both. Asserting their absence pins that this
    verb is not a wait: an existence question about the past needs no budget, and a
    timeout on it would imply the answer could change while being asked.
    """
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'pull-request-runs', '--pr-number', '42'])
    assert not hasattr(args, 'timeout')
    assert not hasattr(args, 'interval')


def test_the_checks_verb_set_agrees_with_the_documented_contract():
    """The LIVE ``checks`` verb set equals the one the leaf-command reference documents.

    Both sides are DERIVED, and from INDEPENDENT sources: the registered set off
    the live argparse subparser, the documented set off the reference table's rows.
    Neither is a literal restated in this file, so a partial mirror cannot form
    here — a mirror is exactly what makes a "sibling" assertion drift, since it
    goes stale silently while the assertion keeps passing.

    The comparison is EQUALITY, not a subset relation. A subset assertion covers a
    newly added verb by ignoring it: the verb is simply invisible to the check, so
    the test neither enumerates the siblings nor detects a new one. Equality means a
    verb added to the parser fails here until its reference row exists, and a row
    added without a parser registration fails the other way — parser and contract
    are pinned to each other in both directions.

    The reference table is a legitimate authority for this because it declares
    itself one: "Every group table below carries one row per registered sub-verb of
    that group — the tables are the complete index, not a selection."
    """
    _parser, _pr_sub, checks_sub, _issue_sub, _branch_sub = build_parser('test')

    registered = set(checks_sub.choices)
    documented = _documented_checks_verbs()

    assert registered, 'the checks subparser registered no verb at all'
    assert registered == documented, (
        f'the checks parser and the leaf-command reference disagree — '
        f'registered but undocumented={sorted(registered - documented)}, '
        f'documented but unregistered={sorted(documented - registered)}'
    )


# =============================================================================
# pr doc-parity — the registered sub-verbs against their documentation rows
# =============================================================================
#
# The ``checks`` guard above takes its live side from ``checks_sub.choices``,
# because every ``checks`` verb is registered in the shared ``ci_base.build_parser``
# and that subparser IS the registry. ``pr`` cannot use that source: the group is
# SPLIT. ``pr landing-state`` is added to ``pr_sub`` by the GitHub front-end
# (``github_ops.main``) rather than by ``build_parser``, so ``pr_sub.choices`` off a
# bare ``build_parser('test')`` is short by exactly the provider-specific additions
# — and a verb the live-side derivation cannot see is one no parity guard can pin.
#
# The authority here is therefore each provider's ``handlers: HandlerMap`` registry
# literal, read through the designated shared derivation in ``_merge_shaped_roster``
# (the same literal and the same regexes that module's other consumers use, so the
# ``pr`` population is derived once rather than re-derived per suite). The
# population is the UNION over both providers: a verb EITHER provider registers is
# reachable through the ``ci`` abstraction and must be documented, even where the
# other provider has no handler for it.
#
# Two documents are pinned, because they answer different questions and a verb can
# be present in one and missing from the other: ``leaf-command-reference.md`` is the
# flag cheat-sheet (pinned by EQUALITY, as for ``checks``, since it declares its
# group tables a complete index), and ``api-contract.md`` is the response-shape
# authority (pinned by COVERAGE modulo a documented exemption, since it documents
# shapes rather than commands).

#: The response-shape authority. Its ``pr`` rows are spread over TWO tables — the
#: read-verb table under "PR Operations" and the "State-Transition Operations
#: (summary)" table — so the derivation reads the whole document and a row in
#: EITHER satisfies the guard. Resolved as a sibling of the leaf-command reference
#: rather than by re-typing the path chain above it.
_API_CONTRACT = _LEAF_COMMAND_REFERENCE.parent / 'api-contract.md'

#: ``marketplace/bundles/plan-marshall/skills`` — the leaf-command reference sits at
#: ``{skills}/tools-integration-ci/standards/leaf-command-reference.md``, so three
#: levels up is the skills root the provider modules also hang off.
_BUNDLE_SKILLS = _LEAF_COMMAND_REFERENCE.parents[2]

#: Each provider's ``*_ops.py`` source text, keyed by the provider set the shared
#: roster declares — iterated rather than re-typed, so a third provider joins this
#: guard by being added there.
_PROVIDER_OPS_TEXT: dict[str, str] = {
    provider: (_BUNDLE_SKILLS / f'workflow-integration-{provider}' / 'scripts' / f'{provider}_ops.py').read_text(
        encoding='utf-8'
    )
    for provider in PROVIDERS
}

#: A ``pr {verb}`` documentation row in either reference. The verb is the backticked
#: command's second word; the remainder of the leading cell is skipped (``[^|]*``)
#: because a row legitimately carries more there — an inline argument
#: (``pr close --pr-number N``) or a provider annotation (``**(GitHub only)**``).
#: Anchored at the line start and requiring the leading pipe AND the backtick, so a
#: ``ci pr merge`` shown in an anti-pattern table or a fenced example is prose and
#: never joins the documented population.
_PR_ROW = re.compile(r'^\|\s*`pr (?P<verb>[a-z][a-z0-9-]*)[^|]*\|', re.MULTILINE)

#: Registered ``pr`` verbs deliberately absent from ``api-contract.md``, each mapped
#: to the reason it is exempt. An exemption is a recorded decision rather than a
#: silence, and it is kept honest from both directions by
#: ``test_api_contract_pr_exemptions_are_live`` below: an entry naming a verb that is
#: no longer registered, or one that HAS since gained its row, fails rather than
#: quietly widening the allowance.
_API_CONTRACT_PR_EXEMPT: dict[str, str] = {
    'submit-review': (
        'api-contract.md documents response SHAPES, and this verb adds none — it '
        'publishes a pending draft review and returns the standard envelope with no '
        'extra response field. Its argument surface is documented in '
        'leaf-command-reference.md (which this guard pins by equality) and its '
        'GitLab-side refusal in that provider impl doc.'
    ),
}


def test_the_pr_verb_set_agrees_with_the_documented_contract():
    """The registered ``pr`` verb set equals the one the leaf-command reference documents.

    The ``checks`` assertion's contract, applied to the split ``pr`` group: both
    sides DERIVED from independent sources, compared by EQUALITY so a verb added to
    a provider registry fails here until its reference row exists, and a row added
    without a registration fails the other way.

    The reference table is a legitimate authority for the equality because it
    declares itself one: "Every group table below carries one row per registered
    sub-verb of that group — the tables are the complete index, not a selection."
    ``pr`` spans TWO of its tables (Pull Request Operations and Review Operations);
    the row regex is table-agnostic, so the documented side is their union — which is
    what that declaration is about, the group rather than any one table.
    """
    registered = _registered_pr_verbs()
    documented = _documented_pr_verbs(_LEAF_COMMAND_REFERENCE)

    assert registered == documented, (
        f'the pr provider registries and the leaf-command reference disagree — '
        f'registered but undocumented={sorted(registered - documented)}, '
        f'documented but unregistered={sorted(documented - registered)}'
    )


def test_every_registered_pr_verb_has_an_api_contract_row():
    """Every registered ``pr`` verb is documented in ``api-contract.md``, or is exempt.

    Coverage rather than equality, because the two documents answer different
    questions: the leaf-command reference indexes COMMANDS (and declares itself
    complete), while ``api-contract.md`` documents RESPONSE SHAPES and legitimately
    says nothing about a verb that adds no field beyond the standard envelope. The
    allowance for that is a NAMED exemption carrying its reason, not a subset
    relation — a subset check would cover a newly added verb by ignoring it.

    A row in EITHER of the document's two ``pr`` tables counts: the read-verb table
    under "PR Operations" and the "State-Transition Operations (summary)" table
    partition the group by what a verb DOES, and that split is a presentation choice
    the guard must not read as a contract.

    The reverse direction is asserted too: a ``pr`` row for a verb no provider
    registers is documentation for a command that cannot be run.
    """
    registered = _registered_pr_verbs()
    documented = _documented_pr_verbs(_API_CONTRACT)

    undocumented = registered - documented - set(_API_CONTRACT_PR_EXEMPT)
    assert not undocumented, (
        f'registered pr verbs with no {_API_CONTRACT.name} row and no recorded exemption: {sorted(undocumented)}'
    )
    assert not documented - registered, (
        f'{_API_CONTRACT.name} documents pr verbs no provider registry registers: {sorted(documented - registered)}'
    )


def test_api_contract_pr_exemptions_are_live():
    """Each recorded exemption names a registered verb that is genuinely undocumented.

    An exemption list is the one part of the guard above that is asserted rather than
    derived, so it is pinned from BOTH directions here — otherwise it decays into a
    permanent hole. A key whose verb is no longer registered is stale; a key whose
    verb HAS since gained its row is an allowance that is now silently covering
    nothing, and either would let a future gap slip in under a name nobody re-read.
    Each entry must also carry a non-empty reason: the exemption is the reason.
    """
    registered = _registered_pr_verbs()
    documented = _documented_pr_verbs(_API_CONTRACT)

    for verb, reason in _API_CONTRACT_PR_EXEMPT.items():
        assert verb in registered, f'exemption {verb!r} names a verb no provider registry registers'
        assert verb not in documented, (
            f'exemption {verb!r} is obsolete — {_API_CONTRACT.name} now carries a row for it, '
            f'so the entry should be removed rather than left covering nothing'
        )
        assert reason.strip(), f'exemption {verb!r} carries no reason'


# =============================================================================
# issue wait-for-close argparse tests
# =============================================================================


def test_issue_wait_for_close_registered():
    """`issue wait-for-close` subcommand must be registered under the issue subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'wait-for-close', '--issue-number', '99'])
    assert args.command == 'issue'
    assert args.issue_command == 'wait-for-close'
    assert args.issue_number == 99


def test_issue_wait_for_close_requires_issue_number():
    """`issue wait-for-close` must exit when --issue-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-close'])


def test_issue_wait_for_close_defaults():
    """--timeout and --interval default to module constants."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'wait-for-close', '--issue-number', '99'])
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL


def test_issue_wait_for_close_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-close',
            '--issue-number',
            '99',
            '--timeout',
            '120',
            '--interval',
            '5',
        ]
    )
    assert args.timeout == 120
    assert args.interval == 5


# =============================================================================
# issue wait-for-label argparse tests
# =============================================================================


def test_ci_wait_parser_registers_adaptive_flag_default_false():
    """`checks wait` registers --adaptive (store_true, default False)."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42'])
    assert args.adaptive is False


def test_ci_wait_parser_adaptive_flag_sets_true():
    """Passing --adaptive flips the namespace flag True."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42', '--adaptive'])
    assert args.adaptive is True


def test_ci_wait_parser_timeout_default_is_none_sentinel():
    """`checks wait --timeout` now defaults to a None sentinel (was DEFAULT_CI_TIMEOUT).

    The sentinel is how ``_run_checks_wait`` detects that the operator did NOT
    pass an explicit --timeout, so it can seed the ceiling from the adaptive
    budget instead of the fixed default.
    """
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42'])
    assert args.timeout is None


def test_ci_wait_parser_explicit_timeout_preserved():
    """An explicit --timeout survives as the integer the operator passed."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42', '--timeout', '900'])
    assert args.timeout == 900


def test_run_checks_wait_adaptive_seeds_timeout_when_omitted(monkeypatch):
    """--adaptive with an omitted --timeout seeds the ceiling from the ci:wait budget."""
    seed_calls: list[int] = []

    def stub_get(default_seconds: int) -> int:
        seed_calls.append(default_seconds)
        return 720

    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_get', stub_get)
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda _d: None)

    seen_timeout: list[int] = []

    def handler(args):
        seen_timeout.append(args.timeout)
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 300}

    result = ci_base._run_checks_wait(_mq_wait_ns(adaptive=True, timeout=None), handler)

    # The handler ran against the seeded ceiling, not the fixed default.
    assert seen_timeout == [720]
    assert seed_calls == [ci_base.DEFAULT_CI_TIMEOUT]  # fallback default forwarded
    assert result['status'] == 'success'


def test_run_checks_wait_adaptive_records_observed_duration(monkeypatch):
    """--adaptive records the handler's observed duration_sec into the ci:wait budget."""
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_get', lambda _d: 600)
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    def handler(_args):
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 415}

    ci_base._run_checks_wait(_mq_wait_ns(adaptive=True, timeout=None), handler)

    assert recorded == [415]


def test_run_checks_wait_non_adaptive_does_not_record(monkeypatch):
    """Without --adaptive, no record is made (the double-record guard)."""
    monkeypatch.setattr(
        ci_base,
        '_adaptive_wait_timeout_get',
        lambda _d: (_ for _ in ()).throw(AssertionError('seed must not run when non-adaptive')),
    )
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    seen_timeout: list[int] = []

    def handler(args):
        seen_timeout.append(args.timeout)
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 415}

    ci_base._run_checks_wait(_mq_wait_ns(adaptive=False, timeout=None), handler)

    # An omitted --timeout falls back to the fixed default (NOT the budget seed).
    assert seen_timeout == [ci_base.DEFAULT_CI_TIMEOUT]
    # And nothing was recorded — ci_complete_precondition owns the record here.
    assert recorded == []


def test_run_checks_wait_adaptive_skips_record_when_no_duration(monkeypatch):
    """A wait envelope without a positive duration_sec records nothing."""
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_get', lambda _d: 600)
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    def handler_missing(_args):
        return {'status': 'success', 'final_status': 'success'}  # no duration_sec

    def handler_zero(_args):
        return {'status': 'timeout', 'duration_sec': 0}

    ci_base._run_checks_wait(_mq_wait_ns(adaptive=True, timeout=None), handler_missing)
    ci_base._run_checks_wait(_mq_wait_ns(adaptive=True, timeout=None), handler_zero)

    assert recorded == []


def test_dispatch_routes_checks_wait_through_adaptive(monkeypatch):
    """dispatch() routes `checks wait --adaptive` through the seed/record wrapper."""
    from ci_base import dispatch

    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_get', lambda _d: 480)
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42', '--adaptive'])

    seen_timeout: list[int] = []

    def wait_handler(a):
        seen_timeout.append(a.timeout)
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 333}

    handlers = {('checks', 'wait'): wait_handler}
    result = dispatch(args, handlers, parser)

    assert seen_timeout == [480]  # seeded via the adaptive budget
    assert recorded == [333]  # observed duration recorded
    assert result['status'] == 'success'


def test_dispatch_checks_wait_non_adaptive_unwrapped(monkeypatch):
    """`checks wait` without --adaptive still resolves the None timeout to the default."""
    from ci_base import dispatch

    monkeypatch.setattr(
        ci_base,
        '_adaptive_wait_timeout_get',
        lambda _d: (_ for _ in ()).throw(AssertionError('seed must not run without --adaptive')),
    )
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait', '--pr-number', '42'])

    seen_timeout: list[int] = []

    def wait_handler(a):
        seen_timeout.append(a.timeout)
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 333}

    handlers = {('checks', 'wait'): wait_handler}
    dispatch(args, handlers, parser)

    assert seen_timeout == [ci_base.DEFAULT_CI_TIMEOUT]
    assert recorded == []


def test_adaptive_wait_timeout_get_delegates_to_run_config(monkeypatch):
    """_adaptive_wait_timeout_get reads the persisted ci:wait budget via run_config."""
    import run_config

    seen: list[tuple[str, int]] = []

    def stub_timeout_get(command_key, default):
        seen.append((command_key, default))
        return 842

    monkeypatch.setattr(run_config, 'timeout_get', stub_timeout_get)

    value = ci_base._adaptive_wait_timeout_get(600)

    assert value == 842
    assert seen == [(ci_base.CI_WAIT_TIMEOUT_KEY, 600)]
    assert ci_base.CI_WAIT_TIMEOUT_KEY == 'ci:wait'


def test_adaptive_wait_timeout_get_degrades_to_default_on_failure(monkeypatch):
    """A failing run_config.timeout_get degrades to the supplied default."""
    import run_config

    def boom(_command_key, _default):
        raise RuntimeError('run-configuration.json unreadable')

    monkeypatch.setattr(run_config, 'timeout_get', boom)

    assert ci_base._adaptive_wait_timeout_get(600) == 600


def test_adaptive_wait_timeout_set_delegates_to_run_config(monkeypatch):
    """_adaptive_wait_timeout_set records the observed duration via run_config."""
    import run_config

    seen: list[tuple[str, int]] = []
    monkeypatch.setattr(run_config, 'timeout_set', lambda command_key, duration: seen.append((command_key, duration)))

    ci_base._adaptive_wait_timeout_set(415)

    assert seen == [(ci_base.CI_WAIT_TIMEOUT_KEY, 415)]


def test_adaptive_wait_timeout_set_swallows_failure(monkeypatch):
    """A failing run_config.timeout_set is swallowed (best-effort telemetry)."""
    import run_config

    def boom(_command_key, _duration):
        raise RuntimeError('write failed')

    monkeypatch.setattr(run_config, 'timeout_set', boom)

    # Must not raise.
    ci_base._adaptive_wait_timeout_set(415)
