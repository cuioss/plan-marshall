# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Claude verbatim emitter."""

import json
import shutil
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.claude.emitter import (
    EXCLUDED_DIR_NAMES,
    emit_bundle_verbatim,
    iter_bundle_dirs,
)
from marketplace.targets.claude.equality_check import run_equality_check
from marketplace.targets.claude.target import (
    EMIT_MARKER_FILENAME,
    ClaudeTarget,
    prune_removed_bundles,
)

# SHA-1 of empty input — the regression signal that the sentinel writer
# computed the fingerprint against the wrong repo_root (one level too
# deep), causing ``git ls-files`` to find zero tracked files under the
# nonexistent ``marketplace/bundles`` prefix and SHA-1-ing the empty
# stream. See marketplace/targets/claude/target.py line 153.
_EMPTY_INPUT_SHA1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'

# Repository root: the directory that contains ``marketplace/``. The
# test invokes ClaudeTarget().generate(...) with marketplace_dir pointing
# at this repo's actual ``marketplace/bundles/`` so the sentinel writer
# exercises the real git work tree (uncommitted edits are part of the
# fingerprint by design — see source_fingerprint.py).
_REPO_ROOT = PROJECT_ROOT
_REAL_MARKETPLACE_BUNDLES = _REPO_ROOT / 'marketplace' / 'bundles'


def _write_bundle(bundle_root: Path, bundle_name: str, files: dict[str, str | bytes]) -> Path:
    bundle_dir = bundle_root / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = bundle_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding='utf-8')
    return bundle_dir


@pytest.fixture()
def fixture_marketplace(tmp_path: Path) -> Path:
    """Build a tiny marketplace tree with a single complete bundle."""
    marketplace = tmp_path / 'bundles'
    marketplace.mkdir()
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'Demo bundle',
            'agents': ['./agents/demo-agent.md'],
            'commands': [],
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write_bundle(
        marketplace,
        'demo',
        {
            '.claude-plugin/plugin.json': plugin_doc,
            'agents/demo-agent.md': '---\nname: demo-agent\n---\nbody',
            'skills/demo-skill/SKILL.md': '---\nname: demo-skill\ndescription: demo\n---\n# demo',
            'skills/demo-skill/standards/rule.md': '# rule\n',
            'README.md': '# demo bundle\n',
            'skills/demo-skill/__pycache__/junk.pyc': b'\x00\x01',
        },
    )
    return marketplace


def test_iter_bundle_dirs_yields_only_bundles(fixture_marketplace: Path):
    bundles = list(iter_bundle_dirs(fixture_marketplace, None))
    assert [b.name for b in bundles] == ['demo']


def test_iter_bundle_dirs_filters_by_name(fixture_marketplace: Path):
    bundles = list(iter_bundle_dirs(fixture_marketplace, ['nonexistent']))
    assert bundles == []


def test_emit_bundle_verbatim_byte_equal(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    written = emit_bundle_verbatim(bundle_dir, out_dir)

    # plugin.json is excluded — emitter does not write it.
    assert all('plugin.json' not in str(p) for p in written), written

    # README and skill body are byte-equal to source.
    assert (out_dir / 'demo' / 'README.md').read_bytes() == (bundle_dir / 'README.md').read_bytes()
    skill_path = out_dir / 'demo' / 'skills' / 'demo-skill' / 'SKILL.md'
    assert skill_path.read_bytes() == (bundle_dir / 'skills' / 'demo-skill' / 'SKILL.md').read_bytes()


def test_emit_bundle_verbatim_excludes_pycache(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)
    # __pycache__ should never appear in the mirror.
    pycache_present = any('__pycache__' in str(p) for p in (out_dir / 'demo').rglob('*'))
    assert not pycache_present
    assert '__pycache__' in EXCLUDED_DIR_NAMES


def test_emit_bundle_verbatim_excludes_plugin_json(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)
    target_plugin_json = out_dir / 'demo' / '.claude-plugin' / 'plugin.json'
    assert not target_plugin_json.exists()


def test_emit_bundle_verbatim_directory_structure(fixture_marketplace: Path, tmp_path: Path):
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)

    expected_files = {
        'README.md',
        'agents/demo-agent.md',
        'skills/demo-skill/SKILL.md',
        'skills/demo-skill/standards/rule.md',
    }
    actual = {
        str(p.relative_to(out_dir / 'demo'))
        for p in (out_dir / 'demo').rglob('*')
        if p.is_file() and '__pycache__' not in str(p)
    }
    assert expected_files.issubset(actual), actual - expected_files


def test_emit_bundle_verbatim_wipes_stale_artifacts(fixture_marketplace: Path, tmp_path: Path):
    """Pre-emit cleanup: the destination bundle dir is wiped before copying so
    stale artifacts from a prior emit (e.g. variant files for a source canonical
    that has since been removed) do NOT linger in the target tree.
    """
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'

    # Simulate leftovers from a prior emit run: a canonical and its variants
    # that no longer exist in source, plus a stale skill standards file.
    stale_canonical = out_dir / 'demo' / 'agents' / 'removed-agent.md'
    stale_variant = out_dir / 'demo' / 'agents' / 'removed-agent-high.md'
    stale_skill_file = out_dir / 'demo' / 'skills' / 'deleted-skill' / 'SKILL.md'
    for stale in (stale_canonical, stale_variant, stale_skill_file):
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text('---\nname: stale\n---\nstale body', encoding='utf-8')

    emit_bundle_verbatim(bundle_dir, out_dir)

    assert not stale_canonical.exists()
    assert not stale_variant.exists()
    assert not stale_skill_file.exists()
    # Fresh source content was emitted in their place.
    assert (out_dir / 'demo' / 'agents' / 'demo-agent.md').is_file()


def test_emit_bundle_verbatim_does_not_touch_sibling_bundles(tmp_path: Path):
    """The wipe is scoped to the emitting bundle's destination directory —
    sibling bundles and the top-level ``.claude-plugin/`` (which holds the
    marketplace.json registration manifest) must NOT be affected.
    """
    marketplace = tmp_path / 'bundles'
    out_dir = tmp_path / 'out'
    plugin_doc = json.dumps(
        {'name': 'a', 'version': '0.0.1', 'description': 'a'}, indent=2
    ) + '\n'
    _write_bundle(
        marketplace,
        'a',
        {
            '.claude-plugin/plugin.json': plugin_doc,
            'agents/a-agent.md': '---\nname: a-agent\n---\nbody',
        },
    )

    # Pre-populate the output with a sibling bundle AND a top-level
    # .claude-plugin/marketplace.json.
    sibling_file = out_dir / 'b' / 'agents' / 'b-agent.md'
    sibling_file.parent.mkdir(parents=True, exist_ok=True)
    sibling_file.write_text('---\nname: b-agent\n---\nbody', encoding='utf-8')
    top_marketplace = out_dir / '.claude-plugin' / 'marketplace.json'
    top_marketplace.parent.mkdir(parents=True, exist_ok=True)
    top_marketplace.write_text('{"name": "marketplace"}\n', encoding='utf-8')

    emit_bundle_verbatim(marketplace / 'a', out_dir)

    assert sibling_file.is_file()
    assert top_marketplace.is_file()
    assert (out_dir / 'a' / 'agents' / 'a-agent.md').is_file()


# =============================================================================
# Wipe-guard matched control (D1)
# =============================================================================
#
# ``emit_bundle_verbatim`` wipes ``output_dir/{bundle}`` before copying. A
# mistyped ``output_dir`` pointing at a tree containing the bundle source would
# make ``dest_root`` the source bundle itself, so the wipe destroys real source.
# The guard refuses a destination inside the source tree. The control has BOTH
# halves — refusing the source-overlap case must NOT break legitimate emits.


def test_emit_bundle_verbatim_refuses_output_inside_source_tree(fixture_marketplace: Path):
    """Negative half: an ``output_dir`` pointing INTO the source tree is refused,
    and the source it would have wiped survives untouched.
    """
    bundle_dir = fixture_marketplace / 'demo'
    source_skill = bundle_dir / 'skills' / 'demo-skill' / 'SKILL.md'
    source_bytes = source_skill.read_bytes()

    # output_dir == the source marketplace root, so dest_root == the bundle's
    # own source directory.
    with pytest.raises(ValueError, match='source tree'):
        emit_bundle_verbatim(bundle_dir, fixture_marketplace)

    # The refusal happened BEFORE any deletion — the source is intact.
    assert source_skill.read_bytes() == source_bytes
    assert (bundle_dir / '.claude-plugin' / 'plugin.json').is_file()


def test_emit_bundle_verbatim_legitimate_output_still_wipes(fixture_marketplace: Path, tmp_path: Path):
    """Positive half: a legitimate ``output_dir`` distinct from the source tree
    still wipes stale content and emits — the guard does not refuse everything.
    """
    bundle_dir = fixture_marketplace / 'demo'
    out_dir = tmp_path / 'out'
    stale = out_dir / 'demo' / 'agents' / 'removed-agent.md'
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('stale', encoding='utf-8')

    written = emit_bundle_verbatim(bundle_dir, out_dir)

    assert not stale.exists()  # the stale artifact was wiped
    assert (out_dir / 'demo' / 'agents' / 'demo-agent.md').is_file()  # fresh emit
    assert written  # a non-empty emit occurred


# =============================================================================
# Removed-bundle prune (D7/G7)
# =============================================================================
#
# ``emit_bundle_verbatim`` wipes and rewrites only the directories it emits, so
# a bundle DELETED from source leaves its whole emitted directory behind. The
# equality check cannot see it — that engine iterates the SOURCE bundles, so a
# directory no source bundle names is never looked at, and its silence is an
# absence of a look rather than a clean verdict. Both directions are pinned:
# the prune must remove the orphan, and must not remove anything else.

#: A directory name no source bundle will ever have, injected into the output
#: tree to stand in for a bundle that was deleted from source.
_ORPHAN_DIR_NAME = 'zz-removed'


def _synthetic_marketplace(root: Path, bundle_names: list[str]) -> Path:
    """Build a source marketplace of ``bundle_names`` and return its bundles dir.

    Laid out as the real tree is — ``{root}/.claude-plugin/marketplace.json``
    beside ``{root}/bundles/{name}/`` — because ``ClaudeTarget.generate``
    regenerates the top-level manifest from ``marketplace_dir.parent``.
    """
    bundles = root / 'bundles'
    bundles.mkdir(parents=True, exist_ok=True)
    for name in bundle_names:
        _write_bundle(
            bundles,
            name,
            {
                '.claude-plugin/plugin.json': json.dumps(
                    {'name': name, 'version': '0.0.1', 'description': name}, indent=2
                ) + '\n',
                f'agents/{name}-agent.md': f'---\nname: {name}-agent\n---\nbody',
            },
        )
    manifest = {
        'name': 'demo-marketplace',
        'plugins': [
            {'name': n, 'description': n, 'source': f'./bundles/{n}'} for n in bundle_names
        ],
    }
    manifest_path = root / '.claude-plugin' / 'marketplace.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return bundles


def _plant_orphan(output_dir: Path) -> Path:
    orphan = output_dir / _ORPHAN_DIR_NAME / 'agents' / 'ghost.md'
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('---\nname: ghost\n---\nleft over from a deleted bundle', encoding='utf-8')
    return output_dir / _ORPHAN_DIR_NAME


def test_prune_removed_bundles_removes_only_the_directories_no_source_names(tmp_path: Path):
    """The unit contract: unnamed bundle dirs go, everything else stays.

    ``.claude-plugin`` holds the top-level marketplace.json and is not a
    bundle; root-level files (the emit sentinel, dist-manifest.json) are not
    bundles either. A prune that took them would break the published tree it
    was meant to clean.
    """
    output_dir = tmp_path / 'out'
    (output_dir / 'alpha').mkdir(parents=True)
    (output_dir / '.claude-plugin').mkdir(parents=True)
    orphan = _plant_orphan(output_dir)
    sentinel = output_dir / EMIT_MARKER_FILENAME
    sentinel.write_text('{}\n', encoding='utf-8')

    pruned = prune_removed_bundles(output_dir, {'alpha'})

    assert pruned == [orphan]
    assert not orphan.exists()
    assert (output_dir / 'alpha').is_dir()
    assert (output_dir / '.claude-plugin').is_dir()
    assert sentinel.is_file()


def test_an_unscoped_emit_prunes_a_bundle_removed_from_source(tmp_path: Path):
    """End to end: the orphan is gone and the verdict counts only source bundles.

    The count matters as much as the removal: a stamp that grew with the
    orphan would be reporting the output tree's size as though it were the
    source's, which is the same overstatement one level up.
    """
    marketplace = _synthetic_marketplace(tmp_path / 'src', ['alpha', 'beta'])
    output_dir = tmp_path / 'out'
    orphan = _plant_orphan(output_dir)

    ClaudeTarget().generate(marketplace, output_dir)

    assert not orphan.exists()
    source_bundles = list(iter_bundle_dirs(marketplace, None))
    assert (output_dir / 'alpha').is_dir() and (output_dir / 'beta').is_dir()
    result = run_equality_check(output_dir, source_bundles)
    assert result.passed is True
    assert f'{len(source_bundles)} bundles' in result.summary


def test_a_scoped_emit_prunes_nothing(tmp_path: Path):
    """The gate's other direction — a subset run must not delete a sibling.

    A ``--bundles`` subset cannot tell "removed from source" from "not part of
    this run", so pruning on a scoped emit would delete a live bundle's output
    on every partial build. Both an unrelated leftover and a real sibling
    bundle's directory must survive.
    """
    marketplace = _synthetic_marketplace(tmp_path / 'src', ['alpha', 'beta'])
    output_dir = tmp_path / 'out'
    orphan = _plant_orphan(output_dir)
    sibling = output_dir / 'beta' / 'agents' / 'beta-agent.md'
    sibling.parent.mkdir(parents=True, exist_ok=True)
    sibling.write_text('---\nname: beta-agent\n---\nemitted earlier', encoding='utf-8')

    ClaudeTarget().generate(marketplace, output_dir, ['alpha'])

    assert orphan.is_dir(), 'a scoped emit must not prune — it cannot attribute the leftover'
    assert sibling.is_file(), 'a scoped emit must leave a non-emitted bundle untouched'
    assert (output_dir / 'alpha' / 'agents' / 'alpha-agent.md').is_file()


def test_emit_marker_fingerprint_non_empty_for_real_worktree(tmp_path: Path):
    """Regression test for the sentinel writer's repo_root resolution.

    Before the fix, ``ClaudeTarget.generate`` resolved ``repo_root`` as
    ``marketplace_dir.parent`` (i.e. ``marketplace/``), so the worktree
    fingerprint helper ran ``git ls-files marketplace/bundles`` from
    inside ``marketplace/`` — a prefix that does not exist relative to
    that cwd. ``ls-files`` matched zero paths and the fingerprint became
    the SHA-1 of empty input
    (``da39a3ee5e6b4b0d3255bfef95601890afd80709``), silently breaking
    the sync-plugin-cache staleness guard. The fix is
    ``repo_root = marketplace_dir.parent.parent`` so the prefix resolves
    against the project root that contains ``marketplace/``.

    The test invokes the target against the *real* worktree so the
    fingerprint is computed against the actual repository contents.
    Skipped when ``git`` is unavailable (the fingerprint helper raises
    ``FingerprintError`` in that case and the sentinel writer falls
    through to ``source_tree_fingerprint: null``, which would mask the
    regression signal).
    """
    if shutil.which('git') is None:
        pytest.skip('git binary not on PATH — fingerprint cannot be computed')
    if not _REAL_MARKETPLACE_BUNDLES.is_dir():
        pytest.skip(f'real marketplace/bundles not found at {_REAL_MARKETPLACE_BUNDLES}')

    output_dir = tmp_path / 'out'
    ClaudeTarget().generate(_REAL_MARKETPLACE_BUNDLES, output_dir)

    marker_path = output_dir / EMIT_MARKER_FILENAME
    assert marker_path.is_file(), 'sentinel marker was not written'

    payload = json.loads(marker_path.read_text(encoding='utf-8'))
    fingerprint = payload.get('source_tree_fingerprint')
    assert fingerprint is not None, (
        'source_tree_fingerprint is None — the sentinel writer fell through '
        'the FingerprintError branch. This indicates ``git`` is unavailable '
        'OR ``marketplace_dir`` is outside a git work tree. The regression '
        'test cannot exercise the empty-input signal when the fingerprint is '
        'null.'
    )
    assert fingerprint != _EMPTY_INPUT_SHA1, (
        f'source_tree_fingerprint == SHA-1 of empty input ({_EMPTY_INPUT_SHA1}). '
        'The sentinel writer computed the fingerprint against the wrong '
        'repo_root — ``git ls-files marketplace/bundles`` found zero tracked '
        'files and SHA-1-ed the empty stream. Check that '
        'marketplace/targets/claude/target.py line 153 reads '
        '``repo_root = marketplace_dir.parent.parent`` (NOT '
        '``marketplace_dir.parent``).'
    )
