#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Contract tests for the project-local ``project:finalize-step-sync-plugin-cache`` skill.

The skill is a markdown executor playbook backed by the project-local
``sync.py`` engine. These tests pin the contract from three angles:

1. **Frontmatter and ordering** — ``order: 14`` so it sits between
   ``project:finalize-step-deploy-target`` (12) and
   ``default:create-pr`` (20).
2. **Project-local registration** — the skill lives at
   ``.claude/skills/finalize-step-sync-plugin-cache/SKILL.md`` (NOT in
   any marketplace bundle, NOT in ``BUILT_IN_FINALIZE_STEPS``).
3. **Display-detail decision branches** — re-implementation of the
   skill's parsing contract, asserting `success` / `partial` / `error`
   produce the expected display_detail strings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT  # type: ignore[import-not-found]

_SKILL_MD = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache' / 'SKILL.md'
)
_DEPLOY_TARGET_SKILL_MD = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'
)

_MANAGE_CONFIG_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))

import _config_defaults as cd  # noqa: E402


def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    assert match is not None, f'frontmatter not found in {path}'
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            fm[key.strip()] = value.strip()
    return fm


# ---------------------------------------------------------------------------
# 1) Frontmatter and ordering
# ---------------------------------------------------------------------------


def test_skill_md_exists():
    assert _SKILL_MD.is_file(), f'project-local finalize-step skill missing: {_SKILL_MD}'


def test_skill_frontmatter_canonical_fields():
    fm = _parse_frontmatter(_SKILL_MD)
    assert fm.get('name') == 'finalize-step-sync-plugin-cache'
    assert fm.get('description'), 'description must be non-empty'
    assert fm.get('order') == '14', (
        'sync-plugin-cache order must be 14 (between deploy-target=12 and create-pr=20)'
    )


def test_order_between_deploy_target_and_create_pr():
    deploy_target = _parse_frontmatter(_DEPLOY_TARGET_SKILL_MD)
    sync_step = _parse_frontmatter(_SKILL_MD)

    # Hard-coded create-pr order (20) — sourced from the bundled workflow doc.
    create_pr_md = (
        MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'
    )
    create_pr = _parse_frontmatter(create_pr_md)

    assert int(deploy_target['order']) < int(sync_step['order']) < int(create_pr['order'])


def test_skill_body_documents_inline_and_engine_call():
    text = _SKILL_MD.read_text(encoding='utf-8')
    flat = re.sub(r'\s+', ' ', text.lower())
    assert 'inline-only' in flat or 'inline only' in flat
    # Engine invocation must appear verbatim — project-local path
    assert '.claude/skills/sync-plugin-cache/scripts/sync.py' in text
    # display_detail templates must reference synced_count semantics
    assert '{synced_count} bundles synced' in text or 'bundles synced' in text


# ---------------------------------------------------------------------------
# 2) NOT in BUILT_IN_FINALIZE_STEPS — meta-project-only step
# ---------------------------------------------------------------------------


def test_sync_plugin_cache_is_not_a_built_in_default():
    """Per the relocation, sync-plugin-cache is project-local, not a default."""
    assert 'default:sync-plugin-cache' not in cd.BUILT_IN_FINALIZE_STEPS
    assert 'default:sync-plugin-cache' not in cd.BUILT_IN_FINALIZE_STEP_DESCRIPTIONS
    assert 'default:sync-plugin-cache' not in cd.DEFAULT_PLAN_FINALIZE['steps']


def test_no_bundled_standards_doc_for_sync_plugin_cache():
    """No bundled phase-6-finalize/standards/sync-plugin-cache.md exists — the
    skill is project-local under .claude/, not in the plan-marshall bundle."""
    bundled = (
        MARKETPLACE_ROOT
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / 'standards'
        / 'sync-plugin-cache.md'
    )
    assert not bundled.exists(), (
        f'Unexpected bundled standards doc: {bundled}. The sync-plugin-cache step '
        f'is project-local only; no marketplace bundle should ship it.'
    )


def test_no_bundled_skill_for_sync_plugin_cache():
    """No bundled marketplace/bundles/plan-marshall/skills/sync-plugin-cache/
    exists — the engine + slash command live under .claude/skills/."""
    bundled = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'sync-plugin-cache'
    assert not bundled.exists(), (
        f'Unexpected bundled sync-plugin-cache skill: {bundled}. The skill is '
        f'project-local; nothing in the bundle should reference it.'
    )


# ---------------------------------------------------------------------------
# 3) Display-detail decision branches
# ---------------------------------------------------------------------------


def _resolve_display_detail(parsed: dict[str, object]) -> tuple[str, str]:
    """Mirror the skill's "Walk the engine's TOON return" decision.

    Returns ``(outcome, display_detail)`` where ``outcome`` is ``'done'`` or
    ``'failed'``.
    """
    status = parsed.get('status')
    if status == 'success':
        return 'done', f"{parsed.get('synced_count')} bundles synced"
    return 'failed', str(parsed.get('summary_message', 'unknown error'))


@pytest.mark.parametrize(
    'parsed,expected_outcome,expected_detail_substring',
    [
        ({'status': 'success', 'synced_count': 3, 'failed_count': 0}, 'done', '3 bundles synced'),
        (
            {'status': 'partial', 'synced_count': 2, 'failed_count': 1, 'summary_message': '2 succeeded, 1 failed'},
            'failed',
            '2 succeeded',
        ),
        (
            {'status': 'error', 'synced_count': 0, 'failed_count': 0, 'summary_message': 'source root not found'},
            'failed',
            'source root not found',
        ),
    ],
)
def test_display_detail_resolution(parsed, expected_outcome, expected_detail_substring):
    outcome, detail = _resolve_display_detail(parsed)
    assert outcome == expected_outcome
    assert expected_detail_substring in detail
