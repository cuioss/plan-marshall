#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Clean-environment executor-dispatch smoke tests.

These tests lock in the invariant that makes per-script ``sys.path`` bootstrap
boilerplate unnecessary: the generated executor (``.plan/execute-script.py``)
injects a ``PYTHONPATH`` covering every skill ``scripts/`` directory (and its
nested subdirectories) before it dispatches, so a dispatched script resolves all
its cross-skill imports without walking ancestors itself.

Each test invokes the real executor through a subprocess whose environment has
``PYTHONPATH`` **stripped**. If any dispatched script relied on its own
``sys.path`` bootstrap to find a shared module, that removal would surface here
as a non-zero exit — the previously runtime-only failure mode becomes
CI-visible. The notation set spans the coupling shapes that matter: a
library-heavy ``manage-*`` entry point, a nested ``script-shared/scripts/build``
consumer, the CI base library, the architecture resolver, and the two
executor-routed Claude hooks (enforcement + title render).
"""

import os
import subprocess
import sys

import pytest

from conftest import PROJECT_ROOT

EXECUTOR = PROJECT_ROOT / '.plan' / 'execute-script.py'

# (notation, args, stdin) — every entry must exit 0 under a PYTHONPATH-free env.
# --help drives argparse to a clean exit for CLI entry points; the hooks read a
# JSON payload on stdin and must fall through to a non-blocking exit.
_DISPATCH_CASES = [
    ('plan-marshall:manage-files:manage-files', ['--help'], None),
    ('plan-marshall:manage-architecture:architecture', ['--help'], None),
    ('plan-marshall:manage-tasks:manage-tasks', ['--help'], None),
    ('plan-marshall:manage-findings:manage-findings', ['--help'], None),
    ('plan-marshall:tools-integration-ci:ci', ['--help'], None),
    ('plan-marshall:tools-permission-doctor:permission_doctor', ['--help'], None),
    ('plan-marshall:plan-doctor:plan_doctor', ['--help'], None),
    ('plan-marshall:plan-marshall:phase_handshake', ['--help'], None),
    ('plan-marshall:build-pyproject:pyproject_build', ['--help'], None),
    ('pm-plugin-development:plugin-doctor:doctor-marketplace', ['--help'], None),
    (
        'plan-marshall:platform-runtime:claude_pretooluse_hook',
        [],
        '{"tool_name": "Bash", "tool_input": {"command": "ls"}}',
    ),
    (
        'plan-marshall:platform-runtime:claude_pretooluse_capture',
        [],
        '{"tool_name": "Bash", "tool_input": {"command": "ls"}}',
    ),
    (
        'plan-marshall:platform-runtime:platform_runtime',
        ['session', 'render-title'],
        None,
    ),
]


def _clean_env(sandbox: str) -> dict[str, str]:
    """Return the current environment with PYTHONPATH removed.

    Copies ``os.environ`` — so platform-required variables (``SystemRoot`` on
    Windows, ``LANG``, proxy settings, any virtualenv wiring) survive — and drops
    ONLY ``PYTHONPATH``, the single variable whose absence forces the dispatched
    script to rely on the executor's own path injection. ``PLAN_BASE_DIR`` is
    redirected to a per-test sandbox so no dispatch writes into the real
    ``.plan/`` tree.
    """
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PLAN_BASE_DIR'] = sandbox
    env['PLAN_DIR_NAME'] = '.plan'
    return env


@pytest.mark.parametrize('notation,args,stdin', _DISPATCH_CASES, ids=[c[0] for c in _DISPATCH_CASES])
def test_dispatch_resolves_without_pythonpath(notation, args, stdin, tmp_path):
    """Each notation dispatches to exit 0 with PYTHONPATH stripped from the env."""
    assert EXECUTOR.is_file(), f'executor not bootstrapped at {EXECUTOR} (conftest should generate it)'

    result = subprocess.run(
        [sys.executable, str(EXECUTOR), notation, *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=_clean_env(str(tmp_path)),
        timeout=120,
    )

    assert result.returncode == 0, (
        f'dispatch of {notation} failed under a PYTHONPATH-free env '
        f'(exit {result.returncode}). A missing cross-skill import here means a '
        f'per-script sys.path bootstrap was load-bearing after all.\n'
        f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
