#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared fixtures and helpers for the two-state ``--plan-id`` /
``--project-dir`` contract.

Re-used by every Bucket B / plan-context test suite that exercises the
contract — the consumer set grows as scripts migrate onto the shared
resolver, so it is deliberately not enumerated here.

The six contract states tested across those suites are:

* ``--plan-id X`` only, ``use_worktree=true`` → resolves to the
  persisted worktree path.
* ``--plan-id X`` only, ``use_worktree=false`` → falls back to the
  cwd-relative checkout root (``file_ops.cwd_checkout_root``).
* ``--plan-id NO_PLAN`` (the sentinel state) → resolves to the
  main-checkout / cwd checkout root with NO worktree lookup. The
  sentinel is NOT a routing source, so it is also not counted as
  "supplied" for the mutual-exclusion check: ``--plan-id NO_PLAN
  --project-dir Y`` stays legal and yields ``Y``.
* ``--project-dir Y`` only → returns ``Y`` verbatim (legacy / escape
  hatch).
* Neither flag → returns the main checkout root.
* Both flags (a REAL plan id plus ``--project-dir``) →
  ``MutuallyExclusiveArgsError``.

This file is intentionally a sibling helper (``_fixtures.py`` style) and
is NOT a ``conftest.py`` — placing a ``conftest.py`` under
``test/plan-marshall/`` would silently shadow the top-level
``test/conftest.py`` and disable shared fixtures.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

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

NO_PLAN_SENTINEL = 'NO_PLAN'
"""The plan-less sentinel every ``--plan-id``-taking script must accept.

Kept as a literal rather than imported from ``file_ops`` so a rename of the
production constant surfaces as a failing contract assertion in every consumer
suite, instead of silently re-pointing all of them at the new value.
"""

MAIN_CHECKOUT_ROOT = '/tmp/test-main-checkout'
"""Stand-in main-checkout root used by :func:`patch_main_checkout_root`."""


# =============================================================================
# Patch helpers — keep ``resolve_project_dir`` deterministic in tests
# =============================================================================


@contextmanager
def patch_query_worktree_path(use_worktree: bool, worktree_path: str | None = None):
    """Patch ``file_ops._query_worktree_path`` deterministically.

    Avoids the need to spin up a real ``manage-status get-worktree-path``
    subprocess.

    The patch target is ``file_ops``, not ``resolve_project_dir``:
    ``resolve_project_dir`` no longer shells out itself — it delegates the
    worktree face to ``file_ops.resolve_plan_context``, and
    ``file_ops._query_worktree_path`` is now the SINGLE place in the codebase
    that invokes ``manage-status get-worktree-path``. Patching that one seam
    therefore still covers every consumer, and it leaves the real delegation
    chain (``resolve_project_dir`` → ``resolve_plan_context`` →
    ``PlanContext.worktree_path``) executing for real rather than mocked out.

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
        'file_ops._query_worktree_path',
        return_value=(use_worktree, worktree_path),
    ) as mock:
        yield mock


CANONICAL_WORKTREE_BRANCH = 'feature/task-routing-canonical'
"""Stand-in persisted feature branch for :func:`patch_worktree_faces`."""


@contextmanager
def patch_query_worktree_path_map(mapping: dict[str, Any]):
    """Patch the resolver seam with a PER-PLAN-ID response map.

    The single-value :func:`patch_query_worktree_path` cannot express a verb
    that resolves several plans in one call — ``worktree-list`` walks the whole
    plan census and must see a different verdict per plan. Each mapping value is
    either a ``(use_worktree, worktree_path)`` tuple or an ``Exception``
    INSTANCE, which is raised for that plan id (modelling an unresolvable plan
    alongside resolvable ones in the same run).

    An unmapped plan id raises ``AssertionError`` rather than silently
    defaulting: a resolution the test did not anticipate is a fact worth
    failing on, not one to paper over with a default verdict.

    Yields:
        The ``MagicMock`` installed at the seam, for call-count assertions.
    """

    def _resolve(plan_id: str):
        if plan_id not in mapping:
            raise AssertionError(
                f'unstubbed worktree resolution for plan_id={plan_id!r}; '
                f'stubbed ids are {sorted(mapping)}'
            )
        outcome = mapping[plan_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    with patch('file_ops._query_worktree_path', side_effect=_resolve) as mock:
        yield mock


@contextmanager
def patch_worktree_faces(
    use_worktree: bool = True,
    worktree_path: str | None = None,
    worktree_branch: str = CANONICAL_WORKTREE_BRANCH,
):
    """Patch BOTH worktree faces of the single ``get-worktree-path`` channel.

    ``PlanContext`` exposes the path/presence faces
    (``worktree_path`` / ``has_worktree``, backed by
    ``file_ops._query_worktree_path``) and the branch face
    (``worktree_branch``, backed by ``file_ops._query_worktree_branch``) over
    two SEPARATE seams, so a consumer that needs only one pays for only one.
    A consumer that needs both — ``force-push-with-lease`` resolves a worktree
    path AND the branch to push — must therefore have both stubbed; patching
    only ``_query_worktree_path`` leaves the branch face shelling out for real.

    Yields:
        ``(path_mock, branch_mock)`` so callers can assert per-face call counts.
    """
    if worktree_path is None:
        worktree_path = CANONICAL_WORKTREE if use_worktree else ''
    with (
        patch(
            'file_ops._query_worktree_path',
            return_value=(use_worktree, worktree_path),
        ) as path_mock,
        patch('file_ops._query_worktree_branch', return_value=worktree_branch) as branch_mock,
    ):
        yield path_mock, branch_mock


@contextmanager
def patch_main_checkout_root(path: str = MAIN_CHECKOUT_ROOT):
    """Patch the cwd-relative checkout-root resolver deterministically.

    Avoids dependence on the real checkout layout of the test runner. Used in
    the "neither flag" and ``use_worktree=false`` branches of the contract.

    BOTH bindings of ``cwd_checkout_root`` are patched, because there are two
    distinct call sites reached by two different lookups:

    * ``resolve_project_dir.cwd_checkout_root`` — the "neither flag" branch;
      bound into that module's namespace by ``from file_ops import ...``, so
      patching ``file_ops`` alone would NOT affect it.
    * ``file_ops.cwd_checkout_root`` — reached through the module global inside
      ``PlanContext._resolve_worktree_face`` on the ``use_worktree=false`` and
      sentinel branches.

    Patching only one of the two leaves the other resolving for real, which is
    exactly the kind of half-patched fixture that makes a test pass for the
    wrong reason.

    The SAME mock object is installed at both bindings, so a caller's
    ``assert_called_once()`` observes the call whichever of the two routes the
    code under test actually took. Yielding one binding's own mock would make
    the call-count assertion silently route-dependent — it would read "never
    called" for a branch that did resolve the root, just through the other name.

    Yields:
        The shared ``MagicMock`` installed at both bindings.
    """
    mock = MagicMock(return_value=path)
    with ExitStack() as stack:
        stack.enter_context(patch('resolve_project_dir.cwd_checkout_root', new=mock))
        stack.enter_context(patch('file_ops.cwd_checkout_root', new=mock))
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


# =============================================================================
# Resolver-migration contract — the two assertions every Bucket B suite makes
# =============================================================================
#
# Both take a ``resolve`` callable supplied by the consuming suite: the SCRIPT's
# OWN worktree-binding entry point, bound through the script module's namespace
# (e.g. ``lambda plan_id: js_coverage.resolve_project_dir(plan_id, '.',
# default='.')``). Binding through the script rather than importing the shared
# helper directly is what makes these assertions statements about that script's
# migration, not about the helper.


def assert_worktree_face_routes_through_resolver(resolve: Any) -> None:
    """Assert ``resolve(plan_id)`` reaches the ONE ``get-worktree-path`` seam.

    ``file_ops._query_worktree_path`` is the single place in the codebase that
    invokes ``manage-status get-worktree-path``; the whole delegation chain
    (script -> ``resolve_project_dir`` -> ``resolve_plan_context`` ->
    ``PlanContext.worktree_path``) executes for real above it. A script that
    still re-derives the worktree by hand never reaches the patched seam and
    fails here, which is precisely the pre-migration behaviour.
    """
    with patch_query_worktree_path(True) as mock:
        resolved = resolve(CANONICAL_PLAN_ID)
    assert resolved == CANONICAL_WORKTREE, (
        'Worktree binding did not resolve through the single resolver seam; '
        f'expected {CANONICAL_WORKTREE!r}, got {resolved!r}'
    )
    assert mock.call_count == 1, (
        'The resolver seam file_ops._query_worktree_path was reached '
        f'{mock.call_count} times, expected exactly 1 — the script either '
        'bypasses the resolver or shells out more than once.'
    )


def assert_sentinel_accepted(resolve: Any) -> None:
    """Assert the ``NO_PLAN`` sentinel resolves WITHOUT touching manage-status.

    The sentinel is the genuinely-plan-less path: its worktree face is always
    the main checkout, resolved in-process. Reaching the ``get-worktree-path``
    channel for ``NO_PLAN`` would mean the sentinel carve-out was bypassed, so
    the call-count assertion is the load-bearing half — a script could return
    the right path while still paying (and failing on) a shell-out.
    """
    with patch_query_worktree_path(True) as mock, patch_main_checkout_root() as root_mock:
        resolved = resolve(NO_PLAN_SENTINEL)
    assert resolved == MAIN_CHECKOUT_ROOT, (
        f'NO_PLAN sentinel resolved to {resolved!r}, expected the main '
        f'checkout root {MAIN_CHECKOUT_ROOT!r}'
    )
    assert root_mock.called, 'The sentinel did not resolve via the checkout-root helper'
    assert mock.call_count == 0, (
        'The NO_PLAN sentinel reached manage-status get-worktree-path '
        f'{mock.call_count} times; the sentinel carve-out must never shell out.'
    )


def assert_sentinel_is_not_a_routing_source(resolve_pair: Any) -> None:
    """Assert ``--plan-id NO_PLAN`` alongside ``--project-dir Y`` stays legal.

    The sentinel is TRUTHY, so a ``bool(plan_id)`` mutual-exclusion check would
    class it as a supplied routing source and reject the combination that every
    plan-less caller with an explicit tree needs. This is the half of the
    sentinel contract :func:`assert_sentinel_accepted` cannot see — that one
    passes whether or not the exclusion check excludes the sentinel, because it
    never supplies ``--project-dir``.

    Args:
        resolve_pair: A callable ``(plan_id, project_dir) -> str`` bound through
            the script under test, mirroring the single-argument ``resolve``
            the sibling assertions take.
    """
    with patch_query_worktree_path(True) as mock:
        resolved = resolve_pair(NO_PLAN_SENTINEL, CANONICAL_PROJECT_DIR)
    assert resolved.endswith(CANONICAL_PROJECT_DIR.lstrip('/')), (
        f'--plan-id NO_PLAN --project-dir {CANONICAL_PROJECT_DIR!r} resolved to '
        f'{resolved!r}; the sentinel must not displace the explicit override.'
    )
    assert mock.call_count == 0, (
        'The NO_PLAN sentinel reached manage-status get-worktree-path '
        f'{mock.call_count} times; it is not a routing source.'
    )
