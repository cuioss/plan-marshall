# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc tests for the workflow-resolution contract of a dispatched leaf.

Deliverable 2 of PLAN-LB-43: the agent's Step 4 calls the single
``resolve-workflow`` verb instead of mapping a notation only to
``marketplace/bundles/``, the extension-point standard states the resolution
order once, and every generated level variant carries the same Step 4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT
from marketplace.targets.antigravity.emitter import emit_bundles as emit_antigravity
from marketplace.targets.claude.variant_emitter import LEVEL_TABLE, emit_variants_for_agent
from marketplace.targets.opencode.emitter import emit_bundles as emit_opencode

AGENT = MARKETPLACE_ROOT / 'plan-marshall' / 'agents' / 'execution-context.md'
STANDARD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'extension-api'
    / 'standards'
    / 'ext-point-execution-context-workflow.md'
)
OPENCODE_CONFIG = MARKETPLACE_ROOT.parent / 'targets' / 'opencode'
ANTIGRAVITY_CONFIG = MARKETPLACE_ROOT.parent / 'targets' / 'antigravity'

VERB = 'resolve-workflow'
OLD_MAPPING = 'marketplace/bundles/{bundle}/skills/{skill}/SKILL.md'


def _step4(text: str) -> str:
    """Return the Step 4 section of the agent body."""
    start = text.index('## Step 4:')
    end = text.index('## Step 5:', start)
    return text[start:end]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def mapping_path(tmp_path: Path) -> Path:
    path = tmp_path / 'mapping.json'
    path.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {'id': 'claude-opus-4-7', 'supports_effort': ['medium', 'high', 'xhigh']},
                    'sonnet': {'id': 'claude-sonnet-4-6', 'supports_effort': ['medium', 'high']},
                    'haiku': {'id': 'claude-haiku-4-5', 'supports_effort': []},
                    'fable': {'id': 'claude-fable-5', 'supports_effort': ['medium', 'high', 'xhigh', 'max']},
                },
            }
        ),
        encoding='utf-8',
    )
    return path


@pytest.fixture()
def fixture_bundle(tmp_path: Path) -> Path:
    """A minimal marketplace tree whose agent is the REAL canonical agent."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'plan-marshall'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'plan-marshall', 'version': '0.0.1', 'agents': ['./agents/execution-context.md']}),
    )
    _write(bundle / 'agents' / 'execution-context.md', AGENT.read_text(encoding='utf-8'))
    return marketplace


# =============================================================================
# Source docs
# =============================================================================


def test_step4_calls_the_verb() -> None:
    step4 = _step4(AGENT.read_text(encoding='utf-8'))
    assert VERB in step4
    assert 'Read' in step4


def test_step4_no_longer_maps_a_notation_only_to_the_source_tree() -> None:
    step4 = _step4(AGENT.read_text(encoding='utf-8'))
    assert OLD_MAPPING not in step4


def test_standard_states_the_resolution_order_once() -> None:
    standard = STANDARD.read_text(encoding='utf-8')
    assert VERB in standard
    # Both legs of the order are named: the worktree copy first, installed second.
    assert 'worktree' in standard
    assert 'installed' in standard
    # The retired cache-only-on-Claude rule is gone.
    assert 'resolution is never performed against' not in standard


def test_the_worktree_paragraph_pins_the_declared_exception() -> None:
    """`WORKTREE` stays repo-relative; the other-repository field is declared by its workflow.

    The paragraph is the one place a dispatched leaf learns that a workflow may
    read or `git -C` outside `WORKTREE` through a declared field — and that the
    exception is read-only. It also names the standard's own heading, so the pin
    catches the dangling `§ Worktree-Resolution Root` spelling as well.
    """
    agent = AGENT.read_text(encoding='utf-8')
    standard = STANDARD.read_text(encoding='utf-8')
    paragraph = standard.split('`WORKTREE` governs where the dispatched workflow', 1)[1].split('\n\n', 1)[0]

    assert '§ Worktree-Resolution Root' not in agent, 'the agent names a heading that does not exist'
    assert '§ Workflow-Resolution Root' in agent, 'the agent does not point at the standard heading it relies on'
    assert '`WORKTREE` stays repo-relative' in paragraph, 'the paragraph does not keep `WORKTREE` repo-relative'
    assert 'never widened to carry it' in paragraph, 'the paragraph does not forbid widening `WORKTREE`'
    assert 'declared under § "Input Contract"' not in paragraph, (
        'the paragraph says the Input Contract declares the other-repository field; that section declares no such field'
    )
    assert "workflow's own input table" in paragraph, (
        "the paragraph must name the workflow's own input table as the field's declaration site"
    )
    assert 'acts outside' in paragraph and 'by design' in paragraph, (
        'the paragraph does not state that a read through the declared field acts outside `WORKTREE` by design'
    )
    assert 'Edit / Write / Read / `git -C`' in paragraph or 'Edit / Write' in paragraph, (
        'the paragraph does not name the tool calls `WORKTREE` governs'
    )


# =============================================================================
# Generated variants carry the same Step 4
# =============================================================================


def test_claude_variants_carry_step4(tmp_path: Path, mapping_path: Path) -> None:
    dest = tmp_path / 'out' / 'execution-context.md'
    emit_variants_for_agent(AGENT, dest, mapping_path)
    for level in LEVEL_TABLE:
        variant = (dest.parent / f'execution-context-{level}.md').read_text(encoding='utf-8')
        step4 = _step4(variant)
        assert VERB in step4, level
        assert OLD_MAPPING not in step4, level


def test_opencode_variants_carry_step4(fixture_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_opencode(fixture_bundle, out, OPENCODE_CONFIG)
    for level in LEVEL_TABLE:
        variant = (out / 'agent' / f'execution-context-{level}.md').read_text(encoding='utf-8')
        step4 = _step4(variant)
        assert VERB in step4, level
        assert OLD_MAPPING not in step4, level


def test_antigravity_variants_carry_step4(fixture_bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out'
    emit_antigravity(fixture_bundle, out, ANTIGRAVITY_CONFIG)
    for level in LEVEL_TABLE:
        variant = (out / 'agents' / f'execution-context-{level}.md').read_text(encoding='utf-8')
        step4 = _step4(variant)
        assert VERB in step4, level
        assert OLD_MAPPING not in step4, level
