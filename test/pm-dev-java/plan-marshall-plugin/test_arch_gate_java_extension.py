#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java extension's arch-gate declaration.

Pins provides_arch_gate() to the ArchUnit single-field descriptor so the
java domain's arch-gate verify-step append fires. Tier 2 (direct import):
loads the bundle extension.py and inspects provides_arch_gate() directly.
"""


# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import load_skill_module


def _load_extension():
    """Load the pm-dev-java bundle extension.py and return an Extension instance."""
    module = load_skill_module(
        'pm-dev-java', 'plan-marshall-plugin', 'extension.py', 'extension_pm_dev_java'
    )
    return module.Extension()


def test_provides_arch_gate_returns_descriptor():
    """The java extension declares a non-None arch-gate descriptor."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor is not None, 'java domain must declare an arch-gate tool'
    assert isinstance(descriptor, dict)


def test_provides_arch_gate_names_archunit():
    """The arch-gate descriptor names ArchUnit as the native tool."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor['tool'] == 'archunit'


def test_provides_arch_gate_is_single_field():
    """The descriptor is single-field — only 'tool', no execution_mode variant."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert set(descriptor.keys()) == {'tool'}, 'descriptor carries only the tool name'
