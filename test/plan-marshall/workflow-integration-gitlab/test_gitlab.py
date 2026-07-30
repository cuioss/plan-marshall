#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for gitlab.py script.

Tests command structure and argument parsing.
Note: Actual glab CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-gitlab', 'gitlab_ops.py')


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'pr' in result.stdout
    assert 'checks' in result.stdout
    assert 'issue' in result.stdout


def test_pr_subcommand_help():
    """Test pr subcommand help."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    assert result.success, f'pr --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'view' in result.stdout
    assert 'reply' in result.stdout
    assert 'resolve-thread' in result.stdout
    assert 'thread-reply' in result.stdout
    assert 'merge' in result.stdout
    assert 'auto-merge' in result.stdout
    assert 'close' in result.stdout
    assert 'ready' in result.stdout
    assert 'edit' in result.stdout
    assert 'reviews' in result.stdout
    assert 'list' in result.stdout


def test_ci_subcommand_help():
    """Test checks subcommand help."""
    result = run_script(SCRIPT_PATH, 'checks', '--help')
    assert result.success, f'checks --help failed: {result.stderr}'
    assert 'status' in result.stdout
    assert 'wait' in result.stdout
    assert 'rerun' in result.stdout
    assert 'logs' in result.stdout


def test_issue_subcommand_help():
    """Test issue subcommand help."""
    result = run_script(SCRIPT_PATH, 'issue', '--help')
    assert result.success, f'issue --help failed: {result.stderr}'
    assert 'create' in result.stdout
    assert 'view' in result.stdout
    assert 'close' in result.stdout


def test_pr_create_help():
    """Test pr create help shows the ONE body source: the plan-bound store.

    Mirrors the GitHub provider's assertion exactly — both providers share the
    ``add_pr_create_args`` registrar, so a divergence here would mean one
    provider's advertised surface drifted from the abstraction.
    """
    result = run_script(SCRIPT_PATH, 'pr', 'create', '--help')
    assert result.success, f'pr create --help failed: {result.stderr}'
    assert '--title' in result.stdout
    assert '--plan-id' in result.stdout
    assert '--body-file' not in result.stdout


def test_pr_create_missing_required():
    """Test pr create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'create')
    assert not result.success, 'Expected failure without --title'
    assert 'title' in result.stderr.lower() or 'required' in result.stderr.lower()


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


def test_pr_reviews_missing_required():
    """Test pr reviews fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'pr', 'reviews')
    assert not result.success, 'Expected failure without --pr-number'


def test_ci_status_missing_required():
    """Test checks status emits a structured error when neither --pr-number nor --head is supplied."""
    result = run_script(SCRIPT_PATH, 'checks', 'status')
    combined = (result.stdout + result.stderr).lower()
    assert 'pr-number' in combined or 'head' in combined or 'auth' in combined, (
        f'Expected pr-number/head/auth in output, got: {combined}'
    )


def test_ci_wait_missing_required():
    """Test checks wait fails without pr-number."""
    result = run_script(SCRIPT_PATH, 'checks', 'wait')
    assert not result.success, 'Expected failure without --pr-number'


def test_issue_create_missing_required():
    """Test issue create fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'create')
    assert not result.success, 'Expected failure without --title'


def test_pr_view_help():
    """Test pr view help works."""
    result = run_script(SCRIPT_PATH, 'pr', 'view', '--help')
    assert result.success, f'pr view --help failed: {result.stderr}'


def test_pr_reply_help():
    """Test pr reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply', '--help')
    assert result.success, f'pr reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--plan-id' in result.stdout
    assert '--body' not in result.stdout


def test_pr_reply_missing_required():
    """Test pr reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_resolve_thread_help():
    """Test pr resolve-thread help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread', '--help')
    assert result.success, f'pr resolve-thread --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--thread-id' in result.stdout


def test_pr_resolve_thread_missing_required():
    """Test pr resolve-thread fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'resolve-thread')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_thread_reply_help():
    """Test pr thread-reply help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply', '--help')
    assert result.success, f'pr thread-reply --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--thread-id' in result.stdout
    assert '--plan-id' in result.stdout
    assert '--body' not in result.stdout


def test_pr_thread_reply_missing_required():
    """Test pr thread-reply fails without required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'thread-reply')
    assert not result.success, 'Expected failure without --pr-number'


def test_pr_merge_help():
    """Test pr merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'merge', '--help')
    assert result.success, f'pr merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_auto_merge_help():
    """Test pr auto-merge help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'auto-merge', '--help')
    assert result.success, f'pr auto-merge --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_close_help():
    """Test pr close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'close', '--help')
    assert result.success, f'pr close --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_ready_help():
    """Test pr ready help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'ready', '--help')
    assert result.success, f'pr ready --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout


def test_pr_edit_help():
    """Test pr edit help shows arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'edit', '--help')
    assert result.success, f'pr edit --help failed: {result.stderr}'
    assert '--pr-number' in result.stdout
    assert '--title' in result.stdout


def test_ci_rerun_help():
    """Test checks rerun help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'checks', 'rerun', '--help')
    assert result.success, f'checks rerun --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_ci_logs_help():
    """Test checks logs help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'checks', 'logs', '--help')
    assert result.success, f'checks logs --help failed: {result.stderr}'
    assert '--run-id' in result.stdout


def test_issue_close_help():
    """Test issue close help shows required arguments."""
    result = run_script(SCRIPT_PATH, 'issue', 'close', '--help')
    assert result.success, f'issue close --help failed: {result.stderr}'
    assert '--issue' in result.stdout


def test_pr_list_help():
    """Test pr list help shows optional arguments."""
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success, f'pr list --help failed: {result.stderr}'
    assert '--head' in result.stdout
    assert '--state' in result.stdout


def test_pr_list_state_choices():
    """Test pr list accepts valid state choices."""
    result = run_script(SCRIPT_PATH, 'pr', 'list', '--help')
    assert result.success
    assert 'open' in result.stdout


def test_no_subcommand():
    """Test that script requires a subcommand."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, 'Expected failure without subcommand'


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
