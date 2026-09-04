#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Unit tests for the project-local sync_opencode.py deploy engine.

Covers the singular→plural path mapping, --dry-run (no filesystem
effect, actions listed), --bundles subsetting, stale-managed-entry
deletion, preservation of unmanaged destination entries, and
preservation of unselected bundles' entries under --bundles — all
against temp directories, no live OpenCode install.

The script under test lives at
``.claude/skills/sync-opencode/scripts/sync_opencode.py`` (project-local),
not in any marketplace bundle — sync-opencode is meta-project-only
tooling that does not ship to consumers of plan-marshall.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


from conftest import PROJECT_ROOT
from toon_parser import parse_toon

_SYNC_OP_XPY = PROJECT_ROOT / '.claude' / 'skills' / 'sync-opencode' / 'scripts' / 'sync_opencode.py'

# Singular source components → plural destination components, and the
# emitter's singular directory layout under the source root.
_SKILL_SRC = 'skill/plan-marshall-sync-opencode'
_AGENT_SRC = 'agent/execution-context.md'
_ANOTHER_AGENT_SRC = 'agent/execution-context-reader.md'
_COMMAND_SRC = 'command/plan-marshall-sync-opencode.md'


def _write(path: Path, content: str | bytes = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


def _make_source(target_root: Path, *, with_agent: bool = True) -> None:
    """Build a fixture target/opencode/ tree with realistic singular layout."""
    _write(target_root / _SKILL_SRC / 'SKILL.md', '---\nname: sync-opencode\n---\nbody\n')
    _write(target_root / _SKILL_SRC / 'standards' / 'note.md', '# standards\n')
    _write(target_root / _COMMAND_SRC, '---\nname: plan-marshall-sync-opencode\n---\ncmd\n')
    if with_agent:
        _write(target_root / _AGENT_SRC, '---\nname: execution-context\n---\nagent\n')
        _write(target_root / _ANOTHER_AGENT_SRC, '---\nname: execution-context-reader\n---\nagent\n')
    _write(target_root / 'opencode.json', '{"skills": {"paths": ["./skill"]}}\n')


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SYNC_OP_XPY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Singular → plural path mapping
# ---------------------------------------------------------------------------


def test_sync_opencode_maps_singular_to_plural(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr

    # Skill dir relocated into plural skills/
    assert (dest / 'skills' / 'plan-marshall-sync-opencode').exists()
    assert not (dest / 'skill' / 'plan-marshall-sync-opencode').exists()
    assert (dest / 'skills' / 'plan-marshall-sync-opencode' / 'SKILL.md').is_file()
    assert (dest / 'skills' / 'plan-marshall-sync-opencode' / 'standards' / 'note.md').is_file()

    # Command relocated into plural commands/
    assert (dest / 'commands' / 'plan-marshall-sync-opencode.md').is_file()
    assert not (dest / 'command' / 'plan-marshall-sync-opencode.md').exists()

    # Agent files relocated into plural agents/
    assert (dest / 'agents' / 'execution-context.md').is_file()
    assert (dest / 'agents' / 'execution-context-reader.md').is_file()
    assert not (dest / 'agent' / 'execution-context.md').exists()


def test_sync_opencode_deploy_counts_match_rows(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest), '--dry-run')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    # Skill SKILL.md + skill standards sub-dir + command + 2 agents + config
    assert int(data['deployed_count']) == 6


# ---------------------------------------------------------------------------
# --dry-run: no filesystem effect, actions listed
# ---------------------------------------------------------------------------


def test_sync_opencode_dry_run_lists_actions_and_noops(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest), '--dry-run')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    assert data['dry_run'] is True
    # Nothing written to disk.
    assert not dest.exists()
    # Actions are listed.
    assert data['summary_message']


def test_sync_opencode_dry_run_does_not_prune(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    # Plant a stale managed skill in the destination that should be pruned on
    # a real run but left in place on --dry-run.
    _write(dest / 'skills' / 'plan-marshall-stale' / 'SKILL.md', '# stale\n')

    result = _run('--source', str(source), '--target-dir', str(dest), '--dry-run')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    assert int(data['removed_count']) == 1
    # Dry-run leaves the file untouched.
    assert (dest / 'skills' / 'plan-marshall-stale' / 'SKILL.md').is_file()


# ---------------------------------------------------------------------------
# Deployment (real run)
# ---------------------------------------------------------------------------


def test_sync_opencode_real_deploy_writes_plural_layout(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'plan-marshall-sync-opencode' / 'SKILL.md').is_file()
    assert (dest / 'commands' / 'plan-marshall-sync-opencode.md').is_file()
    assert (dest / 'agents' / 'execution-context.md').is_file()


def test_sync_opencode_real_deploy_emits_toon_without_dry_run(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source, with_agent=False)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert 'dry_run' not in data


# ---------------------------------------------------------------------------
# Stale managed-entry deletion
# ---------------------------------------------------------------------------


def test_sync_opencode_prunes_stale_managed_skill(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    _write(dest / 'skills' / 'plan-marshall-gone' / 'SKILL.md', '# gone\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert not (dest / 'skills' / 'plan-marshall-gone').exists()
    data = parse_toon(result.stdout)
    assert int(data['removed_count']) == 1
    assert 'plan-marshall-gone' in result.stdout


def test_sync_opencode_prunes_stale_managed_command(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    _write(dest / 'commands' / 'plan-marshall-gone-command.md', '# gone\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert not (dest / 'commands' / 'plan-marshall-gone-command.md').exists()


def test_sync_opencode_preserves_unmanaged_entries(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    # User-managed entry — not in the {bundle}-{skill} namespace of a synced bundle.
    _write(dest / 'skills' / 'my-personal-skill' / 'SKILL.md', '# mine\n')
    # Agent files are never pruned even though they don't match the source.
    _write(dest / 'agents' / 'unmanaged-agent.md', '# agent\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'my-personal-skill' / 'SKILL.md').is_file()
    assert (dest / 'agents' / 'unmanaged-agent.md').is_file()


def test_sync_opencode_preserves_unmanaged_skill_matching_other_bundle(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    # A skill from a bundle NOT being synced must survive.
    _write(dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md', '# other\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md').is_file()


def test_sync_opencode_preserves_user_entry_that_shares_bundle_prefix(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    # An unrelated user entry whose name starts with the truncated first-hyphen
    # token of a synced bundle (e.g. "plan-" from "plan-marshall"). Exact bundle
    # name resolution must NOT treat it as managed, so it survives pruning.
    _write(dest / 'skills' / 'plan-my-personal-tool' / 'SKILL.md', '# mine\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'plan-my-personal-tool' / 'SKILL.md').is_file()


# ---------------------------------------------------------------------------
# --bundles subsetting
# ---------------------------------------------------------------------------


def test_sync_opencode_bundles_flag_preserves_unselected_bundle_entries(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    _make_source(source)
    # Seed the destination with an entry belonging to a bundle that is NOT
    # selected. It must survive a --bundles plan-marshall run.
    _write(dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md', '# other\n')
    # Seed a stale managed entry that IS selected and should be pruned.
    _write(dest / 'skills' / 'plan-marshall-gone' / 'SKILL.md', '# gone\n')

    result = _run(
        '--source', str(source),
        '--target-dir', str(dest),
        '--bundles', 'plan-marshall',
    )
    assert result.returncode == 0, result.stderr
    # Selected bundle's stale entry pruned.
    assert not (dest / 'skills' / 'plan-marshall-gone').exists()
    # Unselected bundle's entry preserved.
    assert (dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md').is_file()


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_sync_opencode_missing_source_returns_error(tmp_path: Path):
    source = tmp_path / 'nosuch' / 'opencode'
    dest = tmp_path / 'dest'

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'source not found' in data['summary_message']


def test_sync_opencode_empty_source_returns_error(tmp_path: Path):
    source = tmp_path / 'src' / 'opencode'
    dest = tmp_path / 'dest'
    source.mkdir(parents=True, exist_ok=True)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'contains no emit output' in data['summary_message']
