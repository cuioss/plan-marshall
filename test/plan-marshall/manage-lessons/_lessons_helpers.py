#!/usr/bin/env python3
"""Shared test helpers for the per-subcommand test_manage_lessons_* suites.

This module is the domain-prefixed home for the imports, the ``_FakeDatetime``
freezer, and the ``SCRIPT_PATH`` constant that the split-out per-subcommand
test files share. Naming the file ``_lessons_helpers.py`` rather than
``_fixtures.py`` / ``_helpers.py`` keeps it disambiguated from generic helper
modules that other test directories may introduce.

The hyphenated production script ``manage-lessons.py`` is loaded once via
``importlib.util.spec_from_file_location`` and re-exported as ``_mod`` plus
the individual ``cmd_*`` callables and ``get_next_id``. The test files
import from this module to avoid each suite re-paying the importlib cost.
"""

import importlib.util

from conftest import MARKETPLACE_ROOT

# Script path used by both direct-import and subprocess (CLI plumbing) tests.
SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-lessons'
    / 'scripts'
    / 'manage-lessons.py'
)

# Tier 2 direct imports — load hyphenated module via importlib.
_MANAGE_LESSONS_SCRIPT = str(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('manage_lessons', _MANAGE_LESSONS_SCRIPT)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-exports — the per-subcommand test files import these names.
cmd_add = _mod.cmd_add
cmd_get = _mod.cmd_get
cmd_list = _mod.cmd_list
cmd_update = _mod.cmd_update
cmd_convert_to_plan = _mod.cmd_convert_to_plan
cmd_restore_from_plan = _mod.cmd_restore_from_plan
cmd_from_error = _mod.cmd_from_error
cmd_remove = _mod.cmd_remove
cmd_supersede = _mod.cmd_supersede
cmd_cleanup_superseded = _mod.cmd_cleanup_superseded
cmd_set_body = _mod.cmd_set_body
get_next_id = _mod.get_next_id


class _FakeDatetime:
    """Stand-in for ``datetime.datetime`` that returns a fixed aware ``now()``.

    The module under test calls ``datetime.now().astimezone()`` at the module
    level import ``from datetime import UTC, datetime``. Tests monkeypatch
    ``_mod.datetime`` with this fake so ID generation becomes deterministic
    regardless of the host timezone or wall clock.
    """

    def __init__(self, fixed_now):
        self._fixed_now = fixed_now

    def now(self, tz=None):  # noqa: D401 - mirrors datetime API
        if tz is None:
            # Strip tzinfo to mimic the naive ``datetime.now()`` behaviour so
            # the subsequent ``.astimezone()`` call attaches the local tz.
            return self._fixed_now.replace(tzinfo=None)
        return self._fixed_now.astimezone(tz)
