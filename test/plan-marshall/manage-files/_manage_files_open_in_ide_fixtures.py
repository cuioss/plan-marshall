#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `open-in-ide` verb on manage-files.

Covers:
  * `detect_ide`: macOS JetBrains family, macOS VS Code, macOS Cursor,
    Linux VS Code, Linux Cursor, Linux JetBrains priority probe, all-miss
    branches on both platforms.
  * `build_launch_command`: each IdeRecord -> correct argv.
  * `is_open_in_ide_enabled`: explicit true, explicit false, missing key
    variants (no open_in_ide key; no plan namespace; no marshal.json file
    at all); non-dict top-level JSON raises ValueError.
  * End-to-end `cmd_open_in_ide`: Mode A success, disabled-by-config
    short-circuit (asserts detect/launcher NEVER called), unknown-IDE
    `ide_not_detected` error, launcher_missing error, Mode B
    invalid-arguments error.
  * Static guards: no `tempfile` import in the module's AST; no
    `tempfile|mkstemp|NamedTemporaryFile|mkdtemp` token in the source;
    `--path` and `--plan-id` share the same `add_mutually_exclusive_group`.
"""

import ast
import json
import re
from pathlib import Path
from unittest import mock

import pytest

from conftest import get_scripts_dir, load_script_module, parse_ns

# Tier 2 direct import - load hyphenated module
_MANAGE_FILES_SCRIPT = get_scripts_dir('plan-marshall', 'manage-files') / 'manage-files.py'
_mod = load_script_module('plan-marshall', 'manage-files', 'manage-files.py', 'manage_files_open_in_ide')

detect_ide = _mod.detect_ide
build_launch_command = _mod.build_launch_command
is_open_in_ide_enabled = _mod.is_open_in_ide_enabled
cmd_open_in_ide = _mod.cmd_open_in_ide
IdeRecord = _mod.IdeRecord
MACOS_JETBRAINS_BUNDLE_IDS = _mod.MACOS_JETBRAINS_BUNDLE_IDS
LINUX_LAUNCHER_PRIORITY = _mod.LINUX_LAUNCHER_PRIORITY

# ⛔ Vacuity guard — both tables belong to the loaded production module, so emptying
# either there collects zero cases at its parametrize below and still reports green.
assert MACOS_JETBRAINS_BUNDLE_IDS, 'manage-files.MACOS_JETBRAINS_BUNDLE_IDS is empty'
assert LINUX_LAUNCHER_PRIORITY, 'manage-files.LINUX_LAUNCHER_PRIORITY is empty'
