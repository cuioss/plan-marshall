#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the canonical-command vocabulary in _extension_constants.py.

Focused on the arch-gate canonical command: it is a known canonical (resolvable
via `architecture resolve --command arch-gate`) but is deliberately NOT a
required command in any resolution category, so no module is ever forced to
provide one.
"""

from _extension_constants import (
    ALL_CANONICAL_COMMANDS,
    CANONICAL_COMMANDS,
    CMD_ARCH_GATE,
    CMD_QUALITY_GATE,
    CMD_VERIFY,
    PROFILE_PATTERNS,
)

# The required-command sets documented in canonical-commands.md. They are not
# encoded as constants in the source module, so the test mirrors the documented
# contract: quality-gate is required for all modules, verify for non-pom modules.
_ALWAYS_REQUIRED = frozenset({CMD_QUALITY_GATE})
_NON_POM_REQUIRED = frozenset({CMD_VERIFY})


def test_arch_gate_constant_value():
    assert CMD_ARCH_GATE == 'arch-gate'


def test_arch_gate_is_a_known_canonical():
    assert CMD_ARCH_GATE in ALL_CANONICAL_COMMANDS


def test_arch_gate_not_in_always_required_set():
    assert CMD_ARCH_GATE not in _ALWAYS_REQUIRED


def test_arch_gate_not_in_non_pom_required_set():
    assert CMD_ARCH_GATE not in _NON_POM_REQUIRED


def test_arch_gate_has_no_profile_aliases():
    # arch-gate is extension-populated per-domain, not profile-classified, so it
    # carries no alias metadata and contributes no PROFILE_PATTERNS entry.
    assert CMD_ARCH_GATE not in CANONICAL_COMMANDS
    assert CMD_ARCH_GATE not in PROFILE_PATTERNS.values()


def test_arch_gate_reexported_from_extension_base():
    from extension_base import CMD_ARCH_GATE as reexported

    assert reexported == 'arch-gate'
