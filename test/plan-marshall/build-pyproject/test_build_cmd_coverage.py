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
import os
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


def _capture_coverage_cmd(build_module) -> tuple[list[str], int]:
    """Invoke cmd_coverage with run/prune/mkdir/path collaborators stubbed.

    Returns ``(pytest_cmd, exit_code)``.

    ⛔ ``_prune_basetemp_roots`` MUST be stubbed, and this helper is the single
    place that guarantees it. ``cmd_coverage`` calls ``_prepare_session_basetemp``,
    which prunes the REAL ``.plan/temp/pytest-basetemp/`` root — the very root the
    pytest session running this test is writing into. The prune walks newest-first
    and STOPS at the first session dir it cannot measure inside the remaining entry
    budget, retaining nothing beyond that point; a live session that has grown past
    ``PYTEST_BASETEMP_MAX_ENTRIES`` is therefore unmeasurable, retains zero, and is
    itself ``rmtree``d. Every later ``tmp_path`` / ``tmp_path_factory.mktemp`` in the
    run then raises ``FileNotFoundError``, which is a whole-suite outage attributed
    to whichever tests happened to run afterwards.

    That makes the damage a function of WHEN this module runs: early in a session the
    live root is small and survives the prune, late in one it does not. Running the
    suite in reverse collection order moves this module to the end and turns the
    latent hazard into ~1500 setup errors. The stub is what keeps the capture a pure
    argv observation — the per-session path itself is pure (pid + uuid) and needs no
    filesystem at all.
    """
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], description: str, env: dict[str, str] | None = None) -> int:
        captured['cmd'] = cmd
        return 0

    with patch.object(build_module, 'run', side_effect=fake_run):
        with patch.object(build_module, '_prune_basetemp_roots', return_value=None):
            with patch.object(build_module.Path, 'mkdir', return_value=None):
                with patch.object(build_module, 'get_test_path', return_value='test/plan-marshall'):
                    with patch.object(
                        build_module, 'get_bundle_path',
                        return_value='marketplace/bundles/plan-marshall',
                    ):
                        exit_code = build_module.cmd_coverage('plan-marshall')

    return captured['cmd'], exit_code


def test_cmd_coverage_emits_cov_fail_under_flag() -> None:
    """cmd_coverage's pytest invocation includes --cov-fail-under={COVERAGE_THRESHOLD}."""
    build_module = _load_build_module()

    cmd, exit_code = _capture_coverage_cmd(build_module)

    assert exit_code == 0
    expected_flag = f'--cov-fail-under={build_module.COVERAGE_THRESHOLD}'
    assert expected_flag in cmd, (
        f'cmd_coverage must emit {expected_flag!r}; got cmd={cmd!r}'
    )


def test_cmd_coverage_emits_xml_report_flag() -> None:
    """cmd_coverage's pytest invocation includes --cov-report=xml:.plan/temp/coverage.xml."""
    build_module = _load_build_module()

    cmd, _ = _capture_coverage_cmd(build_module)

    assert '--cov-report=xml:.plan/temp/coverage.xml' in cmd, (
        f'cmd_coverage must emit --cov-report=xml:.plan/temp/coverage.xml; got cmd={cmd!r}'
    )


def test_cmd_coverage_emits_xdist_parallel_flags() -> None:
    """cmd_coverage's pytest invocation includes ``-n auto --dist=loadgroup``.

    Coverage runs the identical full suite as module-tests; without xdist it
    runs serially on a single core and walls past the background-duration
    ceiling (it gets killed mid-suite). ``--dist=loadgroup`` must accompany
    ``-n`` so ``xdist_group`` markers stay pinned to one worker. This guards
    against a silent regression back to a serial coverage run.
    """
    build_module = _load_build_module()

    cmd, _ = _capture_coverage_cmd(build_module)

    assert '-n' in cmd and 'auto' in cmd[cmd.index('-n') + 1:cmd.index('-n') + 2], (
        f'cmd_coverage must emit "-n auto" for parallel coverage; got cmd={cmd!r}'
    )
    assert '--dist=loadgroup' in cmd, (
        f'cmd_coverage must emit --dist=loadgroup alongside -n; got cmd={cmd!r}'
    )


def test_cmd_coverage_retains_existing_cov_and_html_report_flags() -> None:
    """cmd_coverage keeps the pre-existing --cov={bundle} and --cov-report=html flags."""
    build_module = _load_build_module()

    cmd, _ = _capture_coverage_cmd(build_module)

    assert '--cov=marketplace/bundles/plan-marshall' in cmd, (
        f'cmd_coverage must retain --cov=<bundle_path>; got cmd={cmd!r}'
    )
    assert '--cov-report=html:.plan/temp/htmlcov' in cmd, (
        f'cmd_coverage must retain --cov-report=html:.plan/temp/htmlcov; got cmd={cmd!r}'
    )


def _extract_basetemp(cmd: list[str]) -> str:
    """Return the value of the single --basetemp=<path> flag in ``cmd`` (asserts exactly one)."""
    matches = [a for a in cmd if a.startswith('--basetemp=')]
    assert len(matches) == 1, f'expected exactly one --basetemp flag; got {matches!r} in {cmd!r}'
    return matches[0][len('--basetemp='):]


def test_cmd_coverage_emits_per_session_basetemp_flag() -> None:
    """cmd_coverage's pytest invocation carries --basetemp pointing under .plan/temp/pytest-basetemp/."""
    build_module = _load_build_module()
    cmd, _ = _capture_coverage_cmd(build_module)
    basetemp = _extract_basetemp(cmd)
    assert basetemp.startswith('.plan/temp/pytest-basetemp/'), (
        f'cmd_coverage --basetemp must point under .plan/temp/pytest-basetemp/; got {basetemp!r}'
    )


def test_cmd_coverage_two_invocations_yield_distinct_basetemp() -> None:
    """Two cmd_coverage invocations yield distinct per-session basetemp paths (no collision)."""
    build_module = _load_build_module()
    first = _extract_basetemp(_capture_coverage_cmd(build_module)[0])
    second = _extract_basetemp(_capture_coverage_cmd(build_module)[0])
    assert first != second, (
        f'two cmd_coverage invocations must yield distinct basetemp roots; got {first!r} twice'
    )


def test_prune_basetemp_roots_bounds_retained_dir_count(tmp_path) -> None:
    """_prune_basetemp_roots retains only the ``keep`` most-recent per-session dirs."""
    build_module = _load_build_module()
    root = tmp_path / 'pytest-basetemp'
    root.mkdir()
    for i in range(6):
        session_dir = root / f'session-{i}'
        session_dir.mkdir()
        # Stagger mtimes so newest-first ordering is deterministic.
        os.utime(session_dir, (i, i))

    with patch.object(build_module, 'PYTEST_BASETEMP_ROOT', root):
        build_module._prune_basetemp_roots(keep=3)

    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ['session-3', 'session-4', 'session-5'], (
        f'prune must retain exactly the 3 most-recent dirs; got {remaining!r}'
    )
