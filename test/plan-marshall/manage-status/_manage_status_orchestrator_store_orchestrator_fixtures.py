#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-status orchestrator store (kind=orchestrator epic ledger).

Its sections, in order:

* Create
* Read
* update-field
* Metadata
* Legacy layout refusal
"""

import json
from argparse import Namespace

import pytest
from _orchestrator_store_fixtures import (
    _core,
    _create_args,
    _legacy_document,
    _orchestrator_anchor_file,
    _orchestrator_queue_dir,
    _orchestrator_root,
    _orchestrator_status_file,
    _read_header,
    _row,
    _seed_ledger,
    _write_legacy,
    cmd_orchestrator_create,
    cmd_orchestrator_metadata,
    cmd_orchestrator_read,
    cmd_orchestrator_update_field,
)

#: One valid ``--value`` per updatable field, paired with the value the assembled
#: ledger must then carry. Each differs from what ``create`` writes.
_SWEEP_VALUES = {
    'phase': ('closed', 'closed'),
    'resume_anchor': ('run decompose next', 'run decompose next'),
    'workstreams': ('["WS-09"]', ['WS-09']),
}
