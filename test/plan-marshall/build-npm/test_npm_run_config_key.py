#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``run-config-key`` CLI subcommand on the build-npm skill.

The contract itself — TOON shape, ``--format json``, the canonical-args to
``key_suffix`` mapping, the ``compute_command_key`` round-trip drift guard, and
the missing-``--command-args`` error path — lives in
``build_test_helpers.assert_run_config_key_contract``. This module supplies only
what is genuinely npm-specific: the entry script, the ``build_tool`` name, npm's
own ``_CONFIG``, and the canonical script-invocation args strings.
"""

from build_test_helpers import assert_run_config_key_contract

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'build-npm', 'npm.py')

_CONFIG = load_script_module('plan-marshall', 'build-npm', '_npm_execute.py')._CONFIG

# Canonical npm args: script invocations (``test``, ``run build``, ``ci``),
# multi-token scripts that should be underscore-joined by
# ``default_command_key_fn``.
CANONICAL_ARGS = [
    'test',
    'run build',
    'ci',
    'install',
    'run lint',
]

#: ``(args, expected_suffix)`` pairs pinning ``default_command_key_fn`` under npm.
SUFFIX_CASES = [
    ('test', 'test'),
    ('ci', 'ci'),
    ('install', 'install'),
    # default_command_key_fn underscore-joins every token, dashes -> underscores
    ('run build', 'run_build'),
    ('run lint', 'run_lint'),
]


def test_run_config_key_contract():
    """npm satisfies the whole ``run-config-key`` contract."""
    assert_run_config_key_contract(
        SCRIPT_PATH,
        'npm',
        CANONICAL_ARGS,
        config=_CONFIG,
        suffix_cases=SUFFIX_CASES,
    )
