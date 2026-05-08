#!/usr/bin/env python3
"""Shared fixtures and helpers for the two-state ``--plan-id`` /
``--project-dir`` contract.

Re-used by the test modules that cover every Bucket B script consumer
(build-maven, build-gradle, build-npm, build-python, tools-integration-ci,
extension-api, tools-self-review, workflow-integration-{github,gitlab},
workflow-integration-sonar, workflow-pr-doctor, manage-references,
manage-architecture, script-shared, execute-task).

The four contract states tested across all 21 files are:

* ``--plan-id X`` only, ``use_worktree=true`` → resolves to the
  persisted worktree path.
* ``--plan-id X`` only, ``use_worktree=false`` → falls back to the
  main checkout root (``git rev-parse --show-toplevel``).
* ``--project-dir Y`` only → returns ``Y`` verbatim (legacy / escape
  hatch).
* Neither flag → returns the main checkout root.
* Both flags → ``MutuallyExclusiveArgsError``.

This file is intentionally a sibling helper (``_fixtures.py`` style) and
is NOT a ``conftest.py`` — placing a ``conftest.py`` under
``test/plan-marshall/`` would silently shadow the top-level
``test/conftest.py`` and disable shared fixtures.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

# =============================================================================
# Shared canonical values
# =============================================================================

CANONICAL_PLAN_ID = 'task-routing-canonical'
"""Plan id used across the routing tests — short, kebab-case, valid."""

CANONICAL_WORKTREE = '/tmp/test-worktree-routing'
"""Stand-in worktree path. Never written to — every test patches the
file-system layer or stops at argparse, so the path only needs to be a
shape the helper accepts."""

CANONICAL_PROJECT_DIR = '/tmp/test-explicit-project-dir'
"""Stand-in explicit ``--project-dir`` path."""


# =============================================================================
# Patch helpers — keep ``resolve_project_dir`` deterministic in tests
# =============================================================================


@contextmanager
def patch_query_worktree_path(use_worktree: bool, worktree_path: str | None = None):
    """Patch ``resolve_project_dir._query_worktree_path`` deterministically.

    Avoids the need to spin up a real ``manage-status get-worktree-path``
    subprocess. The helper is the boundary between the in-process resolver
    and the executor invocation, so patching it covers every consumer.

    Args:
        use_worktree: The ``use_worktree`` flag the patched helper returns.
        worktree_path: The persisted worktree path. Defaults to
            ``CANONICAL_WORKTREE`` when ``use_worktree`` is True, empty
            string otherwise (matching the real script's contract).

    Yields:
        The ``MagicMock`` instance — tests can assert call counts when
        the side-effect path matters.
    """
    if worktree_path is None:
        worktree_path = CANONICAL_WORKTREE if use_worktree else ''
    with patch(
        'resolve_project_dir._query_worktree_path',
        return_value=(use_worktree, worktree_path),
    ) as mock:
        yield mock


@contextmanager
def patch_main_checkout_root(path: str = '/tmp/test-main-checkout'):
    """Patch ``resolve_project_dir._main_checkout_root`` deterministically.

    Avoids dependence on the real ``git rev-parse --show-toplevel`` of
    the test runner. Used in the "neither" and ``use_worktree=false``
    branches of the contract.
    """
    with patch('resolve_project_dir._main_checkout_root', return_value=path) as mock:
        yield mock


# =============================================================================
# Argparse helpers — assert both flags are wired uniformly
# =============================================================================


def assert_accepts_plan_id_flag(parser: Any, *prefix_args: str) -> None:
    """Assert the parser accepts ``--plan-id ID`` without crashing.

    Used by build-* / ci / workflow-* tests to lock in the auto-routing
    flag declaration; the resolver then takes over at run time.
    """
    args = parser.parse_args([*prefix_args, '--plan-id', CANONICAL_PLAN_ID])
    assert getattr(args, 'plan_id', None) == CANONICAL_PLAN_ID, (
        f'Parser did not surface --plan-id under args.plan_id; got: {args!r}'
    )


def assert_accepts_project_dir_flag(parser: Any, *prefix_args: str) -> None:
    """Assert the parser accepts ``--project-dir PATH`` without crashing."""
    args = parser.parse_args([*prefix_args, '--project-dir', CANONICAL_PROJECT_DIR])
    assert getattr(args, 'project_dir', None) == CANONICAL_PROJECT_DIR, (
        f'Parser did not surface --project-dir under args.project_dir; got: {args!r}'
    )
