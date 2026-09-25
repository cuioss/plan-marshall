#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-files.py script."""

import json
import os
import shutil
from pathlib import Path

import pytest

from conftest import get_script_path, get_test_fixture_dir, load_script_module, parse_ns, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-files', 'manage-files.py')

# Tier 2 direct imports - load hyphenated module via importlib
_mod = load_script_module('plan-marshall', 'manage-files', 'manage-files.py', 'manage_files')

cmd_read = _mod.cmd_read
cmd_write = _mod.cmd_write
cmd_remove = _mod.cmd_remove
cmd_list = _mod.cmd_list
cmd_exists = _mod.cmd_exists
cmd_mkdir = _mod.cmd_mkdir
cmd_create_or_reference = _mod.cmd_create_or_reference


# =============================================================================
# Helper: EmptyPlanContext (no pre-created plan directory)
# =============================================================================


class EmptyPlanContext:
    """Context manager for test WITHOUT pre-created plan directory."""

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self):
        self.fixture_dir = None
        self._is_standalone = False
        # One MonkeyPatch owns PLAN_BASE_DIR / PLAN_DIR_NAME; reverted atomically
        # by undo() in __exit__ (matches PlanContext and the autouse sandbox).
        self._mp = None

    def __enter__(self):
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        self._mp = pytest.MonkeyPatch()
        self._mp.setenv('PLAN_BASE_DIR', str(self.fixture_dir))
        self._mp.setenv('PLAN_DIR_NAME', '.plan')
        # Create plans directory but NOT the plan subdirectory
        (self.fixture_dir / 'plans').mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._mp is not None:
            self._mp.undo()
            self._mp = None

        # Only cleanup if running standalone
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)

    @property
    def temp_dir(self):
        """Return the fixture directory."""
        return self.fixture_dir

    def plan_dir(self, plan_id):
        return self.fixture_dir / 'plans' / plan_id
