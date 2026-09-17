"""Tests for github.py script.

Tests command structure and argument parsing.
Note: Actual gh CLI operations require authentication and network.
These tests focus on the script interface, not live operations.
"""
import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_ops.py')
_HELP_SURFACE = [
    ((), ('pr', 'checks', 'issue'), ()),
    (
        ('pr',),
        (
            'create',
            'view',
            'reply',
            'resolve-thread',
            'thread-reply',
            'merge',
            'auto-merge',
            'close',
            'ready',
            'edit',
            'reviews',
            'list',
        ),
        (),
    ),
    (('issue',), ('create', 'view', 'close'), ()),
    (('checks',), ('status', 'wait', 'rerun', 'logs'), ()),
    # The plan-bound store is the ONE body source: a retired --body-file must be
    # gone from the advertised surface, since help text is what a caller reads to
    # decide how to supply a body. The legacy inline --body is asserted absent at
    # the parser level by test_ci_base.py.
    (('pr', 'create'), ('--title', '--plan-id'), ('--body-file',)),
    (('pr', 'view'), (), ()),
    (('pr', 'reply'), ('--pr-number', '--plan-id'), ('--body',)),
    (('pr', 'resolve-thread'), ('--thread-id',), ()),
    (('pr', 'thread-reply'), ('--pr-number', '--thread-id', '--plan-id'), ('--body',)),
    (('pr', 'merge'), ('--pr-number',), ()),
    (('pr', 'comments'), ('--pr-number',), ()),
    (('pr', 'auto-merge'), ('--pr-number',), ()),
    (('pr', 'close'), ('--pr-number',), ()),
    (('pr', 'ready'), ('--pr-number',), ()),
    (('pr', 'edit'), ('--pr-number', '--title'), ()),
    (('pr', 'list'), ('--head', '--state', '--limit'), ()),
    # --help renders the choices, so the advertised default doubles as the
    # state-choices assertion.
    (('pr', 'list'), ('open',), ()),
    (('checks', 'rerun'), ('--run-id',), ()),
    (('checks', 'logs'), ('--run-id',), ()),
    (('issue', 'close'), ('--issue',), ()),
]
_MISSING_REQUIRED = [
    (('pr', 'create'), 'title'),
    (('pr', 'reviews'), None),
    (('pr', 'reply'), None),
    (('pr', 'resolve-thread'), None),
    (('pr', 'thread-reply'), None),
    (('checks', 'wait'), None),
    (('checks', 'rerun'), None),
    (('issue', 'create'), None),
    ((), None),
]
_STRUCTURED_REFUSAL = [(('checks', 'status'),), (('pr', 'merge'),)]
def _assert_single_body_source(bundle: str, skill: str, script: str) -> None:
    """Assert ``cmd_pr_create`` in the named script has exactly one body source."""
    import ast  # local import: only this structural check needs it

    from conftest import get_scripts_dir  # local import: only this structural check needs it

    source = (get_scripts_dir(bundle, skill) / script).read_text(encoding='utf-8')
    handler = next(
        (
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == 'cmd_pr_create'
        ),
        None,
    )
    assert handler is not None, f'cmd_pr_create not found in {script}'

    called = {
        node.func.id for node in ast.walk(handler) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert 'read_and_consume_body' in called, f'{script}::cmd_pr_create no longer resolves the body through the store'

    # ``body_file`` can survive as an attribute/local name, as an attribute
    # access (``args.body_file`` — the dormant ``if args.body_file:`` guard
    # this assertion exists to catch, still reachable from a direct-Namespace
    # caller), OR as the string key of a ``getattr(args, "body_file", None)``
    # read — check all three spellings.
    identifiers = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
    identifiers |= {node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)}
    literals = {
        node.value for node in ast.walk(handler) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert 'body_file' not in identifiers, f'{script}::cmd_pr_create retains a body_file local or attribute access'
    assert 'body_file' not in literals, f'{script}::cmd_pr_create retains a body_file lookup'


@pytest.mark.parametrize(
    ('argv', 'names'),
    _MISSING_REQUIRED,
    ids=[
        'pr-create',
        'pr-reviews',
        'pr-reply',
        'pr-resolve-thread',
        'pr-thread-reply',
        'checks-wait',
        'checks-rerun',
        'issue-create',
        'no-subcommand',
    ],
)
def test_missing_required_argument_is_a_nonzero_exit(argv, names):
    """A subcommand invoked without its required flags exits non-zero."""
    result = run_script(SCRIPT_PATH, *argv)
    assert not result.success, f'{" ".join(argv) or "<no subcommand>"} unexpectedly succeeded'
    if names:
        combined = result.stderr.lower()
        assert names in combined or 'required' in combined, combined
def test_pr_create_handler_has_a_single_body_source():
    """Provider parity: one store call, and no surviving ``body_file`` path.

    The symmetric residue this deliverable owes. Both providers' ``cmd_pr_create``
    handlers must resolve the body through the SAME store call and retain no
    ``body_file`` branch — the sibling assertion lives in the GitLab suite and is
    deliberately identical, because the two handlers are kept in lock-step so the
    CI abstraction presents one contract per verb.

    Asserted structurally over the handler's AST rather than behaviourally: a
    behavioural test can only observe the branch that RUNS, so a dormant
    ``body_file`` branch reachable from a direct-Namespace caller would stay
    invisible to it.
    """
    _assert_single_body_source('plan-marshall', 'workflow-integration-github', '_github_pr.py')
