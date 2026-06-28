#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-plugin-development extension's security-profile composition.

Pins the security profile's default skill so the resolution-only security
profile resolves the focused plugin-security skill. Tier 2 (direct import):
loads the bundle extension.py and inspects get_skill_domains() directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-plugin-development bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_plugin_development', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _security_defaults():
    """Return the plan-marshall-plugin-dev domain's security-profile default skill identifiers."""
    domains = _load_extension().get_skill_domains()
    plugin_dev_domain = next(d for d in domains if d['domain']['key'] == 'plan-marshall-plugin-dev')
    security = plugin_dev_domain['profiles']['security']
    return [e['skill'] for e in security['defaults']]


def test_security_profile_declared():
    """The plan-marshall-plugin-dev domain declares a non-empty security profile."""
    # Act
    defaults = _security_defaults()

    # Assert
    assert defaults, 'security profile defaults must be non-empty'


def test_security_profile_resolves_plugin_security():
    """The security profile resolves the focused pm-plugin-development:plugin-security skill."""
    # Act
    defaults = _security_defaults()

    # Assert
    assert 'pm-plugin-development:plugin-security' in defaults
