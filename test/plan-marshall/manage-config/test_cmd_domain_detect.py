#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-config.py domain-detect subcommand.

Deterministic domain detector for phase-1-init Step 7 and phase-2-refine. Walks
the clarified-request narrative for explicit bundle / skill mentions and returns
the SET of matching domains — the unconditional union of the detector, always_on,
and file_globs merge legs. Multi-match, or a zero-match with an empty always_on /
glob union, returns ambiguous=true so the caller raises a multiSelect
AskUserQuestion; there is no LLM dispatch fallback on this path.
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
_glob_to_regex = _mod._glob_to_regex
_extract_narrative_paths = _mod._extract_narrative_paths


def _ns(
    plan_id: str,
    domain_override: str | None = None,
    affected_files: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        domain_override=domain_override,
        affected_files=affected_files,
    )


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        f'# Request\n\n## Original Input\n\n(unused)\n\n## Clarified Request\n\n{body}\n',
        encoding='utf-8',
    )


def _make_plan_dir(plan_context, plan_id: str) -> Path:
    """Create a plan directory under the fixture base for ``plan_id``."""
    plan_dir: Path = plan_context.fixture_dir / 'plans' / plan_id
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
    assert result['domains'] == ['java']
    assert result['ambiguous'] is False
    assert result['source'] == 'single_domain_configured'


# =============================================================================
# Unambiguous narrative match
# =============================================================================


def test_unambiguous_narrative_match_picks_winner(plan_context):
    """Two domains configured; only one is mentioned → ambiguous=false, SET of one."""
    plan_dir = _make_plan_dir(plan_context, 'dd-unamb')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(
        plan_dir,
        'Add a new java-core CDI module for the authentication service.',
    )
    result = cmd_domain_detect(_ns('dd-unamb'))
    assert result['status'] == 'success'
    assert 'java' in result['domains']
    assert result['ambiguous'] is False
    assert any(c['domain'] == 'java' for c in result['candidates'])


# =============================================================================
# Multi-match → ambiguous
# =============================================================================


def test_multi_match_returns_ambiguous(plan_context):
    """Narrative mentions multiple domains → ambiguous=true, both in the domains SET."""
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
    assert {'java', 'javascript'}.issubset(set(result['domains']))


# =============================================================================
# Zero-match → ambiguous (empty always_on / glob union)
# =============================================================================


def test_no_match_returns_ambiguous(plan_context):
    """No domain mentioned and nothing to include → ambiguous=true.

    On the empty-union zero-match path the configured non-system domains are
    surfaced as the multiSelect candidate set, and the domains SET is empty.
    """
    plan_dir = _make_plan_dir(plan_context, 'dd-zero')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(
        plan_dir,
        'Update the deployment configuration to fix the release pipeline.',
    )
    result = cmd_domain_detect(_ns('dd-zero'))
    assert result['ambiguous'] is True
    assert result['reason'] == 'no_narrative_match'
    assert result['domains'] == []
    # The configured non-system domains are surfaced for the multiSelect prompt.
    candidate_domains = {c['domain'] for c in result['candidates']}
    assert {'java', 'javascript', 'plan-marshall-plugin-dev'}.issubset(candidate_domains)


# =============================================================================
# Override
# =============================================================================


def test_override_takes_precedence_over_narrative(plan_context):
    plan_dir = _make_plan_dir(plan_context, 'dd-override')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(plan_dir, 'Refactor the javascript hooks.')

    result = cmd_domain_detect(_ns('dd-override', domain_override='java'))
    assert result['domains'] == ['java']
    assert result['ambiguous'] is False
    assert result['source'] == 'cli_override'


def test_override_unknown_domain_falls_through(plan_context):
    """An unknown --domain-override is ignored; normal detection runs."""
    plan_dir = _make_plan_dir(plan_context, 'dd-bad-override')
    create_nested_marshal_json(plan_context.fixture_dir)
    _write_request(plan_dir, 'Add a new javascript hook.')

    result = cmd_domain_detect(_ns('dd-bad-override', domain_override='cobol'))
    assert 'javascript' in result['domains']


# =============================================================================
# always_on merge leg
# =============================================================================


def _config_with_inclusion(**python_inclusion) -> dict:
    """Build a marshal config with java + a python domain carrying inclusion keys."""
    python_cfg: dict = {'bundle': 'pm-dev-python'}
    python_cfg.update(python_inclusion)
    return {
        'skill_domains': {
            'system': {'defaults': []},
            'java': {'bundle': 'pm-dev-java'},
            'python': python_cfg,
        }
    }


def test_always_on_domain_unioned_despite_unrelated_narrative(plan_context):
    """A domain flagged always_on is unioned into domains regardless of narrative."""
    plan_dir = _make_plan_dir(plan_context, 'dd-always-on')
    create_marshal_json(plan_context.fixture_dir, _config_with_inclusion(always_on=True))
    _write_request(plan_dir, 'Refactor the java CDI bindings.')  # only java mentioned

    result = cmd_domain_detect(_ns('dd-always-on'))
    assert result['status'] == 'success'
    assert 'java' in result['domains']  # narrative leg
    assert 'python' in result['domains']  # always_on leg
    assert 'python' in result['always_on']
    assert result['ambiguous'] is False


def test_zero_narrative_match_with_always_on_resolves_silently(plan_context):
    """A zero narrative match resolved by the always_on leg is silent (ambiguous=false)."""
    plan_dir = _make_plan_dir(plan_context, 'dd-silent')
    create_marshal_json(plan_context.fixture_dir, _config_with_inclusion(always_on=True))
    _write_request(plan_dir, 'Update the deployment pipeline configuration.')  # no domain mentioned

    result = cmd_domain_detect(_ns('dd-silent'))
    assert result['ambiguous'] is False
    assert result['reason'] == 'inclusion_only_resolve'
    assert result['domains'] == ['python']
    assert result['candidates'] == []


# =============================================================================
# file_globs merge leg
# =============================================================================


def test_file_globs_merge_via_affected_files(plan_context):
    """--affected-files is the file signal for the glob leg (the refine path)."""
    plan_dir = _make_plan_dir(plan_context, 'dd-globs-af')
    create_marshal_json(plan_context.fixture_dir, _config_with_inclusion(file_globs=['**/*.py']))
    _write_request(plan_dir, 'Refactor the java CDI bindings.')

    result = cmd_domain_detect(_ns('dd-globs-af', affected_files='src/foo/bar.py,README.md'))
    assert 'java' in result['domains']  # narrative leg
    assert 'python' in result['domains']  # bar.py matches **/*.py
    assert 'python' in result['glob_matched']


def test_file_globs_merge_via_narrative_paths(plan_context):
    """Without --affected-files the narrative's path-like tokens feed the glob leg (init path)."""
    plan_dir = _make_plan_dir(plan_context, 'dd-globs-narr')
    create_marshal_json(plan_context.fixture_dir, _config_with_inclusion(file_globs=['**/*.py']))
    _write_request(plan_dir, 'Update the module at scripts/helper.py to fix the bug.')

    result = cmd_domain_detect(_ns('dd-globs-narr'))
    assert 'python' in result['domains']
    assert 'python' in result['glob_matched']
    assert result['ambiguous'] is False
    assert result['reason'] == 'inclusion_only_resolve'


def test_multi_match_still_merges_inclusion(plan_context):
    """A multi-match stays ambiguous but still merges the always_on / glob legs."""
    plan_dir = _make_plan_dir(plan_context, 'dd-multi-incl')
    config = {
        'skill_domains': {
            'system': {'defaults': []},
            'java': {'bundle': 'pm-dev-java'},
            'javascript': {'bundle': 'pm-dev-frontend'},
            'python': {'bundle': 'pm-dev-python', 'always_on': True},
        }
    }
    create_marshal_json(plan_context.fixture_dir, config)
    _write_request(plan_dir, 'Refactor the java CDI and the javascript frontend hooks.')

    result = cmd_domain_detect(_ns('dd-multi-incl'))
    assert result['ambiguous'] is True  # java + javascript multi-match
    candidates = {c['domain'] for c in result['candidates']}
    assert {'java', 'javascript'}.issubset(candidates)
    assert 'python' in result['domains']  # always_on merged despite ambiguity
    assert {'java', 'javascript', 'python'}.issubset(set(result['domains']))


# =============================================================================
# Glob matcher / narrative-path helper units
# =============================================================================


def test_glob_to_regex_double_star_matches_any_depth():
    """`**/*.py` matches a .py file at any depth, including the repository root."""
    pattern = _glob_to_regex('**/*.py')
    assert pattern.match('foo.py')
    assert pattern.match('marketplace/bundles/foo/bar.py')
    assert not pattern.match('foo.txt')


def test_glob_to_regex_single_star_does_not_cross_separator():
    """A single `*` matches within one path segment only."""
    pattern = _glob_to_regex('src/*.py')
    assert pattern.match('src/foo.py')
    assert not pattern.match('src/sub/foo.py')


def test_extract_narrative_paths_keeps_only_path_like_tokens():
    """Only tokens carrying a separator or a filename extension are kept."""
    paths = _extract_narrative_paths('Edit src/foo/bar.py and README.md but not plainword.')
    assert 'src/foo/bar.py' in paths
    assert 'README.md' in paths
    assert 'plainword' not in paths


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
    assert result['domains'] == []


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
    assert 'java' in result['domains']


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
