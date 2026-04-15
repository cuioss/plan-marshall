#!/usr/bin/env python3
"""Tests for _build_execute_factory.py.

Focus on default_command_key_fn() scope-aware key generation:
the full command_args (including module scope) is normalized, so that
full-scope and module-scoped invocations of the same executable produce
distinct keys. This isolates adaptive-timeout learning per scope and
prevents cross-scope run-config key collisions.
"""

import argparse

from _build_cli import (
    add_check_warnings_subparser,
    add_coverage_subparser,
    add_parse_subparser,
    add_project_dir_arg,
    add_run_subparser,
    register_standard_subparsers,
)
from _build_execute_factory import default_command_key_fn


class TestDefaultCommandKeyFnEmpty:
    """Edge case: empty or missing command args fall back to 'default'."""

    def test_empty_string_returns_default(self):
        assert default_command_key_fn('') == 'default'


class TestDefaultCommandKeyFnScopeAware:
    """Scope-aware behavior: the full args contribute to the key so
    that module-scoped invocations don't collide with full-scope ones."""

    def test_unscoped_command_uses_full_args(self):
        # Full scope (no module) → just the command name, normalized.
        assert default_command_key_fn('module-tests') == 'module_tests'

    def test_scoped_command_includes_module(self):
        # Module-scoped → includes module suffix separated by underscore.
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


# =============================================================================
# Tests: --project-dir CLI propagation through register_standard_subparsers
# =============================================================================


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
