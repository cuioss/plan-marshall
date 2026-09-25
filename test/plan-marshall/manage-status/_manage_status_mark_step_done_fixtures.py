#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the mark-step-done subcommand of manage-status."""

import pytest
from _mark_step_done_fixtures import (
    _args,
    _make_plan,
    _real_head,
    _tmp_repo_two_heads,
    cmd_mark_step_done,
    read_status,
    write_status,
)
