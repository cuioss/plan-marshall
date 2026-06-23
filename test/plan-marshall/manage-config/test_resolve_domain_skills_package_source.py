#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for per-profile package_source surfacing in resolve-domain-skills.

Covers the data-driven per-profile ``package_source`` declaration added to the
domain extension manifests (``pm-dev-java`` / ``pm-dev-frontend`` ``extension.py``)
and surfaced by ``cmd_resolve_domain_skills`` in ``_cmd_skill_resolution.py``.

Contract under test (deliverable 2):
- The ``implementation`` profile declares ``package_source: packages`` and the
  resolved result surfaces ``package_source == 'packages'``.
- The ``module_testing`` profile declares ``package_source: test_packages`` and
  the resolved result surfaces ``package_source == 'test_packages'``.
- Profiles that declare no ``package_source`` (``core`` / ``quality``) omit the
  key entirely from the result (the resolver only adds it when present).
- The surfacing is data-driven from the manifest, not a hardcoded
  profile->source switch — both ``java`` (pm-dev-java) and ``javascript``
  (pm-dev-frontend) domains exhibit the same per-profile values.

Tier 2 (direct import) tests with 1 subprocess test for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH, create_nested_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')

cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402

# =============================================================================
# Implementation profile -> package_source: packages
# =============================================================================


def test_java_implementation_surfaces_packages(plan_context, monkeypatch):
    """java + implementation surfaces package_source == 'packages' from the manifest."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

    assert result['status'] == 'success'
    assert result['package_source'] == 'packages', (
        f"implementation profile must surface package_source='packages', got "
        f"{result.get('package_source')!r}"
    )


def test_javascript_implementation_surfaces_packages(plan_context, monkeypatch):
    """javascript + implementation surfaces package_source == 'packages' (mirror of java)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='implementation'))

    assert result['status'] == 'success'
    assert result['package_source'] == 'packages', (
        f"javascript implementation profile must surface package_source='packages', got "
        f"{result.get('package_source')!r}"
    )


# =============================================================================
# module_testing profile -> package_source: test_packages
# =============================================================================


def test_java_module_testing_surfaces_test_packages(plan_context, monkeypatch):
    """java + module_testing surfaces package_source == 'test_packages' from the manifest."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='module_testing'))

    assert result['status'] == 'success'
    assert result['package_source'] == 'test_packages', (
        f"module_testing profile must surface package_source='test_packages', got "
        f"{result.get('package_source')!r}"
    )


def test_javascript_module_testing_surfaces_test_packages(plan_context, monkeypatch):
    """javascript + module_testing surfaces package_source == 'test_packages' (mirror of java)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='module_testing'))

    assert result['status'] == 'success'
    assert result['package_source'] == 'test_packages', (
        f"javascript module_testing profile must surface package_source='test_packages', got "
        f"{result.get('package_source')!r}"
    )


# =============================================================================
# Profiles without a declared package_source omit the key
# =============================================================================


def test_java_core_omits_package_source(plan_context, monkeypatch):
    """The core profile declares no package_source, so the key is omitted entirely."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='core'))

    assert result['status'] == 'success'
    assert 'package_source' not in result, (
        f"core profile declares no package_source — the key must be omitted, got "
        f"package_source={result.get('package_source')!r}"
    )


def test_java_quality_omits_package_source(plan_context, monkeypatch):
    """The quality profile declares no package_source, so the key is omitted entirely."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='quality'))

    assert result['status'] == 'success'
    assert 'package_source' not in result, (
        f"quality profile declares no package_source — the key must be omitted, got "
        f"package_source={result.get('package_source')!r}"
    )


def test_javascript_core_omits_package_source(plan_context, monkeypatch):
    """javascript core profile declares no package_source, so the key is omitted.

    The javascript domain (pm-dev-frontend) exposes only core/implementation/
    module_testing — it has no quality profile — so core is the profile that
    declares no package_source on this domain.
    """
    create_nested_marshal_json(plan_context.fixture_dir)

    result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='core'))

    assert result['status'] == 'success'
    assert 'package_source' not in result, (
        f"javascript core profile declares no package_source — the key must be omitted, got "
        f"package_source={result.get('package_source')!r}"
    )


# =============================================================================
# Data-driven distinctness: implementation and module_testing differ
# =============================================================================


def test_implementation_and_module_testing_package_source_differ(plan_context, monkeypatch):
    """The two profiles surface distinct package_source values (data-driven, not coincidental)."""
    create_nested_marshal_json(plan_context.fixture_dir)

    impl = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))
    test = cmd_resolve_domain_skills(Namespace(domain='java', profile='module_testing'))

    assert impl['status'] == 'success'
    assert test['status'] == 'success'
    assert impl['package_source'] != test['package_source'], (
        'implementation and module_testing must surface distinct package_source values '
        f"(impl={impl['package_source']!r}, test={test['package_source']!r})"
    )


# =============================================================================
# CLI Plumbing (Tier 3 - subprocess): TOON carries package_source
# =============================================================================


def test_cli_resolve_domain_skills_emits_package_source(plan_context):
    """CLI plumbing: resolve-domain-skills TOON includes the package_source key."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'package_source' in result.stdout
    assert 'packages' in result.stdout


def test_cli_resolve_domain_skills_core_omits_package_source(plan_context):
    """CLI plumbing: core profile TOON does NOT carry a package_source key."""
    create_nested_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'core')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'package_source' not in result.stdout
