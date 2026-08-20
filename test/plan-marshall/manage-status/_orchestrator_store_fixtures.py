#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``orchestrator store`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the manage-status orchestrator store (kind=orchestrator, D5).

Covers:
- create/read/update-field/metadata round-trip under the orchestrator store
  (PLAN_BASE_DIR isolation via plan_context).
- kind=orchestrator schema fields validated on create.
- update-field validation: phase enum, list fields require JSON arrays,
  unknown fields rejected.
- CLI boundary: the new ``update-field`` verb and ``--store orchestrator``
  flags driven through the manage-status.py entry point.
- Default-store regression: plans-store calls remain byte-identical with and
  without the explicit ``--store plans`` flag.
"""


from argparse import Namespace

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_status_core_orchestrator')


cmd_orchestrator_create = _core.cmd_orchestrator_create


cmd_orchestrator_read = _core.cmd_orchestrator_read


cmd_orchestrator_update_field = _core.cmd_orchestrator_update_field


cmd_orchestrator_metadata = _core.cmd_orchestrator_metadata


def _create_args(slug: str, title: str = 'Test Epic', force: bool = False) -> Namespace:
    return Namespace(plan_id=slug, title=title, force=force)


def _orchestrator_status_file(plan_context, slug: str):
    return plan_context.fixture_dir / 'orchestrator' / slug / 'status.json'
