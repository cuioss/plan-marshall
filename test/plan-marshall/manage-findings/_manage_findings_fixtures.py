#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage findings`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for manage-findings.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""


import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')


# Import toon_parser - conftest sets up PYTHONPATH

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_FINDINGS_SCRIPT = str(
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-findings'
    / 'scripts'
    / 'manage-findings.py'
)


_spec = importlib.util.spec_from_file_location('manage_findings', _MANAGE_FINDINGS_SCRIPT)


assert _spec is not None and _spec.loader is not None


_mod = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(_mod)


cmd_add = _mod.cmd_add


cmd_get = _mod.cmd_get


cmd_promote = _mod.cmd_promote


cmd_query = _mod.cmd_query


cmd_resolve = _mod.cmd_resolve


cmd_qgate_add = _mod.cmd_qgate_add


cmd_qgate_clear = _mod.cmd_qgate_clear


cmd_qgate_query = _mod.cmd_qgate_query


cmd_qgate_resolve = _mod.cmd_qgate_resolve


# Core query function (direct, bypassing the CLI namespace) for unified-read tests
query_findings_unified = _mod.query_findings_unified


# Raw-input parse helpers (direct) for the sentinel-collision regression tests
_parse_raw_input = _mod._parse_raw_input


_RawInputError = _mod._RawInputError


# =============================================================================
# Namespace Builders
# =============================================================================


def _add_ns(
    plan_id='test-plan',
    type='bug',
    title='Test finding',
    detail='Test detail',
    file_path=None,
    line=None,
    component=None,
    module=None,
    rule=None,
    severity=None,
    author=None,
    kind=None,
    reviewed_commit_sha=None,
    bot_kind=None,
    raw_input=None,
    raw_input_max_bytes=_mod.DEFAULT_RAW_INPUT_MAX_BYTES,
):
    return Namespace(
        plan_id=plan_id,
        type=type,
        title=title,
        detail=detail,
        file_path=file_path,
        line=line,
        component=component,
        module=module,
        rule=rule,
        severity=severity,
        author=author,
        kind=kind,
        reviewed_commit_sha=reviewed_commit_sha,
        bot_kind=bot_kind,
        raw_input=raw_input,
        raw_input_max_bytes=raw_input_max_bytes,
    )


def _query_ns(
    plan_id='test-plan',
    type=None,
    resolution=None,
    promoted=None,
    file_pattern=None,
    include_qgate=False,
    author=None,
    kind=None,
    bot_kind=None,
):
    return Namespace(
        plan_id=plan_id,
        type=type,
        resolution=resolution,
        promoted=promoted,
        file_pattern=file_pattern,
        include_qgate=include_qgate,
        author=author,
        kind=kind,
        bot_kind=bot_kind,
    )


def _get_ns(plan_id='test-plan', hash_id=''):
    return Namespace(plan_id=plan_id, hash_id=hash_id)


def _resolve_ns(plan_id='test-plan', hash_id='', resolution='fixed', detail=None):
    return Namespace(plan_id=plan_id, hash_id=hash_id, resolution=resolution, detail=detail)


def _promote_ns(plan_id='test-plan', hash_id='', promoted_to='architecture'):
    return Namespace(plan_id=plan_id, hash_id=hash_id, promoted_to=promoted_to)


def _qgate_add_ns(
    plan_id='test-plan',
    phase='3-outline',
    source='qgate',
    type='triage',
    title='Test qgate finding',
    detail='Test detail',
    file_path=None,
    component=None,
    severity=None,
    iteration=None,
    rule=None,
    raw_input=None,
    raw_input_max_bytes=_mod.DEFAULT_RAW_INPUT_MAX_BYTES,
):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        source=source,
        type=type,
        title=title,
        detail=detail,
        file_path=file_path,
        component=component,
        severity=severity,
        iteration=iteration,
        rule=rule,
        raw_input=raw_input,
        raw_input_max_bytes=raw_input_max_bytes,
    )


def _qgate_query_ns(plan_id='test-plan', phase='3-outline', resolution=None, source=None, iteration=None):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        resolution=resolution,
        source=source,
        iteration=iteration,
    )


def _qgate_resolve_ns(plan_id='test-plan', phase='3-outline', hash_id='', resolution='taken_into_account', detail=None):
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        hash_id=hash_id,
        resolution=resolution,
        detail=detail,
    )


def _qgate_clear_ns(plan_id='test-plan', phase='3-outline'):
    return Namespace(plan_id=plan_id, phase=phase)
