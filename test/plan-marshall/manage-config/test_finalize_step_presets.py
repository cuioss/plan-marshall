#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the FinalizeStepPresets constant-class.

Covers behaviour and cross-checks for the finalize-step preset registry:

1. All three presets exist as class-level attributes.
2. ``get(name)`` resolves canonical names and case aliases.
3. ``get('bogus')`` raises ``ValueError`` listing the valid names.
4. Every step in every preset is a member of ``BUILT_IN_FINALIZE_STEPS`` +
   ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` (cross-checked against
   ``_config_defaults`` so a registry rename without updating presets fails
   CI).
5. ``all_names()`` returns ``['local', 'standard', 'full']`` in that exact
   order.
6. ``describe(name)`` returns a non-empty string for each canonical preset.
7. Preset lists are independent — mutating ``FinalizeStepPresets.get('local')``
   does NOT mutate the class-level constant (deep-copy on read).
8. Step nesting: LOCAL ⊆ STANDARD ⊆ FULL (the documented ladder).
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


# =============================================================================
# (1) Presets exist as class-level attributes
# =============================================================================


def test_local_preset_is_class_attribute() -> None:
    assert isinstance(fp.FinalizeStepPresets.LOCAL, list)
    assert fp.FinalizeStepPresets.LOCAL


def test_standard_preset_is_class_attribute() -> None:
    assert isinstance(fp.FinalizeStepPresets.STANDARD, list)
    assert fp.FinalizeStepPresets.STANDARD


def test_full_preset_is_class_attribute() -> None:
    assert isinstance(fp.FinalizeStepPresets.FULL, list)
    assert fp.FinalizeStepPresets.FULL


# =============================================================================
# (2) get() resolves canonical names and case aliases
# =============================================================================


def test_get_local_returns_local_preset() -> None:
    result = fp.FinalizeStepPresets.get('local')
    assert result == fp.FinalizeStepPresets.LOCAL


def test_get_standard_returns_standard_preset() -> None:
    result = fp.FinalizeStepPresets.get('standard')
    assert result == fp.FinalizeStepPresets.STANDARD


def test_get_full_returns_full_preset() -> None:
    result = fp.FinalizeStepPresets.get('full')
    assert result == fp.FinalizeStepPresets.FULL


def test_get_mixed_case_resolves() -> None:
    assert fp.FinalizeStepPresets.get('LOCAL') == fp.FinalizeStepPresets.LOCAL
    assert fp.FinalizeStepPresets.get('Standard') == fp.FinalizeStepPresets.STANDARD
    assert fp.FinalizeStepPresets.get('  full  ') == fp.FinalizeStepPresets.FULL


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
# (4) Cross-check: every step in every preset is a member of the known
#     finalize-step universe in _config_defaults
# =============================================================================


@pytest.mark.parametrize('preset_name', ['local', 'standard', 'full'])
def test_preset_steps_are_subset_of_known_finalize_steps(preset_name: str) -> None:
    known = set(cfg.BUILT_IN_FINALIZE_STEPS) | set(cfg.OPTIONAL_BUNDLE_FINALIZE_STEPS)
    preset = fp.FinalizeStepPresets.get(preset_name)
    for step in preset:
        assert step in known, (
            f"preset '{preset_name}' step '{step}' is not a member of "
            f'BUILT_IN_FINALIZE_STEPS + OPTIONAL_BUNDLE_FINALIZE_STEPS'
        )


def test_known_finalize_steps_matches_config_defaults() -> None:
    # Drift guard: the registry's KNOWN_FINALIZE_STEPS tuple must stay in
    # lock-step with the authoritative _config_defaults lists.
    expected = tuple(cfg.BUILT_IN_FINALIZE_STEPS) + tuple(cfg.OPTIONAL_BUNDLE_FINALIZE_STEPS)
    assert fp.KNOWN_FINALIZE_STEPS == expected


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
    original = list(fp.FinalizeStepPresets.LOCAL)
    snapshot = fp.FinalizeStepPresets.get('local')
    snapshot.append('CORRUPTED')
    snapshot[0] = 'CORRUPTED'
    # Class-level constant must be untouched.
    assert fp.FinalizeStepPresets.LOCAL == original
    # A fresh get() must still return the pristine list.
    assert fp.FinalizeStepPresets.get('local') == original


# =============================================================================
# (8) Ladder containment — LOCAL ⊆ STANDARD ⊆ FULL
# =============================================================================


def test_preset_ladder_is_containment_monotonic() -> None:
    local = set(fp.FinalizeStepPresets.get('local'))
    standard = set(fp.FinalizeStepPresets.get('standard'))
    full = set(fp.FinalizeStepPresets.get('full'))
    assert local <= standard, 'LOCAL must be a subset of STANDARD'
    assert standard <= full, 'STANDARD must be a subset of FULL'
