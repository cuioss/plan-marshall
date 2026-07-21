#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``run-config-key`` CLI subcommand on the build-gradle skill.

The contract itself — TOON shape, ``--format json``, the canonical-args to
``key_suffix`` mapping, the ``compute_command_key`` round-trip drift guard, and
the missing-``--command-args`` error path — lives in
``build_test_helpers.assert_run_config_key_contract``. This module supplies only
what is genuinely Gradle-specific: the entry script, the ``build_tool`` name,
Gradle's own ``_CONFIG``, and the canonical args strings that exercise
``_gradle_command_key_fn`` (only the first task is used, leading colons are
stripped, and inner colons become underscores).
"""

from build_test_helpers import assert_run_config_key_contract

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'build-gradle', 'gradle.py')

_CONFIG = load_script_module('plan-marshall', 'build-gradle', '_gradle_execute.py')._CONFIG

# Canonical Gradle args: lifecycle tasks, leading-colon project tasks, and
# multi-task invocations (only the first task drives the key under
# ``_gradle_command_key_fn``).
CANONICAL_ARGS = [
    'build',
    ':build',
    'test',
    'build test',
    'check',
    ':core:build',
]

#: ``(args, expected_suffix)`` pairs pinning Gradle's key-function semantics.
SUFFIX_CASES = [
    ('build', 'build'),
    # Leading colon stripped by _gradle_command_key_fn
    (':build', 'build'),
    ('test', 'test'),
    # Only the first task drives the key (Gradle-specific behaviour)
    ('build test', 'build'),
    # Project-qualified task path: inner colons become underscores
    (':core:build', 'core_build'),
]


def test_run_config_key_contract():
    """Gradle satisfies the whole ``run-config-key`` contract."""
    assert_run_config_key_contract(
        SCRIPT_PATH,
        'gradle',
        CANONICAL_ARGS,
        config=_CONFIG,
        suffix_cases=SUFFIX_CASES,
    )
