#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for gitlab.py script.

Tests command structure and argument parsing.
Note: Actual glab CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import pytest

from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-gitlab', 'gitlab_ops.py')


# ---------------------------------------------------------------------------
# CLI plumbing. The subprocess layer proves the entry point wires up — argv
# parses, the declared flags are advertised, the declared exit code is used.
# The handlers' behaviour is asserted in-process elsewhere in this suite.
# ---------------------------------------------------------------------------

# (argv, substrings the help text MUST advertise, substrings it must NOT)
_HELP_SURFACE = [
    ((), ('pr', 'checks', 'issue'), ()),
    (
        ('pr',),
        (
            'create', 'view', 'reply', 'resolve-thread', 'thread-reply', 'merge',
            'auto-merge', 'close', 'ready', 'edit', 'reviews', 'list',
        ),
        (),
    ),
    (('checks',), ('status', 'wait', 'rerun', 'logs'), ()),
    (('issue',), ('create', 'view', 'close'), ()),
    # Mirrors the GitHub provider's assertion exactly — both providers share the
    # ``add_pr_create_args`` registrar, so a divergence here would mean one
    # provider's advertised surface drifted from the abstraction.
    (('pr', 'create'), ('--title', '--plan-id'), ('--body-file',)),
    (('pr', 'view'), (), ()),
    (('pr', 'reply'), ('--pr-number', '--plan-id'), ('--body',)),
    (('pr', 'resolve-thread'), ('--pr-number', '--thread-id'), ()),
    (('pr', 'thread-reply'), ('--pr-number', '--thread-id', '--plan-id'), ('--body',)),
    (('pr', 'merge'), ('--pr-number',), ()),
    (('pr', 'auto-merge'), ('--pr-number',), ()),
    (('pr', 'close'), ('--pr-number',), ()),
    (('pr', 'ready'), ('--pr-number',), ()),
    (('pr', 'edit'), ('--pr-number', '--title'), ()),
    (('checks', 'rerun'), ('--run-id',), ()),
    (('checks', 'logs'), ('--run-id',), ()),
    (('issue', 'close'), ('--issue',), ()),
    (('pr', 'list'), ('--head', '--state'), ()),
    # --help renders the choices, so the advertised default doubles as the
    # state-choices assertion.
    (('pr', 'list'), ('open',), ()),
]


@pytest.mark.parametrize(
    ('argv', 'advertised', 'absent'),
    _HELP_SURFACE,
    ids=[
        'root', 'pr', 'checks', 'issue', 'pr-create', 'pr-view', 'pr-reply',
        'pr-resolve-thread', 'pr-thread-reply', 'pr-merge', 'pr-auto-merge',
        'pr-close', 'pr-ready', 'pr-edit', 'checks-rerun', 'checks-logs',
        'issue-close', 'pr-list', 'pr-list-state-default',
    ],
)
def test_help_advertises_the_declared_surface(argv, advertised, absent):
    """``--help`` exits zero and advertises exactly the flags a caller drives it with."""
    result = run_script(SCRIPT_PATH, *argv, '--help')
    assert result.success, f'{" ".join(argv)} --help failed: {result.stderr}'
    for token in advertised:
        assert token in result.stdout, f'{token!r} missing from {" ".join(argv)} --help'
    for token in absent:
        assert token not in result.stdout, f'{token!r} still advertised by {" ".join(argv)} --help'


# (argv, a substring the diagnostic must name — None when only the exit code is pinned)
_MISSING_REQUIRED = [
    (('pr', 'create'), 'title'),
    (('pr', 'reviews'), None),
    (('pr', 'reply'), None),
    (('pr', 'resolve-thread'), None),
    (('pr', 'thread-reply'), None),
    (('checks', 'wait'), None),
    (('issue', 'create'), None),
    ((), None),
]


@pytest.mark.parametrize(
    ('argv', 'names'),
    _MISSING_REQUIRED,
    ids=[
        'pr-create', 'pr-reviews', 'pr-reply', 'pr-resolve-thread',
        'pr-thread-reply', 'checks-wait', 'issue-create', 'no-subcommand',
    ],
)
def test_missing_required_argument_is_a_nonzero_exit(argv, names):
    """A subcommand invoked without its required flags exits non-zero."""
    result = run_script(SCRIPT_PATH, *argv)
    assert not result.success, f'{" ".join(argv) or "<no subcommand>"} unexpectedly succeeded'
    if names:
        combined = result.stderr.lower()
        assert names in combined or 'required' in combined, combined


def test_either_or_flags_missing_emits_a_structured_error():
    """``checks status`` with neither ``--pr-number`` nor ``--head`` is reported, not ignored.

    The parser accepts the bare call and the HANDLER rejects it, so the
    diagnostic — not the exit code — is the contract. Auth runs first, so its
    error is also admissible.
    """
    result = run_script(SCRIPT_PATH, 'checks', 'status')
    combined = (result.stdout + result.stderr).lower()
    assert 'pr-number' in combined or 'head' in combined or 'auth' in combined, (
        f'Expected pr-number/head/auth in output, got: {combined}'
    )


def test_pr_create_handler_has_a_single_body_source():
    """Provider parity: one store call, and no surviving ``body_file`` path.

    The GitLab half of the symmetric residue this deliverable owes; the sibling
    assertion lives in the GitHub suite and is deliberately identical. The two
    ``cmd_pr_create`` handlers are kept in lock-step so the CI abstraction
    presents one contract per verb — an asymmetry here is exactly the drift the
    pair exists to catch.

    Asserted structurally over the handler's AST rather than behaviourally: a
    behavioural test can only observe the branch that RUNS, so a dormant
    ``body_file`` branch reachable from a direct-Namespace caller would stay
    invisible to it.
    """
    import ast  # noqa: PLC0415

    from conftest import get_scripts_dir  # noqa: PLC0415

    source = (
        get_scripts_dir('plan-marshall', 'workflow-integration-gitlab') / 'gitlab_ops.py'
    ).read_text(encoding='utf-8')
    handler = next(
        (
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == 'cmd_pr_create'
        ),
        None,
    )
    assert handler is not None, 'cmd_pr_create not found in gitlab_ops.py'

    called = {
        node.func.id
        for node in ast.walk(handler)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert 'read_and_consume_body' in called, (
        'gitlab_ops.py::cmd_pr_create no longer resolves the body through the store'
    )

    # ``body_file`` can survive as a local name, as an attribute access
    # (``args.body_file`` — the dormant guard this test's docstring cites,
    # still reachable from a direct-Namespace caller), OR as the string key of
    # a ``getattr(args, "body_file", None)`` read — check all three spellings.
    identifiers = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
    identifiers |= {node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)}
    literals = {
        node.value
        for node in ast.walk(handler)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert 'body_file' not in identifiers, (
        'gitlab_ops.py::cmd_pr_create retains a body_file local or attribute access'
    )
    assert 'body_file' not in literals, 'gitlab_ops.py::cmd_pr_create retains a body_file lookup'


def test_pr_comments_no_body_truncation():
    """Regression: comment body must not be truncated (was [:100])."""
    with open(SCRIPT_PATH) as f:
        source = f.read()
    # The TOON output section for pr_comments should normalize but not truncate
    assert "['body'].replace('\\t', ' ').replace('\\n', ' ')[:100]" not in source, (
        'Comment body is still truncated at 100 chars — remove [:100]'
    )


def test_pr_comments_kind_inline_vs_issue_comment(monkeypatch):
    """New: GitLab discussions are classified into the unified comment schema
    with kind=inline when a diff position is present and kind=issue_comment
    otherwise. GitLab has no equivalent of GitHub's review_body kind."""
    import argparse

    import gitlab_ops

    discussions_payload = [
        {
            'id': 'disc-inline',
            'notes': [
                {
                    'id': 1001,
                    'system': False,
                    'author': {'username': 'reviewer'},
                    'body': 'diff-anchored feedback',
                    'created_at': '2026-04-14T00:00:00Z',
                    'resolved': False,
                    'position': {
                        'new_path': 'src/file.py',
                        'old_path': 'src/file.py',
                        'new_line': 42,
                        'old_line': 40,
                    },
                }
            ],
        },
        {
            'id': 'disc-issue',
            'notes': [
                {
                    'id': 1002,
                    'system': False,
                    'author': {'username': 'commenter'},
                    'body': 'overall comment without position',
                    'created_at': '2026-04-14T00:05:00Z',
                    'resolved': False,
                    'position': None,
                }
            ],
        },
        {
            'id': 'disc-system',
            'notes': [
                {
                    'id': 1003,
                    'system': True,
                    'author': {'username': 'ghost'},
                    'body': 'assigned to foo',
                    'created_at': '2026-04-14T00:06:00Z',
                    'resolved': False,
                }
            ],
        },
    ]

    def fake_check_auth():
        return True, ''

    def fake_get_project_path():
        return 'group/project'

    def fake_run_api(endpoint: str):
        return 0, discussions_payload, ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', fake_check_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', fake_get_project_path)
    monkeypatch.setattr(gitlab_ops, 'run_api', fake_run_api)

    ns = argparse.Namespace(pr_number=7, unresolved_only=False)
    result = gitlab_ops.cmd_pr_comments(ns)

    assert result['status'] == 'success', result
    # System note must be filtered out, leaving exactly two entries
    assert result['total'] == 2
    by_id = {c['id']: c for c in result['comments']}

    inline = by_id['1001']
    assert inline['kind'] == 'inline'
    assert inline['path'] == 'src/file.py'
    assert inline['line'] == 42
    assert inline['thread_id'] == 'disc-inline'

    issue = by_id['1002']
    assert issue['kind'] == 'issue_comment'
    assert issue['path'] == ''
    assert issue['line'] == 0
    assert issue['thread_id'] == 'disc-issue'

    # Unified schema: no GitLab-side review_body kind
    kinds = {c['kind'] for c in result['comments']}
    assert 'review_body' not in kinds
