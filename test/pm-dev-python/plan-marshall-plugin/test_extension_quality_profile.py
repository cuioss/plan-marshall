#!/usr/bin/env python3
"""Tests for the pm-dev-python extension's quality-profile composition.

Pins the quality profile's default skills so the language-agnostic
dev-general-code-quality skill stays at parity with the core and
implementation profiles. The defect this guards: quality.defaults
previously listed only pm-dev-python:python-core, dropping the
code-quality guidance from the profile where it is most relevant.

Tier 2 (direct import): loads the bundle extension.py and inspects the
get_skill_domains() return value directly.
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


def _quality_defaults():
    """Return the python domain's quality-profile default skill identifiers."""
    domains = _load_extension().get_skill_domains()
    python_domain = next(d for d in domains if d['domain']['key'] == 'python')
    quality = python_domain['profiles']['quality']
    return [e['skill'] for e in quality['defaults']]


def test_quality_profile_includes_python_core():
    """The quality profile still defaults pm-dev-python:python-core (no regression)."""
    # Act
    defaults = _quality_defaults()

    # Assert
    assert 'pm-dev-python:python-core' in defaults


def test_quality_profile_includes_dev_general_code_quality():
    """The quality profile defaults the language-agnostic dev-general-code-quality skill."""
    # Act
    defaults = _quality_defaults()

    # Assert
    assert 'plan-marshall:dev-general-code-quality' in defaults
