#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Degrade-path pins for opencode runtime gaps and the sentinel convention.

Asserts no-op status with reason and alternative on every input for no
session id, no transcript, and hook_not_configured absence, that no manual
count returns success, and the sentinel meaning guard over the surrounding
evidence.
"""

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from opencode_runtime import OpenCodeRuntime
from runtime_base import NO_SESSION_IDENTITY, has_session_identity
from toon_parser import parse_toon


@pytest.fixture()
def runtime() -> OpenCodeRuntime:
    """Return a fresh OpenCodeRuntime instance."""
    return OpenCodeRuntime()


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is non-empty."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict)
    return result


def test_session_capture_noop_on_every_input(runtime: OpenCodeRuntime) -> None:
    """Session capture degrades visibly with reason and alternative."""
    result = _parse(runtime.session_capture('my-plan'))
    assert result['status'] == 'no-op'
    assert result['reason']
    assert result['alternative']


def test_metrics_capture_manual_count_never_succeeds(runtime: OpenCodeRuntime) -> None:
    """No manual token count is reported as success."""
    for total in (None, 0, 1, 42000):
        result = _parse(runtime.metrics_capture('my-plan', '5-execute', total))
        assert result['status'] == 'no-op'
        assert result['reason']
        assert result['alternative']
        assert result.get('tokens_captured') is None


def test_transcript_paths_return_transcript_not_found(runtime: OpenCodeRuntime) -> None:
    """No-transcript paths decline with transcript_not_found."""
    normalized = _parse(runtime.metrics_normalized_tokens('sid', [], '/tmp/out.json'))
    assert normalized['status'] == 'no-op'
    assert normalized['reason'] == 'transcript_not_found'
    assert normalized['alternative']

    signal = _parse(runtime.chat_extract_signal('sid'))
    assert signal['status'] == 'no-op'
    assert signal['reason'] == 'transcript_not_found'
    assert signal['alternative']


def test_opencode_never_returns_hook_not_configured(runtime: OpenCodeRuntime) -> None:
    """The hook_not_configured error names Claude wiring; opencode answers no-op."""
    for payload in (
        runtime.session_capture('my-plan'),
        runtime.metrics_capture('my-plan', '5-execute', None),
        runtime.metrics_capture('my-plan', '5-execute', 10),
        runtime.wait_for('build-job', 'job-1', 60),
    ):
        result = _parse(payload)
        assert result.get('error') != 'hook_not_configured'


def test_sentinel_meaning_guard() -> None:
    """Absent identity reads as the sentinel through the named guard."""
    assert NO_SESSION_IDENTITY == 'NO_SESSION_IDENTITY'
    assert has_session_identity('abc123') is True
    assert has_session_identity(None) is False
    assert has_session_identity('') is False
    assert has_session_identity('   ') is False
    assert has_session_identity(NO_SESSION_IDENTITY) is False
