#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives."""


from __future__ import annotations

from _locks_core_fixtures import _lock_log_base, _mod, log_lock_event


def test_log_lock_event_appends_not_overwrites(tmp_path, monkeypatch):
    # A second emission appends to the SAME log file; the first line survives.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='first')
    log_lock_event('merge', 'released', lock_id='first')

    content = log_path.read_text(encoding='utf-8')
    assert '[LOCK] (merge:acquired) first' in content
    assert '[LOCK] (merge:released) first' in content


def test_log_lock_event_swallows_resolution_failure(tmp_path, monkeypatch):
    # A failure ANYWHERE in the emission body (here: the path resolver raising)
    # is swallowed — log_lock_event is best-effort and MUST NOT raise into the
    # lock action it observes.
    _lock_log_base(tmp_path, monkeypatch)

    def _boom() -> object:
        raise RuntimeError('resolution failed')

    monkeypatch.setattr(_mod, '_resolve_lock_log_path', _boom)

    # No exception propagates.
    log_lock_event('merge', 'acquired', lock_id='plan-a')


def test_log_lock_event_swallows_unwritable_dir(tmp_path, monkeypatch):
    # An open() that raises (unwritable dir / encoding error) is swallowed too —
    # the emission is OUTSIDE the lock's atomic window, so a write failure can
    # never affect lock correctness.
    _lock_log_base(tmp_path, monkeypatch)

    def _raising_open(*_a: object, **_k: object) -> object:
        raise OSError('disk full')

    monkeypatch.setattr('builtins.open', _raising_open)

    # No exception propagates despite the write failing.
    log_lock_event('merge', 'released', lock_id='plan-a')
