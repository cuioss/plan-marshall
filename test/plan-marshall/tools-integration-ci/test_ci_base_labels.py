#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Labels cluster — issue_wait_for_label."""

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


def test_issue_wait_for_label_registered():
    """`issue wait-for-label` subcommand must be registered under the issue subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
        ]
    )
    assert args.command == 'issue'
    assert args.issue_command == 'wait-for-label'
    assert args.issue_number == 99
    assert args.label == 'ready'


def test_issue_wait_for_label_requires_issue_number():
    """`issue wait-for-label` must exit when --issue-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-label', '--label', 'ready'])


def test_issue_wait_for_label_requires_label():
    """`issue wait-for-label` must exit when --label is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-label', '--issue-number', '99'])


def test_issue_wait_for_label_defaults():
    """--timeout and --interval default to module constants; --mode defaults to 'present'."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
        ]
    )
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL
    assert args.mode == 'present'


def test_issue_wait_for_label_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
            '--timeout',
            '45',
            '--interval',
            '3',
        ]
    )
    assert args.timeout == 45
    assert args.interval == 3


@pytest.mark.parametrize('mode', ['present', 'absent'])
def test_issue_wait_for_label_accepts_valid_mode_values(mode):
    """--mode accepts present and absent."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
            '--mode',
            mode,
        ]
    )
    assert args.mode == mode


def test_issue_wait_for_label_rejects_invalid_mode_value():
    """--mode must reject values outside the present|absent choice set."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'issue',
                'wait-for-label',
                '--issue-number',
                '99',
                '--label',
                'ready',
                '--mode',
                'toggled',
            ]
        )


# =============================================================================
# extract_routing_args — two-state ``--plan-id`` / ``--project-dir`` contract
# =============================================================================
#
# ``extract_routing_args`` is the router-side wrapper that combines
# ``extract_project_dir`` and ``extract_plan_id``. It enforces:
#
# * router-level ``--plan-id`` is consumed for worktree resolution
# * subcommand-level ``--plan-id`` (after pr/ci/issue/branch) is left in place
# * supplying both flags at the router → exit 2 + mutually_exclusive_args
# * supplying only ``--plan-id`` → manage-status get-worktree-path resolves
# * supplying only ``--project-dir`` → returned verbatim (legacy escape hatch)
# * supplying neither → returns (None, argv)
