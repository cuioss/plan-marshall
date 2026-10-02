#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract tests for the project-local ``project:finalize-step-sync-plugin-cache`` skill.

The skill is a markdown executor playbook backed by the unified sync engine
at ``marketplace/targets/sync.py``, which it runs with no ``--target`` so one
call syncs every harness install. These tests pin the contract from three
angles:

1. **Frontmatter and ordering** — ``order: 85`` so it sits post-merge
   immediately after ``project:finalize-step-deploy-target`` (81) and
   before ``default:record-metrics`` (990).
2. **Project-local registration** — the skill lives at
   ``.claude/skills/finalize-step-sync-plugin-cache/SKILL.md`` (NOT in
   any marketplace bundle, NOT in ``BUILT_IN_FINALIZE_STEPS``).
3. **Outcome and display-detail decision branches** — a re-implementation
   of the skill's parsing contract over the engine's aggregate document,
   asserting which outcome each aggregate status records, what the
   display detail names, and that the executor regeneration and the
   daemon reconcile key on the ``claude`` row alone.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from _documented_example_scan import BARE_PYTHON_TARGETS_PREFIX, scan_shell_prescriptions

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

cd = load_script_module('plan-marshall', 'manage-config', '_config_defaults.py')

_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache' / 'SKILL.md'
_DEPLOY_TARGET_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'

#: The engine call the step prescribes: no ``--target``, so one call syncs every
#: harness. Built from the shared prefix constant so this module never opens a
#: line with the invocation itself.
_ENGINE_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}sync.py'

#: The daemon reconcile the step prescribes once the Claude target has synced.
_RECONCILE_INVOCATION = f'{BARE_PYTHON_TARGETS_PREFIX}claude/reconcile_daemon.py'

#: A row of the skill's result table: an aggregate status, then the
#: ``outcome=`` token that status records.
_STATUS_ROW_RE = re.compile(r'^\| `(?P<status>success|partial|error)` \|.*?`outcome=(?P<outcome>\w+)`', re.MULTILINE)


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
    assert fm.get('order') == '85', (
        'finalize-step-sync-plugin-cache order must be 85 (post-merge: immediately after '
        'finalize-step-deploy-target=81, before record-metrics=990)'
    )


def test_order_after_deploy_target_post_merge():
    """Post-merge, the deploy-target step and the sync step run after branch-cleanup;
    the sync step immediately follows deploy-target."""
    deploy_target = _parse_frontmatter(_DEPLOY_TARGET_SKILL_MD)
    sync_step = _parse_frontmatter(_SKILL_MD)

    # Hard-coded create-pr order (20) — sourced from the bundled workflow doc.
    # Post-merge, both deploy/sync steps sort AFTER create-pr.
    create_pr_md = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'
    create_pr = _parse_frontmatter(create_pr_md)

    assert int(create_pr['order']) < int(deploy_target['order']) < int(sync_step['order'])


def test_skill_body_documents_inline_and_engine_call():
    """The step is inline-only and its one sync call is the unified engine, run without ``--target``.

    Matching every prescribed line that names a ``sync.py`` — rather than only
    looking for the engine line — is what catches a second sync script or a
    ``--target`` narrowing the finalize-time sync to one harness.
    """
    text = _SKILL_MD.read_text(encoding='utf-8')
    flat = re.sub(r'\s+', ' ', text.lower())
    prescriptions, _ = scan_shell_prescriptions(text)

    sync_calls = [line for line in prescriptions if 'sync.py' in line]

    assert 'inline-only' in flat or 'inline only' in flat
    assert sync_calls == [_ENGINE_INVOCATION]


def test_skill_body_maps_each_aggregate_status_to_an_outcome():
    """Only an aggregate ``success`` records ``done``; ``partial`` and ``error`` both record ``failed``.

    ``partial`` recording ``done`` would report a finalize whose harness installs
    disagree with each other as a clean sync.
    """
    text = _SKILL_MD.read_text(encoding='utf-8')

    outcomes = {match.group('status'): match.group('outcome') for match in _STATUS_ROW_RE.finditer(text)}

    assert outcomes == {'success': 'done', 'partial': 'failed', 'error': 'failed'}


def test_skill_body_gates_regen_and_reconcile_on_the_claude_target():
    """The executor regeneration and the daemon reconcile are both conditioned on the Claude target."""
    text = _SKILL_MD.read_text(encoding='utf-8')
    prescriptions, _ = scan_shell_prescriptions(text)

    assert '### 3. Regenerate the on-main executor (when the Claude target synced)' in text
    assert '### 3b. Reconcile the build daemon (when the Claude target synced)' in text
    assert _RECONCILE_INVOCATION in prescriptions


def test_skill_body_display_detail_templates_name_the_per_target_result():
    """Both ``display_detail`` templates name harnesses: counts on success, each failed row otherwise."""
    text = _SKILL_MD.read_text(encoding='utf-8')
    flat = re.sub(r'\s+', ' ', text)

    assert 'claude {synced_count} bundles, opencode {deployed_count}, antigravity {deployed_count} synced' in flat
    assert '"{target}: {summary_message}"' in flat
    assert '"; claude synced, on-main executor regenerated"' in flat


# ---------------------------------------------------------------------------
# 2) NOT a built-in default — meta-project-only project step
# ---------------------------------------------------------------------------


def test_sync_plugin_cache_is_not_a_built_in_default():
    """The sync step is project-local, not a default.

    Finalize-step membership is discovered via
    ``extension_discovery.find_implementors``. A ``default:sync-plugin-cache``
    built-in id must NOT appear among the discovered finalize steps, and must
    NOT be in the default-on seed.
    """
    from extension_discovery import find_implementors

    discovered_names = {rec['name'] for rec in find_implementors(cd.FINALIZE_STEP_EXT_POINT) if rec.get('name')}
    assert 'default:sync-plugin-cache' not in discovered_names
    # Positive contract: the project-local step IS discovered under its
    # PATH-derived ``project:{dir}`` id — confirming the step is surfaced, not
    # merely that the wrong built-in id is absent.
    assert 'project:finalize-step-sync-plugin-cache' in discovered_names
    # DEFAULT_PLAN_FINALIZE['steps'] is a lazy None placeholder; the seeded map is
    # built by _seed_finalize_steps() (the discovered default-on built-in set).
    assert 'default:sync-plugin-cache' not in cd._seed_finalize_steps()


def test_no_bundled_standards_doc_for_sync_plugin_cache():
    """No bundled phase-6-finalize/standards/sync-plugin-cache.md exists — the
    step is project-local under .claude/, not in the plan-marshall bundle."""
    bundled = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'sync-plugin-cache.md'
    assert not bundled.exists(), (
        f'Unexpected bundled standards doc: {bundled}. The sync step '
        f'is project-local only; no marketplace bundle should ship it.'
    )


def test_no_bundled_skill_for_the_sync_command():
    """No bundled marketplace/bundles/plan-marshall/skills/sync-harnesses/ exists —
    the ``sync-harnesses`` command is project-local and its engine lives under
    marketplace/targets/, so nothing in the bundle ships either."""
    bundled = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'sync-harnesses'
    assert not bundled.exists(), (
        f'Unexpected bundled sync-harnesses skill: {bundled}. The command is '
        f'project-local; nothing in the bundle should ship it.'
    )


# ---------------------------------------------------------------------------
# 3) Outcome and display-detail decision branches
# ---------------------------------------------------------------------------

#: Per-harness ``(status, summary_message)`` of a harness that synced.
_SYNCED = ('success', 'synced')


def _aggregate(
    status: str,
    *,
    claude: tuple[str, str] = _SYNCED,
    opencode: tuple[str, str] = _SYNCED,
    antigravity: tuple[str, str] = _SYNCED,
) -> dict[str, Any]:
    """Build an aggregate document in the engine's shape.

    Each harness is given as its ``(status, summary_message)`` pair; the
    document carries the ``targets`` table plus one result block per harness,
    as a run of the engine with no ``--target`` emits it.
    """
    rows = {'claude': claude, 'opencode': opencode, 'antigravity': antigravity}
    return {
        'status': status,
        'targets': [
            {'target': name, 'status': row_status, 'summary_message': message}
            for name, (row_status, message) in rows.items()
        ],
        'claude': {'status': claude[0], 'synced_count': 10, 'summary_message': claude[1]},
        'opencode': {'status': opencode[0], 'deployed_count': 164, 'summary_message': opencode[1]},
        'antigravity': {'status': antigravity[0], 'deployed_count': 170, 'summary_message': antigravity[1]},
    }


def _resolve_step(document: dict[str, Any]) -> tuple[str, str, bool]:
    """Mirror the skill's Steps 2-4 decision over the engine's aggregate document.

    Returns ``(outcome, display_detail, claude_followups_run)``. ``outcome`` is
    ``'done'`` or ``'failed'``; the last element says whether the executor
    regeneration and the daemon reconcile run, which the skill keys on the
    ``claude`` row alone rather than on the aggregate status.
    """
    rows = {row['target']: row for row in document['targets']}
    claude_synced = rows['claude']['status'] == 'success'
    if document['status'] == 'success':
        detail = (
            f'claude {document["claude"]["synced_count"]} bundles, '
            f'opencode {document["opencode"]["deployed_count"]}, '
            f'antigravity {document["antigravity"]["deployed_count"]} synced; on-main executor regenerated'
        )
        return 'done', detail, claude_synced
    failures = [
        f'{row["target"]}: {row["summary_message"]}' for row in document['targets'] if row['status'] != 'success'
    ]
    detail = '; '.join(failures)
    if claude_synced:
        detail += '; claude synced, on-main executor regenerated'
    return 'failed', detail, claude_synced


@pytest.mark.parametrize(
    ('document', 'expected'),
    [
        (
            _aggregate('success'),
            ('done', 'claude 10 bundles, opencode 164, antigravity 170 synced; on-main executor regenerated', True),
        ),
        (
            _aggregate('partial', opencode=('error', 'source not found: /repo/target/opencode')),
            (
                'failed',
                'opencode: source not found: /repo/target/opencode; claude synced, on-main executor regenerated',
                True,
            ),
        ),
        (
            _aggregate('partial', claude=('error', 'staleness_guard: source tree changed since last emit')),
            ('failed', 'claude: staleness_guard: source tree changed since last emit', False),
        ),
        (
            _aggregate('partial', claude=('partial', '9 succeeded, 1 failed')),
            ('failed', 'claude: 9 succeeded, 1 failed', False),
        ),
        (
            _aggregate(
                'error',
                claude=('error', 'source root not found'),
                opencode=('error', 'source not found'),
                antigravity=('error', 'source contains no emit output'),
            ),
            (
                'failed',
                'claude: source root not found; opencode: source not found; '
                'antigravity: source contains no emit output',
                False,
            ),
        ),
    ],
    ids=[
        'all-synced',
        'partial-opencode-failed-claude-synced',
        'partial-claude-guard-refused',
        'partial-claude-bundles-failed',
        'error-none-synced',
    ],
)
def test_step_resolution(document: dict[str, Any], expected: tuple[str, str, bool]):
    """Each aggregate document resolves to its outcome, its per-target detail and its Claude follow-ups.

    The two ``partial`` cases with a failed Claude row and the one with a
    synced Claude row are the discriminating ones: the step fails in all three,
    yet the executor regeneration and the daemon reconcile run only where the
    plugin cache was actually completed.
    """
    assert _resolve_step(document) == expected
