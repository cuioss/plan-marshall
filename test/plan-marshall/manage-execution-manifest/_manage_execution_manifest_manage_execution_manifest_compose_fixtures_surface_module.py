#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _mem, contextlib


@contextlib.contextmanager
def _capture_decision_log():
    """Capture ``_emit_decision_log`` calls; yield the (plan_id, message) list."""
    captured: list[tuple[str, str]] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda pid, msg: captured.append((pid, msg))
    try:
        yield captured
    finally:
        _mem._emit_decision_log = original
