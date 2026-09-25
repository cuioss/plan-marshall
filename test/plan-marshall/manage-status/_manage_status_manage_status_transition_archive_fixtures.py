#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition: archive — dry-run, reason metadata and the findings gate."""

import json
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _seed_early_archive_plan,
    _seed_finalize_phase_plan,
    _seed_two_in_progress_plan,
    _stub_finding_queries,
    cmd_archive,
    cmd_transition,
)

from conftest import run_script
