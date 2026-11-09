# SPDX-License-Identifier: FSL-1.1-ALv2
"""Registered system temp roots — the one place test support may create one.

A test-support module that calls :func:`tempfile.mkdtemp` directly leaves the
directory behind: nothing removes it, so every suite run adds to the system temp
tree until the tmpfs inode pool is exhausted. Two such sites (the relocated guard
harness root and the executor-mapping stub directory) did exactly that, and the
accumulated ``guard-node-*`` directories exhausted ``/tmp`` on the machine the
suite runs on.

:func:`create` is the sanctioned replacement. It creates the directory, records
it in a registry, AND registers an ``atexit`` removal at the create site, so:

* ``test/conftest.py::pytest_unconfigure`` drains the registry at the end of
  every pytest process — including each xdist worker, which the verify-first
  measurement confirmed runs that hook;
* a process that exits normally without pytest still leaves nothing behind,
  because the ``atexit`` handler runs in every process that created a root.

``test/plan-marshall/platform-runtime/test_tempdir_teardown.py`` enforces the
rule: a bare ``tempfile.mkdtemp`` call in a test module fails the suite.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path

#: Every root created by :func:`create` and not yet released.
_REGISTERED: list[Path] = []


def create(prefix: str = '') -> Path:
    """Create a system temp directory whose removal is registered.

    Args:
        prefix: The ``mkdtemp`` prefix, so the directory stays attributable in a
            process listing while it lives.

    Returns:
        The created directory.
    """
    root = Path(tempfile.mkdtemp(prefix=prefix))
    _REGISTERED.append(root)
    atexit.register(shutil.rmtree, root, True)
    return root


def release(root: Path) -> bool:
    """Remove one registered root.

    Args:
        root: The path returned by :func:`create`.

    Returns:
        Whether the path was registered (an unregistered path is left alone).
    """
    try:
        _REGISTERED.remove(root)
    except ValueError:
        return False
    shutil.rmtree(root, ignore_errors=True)
    return True


def release_all() -> int:
    """Remove every registered root; return how many were removed."""
    removed = 0
    while _REGISTERED:
        shutil.rmtree(_REGISTERED.pop(), ignore_errors=True)
        removed += 1
    return removed
