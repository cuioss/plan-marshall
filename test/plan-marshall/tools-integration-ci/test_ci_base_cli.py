#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI cluster — parser surface, body path, run_cli."""


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


def test_add_head_arg_registers_optional_flag():
    """add_head_arg should register --head as an optional argument on a subparser."""
    parser = argparse.ArgumentParser()
    add_head_arg(parser)

    # Optional — parses without --head
    args = parser.parse_args([])
    assert args.head is None

    # Accepts a branch name
    args = parser.parse_args(['--head', 'feature/x'])
    assert args.head == 'feature/x'


def test_pr_create_parser_accepts_head_flag():
    """add_pr_create_args should register --head on the pr create subparser."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'my-plan', '--head', 'feature/x'])
    assert args.head == 'feature/x'

    # Still optional — works without --head, but --plan-id is now required
    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'my-plan'])
    assert args.head is None
    assert args.plan_id == 'my-plan'


def test_pr_create_parser_registers_no_inline_body_source():
    """pr create registers NEITHER retired body flag: ``--body`` nor ``--body-file``.

    The body now comes from ONE source — the plan-bound store keyed by
    ``--plan-id``, with the ``NO_PLAN`` sentinel serving genuinely plan-less
    callers. Both retired flags are asserted here rather than only the legacy
    ``--body``: ``--body-file`` was the SECOND plan-less convention this
    deliverable removed, and an un-asserted removal is one a future change can
    silently undo.
    """
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    # Legacy inline --body flag is unknown → argparse error.
    with pytest.raises(SystemExit):
        parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--body', 'X'])
    # The retired plan-less --body-file source is likewise unknown.
    with pytest.raises(SystemExit):
        parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--body-file', '/tmp/x'])


def test_pr_create_parser_requires_plan_id():
    """``--plan-id`` is a plain required argument on ``pr create`` again.

    While ``--body-file`` existed, ``--plan-id`` was an optional member of a
    required mutually-exclusive body-source group, and this case asserted only
    that omitting BOTH sources failed. With the second source gone ``--plan-id``
    returns to ``required=True``, matching the five verbs that use
    ``add_body_consumer_args`` — the registration symmetry this deliverable
    restores — so the accepting half is asserted here too.
    """
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    with pytest.raises(SystemExit):
        parser.parse_args(['create', '--title', 'T'])

    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'NO_PLAN'])
    assert args.plan_id == 'NO_PLAN'
    assert args.slot is None


def test_pr_create_parser_accepts_slot():
    """Optional --slot passes through to the namespace."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)
    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--slot', 'pr-body'])
    assert args.slot == 'pr-body'


def test_build_parser_pr_view_accepts_head_flag():
    """build_parser should register --head on pr view (was: no args)."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'view', '--head', 'feature/x'])
    assert args.head == 'feature/x'


def test_build_parser_pr_view_accepts_pr_number_flag():
    """`pr view` must declare --pr-number — the only selector a landing poll can use.

    A required platform merge queue auto-deletes the head branch as it merges, so a
    --head-keyed poll stops resolving at exactly the moment `state: merged` becomes
    observable. While this flag was undeclared, the documented queue-landing poll
    (`ci pr view --pr-number {n}`) exited 2 on every iteration, so the gate could
    never corroborate the landing it exists to gate on.
    """
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'view', '--pr-number', '42'])
    assert args.pr_number == 42
    assert args.head is None


def test_build_parser_pr_view_accepts_neither_selector():
    """Unlike the merge-shaped verbs, `pr view` parses with NEITHER selector.

    Both flags are optional here; omitting both is the historical current-cwd-HEAD
    lookup, and adding --pr-number must not have silently made a selector mandatory.
    """
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'view'])
    assert args.pr_number is None
    assert args.head is None


def test_every_add_head_arg_verb_also_declares_pr_number(monkeypatch):
    """Every subparser that receives --head must also declare --pr-number.

    ``add_head_arg``'s help string presents --head as usable "in place of
    --pr-number", a claim that is only true on a parser which actually declares that
    flag. `pr view` carried the help string without the flag, so the advertised
    substitute was a form argparse rejected with exit 2.

    The population is DERIVED, not hand-listed: ``add_head_arg`` is wrapped for the
    duration of one real ``build_parser`` call, so the checked set is exactly its live
    call sites. The population itself is asserted first, so a probe that observed
    nothing (a refactor that stops routing through the helper) fails loudly instead of
    passing vacuously on an empty offender list. `pr create` / `pr list` declare their
    own branch-filter --head without this helper and are correctly outside the set —
    neither has a PR to number.
    """
    registered: list[argparse.ArgumentParser] = []
    real_add_head_arg = ci_base.add_head_arg

    def recording_add_head_arg(subparser: argparse.ArgumentParser) -> None:
        registered.append(subparser)
        real_add_head_arg(subparser)

    monkeypatch.setattr(ci_base, 'add_head_arg', recording_add_head_arg)
    parser, _, _, _, _ = ci_base.build_parser('test')

    paths = _parser_paths(parser)
    population = sorted(paths.get(id(sub), '<unreachable-from-parser-tree>') for sub in registered)
    assert population == [
        'checks status',
        'pr auto-merge',
        'pr merge',
        'pr merge-queue',
        'pr safe-merge',
        'pr update-branch',
        'pr view',
    ], population

    offenders = sorted(
        paths.get(id(sub), '<unreachable-from-parser-tree>')
        for sub in registered
        if '--pr-number' not in _option_strings(sub)
    )
    assert offenders == [], (
        f'these --head verbs advertise --head "in place of --pr-number" but declare no such flag: {offenders}'
    )


def test_build_parser_pr_merge_pr_number_optional():
    """pr merge should accept --head as alternative to --pr-number (both optional)."""
    parser, _, _, _, _ = build_parser('test')
    # --head alone is allowed
    args = parser.parse_args(['pr', 'merge', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None
    # --pr-number alone is allowed
    args = parser.parse_args(['pr', 'merge', '--pr-number', '42'])
    assert args.pr_number == 42
    assert args.head is None


def test_build_parser_pr_auto_merge_pr_number_optional():
    """pr auto-merge should accept --head as alternative to --pr-number."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'auto-merge', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


def test_build_parser_ci_status_pr_number_optional():
    """checks status should accept --head as alternative to --pr-number."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'status', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


# =============================================================================
# prepare-body subcommand registration (argparse wiring)
# =============================================================================


def test_build_parser_registers_pr_prepare_body():
    """`pr prepare-body` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'pr'
    assert args.pr_command == 'prepare-body'
    assert args.plan_id == 'my-plan'
    assert args.prepare_for == 'create'  # default

    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan', '--for', 'edit', '--slot', 'update'])
    assert args.prepare_for == 'edit'
    assert args.slot == 'update'

    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'prepare-body'])  # missing --plan-id


def test_build_parser_registers_pr_prepare_comment():
    """`pr prepare-comment` must be registered with reply/thread-reply modes."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-comment', '--plan-id', 'my-plan'])
    assert args.pr_command == 'prepare-comment'
    assert args.prepare_for == 'reply'

    args = parser.parse_args(['pr', 'prepare-comment', '--plan-id', 'my-plan', '--for', 'thread-reply'])
    assert args.prepare_for == 'thread-reply'


def test_build_parser_registers_issue_prepare_body():
    """`issue prepare-body` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'prepare-body'
    assert args.plan_id == 'my-plan'


def test_issue_comment_body_kind_in_valid_set():
    """The issue-comment body kind must be a recognised consumer surface."""
    assert BODY_KIND_ISSUE_COMMENT == 'issue-comment'
    assert BODY_KIND_ISSUE_COMMENT in VALID_BODY_KINDS


def test_get_body_path_accepts_issue_comment_kind(plan_base_env):
    """get_body_path must resolve a scratch path for the issue-comment kind."""
    path = get_body_path('my-plan', BODY_KIND_ISSUE_COMMENT)
    assert path.name == 'issue-comment-default.md'
    assert 'work/ci-bodies' in str(path)


def test_build_parser_registers_issue_comment():
    """`issue comment` must be registered, require --issue and --plan-id, accept --slot."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'comment'
    assert args.issue == '42'
    assert args.plan_id == 'my-plan'

    args = parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'my-plan', '--slot', 'milestone'])
    assert args.slot == 'milestone'


def test_issue_comment_requires_issue():
    """`issue comment` must reject a missing --issue."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--plan-id', 'my-plan'])


def test_issue_comment_requires_plan_id():
    """`issue comment` must reject a missing --plan-id (body consumer)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--issue', '42'])


def test_issue_comment_rejects_body_flag():
    """`issue comment` consumes a prepared body — a raw --body flag is rejected."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'p', '--body', 'X'])


def test_build_parser_registers_issue_prepare_comment():
    """`issue prepare-comment` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'prepare-comment', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'prepare-comment'
    assert args.plan_id == 'my-plan'

    args = parser.parse_args(['issue', 'prepare-comment', '--plan-id', 'my-plan', '--slot', 'alt'])
    assert args.slot == 'alt'


def test_issue_prepare_comment_requires_plan_id():
    """`issue prepare-comment` must reject a missing --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'prepare-comment'])


def test_normalize_issue_ref_bare_number_unchanged():
    """A bare issue number is returned unchanged."""
    assert normalize_issue_ref('42') == '42'


def test_normalize_issue_ref_github_url():
    """A GitHub issue URL is normalized to the bare number."""
    assert normalize_issue_ref('https://github.com/o/r/issues/42') == '42'


def test_normalize_issue_ref_gitlab_url():
    """A GitLab issue URL (with the /-/ segment) is normalized to the IID."""
    assert normalize_issue_ref('https://gitlab.com/o/r/-/issues/42') == '42'


def test_normalize_issue_ref_url_with_query_and_fragment():
    """Trailing query/fragment segments are stripped from the extracted id."""
    assert normalize_issue_ref('https://github.com/o/r/issues/42?foo=bar') == '42'
    assert normalize_issue_ref('https://github.com/o/r/issues/42#note_1') == '42'


def test_normalize_issue_ref_unparseable_returned_unchanged():
    """A value with no extractable id is returned unchanged (silent-fail contract)."""
    assert normalize_issue_ref('not-a-url') == 'not-a-url'


# =============================================================================
# Consumer subcommands reject removed legacy body flags
# =============================================================================


def test_pr_reply_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'reply', '--pr-number', '1', '--plan-id', 'p', '--body', 'X'])


def test_pr_thread_reply_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'pr',
                'thread-reply',
                '--pr-number',
                '1',
                '--thread-id',
                't',
                '--plan-id',
                'p',
                '--body',
                'X',
            ]
        )


def test_pr_edit_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'edit', '--pr-number', '1', '--plan-id', 'p', '--body', 'X'])


def test_issue_create_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'create', '--title', 'T', '--plan-id', 'p', '--body', 'X'])


def test_consumers_require_plan_id():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'reply', '--pr-number', '1'])
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'create', '--title', 'T'])


# =============================================================================
# Body store helpers
# =============================================================================


def test_get_body_path_rejects_unknown_kind(plan_base_env):
    with pytest.raises(ValueError):
        get_body_path('my-plan', 'unknown-kind')


def test_get_body_path_default_slot(plan_base_env):
    path = get_body_path('my-plan', BODY_KIND_PR_CREATE)
    assert path.name == 'pr-create-default.md'
    assert 'work/ci-bodies' in str(path)


def test_get_body_path_custom_slot(plan_base_env):
    path = get_body_path('my-plan', BODY_KIND_PR_CREATE, slot='alt')
    assert path.name == 'pr-create-alt.md'


def test_get_body_path_rejects_invalid_slot(plan_base_env):
    with pytest.raises(ValueError):
        get_body_path('my-plan', BODY_KIND_PR_CREATE, slot='Has Spaces!')


def test_prepare_body_creates_parent_directory(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE)
    assert result['status'] == 'success'
    assert result['kind'] == BODY_KIND_PR_CREATE
    assert result['slot'] == 'default'
    assert result['exists'] is False
    # Parent directory was created so the caller can write immediately
    from pathlib import Path as _P

    assert _P(result['path']).parent.exists()


def test_prepare_body_reports_exists_flag(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    path = result['path']
    from pathlib import Path as _P

    _P(path).write_text('existing content', encoding='utf-8')
    result2 = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    assert result2['exists'] is True


def test_prepare_body_rejects_invalid_slot(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE, slot='BAD SLOT')
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_slot'


# ---------------------------------------------------------------------------
# Script-side require_plan_exists guard
#
# prepare_body MUST refuse to materialise a body scratch path under a plan
# directory that does not exist (or exists but lacks status.json). The guard
# returns the canonical TOON envelope and MUST NOT mkdir the plan tree as a
# side-effect.
# ---------------------------------------------------------------------------


def test_prepare_body_rejects_unknown_plan_id_no_mkdir(plan_base_env):
    """Unknown plan_id: prepare_body returns plan_not_found, no plan dir created."""
    unknown_plan_dir = plan_base_env / 'plans' / 'never-initialized'
    assert not unknown_plan_dir.exists(), 'pre-condition: plan dir must not exist'

    result = prepare_body('never-initialized', BODY_KIND_PR_CREATE)

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'never-initialized'
    assert 'never-initialized' in result['plan_dir']
    # Side-effect invariant: the guard MUST NOT have created the plan dir
    # (the orphan-mkdir failure mode this guard exists to prevent).
    assert not unknown_plan_dir.exists()
    # And no scratch ci-bodies dir is left behind either.
    assert not (unknown_plan_dir / 'work' / 'ci-bodies').exists()


def test_prepare_body_rejects_plan_dir_missing_status_json_no_mkdir(plan_base_env):
    """Plan dir exists but no status.json: prepare_body returns plan_not_found."""
    half_dir = plan_base_env / 'plans' / 'half-initialized'
    half_dir.mkdir(parents=True)
    assert not (half_dir / 'status.json').exists()

    result = prepare_body('half-initialized', BODY_KIND_PR_REPLY)

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'half-initialized'
    # The pre-existing directory was left untouched — the guard does not
    # remove it, and it certainly does not auto-create status.json.
    assert half_dir.is_dir()
    assert not (half_dir / 'status.json').exists()
    # The scratch tree was NOT materialised.
    assert not (half_dir / 'work' / 'ci-bodies').exists()


def test_prepare_body_with_initialized_plan_id_continues_to_work(plan_base_env):
    """Happy path: initialized plan_id (status.json present) → success.

    The `plan_base_env` fixture seeds `my-plan/status.json`. This test pins
    that the guard does not regress the existing prepare-body contract for
    in-progress plans.
    """
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE)

    assert result['status'] == 'success'
    assert result['kind'] == BODY_KIND_PR_CREATE
    assert result['slot'] == 'default'
    from pathlib import Path as _P

    assert _P(result['path']).parent.exists()


def test_read_and_consume_body_returns_content(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_ISSUE_CREATE)
    from pathlib import Path as _P

    _P(prep['path']).write_text('Issue description body', encoding='utf-8')

    content, err = read_and_consume_body('my-plan', BODY_KIND_ISSUE_CREATE)
    assert err is None
    assert content == 'Issue description body'


def test_read_and_consume_body_missing_file(plan_base_env):
    content, err = read_and_consume_body('no-plan', BODY_KIND_PR_CREATE)
    assert content is None
    assert err is not None
    assert err['error'] == 'body_not_prepared'


def test_read_and_consume_body_empty_file(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    from pathlib import Path as _P

    _P(prep['path']).write_text('   \n  ', encoding='utf-8')
    content, err = read_and_consume_body('my-plan', BODY_KIND_PR_REPLY)
    assert content is None
    assert err['error'] == 'body_empty'


def test_read_and_consume_body_optional_missing(plan_base_env):
    content, err = read_and_consume_body('my-plan', BODY_KIND_PR_EDIT, required=False)
    assert err is None
    assert content == ''


def test_read_and_consume_body_requires_plan_id(plan_base_env):
    content, err = read_and_consume_body('', BODY_KIND_PR_CREATE)
    assert content is None
    assert err['error'] == 'missing_plan_id'


def test_delete_consumed_body_removes_file(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_PR_THREAD_REPLY)
    from pathlib import Path as _P

    _P(prep['path']).write_text('body', encoding='utf-8')
    assert _P(prep['path']).exists()

    delete_consumed_body('my-plan', BODY_KIND_PR_THREAD_REPLY)
    assert not _P(prep['path']).exists()


def test_delete_consumed_body_silent_when_missing(plan_base_env):
    # Must not raise when the file does not exist
    delete_consumed_body('never-prepared', BODY_KIND_PR_CREATE)


# =============================================================================
# run_cli cwd propagation (worktree --project-dir plumbing)
# =============================================================================


def test_run_cli_forwards_explicit_cwd(_capture_subprocess_run, _reset_default_cwd):
    """An explicit cwd= kwarg must be passed through to subprocess.run."""
    set_default_cwd(None)
    rc, stdout, stderr = run_cli('gh', ['pr', 'list'], cwd='/tmp/worktree-xyz')
    assert rc == 0
    assert stdout == 'ok'
    assert stderr == ''
    assert len(_capture_subprocess_run) == 1
    call = _capture_subprocess_run[0]
    assert call['cwd'] == '/tmp/worktree-xyz'
    assert call['cmd'] == ['gh', 'pr', 'list']


def test_run_cli_uses_default_cwd_when_not_passed(_capture_subprocess_run, _reset_default_cwd):
    """When no cwd= is passed, run_cli must fall back to _DEFAULT_CWD."""
    set_default_cwd('/tmp/from-default')
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] == '/tmp/from-default'


def test_run_cli_defaults_cwd_to_none(_capture_subprocess_run, _reset_default_cwd):
    """Legacy behaviour: no explicit cwd and no default → cwd=None."""
    set_default_cwd(None)
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] is None


def test_run_cli_explicit_cwd_overrides_default(_capture_subprocess_run, _reset_default_cwd):
    """Explicit cwd= must win over the process-global default."""
    set_default_cwd('/tmp/from-default')
    run_cli('gh', ['pr', 'view'], cwd='/tmp/explicit')
    assert _capture_subprocess_run[0]['cwd'] == '/tmp/explicit'


def test_set_default_cwd_round_trip(_reset_default_cwd):
    """set_default_cwd / get_default_cwd should round-trip values including None."""
    set_default_cwd('/some/path')
    assert get_default_cwd() == '/some/path'
    set_default_cwd(None)
    assert get_default_cwd() is None


def test_run_cli_handles_file_not_found_without_touching_cwd(monkeypatch, _reset_default_cwd):
    """When the CLI binary is missing, run_cli must still return gracefully."""

    def raising_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(ci_base.subprocess, 'run', raising_run)
    set_default_cwd('/tmp/anywhere')
    rc, stdout, stderr = run_cli('nonexistent-cli', ['x'], not_found_msg='missing')
    assert rc == 127
    assert stdout == ''
    assert stderr == 'missing'


# =============================================================================
# checks wait-for-status-flip argparse tests
# =============================================================================


def test_extract_routing_args_neither_flag_returns_none():
    """No routing flags → (None, argv) so the legacy "inherit cwd" path runs."""
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['pr', 'view'])
    assert resolved is None
    assert remaining == ['pr', 'view']


def test_extract_routing_args_project_dir_only_returns_path():
    """--project-dir alone is returned verbatim as the resolved cwd."""
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['--project-dir', '/tmp/explicit', 'pr', 'view'])
    # The resolver normalizes to absolute paths; we assert the input survived.
    assert resolved is not None
    assert resolved.endswith('explicit'), f'Expected absolute path ending in explicit, got: {resolved!r}'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_plan_id_only_resolves_via_manage_status(monkeypatch):
    """--plan-id alone is resolved via the patched manage-status helper."""
    import file_ops as _resolver_core
    from ci_base import extract_routing_args

    # The manage-status shell-out seam lives in file_ops; resolve_project_dir
    # delegates the worktree face to file_ops.resolve_plan_context.
    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(True, '/tmp/worktree-resolved')
    )
    resolved, remaining = extract_routing_args(['--plan-id', 'task-routing-canonical', 'pr', 'view'])
    assert resolved is not None
    assert resolved.endswith('worktree-resolved'), f'Expected worktree path, got: {resolved!r}'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_plan_id_use_worktree_false_falls_back(monkeypatch):
    """--plan-id with use_worktree=false falls back to main checkout root."""
    import file_ops as _resolver_core
    from ci_base import extract_routing_args

    monkeypatch.setattr(_resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(False))
    monkeypatch.setattr(_resolver_core, 'cwd_checkout_root', lambda: '/tmp/main-checkout')
    resolved, remaining = extract_routing_args(['--plan-id', 'task-routing-canonical', 'pr', 'view'])
    assert resolved == '/tmp/main-checkout'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_both_flags_exits_with_mutually_exclusive_error(capsys):
    """Both --plan-id and --project-dir at the router → exit 2 + TOON error."""
    from ci_base import extract_routing_args

    with pytest.raises(SystemExit) as exc_info:
        extract_routing_args(
            [
                '--plan-id',
                'task-routing-canonical',
                '--project-dir',
                '/tmp/explicit',
                'pr',
                'view',
            ]
        )
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert 'mutually_exclusive_args' in captured.out


def test_extract_routing_args_router_level_plan_id_before_prepare_body_accepted(monkeypatch):
    """``--plan-id`` BEFORE a body-consumer subcommand is accepted at router level.

    Fix A (secondary guard): the guard rejects routing flags that appear AFTER
    the subcommand boundary. When ``--plan-id`` is placed BEFORE the subcommand
    token (router-level placement), the guard must NOT fire — the flag is
    consumed by the router, worktree resolution succeeds, and the remaining argv
    contains only the subcommand and its own arguments.

    This test specifically uses ``pr prepare-body`` — a subcommand that declares
    its own ``--plan-id`` argument via ``add_plan_id_arg``. The test demonstrates
    that router-level ``--plan-id`` placement is the correct calling convention
    even when the downstream subcommand also needs a ``--plan-id`` at its own
    argparse level.
    """
    import file_ops as _resolver_core
    from ci_base import extract_routing_args

    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(True, '/tmp/worktree-resolved')
    )
    resolved, remaining = extract_routing_args(['--plan-id', 'my-plan', 'pr', 'prepare-body'])
    assert resolved is not None
    assert resolved.endswith('worktree-resolved'), f'Expected worktree path, got: {resolved!r}'
    assert remaining == ['pr', 'prepare-body']


def test_extract_routing_args_plan_id_after_prepare_body_passes_through():
    """``--plan-id`` AFTER ``pr prepare-body`` passes through to the subcommand parser.

    Body-consumer subcommands (``pr prepare-body``, ``pr create``, ``issue create`` …)
    declare their own ``--plan-id`` argparse argument and consume the post-subcommand
    occurrence themselves. The positional guard MUST NOT reject this placement —
    rejecting it would break the documented invocation pattern for every body-
    consumer call site.

    The router returns ``resolved=None`` (no router-level routing flag supplied)
    and the unchanged argv so the subcommand argparse can consume ``--plan-id``.
    """
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert resolved is None
    assert remaining == ['pr', 'prepare-body', '--plan-id', 'my-plan']


def test_argparse_layer_plan_id_unaffected_by_routing_guard():
    """The positional routing guard does not interfere with ``build_parser`` argparse.

    Fix A (secondary guard) lives exclusively in ``extract_routing_args``. The
    argparse layer — used by provider scripts AFTER routing has been done — must
    still accept ``pr prepare-body --plan-id xxx`` when the tokens are passed
    directly to ``build_parser().parse_args()``.

    This test documents the separation of concerns: ``extract_routing_args``
    enforces the router-level placement rule; ``build_parser`` enforces the
    subcommand-level argument contract. A provider that has already stripped
    router-level flags via ``extract_routing_args`` can subsequently feed the
    remaining subcommand argv (which may include a subcommand-level ``--plan-id``)
    directly to its argparse parser without triggering the routing guard.
    """
    parser, _, _, _, _ = build_parser('test')
    # Direct argparse parse — no extract_routing_args in the call path.
    # The routing guard is absent here, so --plan-id at the subcommand level
    # is accepted by argparse normally.
    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'pr'
    assert args.pr_command == 'prepare-body'
    assert args.plan_id == 'my-plan'


def test_extract_routing_args_comments_stage_plan_id_passes_through(_reset_subcommand_cache):
    """``--plan-id`` AFTER the ``comments-stage`` token passes through to the subcommand.

    ``comments-stage`` declares its own ``--plan-id`` argument (for finding-store
    routing). The positional guard MUST NOT reject this placement — the subcommand
    parser consumes ``--plan-id`` directly from its own argv.

    Provider scripts register ``comments-stage`` via ``register_subcommands`` at
    import time; this test mirrors that pattern.
    """
    from ci_base import extract_routing_args

    register_subcommands({'comments-stage', 'fetch-comments'})

    resolved, remaining = extract_routing_args(
        ['comments-stage', '--pr-number', '123', '--plan-id', 'my-plan'],
    )
    assert resolved is None
    assert remaining == ['comments-stage', '--pr-number', '123', '--plan-id', 'my-plan']


def test_extract_routing_args_fetch_comments_plan_id_passes_through(_reset_subcommand_cache):
    """``--plan-id`` AFTER the ``fetch-comments`` token passes through to the subcommand.

    Same contract as ``comments-stage`` — the subcommand parser declares and
    consumes its own ``--plan-id`` argument; the router MUST NOT reject the
    post-subcommand placement.
    """
    from ci_base import extract_routing_args

    register_subcommands({'comments-stage', 'fetch-comments'})

    resolved, remaining = extract_routing_args(
        ['fetch-comments', '--pr', '5', '--plan-id', 'my-plan'],
    )
    assert resolved is None
    assert remaining == ['fetch-comments', '--pr', '5', '--plan-id', 'my-plan']


# =============================================================================
# Registration-driven subcommand boundary set — unit tests
# =============================================================================
#
# These tests cover the ``get_known_subcommands`` / ``register_subcommands``
# contract introduced to replace the literal ``_SUBCOMMAND_TOKENS`` frozenset.
# Each test uses the ``_reset_subcommand_cache`` fixture so the module-level
# cache is restored to its pre-test value after each case.


def test_get_known_subcommands_bootstraps_from_build_parser(_reset_subcommand_cache):
    """get_known_subcommands() must include EVERY top-level key from build_parser().

    The expected set is re-derived from the live parser rather than restated as a
    literal list with a hand-maintained count. A noun added to ``build_parser``
    then inherits this assertion automatically, where a literal (and its "registers
    four top-level subcommands" comment) would silently go one member short — the
    bootstrap could stop exposing a noun while every named assertion still passed.
    """
    parser, _pr_sub, _checks_sub, _issue_sub, _branch_sub = build_parser('test')
    declared: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            declared = set(action.choices)
            break

    assert declared, 'build_parser declared no top-level subcommands — the derivation is vacuous'
    assert declared <= get_known_subcommands()


def test_get_known_subcommands_returns_frozenset(_reset_subcommand_cache):
    """get_known_subcommands() must return a frozenset (immutable)."""
    tokens = get_known_subcommands()
    assert isinstance(tokens, frozenset)


def test_get_known_subcommands_cached_on_second_call(_reset_subcommand_cache):
    """get_known_subcommands() must return the same object on repeated calls (lazy cache)."""
    first = get_known_subcommands()
    second = get_known_subcommands()
    assert first is second


def test_register_subcommands_extends_known_set(_reset_subcommand_cache):
    """register_subcommands() must merge extra tokens into the registry."""
    before = get_known_subcommands()
    assert 'fetch-comments' not in before
    assert 'comments-stage' not in before

    register_subcommands({'fetch-comments', 'comments-stage'})

    after = get_known_subcommands()
    assert 'fetch-comments' in after
    assert 'comments-stage' in after
    # Existing parser-derived tokens must still be present.
    assert 'pr' in after
    assert 'checks' in after


def test_register_subcommands_idempotent(_reset_subcommand_cache):
    """Calling register_subcommands() twice with overlapping tokens is safe."""
    register_subcommands({'fetch-comments'})
    register_subcommands({'fetch-comments', 'comments-stage'})
    tokens = get_known_subcommands()
    assert 'fetch-comments' in tokens
    assert 'comments-stage' in tokens


def test_register_subcommands_does_not_remove_existing(_reset_subcommand_cache):
    """register_subcommands() must never shrink the existing token set."""
    base = get_known_subcommands()
    register_subcommands({'extra-token'})
    after = get_known_subcommands()
    # All original tokens still present.
    assert base.issubset(after)
    assert 'extra-token' in after


def test_split_at_subcommand_uses_registry(_reset_subcommand_cache):
    """_split_at_subcommand must use the live registry, not a stale literal."""
    from ci_base import _split_at_subcommand

    # Before registration, 'fetch-comments' is unknown; entire argv is prefix.
    pre, post = _split_at_subcommand(['--plan-id', 'p', 'fetch-comments', '--pr', '5'])
    assert post == []  # 'fetch-comments' not yet known

    # After registration, 'fetch-comments' splits the argv.
    register_subcommands({'fetch-comments'})
    pre2, post2 = _split_at_subcommand(['--plan-id', 'p', 'fetch-comments', '--pr', '5'])
    assert pre2 == ['--plan-id', 'p']
    assert post2 == ['fetch-comments', '--pr', '5']


# =============================================================================
# --error-style registration on checks wait / checks status
# =============================================================================
#
# The shared failure-path log-download hook (``enrich_failing_checks_with_logs``)
# is governed by an ``--error-style`` selector. That flag MUST be registered on
# both the ``checks wait`` and ``checks status`` subparsers so a caller can pick
# the per-build-system filter heuristic at invocation time. The default is
# ``generic`` and the choice set is restricted to maven|gradle|npm|generic.


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_registered_on_checks_subparsers(checks_command):
    """``--error-style`` must be accepted on both checks wait and checks status."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', checks_command, '--pr-number', '42', '--error-style', 'maven'])
    assert args.error_style == 'maven'


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_defaults_to_generic(checks_command):
    """When ``--error-style`` is omitted it defaults to ``generic`` on both subparsers."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', checks_command, '--pr-number', '42'])
    assert args.error_style == 'generic'


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
@pytest.mark.parametrize('style', ['maven', 'gradle', 'npm', 'generic'])
def test_error_style_accepts_every_valid_choice(checks_command, style):
    """Every member of the maven|gradle|npm|generic choice set is accepted."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', checks_command, '--pr-number', '42', '--error-style', style])
    assert args.error_style == style


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_rejects_unknown_value(checks_command):
    """An out-of-choice ``--error-style`` value must exit (argparse error)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['checks', checks_command, '--pr-number', '42', '--error-style', 'sbt'])


def test_add_error_style_arg_registers_default_generic():
    """add_error_style_arg directly registers ``--error-style`` defaulting to generic."""
    parser = argparse.ArgumentParser()
    ci_base.add_error_style_arg(parser)
    args = parser.parse_args([])
    assert args.error_style == 'generic'
    args = parser.parse_args(['--error-style', 'gradle'])
    assert args.error_style == 'gradle'


# =============================================================================
# enrich_failing_checks_with_logs — shared failure-path download+filter+store
# =============================================================================
#
# The hook iterates a list of failing-check entries and, for each, downloads the
# raw log via an injected fetcher, filters it, persists raw + filtered variants
# under the manage-ci-artifacts storage layout, and appends the plan-dir-relative
# ``log_file`` / ``filtered_log_file`` back onto the entry. The contract pinned
# below:
#
# - For >=2 entries it appends a DISTINCT log_file / filtered_log_file per entry,
#   slug-disambiguated, with NO collision even when two entries share a run_id.
# - It degrades gracefully PER ENTRY (empty path fields on the affected entry
#   only, never raising) when plan_id / run_id is absent or a fetch fails.
#
# Tests inject a stub raw-log fetcher and use the ``plan_context`` fixture's
# isolated plan dir so no live CI access is required.


def test_enrich_appends_distinct_paths_per_entry(plan_context):
    """Two failing checks (distinct run_ids) each gain their own raw + filtered paths."""
    plan_id = 'enrich-distinct-runs'
    entries = [
        _failing_check('verify / verify', '101'),
        _failing_check('build (3.12)', '102'),
    ]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom for run {run_id}\ntrailing line\n'

    result = enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    # The hook mutates in place and returns the same list.
    assert result is entries
    log_files = [e['log_file'] for e in entries]
    filtered_files = [e['filtered_log_file'] for e in entries]
    # Every entry got a non-empty, distinct pair.
    assert all(log_files), log_files
    assert all(filtered_files), filtered_files
    assert len(set(log_files)) == 2, f'log_file paths collided: {log_files}'
    assert len(set(filtered_files)) == 2, f'filtered_log_file paths collided: {filtered_files}'
    # Paths reflect each check's slug.
    assert any('verify-verify' in p for p in log_files)
    assert any('build-3-12' in p for p in log_files)


def test_enrich_no_collision_when_two_checks_share_run_id(plan_context):
    """Two failing checks sharing ONE run_id must get distinctly-slugged, non-colliding files."""
    plan_id = 'enrich-shared-run-id'
    entries = [
        _failing_check('verify / verify', '500'),
        _failing_check('build (3.12)', '500'),
    ]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR failure log for {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    log_files = [e['log_file'] for e in entries]
    filtered_files = [e['filtered_log_file'] for e in entries]
    assert all(log_files), log_files
    assert all(filtered_files), filtered_files
    # The defining assertion: same run_id, but the slug disambiguates so the two
    # entries never write to the same on-disk path.
    assert log_files[0] != log_files[1], f'shared run_id collided: {log_files}'
    assert filtered_files[0] != filtered_files[1], f'shared run_id filtered paths collided: {filtered_files}'
    # Both raw files actually exist on disk (no overwrite of one by the other).
    # persist() expresses paths relative to the anchor (get_base_dir().parent);
    # in fixture mode get_base_dir() == fixture_dir, so the anchor is its parent.
    plan_context.plan_dir_for(plan_id)  # ensure the plan dir exists
    base = plan_context.fixture_dir.parent
    for rel in log_files:
        assert (base / rel).is_file(), f'expected raw log on disk: {rel}'
    for rel in filtered_files:
        assert (base / rel).is_file(), f'expected filtered log on disk: {rel}'


def test_enrich_degrades_when_plan_id_absent():
    """plan_id=None makes the hook a no-op enrichment — empty path fields, no raise."""
    entries = [_failing_check('verify / verify', '101')]

    def fetcher(run_id: str, job_id: str = '') -> str:  # pragma: no cover - must not be called
        raise AssertionError('fetcher must not run when plan_id is None')

    result = enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=None,
    )
    assert result is entries
    assert entries[0]['log_file'] == ''
    assert entries[0]['filtered_log_file'] == ''


def test_enrich_degrades_per_entry_when_run_id_missing(plan_context):
    """An entry with no run_id keeps empty path fields; siblings still enriched."""
    plan_id = 'enrich-missing-run-id'
    good = _failing_check('verify / verify', '900')
    bad = _failing_check('build (3.12)', '')  # empty run_id
    entries = [good, bad]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    # The healthy entry was enriched.
    assert good['log_file']
    assert good['filtered_log_file']
    # The run_id-less entry degraded to empty path fields — never raised.
    assert bad['log_file'] == ''
    assert bad['filtered_log_file'] == ''


def test_enrich_degrades_per_entry_when_fetch_fails(plan_context):
    """A fetch failure on one entry must not abort enrichment of the others, nor raise."""
    plan_id = 'enrich-fetch-fails'
    first = _failing_check('verify / verify', '601')
    second = _failing_check('build (3.12)', '602')
    entries = [first, second]

    def fetcher(run_id: str, job_id: str = '') -> str:
        if run_id == '601':
            raise RuntimeError('network down')
        return f'ERROR ok {run_id}\n'

    # Must not raise despite the per-entry fetch failure.
    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    # The failing-fetch entry degraded to empty path fields.
    assert first['log_file'] == ''
    assert first['filtered_log_file'] == ''
    # The healthy entry was still enriched.
    assert second['log_file']
    assert second['filtered_log_file']


def test_enrich_degrades_per_entry_when_fetch_returns_none(plan_context):
    """A fetcher returning None for an entry leaves that entry's path fields empty."""
    plan_id = 'enrich-fetch-none'
    first = _failing_check('verify / verify', '701')
    second = _failing_check('build (3.12)', '702')
    entries = [first, second]

    def fetcher(run_id: str, job_id: str = '') -> str | None:
        if run_id == '701':
            return None
        return f'ERROR ok {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    assert first['log_file'] == ''
    assert first['filtered_log_file'] == ''
    assert second['log_file']
    assert second['filtered_log_file']


def test_enrich_records_error_style_on_each_entry(plan_context):
    """The chosen error_style is stamped onto every entry (default generic)."""
    plan_id = 'enrich-error-style'
    entries = [_failing_check('verify / verify', '111')]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
        error_style='maven',
    )
    assert entries[0]['error_style'] == 'maven'


def test_enrich_passes_job_id_to_fetcher(plan_context):
    """The entry's job_id is forwarded as the fetcher's second positional arg.

    Reusable-workflow callers populate ``job_id`` on the failing-check entry;
    the shared hook must thread it through to ``raw_log_fetcher`` so the
    GitHub fetcher can target the nested called job.
    """
    plan_id = 'enrich-job-id-forward'
    entry = _failing_check('verify / verify', '321')
    entry['job_id'] = '654'
    entries = [entry]

    captured: list[tuple[str, str]] = []

    def fetcher(run_id: str, job_id: str = '') -> str:
        captured.append((run_id, job_id))
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    assert captured == [('321', '654')]


def test_enrich_passes_empty_job_id_when_absent(plan_context):
    """When the entry carries no job_id, the fetcher receives an empty string."""
    plan_id = 'enrich-job-id-absent'
    entries = [_failing_check('build (3.12)', '322')]  # no job_id key

    captured: list[tuple[str, str]] = []

    def fetcher(run_id: str, job_id: str = '') -> str:
        captured.append((run_id, job_id))
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    assert captured == [('322', '')]


# =============================================================================
# repo merge-queue — 3-level parser tree + dispatch routing
# =============================================================================
#
# `repo merge-queue {probe|enable}` is a NEW top-level subcommand grouping a
# `merge-queue` noun with two sub-verbs. dispatch() keys the repo branch on the
# three-level path (repo, merge-queue, args.merge_queue_command). The shared
# eligibility vocabulary is exposed as module-level constants both providers
# consume.


def test_build_parser_accepts_repo_merge_queue_probe():
    """`repo merge-queue probe` round-trips to the three-level namespace."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['repo', 'merge-queue', 'probe'])
    assert args.command == 'repo'
    assert args.repo_command == 'merge-queue'
    assert args.merge_queue_command == 'probe'


def test_build_parser_accepts_repo_merge_queue_enable():
    """`repo merge-queue enable` round-trips (no args — enable is idempotent)."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['repo', 'merge-queue', 'enable'])
    assert args.command == 'repo'
    assert args.repo_command == 'merge-queue'
    assert args.merge_queue_command == 'enable'


def test_build_parser_repo_requires_merge_queue_noun():
    """`repo` with no noun must exit (subparser is required)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['repo'])


def test_build_parser_repo_merge_queue_requires_sub_verb():
    """`repo merge-queue` with no sub-verb must exit (subparser is required)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['repo', 'merge-queue'])


def test_build_parser_repo_merge_queue_rejects_unknown_sub_verb():
    """An out-of-choice sub-verb under merge-queue must exit."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['repo', 'merge-queue', 'disable'])


def test_get_known_subcommands_includes_repo(_reset_subcommand_cache):
    """The registration-driven boundary set must include the new `repo` token."""
    tokens = get_known_subcommands()
    assert 'repo' in tokens


def test_dispatch_routes_repo_merge_queue_probe():
    """dispatch() maps `repo merge-queue probe` to the 3-tuple handler key."""
    from ci_base import dispatch

    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['repo', 'merge-queue', 'probe'])

    called: list[str] = []

    def probe_handler(_args):
        called.append('probe')
        return {'status': 'success', 'operation': 'repo_merge_queue_probe'}

    handlers = {('repo', 'merge-queue', 'probe'): probe_handler}
    result = dispatch(args, handlers, parser)
    assert called == ['probe']
    assert result['operation'] == 'repo_merge_queue_probe'


def test_dispatch_routes_repo_merge_queue_enable():
    """dispatch() maps `repo merge-queue enable` to the 3-tuple handler key."""
    from ci_base import dispatch

    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['repo', 'merge-queue', 'enable'])

    def enable_handler(_args):
        return {'status': 'success', 'operation': 'repo_merge_queue_enable'}

    handlers = {('repo', 'merge-queue', 'enable'): enable_handler}
    result = dispatch(args, handlers, parser)
    assert result['operation'] == 'repo_merge_queue_enable'


def test_dispatch_repo_unknown_sub_verb_returns_error():
    """dispatch() returns an error dict when no handler is registered for the key."""
    from ci_base import dispatch

    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['repo', 'merge-queue', 'probe'])
    # Empty handler map → no match → error dict (not a raise).
    result = dispatch(args, {}, parser)
    assert result['status'] == 'error'


def test_merge_queue_eligibility_vocabulary_constants():
    """The shared eligibility discriminators are exposed as module-level constants."""
    assert ci_base.MERGE_QUEUE_ELIGIBLE_CONFIGURED == 'eligible_configured'
    assert ci_base.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED == 'eligible_unconfigured'
    assert ci_base.MERGE_QUEUE_INELIGIBLE == 'ineligible'
    assert ci_base.MERGE_QUEUE_UNSUPPORTED == 'unsupported'


def test_merge_queue_eligible_states_set():
    """MERGE_QUEUE_ELIGIBLE_STATES is exactly the two eligible-to-enable discriminators."""
    assert ci_base.MERGE_QUEUE_ELIGIBLE_STATES == frozenset({'eligible_configured', 'eligible_unconfigured'})
    # The ineligible / unsupported values are NOT eligible-to-enable.
    assert ci_base.MERGE_QUEUE_INELIGIBLE not in ci_base.MERGE_QUEUE_ELIGIBLE_STATES
    assert ci_base.MERGE_QUEUE_UNSUPPORTED not in ci_base.MERGE_QUEUE_ELIGIBLE_STATES


# =============================================================================
# checks wait — opt-in adaptive ci:wait budget
# =============================================================================
#
# ``checks wait --adaptive`` wires the branch-cleanup / verification-feedback CI
# waits into the SAME adaptive ci:wait ratchet ci_complete_precondition already
# drives (manage-run-config timeout get/set --command ci:wait). The flag is
# opt-in so ci_complete_precondition (which manages its own read+record around a
# non-adaptive wait) never double-records.
#
# The seed/record are exercised at the ``_run_checks_wait`` orchestration seam
# with stubbed timeout get/set functions and a stub wait handler — no live
# run-configuration.json and no live CI provider.


def test_run_checks_wait_explicit_timeout_not_reseeded_but_still_records(monkeypatch):
    """An explicit --timeout wins over the seed, yet the adaptive record still fires."""
    monkeypatch.setattr(
        ci_base,
        '_adaptive_wait_timeout_get',
        lambda _d: (_ for _ in ()).throw(AssertionError('seed must not run when --timeout is explicit')),
    )
    recorded: list[int] = []
    monkeypatch.setattr(ci_base, '_adaptive_wait_timeout_set', lambda d: recorded.append(d))

    seen_timeout: list[int] = []

    def handler(args):
        seen_timeout.append(args.timeout)
        return {'status': 'success', 'final_status': 'success', 'duration_sec': 200}

    ci_base._run_checks_wait(_mq_wait_ns(adaptive=True, timeout=900), handler)

    assert seen_timeout == [900]  # explicit ceiling preserved, no re-seed
    assert recorded == [200]  # observed duration still teaches the budget


def test_ci_router_flags_are_derived_from_the_routing_contract():
    """``CI_ROUTER_FLAGS`` is the router's own set, not a hand-kept copy.

    The placement diagnostic names the flags it believes are router-scoped. When
    that set is restated rather than derived, a routing change makes the
    diagnostic name a flag the router no longer consumes — a confidently wrong
    error message, which is worse than none. Identity, not equality: a copy that
    happens to match today would pass an equality check and drift tomorrow.
    """
    import resolve_project_dir
    from ci_base import CI_ROUTER_FLAGS

    assert CI_ROUTER_FLAGS is resolve_project_dir.ROUTER_FLAGS
    assert resolve_project_dir.ROUTER_PLAN_ID_FLAG in CI_ROUTER_FLAGS
    assert resolve_project_dir.ROUTER_PROJECT_DIR_FLAG in CI_ROUTER_FLAGS
