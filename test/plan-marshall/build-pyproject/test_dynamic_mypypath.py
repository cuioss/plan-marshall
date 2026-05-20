#!/usr/bin/env python3
"""Regression tests for dynamic MYPYPATH resolution in build.py.

Guards against drift in collect_script_dirs() and removal of build.py's
_compute_mypypath() helper. See lesson-2026-04-13-005-mypypath-dynamic.
"""

import importlib.util
import os
from pathlib import Path

# conftest.py puts script-shared/scripts on PYTHONPATH
from marketplace_bundles import collect_script_dirs  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUNDLES_DIR = PROJECT_ROOT / 'marketplace' / 'bundles'
PLAN_MARSHALL_SCRIPTS = BUNDLES_DIR / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts'

CANONICAL_SUBDIRS = {
    PLAN_MARSHALL_SCRIPTS / 'build',
    PLAN_MARSHALL_SCRIPTS / 'extension',
    PLAN_MARSHALL_SCRIPTS / 'workflow',
    PLAN_MARSHALL_SCRIPTS / 'query',
}


def test_collect_script_dirs_includes_canonical_subdirs() -> None:
    """Ensures the four canonical script-shared subdirs are always collected."""
    collected = {Path(p) for p in collect_script_dirs(BUNDLES_DIR)}
    missing = CANONICAL_SUBDIRS - collected
    assert not missing, f'Missing canonical subdirs: {missing}'


def test_compute_mypypath_helper_exposes_subdirs() -> None:
    """Guards that build.py._compute_mypypath() returns the canonical subdirs."""
    build_py = PROJECT_ROOT / 'build.py'
    spec = importlib.util.spec_from_file_location('build_module_under_test', build_py)
    assert spec is not None and spec.loader is not None
    build_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_module)

    result = build_module._compute_mypypath()
    assert isinstance(result, str) and result, 'MYPYPATH must be a non-empty string'
    entries = {Path(p) for p in result.split(os.pathsep)}
    missing = CANONICAL_SUBDIRS - entries
    assert not missing, f'Missing canonical subdirs in MYPYPATH: {missing}'


def test_collect_script_dirs_covers_every_immediate_subdir() -> None:
    """Guards that collect_script_dirs covers every immediate scripts/ subdir on disk."""
    expected: set[Path] = set()
    for bundle in BUNDLES_DIR.iterdir():
        if not bundle.is_dir() or bundle.name.startswith('.'):
            continue
        skills_dir = bundle / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill in skills_dir.iterdir():
            if not skill.is_dir() or skill.name.startswith('.'):
                continue
            scripts_dir = skill / 'scripts'
            if not scripts_dir.is_dir():
                continue
            for child in scripts_dir.iterdir():
                if not child.is_dir():
                    continue
                if child.name == '__pycache__' or child.name.startswith('.'):
                    continue
                expected.add(child)

    collected = {Path(p) for p in collect_script_dirs(BUNDLES_DIR)}
    missing = expected - collected
    assert not missing, f'collect_script_dirs missing subdirs: {missing}'
