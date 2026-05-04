#!/usr/bin/env python3
"""Tests for Rule 2 (subprocess.run PYTHONPATH propagation) of doctor-test-conventions.

The rule walks every ``.py`` file under the test tree, locates calls of
the shape ``subprocess.run([sys.executable, ...])``, and emits a finding
when the call neither routes through ``conftest.run_script(...)`` nor
provides ``env=`` with ``PYTHONPATH`` derived from ``sys.path``. Lesson
``2026-05-02-01-001`` documents the original incident.
"""

import importlib.util
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_analyze_test_conventions = _load_module('_analyze_test_conventions', '_analyze_test_conventions.py')
analyze_subprocess_pythonpath = _analyze_test_conventions.analyze_subprocess_pythonpath


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding='utf-8')
    return path


def test_bare_subprocess_run_flagged(tmp_path):
    """``subprocess.run([sys.executable, ...])`` without env= is flagged."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs():
            subprocess.run([sys.executable, '-c', 'print(1)'], check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == 'subprocess-pythonpath'
    assert finding['file'] == str(target)
    assert finding['severity'] == 'error'
    assert finding['details']['standard_anchor'] == 'doctor-test-conventions.md#subprocess-pythonpath'


def test_run_script_helper_call_passes(tmp_path):
    """A ``conftest.run_script`` invocation is exempt."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        from conftest import run_script

        def test_runs(plan_id):
            run_script('bundle:skill:script', '--plan-id', plan_id)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_explicit_env_pythonpath_dict_passes(tmp_path):
    """Passing env= dict with a PYTHONPATH key is exempt."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            env = os.environ.copy()
            env['PYTHONPATH'] = os.pathsep.join(sys.path)
            subprocess.run([sys.executable, '-c', 'print(1)'], env=env, check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_env_var_named_env_treated_as_pythonpath(tmp_path):
    """``env=env`` passes — the named binding is trusted by the heuristic."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs(env):
            subprocess.run([sys.executable, '-c', 'print(1)'], env=env)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_subprocess_run_without_sys_executable_ignored(tmp_path):
    """Calls whose first list element is not ``sys.executable`` are ignored."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess

        def test_runs():
            subprocess.run(['ls', '-la'], check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_bare_run_import_form_flagged(tmp_path):
    """``from subprocess import run`` followed by bare ``run(...)`` is in scope."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import sys
        from subprocess import run

        def test_runs():
            run([sys.executable, '-c', 'print(1)'], check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_dict_merge_form_with_pythonpath_passes(tmp_path):
    """``env=os.environ.copy() | {"PYTHONPATH": ...}`` exempts via dict-merge."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            subprocess.run(
                [sys.executable, '-c', 'print(1)'],
                env=os.environ.copy() | {'PYTHONPATH': os.pathsep.join(sys.path)},
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_env_dict_without_pythonpath_flagged(tmp_path):
    """An ``env={}`` dict without a PYTHONPATH key is still a violation."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs():
            subprocess.run([sys.executable, '-c', 'print(1)'], env={'OTHER': '1'})
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_lineno_reported_per_violation(tmp_path):
    """Each finding carries the call's source line."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_first():
            subprocess.run([sys.executable, '-c', 'print(1)'])

        def test_second():
            subprocess.run([sys.executable, '-c', 'print(2)'])
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 2
    linenos = sorted(f['line'] for f in findings)
    assert linenos[0] < linenos[1]


def test_missing_test_root_returns_empty(tmp_path):
    findings = analyze_subprocess_pythonpath(tmp_path / 'does-not-exist')
    assert findings == []
