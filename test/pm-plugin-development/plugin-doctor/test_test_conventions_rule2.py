#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for Rule 2 (subprocess.run PYTHONPATH propagation) of doctor-test-conventions.

The rule walks every ``.py`` file under the test tree, locates calls of
the shape ``subprocess.run([sys.executable, ...])``, and emits a finding
when the call neither routes through ``conftest.run_script(...)`` nor
provides ``env=`` with ``PYTHONPATH`` derived from ``sys.path``. Lesson
``2026-05-02-01-001`` documents the original incident.
"""

import textwrap
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


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


def test_env_var_named_env_without_binding_flagged(tmp_path):
    """``env=env`` with no visible binding is flagged — the name alone proves nothing.

    The pre-fix heuristic trusted any ``env``/``subprocess_env``/``child_env``
    name by spelling; a bare parameter (or any unbound name) carries no
    PYTHONPATH evidence, so the kwarg test must prove the behavior, not the
    parameter name.
    """
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs(env):
            subprocess.run([sys.executable, '-c', 'print(1)'], env=env)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'subprocess-pythonpath'
    assert findings[0]['file'] == str(target)


def test_env_var_named_env_with_pythonpath_binding_passes(tmp_path):
    """``env=env`` passes when the visible binding constructs PYTHONPATH."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            env = {'PYTHONPATH': os.pathsep.join(sys.path)}
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


def test_m_module_invocation_passes(tmp_path):
    """Class 3: a ``-m`` stdlib invocation (py_compile) is exempt."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs(tmp_path):
            subprocess.run(
                [sys.executable, '-m', 'py_compile', str(tmp_path / 'x.py')],
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_m_neighbor_bare_run_without_m_still_flagged(tmp_path):
    """Closest genuine-violation neighbor of the ``-m`` class: a bare script
    invocation with no ``-m`` and no ``env=`` must still fire."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs():
            subprocess.run([sys.executable, 'scripts/run.py'], check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_deliberate_env_scrub_comprehension_passes(tmp_path):
    """Class 1: PYTHONPATH deliberately removed from a copied env is exempt.

    The comprehension over ``os.environ.items()`` with a ``not in`` guard on
    ``PYTHONPATH`` is the env-scrubbing shape (the removal is the test's
    intent, not a propagation defect).
    """
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            scrubbed_env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
            subprocess.run(
                [sys.executable, str(_EXECUTOR_PATH), '--help'],
                env=scrubbed_env,
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_scrub_neighbor_env_comprehension_without_guard_still_flagged(tmp_path):
    """Closest genuine-violation neighbor of the scrub class: the same
    comprehension family with no ``not in`` guard, still a plain copy."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            plain_env = {k: v for k, v in os.environ.items()}
            subprocess.run([sys.executable, '-c', 'print(1)'], env=plain_env, check=True)
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_helper_built_env_passes(tmp_path):
    """Class 2: an env built by a helper call is exempt (detector cannot see
    inside the call and trusts the helper to construct PYTHONPATH)."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def _subprocess_env():
            import os
            env = os.environ.copy()
            env['PYTHONPATH'] = os.pathsep.join(sys.path)
            return env

        def test_runs():
            subprocess.run(
                [sys.executable, str(_EXECUTOR_PATH), '--help'],
                env=_subprocess_env(),
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_helper_env_neighbor_inline_dict_without_pythonpath_still_flagged(tmp_path):
    """Closest genuine-violation neighbor of the helper class: the same intent
    spelled as an inline dict without a PYTHONPATH key must still fire."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs():
            subprocess.run(
                [sys.executable, '-c', 'print(1)'],
                env={'OTHER': '1'},
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_m_py_compile_literal_still_passes(tmp_path):
    """Class 3 (narrowed): the literal ``-m py_compile`` launcher stays exempt."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs(tmp_path):
            subprocess.run(
                [sys.executable, '-m', 'py_compile', str(tmp_path / 'x.py')],
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_m_unittest_repo_import_flagged(tmp_path):
    """Class 3 neighbor: ``-m unittest repo_pkg`` imports repo code via
    loadTestsFromName, so it must still fire."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import subprocess
        import sys

        def test_runs():
            subprocess.run(
                [sys.executable, '-m', 'unittest', 'repo_pkg'],
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)


def test_scrub_key_guard_passes(tmp_path):
    """Class 1 (narrowed): a ``not in`` guard on the KEY target stays exempt."""
    test_root = tmp_path / 'test'
    _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            scrubbed_env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH'}}
            subprocess.run(
                [sys.executable, str(_EXECUTOR_PATH), '--help'],
                env=scrubbed_env,
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert findings == []


def test_scrub_value_guard_over_items_pair_flagged(tmp_path):
    """Class 1 neighbor: ``if v not in {'PYTHONPATH'}`` over an ``items()``
    pair tests the value, scrubs nothing, and must still fire."""
    test_root = tmp_path / 'test'
    target = _write(
        test_root / 'foo' / 'test_thing.py',
        """
        import os
        import subprocess
        import sys

        def test_runs():
            scrubbed_env = {k: v for k, v in os.environ.items() if v not in {'PYTHONPATH'}}
            subprocess.run(
                [sys.executable, str(_EXECUTOR_PATH), '--help'],
                env=scrubbed_env,
                check=True,
            )
        """,
    )

    findings = analyze_subprocess_pythonpath(test_root)

    assert len(findings) == 1
    assert findings[0]['file'] == str(target)
