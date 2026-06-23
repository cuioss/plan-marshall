#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the static coverage expander (``coverage_presets.py``).

Covers the ``CoveragePresets.expand`` / ``describe`` / ``all_cells`` API, the
``inherit/inherit`` behavior-preserving collapse, the coupling-violation
rejection at the API boundary (``thoroughness >= T4 AND scope < component``),
the import-time self-check, and the lock-step guard asserting every cell the
implementor deliverables (D5-D9) consume is present in the table.

Isolation: the expander is a pure constant-class with no config/filesystem
dependency, so these tests need no ``plan_context`` fixture — they exercise
the in-memory table directly.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# coverage_presets imports from _cmd_coverage at module load, so load the
# dependency first under its canonical module name.
_cmd_coverage_mod = _load_module(
    '_cmd_coverage', '_cmd_coverage.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
_coverage_presets_mod = _load_module(
    'coverage_presets', 'coverage_presets.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
CoveragePresets = _coverage_presets_mod.CoveragePresets
ALLOWED_THOROUGHNESS = _cmd_coverage_mod.ALLOWED_THOROUGHNESS
ALLOWED_SCOPE = _cmd_coverage_mod.ALLOWED_SCOPE


class TestExpand:
    """``CoveragePresets.expand`` returns the composed instruction block."""

    def test_t3_component_emits_breadth_and_depth(self):
        instruction = CoveragePresets.expand('T3', 'component')

        # both the scope-breadth and thoroughness-depth halves appear.
        assert 'Breadth (component):' in instruction
        assert 'Depth (T3):' in instruction
        assert 'cohesive unit' in instruction  # component breadth text
        assert 'one hop out' in instruction  # T3 depth text

    def test_inherit_inherit_is_behavior_preserving(self):
        instruction = CoveragePresets.expand('inherit', 'inherit')

        assert instruction == _coverage_presets_mod._BEHAVIOR_PRESERVING
        assert 'behave exactly as the component does today' in instruction.lower()

    def test_inherit_on_either_axis_collapses_to_behavior_preserving(self):
        # a concrete dial paired with inherit still collapses.
        a = CoveragePresets.expand('T2', 'inherit')
        b = CoveragePresets.expand('inherit', 'overall')

        assert a == _coverage_presets_mod._BEHAVIOR_PRESERVING
        assert b == _coverage_presets_mod._BEHAVIOR_PRESERVING

    def test_t4_change_set_rejected_with_coupling_violation(self):
        # the incoherent cell raises at the API.
        with pytest.raises(ValueError, match='coupling'):
            CoveragePresets.expand('T4', 'change-set')

    def test_invalid_thoroughness_rejected(self):
        with pytest.raises(ValueError, match='thoroughness'):
            CoveragePresets.expand('T9', 'component')

    def test_invalid_scope_rejected(self):
        with pytest.raises(ValueError, match='scope'):
            CoveragePresets.expand('T2', 'galaxy')


class TestDescribe:
    """``CoveragePresets.describe`` returns a one-line summary."""

    def test_describe_concrete_cell(self):
        assert CoveragePresets.describe('T3', 'component') == 'T3 over component'

    def test_describe_inherit_is_behavior_preserving(self):
        summary = CoveragePresets.describe('inherit', 'inherit')
        assert 'behavior-preserving' in summary

    def test_describe_rejects_coupling_violation(self):
        with pytest.raises(ValueError, match='coupling'):
            CoveragePresets.describe('T5', 'artifact')


class TestAllCells:
    """``all_cells`` enumerates exactly the coherent concrete cells."""

    def test_excludes_inherit_axes(self):
        cells = CoveragePresets.all_cells()
        assert all('inherit' not in (t, s) for t, s in cells)

    def test_excludes_coupling_violations(self):
        cells = CoveragePresets.all_cells()
        # No T4/T5 cell below component scope.
        for thoroughness, scope in cells:
            if thoroughness in ('T4', 'T5'):
                assert scope in ('component', 'module', 'overall')

    def test_every_enumerated_cell_expands(self):
        for thoroughness, scope in CoveragePresets.all_cells():
            # Must not raise.
            assert CoveragePresets.expand(thoroughness, scope)


class TestImportTimeSelfCheck:
    """The import-time table validation succeeds (module loaded above)."""

    def test_scope_breadth_keys_match_concrete_ladder(self):
        concrete_scope = {s for s in ALLOWED_SCOPE if s != 'inherit'}
        assert set(CoveragePresets._SCOPE_BREADTH) == concrete_scope

    def test_thoroughness_depth_keys_match_concrete_ladder(self):
        concrete_thoroughness = {t for t in ALLOWED_THOROUGHNESS if t != 'inherit'}
        assert set(CoveragePresets._THOROUGHNESS_DEPTH) == concrete_thoroughness


class TestLockStepWithContract:
    """Every cell the implementor deliverables (D5-D9) consume is in the table.

    The contract's Current-Implementations table binds each component's scope
    rungs and thoroughness rungs; this guard asserts each referenced cell is a
    coherent, expandable cell so no implementor ever references an unexpanded
    or incoherent cell.
    """

    # The (thoroughness, scope) cells named across the implementor bindings in
    # coverage-gathering-contract.md § Current Implementations. Each must be a
    # coherent, expandable cell.
    _CONSUMED_CELLS = [
        # audit-archived-plan-retrospectives
        ('T1', 'change-set'),
        ('T2', 'overall'),
        ('T3', 'module'),
        ('T4', 'overall'),
        ('T5', 'overall'),
        # recipe-plugin-compliance
        ('T2', 'component'),
        ('T3', 'module'),
        ('T4', 'module'),
        # recipe-refactor-to-profile-standards
        ('T2', 'component'),
        ('T3', 'component'),
        ('T4', 'component'),
        # pre-submission-self-review / finalize-step-simplify
        ('T3', 'component'),
    ]

    def test_consumed_cells_are_expandable(self):
        for thoroughness, scope in self._CONSUMED_CELLS:
            # Must not raise — proves every consumed cell is coherent + present.
            instruction = CoveragePresets.expand(thoroughness, scope)
            assert instruction
            assert instruction != _coverage_presets_mod._BEHAVIOR_PRESERVING

    def test_consumed_cells_are_in_all_cells(self):
        enumerated = set(CoveragePresets.all_cells())
        for cell in self._CONSUMED_CELLS:
            assert cell in enumerated
