#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``harness bash-timeout-ceiling`` platform-runtime operation.

Asserts the widened contract the D4 discovery demanded: the Bash-tool timeout
ceiling is a per-target property read through the runtime seam, so a non-Claude
target is never bound by the Claude harness ceiling. The operation is exercised
through the real concrete runtimes (mirroring how consumers read it via
``platform_runtime._runtime_for_target``), not through a stubbed seam.
"""

from __future__ import annotations

from typing import Any

import claude_runtime
import pytest
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    """Parse a TOON string and return the result dict."""
    return parse_toon(output)


def test_claude_resolves_its_own_ceiling() -> None:
    """ClaudeRuntime returns the Claude harness ceiling."""
    result = _parse(ClaudeRuntime().harness_bash_timeout_ceiling())
    assert result["operation"] == "harness bash-timeout-ceiling"
    assert result["target"] == "claude"
    assert result["ceiling_seconds"] == 600


def test_opencode_resolves_its_own_ceiling() -> None:
    """OpenCodeRuntime returns the OpenCode harness ceiling."""
    result = _parse(OpenCodeRuntime().harness_bash_timeout_ceiling())
    assert result["operation"] == "harness bash-timeout-ceiling"
    assert result["target"] == "opencode"
    assert result["ceiling_seconds"] == 120


def test_targets_carry_distinct_ceilings() -> None:
    """The two registered targets are not bound by a shared harness ceiling."""
    claude_ceiling = _parse(ClaudeRuntime().harness_bash_timeout_ceiling())[
        "ceiling_seconds"
    ]
    opencode_ceiling = _parse(OpenCodeRuntime().harness_bash_timeout_ceiling())[
        "ceiling_seconds"
    ]
    assert claude_ceiling != opencode_ceiling


def test_claude_ceiling_is_monkeypatchable_via_attribute_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ceiling value is read by attribute access from the entry module.

    A consumer test can therefore patch ``claude_runtime.
    HARNESS_BASH_TIMEOUT_CEILING_SECONDS`` and observe a different ceiling
    through the seam, exactly as it must for the cross-target comparison.
    """
    monkeypatch.setattr(claude_runtime, "HARNESS_BASH_TIMEOUT_CEILING_SECONDS", 42)
    result = _parse(ClaudeRuntime().harness_bash_timeout_ceiling())
    assert result["ceiling_seconds"] == 42
