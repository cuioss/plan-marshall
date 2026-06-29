#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the execution_tier verb parser in manage-execution-manifest.py.

``_parse_verification_command`` is the pure parser that extracts ``(verb,
command_args)`` from a Bucket-B build verification command. The compose suites
only ever invoke it via the ``_resolve_command_tier`` stubs with a known-good
command, so its many rejection arms (no executor token, wrong notation prefix,
missing ``run`` subcommand, missing / empty ``--command-args``, unbalanced
quoting) are otherwise unexercised. This module pins every arm directly, plus
``_verb_to_phase_5_step``'s mapping and ``_resolve_command_tier``'s two early
``None`` returns (non-build command, unresolvable executor).

Tier 2 (direct import) — all assertions run against the loaded module with no
subprocess spawn.
"""

import importlib.util
from pathlib import Path

import pytest

# Tier 2 direct import via importlib (kebab-case filename).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)
_spec = importlib.util.spec_from_file_location(
    '_mem_parse_verb', _SCRIPTS_DIR / 'manage-execution-manifest.py'
)
assert _spec is not None and _spec.loader is not None
_mem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mem)

_parse_verification_command = _mem._parse_verification_command
_verb_to_phase_5_step = _mem._verb_to_phase_5_step
_resolve_command_tier = _mem._resolve_command_tier

_EXECUTOR = '.plan/execute-script.py'
_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


def _build_cmd(command_args_token: str) -> str:
    """Compose a canonical Bucket-B build command with the given args token."""
    return f'python3 {_EXECUTOR} {_NOTATION} run --command-args {command_args_token}'


# =============================================================================
# _parse_verification_command — happy parses
# =============================================================================


class TestParseVerificationCommandHappy:
    """Well-formed build commands parse to (verb, command_args)."""

    def test_verb_and_module(self):
        """A two-token command_args yields the verb plus the verbatim args."""
        cmd = _build_cmd('"verify plan-marshall"')
        assert _parse_verification_command(cmd) == ('verify', 'verify plan-marshall')

    def test_verb_only(self):
        """A single-token command_args yields the verb with no module."""
        cmd = _build_cmd('"coverage"')
        assert _parse_verification_command(cmd) == ('coverage', 'coverage')

    def test_equals_form_command_args(self):
        """The ``--command-args=VALUE`` form parses identically to the spaced form."""
        cmd = f'python3 {_EXECUTOR} {_NOTATION} run --command-args=quality-gate'
        assert _parse_verification_command(cmd) == ('quality-gate', 'quality-gate')

    def test_bare_executor_path_suffix_matches(self):
        """An executor token not ending in ``.plan/...`` still matches via the
        ``execute-script.py`` suffix fallback."""
        cmd = f'python /abs/install/execute-script.py {_NOTATION} run --command-args "verify"'
        assert _parse_verification_command(cmd) == ('verify', 'verify')


# =============================================================================
# _parse_verification_command — rejection arms (return None)
# =============================================================================


class TestParseVerificationCommandRejections:
    """Non-build / malformed commands return None without raising."""

    def test_empty_string(self):
        """An empty command short-circuits to None."""
        assert _parse_verification_command('') is None

    def test_unbalanced_quoting_returns_none(self):
        """A shlex ValueError (unbalanced quote) is caught and returns None."""
        assert _parse_verification_command('python3 "unterminated') is None

    def test_no_executor_token(self):
        """A command with no execute-script.py token is not a build invocation."""
        assert _parse_verification_command('echo hello world') is None

    def test_notation_not_build_prefixed(self):
        """A non-``plan-marshall:build-`` notation returns None."""
        cmd = f'python3 {_EXECUTOR} plan-marshall:manage-files:manage-files list'
        assert _parse_verification_command(cmd) is None

    def test_missing_run_subcommand(self):
        """A build notation whose subcommand is not ``run`` returns None."""
        cmd = f'python3 {_EXECUTOR} {_NOTATION} describe --command-args "verify"'
        assert _parse_verification_command(cmd) is None

    def test_notation_token_absent_after_executor(self):
        """An executor token with nothing following it returns None."""
        assert _parse_verification_command(f'python3 {_EXECUTOR}') is None

    def test_command_args_flag_absent(self):
        """A ``run`` invocation with no ``--command-args`` flag returns None."""
        cmd = f'python3 {_EXECUTOR} {_NOTATION} run'
        assert _parse_verification_command(cmd) is None

    def test_command_args_empty_value(self):
        """A present-but-empty ``--command-args`` value returns None."""
        cmd = _build_cmd('""')
        assert _parse_verification_command(cmd) is None


# =============================================================================
# _verb_to_phase_5_step
# =============================================================================


class TestVerbToPhase5Step:
    """The four canonical build verbs map to their bare phase-5 step IDs."""

    @pytest.mark.parametrize(
        'verb,expected',
        [
            ('quality-gate', 'verify:quality-gate'),
            ('verify', 'verify:module-tests'),
            ('module-tests', 'verify:module-tests'),
            ('coverage', 'verify:coverage'),
        ],
    )
    def test_known_verbs_map(self, verb, expected):
        """Each known verb resolves to its mapped step ID."""
        assert _verb_to_phase_5_step(verb) == expected

    def test_unknown_verb_returns_none(self):
        """An unmapped verb (custom build target) resolves to None."""
        assert _verb_to_phase_5_step('package') is None


# =============================================================================
# _resolve_command_tier — early-return arms
# =============================================================================


class TestResolveCommandTierEarlyReturns:
    """_resolve_command_tier returns None before any subprocess for two cases."""

    def test_non_build_command_returns_none_without_subprocess(self, monkeypatch):
        """A command that fails the parser never reaches the executor lookup."""
        # If the executor resolver were consulted, this sentinel would raise.
        def _boom():
            raise AssertionError('_resolve_executor must not run for a non-build command')

        monkeypatch.setattr(_mem, '_resolve_executor', _boom)

        assert _resolve_command_tier('echo not-a-build-command', 'any-plan') is None

    def test_unresolvable_executor_returns_none(self, monkeypatch):
        """A well-formed build command with no resolvable executor returns None."""
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: None)

        cmd = _build_cmd('"verify plan-marshall"')
        assert _resolve_command_tier(cmd, 'any-plan') is None
