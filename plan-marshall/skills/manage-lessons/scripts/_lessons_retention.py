#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Retention-window resolution helpers for ``manage-lessons.py``.

Co-located helper module holding the ``system.retention`` config resolvers used
by the ``cleanup-superseded`` and ``retire-quiet`` commands. These resolvers are
wall-clock-independent (they read only marshal.json and CLI values) and are not
patched by any test, so they extract cleanly. The commands that consume them
(``cmd_cleanup_superseded`` / ``cmd_retire_quiet``) stay in the entry module
because their retention/quiet cutoffs read ``datetime.now`` under the test time
freeze.

This module imports only shared modules plus the co-located ``_lessons_crud``
default, so the entry module can re-import these names without an import cycle.
"""

import json

from _lessons_crud import (
    DEFAULT_ARCH_CONSTRAINT_QUIET_DAYS,
)
from file_ops import get_marshal_path

# Hard fallback for ``cleanup-superseded --retention-days`` when neither the
# CLI flag nor ``system.retention.lessons_superseded_days`` in marshal.json
# yields an integer. Matches the default seeded into ``DEFAULT_SYSTEM_RETENTION``
# (0 days — superseded stubs are pruned on the next cleanup invocation).
DEFAULT_LESSONS_SUPERSEDED_DAYS = 0


def _resolve_retention_setting(cli_value: int | None, config_key: str, fallback: int) -> int:
    """Resolve a ``system.retention`` integer setting.

    Precedence: ``cli_value`` (when not None) → ``system.retention.{config_key}``
    from marshal.json → ``fallback``. A missing or unreadable marshal.json silently
    falls through to the hard fallback so these commands remain usable on pre-init
    checkouts.
    """
    if cli_value is not None:
        return cli_value if cli_value >= 0 else fallback

    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return fallback

    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return fallback

    retention = config.get('system', {}).get('retention', {})
    value = retention.get(config_key)
    if isinstance(value, int) and value >= 0:
        return value
    return fallback


def _resolve_retention_days(cli_value: int | None) -> int:
    """Resolve effective ``retention_days`` for ``cleanup-superseded``."""
    return _resolve_retention_setting(cli_value, 'lessons_superseded_days', DEFAULT_LESSONS_SUPERSEDED_DAYS)


def _resolve_quiet_days(cli_value: int | None) -> int:
    """Resolve the effective retire-on-quiet window (days) for ``retire-quiet``."""
    return _resolve_retention_setting(cli_value, 'arch_constraint_quiet_days', DEFAULT_ARCH_CONSTRAINT_QUIET_DAYS)
