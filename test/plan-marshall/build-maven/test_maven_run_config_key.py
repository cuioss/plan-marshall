#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``run-config-key`` CLI subcommand on the build-maven skill.

The contract itself — TOON shape, ``--format json``, the canonical-args to
``key_suffix`` mapping, the ``compute_command_key`` round-trip drift guard, and
the missing-``--command-args`` error path — lives in
``build_test_helpers.assert_run_config_key_contract``. This module supplies only
what is genuinely Maven-specific: the entry script, the ``build_tool`` name,
Maven's own ``_CONFIG``, and the canonical lifecycle-phase / module-scoped args
strings.
"""

from build_test_helpers import assert_run_config_key_contract

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')

_CONFIG = load_script_module('plan-marshall', 'build-maven', '_maven_execute.py')._CONFIG

# Canonical Maven args: lifecycle phases and module-scoped invocations.
CANONICAL_ARGS = [
    'verify',
    'verify -pl core',
    'clean verify',
    'test',
    'compile',
]

#: ``(args, expected_suffix)`` pairs pinning ``default_command_key_fn`` under Maven.
SUFFIX_CASES = [
    ('verify', 'verify'),
    ('clean verify', 'clean_verify'),
    ('test', 'test'),
    ('compile', 'compile'),
    # default_command_key_fn underscore-joins tokens THEN replaces dashes
    # with underscores, so the dash in '-pl' becomes an extra underscore.
    ('verify -pl core', 'verify__pl_core'),
]


def test_run_config_key_contract():
    """Maven satisfies the whole ``run-config-key`` contract."""
    assert_run_config_key_contract(
        SCRIPT_PATH,
        'maven',
        CANONICAL_ARGS,
        config=_CONFIG,
        suffix_cases=SUFFIX_CASES,
    )
