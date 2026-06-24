#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java-cui extension's security-profile composition.

Pins the security profile's default skill so the resolution-only security
profile resolves the focused cui-http security skill. Tier 2 (direct import):
loads the bundle extension.py and inspects get_skill_domains() directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-dev-java-cui bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-java-cui' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_java_cui', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _security_defaults():
    """Return the java-cui domain's security-profile default skill identifiers."""
    domains = _load_extension().get_skill_domains()
    java_cui_domain = next(d for d in domains if d['domain']['key'] == 'java-cui')
    security = java_cui_domain['profiles']['security']
    return [e['skill'] for e in security['defaults']]


def test_security_profile_declared():
    """The java-cui domain declares a non-empty security profile."""
    # Act
    defaults = _security_defaults()

    # Assert
    assert defaults, 'security profile defaults must be non-empty'


def test_security_profile_resolves_cui_http():
    """The security profile resolves the focused pm-dev-java-cui:cui-http skill."""
    # Act
    defaults = _security_defaults()

    # Assert
    assert 'pm-dev-java-cui:cui-http' in defaults
