#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D4 residual: consumers source the Bash-tool ceiling through the runtime seam.

The per-target Bash-tool timeout ceiling is declared in the platform-runtime
(``harness bash-timeout-ceiling`` op), NOT in
``tools-file-ops/scripts/constants.py``. Two consumers bind a module-level
``HARNESS_BASH_CEILING_SECONDS`` by resolving that op through
``platform_runtime._runtime_for_target`` at import time:

* ``manage-architecture/scripts/_cmd_client_build.py`` — the
  ``exceeds_bash_ceiling`` flag compares a stamped ``bash_timeout_seconds``
  against the bound name (``_compute_execution_tier_fields``).
* ``phase-6-finalize/scripts/ci_complete_precondition.py`` — the CI-wait clamp
  derives ``_MAX_INNER_WAIT_SECONDS`` from the bound name.

Both MUST follow the ACTIVE TARGET: patching ``_runtime_for_target`` to yield
the OpenCode runtime (ceiling 120 s) and re-importing must make each module
observe 120 — not the Claude default 600. These tests would turn red the moment
a consumer hard-codes the number instead of going through the seam.

The op's allowed ``status: no-op`` response (a target enforcing no ceiling) must
also be honoured: the bound name becomes ``None``, no stamp ever exceeds it, and
the CI-wait clamp loses its upper bound.
"""

from __future__ import annotations

import platform_runtime
import pytest
from platform_runtime import ClaudeRuntime, OpenCodeRuntime
from toon_parser import parse_toon, serialize_toon

from conftest import load_script_module


def _ceiling_seconds(runtime) -> int:
    """Read the active ceiling straight from the op, no consumer involvement."""
    parsed = parse_toon(runtime.harness_bash_timeout_ceiling())
    return int(parsed['ceiling_seconds'])


def _patched_module(monkeypatch, bundle, skill, script_file, module_name, runtime):
    """Load a consumer module after redirecting the seam to ``runtime``."""
    monkeypatch.setattr(
        platform_runtime,
        '_runtime_for_target',
        lambda *args, **kwargs: runtime,
    )
    return load_script_module(bundle, skill, script_file, module_name)


# ---------------------------------------------------------------------------
# _cmd_client_build — default target resolves the Claude ceiling via the seam
# ---------------------------------------------------------------------------


def test_arch_ceiling_follows_default_target_via_seam():
    """Default target -> module binding equals the op the seam reports."""
    mod = load_script_module(
        'plan-marshall',
        'manage-architecture',
        '_cmd_client_build.py',
        '_cmd_client_build_seam_default',
    )
    assert mod.HARNESS_BASH_CEILING_SECONDS == _ceiling_seconds(ClaudeRuntime())


def test_arch_ceiling_follows_opencode_via_seam(monkeypatch):
    """OpenCode target -> module binding tracks the seam, not a hard-coded 600."""
    mod = _patched_module(
        monkeypatch,
        'plan-marshall',
        'manage-architecture',
        '_cmd_client_build.py',
        '_cmd_client_build_seam_opencode',
        OpenCodeRuntime(),
    )
    opencode_ceiling = _ceiling_seconds(OpenCodeRuntime())
    assert opencode_ceiling != _ceiling_seconds(ClaudeRuntime())
    assert mod.HARNESS_BASH_CEILING_SECONDS == opencode_ceiling
    assert mod.HARNESS_BASH_CEILING_SECONDS == 120


def test_arch_exceeds_flag_tracks_the_seam_bound(monkeypatch):
    """The ``exceeds_bash_ceiling`` flag is computed against the seam-bound name."""
    mod = _patched_module(
        monkeypatch,
        'plan-marshall',
        'manage-architecture',
        '_cmd_client_build.py',
        '_cmd_client_build_seam_exceeds',
        OpenCodeRuntime(),
    )
    beyond = mod._compute_execution_tier_fields(200, measured=True)
    within = mod._compute_execution_tier_fields(100, measured=True)
    assert beyond['exceeds_bash_ceiling'] is True
    assert beyond['execution_tier'] == 'orchestrator'
    assert within['exceeds_bash_ceiling'] is False
    assert within['execution_tier'] == 'per_task'


# ---------------------------------------------------------------------------
# ci_complete_precondition — the wait clamp tracks the same seam
# ---------------------------------------------------------------------------


def test_ci_wait_clamp_tracks_default_target_via_seam():
    """Default target -> clamp derives from the seam-reported ceiling."""
    mod = load_script_module(
        'plan-marshall',
        'phase-6-finalize',
        'ci_complete_precondition.py',
        '_ci_complete_precondition_seam_default',
    )
    claude_ceiling = _ceiling_seconds(ClaudeRuntime())
    assert mod.HARNESS_BASH_CEILING_SECONDS == claude_ceiling
    assert mod._MAX_INNER_WAIT_SECONDS == claude_ceiling - mod.CI_WAIT_OUTER_BUFFER_SECONDS - 1


def test_ci_wait_clamp_tracks_opencode_via_seam(monkeypatch):
    """OpenCode target -> the clamp tightens with the seam, never hard-codes 600."""
    mod = _patched_module(
        monkeypatch,
        'plan-marshall',
        'phase-6-finalize',
        'ci_complete_precondition.py',
        '_ci_complete_precondition_seam_opencode',
        OpenCodeRuntime(),
    )
    assert mod.HARNESS_BASH_CEILING_SECONDS == 120
    assert mod._MAX_INNER_WAIT_SECONDS == 120 - 30 - 1


# ---------------------------------------------------------------------------
# no-ceiling target — the op's allowed ``status: no-op`` response
# ---------------------------------------------------------------------------


class _NoCeilingRuntime:
    """Stub runtime whose ceiling op honours the allowed no-op response."""

    def harness_bash_timeout_ceiling(self) -> str:
        return serialize_toon(
            {
                'status': 'no-op',
                'operation': 'harness bash-timeout-ceiling',
                'reason': 'Target enforces no harness time ceiling',
                'alternative': 'Use the stamped timeout unchanged',
            }
        )


def test_arch_never_exceeds_a_nonexistent_ceiling(monkeypatch):
    """A ``no-op`` ceiling is ``None``: no stamp can exceed it."""
    mod = _patched_module(
        monkeypatch,
        'plan-marshall',
        'manage-architecture',
        '_cmd_client_build.py',
        '_cmd_client_build_seam_noop',
        _NoCeilingRuntime(),
    )
    assert mod.HARNESS_BASH_CEILING_SECONDS is None
    fields = mod._compute_execution_tier_fields(999999, measured=True)
    assert fields['exceeds_bash_ceiling'] is False
    assert fields['execution_tier'] == 'per_task'


def test_ci_wait_clamp_disabled_when_target_has_no_ceiling(monkeypatch):
    """A ``no-op`` ceiling disables the upper clamp; the lower bound stays."""
    mod = _patched_module(
        monkeypatch,
        'plan-marshall',
        'phase-6-finalize',
        'ci_complete_precondition.py',
        '_ci_complete_precondition_seam_noop',
        _NoCeilingRuntime(),
    )
    assert mod.HARNESS_BASH_CEILING_SECONDS is None
    assert mod._MAX_INNER_WAIT_SECONDS is None
    assert mod._clamp_wait_ceiling(999999) == 999999
    assert mod._clamp_wait_ceiling(0) == 1
