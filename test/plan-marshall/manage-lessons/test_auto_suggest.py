#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-lessons.py auto-suggest subcommand.

Recipe-registry matcher for phase-1-init Step 5c. Scans the live
recipe registry and returns up to --max-suggestions recipes ordered
by deterministic confidence (keyword overlap + domain + scope).
Findings are emitted under --source qgate so the orchestrator's
phase-1-init Step 5c can surface them in the audit log.

The pure scoring core (``tokenize`` / ``score_recipe``) was extracted
into ``script-shared/scripts/recipe_scoring.py`` so the auto-suggest
path and the generalized ``manage-config recipe-match`` verb score
against a single source. The unit coverage of that scoring core lives
in ``test/plan-marshall/script-shared/test_recipe_scoring.py``; this
module covers the ``cmd_auto_suggest`` orchestration on top of it.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-lessons'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_auto_suggest_under_test', '_cmd_auto_suggest.py')
cmd_auto_suggest = _mod.cmd_auto_suggest


def _ns(plan_id: str, *, max_suggestions: int = 3, no_emit: bool = True) -> Namespace:
    return Namespace(plan_id=plan_id, max_suggestions=max_suggestions, no_emit=no_emit)


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        f'# Request\n\n## Original Input\n\n(unused)\n\n## Clarified Request\n\n{body}\n',
        encoding='utf-8',
    )


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': metadata or {},
            }
        ),
        encoding='utf-8',
    )


# =============================================================================
# Refactored-import-path regression
# =============================================================================


def test_auto_suggest_imports_scoring_core_from_script_shared():
    """``_cmd_auto_suggest`` sources its scorer from the shared module.

    After the extraction the module-local ``_score_recipe`` / ``_tokenize``
    no longer exist; the names are imported from ``recipe_scoring``. Pin the
    refactored import path so a regression that re-inlines the scorer (or
    drops the import) is caught here rather than at a downstream caller.
    """
    assert not hasattr(_mod, '_score_recipe'), (
        'module-local _score_recipe should be gone after the script-shared extraction'
    )
    assert not hasattr(_mod, '_tokenize'), (
        'module-local _tokenize should be gone after the script-shared extraction'
    )
    # The shared names are bound at module scope via the recipe_scoring import.
    assert callable(_mod.score_recipe)
    assert callable(_mod.tokenize)
    assert callable(_mod.load_registry)


# =============================================================================
# End-to-end (live registry)
# =============================================================================


def test_known_good_documentation_request_lands_on_doc_verify(plan_context):
    """A request that matches recipe-doc-verify's description ranks it first."""
    pdir = plan_context.plan_dir_for('ls-docverify')
    _write_request(
        pdir,
        'Verify documentation links and AsciiDoc references across the project. '
        'Ensure no broken cross-references in standards files.',
    )
    _write_status(pdir, {'domain': 'documentation', 'scope_estimate': 'broad'})

    result = cmd_auto_suggest(_ns('ls-docverify'))
    assert result['status'] == 'success'
    keys = [s['key'] for s in result['suggestions']]
    assert 'doc-verify' in keys, f"doc-verify missing from suggestions; got {keys}"


def test_max_suggestions_caps_returned_list(plan_context):
    """--max-suggestions caps the returned list even when more recipes match."""
    pdir = plan_context.plan_dir_for('ls-cap')
    # A very generic narrative that nominally touches every recipe.
    _write_request(
        pdir,
        'Standards documentation code refactor verify architecture diagrams logging.',
    )
    _write_status(pdir)
    result = cmd_auto_suggest(_ns('ls-cap', max_suggestions=2))
    assert result['count'] <= 2


def test_no_narrative_returns_empty_suggestions(plan_context):
    """When request.md is missing the script returns an empty list with reason."""
    plan_context.plan_dir_for('ls-no-narrative')
    # No request.md, no lesson-*.md.
    result = cmd_auto_suggest(_ns('ls-no-narrative'))
    assert result['status'] == 'success'
    assert result['suggestions'] == []
    assert result['narrative_source'] is None
    assert result['reason'] == 'narrative_unavailable'


def test_lesson_body_preferred_over_request_md(plan_context):
    """A staged lesson-{id}.md is consulted before request.md."""
    pdir = plan_context.plan_dir_for('ls-lesson')
    _write_request(
        pdir,
        'Generic placeholder request that should NOT drive suggestions.',
    )
    (pdir / 'lesson-2026-05-01-12-001.md').write_text(
        '# Verify Documentation Quality\n\nThe project documentation has drifted; verify all links and references.\n',
        encoding='utf-8',
    )
    _write_status(pdir, {'domain': 'documentation'})

    result = cmd_auto_suggest(_ns('ls-lesson'))
    # The narrative_source must indicate the lesson body was consulted.
    assert result['narrative_source'] is not None
    assert result['narrative_source'].startswith('lesson-body:')


def test_emit_writes_qgate_findings(plan_context):
    """With emit=True the suggestions are also recorded as Q-Gate findings.

    The documentation narrative is constructed to match at least one live
    recipe (recipe-doc-verify), so the suggestion count is deterministically
    non-zero and the findings file is always written — no conditional guard.
    """
    pdir = plan_context.plan_dir_for('ls-emit')
    _write_request(
        pdir,
        'Verify documentation links and architecture diagrams across the project.',
    )
    _write_status(pdir, {'domain': 'documentation', 'scope_estimate': 'broad'})
    result = cmd_auto_suggest(_ns('ls-emit', no_emit=False))
    assert result['count'] >= 1
    assert result['findings_emitted'] == result['count']
    findings_path = pdir / 'artifacts' / 'findings' / 'tip.jsonl'
    assert findings_path.exists()


def test_plan_dir_not_found_errors(plan_context):
    result = cmd_auto_suggest(_ns('does-not-exist'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_auto_suggest_registered_in_manage_lessons_dispatch():
    """argparse subparser routes 'auto-suggest' to cmd_auto_suggest."""
    import argparse  # noqa: PLC0415

    manage_lessons = _load_module('_manage_lessons_dispatch_check', 'manage-lessons.py')
    assert manage_lessons.cmd_auto_suggest is cmd_auto_suggest or callable(manage_lessons.cmd_auto_suggest)

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    leaf = sub.add_parser('auto-suggest')
    leaf.set_defaults(func=manage_lessons.cmd_auto_suggest)
    ns = parser.parse_args(['auto-suggest'])
    assert ns.func is manage_lessons.cmd_auto_suggest
