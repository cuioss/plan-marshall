#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage-locks`` test modules.

Holds the definitions used by modules of MORE THAN ONE unit in this
directory. A definition used by one unit belongs in that unit's own
helper; this file is for what genuinely crosses them.
"""

from __future__ import annotations

from pathlib import Path


def _write_lock(lock_path: Path, holder: str) -> None:
    """Stage a held lock file recording ``holder`` (mirrors _try_atomic_create)."""
    lock_path.write_text(holder + '\n', encoding='utf-8')
