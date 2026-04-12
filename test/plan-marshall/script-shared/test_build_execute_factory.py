#!/usr/bin/env python3
"""Tests for _build_execute_factory.py.

Focus on default_command_key_fn() scope-aware key generation:
the full command_args (including module scope) is normalized, so that
full-scope and module-scoped invocations of the same executable produce
distinct keys. This isolates adaptive-timeout learning per scope and
prevents cross-scope run-config key collisions.
"""

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
