#!/usr/bin/env python3
"""Tests for manage-config.py domain-detect subcommand.

Deterministic domain detector for phase-1-init Step 7. Walks the
clarified-request narrative for explicit bundle / skill mentions and
returns the single matching domain. Single-domain projects auto-select;
multi-match or zero-match returns ambiguous=true so the caller raises
AskUserQuestion — there is no LLM dispatch fallback on this path.
"""

from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json, create_nested_marshal_json

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_domain_detect_under_test', '_cmd_domain_detect.py')
cmd_domain_detect = _mod.cmd_domain_detect


def _ns(plan_id: str, domain_override: str | None = None) -> Namespace:
    return Namespace(plan_id=plan_id, domain_override=domain_override)


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        f'# Request\n\n## Original Input\n\n(unused)\n\n## Clarified Request\n\n{body}\n',
        encoding='utf-8',
    )


def _make_plan_dir(plan_context, plan_id: str) -> Path:
    """Create a plan directory under the fixture base for ``plan_id``."""
    plan_dir = plan_context.fixture_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    return plan_dir


# =============================================================================
# Single-domain auto-select
# =============================================================================


def test_single_user_domain_auto_selects(plan_context):
    """One configured non-system domain always wins regardless of narrative."""
    plan_dir = _make_plan_dir(plan_context, 'dd-single')
    single = {
        'skill_domains': {
            'java': {'defaults': ['pm-dev-java:java-core'], 'optionals': []},
        }
    }
    create_marshal_json(plan_context.fixture_dir, single)
    _write_request(plan_dir, 'Improve the python service.')  # unrelated narrative

    result = cmd_domain_detect(_ns('dd-single'))
    assert result['status'] == 'success'
    assert result['domain'] == 'java'
    assert result['ambiguous'] is False
    assert result['source'] == 'single_domain_configured'


# =============================================================================
# Unambiguous narrative match
# =============================================================================


def test_unambiguous_narrative_match_picks_winner(plan_context):
    """Two domains configured; only one is mentioned → ambiguous=false."""
    plan_dir = _make_plan_dir(plan_context, 'dd-unamb')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(
        plan_dir,
        'Add a new java-core CDI module for the authentication service.',
    )
    result = cmd_domain_detect(_ns('dd-unamb'))
    assert result['status'] == 'success'
    assert result['domain'] == 'java'
    assert result['ambiguous'] is False
    assert any(c['domain'] == 'java' for c in result['candidates'])


# =============================================================================
# Multi-match → ambiguous
# =============================================================================


def test_multi_match_returns_ambiguous(plan_context):
    """Narrative mentions multiple domains → ambiguous=true with all candidates."""
    plan_dir = _make_plan_dir(plan_context, 'dd-multi')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(
        plan_dir,
        'Refactor the java CDI bindings AND the javascript frontend hooks.',
    )
    result = cmd_domain_detect(_ns('dd-multi'))
    assert result['ambiguous'] is True
    candidates = {c['domain'] for c in result['candidates']}
    assert {'java', 'javascript'}.issubset(candidates)


# =============================================================================
# Zero-match → ambiguous
# =============================================================================


def test_no_match_returns_ambiguous(plan_context):
    """No domain mentioned in the narrative → ambiguous=true, empty candidates."""
    plan_dir = _make_plan_dir(plan_context, 'dd-zero')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(
        plan_dir,
        'Update the deployment scripts to fix the release pipeline.',
    )
    result = cmd_domain_detect(_ns('dd-zero'))
    assert result['ambiguous'] is True
    assert result['candidates'] == []
    assert result['reason'] == 'no_narrative_match'


# =============================================================================
# Override
# =============================================================================


def test_override_takes_precedence_over_narrative(plan_context):
    plan_dir = _make_plan_dir(plan_context, 'dd-override')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(plan_dir, 'Refactor the javascript hooks.')

    result = cmd_domain_detect(_ns('dd-override', domain_override='java'))
    assert result['domain'] == 'java'
    assert result['ambiguous'] is False
    assert result['source'] == 'cli_override'


def test_override_unknown_domain_falls_through(plan_context):
    """An unknown --domain-override is ignored; normal detection runs."""
    plan_dir = _make_plan_dir(plan_context, 'dd-bad-override')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(plan_dir, 'Add a new javascript hook.')

    result = cmd_domain_detect(_ns('dd-bad-override', domain_override='cobol'))
    assert result['domain'] == 'javascript'


# =============================================================================
# Edge cases
# =============================================================================


def test_missing_marshal_returns_ambiguous(plan_context):
    """No marshal.json → ambiguous=true, reason=marshal_not_initialized."""
    plan_dir = _make_plan_dir(plan_context, 'dd-no-marshal')
    _write_request(plan_dir, 'Add java code.')
    # NO create_marshal_json — fresh fixture.
    result = cmd_domain_detect(_ns('dd-no-marshal'))
    assert result['ambiguous'] is True
    assert result['reason'] in ('marshal_not_initialized', 'no_skill_domains_configured', 'no_user_domains')


def test_plan_dir_not_found_errors(plan_context):
    _make_plan_dir(plan_context, 'dd-exists')
    result = cmd_domain_detect(_ns('does-not-exist'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_lesson_body_preferred_over_request_md(plan_context):
    plan_dir = _make_plan_dir(plan_context, 'dd-lesson')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(plan_dir, 'Generic narrative — javascript.')
    (plan_dir / 'lesson-2026-05-01-12-001.md').write_text(
        '# Java lesson\n\nFix the java CDI bindings.\n',
        encoding='utf-8',
    )
    result = cmd_domain_detect(_ns('dd-lesson'))
    assert result['source'].startswith('lesson-body:')
    assert result['domain'] == 'java'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_domain_detect_registered_in_manage_config_dispatch():
    """argparse routes 'domain-detect' to cmd_domain_detect."""
    import argparse  # noqa: PLC0415

    manage_config = _load_module('_manage_config_dispatch_check', 'manage-config.py')
    assert manage_config.cmd_domain_detect is cmd_domain_detect or callable(
        manage_config.cmd_domain_detect
    )

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='noun')
    leaf = sub.add_parser('domain-detect')
    leaf.set_defaults(func=manage_config.cmd_domain_detect)
    ns = parser.parse_args(['domain-detect'])
    assert ns.func is manage_config.cmd_domain_detect
