#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how the staleness guard reads the emit sentinel's bytes.

The guard lives in ``marketplace/targets/claude/cache_sync.py``, which is
loaded by file location exactly as the sync engine loads it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from conftest import PROJECT_ROOT

_CACHE_SYNC_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'claude' / 'cache_sync.py'


@pytest.fixture
def cache_sync() -> ModuleType:
    spec = importlib.util.spec_from_file_location('cache_sync_sentinel_under_test', _CACHE_SYNC_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    'sentinel_bytes',
    [b'\xff\xfe{"source_tree_fingerprint": "abc"}', b'[]'],
    ids=['not-utf8', 'json-non-object'],
)
def test_sentinel_that_cannot_be_read_as_an_object_is_refused_as_stale(
    tmp_path: Path, cache_sync: ModuleType, sentinel_bytes: bytes
) -> None:
    """A sentinel that does not decode to a JSON object is a refusal, not an exception."""
    source_root = tmp_path / 'target' / 'claude'
    manifest = source_root / 'demo' / '.claude-plugin' / 'plugin.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name": "demo", "version": "0.1.0"}\n', encoding='utf-8')
    sentinel = source_root / cache_sync.EMIT_MARKER_FILENAME
    sentinel.write_bytes(sentinel_bytes)

    refusal = cache_sync._staleness_guard(source_root, tmp_path / 'no-marketplace')

    assert refusal is not None
    assert refusal.kind == 'stale'
    assert f'sentinel missing or unreadable at {sentinel}' in refusal.message
