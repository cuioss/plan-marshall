#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Test that marshalld.double_fork() re-parents the daemon to PID 1.

Spawns a subprocess that imports marshalld, double-forks, and (after the
intermediate session leader exits) writes its ppid to a file. A correct double
fork re-parents the surviving grandchild to init, so the recorded ppid is 1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
SCRIPTS_DIR = SCRIPT_PATH.parent


def test_double_fork_reparents_to_pid_1(tmp_path):
    out_file = tmp_path / 'ppid.txt'
    code = textwrap.dedent(
        f"""
        import os, sys, time
        sys.path[:0] = {list(_MARKETPLACE_SCRIPT_DIRS)!r}
        sys.path.insert(0, {str(SCRIPTS_DIR)!r})
        import marshalld            # import BEFORE forking so import errors are visible
        marshalld.double_fork()
        time.sleep(0.5)             # let the intermediate session leader exit -> reparent to init
        with open({str(out_file)!r}, 'w') as fh:
            fh.write(str(os.getppid()))
        """
    )

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)

    # The first fork's parent exits 0 immediately, so run returns fast.
    subprocess.run([sys.executable, '-c', code], env=env, timeout=30, check=True)

    # The reparented grandchild writes the file asynchronously; poll for it.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if out_file.exists() and out_file.read_text().strip():
            break
        time.sleep(0.1)

    assert out_file.exists(), 'double-forked grandchild never wrote its ppid'
    recorded_ppid = int(out_file.read_text().strip())
    assert recorded_ppid == 1, f'expected reparent to PID 1, got ppid={recorded_ppid}'
