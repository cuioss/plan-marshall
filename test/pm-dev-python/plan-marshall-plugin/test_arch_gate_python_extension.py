#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-python extension's arch-gate declaration.

Pins provides_arch_gate() to the import-linter single-field descriptor so the
python domain's arch-gate verify-step append fires. Tier 2 (direct import):
loads the bundle extension.py and inspects provides_arch_gate() directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-dev-python bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-python' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_python', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def test_provides_arch_gate_returns_descriptor():
    """The python extension declares a non-None arch-gate descriptor."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor is not None, 'python domain must declare an arch-gate tool'
    assert isinstance(descriptor, dict)


def test_provides_arch_gate_names_import_linter():
    """The arch-gate descriptor names import-linter as the native tool."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor['tool'] == 'import-linter'


def test_provides_arch_gate_is_single_field():
    """The descriptor is single-field — only 'tool', no execution_mode variant."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert set(descriptor.keys()) == {'tool'}, 'descriptor carries only the tool name'
