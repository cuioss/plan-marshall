#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Preflight staleness derivation when the installed manifest is unresolvable.

An absent ``dist-manifest.json`` is not permission to answer ``unknown`` when the
marshal-config seed and the executor version are both readable: their pair is a
measurable drift signal. The verdict is derived from it; only a pair with a
missing side reports ``unknown``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from conftest import load_script_module

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py')


def _args() -> argparse.Namespace:
    return argparse.Namespace(target='opencode', marketplace_root=None, marketplace=False, dry_run=False)


def _stub_readers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, marshal: str, executor: str) -> None:
    monkeypatch.setattr(ge, 'read_installed_manifest', lambda base_path=None, target='claude': {})
    monkeypatch.setattr(ge, 'read_executor_version', lambda target=None: executor)
    monkeypatch.setattr(ge, 'read_marshal_provisioned_version', lambda cwd=None: marshal)
    monkeypatch.setattr(ge, 'get_base_path', lambda **kwargs: tmp_path)


def test_readable_pair_derives_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """marshal 0.1.1938 + executor 0.1.1953 with no manifest is ``stale``."""
    _stub_readers(monkeypatch, tmp_path, marshal='0.1.1938', executor='0.1.1953')

    result = ge.cmd_preflight(_args())

    assert result['installed_version'] == 'unknown'
    assert result['marshal_status'] == 'stale'
    assert 'derived from the readable pair' in result['warning']
    assert 'probed:' in result['warning']


def test_readable_pair_not_ahead_is_fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """An executor at or behind the seed shows no drift and is ``fresh``."""
    _stub_readers(monkeypatch, tmp_path, marshal='0.1.1953', executor='0.1.1953')

    result = ge.cmd_preflight(_args())

    assert result['marshal_status'] == 'fresh'


def test_missing_pair_side_stays_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """With no executor version there is no measurable pair; ``unknown`` stands."""
    _stub_readers(monkeypatch, tmp_path, marshal='0.1.1938', executor='')

    result = ge.cmd_preflight(_args())

    assert result['marshal_status'] == 'unknown'
    assert 'probed:' in result['warning']
