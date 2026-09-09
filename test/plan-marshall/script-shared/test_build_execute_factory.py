#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _build_execute_factory.py.

Focus on default_command_key_fn() scope-aware key generation:
the full command_args (including module scope) is normalized, so that
full-scope and module-scoped invocations of the same executable produce
distinct keys. This isolates adaptive-timeout learning per scope and
prevents cross-scope run-config key collisions.

Also covers the D6 build-queue integration at the factory ``cmd_run`` wrap
site: ``cmd_run`` runs ``execute_direct`` inside ``build_queue_slot(plan_id)``,
so the build participates in the cluster queue only when a ``plan_id`` is set.
The integration tests drive ``cmd_run`` end-to-end through the REAL
``build_queue_slot`` context manager (with the queue ``_acquire`` / ``_release``
seam mocked on the ``_build_queue_slot`` module) and assert the four admission
paths: admitted-once, blocked-then-admitted, max-retries-exhausted (structured
``queue_saturated`` error, build NOT run), and plan_id-absent (pure passthrough,
zero queue interaction).

These queue-integration cases leave ``execution_mode`` at its ``auto`` default
and depend on the autouse ``_neutralize_daemon_routing`` fixture in
``test/conftest.py`` to hold the D5 ``_route_to_daemon`` seam at its non-routing
outcome — without it, a host with marshalld registered and ready would route the
build away before the injected queue double and exec recorder are ever reached.
The ``TestCmdRunExecutionModeVerdict`` daemon-mode cases below own that seam as
their subject and re-arm it with ``@pytest.mark.allow_daemon_routing``.
"""

import argparse
import json

import _build_execute as build_execute
import _build_execute_factory as factory
import _build_queue_slot as bqs
import pytest
from _build_cli import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_parse_subparser,
    add_project_dir_arg,
    add_run_subparser,
    register_standard_subparsers,
)
from _build_execute import CaptureStrategy
from _build_execute_factory import default_command_key_fn
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL

#: The three shapes a plan-less build's ``plan_id`` arrives in. Every seam below
#: that has to treat "no plan" alike is driven over this one list, so the three
#: shapes cannot drift apart between seams. The ids are stated rather than left
#: to pytest: the empty-string row generates no readable id of its own, so the
#: report would name it only by position.
_PLAN_LESS_PLAN_IDS = [None, '', NO_PLAN_SENTINEL]

_PLAN_LESS_PLAN_ID_IDS = [
    'no-plan-id-attribute-value-at-all',
    'an-empty-plan-id',
    'the-explicit-no-plan-sentinel',
]

#: ``(command args, key)`` for the scope-aware half of the contract: the module
#: scope is part of the key, so a module-scoped invocation cannot inherit the
#: full-scope one's learned timeout.
_COMMAND_KEY_SCOPE_CASES = [
    ('module-tests', 'module_tests'),
    ('module-tests plan-marshall', 'module_tests_plan_marshall'),
]

_COMMAND_KEY_SCOPE_IDS = ['unscoped-uses-the-full-args', 'scoped-includes-the-module']

#: ``(first command args, second command args)`` — pairs that must NOT share a
#: key. Each row is a different axis two invocations could collide along: scope,
#: module, and command.
_COMMAND_KEY_DISTINCT_PAIRS = [
    ('module-tests', 'module-tests plan-marshall'),
    ('module-tests plan-marshall', 'module-tests pm-plugin-development'),
    ('compile plan-marshall', 'module-tests plan-marshall'),
]

_COMMAND_KEY_DISTINCT_PAIR_IDS = [
    'full-scope-versus-module-scope',
    'two-different-modules',
    'two-different-commands-in-one-module',
]


class TestDefaultCommandKeyFnScopeAware:
    """Scope-aware behavior: the full args contribute to the key so
    that module-scoped invocations don't collide with full-scope ones."""

    @pytest.mark.parametrize('command_args,expected_key', _COMMAND_KEY_SCOPE_CASES, ids=_COMMAND_KEY_SCOPE_IDS)
    def test_the_key_carries_the_whole_command_args(self, command_args, expected_key):
        assert default_command_key_fn(command_args) == expected_key

    @pytest.mark.parametrize('first,second', _COMMAND_KEY_DISTINCT_PAIRS, ids=_COMMAND_KEY_DISTINCT_PAIR_IDS)
    def test_two_invocations_that_must_not_share_a_key(self, first, second):
        """Distinct keys are what make adaptive timeouts learn per-scope values."""
        assert default_command_key_fn(first) != default_command_key_fn(second)

    def test_isolation_across_multiple_scopes(self):
        """All four permutations (full, moduleA, moduleB, moduleC) must
        yield four distinct keys — no cross-scope collisions."""
        keys = {
            default_command_key_fn('verify'),
            default_command_key_fn('verify plan-marshall'),
            default_command_key_fn('verify pm-dev-java'),
            default_command_key_fn('verify pm-dev-python'),
        }
        assert len(keys) == 4


#: ``(command args, key)`` for the normalizing half: whitespace and hyphens
#: become underscores, the ends are stripped, and an empty argument string falls
#: back to the literal ``default`` rather than to an empty key.
_COMMAND_KEY_NORMALIZATION_CASES = [
    ('', 'default'),
    ('compile', 'compile'),
    ('quality-gate', 'quality_gate'),
    ('clean verify', 'clean_verify'),
    ('  module-tests  ', 'module_tests'),
    ('module-tests plan-marshall', 'module_tests_plan_marshall'),
]

_COMMAND_KEY_NORMALIZATION_IDS = [
    'empty-string-falls-back-to-default',
    'single-word-is-unchanged',
    'hyphen-becomes-underscore',
    'space-becomes-underscore',
    'surrounding-whitespace-is-stripped',
    'spaces-and-hyphens-together',
]


class TestDefaultCommandKeyFnNormalization:
    """The function must normalize whitespace and hyphens to underscores
    so the resulting key is safe for use as a config/dedup identifier."""

    @pytest.mark.parametrize(
        'command_args,expected_key',
        _COMMAND_KEY_NORMALIZATION_CASES,
        ids=_COMMAND_KEY_NORMALIZATION_IDS,
    )
    def test_the_key_is_a_safe_identifier(self, command_args, expected_key):
        assert default_command_key_fn(command_args) == expected_key


def _noop(_args):
    return 0


def _parse_log_stub(*_args, **_kwargs):
    return []


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace:
    """Parse argv against a freshly-built parser.

    Uses parse_known_args so tests only need to supply the arguments they care
    about, without listing every required field of each subparser.
    """
    ns, _ = parser.parse_known_args(argv)
    return ns


class TestAddProjectDirArg:
    """Unit tests for the shared --project-dir helper."""

    def test_default_is_dot(self):
        parser = argparse.ArgumentParser()
        add_project_dir_arg(parser)
        ns = parser.parse_args([])
        assert ns.project_dir == '.'

    def test_override_via_long_flag(self):
        parser = argparse.ArgumentParser()
        add_project_dir_arg(parser)
        ns = parser.parse_args(['--project-dir', '/tmp/worktree'])
        assert ns.project_dir == '/tmp/worktree'

    def test_dest_is_project_dir_snake_case(self):
        parser = argparse.ArgumentParser()
        add_project_dir_arg(parser)
        ns = parser.parse_args(['--project-dir', '/a/b'])
        assert hasattr(ns, 'project_dir')
        # Underscore dest, not hyphen
        assert not hasattr(ns, 'project-dir')


#: ``(registration function, the argv that reaches that subcommand)`` — one row
#: per subparser the shared CLI registers individually. Each is built ALONE, so a
#: subcommand that only gets the flag through the declarative helper is not
#: credited here.
_SUBPARSER_REGISTRATIONS = [
    (lambda subs: add_run_subparser(subs).set_defaults(func=_noop), ['run', '--command-args', 'verify']),
    (lambda subs: add_parse_subparser(subs, _parse_log_stub), ['parse', '--log', '/tmp/build.log']),
    (lambda subs: add_coverage_subparser(subs).set_defaults(func=_noop), ['coverage-report']),
    (lambda subs: add_check_warnings_subparser(subs, _noop), ['check-warnings']),
]

_SUBPARSER_REGISTRATION_IDS = ['run', 'parse', 'coverage-report', 'check-warnings']

#: ``(extra argv, expected project_dir)`` — the flag left at its default, and the
#: flag supplied. Crossed with the registrations above, so every subparser is
#: checked on both.
_PROJECT_DIR_ARGV_CASES = [([], '.'), (['--project-dir', '/wt'], '/wt')]

_PROJECT_DIR_ARGV_IDS = ['default-is-dot', 'override-is-honoured']


class TestSubparserProjectDir:
    """Every individually-registered subparser exposes --project-dir."""

    @pytest.mark.parametrize('extra_argv,expected', _PROJECT_DIR_ARGV_CASES, ids=_PROJECT_DIR_ARGV_IDS)
    @pytest.mark.parametrize('register_fn,base_argv', _SUBPARSER_REGISTRATIONS, ids=_SUBPARSER_REGISTRATION_IDS)
    def test_subparser_carries_project_dir(self, register_fn, base_argv, extra_argv, expected):
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest='command', required=True)
        register_fn(subs)

        ns = _parse(parser, [*base_argv, *extra_argv])

        assert ns.project_dir == expected


#: The plan id every ``--plan-id`` row supplies.
_CANONICAL_PLAN_ID = 'task-routing-canonical'


def _build_full_parser() -> argparse.ArgumentParser:
    """The parser ``register_standard_subparsers`` produces with every slot filled."""
    fns = register_standard_subparsers(
        run_handler=_noop,
        parse_handler=_parse_log_stub,
        coverage_handler=_noop,
        check_warnings_handler=_noop,
    )
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    for fn in fns:
        fn(subs)
    return parser


def _registered_subcommands(parser: argparse.ArgumentParser) -> list[str]:
    """The subcommand names ``parser`` actually registered, sorted.

    Read off the live subparsers action rather than restated, so the sweeps
    below cover whatever ``register_standard_subparsers`` produces today.
    ``argparse`` exposes the registered choices only through the action object,
    hence the private class reference; sorting makes the row order stable.
    """
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return sorted(action.choices)
    raise AssertionError('the full parser registered no subparsers action')


#: The minimal argv each standard subcommand needs in order to parse at all,
#: keyed by subcommand name — a subcommand with no required flag maps to an
#: empty tuple. This is the one place a newly-registered subcommand has to be
#: named; the sweeps derive their rows from the live parser and look the argv up
#: here, and ``test_minimal_argv_covers_every_registered_subcommand`` fails
#: naming the omission when a subcommand is registered without an entry.
_STANDARD_MINIMAL_ARGV: dict[str, tuple[str, ...]] = {
    'run': ('--command-args', 'verify'),
    'parse': ('--log', '/tmp/log'),
    'coverage-report': (),
    'check-warnings': (),
}

_STANDARD_SUBCOMMANDS = _registered_subcommands(_build_full_parser())

#: ``(argv, expected project_dir)`` against the parser the declarative helper
#: builds. The default rows are derived one-per-registered-subcommand, so a
#: subparser added without ``add_project_dir_arg`` gets a row and fails; a
#: hand-written table could not fail for a subcommand it did not name. The two
#: override rows stay literal — they assert the flag is honoured when supplied,
#: which is a property of the flag and not of the subcommand set.
_STANDARD_PROJECT_DIR_CASES = [
    ([name, *_STANDARD_MINIMAL_ARGV[name]], '.') for name in _STANDARD_SUBCOMMANDS if name in _STANDARD_MINIMAL_ARGV
] + [
    (['run', '--command-args', 'verify', '--project-dir', '/plan/wt'], '/plan/wt'),
    (['parse', '--log', '/tmp/log', '--project-dir', '/plan/wt'], '/plan/wt'),
]

_STANDARD_PROJECT_DIR_IDS = [f'{name}-default' for name in _STANDARD_SUBCOMMANDS if name in _STANDARD_MINIMAL_ARGV] + [
    'run-override',
    'parse-override',
]


def test_minimal_argv_covers_every_registered_subcommand():
    """Every subcommand the full parser registers has a minimal-argv entry.

    The default-value sweep is derived from the live subcommand set but can only
    build a row for a subcommand whose minimal argv is known, so this is what
    turns a newly-registered subcommand into a named failure here rather than a
    row that silently never gets swept. The non-emptiness guard stops a parser
    that registered nothing from reducing the sweep to zero rows that pass by
    collecting nothing.
    """
    assert _STANDARD_SUBCOMMANDS, 'the full parser registered no subcommands'
    assert set(_STANDARD_SUBCOMMANDS) == set(_STANDARD_MINIMAL_ARGV)


class TestRegisterStandardSubparsersPropagation:
    """register_standard_subparsers must wire --project-dir into every
    standard subparser it produces. This is the end-to-end regression: if a
    new subparser is added without add_project_dir_arg, these tests catch it."""

    @pytest.mark.parametrize('argv,expected', _STANDARD_PROJECT_DIR_CASES, ids=_STANDARD_PROJECT_DIR_IDS)
    def test_every_standard_subcommand_carries_project_dir(self, argv, expected):
        assert _parse(_build_full_parser(), argv).project_dir == expected


#: ``(argv, expected plan_id)``. The ``None`` rows are what fails when a
#: subparser is registered without ``add_project_dir_arg``: the flag falls off
#: silently and auto-routing stops working for that subcommand alone.
_STANDARD_PLAN_ID_CASES = [
    (['run', '--command-args', 'verify'], None),
    (['run', '--command-args', 'verify', '--plan-id', _CANONICAL_PLAN_ID], _CANONICAL_PLAN_ID),
    (['parse', '--log', '/tmp/log'], None),
    (['parse', '--log', '/tmp/log', '--plan-id', _CANONICAL_PLAN_ID], _CANONICAL_PLAN_ID),
    (['coverage-report', '--plan-id', _CANONICAL_PLAN_ID], _CANONICAL_PLAN_ID),
    (['check-warnings', '--plan-id', _CANONICAL_PLAN_ID], _CANONICAL_PLAN_ID),
]

_STANDARD_PLAN_ID_IDS = [
    'run-default-is-none',
    'run-override',
    'parse-default-is-none',
    'parse-override',
    'coverage-report-override',
    'check-warnings-override',
]


class TestRegisterStandardSubparsersPlanIdPropagation:
    """Mirror of TestRegisterStandardSubparsersPropagation for the --plan-id flag.

    ``add_project_dir_arg`` registers BOTH ``--project-dir`` and ``--plan-id``
    so the four-state routing contract is uniform. These tests are the
    regression net: if a new subparser is added without
    ``add_project_dir_arg``, ``--plan-id`` would silently fall off and
    auto-routing breaks for that subcommand. The pre-existing
    ``--project-dir`` tests above continue to cover the escape-hatch path.
    """

    @pytest.mark.parametrize('argv,expected', _STANDARD_PLAN_ID_CASES, ids=_STANDARD_PLAN_ID_IDS)
    def test_every_standard_subcommand_carries_plan_id(self, argv, expected):
        assert _parse(_build_full_parser(), argv).plan_id == expected

    def test_run_accepts_both_flags_at_argparse_level(self):
        """Argparse accepts both flags; the resolver enforces mutual exclusion later."""
        ns = _parse(
            _build_full_parser(),
            [
                'run',
                '--command-args',
                'verify',
                '--plan-id',
                _CANONICAL_PLAN_ID,
                '--project-dir',
                '/plan/wt',
            ],
        )
        assert ns.plan_id == _CANONICAL_PLAN_ID
        assert ns.project_dir == '/plan/wt'


# D6 build-queue integration: these tests drive the factory's generated
# ``cmd_run`` end-to-end through the REAL ``build_queue_slot`` context manager.
# The queue acquire/release seam (``_acquire`` / ``_release_raw``) is mocked on
# the ``_build_queue_slot`` module, so the slot's admit / wait / release
# behaviour is exercised exactly as it runs in production while the build itself
# is replaced by a recorder. ``time.sleep`` is patched to a no-op (autouse) so
# the 60s blocked-poll wait is never actually slept.


class _QueueDouble:
    """Scriptable acquire/release double installed over ``_build_queue_slot``'s
    ``_acquire`` / ``_release_raw`` seams. Acquire responses are popped
    left-to-right (the last repeats); every release is recorded."""

    def __init__(self, acquire_responses: list[dict]):
        self._acquire_responses = list(acquire_responses)
        self.acquire_calls: list[str] = []
        self.release_calls: list[tuple[str, str]] = []

    def acquire(self, plan_id: str) -> dict:
        self.acquire_calls.append(plan_id)
        if not self._acquire_responses:
            return {'status': 'error', 'error': 'no scripted acquire response'}
        return self._acquire_responses.pop(0) if len(self._acquire_responses) > 1 else self._acquire_responses[0]

    def release(self, plan_id: str, admission_id: str) -> dict:
        self.release_calls.append((plan_id, admission_id))
        return {'status': 'success', 'action': 'released'}

    @property
    def released_ids(self) -> list[str]:
        return [aid for _plan, aid in self.release_calls]


class _ExecRecorder:
    """Records whether (and with what args) the factory's build body ran.

    The factory closure calls the module-level ``execute_direct_base`` to run
    the actual build. Patching ``factory.execute_direct_base`` with this
    recorder lets the integration tests assert the build ran exactly once
    (admitted paths) or never (saturation path) without spawning a real
    subprocess. The returned ``DirectCommandResult`` is a minimal success
    envelope so ``cmd_run_common`` (also stubbed below) is never reached on its
    parse path."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {
            'status': 'success',
            'exit_code': 0,
            'duration_seconds': 0,
            'log_file': '',
            'command': 'pw verify',
        }

    @property
    def ran(self) -> bool:
        return len(self.calls) > 0


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch):
    """Never actually sleep 60s in a unit test — patch the slot's time.sleep."""
    monkeypatch.setattr(bqs.time, 'sleep', lambda _s: None)


@pytest.fixture(autouse=True)
def _isolated_home_root(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Point the machine-global home root at a per-test ``tmp_path``.

    ``_record_resolution`` persists a per-plan fallback streak to
    ``home_root()/marshalld/fallback-streak.json``. Without this fixture that
    write lands in the developer's REAL ``~/.plan-marshall`` and ACCUMULATES
    across pytest runs, so a case asserting that a fallback still emits its
    per-build WARNING passes on a clean machine and fails on any machine that
    has run the suite more than ``_FALLBACK_WARN_STREAK`` times — the streak
    escalates once and suppresses the repeat from then on.

    That is a false signal in exactly the direction this suite exists to
    prevent: the test read green because of where it ran, not because of what
    the code did. Isolating the home root here makes the outcome a property of
    the code alone. It follows the same ``PLAN_MARSHALL_HOME`` convention every
    ``test/plan-marshall/build-server/`` module already uses.
    """
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / 'plan-marshall-home'))


def _make_config(*, with_resolve_fn: bool = True) -> factory.ExecuteConfig:
    """A minimal config for factory tests.

    By default ``with_resolve_fn=True`` installs an npm-style bypass
    (``wrapper_resolve_fn`` returning 'pw') so the queue-integration tests never
    touch the filesystem. Auto-detect tests pass ``with_resolve_fn=False`` to
    exercise the default detect-wrapper-then-fall-back-to-system path.
    """
    return factory.ExecuteConfig(
        tool_name='python',
        unix_wrapper='pw',
        windows_wrapper='pw.bat',
        system_fallback='pwx',
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        build_command_fn=factory.default_build_command_fn,
        scope_fn=lambda _a: 'default',
        command_key_fn=factory.default_command_key_fn,
        wrapper_resolve_fn=(lambda _project_dir: 'pw') if with_resolve_fn else None,
    )


def _install(monkeypatch: pytest.MonkeyPatch, double: _QueueDouble):
    """Install the queue double + exec recorder, and stub ``cmd_run_common`` to a
    no-op (it is downstream of the slot and not under test here). Returns
    (cmd_run, exec_recorder)."""
    monkeypatch.setattr(bqs, '_acquire', double.acquire)
    monkeypatch.setattr(bqs, '_release_raw', double.release)

    exec_recorder = _ExecRecorder()
    monkeypatch.setattr(factory, 'execute_direct_base', exec_recorder)
    # cmd_run_common runs AFTER the slot closes; stub it so the test does not
    # depend on the formatter / findings-store path.
    monkeypatch.setattr(factory, 'cmd_run_common', lambda **_kwargs: 0)

    _execute_direct, cmd_run = factory.create_execute_handlers(_make_config(), lambda *_a, **_k: ([], None, 'SUCCESS'))
    return cmd_run, exec_recorder


class TestFactoryCmdRunQueueAdmitted:
    """Admitted-immediately: the build runs once inside the slot and the slot is
    released."""

    def test_admitted_runs_build_once_inside_slot(self, monkeypatch):
        double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
        cmd_run, exec_recorder = _install(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 0
        assert exec_recorder.ran is True
        assert len(exec_recorder.calls) == 1
        assert 'P:uuid-1' in double.released_ids


class TestFactoryCmdRunQueueBlockedThenAdmitted:
    """Blocked-then-admitted: the first poll is blocked (sleep mocked), a later
    poll admits, and only then does the build run."""

    def test_blocked_then_admitted_waits_then_runs(self, monkeypatch):
        double = _QueueDouble(
            [
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
                {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-B'},
            ]
        )
        cmd_run, exec_recorder = _install(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        # The blocked id is NOT released before re-polling — re-poll is idempotent
        # so the plan keeps its FIFO position. Only the final admitted id is
        # released in the finally.
        assert 'P:uuid-A' not in double.released_ids
        assert double.released_ids == ['P:uuid-B']

    def test_blocked_then_admitted_sleeps_once_per_retry(self, monkeypatch):
        sleeps: list[int] = []
        monkeypatch.setattr(bqs.time, 'sleep', lambda s: sleeps.append(s))
        double = _QueueDouble(
            [
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-A'},
                {'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-B'},
                {'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-C'},
            ]
        )
        cmd_run, exec_recorder = _install(monkeypatch, double)

        cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        # Two blocked polls before admission → two 60s sleeps; build ran once.
        assert sleeps == [bqs._WAIT_SECONDS, bqs._WAIT_SECONDS]
        assert len(exec_recorder.calls) == 1


class TestFactoryCmdRunQueueSaturated:
    """Max-retries-exhausted: the queue stays blocked past max_retries, so
    cmd_run returns the structured ``queue_saturated`` error, releases the
    queued id, and NEVER runs the build."""

    def test_saturation_returns_structured_error_without_running_build(self, monkeypatch, capsys):
        monkeypatch.setattr(bqs, '_resolve_max_retries', lambda: 2)
        double = _QueueDouble([{'status': 'success', 'admission': 'blocked', 'id': 'P:uuid-X'}])
        cmd_run, exec_recorder = _install(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='P', format='toon'))

        assert rc == 1
        assert exec_recorder.ran is False
        out = capsys.readouterr().out
        assert factory.ERROR_QUEUE_SATURATED in out
        assert 'try again later' in out
        assert 'P' in out
        # The final queued id was released as cleanup before the timeout raise.
        assert 'P:uuid-X' in double.released_ids


class TestFactoryCmdRunPlanIdAbsentPassthrough:
    """plan_id-absent: pure passthrough — the build runs with ZERO queue
    interaction (the backward-compatibility guarantee for plan-less builds).

    ``NO_PLAN`` is included because ``build_main`` now resolves every absent
    ``--plan-id`` to that TRUTHY sentinel: it is the value a plan-less build
    actually arrives here with, so it — not the falsy cases — is what a
    falsiness-only guard would silently start queueing.
    """

    @pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
    def test_no_plan_id_runs_build_with_no_queue_interaction(self, monkeypatch, plan_id):
        double = _QueueDouble([])  # any acquire would record a call
        cmd_run, exec_recorder = _install(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id=plan_id, format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
        assert double.release_calls == []

    def test_missing_plan_id_attr_is_passthrough(self, monkeypatch):
        """A Namespace with no plan_id attribute at all (getattr default None)
        is also a pure passthrough."""
        double = _QueueDouble([])
        cmd_run, exec_recorder = _install(monkeypatch, double)

        rc = cmd_run(argparse.Namespace(command_args='verify', format='toon'))

        assert rc == 0
        assert len(exec_recorder.calls) == 1
        assert double.acquire_calls == []
        assert double.release_calls == []


class TestPlanIdThreadsThroughBothFactoryLayers:
    """``plan_id`` survives BOTH factory layers on its way to the log placement.

    The attribution crosses two seams inside this factory — ``cmd_run`` hands it
    to the in-process execute closure, and that closure hands it to
    ``execute_direct_base``, which is the call that reaches ``create_log_file``.
    Either seam can drop it independently, and a drop is silent: the build still
    succeeds, the log just lands under the wrong owner. Both are asserted here on
    the CONSTRUCTED call rather than on a resulting path, so a shared default can
    never make a dropped forward look correct.
    """

    def test_cmd_run_threads_a_real_plan_id_to_execute_direct_base(self, monkeypatch):
        double = _QueueDouble([{'status': 'success', 'admission': 'admitted', 'id': 'P:uuid-1'}])
        cmd_run, exec_recorder = _install(monkeypatch, double)

        cmd_run(argparse.Namespace(command_args='verify', plan_id='owning-plan', format='toon'))

        assert exec_recorder.calls[0]['plan_id'] == 'owning-plan'

    @pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
    def test_cmd_run_threads_a_plan_less_build_as_the_sentinel(self, monkeypatch, plan_id):
        """A plan-less build reaches the placement as NO_PLAN, never as ''.

        The empty string has no owning directory; the sentinel does. This is the
        same never-null contract the routing and ledger values carry.
        """
        double = _QueueDouble([])
        cmd_run, exec_recorder = _install(monkeypatch, double)

        cmd_run(argparse.Namespace(command_args='verify', plan_id=plan_id, format='toon'))

        assert exec_recorder.calls[0]['plan_id'] == NO_PLAN_SENTINEL

    def test_execute_direct_closure_forwards_plan_id_verbatim(self, monkeypatch, tmp_path):
        """The second seam in isolation: the closure forwards what it was given."""
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        execute_direct, _ = factory.create_execute_handlers(_make_config(), lambda *_a, **_k: ([], None, 'SUCCESS'))

        execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
            plan_id='owning-plan',
        )

        assert recorder.calls[0]['plan_id'] == 'owning-plan'

    def test_execute_direct_closure_requires_plan_id(self, monkeypatch, tmp_path):
        """``plan_id`` is keyword-only and mandatory on the generated closure."""
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        execute_direct, _ = factory.create_execute_handlers(_make_config(), lambda *_a, **_k: ([], None, 'SUCCESS'))

        with pytest.raises(TypeError):
            execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))


class TestResolveWrapperAutoDetect:
    """The factory-level wrapper auto-detection (the require_wrapper gate is gone).

    Drives the generated ``execute_direct`` directly (no queue), asserting that a
    present project wrapper resolves to the project wrapper, an absent wrapper
    falls back to the system binary (whether or not it is on PATH, and with NO
    FileNotFoundError raised during resolution), and the npm-style
    ``wrapper_resolve_fn`` bypass still wins. ``execute_direct_base`` is stubbed
    by a recorder so a resolved wrapper never spawns a real subprocess.
    """

    def _handlers(self, config):
        return factory.create_execute_handlers(config, lambda *_a, **_k: ([], None, 'SUCCESS'))

    def test_present_wrapper_resolves_project_wrapper(self, monkeypatch, tmp_path):
        """A present pw file → wrapper resolves to ./pw and the build body runs."""
        (tmp_path / 'pw').write_text('#!/bin/sh\n')
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
            plan_id='wrapper-detect-plan',
        )

        assert recorder.ran is True
        assert recorder.calls[0]['wrapper'] == './pw'

    def test_absent_wrapper_with_system_on_path_resolves_system_binary(self, monkeypatch, tmp_path):
        """No wrapper but system_fallback on PATH → resolves to the system binary,
        no raise."""
        monkeypatch.setattr(build_execute.shutil, 'which', lambda cmd: '/usr/bin/' + cmd)
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
            plan_id='wrapper-detect-plan',
        )

        assert result['status'] == 'success'
        assert recorder.calls[0]['wrapper'] == 'pwx'

    def test_absent_wrapper_without_system_on_path_still_resolves_system_binary(self, monkeypatch, tmp_path):
        """No wrapper AND system_fallback absent from PATH → resolution STILL
        returns the system binary string with NO FileNotFoundError. The gate that
        used to error here has been removed."""
        monkeypatch.setattr(build_execute.shutil, 'which', lambda _cmd: None)
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
            plan_id='wrapper-detect-plan',
        )

        assert result['status'] == 'success'
        assert recorder.calls[0]['wrapper'] == 'pwx'

    def test_wrapper_resolve_fn_bypasses_detection(self, monkeypatch, tmp_path):
        """An npm-style wrapper_resolve_fn config bypasses detection entirely and
        returns its own value unconditionally."""
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(with_resolve_fn=True)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(
            args='verify',
            command_key='python:verify',
            project_dir=str(tmp_path),
            plan_id='wrapper-detect-plan',
        )

        assert result['status'] == 'success'
        # wrapper_resolve_fn returns 'pw' unconditionally; no FileNotFoundError.
        assert recorder.calls[0]['wrapper'] == 'pw'


# =============================================================================
# D4 — client-side routed-verdict cross-check
# =============================================================================
# The daemon's child is a build wrapper that exits 0 even on a failed build and
# reports its real verdict in the emitted build TOON. ``_daemon_result_to_direct``
# no longer trusts a ``job_status: success`` blindly: it re-reads the job log's own
# verdict through the shared ``read_log_verdict`` and FAILS CLOSED when the verdict
# disagrees, so a lying / lagging daemon can never launder a failure into a green.


#: ``(daemon job_status, job-log text, command, rendered status, rendered
#: exit_code)``. A ``None`` log text means the log file is never written, so the
#: cross-check has nothing to read; a ``None`` exit_code means the row does not
#: pin one. The first two rows are the regression anchors — the daemon claims
#: success over a log that says otherwise — and the rest are what keeps the
#: cross-check from simply distrusting every success it is handed.
_DAEMON_CROSS_CHECK_CASES = [
    ('success', '[EXEC] ./pw verify\nstatus: error\nexit_code: 5\n', 'pw verify', 'error', 5),
    ('success', 'status: error\n', 'pw verify', 'error', 1),
    ('success', 'status: success\nexit_code: 0\n', 'pw verify', 'success', None),
    ('success', 'plain chatter with no build TOON at all\n', 'echo hi', 'success', None),
    ('success', None, 'echo hi', 'success', None),
    ('timeout', 'status: success\nexit_code: 0\n', 'pw verify', 'timeout', None),
]

_DAEMON_CROSS_CHECK_IDS = [
    'lying-success-over-an-error-log',
    'error-verdict-with-no-parseable-exit-code',
    'agreeing-success-verdict',
    'non-wrapper-log-yields-no-verdict',
    'log-file-was-never-written',
    'timeout-leg-ignores-a-contradicting-log',
]


class TestDaemonResultCrossCheck:
    """Unit coverage of the ``_daemon_result_to_direct`` verdict cross-check."""

    @pytest.mark.parametrize(
        'job_status,log_text,command,expected_status,expected_exit_code',
        _DAEMON_CROSS_CHECK_CASES,
        ids=_DAEMON_CROSS_CHECK_IDS,
    )
    def test_the_rendered_verdict_follows_the_job_log(
        self, tmp_path, job_status, log_text, command, expected_status, expected_exit_code
    ):
        log = tmp_path / 'job.log'
        if log_text is not None:
            log.write_text(log_text)

        result = factory._daemon_result_to_direct(
            {'job_status': job_status, 'log_file': str(log), 'duration_seconds': 4}, command
        )

        assert result['status'] == expected_status
        if expected_exit_code is not None:
            assert result['exit_code'] == expected_exit_code

    def test_killed_leg_ignores_a_contradicting_log(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\n')

        result = factory._daemon_result_to_direct(
            {'job_status': 'killed', 'log_file': str(log), 'duration_seconds': 2}, 'pw verify'
        )

        assert result['error'] == 'killed'
        assert 'do not blind-retry' in result['message']


class _ResultCapture:
    """Captures the ``result`` dict handed to the stubbed ``cmd_run_common`` so a
    routed / in-process ``cmd_run`` can be asserted on the rendered verdict shape
    without depending on the real formatter/parse path."""

    def __init__(self):
        self.result: dict | None = None

    def __call__(self, **kwargs):
        self.result = kwargs.get('result')
        return 0


class _FakeBuildServerClient:
    """A faked build-server client: preflight ready, submit accepted, and a
    scripted ``wait`` payload — so the routed path runs end-to-end through the
    real ``_daemon_result_to_direct`` cross-check under ``execution_mode=daemon``.

    Every ``plan_id`` the routing seam forwards is recorded on
    :attr:`forwarded_plan_ids`, so a test can assert WHICH value reached the
    daemon rather than only that routing happened."""

    def __init__(self, wait_payload: dict):
        self._wait_payload = wait_payload
        self.forwarded_plan_ids: list[tuple[str, str]] = []

    def run_preflight(self, _ns):
        return {'preflight': 'ready'}

    def run_submit(self, ns):
        self.forwarded_plan_ids.append(('submit', ns.plan_id))
        return {'status': 'success', 'job_id': 'J1'}

    def run_wait(self, ns):
        self.forwarded_plan_ids.append(('wait', ns.plan_id))
        return self._wait_payload


# =============================================================================
# The NO_PLAN sentinel across the routing / audit seams
# =============================================================================
#
# Two OPPOSITE dispositions live in this module, and both are asserted below
# because getting either backwards is silent:
#
# * ``_record_resolution`` treats the sentinel as ABSENT — it writes no plan
#   work log (a plan-less build has none), while its stderr line still fires.
# * ``_route_to_daemon`` FORWARDS the sentinel — routing and ledger values do
#   carry NO_PLAN, so the daemon's kind=job row matches the kind=build row's
#   never-null contract.


class TestRecordResolutionSentinelSuppressesWorkLog:
    """``_record_resolution``: the sentinel suppresses the work-log write only."""

    def _capture_log_entries(self, monkeypatch) -> list[tuple]:
        written: list[tuple] = []
        monkeypatch.setattr(factory, 'log_entry', lambda *args: written.append(args))
        return written

    @pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
    def test_plan_less_writes_no_work_log_but_still_emits_stderr(self, monkeypatch, capsys, plan_id):
        written = self._capture_log_entries(monkeypatch)

        factory._record_resolution('auto', 'in_process', 'socket_absent', 'n', plan_id)

        assert written == [], (
            f'plan_id={plan_id!r} wrote {written!r} to a plan work log; a '
            'plan-less build has no per-plan log to write to.'
        )
        err = capsys.readouterr().err
        assert '[BUILD-SERVER] resolved build' in err, (
            'the stderr emission is the ONLY sink a plan-less build has and must fire unconditionally'
        )

    def test_a_real_plan_id_still_writes_the_work_log(self, monkeypatch):
        """The carve-out is narrow — a real plan still gets its routing record.

        Without this counter-case a guard that suppressed the write outright
        would satisfy every assertion above while silently deleting the routing
        diagnostic for every plan-scoped build.
        """
        written = self._capture_log_entries(monkeypatch)

        factory._record_resolution('auto', 'in_process', 'socket_absent', 'n', 'a-real-plan')

        assert len(written) == 1
        assert written[0][1] == 'a-real-plan'


class TestRouteToDaemonForwardsTheSentinel:
    """``_route_to_daemon``: the sentinel IS the routing value, not an empty string."""

    @pytest.mark.allow_daemon_routing
    @pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
    def test_plan_less_routing_forwards_the_sentinel(self, monkeypatch, tmp_path, plan_id):
        monkeypatch.delenv(factory.MARSHALLD_JOB_ENV, raising=False)
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\n')
        client = _FakeBuildServerClient({'job_status': 'success', 'log_file': str(log), 'duration_seconds': 1})
        monkeypatch.setattr(factory, '_load_build_server', lambda: client)

        routed, reason = factory._route_to_daemon(_make_config(), str(tmp_path), plan_id)

        assert routed is not None, f'routing did not happen (reason={reason!r})'
        assert client.forwarded_plan_ids == [
            ('submit', NO_PLAN_SENTINEL),
            ('wait', NO_PLAN_SENTINEL),
        ], (
            f'plan_id={plan_id!r} was forwarded as {client.forwarded_plan_ids!r}; '
            'a plan-less build must submit and wait under the NO_PLAN sentinel '
            "so the daemon's kind=job row is never null / empty."
        )

    @pytest.mark.allow_daemon_routing
    def test_a_real_plan_id_is_forwarded_verbatim(self, monkeypatch, tmp_path):
        """The fallback must not overwrite a real plan id."""
        monkeypatch.delenv(factory.MARSHALLD_JOB_ENV, raising=False)
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\n')
        client = _FakeBuildServerClient({'job_status': 'success', 'log_file': str(log), 'duration_seconds': 1})
        monkeypatch.setattr(factory, '_load_build_server', lambda: client)

        factory._route_to_daemon(_make_config(), str(tmp_path), 'a-real-plan')

        assert client.forwarded_plan_ids == [
            ('submit', 'a-real-plan'),
            ('wait', 'a-real-plan'),
        ]


class TestEmitDaemonRequiredReportsTheSentinel:
    """The ``daemon_required`` envelope carries NO_PLAN, never the empty string."""

    @pytest.mark.parametrize('plan_id', _PLAN_LESS_PLAN_IDS, ids=_PLAN_LESS_PLAN_ID_IDS)
    def test_plan_less_envelope_reports_the_sentinel(self, monkeypatch, capsys, plan_id):
        monkeypatch.setattr(factory, 'log_entry', lambda *_a: None)

        rc = factory._emit_daemon_required('python', 'verify', 'json', 'socket_absent', 'n', plan_id)

        assert rc == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload['plan_id'] == NO_PLAN_SENTINEL


class TestCmdRunExecutionModeVerdict:
    """End-to-end ``cmd_run`` verdict truthfulness across execution modes: the
    in-process control and the routed daemon-lying case both surface ``error``."""

    def _handlers(self):
        return factory.create_execute_handlers(_make_config(), lambda *_a, **_k: ([], None, 'SUCCESS'))

    def test_in_process_failing_build_renders_error(self, monkeypatch):
        # (a) A genuinely failing build under --execution-mode in_process surfaces
        # error truthfully — the non-daemon control for the cross-check.
        failing = {
            'status': 'error',
            'exit_code': 2,
            'duration_seconds': 1,
            'log_file': '',
            'command': 'pw verify',
        }
        monkeypatch.setattr(factory, 'execute_direct_base', lambda **_k: failing)
        capture = _ResultCapture()
        monkeypatch.setattr(factory, 'cmd_run_common', capture)
        _ed, cmd_run = self._handlers()

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='', format='toon', execution_mode='in_process'))

        assert rc == 0
        assert capture.result is not None
        assert capture.result['status'] == 'error'

    @pytest.mark.allow_daemon_routing
    def test_daemon_mode_lying_success_is_failed_closed(self, monkeypatch, tmp_path):
        # (b) The daemon reports job_status: success over a failure-log; the
        # client cross-check catches the lying/lagging daemon and renders error.
        monkeypatch.delenv(factory.MARSHALLD_JOB_ENV, raising=False)
        log = tmp_path / 'job.log'
        log.write_text('status: error\nexit_code: 5\n')
        client = _FakeBuildServerClient({'job_status': 'success', 'log_file': str(log), 'duration_seconds': 4})
        monkeypatch.setattr(factory, '_load_build_server', lambda: client)
        capture = _ResultCapture()
        monkeypatch.setattr(factory, 'cmd_run_common', capture)
        _ed, cmd_run = self._handlers()

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='', format='toon', execution_mode='daemon'))

        assert rc == 0
        assert capture.result is not None
        assert capture.result['status'] == 'error'
        assert capture.result['exit_code'] == 5

    @pytest.mark.allow_daemon_routing
    def test_daemon_mode_genuine_success_stays_success(self, monkeypatch, tmp_path):
        monkeypatch.delenv(factory.MARSHALLD_JOB_ENV, raising=False)
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\n')
        client = _FakeBuildServerClient({'job_status': 'success', 'log_file': str(log), 'duration_seconds': 3})
        monkeypatch.setattr(factory, '_load_build_server', lambda: client)
        capture = _ResultCapture()
        monkeypatch.setattr(factory, 'cmd_run_common', capture)
        _ed, cmd_run = self._handlers()

        rc = cmd_run(argparse.Namespace(command_args='verify', plan_id='', format='toon', execution_mode='daemon'))

        assert rc == 0
        assert capture.result is not None
        assert capture.result['status'] == 'success'
