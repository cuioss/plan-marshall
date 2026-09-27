#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the assert-step-recorded subcommand of manage-status."""

import pytest
from _assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    _seed_step,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)
from _mark_step_done_fixtures import _real_head
