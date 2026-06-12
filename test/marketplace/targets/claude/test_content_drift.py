"""Tests for the Claude target live content-drift check engine.

The engine (``content_drift.run_content_drift_check``) is **regen-first**:
it regenerates a fresh Claude target tree from the current
``marketplace/bundles/`` sources into a throwaway temp dir via
``ClaudeTarget().generate`` in emit mode, then diffs every regenerated
``*.md`` file byte-for-byte against the same-relative-path file under the
on-disk ``target/claude/`` tree. It surfaces per-file markdown drift that
the manifest-only equality gate cannot see — a skill body edited in
``marketplace/bundles/`` but not re-emitted, or an emitted ``.md`` mutated
directly under ``target/claude/``.

These tests build a synthetic single-bundle marketplace, run a real emit
to produce a clean on-disk target, and then exercise the three drift
categories (``drifted_files`` / ``missing_in_target`` / ``orphan_in_target``)
plus the regen-first source-mutation invariant. The synthetic marketplace
is NOT inside a git work tree, so the emit's sentinel fingerprint degrades
to ``null`` — that is irrelevant to the ``.md`` content-drift check, which
never inspects the sentinel.
"""

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.content_drift import (
    ContentDriftResult,
    run_content_drift_check,
)
from marketplace.targets.claude.target import ClaudeTarget


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _build_source_marketplace(tmp_path: Path) -> Path:
    """Build a synthetic single-bundle marketplace and return its bundles dir.

    Layout mirrors the real source tree:

    * ``tmp_path/bundles/demo/.claude-plugin/plugin.json`` (so
      ``iter_bundle_dirs`` recognizes ``demo`` as a bundle)
    * ``tmp_path/bundles/demo/`` content ``.md`` files (a skill body and a
      standards doc) — the in-scope content the drift engine compares
    * ``tmp_path/.claude-plugin/marketplace.json`` (the source marketplace
      manifest the emitter rewrites; ``plugins[].source`` MUST start with
      ``./bundles/`` per ``marketplace_json_gen``)

    Returns the ``bundles`` directory — the ``marketplace_dir`` argument the
    emitter and the drift engine both take.
    """
    bundles = tmp_path / 'bundles'
    bundle = bundles / 'demo'

    plugin_doc = {
        'name': 'demo',
        'version': '0.0.1',
        'description': 'Demo bundle',
        'agents': [],
        'commands': [],
        'skills': ['./skills/demo-skill'],
    }
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps(plugin_doc, indent=2) + '\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: demo\n---\n# demo skill body\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'standards' / 'rule.md',
        '# rule\n\nsome standard content\n',
    )
    _write(bundle / 'README.md', '# demo bundle\n')

    source_manifest = {
        'name': 'demo-marketplace',
        'plugins': [
            {'name': 'demo', 'description': 'demo', 'source': './bundles/demo'},
        ],
    }
    _write(
        tmp_path / '.claude-plugin' / 'marketplace.json',
        json.dumps(source_manifest, indent=2) + '\n',
    )
    return bundles


@pytest.fixture()
def synced_target(tmp_path: Path) -> tuple[Path, Path]:
    """Synthetic marketplace + a freshly emitted, in-sync target tree.

    Returns ``(target_dir, marketplace_dir)`` — the exact pair
    ``run_content_drift_check`` consumes. After this fixture runs, the
    on-disk ``target_dir`` is a faithful emit of ``marketplace_dir``, so a
    drift check over the pair passes.
    """
    marketplace_dir = _build_source_marketplace(tmp_path)
    target_dir = tmp_path / 'target' / 'claude'
    ClaudeTarget().generate(marketplace_dir, target_dir, None)
    return target_dir, marketplace_dir


def test_clean_emit_passes(synced_target: tuple[Path, Path]):
    """A freshly emitted target is in sync — the drift check passes and the
    summary reports the markdown file count.
    """
    target_dir, marketplace_dir = synced_target

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert isinstance(result, ContentDriftResult)
    assert result.passed is True
    assert result.drifted_files == []
    assert result.missing_in_target == []
    assert result.orphan_in_target == []
    assert 'passed' in result.summary


def test_on_disk_md_mutation_surfaces_drift_and_names_file(synced_target: tuple[Path, Path]):
    """An emitted ``.md`` mutated directly under target/claude/ surfaces as a
    ``drifted_files`` entry whose path names the drifted file, and the
    summary directs the caller to re-run the emit step.
    """
    target_dir, marketplace_dir = synced_target
    drifted = target_dir / 'demo' / 'skills' / 'demo-skill' / 'SKILL.md'
    drifted.write_text(
        '---\nname: demo-skill\ndescription: demo\n---\n# MUTATED body\n',
        encoding='utf-8',
    )

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert result.passed is False
    rel = 'demo/skills/demo-skill/SKILL.md'
    assert rel in result.drifted_files
    assert result.missing_in_target == []
    assert result.orphan_in_target == []
    assert rel in result.summary
    assert 'generate.py --target claude' in result.summary


def test_source_md_edit_without_reemit_surfaces_drift(synced_target: tuple[Path, Path]):
    """Regen-first invariant: a source ``.md`` edited under marketplace/bundles/
    but NEVER re-emitted is caught exactly as an on-disk mutation is. The
    engine regenerates a fresh tree from the edited source and finds the
    on-disk target lagging behind.
    """
    target_dir, marketplace_dir = synced_target
    source_md = marketplace_dir / 'demo' / 'skills' / 'demo-skill' / 'standards' / 'rule.md'
    # Edit the canonical source — do NOT re-run the emit.
    source_md.write_text('# rule\n\nEDITED standard content\n', encoding='utf-8')

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert result.passed is False
    rel = 'demo/skills/demo-skill/standards/rule.md'
    assert rel in result.drifted_files
    assert rel in result.summary


def test_missing_in_target_surfaces_when_emitted_md_deleted(synced_target: tuple[Path, Path]):
    """A regenerated ``.md`` that is absent under target/claude/ surfaces as
    ``missing_in_target`` (the on-disk tree is missing emitted content).
    """
    target_dir, marketplace_dir = synced_target
    deleted = target_dir / 'demo' / 'skills' / 'demo-skill' / 'standards' / 'rule.md'
    deleted.unlink()

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert result.passed is False
    rel = 'demo/skills/demo-skill/standards/rule.md'
    assert rel in result.missing_in_target
    assert result.drifted_files == []
    assert rel in result.summary


def test_orphan_in_target_surfaces_when_stale_md_present(synced_target: tuple[Path, Path]):
    """An ``.md`` present under target/claude/ that a fresh emit does NOT
    produce surfaces as ``orphan_in_target`` (a stale leftover whose source
    no longer exists).
    """
    target_dir, marketplace_dir = synced_target
    orphan = target_dir / 'demo' / 'skills' / 'demo-skill' / 'standards' / 'ghost.md'
    orphan.write_text('# ghost standard\n', encoding='utf-8')

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert result.passed is False
    rel = 'demo/skills/demo-skill/standards/ghost.md'
    assert rel in result.orphan_in_target
    assert result.drifted_files == []
    assert result.missing_in_target == []
    assert rel in result.summary


def test_missing_target_dir_returns_diagnostic_not_crash(tmp_path: Path):
    """When target/claude/ does not exist, the check fails with a
    "run emit mode first" diagnostic rather than raising.
    """
    marketplace_dir = _build_source_marketplace(tmp_path)
    nowhere = tmp_path / 'target' / 'does-not-exist'

    result = run_content_drift_check(nowhere, marketplace_dir)

    assert result.passed is False
    assert result.drifted_files == []
    assert 'not generated' in result.summary
    assert 'generate.py --target claude' in result.summary


def test_manifest_and_marker_files_are_out_of_scope(synced_target: tuple[Path, Path]):
    """The check ignores non-content files: mutating the emitted plugin.json
    (a ``.claude-plugin/`` manifest, owned by the equality engine) and the
    ``.emit-marker.json`` sentinel does NOT register as ``.md`` content drift.
    """
    target_dir, marketplace_dir = synced_target
    plugin_json = target_dir / 'demo' / '.claude-plugin' / 'plugin.json'
    plugin_json.write_text('{"name": "mutated"}\n', encoding='utf-8')
    marker = target_dir / '.emit-marker.json'
    marker.write_text('{"mutated": true}\n', encoding='utf-8')

    result = run_content_drift_check(target_dir, marketplace_dir)

    assert result.passed is True
    assert result.drifted_files == []
    assert result.missing_in_target == []
    assert result.orphan_in_target == []
