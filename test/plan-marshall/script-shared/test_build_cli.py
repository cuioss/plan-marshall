#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Comprehensive unit tests for ``_build_cli.py`` and the four-state
``--plan-id`` / ``--project-dir`` routing helper it integrates.

Covers:

* :func:`_build_cli.add_project_dir_arg` — registers the routing pair
  on every Bucket B build subparser (run, parse, coverage-report,
  check-warnings).
* :func:`_build_cli.build_main` — dispatches to the resolver before the
  selected handler reads ``args.project_dir``, so all Bucket B build
  scripts (maven, gradle, npm, pyproject_build) inherit the contract.
* :mod:`_build_class_roster` — the argparse-derived build-class operation
  population, cross-checked against the executor's own
  ``_BUILD_CLASS_PREFIXES`` declaration.
* :func:`resolve_project_dir.resolve_project_dir` — the canonical
  four-state contract:

  - ``--plan-id X`` only, ``use_worktree=true`` → worktree path
  - ``--plan-id X`` only, ``use_worktree=false`` → main checkout
  - ``--project-dir Y`` only → ``Y`` (verbatim, absolutised)
  - both → ``MutuallyExclusiveArgsError``
  - neither → main checkout

The resolver tests are exercised at the library level (no subprocess)
because per-build-script tests (``test_pyproject_build``, ``test_maven``,
``test_gradle``, ``test_npm``) only pin the parser surface and the
subprocess-level both-supplied error path. Centralising the deep
behaviour here avoids 4× duplication.
"""

from __future__ import annotations

import argparse

import pytest

# Cross-skill imports — PYTHONPATH is configured by the root conftest.
from _build_class_roster import (
    PLAN_ID_FLAG,
    PROJECT_DIR_FLAG,
    _subcommand_flag_pairs,
    build_class_prefixes,
    build_class_roster,
)
from _build_cli import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_discover_subparser,
    add_parse_subparser,
    add_project_dir_arg,
    add_run_subparser,
    build_main,
    register_standard_subparsers,
)
from _resolve_project_dir_fixtures import (
    CANONICAL_PLAN_ID,
    CANONICAL_PROJECT_DIR,
    CANONICAL_WORKTREE,
    MAIN_CHECKOUT_ROOT,
    NO_PLAN_SENTINEL,
    patch_main_checkout_root,
    patch_query_worktree_path,
)


def test_build_cli_no_longer_exposes_search_markers_subparser():
    """The retired ``add_search_markers_subparser`` helper is gone from _build_cli.

    Marker detection is no longer a build-tool subcommand — it relocated to the
    java-cui domain bundle as the ``marker-detect`` domain verb, so the shared
    build CLI must not offer a registration seam for it.
    """
    import _build_cli

    assert not hasattr(_build_cli, 'add_search_markers_subparser')


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
    import file_ops as _resolver_core
    import resolve_project_dir as _routing

    def fake_query(_pid):
        raise _routing.WorktreeResolutionError(f'plan {_pid!r} metadata is corrupt')

    # The shell-out seam lives in file_ops now; resolve_project_dir delegates to
    # it through resolve_plan_context, and re-exports the same error class.
    monkeypatch.setattr(_resolver_core, '_query_worktree_path', fake_query)
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
    import file_ops as _resolver_core

    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: (True, CANONICAL_WORKTREE)
    )

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

    # The "neither flag" branch reaches cwd_checkout_root through the name bound
    # into resolve_project_dir by its `from file_ops import ...`, so THAT is the
    # binding to patch here.
    monkeypatch.setattr(_routing, 'cwd_checkout_root', lambda: '/tmp/main-checkout-stub')

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


# =============================================================================
# Resolver-migration contract — the NO_PLAN sentinel
# =============================================================================
#
# ``--plan-id`` is no longer a plan-only flag: a genuinely plan-less caller
# passes the ``NO_PLAN`` sentinel and must resolve to the main checkout. Because
# every Bucket B build script inherits its routing from ``build_main``, pinning
# the sentinel here covers maven / gradle / npm / pyproject_build at once —
# the same reason the four-state resolver behaviour is centralised in this file.


def test_resolve_no_plan_sentinel_returns_main_checkout():
    """The sentinel resolves to the main checkout WITHOUT reaching manage-status.

    The call-count half is the load-bearing one: a sentinel that returned the
    right path but still paid a ``get-worktree-path`` shell-out would fail in
    exactly the plan-less contexts the sentinel exists to serve (no plan record
    exists for it to resolve).
    """
    from resolve_project_dir import resolve_project_dir

    with (
        patch_query_worktree_path(use_worktree=True) as mock,
        patch_main_checkout_root(MAIN_CHECKOUT_ROOT),
    ):
        resolved = resolve_project_dir(NO_PLAN_SENTINEL, '.', default='.')

    assert resolved == MAIN_CHECKOUT_ROOT
    assert mock.call_count == 0, 'the sentinel must never reach get-worktree-path'


def test_build_main_routes_the_sentinel_to_the_main_checkout(monkeypatch):
    """End-to-end through ``build_main``: ``--plan-id NO_PLAN`` reaches the handler.

    A build invoked outside any plan must run against the main checkout rather
    than failing resolution, so the resolved ``args.project_dir`` the handler
    sees is the checkout root.
    """
    import file_ops as _resolver_core

    def _forbidden(_pid):
        raise AssertionError('the NO_PLAN sentinel reached get-worktree-path')

    monkeypatch.setattr(_resolver_core, '_query_worktree_path', _forbidden)
    monkeypatch.setattr(_resolver_core, 'cwd_checkout_root', lambda: MAIN_CHECKOUT_ROOT)

    captured: list[str] = []

    def capture_run(args):
        captured.append(args.project_dir)
        return 0

    def register(subparsers):
        p = add_run_subparser(subparsers, command_args_help='Test')
        p.set_defaults(func=capture_run)

    monkeypatch.setattr(
        'sys.argv',
        ['maven.py', 'run', '--command-args', 'verify', '--plan-id', NO_PLAN_SENTINEL],
    )
    rc = build_main('Maven build', [register])

    assert rc == 0
    assert captured == [MAIN_CHECKOUT_ROOT]


# =============================================================================
# Build-class operation roster — the derived population
# =============================================================================
#
# Everything below reads the population from ``_build_class_roster``, which
# derives it by argparse introspection. No test here names a subcommand: a
# literal name would re-introduce the hand-list the roster exists to replace,
# and would keep passing while a wrapper silently gained or lost a subcommand.


def _shared_helper_subcommands() -> set[str]:
    """Return the subcommand names ``register_standard_subparsers`` alone emits.

    Built by driving the declarative helper with every standard handler slot
    filled, so the result is the MAXIMAL set the shared seam can contribute. Any
    roster subcommand outside this set therefore came from a wrapper-local
    ``extra_register_fns`` registration — which is what makes the comparison a
    real coverage check rather than a name lookup.

    The ``run_config_key_config`` slot takes a bare sentinel: the registration
    only stores the object in the handler closure, and no handler runs here.
    """
    fns = register_standard_subparsers(
        run_handler=lambda _args: 0,
        parse_handler=lambda _path: ([], None, 'SUCCESS'),
        coverage_handler=lambda _args: 0,
        check_warnings_handler=lambda _args: 0,
        discover_handler=lambda _root: [],
        run_config_key_config=object(),
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    for fn in fns:
        fn(subparsers)
    return set(subparsers.choices)


def test_build_class_roster_population_is_non_empty():
    """A broken introspection path must fail, never pass as "nothing to check".

    This is the load-bearing anti-vacuity guard for every roster-driven
    assertion: a derivation that silently yielded an empty population would make
    each of those assertions trivially true. Both levels are checked — at least
    one wrapper, and at least one subcommand per wrapper.
    """
    roster = build_class_roster()

    assert roster, (
        'The build-class roster derived an EMPTY population. Every roster-driven '
        'check downstream would pass vacuously — the wrapper discovery or the '
        'parser capture in _build_class_roster is broken.'
    )
    empty = sorted(notation for notation, subcommands in roster.items() if not subcommands)
    assert not empty, (
        f'These build wrappers contributed no subcommands to the roster: {empty}. '
        'A wrapper whose parser captured zero subcommands makes every per-subcommand '
        'assertion vacuous for it.'
    )


def test_every_roster_notation_is_a_build_class_dispatch():
    """No derived wrapper escapes the executor's build-class net.

    The roster discovers wrappers structurally (anything routing through
    ``_build_cli.build_main``), while ``_BUILD_CLASS_PREFIXES`` is the executor's
    own declaration of which dispatches append a ``kind=build`` ledger row. A
    wrapper the executor does not classify as build-class is real drift: its
    builds would go unrecorded.
    """
    prefixes = build_class_prefixes()
    unclassified = sorted(
        notation
        for notation in build_class_roster()
        if not any(notation.startswith(prefix) for prefix in prefixes)
    )

    assert not unclassified, (
        f'These build wrappers are not covered by the executor\'s '
        f'_BUILD_CLASS_PREFIXES ({sorted(prefixes)}): {unclassified}. Their '
        'dispatches would never append a kind=build change-ledger entry.'
    )


def test_every_build_class_prefix_is_represented_in_the_roster():
    """Every declared build-class skill contributes a wrapper to the roster.

    The converse direction of the check above, and the one that catches an
    under-derived population: a prefix the executor declares but the roster never
    reaches means a whole build tool is absent from every roster-driven
    assertion, silently shrinking their coverage.
    """
    notations = list(build_class_roster())
    unrepresented = sorted(
        prefix
        for prefix in build_class_prefixes()
        if not any(notation.startswith(prefix) for notation in notations)
    )

    assert not unrepresented, (
        f'These build-class prefixes contributed no wrapper to the roster: '
        f'{unrepresented}. Derived notations were: {sorted(notations)}.'
    )


def test_roster_covers_extra_register_fn_subcommands():
    """Subcommands registered outside the shared helper are in the population.

    ``extra_register_fns`` is where the wrapper-local subparsers live — they are
    built inside the wrapper scripts, entirely outside
    ``register_standard_subparsers``. A roster derived only from the shared
    seam's emission would omit them while still reporting a healthy-looking
    population, so their presence is asserted explicitly.
    """
    shared = _shared_helper_subcommands()
    beyond_shared = {
        notation: sorted(set(subcommands) - shared)
        for notation, subcommands in build_class_roster().items()
        if set(subcommands) - shared
    }

    assert beyond_shared, (
        'No roster subcommand falls outside the shared '
        f'register_standard_subparsers emission ({sorted(shared)}), so the '
        'extra_register_fns registrations were not captured by the derivation.'
    )


def test_flag_pair_boolean_is_derived_from_the_declared_options():
    """The per-subcommand boolean reads the parser, and it discriminates.

    Driven against a parser this test constructs, so the expected verdict is
    known independently of any wrapper's current state — the check therefore
    stays meaningful once the flag pair becomes universal across the real
    population, where a "some subcommand reports False" assertion would go
    vacuous (and then fail outright).
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    with_pair = subparsers.add_parser('with-pair')
    add_project_dir_arg(with_pair)
    subparsers.add_parser('without-pair')

    pairs = _subcommand_flag_pairs(parser)

    assert pairs == {'with-pair': True, 'without-pair': False}


def test_flag_pair_boolean_requires_both_flags():
    """Declaring only one half of the routing pair does NOT satisfy the boolean.

    The pair is a two-state contract: a subcommand carrying ``--plan-id`` without
    ``--project-dir`` (or the reverse) cannot honour it. A boolean that answered
    on either flag alone would report such a subcommand as compliant.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('plan-id-only').add_argument(PLAN_ID_FLAG, dest='plan_id')
    subparsers.add_parser('project-dir-only').add_argument(PROJECT_DIR_FLAG, dest='project_dir')

    pairs = _subcommand_flag_pairs(parser)

    assert pairs == {'plan-id-only': False, 'project-dir-only': False}


def test_every_build_class_subcommand_declares_the_routing_pair():
    """THE universality gate: no build-class subcommand lacks the routing pair.

    Written against the derived roster, never against a list of subcommand
    names — a subcommand added to any wrapper (through the shared helper or
    through ``extra_register_fns``) joins the population automatically and fails
    here if it was registered without the pair. A hand-list would keep passing
    while covering less than it claims.

    The population size is asserted alongside the verdict because this
    assertion's own shape (``no subcommand is missing the pair``) is trivially
    satisfied by an empty population: an anti-vacuity re-check here keeps THIS
    test meaningful on its own, rather than relying on a sibling test's guard
    still existing.
    """
    roster = build_class_roster()
    population = [
        (notation, subcommand) for notation, subcommands in roster.items() for subcommand in subcommands
    ]

    assert population, (
        'The build-class roster derived an EMPTY population, so the '
        'universality verdict below would hold vacuously.'
    )

    missing = {
        notation: sorted(name for name, declares_pair in subcommands.items() if not declares_pair)
        for notation, subcommands in roster.items()
        if not all(subcommands.values())
    }

    assert not missing, (
        f'These build-class subcommands do not declare BOTH {PLAN_ID_FLAG} and '
        f'{PROJECT_DIR_FLAG}: {missing}. Every build-class dispatch appends a '
        'kind=build ledger row, so a subcommand without the pair cannot attribute '
        'its build to the plan that caused it. Attach the pair through '
        '_build_cli.add_project_dir_arg at the registration site.'
    )


# =============================================================================
# ``--root`` precedence against the resolved routing root
# =============================================================================
#
# ``discover`` is the one shared subcommand that declared a root-style flag
# BEFORE it gained the routing pair, so the two sources have to be reconciled.
# The rule (``_build_cli.resolve_root_arg``): an explicit ``--root`` wins
# verbatim, otherwise the root ``build_main`` resolved from
# ``--plan-id`` / ``--project-dir`` applies. The ``None`` sentinel default on
# ``--root`` is what makes an explicit ``--root .`` distinguishable from an
# unsupplied flag — without it, both would arrive as ``'.'``.

_EXPLICIT_ROOT = '/tmp/test-explicit-discover-root'


def _capturing_discover_fn(captured: list[str]):
    """Return a discover handler that records the project root it was given."""

    def discover(project_root: str) -> list:
        captured.append(project_root)
        return []

    return discover


def _run_discover(monkeypatch, argv_tail: list[str]) -> list[str]:
    """Drive ``discover`` end-to-end through ``build_main`` and return the roots seen.

    End-to-end rather than against the helper in isolation: the fallback value is
    the root ``build_main`` writes into ``args.project_dir``, so a test that
    called ``resolve_root_arg`` on a hand-built namespace would never exercise
    the resolution step that supplies it.
    """
    captured: list[str] = []

    def register(subparsers):
        add_discover_subparser(subparsers, _capturing_discover_fn(captured))

    monkeypatch.setattr('sys.argv', ['gradle.py', 'discover', *argv_tail])
    rc = build_main('Gradle build', [register])

    assert rc == 0
    return captured


def test_discover_root_default_is_the_none_sentinel():
    """``--root`` defaults to ``None``, not to ``'.'``.

    The sentinel IS the mechanism: with a ``'.'`` default the unsupplied case is
    indistinguishable from an explicit ``--root .``, and the precedence rule
    below could not be expressed at all.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    add_discover_subparser(subparsers, lambda _root: [])

    assert parser.parse_args(['discover']).root is None
    assert parser.parse_args(['discover', '--root', '.']).root == '.'


def test_discover_explicit_root_wins_over_resolved_project_dir(monkeypatch):
    """An explicitly-supplied ``--root`` is used verbatim, routing flag or not."""
    captured = _run_discover(
        monkeypatch,
        ['--root', _EXPLICIT_ROOT, '--project-dir', CANONICAL_PROJECT_DIR],
    )

    assert captured == [_EXPLICIT_ROOT]


def test_discover_without_root_falls_back_to_resolved_project_dir(monkeypatch):
    """Absent ``--root``, the root resolved from ``--project-dir`` applies."""
    captured = _run_discover(monkeypatch, ['--project-dir', CANONICAL_PROJECT_DIR])

    assert len(captured) == 1
    assert captured[0].endswith(CANONICAL_PROJECT_DIR.lstrip('/'))


def test_discover_without_root_follows_plan_id_to_the_worktree(monkeypatch):
    """``discover --plan-id X`` enumerates X's worktree, not the caller's cwd.

    This is the behaviour the deliverable exists to produce: before the pair was
    declared, a plan-scoped discover silently enumerated whatever directory the
    process happened to start in, and the resulting module list was attributed to
    the plan anyway.
    """
    with patch_query_worktree_path(use_worktree=True, worktree_path=CANONICAL_WORKTREE):
        captured = _run_discover(monkeypatch, ['--plan-id', CANONICAL_PLAN_ID])

    assert len(captured) == 1
    assert captured[0].endswith(CANONICAL_WORKTREE.lstrip('/'))


def test_discover_explicit_dot_root_is_distinguishable_from_unsupplied(monkeypatch):
    """An explicit ``--root .`` and an unsupplied ``--root`` take different paths.

    The pair of runs is the whole point of the sentinel: ``--root .`` stays the
    caller-relative ``'.'``, while omitting it resolves through the routing pair
    to the checkout root. A ``'.'`` argparse default would collapse both runs to
    the same value and make the distinction unobservable.
    """
    with patch_main_checkout_root(MAIN_CHECKOUT_ROOT):
        explicit = _run_discover(monkeypatch, ['--root', '.'])
        unsupplied = _run_discover(monkeypatch, [])

    assert explicit == ['.']
    assert unsupplied == [MAIN_CHECKOUT_ROOT]
