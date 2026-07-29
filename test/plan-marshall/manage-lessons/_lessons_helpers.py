#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared test helpers for the per-subcommand test_manage_lessons_* suites.

This module is the domain-prefixed home for the imports, the ``_FakeDatetime``
freezer, and the ``SCRIPT_PATH`` constant that the split-out per-subcommand
test files share. Naming the file ``_lessons_helpers.py`` rather than
``_fixtures.py`` / ``_helpers.py`` keeps it disambiguated from generic helper
modules that other test directories may introduce.

The hyphenated production script ``manage-lessons.py`` is loaded once via
``conftest.load_script_module`` — the single loading convention for the suite —
and re-exported as ``_mod`` plus the individual ``cmd_*`` callables and
``get_next_id``. The test files import from this module to avoid each suite
re-paying the module-load cost.
"""

from conftest import MARKETPLACE_ROOT, load_script_module

# Script path used by both direct-import and subprocess (CLI plumbing) tests.
SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-lessons'
    / 'scripts'
    / 'manage-lessons.py'
)

# Tier 2 direct imports — the hyphenated filename is not importable by name, so
# the module is registered under the underscored ``manage_lessons`` alias.
_mod = load_script_module('plan-marshall', 'manage-lessons', 'manage-lessons.py', 'manage_lessons')

# Re-exports — the per-subcommand test files import these names.
cmd_add = _mod.cmd_add
cmd_consult = _mod.cmd_consult
cmd_get = _mod.cmd_get
cmd_list = _mod.cmd_list
cmd_update = _mod.cmd_update
cmd_convert_to_plan = _mod.cmd_convert_to_plan
cmd_restore_from_plan = _mod.cmd_restore_from_plan
cmd_list_stalled = _mod.cmd_list_stalled
cmd_from_error = _mod.cmd_from_error
cmd_remove = _mod.cmd_remove
cmd_supersede = _mod.cmd_supersede
cmd_cleanup_superseded = _mod.cmd_cleanup_superseded
cmd_set_body = _mod.cmd_set_body
get_next_id = _mod.get_next_id


class _FakeDatetime:
    """Stand-in for ``datetime.datetime`` that freezes a single instant.

    The module under test imports ``from datetime import UTC, datetime`` and
    calls ``datetime.now(UTC)``. Tests monkeypatch ``_mod.datetime`` with this
    fake so ID generation becomes deterministic regardless of the host
    timezone or wall clock.

    ``fixed_now`` is an *instant*, not a wall-clock reading: pass an aware
    datetime (typically UTC) and both branches project that one instant into
    the requested zone, so a test can pin an instant whose local date and UTC
    date differ and observe how the module under test reads it. A naive
    ``fixed_now`` is interpreted as local time by both branches, which is why
    the pre-existing naive fixtures keep their wall-clock values.
    """

    def __init__(self, fixed_now):
        self._fixed_now = fixed_now

    def now(self, tz=None):  # noqa: D401 - mirrors datetime API
        if tz is None:
            # ``datetime.now()`` returns the LOCAL wall clock with no tzinfo —
            # project the instant into the local zone first, then strip.
            return self._fixed_now.astimezone().replace(tzinfo=None)
        return self._fixed_now.astimezone(tz)
