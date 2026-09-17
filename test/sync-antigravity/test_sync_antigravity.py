#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Unit tests for the project-level sync_antigravity.py deploy engine.

Covers the component deployment, root asset handling (plugin.json,
install.sh, README.adoc), --dry-run (no filesystem effect, actions listed),
--bundles subsetting, stale-managed-entry deletion, preservation of
unmanaged destination entries, preservation of unselected bundles'
entries under --bundles, and the prefix-ambiguous bundle derivation
(longest match resolves exactly one bundle per entry) — all against
temp directories, no live Antigravity install.

The script under test lives at ``.agents/scripts/sync_antigravity.py``
(project-level, deployed as the ``/sync-antigravity`` Antigravity command
from ``.agents/commands/``), not in any marketplace bundle — sync-antigravity
is meta-project-only tooling that does not ship to consumers of
plan-marshall.
"""

from __future__ import annotations

import os
from pathlib import Path

from conftest import PROJECT_ROOT, ScriptResult, run_script
from toon_parser import parse_toon

_SYNC_AG_PY = PROJECT_ROOT / '.agents' / 'scripts' / 'sync_antigravity.py'

# Antigravity uses plural component layout in both source and destination.
_SKILL_SRC = 'skills/plan-marshall-sync-antigravity'
_AGENT_SRC = 'agents/execution-context.md'
_ANOTHER_AGENT_SRC = 'agents/execution-context-reader.md'
_COMMAND_SRC = 'commands/plan-marshall-sync-antigravity.md'


def _write(path: Path, content: str | bytes = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


def _make_source(target_root: Path, *, with_agent: bool = True, with_root_assets: bool = True) -> None:
    """Build a fixture target/antigravity/ tree with realistic layout."""
    _write(target_root / _SKILL_SRC / 'SKILL.md', '---\nname: sync-antigravity\n---\nbody\n')
    _write(target_root / _SKILL_SRC / 'standards' / 'note.md', '# standards\n')
    _write(target_root / _COMMAND_SRC, '---\nname: plan-marshall-sync-antigravity\n---\ncmd\n')
    if with_agent:
        _write(target_root / _AGENT_SRC, '---\nname: execution-context\n---\nagent\n')
        _write(target_root / _ANOTHER_AGENT_SRC, '---\nname: execution-context-reader\n---\nagent\n')
    if with_root_assets:
        _write(target_root / 'plugin.json', '{"name": "plan-marshall"}\n')
        _write(target_root / 'install.sh', '#!/usr/bin/env bash\necho install\n')
        _write(target_root / 'README.adoc', '= Plan Marshall\n')


def _run(*args: str, cwd: Path | None = None) -> ScriptResult:
    return run_script(_SYNC_AG_PY, *args, cwd=cwd, timeout=60)


# ---------------------------------------------------------------------------
# Path mapping and component deployment
# ---------------------------------------------------------------------------


def test_sync_antigravity_deploys_components(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr

    # Skill dir deployed into skills/
    assert (dest / 'skills' / 'plan-marshall-sync-antigravity').exists()
    assert (dest / 'skills' / 'plan-marshall-sync-antigravity' / 'SKILL.md').is_file()
    assert (dest / 'skills' / 'plan-marshall-sync-antigravity' / 'standards' / 'note.md').is_file()

    # Command deployed into commands/
    assert (dest / 'commands' / 'plan-marshall-sync-antigravity.md').is_file()

    # Agent files deployed into agents/
    assert (dest / 'agents' / 'execution-context.md').is_file()
    assert (dest / 'agents' / 'execution-context-reader.md').is_file()

    # Root plugin assets deployed
    assert (dest / 'plugin.json').is_file()
    assert (dest / 'install.sh').is_file()
    assert (dest / 'README.adoc').is_file()
    assert os.stat(dest / 'install.sh').st_mode & 0o111 != 0


def test_sync_antigravity_deploy_counts_match_rows(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest), '--dry-run')
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    # Skill SKILL.md + standards sub-dir + command + 2 agents + plugin.json + install.sh + README.adoc = 8
    assert int(data['deployed_count']) == 8
    assert len(data['deployed']) == 8


# ---------------------------------------------------------------------------
# --dry-run: no filesystem effect, actions listed
# ---------------------------------------------------------------------------


def test_sync_antigravity_dry_run_lists_actions_and_noops(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
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


def test_sync_antigravity_dry_run_does_not_prune(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
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


def test_sync_antigravity_real_deploy_writes_layout(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'plan-marshall-sync-antigravity' / 'SKILL.md').is_file()
    assert (dest / 'commands' / 'plan-marshall-sync-antigravity.md').is_file()
    assert (dest / 'agents' / 'execution-context.md').is_file()
    assert (dest / 'plugin.json').is_file()


def test_sync_antigravity_real_deploy_emits_toon_without_dry_run(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
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


def test_sync_antigravity_prunes_stale_managed_skill(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    _write(dest / 'skills' / 'plan-marshall-gone' / 'SKILL.md', '# gone\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert not (dest / 'skills' / 'plan-marshall-gone').exists()
    data = parse_toon(result.stdout)
    assert int(data['removed_count']) == 1
    assert 'plan-marshall-gone' in result.stdout


def test_sync_antigravity_prunes_stale_managed_command(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    _write(dest / 'commands' / 'plan-marshall-gone-command.md', '# gone\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert not (dest / 'commands' / 'plan-marshall-gone-command.md').exists()


def test_sync_antigravity_preserves_unmanaged_entries(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
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


def test_sync_antigravity_preserves_unmanaged_skill_matching_other_bundle(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    # A skill from a bundle NOT being synced must survive.
    _write(dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md', '# other\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    assert (dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md').is_file()


def test_sync_antigravity_preserves_user_entry_that_shares_bundle_prefix(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
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


def test_sync_antigravity_bundles_flag_preserves_unselected_bundle_entries(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    # Seed the destination with an entry belonging to a bundle that is NOT
    # selected. It must survive a --bundles plan-marshall run.
    _write(dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md', '# other\n')
    # Seed a stale managed entry that IS selected and should be pruned.
    _write(dest / 'skills' / 'plan-marshall-gone' / 'SKILL.md', '# gone\n')

    result = _run(
        '--source',
        str(source),
        '--target-dir',
        str(dest),
        '--bundles',
        'plan-marshall',
    )
    assert result.returncode == 0, result.stderr
    # Selected bundle's stale entry pruned.
    assert not (dest / 'skills' / 'plan-marshall-gone').exists()
    # Unselected bundle's entry preserved.
    assert (dest / 'skills' / 'other-bundle-stuff' / 'SKILL.md').is_file()


def test_sync_antigravity_bundles_flag_deploys_exact_bundle_named_command(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    # Add a command named exactly {bundle}.md (e.g. plan-marshall.md)
    _write(source / 'commands' / 'plan-marshall.md', '---\nname: plan-marshall\n---\n')

    result = _run(
        '--source',
        str(source),
        '--target-dir',
        str(dest),
        '--bundles',
        'plan-marshall',
    )
    assert result.returncode == 0, result.stderr
    assert (dest / 'commands' / 'plan-marshall.md').is_file()


# ---------------------------------------------------------------------------
# Prefix-ambiguous bundle derivation
# ---------------------------------------------------------------------------


def _find_prefix_ambiguous_pair(bundles_dir: Path) -> tuple[str, str] | None:
    """Find a real prefix-ambiguous bundle pair from the marketplace tree.

    Scans ``bundles_dir`` for any two bundle names where one name plus ``-``
    is a prefix of the other.  Returns the shorter / longer pair or ``None``
    when no ambiguous pair exists.
    """
    names = sorted(p.name for p in bundles_dir.iterdir() if p.is_dir())
    for i, shorter in enumerate(names):
        for longer in names[i + 1 :]:
            if longer.startswith(f'{shorter}-'):
                return shorter, longer
    return None


_BUNDLES_DIR = PROJECT_ROOT / 'marketplace' / 'bundles'

_REQUIRED_PREFIX_AMBIGUOUS_PAIRS = (
    ('pm-dev-frontend', 'pm-dev-frontend-cui'),
    ('pm-dev-java', 'pm-dev-java-cui'),
)

_MISSING_REQUIRED_PAIRS = [
    f'{shorter}/{longer}'
    for shorter, longer in _REQUIRED_PREFIX_AMBIGUOUS_PAIRS
    if not ((_BUNDLES_DIR / shorter).is_dir() and (_BUNDLES_DIR / longer).is_dir())
]
assert not _MISSING_REQUIRED_PAIRS, (
    f'Required prefix-ambiguous bundle pair(s) absent from {_BUNDLES_DIR}: '
    f'{", ".join(_MISSING_REQUIRED_PAIRS)}. This repository ships both pairs, so '
    'an absence means a bundle was renamed or removed — not that these tests do '
    'not apply to this checkout.'
)

_PREFIX_AMBIGUOUS_PAIR = _find_prefix_ambiguous_pair(_BUNDLES_DIR)
assert _PREFIX_AMBIGUOUS_PAIR is not None, (
    f'_find_prefix_ambiguous_pair derived no pair from {_BUNDLES_DIR} even though '
    f'{_REQUIRED_PREFIX_AMBIGUOUS_PAIRS[0][0]}/{_REQUIRED_PREFIX_AMBIGUOUS_PAIRS[0][1]} '
    'is present — the derivation itself is broken.'
)


def test_sync_antigravity_prefix_ambiguous_shorter_bundle_preserved(tmp_path: Path):
    """Source carries only the LONGER bundle's entries; shorter bundle's stale
    destination entry must NOT be pruned.

    The script derives the managed set from ``marketplace/bundles/``.  When
    only the LONGER bundle's entries are in the source the derivation must
    resolve exactly one bundle (the longer), so the shorter bundle's destination
    entries are NOT managed and must survive.
    """
    shorter, longer = _PREFIX_AMBIGUOUS_PAIR

    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    # Source carries ONE entry belonging to the LONGER bundle only.
    _write(source / 'skills' / f'{longer}-sample' / 'SKILL.md', 'body\n')
    _write(source / 'plugin.json', '{}\n')
    # Destination has a stale entry belonging to the SHORTER bundle.
    _write(dest / 'skills' / f'{shorter}-gone' / 'SKILL.md', '# stale\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    # The shorter bundle's entry must survive — it is NOT managed when the
    # source carries only the longer bundle.
    assert (dest / 'skills' / f'{shorter}-gone' / 'SKILL.md').is_file(), (
        f'{shorter}-gone was pruned: the derivation resolved {shorter} when the source '
        f'carried only {longer} entries — prefix ambiguity resolved incorrectly'
    )


def test_sync_antigravity_prefix_ambiguous_both_bundles_managed(tmp_path: Path):
    """Source carries entries for BOTH ambiguous bundles; both must be managed.

    When the source carries entries from both the shorter and longer bundle
    the derivation must resolve exactly two bundles and prune stale entries
    belonging to either.
    """
    shorter, longer = _PREFIX_AMBIGUOUS_PAIR

    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    # Source carries entries for both bundles.
    _write(source / 'skills' / f'{shorter}-keep' / 'SKILL.md', 'body\n')
    _write(source / 'skills' / f'{longer}-keep' / 'SKILL.md', 'body\n')
    _write(source / 'plugin.json', '{}\n')
    # Destination has stale entries for both bundles.
    _write(dest / 'skills' / f'{shorter}-gone' / 'SKILL.md', '# stale\n')
    _write(dest / 'skills' / f'{longer}-gone' / 'SKILL.md', '# stale\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    # Both bundles should be in the managed set; both stale entries pruned.
    removed_names = {r['name'] for r in data['removed']}
    assert f'{shorter}-gone' in removed_names, (
        f'{shorter}-gone not pruned when source carries both {shorter} and {longer}'
    )
    assert f'{longer}-gone' in removed_names, (
        f'{longer}-gone not pruned when source carries both {shorter} and {longer}'
    )


# ---------------------------------------------------------------------------
# Verbatim subdirectories
# ---------------------------------------------------------------------------


def test_sync_antigravity_copies_verbatim_subdirs(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    _make_source(source)
    _write(source / _SKILL_SRC / 'references' / 'manual.md', '# ref\n')
    _write(source / _SKILL_SRC / 'templates' / 'tpl.txt', 'tpl\n')
    _write(source / _SKILL_SRC / 'scripts' / 'run.sh', '#!/bin/sh\n')

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 0, result.stderr
    skill_dst = dest / 'skills' / 'plan-marshall-sync-antigravity'
    assert (skill_dst / 'standards' / 'note.md').is_file()
    assert (skill_dst / 'references' / 'manual.md').is_file()
    assert (skill_dst / 'templates' / 'tpl.txt').is_file()
    assert (skill_dst / 'scripts' / 'run.sh').is_file()


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_sync_antigravity_missing_source_returns_error(tmp_path: Path):
    source = tmp_path / 'nosuch' / 'antigravity'
    dest = tmp_path / 'dest'

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'source not found' in data['summary_message']


def test_sync_antigravity_empty_source_returns_error(tmp_path: Path):
    source = tmp_path / 'src' / 'antigravity'
    dest = tmp_path / 'dest'
    source.mkdir(parents=True, exist_ok=True)

    result = _run('--source', str(source), '--target-dir', str(dest))
    assert result.returncode == 1
    data = parse_toon(result.stdout)
    assert data['status'] == 'error'
    assert 'contains no emit output' in data['summary_message']
