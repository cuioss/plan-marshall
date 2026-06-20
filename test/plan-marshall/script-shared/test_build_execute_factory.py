#!/usr/bin/env python3
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


class TestDefaultCommandKeyFnEmpty:
    """Edge case: empty or missing command args fall back to 'default'."""

    def test_empty_string_returns_default(self):
        assert default_command_key_fn('') == 'default'


class TestDefaultCommandKeyFnScopeAware:
    """Scope-aware behavior: the full args contribute to the key so
    that module-scoped invocations don't collide with full-scope ones."""

    def test_unscoped_command_uses_full_args(self):
        assert default_command_key_fn('module-tests') == 'module_tests'

    def test_scoped_command_includes_module(self):
        assert default_command_key_fn('module-tests plan-marshall') == 'module_tests_plan_marshall'

    def test_unscoped_and_scoped_do_not_collide(self):
        """Regression: full-scope and module-scoped must be distinct keys
        so adaptive timeouts learn per-scope values instead of mixing."""
        unscoped = default_command_key_fn('module-tests')
        scoped = default_command_key_fn('module-tests plan-marshall')
        assert unscoped != scoped

    def test_different_modules_produce_different_keys(self):
        """Two module-scoped invocations of the same command must not
        share a key — each module gets its own dedup slot."""
        a = default_command_key_fn('module-tests plan-marshall')
        b = default_command_key_fn('module-tests pm-plugin-development')
        assert a != b

    def test_different_commands_same_module_are_distinct(self):
        compile_key = default_command_key_fn('compile plan-marshall')
        tests_key = default_command_key_fn('module-tests plan-marshall')
        assert compile_key != tests_key

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


class TestDefaultCommandKeyFnNormalization:
    """The function must normalize whitespace and hyphens to underscores
    so the resulting key is safe for use as a config/dedup identifier."""

    def test_hyphens_replaced_with_underscores(self):
        assert default_command_key_fn('quality-gate') == 'quality_gate'

    def test_spaces_replaced_with_underscores(self):
        assert default_command_key_fn('clean verify') == 'clean_verify'

    def test_leading_and_trailing_whitespace_stripped(self):
        assert default_command_key_fn('  module-tests  ') == 'module_tests'

    def test_mixed_spaces_and_hyphens(self):
        assert default_command_key_fn('module-tests plan-marshall') == 'module_tests_plan_marshall'

    def test_simple_single_word(self):
        assert default_command_key_fn('compile') == 'compile'


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


class TestRunSubparserProjectDir:
    """run subparser must expose --project-dir with default '.'."""

    def _build(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest='command', required=True)
        run_parser = add_run_subparser(subs)
        run_parser.set_defaults(func=_noop)
        return parser

    def test_run_default_project_dir_is_dot(self):
        parser = self._build()
        ns = _parse(parser, ['run', '--command-args', 'verify'])
        assert ns.project_dir == '.'

    def test_run_accepts_project_dir_override(self):
        parser = self._build()
        ns = _parse(parser, ['run', '--command-args', 'verify', '--project-dir', '/work/tree'])
        assert ns.project_dir == '/work/tree'


class TestParseSubparserProjectDir:
    """parse subparser must expose --project-dir with default '.'."""

    def _build(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest='command', required=True)
        add_parse_subparser(subs, _parse_log_stub)
        return parser

    def test_parse_default_project_dir_is_dot(self):
        parser = self._build()
        ns = _parse(parser, ['parse', '--log', '/tmp/build.log'])
        assert ns.project_dir == '.'

    def test_parse_accepts_project_dir_override(self):
        parser = self._build()
        ns = _parse(parser, ['parse', '--log', '/tmp/build.log', '--project-dir', '/wt'])
        assert ns.project_dir == '/wt'


class TestCoverageSubparserProjectDir:
    """coverage-report subparser must expose --project-dir with default '.'."""

    def _build(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest='command', required=True)
        cov = add_coverage_subparser(subs)
        cov.set_defaults(func=_noop)
        return parser

    def test_coverage_default_project_dir_is_dot(self):
        parser = self._build()
        ns = _parse(parser, ['coverage-report'])
        assert ns.project_dir == '.'

    def test_coverage_accepts_project_dir_override(self):
        parser = self._build()
        ns = _parse(parser, ['coverage-report', '--project-dir', '/wt'])
        assert ns.project_dir == '/wt'


class TestCheckWarningsSubparserProjectDir:
    """check-warnings subparser must expose --project-dir with default '.'."""

    def _build(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest='command', required=True)
        add_check_warnings_subparser(subs, _noop)
        return parser

    def test_check_warnings_default_project_dir_is_dot(self):
        parser = self._build()
        ns = _parse(parser, ['check-warnings'])
        assert ns.project_dir == '.'

    def test_check_warnings_accepts_project_dir_override(self):
        parser = self._build()
        ns = _parse(parser, ['check-warnings', '--project-dir', '/wt'])
        assert ns.project_dir == '/wt'


class TestRegisterStandardSubparsersPropagation:
    """register_standard_subparsers must wire --project-dir into every
    standard subparser it produces. This is the end-to-end regression: if a
    new subparser is added without add_project_dir_arg, these tests catch it."""

    def _build_full_parser(self) -> argparse.ArgumentParser:
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

    def test_run_has_project_dir(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['run', '--command-args', 'verify'])
        assert ns.project_dir == '.'

    def test_parse_has_project_dir(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['parse', '--log', '/tmp/log'])
        assert ns.project_dir == '.'

    def test_coverage_has_project_dir(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['coverage-report'])
        assert ns.project_dir == '.'

    def test_check_warnings_has_project_dir(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['check-warnings'])
        assert ns.project_dir == '.'

    def test_run_override_end_to_end(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['run', '--command-args', 'verify', '--project-dir', '/plan/wt'])
        assert ns.project_dir == '/plan/wt'

    def test_parse_override_end_to_end(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['parse', '--log', '/tmp/log', '--project-dir', '/plan/wt'])
        assert ns.project_dir == '/plan/wt'


class TestRegisterStandardSubparsersPlanIdPropagation:
    """Mirror of TestRegisterStandardSubparsersPropagation for the --plan-id flag.

    ``add_project_dir_arg`` registers BOTH ``--project-dir`` and ``--plan-id``
    so the four-state routing contract is uniform. These tests are the
    regression net: if a new subparser is added without
    ``add_project_dir_arg``, ``--plan-id`` would silently fall off and
    auto-routing breaks for that subcommand. The pre-existing
    ``--project-dir`` tests above continue to cover the escape-hatch path.
    """

    def _build_full_parser(self) -> argparse.ArgumentParser:
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

    def test_run_default_plan_id_is_none(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['run', '--command-args', 'verify'])
        assert ns.plan_id is None

    def test_run_accepts_plan_id_override(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['run', '--command-args', 'verify', '--plan-id', 'task-routing-canonical'])
        assert ns.plan_id == 'task-routing-canonical'

    def test_parse_default_plan_id_is_none(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['parse', '--log', '/tmp/log'])
        assert ns.plan_id is None

    def test_parse_accepts_plan_id_override(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['parse', '--log', '/tmp/log', '--plan-id', 'task-routing-canonical'])
        assert ns.plan_id == 'task-routing-canonical'

    def test_coverage_accepts_plan_id_override(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['coverage-report', '--plan-id', 'task-routing-canonical'])
        assert ns.plan_id == 'task-routing-canonical'

    def test_check_warnings_accepts_plan_id_override(self):
        parser = self._build_full_parser()
        ns = _parse(parser, ['check-warnings', '--plan-id', 'task-routing-canonical'])
        assert ns.plan_id == 'task-routing-canonical'

    def test_run_accepts_both_flags_at_argparse_level(self):
        """Argparse accepts both flags; the resolver enforces mutual exclusion later."""
        parser = self._build_full_parser()
        ns = _parse(
            parser,
            [
                'run',
                '--command-args',
                'verify',
                '--plan-id',
                'task-routing-canonical',
                '--project-dir',
                '/plan/wt',
            ],
        )
        assert ns.plan_id == 'task-routing-canonical'
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


def _make_config(
    *,
    require_wrapper: bool = False,
    with_resolve_fn: bool = True,
    tool_name: str = 'python',
    unix_wrapper: str = 'pw',
    windows_wrapper: str = 'pw.bat',
    system_fallback: str = 'pwx',
) -> factory.ExecuteConfig:
    """A minimal config for factory tests.

    By default ``with_resolve_fn=True`` installs an npm-style bypass
    (``wrapper_resolve_fn`` returning 'pw') so the queue-integration tests never
    touch the filesystem. Gate tests pass ``with_resolve_fn=False`` to exercise
    the default detection + gate path, optionally with ``require_wrapper=True``.
    """
    return factory.ExecuteConfig(
        tool_name=tool_name,
        unix_wrapper=unix_wrapper,
        windows_wrapper=windows_wrapper,
        system_fallback=system_fallback,
        capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
        build_command_fn=factory.default_build_command_fn,
        scope_fn=lambda _a: 'default',
        command_key_fn=factory.default_command_key_fn,
        wrapper_resolve_fn=(lambda _project_dir: 'pw') if with_resolve_fn else None,
        require_wrapper=require_wrapper,
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
    interaction (the backward-compatibility guarantee for plan-less builds)."""

    @pytest.mark.parametrize('plan_id', [None, ''])
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


def _no_marshal(monkeypatch: pytest.MonkeyPatch):
    """Force the override read to find no marshal.json so the static default wins.

    Both ``_resolve_marshal_path`` (project_dir walk-up) and the
    ``get_marshal_path`` fallback are pointed at a non-existent path, so
    ``_read_require_wrapper_override`` always returns the passed default. Gate
    tests that want the static ``ExecuteConfig.require_wrapper`` to drive the
    behaviour install this first.
    """
    monkeypatch.setattr(factory, 'get_marshal_path', lambda: factory.Path('/nonexistent/.plan/marshal.json'))
    monkeypatch.setattr(
        factory, '_resolve_marshal_path', lambda _project_dir: factory.Path('/nonexistent/.plan/marshal.json')
    )


class TestResolveWrapperGate:
    """The factory-level require_wrapper gate (D1).

    Drives the generated ``execute_direct`` directly (no queue), asserting the
    four gate behaviours plus the npm-style ``wrapper_resolve_fn`` bypass.
    ``execute_direct_base`` is stubbed by a recorder so a resolved wrapper never
    spawns a real subprocess.
    """

    def _handlers(self, config):
        return factory.create_execute_handlers(config, lambda *_a, **_k: ([], None, 'SUCCESS'))

    def test_require_true_no_wrapper_returns_structured_error(self, monkeypatch, tmp_path):
        """(a) require_wrapper=True + empty dir → status:error, exit_code -1,
        error string carries the canonical 'No python wrapper found' message."""
        _no_marshal(monkeypatch)
        config = _make_config(require_wrapper=True, with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))

        assert result['status'] == 'error'
        assert result['exit_code'] == -1
        assert 'No python wrapper found' in result['error']
        assert '(pw or pw.bat)' in result['error']

    def test_require_true_present_wrapper_runs_build(self, monkeypatch, tmp_path):
        """(b) require_wrapper=True + a present pw file → wrapper resolves to
        ./pw and the build body runs."""
        _no_marshal(monkeypatch)
        (tmp_path / 'pw').write_text('#!/bin/sh\n')
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(require_wrapper=True, with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))

        assert recorder.ran is True
        assert recorder.calls[0]['wrapper'] == './pw'

    def test_require_false_no_wrapper_falls_back_to_system(self, monkeypatch, tmp_path):
        """(c) require_wrapper=False + no wrapper but system_fallback on PATH →
        resolves to system_fallback, no raise."""
        _no_marshal(monkeypatch)
        monkeypatch.setattr(build_execute.shutil, 'which', lambda cmd: '/usr/bin/' + cmd)
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(require_wrapper=False, with_resolve_fn=False)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))

        assert result['status'] == 'success'
        assert recorder.calls[0]['wrapper'] == 'pwx'

    def test_wrapper_resolve_fn_bypasses_gate_even_when_required(self, monkeypatch, tmp_path):
        """(e) an npm-style wrapper_resolve_fn config bypasses the gate entirely
        even when require_wrapper=True."""
        _no_marshal(monkeypatch)
        recorder = _ExecRecorder()
        monkeypatch.setattr(factory, 'execute_direct_base', recorder)
        config = _make_config(require_wrapper=True, with_resolve_fn=True)
        execute_direct, _ = self._handlers(config)

        result = execute_direct(args='verify', command_key='python:verify', project_dir=str(tmp_path))

        assert result['status'] == 'success'
        # wrapper_resolve_fn returns 'pw' unconditionally; no FileNotFoundError.
        assert recorder.calls[0]['wrapper'] == 'pw'


class TestReadRequireWrapperOverride:
    """(d) ``_read_require_wrapper_override`` reads build.{tool}.require_wrapper
    from marshal.json with graceful degradation to the passed default."""

    def _write_marshal(self, tmp_path, build_block):
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'marshal.json').write_text(json.dumps({'build': build_block}))
        return str(tmp_path)

    def test_reads_true(self, tmp_path):
        project_dir = self._write_marshal(tmp_path, {'maven': {'require_wrapper': True}})
        assert factory._read_require_wrapper_override('maven', project_dir, default=False) is True

    def test_reads_false(self, tmp_path):
        project_dir = self._write_marshal(tmp_path, {'maven': {'require_wrapper': False}})
        assert factory._read_require_wrapper_override('maven', project_dir, default=True) is False

    def test_missing_tool_block_returns_default(self, tmp_path):
        project_dir = self._write_marshal(tmp_path, {'gradle': {'require_wrapper': False}})
        assert factory._read_require_wrapper_override('maven', project_dir, default=True) is True

    def test_missing_require_wrapper_key_returns_default(self, tmp_path):
        project_dir = self._write_marshal(tmp_path, {'maven': {'something_else': 1}})
        assert factory._read_require_wrapper_override('maven', project_dir, default=True) is True

    def test_non_bool_value_returns_default(self, tmp_path):
        project_dir = self._write_marshal(tmp_path, {'maven': {'require_wrapper': 'yes'}})
        assert factory._read_require_wrapper_override('maven', project_dir, default=True) is True

    def test_missing_file_returns_default(self, tmp_path, monkeypatch):
        # No marshal.json anywhere; both resolution paths point at a non-file.
        monkeypatch.setattr(factory, 'get_marshal_path', lambda: factory.Path('/nonexistent/.plan/marshal.json'))
        assert factory._read_require_wrapper_override('maven', str(tmp_path), default=True) is True
