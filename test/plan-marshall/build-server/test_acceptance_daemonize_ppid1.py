#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: the daemon double-forks and re-parents to PID 1.

Spawns a subprocess that imports marshalld, double-forks, and — after the
intermediate session leader exits — records its ppid. A correct double fork
re-parents the surviving grandchild to init, so the recorded ppid is 1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path

_SCRIPTS_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent


def test_daemon_reparents_to_pid_1(tmp_path):
    out_file = tmp_path / 'ppid.txt'
    code = textwrap.dedent(
        f"""
        import os, sys, time
        sys.path[:0] = {list(_MARKETPLACE_SCRIPT_DIRS)!r}
        sys.path.insert(0, {str(_SCRIPTS_DIR)!r})
        import marshalld
        marshalld.double_fork()
        time.sleep(0.5)
        with open({str(out_file)!r}, 'w') as fh:
            fh.write(str(os.getppid()))
        """
    )

    env = dict(os.environ)
    inherited = env.get('PYTHONPATH', '')
    subprocess_dirs = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    env['PYTHONPATH'] = subprocess_dirs + os.pathsep + inherited if inherited else subprocess_dirs

    subprocess.run([sys.executable, '-c', code], env=env, timeout=30, check=True)

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if out_file.exists() and out_file.read_text().strip():
            break
        time.sleep(0.1)

    assert out_file.exists(), 'double-forked grandchild never wrote its ppid'
    assert int(out_file.read_text().strip()) == 1
