#!/usr/bin/env python3
"""Comprehensive unit tests for ``_build_cli.py`` and the four-state
``--plan-id`` / ``--project-dir`` routing helper it integrates.

Covers:

* :func:`_build_cli.add_project_dir_arg` — registers the routing pair
  on every Bucket B build subparser (run, parse, coverage-report,
  check-warnings).
* :func:`_build_cli.build_main` — dispatches to the resolver before the
  selected handler reads ``args.project_dir``, so all Bucket B build
  scripts (maven, gradle, npm, python_build) inherit the contract.
* :func:`resolve_project_dir.resolve_project_dir` — the canonical
  four-state contract:

  - ``--plan-id X`` only, ``use_worktree=true`` → worktree path
  - ``--plan-id X`` only, ``use_worktree=false`` → main checkout
  - ``--project-dir Y`` only → ``Y`` (verbatim, absolutised)
  - both → ``MutuallyExclusiveArgsError``
  - neither → main checkout

The resolver tests are exercised at the library level (no subprocess)
because per-build-script tests (``test_python_build``, ``test_maven``,
``test_gradle``, ``test_npm``) only pin the parser surface and the
subprocess-level both-supplied error path. Centralising the deep
behaviour here avoids 4× duplication.
"""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

# Cross-skill imports — PYTHONPATH is configured by the root conftest.
from _build_cli import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_parse_subparser,
    add_project_dir_arg,
    add_run_subparser,
    build_main,
    register_standard_subparsers,
)
from _resolve_project_dir_fixtures import (  # type: ignore[import-not-found]
    CANONICAL_PLAN_ID,
    CANONICAL_PROJECT_DIR,
    CANONICAL_WORKTREE,
    patch_main_checkout_root,
    patch_query_worktree_path,
)

# =============================================================================
# add_project_dir_arg — registers --project-dir AND --plan-id
# =============================================================================


def test_add_project_dir_arg_registers_both_flags():
    """The helper attaches BOTH --project-dir and --plan-id to a parser."""
    parser = argparse.ArgumentParser()
    add_project_dir_arg(parser)

    # Default values match the canonical contract: project_dir='.' so
    # the resolver detects "user did not pass --project-dir";
    # plan_id=None so the resolver detects absence.
    args = parser.parse_args([])
    assert args.project_dir == '.'
    assert args.plan_id is None


def test_add_project_dir_arg_accepts_plan_id():
    parser = argparse.ArgumentParser()
    add_project_dir_arg(parser)
    args = parser.parse_args(['--plan-id', CANONICAL_PLAN_ID])
    assert args.plan_id == CANONICAL_PLAN_ID
    assert args.project_dir == '.'


def test_add_project_dir_arg_accepts_project_dir():
    parser = argparse.ArgumentParser()
    add_project_dir_arg(parser)
    args = parser.parse_args(['--project-dir', CANONICAL_PROJECT_DIR])
    assert args.project_dir == CANONICAL_PROJECT_DIR
    assert args.plan_id is None


def test_add_project_dir_arg_accepts_both_at_argparse_level():
    """argparse itself does NOT reject the both-supplied case.

    The error fires later, inside ``build_main`` via ``resolve_project_dir``.
    Argparse only enforces single-flag uniqueness; the cross-flag
    mutual-exclusion is a runtime concern.
    """
    parser = argparse.ArgumentParser()
    add_project_dir_arg(parser)
    args = parser.parse_args(
        [
            '--project-dir',
            CANONICAL_PROJECT_DIR,
            '--plan-id',
            CANONICAL_PLAN_ID,
        ]
    )
    assert args.project_dir == CANONICAL_PROJECT_DIR
    assert args.plan_id == CANONICAL_PLAN_ID


# =============================================================================
# Subparser helpers — every Bucket B subcommand inherits the flag pair
# =============================================================================


@pytest.mark.parametrize(
    'register_fn,subcommand,extra_args',
    [
        (
            lambda subs: add_run_subparser(subs).set_defaults(func=lambda _a: 0),
            'run',
            ['--command-args', 'verify'],
        ),
        (
            lambda subs: add_coverage_subparser(subs).set_defaults(func=lambda _a: 0),
            'coverage-report',
            [],
        ),
        (
            lambda subs: add_check_warnings_subparser(subs, lambda _a: 0),
            'check-warnings',
            [],
        ),
    ],
    ids=['run', 'coverage_report', 'check_warnings'],
)
def test_subparsers_inherit_routing_flag_pair(register_fn, subcommand, extra_args):
    """Every Bucket B subparser MUST declare both --project-dir and --plan-id."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    register_fn(sub)

    args = parser.parse_args([subcommand, *extra_args, '--plan-id', CANONICAL_PLAN_ID])
    assert args.plan_id == CANONICAL_PLAN_ID
    # project_dir keeps its default '.' so the resolver detects absence.
    assert args.project_dir == '.'


def test_parse_subparser_does_not_declare_routing_flags():
    """``parse`` is a log-file analyser — it has no project-relative work.

    The parse subparser intentionally still declares ``--project-dir``
    via ``add_project_dir_arg`` for symmetry, but the resolver is a
    no-op when the handler doesn't read ``args.project_dir``. This test
    locks the symmetry: the flag pair must remain attached so callers
    can route uniformly across subcommands.
    """
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    add_parse_subparser(sub, lambda _path: ([], None, 'SUCCESS'))

    args = parser.parse_args(['parse', '--log', '/tmp/build.log'])
    # Both flags are declared (default values).
    assert hasattr(args, 'project_dir')
    assert hasattr(args, 'plan_id')


# =============================================================================
# resolve_project_dir — four-state contract
# =============================================================================


def test_resolve_plan_id_only_use_worktree_true_returns_worktree():
    from resolve_project_dir import resolve_project_dir

    with patch_query_worktree_path(use_worktree=True, worktree_path=CANONICAL_WORKTREE):
        resolved = resolve_project_dir(CANONICAL_PLAN_ID, '.', default='.')
    assert resolved.endswith(CANONICAL_WORKTREE.lstrip('/'))


def test_resolve_plan_id_only_use_worktree_false_falls_back_to_main():
    from resolve_project_dir import resolve_project_dir

    with (
        patch_query_worktree_path(use_worktree=False),
        patch_main_checkout_root('/tmp/main-checkout-stub'),
    ):
        resolved = resolve_project_dir(CANONICAL_PLAN_ID, '.', default='.')
    assert resolved == '/tmp/main-checkout-stub'


def test_resolve_project_dir_only_returns_path_verbatim():
    from resolve_project_dir import resolve_project_dir

    resolved = resolve_project_dir(None, CANONICAL_PROJECT_DIR, default='.')
    # The resolver normalises to absolute paths; we assert the input
    # survived (the basename matches).
    assert resolved.endswith(CANONICAL_PROJECT_DIR.lstrip('/'))


def test_resolve_both_flags_raises_mutually_exclusive_error():
    from resolve_project_dir import MutuallyExclusiveArgsError, resolve_project_dir

    with pytest.raises(MutuallyExclusiveArgsError):
        resolve_project_dir(CANONICAL_PLAN_ID, CANONICAL_PROJECT_DIR, default='.')


def test_resolve_neither_flag_returns_main_checkout():
    from resolve_project_dir import resolve_project_dir

    with patch_main_checkout_root('/tmp/main-checkout-stub'):
        resolved = resolve_project_dir(None, '.', default='.')
    assert resolved == '/tmp/main-checkout-stub'


def test_resolve_default_sentinel_distinguishes_explicit_from_missing():
    """``default`` parameter lets the resolver detect "user passed --project-dir Y"
    vs. "user accepted the argparse default".

    When ``project_dir`` equals ``default``, the resolver treats it as
    absent and falls through to the plan_id / main-checkout branches.
    """
    from resolve_project_dir import resolve_project_dir

    # Pretend the parser default is '/tmp/argparse-default'. A user who
    # passes nothing surfaces that exact value, which the resolver must
    # NOT treat as an explicit override.
    with patch_main_checkout_root('/tmp/main-checkout-stub'):
        resolved = resolve_project_dir(
            None,
            '/tmp/argparse-default',
            default='/tmp/argparse-default',
        )
    assert resolved == '/tmp/main-checkout-stub'


def test_resolve_plan_id_with_use_worktree_true_but_empty_worktree_path_raises():
    """``use_worktree=true`` + empty path is a corrupt-state error."""
    from resolve_project_dir import WorktreeResolutionError, resolve_project_dir

    with patch_query_worktree_path(use_worktree=True, worktree_path=''):
        with pytest.raises(WorktreeResolutionError):
            resolve_project_dir(CANONICAL_PLAN_ID, '.', default='.')


# =============================================================================
# build_main — emits TOON error payloads via the resolver
# =============================================================================


def _register_noop_run(subparsers):
    """Register a stub run subparser whose handler echoes the resolved path."""
    p = add_run_subparser(subparsers, command_args_help='Test')
    p.set_defaults(func=lambda args: 0)
    return p


def test_build_main_emits_mutually_exclusive_error_on_both_flags(monkeypatch, capsys):
    """build_main MUST print mutually_exclusive_args TOON and return 2."""
    monkeypatch.setattr(
        'sys.argv',
        [
            'maven.py',
            'run',
            '--command-args',
            'verify',
            '--plan-id',
            CANONICAL_PLAN_ID,
            '--project-dir',
            CANONICAL_PROJECT_DIR,
        ],
    )
    rc = build_main('Maven build', [_register_noop_run])
    assert rc == 2
    out = capsys.readouterr().out
    assert 'mutually_exclusive_args' in out


def test_build_main_emits_worktree_resolution_error_on_corrupt_metadata(monkeypatch, capsys):
    """When --plan-id points to corrupt metadata, build_main emits worktree_resolution_failed."""
    import resolve_project_dir as _routing

    def fake_query(_pid):
        raise _routing.WorktreeResolutionError(f'plan {_pid!r} metadata is corrupt')

    monkeypatch.setattr(_routing, '_query_worktree_path', fake_query)
    monkeypatch.setattr(
        'sys.argv',
        [
            'maven.py',
            'run',
            '--command-args',
            'verify',
            '--plan-id',
            CANONICAL_PLAN_ID,
        ],
    )
    rc = build_main('Maven build', [_register_noop_run])
    assert rc == 2
    out = capsys.readouterr().out
    assert 'worktree_resolution_failed' in out


def test_build_main_resolves_plan_id_to_worktree_before_handler(monkeypatch):
    """The resolver overwrites args.project_dir BEFORE the handler runs."""
    import resolve_project_dir as _routing

    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, CANONICAL_WORKTREE))

    captured: list[str] = []

    def capture_run(args):
        captured.append(args.project_dir)
        return 0

    def register(subparsers):
        p = add_run_subparser(subparsers, command_args_help='Test')
        p.set_defaults(func=capture_run)

    monkeypatch.setattr(
        'sys.argv',
        [
            'maven.py',
            'run',
            '--command-args',
            'verify',
            '--plan-id',
            CANONICAL_PLAN_ID,
        ],
    )
    rc = build_main('Maven build', [register])
    assert rc == 0
    assert len(captured) == 1
    assert captured[0].endswith(CANONICAL_WORKTREE.lstrip('/'))


def test_build_main_resolves_neither_flag_to_main_checkout(monkeypatch):
    """build_main with neither flag falls back to the main checkout root."""
    import resolve_project_dir as _routing

    monkeypatch.setattr(_routing, '_main_checkout_root', lambda: '/tmp/main-checkout-stub')

    captured: list[str] = []

    def capture_run(args):
        captured.append(args.project_dir)
        return 0

    def register(subparsers):
        p = add_run_subparser(subparsers, command_args_help='Test')
        p.set_defaults(func=capture_run)

    monkeypatch.setattr('sys.argv', ['maven.py', 'run', '--command-args', 'verify'])
    rc = build_main('Maven build', [register])
    assert rc == 0
    assert captured == ['/tmp/main-checkout-stub']


def test_build_main_preserves_explicit_project_dir(monkeypatch):
    """build_main with --project-dir only echoes the path verbatim (absolutised)."""
    captured: list[str] = []

    def capture_run(args):
        captured.append(args.project_dir)
        return 0

    def register(subparsers):
        p = add_run_subparser(subparsers, command_args_help='Test')
        p.set_defaults(func=capture_run)

    monkeypatch.setattr(
        'sys.argv',
        [
            'maven.py',
            'run',
            '--command-args',
            'verify',
            '--project-dir',
            CANONICAL_PROJECT_DIR,
        ],
    )
    rc = build_main('Maven build', [register])
    assert rc == 0
    assert captured[0].endswith(CANONICAL_PROJECT_DIR.lstrip('/'))


# =============================================================================
# register_standard_subparsers — declarative wiring still propagates the contract
# =============================================================================


def test_register_standard_subparsers_propagates_routing_flags():
    """The declarative builder MUST propagate the routing pair to every subcommand."""
    fns = register_standard_subparsers(
        run_handler=lambda _a: 0,
        parse_handler=lambda _path: ([], None, 'SUCCESS'),
        check_warnings_handler=lambda _a: 0,
    )
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for fn in fns:
        fn(sub)

    # Each subcommand inherits both flags.
    args = parser.parse_args(['run', '--command-args', 'verify', '--plan-id', CANONICAL_PLAN_ID])
    assert args.plan_id == CANONICAL_PLAN_ID

    args = parser.parse_args(['parse', '--log', '/tmp/x.log'])
    assert hasattr(args, 'plan_id')

    args = parser.parse_args(['check-warnings', '--project-dir', CANONICAL_PROJECT_DIR])
    assert args.project_dir == CANONICAL_PROJECT_DIR


# Silence unused-import warning.
_ = patch
