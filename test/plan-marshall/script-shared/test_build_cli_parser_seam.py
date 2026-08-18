#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the published parser seams on the shared build CLI.

``_build_cli.build_parser`` and ``_build_execute_factory.build_parser`` expose the
build-class argument surface under a name the shared test harness resolves, so a
namespace for a build subcommand is produced by the production parser instead of
being written by hand. These pin:

* the shared ``run`` surface's defaults, which are what a namespace gains by
  coming from the real parser;
* that the published surface stays a faithful restriction of every build
  wrapper's own ``run`` surface, so the seam cannot drift from what the wrappers
  parse;
* that ``build_main`` and the seam construct their parsers through one helper,
  which is what makes that restriction hold by construction rather than by
  coincidence.
"""

import argparse
import ast
import sys
from unittest import mock

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

BUNDLE = 'plan-marshall'
SKILL = 'script-shared'
CLI_SCRIPT = 'build/_build_cli.py'
FACTORY_SCRIPT = 'build/_build_execute_factory.py'

#: Every build wrapper that routes its CLI through ``build_main``. Declared for
#: readability and asserted against the tree below, so a fifth wrapper cannot bypass
#: the shared-surface checks by being absent from this list.
WRAPPER_SCRIPTS = [
    ('build-pyproject', 'pyproject_build.py'),
    ('build-maven', 'maven.py'),
    ('build-gradle', 'gradle.py'),
    ('build-npm', 'npm.py'),
]

#: The ``run`` invocation used everywhere below. Only ``--command-args`` is
#: required, so every other attribute the namespace carries arrives as a default.
RUN_ARGV = ('run', '--command-args', 'verify')

#: The defaults the shared ``run`` surface applies. ``timeout`` is a ``None``
#: sentinel rather than a missing default: it is what distinguishes an explicit
#: ``--timeout N`` from an unsupplied flag.
RUN_DEFAULTS = {
    'command': 'run',
    'command_args': 'verify',
    'timeout': None,
    'mode': 'actionable',
    'format': 'toon',
    'execution_mode': 'auto',
    'project_dir': '.',
    'plan_id': None,
}


def _wrappers_calling_build_main() -> set[tuple[str, str]]:
    """Return every marketplace script that dispatches its CLI through ``build_main``.

    The whole marketplace is walked, not this bundle alone: a wrapper added under
    another bundle is exactly the case a hand-kept list would miss, and it belongs in
    the checks below no less than the four here today.
    """
    found: set[tuple[str, str]] = set()
    for path in MARKETPLACE_ROOT.glob('*/skills/*/scripts/**/*.py'):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except SyntaxError:  # pragma: no cover - a marketplace script that parses is the norm
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == 'build_main'
            ):
                found.add((path.parents[1].name, path.name))
                break
    return found


def test_the_wrapper_population_is_derived_from_the_tree():
    """Every script that calls ``build_main`` is one of the wrappers checked here.

    ``WRAPPER_SCRIPTS`` is what the restriction checks below quantify over, so a
    wrapper missing from it is a wrapper whose ``run`` surface is never compared
    against the published seam — a green result over a population that silently
    shrank. Deriving the set from the call sites makes the list an assertion about
    the tree rather than a copy of it.
    """
    derived = _wrappers_calling_build_main()

    assert derived, (
        'no script in the marketplace calls build_main — the derivation has stopped '
        'finding the wrappers, so the comparison below quantifies over nothing'
    )
    assert derived == set(WRAPPER_SCRIPTS), (
        f'scripts routing through build_main: {sorted(derived)}; scripts checked here: '
        f'{sorted(WRAPPER_SCRIPTS)}. A wrapper in the first set and not the second is '
        'never compared against the published seam.'
    )


@pytest.fixture(scope='module')
def shared_run_ns():
    """The ``run`` namespace the shared build-CLI seam produces."""
    return parse_ns(BUNDLE, SKILL, CLI_SCRIPT, *RUN_ARGV, register=False)


@pytest.mark.parametrize(('attribute', 'expected'), sorted(RUN_DEFAULTS.items()))
def test_shared_run_seam_carries_production_defaults(shared_run_ns, attribute, expected):
    """The shared ``run`` seam applies every default the production parser declares."""
    assert getattr(shared_run_ns, attribute) == expected


def _subcommands(parser: argparse.ArgumentParser) -> set[str]:
    """Return the subcommand names ``parser`` accepts."""
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(actions) == 1, f'expected exactly one subparsers action, got {len(actions)}'
    return set(actions[0].choices)


def _wrapper_subcommands(skill: str, script: str) -> set[str]:
    """Return the subcommands a build wrapper's production parser accepts.

    Captured by intercepting the wrapper's own ``main()`` at its ``parse_args``
    call, so it is the parser production builds rather than a restatement of it.
    """
    module = load_script_module(BUNDLE, skill, script, register=False)
    captured: list[argparse.ArgumentParser] = []

    def _intercept(self, args=None, namespace=None):
        captured.append(self)
        raise SystemExit(0)

    saved = sys.argv
    sys.argv = [script]
    try:
        with mock.patch.object(argparse.ArgumentParser, 'parse_args', _intercept):
            with pytest.raises(SystemExit):
                module.main()
    finally:
        sys.argv = saved

    assert captured, f'{script} did not reach parse_args'
    return _subcommands(captured[0])


#: The one subcommand this module registers that the seam cannot carry: its
#: registration takes the wrapper's own ``ExecuteConfig``, and the exposed key must
#: round-trip against the one ``cmd_run`` persists, so a zero-argument builder has
#: nothing correct to pass.
CONFIG_BOUND_SUBCOMMAND = 'run-config-key'


def test_seam_publishes_every_shared_subcommand_but_the_config_bound_one():
    """The seam carries exactly the subcommands all wrappers share, less the config-bound one.

    The expected set is DERIVED by intersecting the four wrappers' live parsers
    rather than listed here, so a subcommand added to the shared surface and wired
    into every wrapper — but not into the seam — fails this instead of passing
    against a stale literal.
    """
    cli = load_script_module(BUNDLE, SKILL, CLI_SCRIPT, register=False)

    shared = set.intersection(
        *(_wrapper_subcommands(skill, script) for skill, script in WRAPPER_SCRIPTS)
    )

    assert CONFIG_BOUND_SUBCOMMAND in shared, (
        'the exclusion below is only meaningful while every wrapper registers it'
    )
    assert _subcommands(cli.build_parser()) == shared - {CONFIG_BOUND_SUBCOMMAND}


def test_execute_factory_seam_yields_the_shared_run_namespace(shared_run_ns):
    """The factory's seam parses ``run`` into the namespace the shared surface defines."""
    factory_ns = parse_ns(BUNDLE, SKILL, FACTORY_SCRIPT, *RUN_ARGV, register=False)

    assert vars(factory_ns) == vars(shared_run_ns)


@pytest.mark.parametrize(
    ('skill', 'script'), WRAPPER_SCRIPTS, ids=[skill for skill, _ in WRAPPER_SCRIPTS]
)
def test_shared_run_surface_is_a_restriction_of_each_wrapper(shared_run_ns, skill, script):
    """Every shared ``run`` attribute is present in each wrapper's own ``run`` namespace, with the same value.

    A wrapper may ADD tool-specific flags through ``extra_args_fn`` — npm and
    pyproject contribute ``--env`` and ``--working-dir`` — but may not drop or
    redefine a shared one. Asserting the restriction rather than equality is what
    lets the extra flags exist while still failing on a shared default that drifts.
    """
    wrapper_ns = parse_ns(BUNDLE, skill, script, *RUN_ARGV, register=False)

    shared = vars(shared_run_ns)
    wrapper = vars(wrapper_ns)

    assert set(shared) <= set(wrapper)
    assert {key: wrapper[key] for key in shared} == shared


def test_build_main_parses_with_the_shared_construction(monkeypatch):
    """``build_main`` obtains its parser from the same helper the seam calls.

    The seam is only a faithful restriction of the wrappers' surface because both
    are constructed by ``build_cli_parser``. Pinning the call is what keeps a
    later edit from giving ``build_main`` a second, independent construction that
    the seam would then silently misdescribe.
    """
    cli = load_script_module(BUNDLE, SKILL, CLI_SCRIPT, register=False)
    calls = []

    def _record(description, subparser_fns):
        calls.append((description, list(subparser_fns)))
        raise SystemExit(0)

    monkeypatch.setattr(cli, 'build_cli_parser', _record)
    registration = [lambda subparsers: subparsers.add_parser('demo')]

    with pytest.raises(SystemExit):
        cli.build_main('Demo build operations', registration)

    assert calls == [('Demo build operations', registration)]
