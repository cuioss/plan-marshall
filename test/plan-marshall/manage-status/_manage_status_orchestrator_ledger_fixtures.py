#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for ``_orchestrator_ledger`` — the per-concern epic ledger layout.

Covers every module entry point: path resolution (including the refusal of a
plan id outside the grammar), the assembled view round-trip ordered by
``(seq, id)``, the atomic duplicate-id and duplicate-slug refusals of
``create_row``, per-row mutate isolation, legacy-layout detection, migration
fidelity (``seq`` follows array order), the absent-queue versus
unreadable-row distinction, and the non-UTF-8 header, anchor and row file each
reported as unreadable rather than raised.
"""

import json
import threading

import pytest

from conftest import load_script_module

_ledger = load_script_module('plan-marshall', 'manage-status', '_orchestrator_ledger.py', '_orchestrator_ledger_unit')


def _header(**overrides) -> dict:
    header = {
        'kind': 'orchestrator',
        'title': 'Unit Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'metadata': {'parallelization_scope': '2'},
        'created': '2020-01-01T00:00:00Z',
    }
    header.update(overrides)
    return header


def _row(plan_id: str, slug: str, **extra) -> dict:
    row = {
        'id': plan_id,
        'slug': slug,
        'workstream': 'WS-01',
        'status': 'staged',
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }
    row.update(extra)
    return row


@pytest.fixture
def root(tmp_path):
    epic = tmp_path / 'orchestrator' / 'unit-epic'
    epic.mkdir(parents=True)
    return epic
