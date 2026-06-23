# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the in-repo SPDX-header enforcement wired into build.py.

Covers ``check_spdx_headers`` (the pure helper) and the ``cmd_quality_gate``
wiring that fails the build when any project-owned ``.py`` file lacks the
``# SPDX-License-Identifier: FSL-1.1-ALv2`` header.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_PY = PROJECT_ROOT / 'build.py'

HEADER = '# SPDX-License-Identifier: FSL-1.1-ALv2'


def _load_build_module():
    """Load the repo-root build.py as an importable module."""
    spec = importlib.util.spec_from_file_location('build_under_test', BUILD_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules['build_under_test'] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def build():
    return _load_build_module()


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
# check_spdx_headers — the pure helper
# ---------------------------------------------------------------------------


def test_compliant_files_yield_no_offenders(build, tmp_path):
    _write(tmp_path / 'plain.py', [HEADER, 'x = 1'])
    _write(tmp_path / 'shebang.py', ['#!/usr/bin/env python3', HEADER, 'y = 2'])
    _write(tmp_path / 'cookie.py', ['# -*- coding: utf-8 -*-', HEADER, 'z = 3'])
    _write(tmp_path / 'shebang_cookie.py', ['#!/usr/bin/env python3', '# -*- coding: utf-8 -*-', HEADER, 'w = 4'])

    offenders = build.check_spdx_headers([str(tmp_path)])

    assert offenders == []


def test_missing_header_is_flagged(build, tmp_path):
    _write(tmp_path / 'good.py', [HEADER, 'ok = True'])
    bad = tmp_path / 'bad.py'
    _write(bad, ['import os', 'print(os.getcwd())'])

    offenders = build.check_spdx_headers([str(tmp_path)])

    assert offenders == [str(bad)]


def test_wrong_header_is_flagged(build, tmp_path):
    bad = tmp_path / 'wrong.py'
    _write(bad, ['# SPDX-License-Identifier: AGPL-3.0-only', 'v = 1'])

    offenders = build.check_spdx_headers([str(tmp_path)])

    assert offenders == [str(bad)]


def test_header_after_shebang_must_be_present(build, tmp_path):
    # A shebang with the header missing immediately after is an offender.
    bad = tmp_path / 'shebang_only.py'
    _write(bad, ['#!/usr/bin/env python3', 'import sys'])

    offenders = build.check_spdx_headers([str(tmp_path)])

    assert offenders == [str(bad)]


def test_single_file_path_is_checked_directly(build, tmp_path):
    bad = tmp_path / 'build_like.py'
    _write(bad, ['import os'])

    offenders = build.check_spdx_headers([str(bad)])

    assert offenders == [str(bad)]


def test_non_py_and_missing_paths_are_ignored(build, tmp_path):
    (tmp_path / 'notes.txt').write_text('no header here', encoding='utf-8')

    offenders = build.check_spdx_headers([str(tmp_path / 'notes.txt'), str(tmp_path / 'does-not-exist')])

    assert offenders == []


# ---------------------------------------------------------------------------
# cmd_quality_gate — the wiring (behavioural)
# ---------------------------------------------------------------------------


def test_quality_gate_fails_when_header_missing(build, tmp_path, monkeypatch):
    """A module-scoped quality-gate fails (non-zero) when an in-scope file lacks the header.

    Drives the real cmd_quality_gate path with the heavy external steps
    (mypy/ruff) stubbed to success, so only the SPDX-header check decides the
    outcome. The temp tree carries one compliant and one missing-header file.
    """
    bundle = tmp_path / 'bundles' / 'mod'
    test_dir = tmp_path / 'tests' / 'mod'
    _write(bundle / 'good.py', [HEADER, 'ok = True'])
    _write(test_dir / 'bad.py', ['import os'])  # missing header

    # Stub mypy/ruff/doctor so cmd_compile and the ruff run both succeed; the
    # SPDX check is the only gate that can fail.
    monkeypatch.setattr(build, 'cmd_compile', lambda module: 0)
    monkeypatch.setattr(build, 'run', lambda *a, **k: 0)
    # Point the module-scoped bundle/test resolution at the temp tree.
    monkeypatch.setattr(build, 'get_bundle_path', lambda module: str(bundle))
    monkeypatch.setattr(build, 'get_test_path', lambda module: str(test_dir))

    exit_code = build.cmd_quality_gate('mod')

    assert exit_code == 1


def test_quality_gate_passes_when_all_headers_present(build, tmp_path, monkeypatch):
    bundle = tmp_path / 'bundles' / 'mod'
    test_dir = tmp_path / 'tests' / 'mod'
    _write(bundle / 'good.py', [HEADER, 'ok = True'])
    _write(test_dir / 'also_good.py', [HEADER, 'fine = True'])

    monkeypatch.setattr(build, 'cmd_compile', lambda module: 0)
    monkeypatch.setattr(build, 'run', lambda *a, **k: 0)
    monkeypatch.setattr(build, 'get_bundle_path', lambda module: str(bundle))
    monkeypatch.setattr(build, 'get_test_path', lambda module: str(test_dir))

    exit_code = build.cmd_quality_gate('mod')

    assert exit_code == 0
