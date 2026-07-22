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

from _poll_until import poll_until

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
    # _MARKETPLACE_SCRIPT_DIRS is only the DELTA conftest added to sys.path (the
    # dirs not already present), not the full marketplace script-dir set — its
    # composition shifts as skills are added. APPEND the inherited PYTHONPATH
    # (which carries the full set) rather than overwriting it, so the subprocess
    # can always resolve marshalld's cross-skill imports (e.g. _build_server_protocol
    # under script-shared) regardless of the delta's contents.
    inherited_pythonpath = env.get('PYTHONPATH', '')
    subprocess_dirs = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    env['PYTHONPATH'] = (
        subprocess_dirs + os.pathsep + inherited_pythonpath
        if inherited_pythonpath
        else subprocess_dirs
    )

    # The first fork's parent exits 0 immediately, so run returns fast.
    subprocess.run([sys.executable, '-c', code], env=env, timeout=30, check=True)

    # The reparented grandchild writes the file asynchronously; poll for it.
    poll_until(
        lambda: out_file.exists() and bool(out_file.read_text().strip()),
        timeout_seconds=10,
        description='double-forked grandchild to write its ppid',
    )

    assert out_file.exists(), 'double-forked grandchild never wrote its ppid'
    recorded_ppid = int(out_file.read_text().strip())
    assert recorded_ppid == 1, f'expected reparent to PID 1, got ppid={recorded_ppid}'
