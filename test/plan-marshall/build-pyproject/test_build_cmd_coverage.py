#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for native coverage threshold enforcement in build.py::cmd_coverage.

Guards the single-resolver coverage-check contract: cmd_coverage must invoke
pytest with native --cov-fail-under and --cov-report=xml flags so the
phase-5-execute default:verify:coverage verify step requires only one
resolver call (architecture resolve --command coverage) — threshold
enforcement happens inside the build tool, not in a follow-up
build-pyproject:pyproject_build coverage-report dispatch.

See solution_outline.md deliverable 2 for the contract this guards.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUILD_PY = PROJECT_ROOT / 'build.py'


def _load_build_module():
    """Load build.py as an importable module for direct function exercise."""
    spec = importlib.util.spec_from_file_location('build_module_under_test', BUILD_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_coverage_threshold_constant_is_80() -> None:
    """The COVERAGE_THRESHOLD module-level constant is set to 80."""
    build_module = _load_build_module()
    assert build_module.COVERAGE_THRESHOLD == 80


def test_cmd_coverage_emits_cov_fail_under_flag() -> None:
    """cmd_coverage's pytest invocation includes --cov-fail-under={COVERAGE_THRESHOLD}."""
    build_module = _load_build_module()
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        captured['cmd'] = cmd
        return 0

    with patch.object(build_module, 'run', side_effect=fake_run):
        with patch.object(build_module.Path, 'mkdir', return_value=None):
            with patch.object(build_module, 'get_test_path', return_value='test/plan-marshall'):
                with patch.object(
                    build_module, 'get_bundle_path',
                    return_value='marketplace/bundles/plan-marshall',
                ):
                    exit_code = build_module.cmd_coverage('plan-marshall')

    assert exit_code == 0
    cmd = captured['cmd']
    expected_flag = f'--cov-fail-under={build_module.COVERAGE_THRESHOLD}'
    assert expected_flag in cmd, (
        f'cmd_coverage must emit {expected_flag!r}; got cmd={cmd!r}'
    )


def test_cmd_coverage_emits_xml_report_flag() -> None:
    """cmd_coverage's pytest invocation includes --cov-report=xml:.plan/temp/coverage.xml."""
    build_module = _load_build_module()
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        captured['cmd'] = cmd
        return 0

    with patch.object(build_module, 'run', side_effect=fake_run):
        with patch.object(build_module.Path, 'mkdir', return_value=None):
            with patch.object(build_module, 'get_test_path', return_value='test/plan-marshall'):
                with patch.object(
                    build_module, 'get_bundle_path',
                    return_value='marketplace/bundles/plan-marshall',
                ):
                    build_module.cmd_coverage('plan-marshall')

    cmd = captured['cmd']
    assert '--cov-report=xml:.plan/temp/coverage.xml' in cmd, (
        f'cmd_coverage must emit --cov-report=xml:.plan/temp/coverage.xml; got cmd={cmd!r}'
    )


def test_cmd_coverage_retains_existing_cov_and_html_report_flags() -> None:
    """cmd_coverage keeps the pre-existing --cov={bundle} and --cov-report=html flags."""
    build_module = _load_build_module()
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        captured['cmd'] = cmd
        return 0

    with patch.object(build_module, 'run', side_effect=fake_run):
        with patch.object(build_module.Path, 'mkdir', return_value=None):
            with patch.object(build_module, 'get_test_path', return_value='test/plan-marshall'):
                with patch.object(
                    build_module, 'get_bundle_path',
                    return_value='marketplace/bundles/plan-marshall',
                ):
                    build_module.cmd_coverage('plan-marshall')

    cmd = captured['cmd']
    assert '--cov=marketplace/bundles/plan-marshall' in cmd, (
        f'cmd_coverage must retain --cov=<bundle_path>; got cmd={cmd!r}'
    )
    assert '--cov-report=html:.plan/temp/htmlcov' in cmd, (
        f'cmd_coverage must retain --cov-report=html:.plan/temp/htmlcov; got cmd={cmd!r}'
    )
