#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the discovery-driven FinalizeStepPresets access surface.

Covers behaviour and cross-checks for the finalize-step preset registry. The
preset step lists are no longer class-attribute literals (the removed
``LOCAL`` / ``STANDARD`` / ``FULL`` constants and the ``KNOWN_FINALIZE_STEPS``
tuple): each finalize-step doc DECLARES its preset memberships in a ``presets:``
frontmatter list, and the preset step lists are BUILT lazily from the reusable
``extension_discovery.find_implementors`` query (the SOLE discovery path).

1. ``get(name)`` returns a non-empty list for each canonical preset, matching
   the discovery-derived membership for that preset.
2. ``get(name)`` resolves canonical names and case aliases.
3. ``get('bogus')`` raises ``ValueError`` listing the valid names.
4. Every step in every preset is a discovered finalize-step implementor
   (cross-checked against ``find_implementors`` so a doc rename without updating
   the step's ``presets:`` frontmatter fails CI).
5. ``all_names()`` returns ``['local', 'standard', 'full']`` in that exact order.
6. ``describe(name)`` returns a non-empty string for each canonical preset.
7. Preset lists are independent — mutating ``FinalizeStepPresets.get('local')``
   does NOT poison a subsequent ``get`` (deep-copy on read).
8. Step nesting: local ⊆ standard ⊆ full (the documented ladder).
"""

from __future__ import annotations

import sys

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

PRESETS_SCRIPT = get_script_path('plan-marshall', 'manage-config', 'finalize_step_presets.py')
PRESETS_DIR = PRESETS_SCRIPT.parent

CONFIG_DEFAULTS_SCRIPT = get_script_path('plan-marshall', 'manage-config', '_config_defaults.py')
CONFIG_DEFAULTS_DIR = CONFIG_DEFAULTS_SCRIPT.parent

if str(PRESETS_DIR) not in sys.path:
    sys.path.insert(0, str(PRESETS_DIR))
if str(CONFIG_DEFAULTS_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DEFAULTS_DIR))

import _config_defaults as cfg  # noqa: E402
import finalize_step_presets as fp  # noqa: E402
from extension_discovery import find_implementors  # type: ignore[import-not-found]  # noqa: E402


# =============================================================================
# Discovery-derived expectations (no hand-maintained constants)
# =============================================================================


def _discovered_preset_members(preset_name: str) -> list[str]:
    """Return the discovered step ids for ``preset_name``, ordered by (order, name).

    Mirrors ``finalize_step_presets._discover_presets``: a step belongs to preset
    P iff P appears in its ``presets`` frontmatter list; the per-preset order is
    the discovered ``order``.
    """
    records = sorted(
        find_implementors(cfg.FINALIZE_STEP_EXT_POINT),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [
        rec['name']
        for rec in records
        if preset_name in (rec.get('presets') or []) and rec.get('name')
    ]


def _all_discovered_step_ids() -> set[str]:
    """Return the full set of discovered finalize-step ids."""
    return {rec['name'] for rec in find_implementors(cfg.FINALIZE_STEP_EXT_POINT) if rec.get('name')}


# =============================================================================
# (1) get() returns the discovery-derived membership for each preset
# =============================================================================


@pytest.mark.parametrize('preset_name', ['local', 'standard', 'full'])
def test_get_returns_discovered_membership(preset_name: str) -> None:
    result = fp.FinalizeStepPresets.get(preset_name)
    assert isinstance(result, list)
    assert result, f"preset '{preset_name}' must be non-empty"
    # exact match against the discovery-derived membership (same query + sort)
    assert result == _discovered_preset_members(preset_name)


# =============================================================================
# (2) get() resolves canonical names and case aliases
# =============================================================================


def test_get_mixed_case_resolves() -> None:
    assert fp.FinalizeStepPresets.get('LOCAL') == fp.FinalizeStepPresets.get('local')
    assert fp.FinalizeStepPresets.get('Standard') == fp.FinalizeStepPresets.get('standard')
    assert fp.FinalizeStepPresets.get('  full  ') == fp.FinalizeStepPresets.get('full')


# =============================================================================
# (3) get('bogus') raises ValueError mentioning all three valid names
# =============================================================================


def test_get_unknown_name_raises_with_valid_names_listed() -> None:
    with pytest.raises(ValueError) as excinfo:
        fp.FinalizeStepPresets.get('bogus')
    msg = str(excinfo.value)
    assert 'local' in msg
    assert 'standard' in msg
    assert 'full' in msg


# =============================================================================
# (4) Cross-check: every step in every preset is a discovered implementor
# =============================================================================


@pytest.mark.parametrize('preset_name', ['local', 'standard', 'full'])
def test_preset_steps_are_subset_of_discovered_finalize_steps(preset_name: str) -> None:
    known = _all_discovered_step_ids()
    preset = fp.FinalizeStepPresets.get(preset_name)
    for step in preset:
        assert step in known, (
            f"preset '{preset_name}' step '{step}' is not a discovered "
            f'finalize-step implementor'
        )


def test_known_finalize_steps_constant_is_removed() -> None:
    # The hand-maintained KNOWN_FINALIZE_STEPS drift-guard tuple was removed; the
    # discovery query is now the sole source of the known finalize-step universe.
    assert not hasattr(fp, 'KNOWN_FINALIZE_STEPS'), (
        'KNOWN_FINALIZE_STEPS must be deleted — the known universe is discovered '
        'via extension_discovery.find_implementors'
    )


def test_preset_class_attribute_literals_are_removed() -> None:
    # The class-attribute literals LOCAL / STANDARD / FULL were removed; preset
    # membership is discovery-driven via get().
    for attr in ('LOCAL', 'STANDARD', 'FULL'):
        assert not hasattr(fp.FinalizeStepPresets, attr), (
            f'FinalizeStepPresets.{attr} literal must be deleted — preset '
            f'membership is now discovery-driven'
        )


# =============================================================================
# (5) all_names() returns canonical names in display order
# =============================================================================


def test_all_names_returns_canonical_order() -> None:
    assert fp.FinalizeStepPresets.all_names() == ['local', 'standard', 'full']


# =============================================================================
# (6) describe(name) returns a non-empty string for each preset
# =============================================================================


@pytest.mark.parametrize('preset_name', ['local', 'standard', 'full'])
def test_describe_returns_non_empty_string(preset_name: str) -> None:
    description = fp.FinalizeStepPresets.describe(preset_name)
    assert isinstance(description, str)
    assert description.strip() != ''


def test_describe_accepts_case_aliases() -> None:
    via_canonical = fp.FinalizeStepPresets.describe('full')
    via_upper = fp.FinalizeStepPresets.describe('FULL')
    assert via_canonical == via_upper


def test_describe_unknown_name_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        fp.FinalizeStepPresets.describe('bogus')
    msg = str(excinfo.value)
    assert 'local' in msg
    assert 'standard' in msg
    assert 'full' in msg


# =============================================================================
# (7) Preset lists are independent — get() returns a deep copy
# =============================================================================


def test_get_returns_deep_copy_mutation_does_not_leak() -> None:
    pristine = fp.FinalizeStepPresets.get('local')
    snapshot = fp.FinalizeStepPresets.get('local')
    snapshot.append('CORRUPTED')
    snapshot[0] = 'CORRUPTED'
    # A fresh get() must still return the pristine list, unpoisoned by the mutation.
    assert fp.FinalizeStepPresets.get('local') == pristine


# =============================================================================
# (8) Ladder containment — local ⊆ standard ⊆ full
# =============================================================================


def test_preset_ladder_is_containment_monotonic() -> None:
    local = set(fp.FinalizeStepPresets.get('local'))
    standard = set(fp.FinalizeStepPresets.get('standard'))
    full = set(fp.FinalizeStepPresets.get('full'))
    assert local <= standard, 'local must be a subset of standard'
    assert standard <= full, 'standard must be a subset of full'
