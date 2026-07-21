#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``run-config-key`` CLI subcommand on the build-pyproject skill.

The contract itself — TOON shape, ``--format json``, the canonical-args to
``key_suffix`` mapping, the ``compute_command_key`` round-trip drift guard, and
the missing-``--command-args`` error path — lives in
``build_test_helpers.assert_run_config_key_contract``. This module supplies only
what is genuinely pyproject-specific: the entry script, the ``build_tool`` name
(``python``, not ``pyproject``), pyproject's own ``_CONFIG``, and the canonical
args strings covering full scope, module scope, module-tests, and coverage.
"""

from build_test_helpers import assert_run_config_key_contract

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'build-pyproject', 'pyproject_build.py')

_CONFIG = load_script_module('plan-marshall', 'build-pyproject', '_pyproject_execute.py')._CONFIG

# Canonical args strings the build-pyproject skill is expected to handle.
# Covers full-scope ("verify"), module-scoped ("verify plan-marshall"),
# module-tests scope ("module-tests"), and coverage scope ("coverage <module>").
CANONICAL_ARGS = [
    'verify',
    'verify plan-marshall',
    'module-tests',
    'coverage pm-plugin-development',
    'quality-gate',
]

#: ``(args, expected_suffix)`` pairs pinning ``default_command_key_fn`` under pyproject.
SUFFIX_CASES = [
    ('verify', 'verify'),
    ('verify plan-marshall', 'verify_plan_marshall'),
    ('module-tests', 'module_tests'),
    ('module-tests plan-marshall', 'module_tests_plan_marshall'),
    ('coverage pm-plugin-development', 'coverage_pm_plugin_development'),
    ('quality-gate', 'quality_gate'),
]


def test_run_config_key_contract():
    """build-pyproject satisfies the whole ``run-config-key`` contract."""
    assert_run_config_key_contract(
        SCRIPT_PATH,
        'python',
        CANONICAL_ARGS,
        config=_CONFIG,
        suffix_cases=SUFFIX_CASES,
    )
