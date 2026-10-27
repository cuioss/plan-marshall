# SPDX-License-Identifier: FSL-1.1-ALv2
"""D4 — a lane run cannot write a tracked file of the MAIN checkout.

A runbook-lane run issues every tool call with the MAIN checkout as its working
directory and implements inside ``.plan/local/worktrees/<plan>``. Three of seven
audited runs wrote tracked files into the main checkout before switching to their
worktree (PLAN-LB-43 twelve edits, PLAN-LB-55 two edits plus a draft, PLAN-LB-85
fourteen), because nothing refused it: the edit-tool handler judged only R3 (the
generated executor path).

Both harnesses carry the SAME rule, exercised here by real execution — the
OpenCode plugin under ``node`` and the Claude hook's ``evaluate``:

* a lane run's edit of a main-checkout path is refused, and the refusal names the
  worktree path to use instead;
* the same edit inside the lane's worktree passes;
* ``.plan/temp/rb-<plan>/progress.md`` passes (the lane's own bookkeeping);
* with NO lane marker the main-checkout edit passes (a developer session);
* with a marker but NO matching worktree it passes too — the binding is narrow on
  purpose, so a stale marker cannot refuse a developer's ordinary work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from _guard_node_harness import SUB_AGENT_AGENT, GuardHarness, build_harness, edit_event

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='lane_write_pretooluse_hook',
    register=False,
)

LANE = 'lane-a'
MAIN_CHECKOUT_TARGET = 'marketplace/bundles/plan-marshall/skills/x/scripts/x.py'


def _lane_marker(root: Path, lane: str = LANE) -> Path:
    """Write the runbook-lane marker the guard's Signal 3 reads."""
    marker = root / '.plan' / 'temp' / f'rb-{lane}' / 'progress.md'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('lane run\n', encoding='utf-8')
    return marker


def _lane_worktree(root: Path, lane: str = LANE) -> Path:
    """Create the worktree directory the marker maps onto."""
    worktree = root / '.plan' / 'local' / 'worktrees' / lane
    worktree.mkdir(parents=True, exist_ok=True)
    return worktree


def _hook_payload(file_path: str, root: Path) -> dict[str, Any]:
    """A Claude ``Edit`` payload rooted at the fixture checkout."""
    return {
        'tool_name': 'Edit',
        'tool_input': {'file_path': file_path},
        'cwd': str(root),
        'agent_type': SUB_AGENT_AGENT,
    }


@pytest.fixture
def harness(tmp_path_factory: pytest.TempPathFactory) -> GuardHarness:
    """A node scratch root running the real guard plugin."""
    return build_harness(tmp_path_factory.mktemp('guard-lane-write'))


@pytest.fixture(autouse=True)
def _no_ambient_project_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook anchors R7 on ``CLAUDE_PROJECT_DIR`` or the payload cwd — never both."""
    monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)


def _both(harness: GuardHarness, root: Path, file_path: str) -> tuple[tuple[bool, str], str | None]:
    """Run one edit through both harnesses; return the guard outcome and hook reason."""
    guard_blocked, guard_message = harness.blocks(edit_event(file_path, agent=SUB_AGENT_AGENT))
    return (guard_blocked, guard_message), _HOOK.evaluate(_hook_payload(file_path, root))


def test_a_lane_run_may_not_edit_a_main_checkout_path(harness: GuardHarness) -> None:
    """The first direction: refused by BOTH, and the worktree path is named."""
    root = harness.root
    _lane_marker(root)
    worktree = _lane_worktree(root)
    target = root / MAIN_CHECKOUT_TARGET

    (blocked, message), hook_reason = _both(harness, root, str(target))

    assert blocked, f'guard.js must refuse a lane edit of the main checkout; message={message!r}'
    assert str(worktree) in message, f'the refusal must name the worktree to use; message={message!r}'
    assert hook_reason is not None, 'the hook must refuse the same edit'
    assert str(worktree) in hook_reason, f'the hook refusal must name the worktree; reason={hook_reason!r}'


def test_the_same_edit_inside_the_lane_worktree_passes(harness: GuardHarness) -> None:
    """The sanctioned path: the worktree copy is where the work belongs."""
    root = harness.root
    _lane_marker(root)
    worktree = _lane_worktree(root)

    (blocked, message), hook_reason = _both(harness, root, str(worktree / MAIN_CHECKOUT_TARGET))

    assert not blocked, message
    assert hook_reason is None


def test_the_lane_progress_file_passes(harness: GuardHarness) -> None:
    """``.plan/temp/rb-<plan>/progress.md`` is the lane's own bookkeeping."""
    root = harness.root
    marker = _lane_marker(root)
    _lane_worktree(root)

    (blocked, message), hook_reason = _both(harness, root, str(marker))

    assert not blocked, message
    assert hook_reason is None


def test_without_a_lane_marker_the_main_checkout_edit_passes(harness: GuardHarness) -> None:
    """A developer session in the main checkout is not refused."""
    root = harness.root
    _lane_worktree(root)

    (blocked, message), hook_reason = _both(harness, root, str(root / MAIN_CHECKOUT_TARGET))

    assert not blocked, message
    assert hook_reason is None


def test_a_marker_without_a_matching_worktree_passes(harness: GuardHarness) -> None:
    """A stale marker cannot refuse ordinary work: the binding needs the worktree."""
    root = harness.root
    _lane_marker(root)

    (blocked, message), hook_reason = _both(harness, root, str(root / MAIN_CHECKOUT_TARGET))

    assert not blocked, message
    assert hook_reason is None
