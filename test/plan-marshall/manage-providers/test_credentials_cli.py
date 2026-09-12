#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the routing chain in the credential-management CLI.

``credentials.main`` is a dispatcher: the published parser decides which
subcommand was asked for, and ``main`` turns that into exactly one handler call.
Every handler is imported inside the branch that uses it, so a ``monkeypatch``
on the owning module reaches the binding the branch resolves at call time.

These pin each route to its OWN handler and to that handler's return value.
``safe_main`` wraps ``main`` in ``sys.exit(main_fn())``, so the value a handler
returns leaves the process as the ``SystemExit`` code rather than as a return —
which is what makes a mis-wired route observable at all.
"""

import argparse
import sys

import pytest

from conftest import load_script_module

BUNDLE = 'plan-marshall'
SKILL = 'manage-providers'
SCRIPT = 'credentials.py'

#: The code a stubbed handler returns. Distinct from both codes the dispatcher
#: produces on its own — ``0`` for the ``migrate-home`` wrapper and ``1`` for the
#: fall-through — so an assertion on it can only pass if the stub's value is what
#: travelled out through ``safe_main``.
HANDLER_SENTINEL = 42

#: The status literal the migration helper hands back. One of the three the
#: subcommand's help text publishes (``migrated|already_migrated|conflict``);
#: which one is immaterial to the wrapper, and that is the point — it forwards
#: whatever it is given rather than interpreting it.
MIGRATION_RESULT = 'already_migrated'

#: One row per route that delegates: the argv the real parser consumes, and the
#: handler that route must reach, as ``module.attribute``. ``migrate-home`` is
#: absent deliberately — it dispatches to no handler and is covered on its own
#: below.
ROUTES = [
    (('configure', '--skill', 'sonarqube'), '_cred_configure.run_configure'),
    (('check', '--skill', 'sonarqube'), '_cred_check.run_check'),
    (('edit', '--skill', 'sonarqube'), '_cred_edit.run_edit'),
    (('discover-and-persist',), '_list_providers.run_discover_and_persist'),
    (('list-providers',), '_list_providers.run_list_providers'),
    (('find-by-category', '--category', 'ci'), '_list_providers.run_find_by_category'),
    (('verify',), '_cred_verify.run_verify'),
    (('list',), '_cred_list.run_list'),
    (('remove', '--skill', 'sonarqube'), '_cred_remove.run_remove'),
    (('ensure-denied',), '_cred_ensure_denied.run_ensure_denied'),
]


@pytest.fixture
def cli():
    """The credential CLI module, loaded without registering it in ``sys.modules``."""
    return load_script_module(BUNDLE, SKILL, SCRIPT, register=False)


@pytest.fixture
def handler_calls(monkeypatch):
    """Replace EVERY delegating handler with a recorder; yield the call log.

    All ten are stubbed for each test, not just the one under exercise: that is
    what makes "reached its own handler" an exclusive claim rather than a
    presence check, and it keeps a mis-wired route from running a real handler —
    which would reach the network or the credential store.
    """
    calls: list[tuple[str, argparse.Namespace]] = []

    def _recorder(target):
        def handler(args):
            calls.append((target, args))
            return HANDLER_SENTINEL

        return handler

    for _, target in ROUTES:
        monkeypatch.setattr(target, _recorder(target))
    return calls


def _exit_code(cli_module, monkeypatch, argv):
    """Drive ``main`` over ``argv`` and return the code ``safe_main`` exits with."""
    monkeypatch.setattr(sys, 'argv', [SCRIPT, *argv])
    with pytest.raises(SystemExit) as exit_info:
        cli_module.main()
    return exit_info.value.code


@pytest.mark.parametrize(('argv', 'target'), ROUTES, ids=[argv[0] for argv, _ in ROUTES])
def test_route_reaches_its_own_handler(cli, handler_calls, monkeypatch, argv, target):
    """Each delegating subcommand calls its own handler once and returns that handler's value."""
    code = _exit_code(cli, monkeypatch, argv)

    assert [called for called, _ in handler_calls] == [target]
    assert handler_calls[0][1].command == argv[0]
    assert code == HANDLER_SENTINEL


def test_migrate_home_wraps_the_migration_helper(cli, handler_calls, monkeypatch):
    """``migrate-home`` calls the migration helper once, emits its result, and returns 0.

    It is the one route with no handler of its own: the branch performs the call,
    the emission and the return itself, so those three are the whole contract.
    """
    migrations: list[str] = []
    emitted: list[dict] = []

    def _migrate():
        migrations.append('called')
        return MIGRATION_RESULT

    monkeypatch.setattr('_providers_core._migrate_credentials_home_if_needed', _migrate)
    monkeypatch.setattr('file_ops.output_toon', emitted.append)

    code = _exit_code(cli, monkeypatch, ('migrate-home',))

    assert migrations == ['called']
    assert emitted == [{'status': 'success', 'operation': 'migrate-home', 'result': MIGRATION_RESULT}]
    assert code == 0
    assert handler_calls == []


def test_unrouted_command_falls_through_to_1(cli, handler_calls, monkeypatch):
    """A parsed command outside the routing chain exits 1 without calling any handler.

    The published parser cannot produce this state — its subparsers are
    ``required=True`` and every subcommand it declares is routed — so the parser
    is substituted with one that accepts any bare command word. The branch is the
    dispatcher's guard for a parser that grows a subcommand without a route, and
    substituting a real (if smaller) parser is the only way to stand where such a
    parser would put it.
    """

    def _bare_command_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument('command')
        return parser

    monkeypatch.setattr(cli, 'build_parser', _bare_command_parser)

    code = _exit_code(cli, monkeypatch, ('not-a-route',))

    assert code == 1
    assert handler_calls == []
