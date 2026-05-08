"""Tests for the OpenCode emitter (per-bundle emit + validation contract)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.opencode.emitter import (
    EXCLUDED_DIR_NAMES,
    VERBATIM_SKILL_SUBDIRS,
    emit_bundles,
    iter_bundle_dirs,
)
from marketplace.targets.opencode.frontmatter import (
    UnmappedFrontmatterError,
    UnmappedToolError,
)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


@pytest.fixture()
def opencode_config_dir() -> Path:
    """Return the canonical OpenCode mapping/rules config directory."""
    return Path(__file__).resolve().parents[3].parent / 'marketplace' / 'targets' / 'opencode'


@pytest.fixture()
def fixture_bundle(tmp_path: Path) -> Path:
    """Build a single complete bundle that exercises every emit path."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'Demo bundle',
            'agents': ['./agents/demo-agent.md'],
            'commands': ['./commands/demo-cmd.md'],
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write(bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n',
    )
    _write(bundle / 'skills' / 'demo-skill' / 'standards' / 'rule.md', '# rule\n')
    _write(bundle / 'skills' / 'demo-skill' / 'templates' / 't.md', 'tpl\n')
    _write(bundle / 'skills' / 'demo-skill' / '__pycache__' / 'junk.pyc', b'\x00')
    _write(
        bundle / 'agents' / 'demo-agent.md',
        '---\ndescription: an agent\nmodel: sonnet\ntools: Read, Write\n---\nagent body\n',
    )
    _write(
        bundle / 'commands' / 'demo-cmd.md',
        '---\ndescription: a command\n---\ncmd body\n',
    )
    return marketplace


def test_iter_bundle_dirs_yields_only_bundles(fixture_bundle: Path):
    bundles = list(iter_bundle_dirs(fixture_bundle, None))
    assert [b.name for b in bundles] == ['demo']


def test_iter_bundle_dirs_filters_unknown(fixture_bundle: Path):
    bundles = list(iter_bundle_dirs(fixture_bundle, ['no-such-bundle']))
    assert bundles == []


def test_iter_bundle_dirs_rejects_path_traversal(fixture_bundle: Path):
    bundles = list(iter_bundle_dirs(fixture_bundle, ['../etc']))
    assert bundles == []


def test_emit_bundles_singular_layout(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    written = emit_bundles(fixture_bundle, out, opencode_config_dir)

    rels = {p.relative_to(out).as_posix() for p in written}
    assert 'skill/demo-demo-skill/SKILL.md' in rels
    assert 'skill/demo-demo-skill/standards/rule.md' in rels
    assert 'skill/demo-demo-skill/templates/t.md' in rels
    assert 'agent/demo-agent.md' in rels
    assert 'command/demo-cmd.md' in rels
    assert 'opencode.json' in rels


def test_emit_bundles_excludes_pycache(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(fixture_bundle, out, opencode_config_dir)
    pycache_present = any('__pycache__' in str(p) for p in out.rglob('*'))
    assert not pycache_present
    assert '__pycache__' in EXCLUDED_DIR_NAMES


def test_emit_bundles_passes_body_transformer(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    seen: list[tuple[str, str]] = []

    def transformer(body: str, bundle: str, kind: str) -> str:
        seen.append((bundle, kind))
        return f'[{kind}]{body}'

    emit_bundles(fixture_bundle, out, opencode_config_dir, body_transformer=transformer)

    # Every emit kind invoked the transformer exactly once
    kinds = sorted({kind for _, kind in seen})
    assert kinds == ['agent', 'command', 'skill']

    skill_md = (out / 'skill' / 'demo-demo-skill' / 'SKILL.md').read_text(encoding='utf-8')
    assert '[skill]' in skill_md


def test_missing_description_in_skill_raises_unmapped_frontmatter(
    tmp_path: Path, opencode_config_dir: Path
):
    """When SKILL.md omits the required ``description`` field, emit raises (CLI exits 2)."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'skills': ['./skills/demo-skill']}) + '\n',
    )
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\n---\n# body\n',
    )
    out = tmp_path / 'out'
    with pytest.raises(UnmappedFrontmatterError):
        emit_bundles(marketplace, out, opencode_config_dir)


def test_unknown_agent_tool_raises_unmapped_tool(tmp_path: Path, opencode_config_dir: Path):
    """When an agent uses an unmapped tool, emit raises so the CLI exits 2."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    _write(
        bundle / '.claude-plugin' / 'plugin.json',
        json.dumps({'name': 'demo', 'agents': ['./agents/a.md']}) + '\n',
    )
    _write(
        bundle / 'agents' / 'a.md',
        '---\ndescription: x\ntools: NotARealTool\n---\nbody\n',
    )
    out = tmp_path / 'out'
    with pytest.raises(UnmappedToolError):
        emit_bundles(marketplace, out, opencode_config_dir)


def test_verbatim_skill_subdirs_constant_exposed():
    """The constant must enumerate the four canonical skill subdirs."""
    assert set(VERBATIM_SKILL_SUBDIRS) == {'standards', 'references', 'templates', 'scripts'}
