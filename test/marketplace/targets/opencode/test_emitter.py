# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode emitter (per-bundle emit + validation contract)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.opencode.emitter import (
    EXCLUDED_DIR_NAMES,
    VERBATIM_SKILL_SUBDIRS,
    _resolve_md_components,
    _resolve_skill_dirs,
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
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'opencode'


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


# =============================================================================
# Stale-output pruning (D2)
# =============================================================================
#
# The per-component emit only creates directories and overwrites in place, so a
# skill/agent/command removed from source used to leave its emitted output
# behind and the tree drifted past source. A full re-emit now prunes stale
# outputs.


def test_emit_bundles_prunes_removed_skill(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    """A skill removed from source leaves no emitted directory behind after a
    full re-emit.
    """
    out = tmp_path / 'out'
    emit_bundles(fixture_bundle, out, opencode_config_dir)
    assert (out / 'skill' / 'demo-demo-skill' / 'SKILL.md').is_file()

    # Remove the skill from source and drop it from the bundle manifest.
    shutil.rmtree(fixture_bundle / 'demo' / 'skills' / 'demo-skill')
    plugin_path = fixture_bundle / 'demo' / '.claude-plugin' / 'plugin.json'
    doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    doc['skills'] = []
    plugin_path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')

    emit_bundles(fixture_bundle, out, opencode_config_dir)

    assert not (out / 'skill' / 'demo-demo-skill').exists()
    # A surviving component is untouched by the prune.
    assert (out / 'agent' / 'demo-agent.md').is_file()


def test_emit_bundles_prunes_removed_agent(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    """An agent removed from source leaves no emitted file behind after a full
    re-emit.
    """
    out = tmp_path / 'out'
    emit_bundles(fixture_bundle, out, opencode_config_dir)
    assert (out / 'agent' / 'demo-agent.md').is_file()

    (fixture_bundle / 'demo' / 'agents' / 'demo-agent.md').unlink()
    plugin_path = fixture_bundle / 'demo' / '.claude-plugin' / 'plugin.json'
    doc = json.loads(plugin_path.read_text(encoding='utf-8'))
    doc['agents'] = []
    plugin_path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')

    emit_bundles(fixture_bundle, out, opencode_config_dir)

    assert not (out / 'agent' / 'demo-agent.md').exists()
    # The surviving skill is untouched by the prune.
    assert (out / 'skill' / 'demo-demo-skill' / 'SKILL.md').is_file()


def test_emit_bundles_prunes_removed_skill_subdir(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    """A verbatim sub-directory removed from a SURVIVING skill's source is pruned
    from the emitted skill — output does not drift past source at sub-directory
    granularity either (a whole-skill-dir sweep would miss this).
    """
    out = tmp_path / 'out'
    emit_bundles(fixture_bundle, out, opencode_config_dir)
    assert (out / 'skill' / 'demo-demo-skill' / 'standards' / 'rule.md').is_file()

    # Remove ONLY the standards/ subdir from the (surviving) skill's source.
    shutil.rmtree(fixture_bundle / 'demo' / 'skills' / 'demo-skill' / 'standards')

    emit_bundles(fixture_bundle, out, opencode_config_dir)

    assert not (out / 'skill' / 'demo-demo-skill' / 'standards').exists()
    # The skill itself and its other content survive.
    assert (out / 'skill' / 'demo-demo-skill' / 'SKILL.md').is_file()
    assert (out / 'skill' / 'demo-demo-skill' / 'templates' / 't.md').is_file()


# =============================================================================
# Component-reference traversal containment
# =============================================================================
#
# The two resolvers normalised references with a CHARACTER-SET strip, which
# removes every leading ``.`` and ``/`` rather than one exact ``./`` prefix. A
# reference of ``../decoy/x`` was flattened to ``decoy/x`` — resolving to a
# DIFFERENT file that exists inside the bundle, which the emitter would then
# copy into the generated output under the intended component's identity.
# ``iter_bundle_dirs`` already refused ``..`` in bundle names; these resolvers
# now apply the same containment.
#
# The decoy is seeded INSIDE the bundle at exactly the path the strip would
# flatten onto — otherwise the traversal reference would fail the existence test
# anyway and the assertion would hold against the pre-fix source for the wrong
# reason.


def _traversal_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / 'bundle'
    _write(bundle / 'skills' / 'real-skill' / 'SKILL.md', '---\nname: real\n---\nbody\n')
    _write(bundle / 'decoy' / 'other-skill' / 'SKILL.md', '---\nname: decoy\n---\nbody\n')
    _write(bundle / 'agents' / 'real-agent.md', '---\ndescription: real\n---\nbody\n')
    _write(bundle / 'decoy' / 'other-agent.md', '---\ndescription: decoy\n---\nbody\n')
    return bundle


def test_resolve_skill_dirs_refuses_traversal_reference(tmp_path: Path):
    """A ``..`` skill reference is skipped, not flattened onto the decoy."""
    bundle = _traversal_bundle(tmp_path)

    resolved = _resolve_skill_dirs(bundle, {'skills': ['./skills/real-skill', '../decoy/other-skill']})

    assert resolved == [bundle / 'skills' / 'real-skill']


def test_resolve_md_components_refuses_traversal_reference(tmp_path: Path):
    """A ``..`` agent reference is skipped, not flattened onto the decoy."""
    bundle = _traversal_bundle(tmp_path)

    resolved = _resolve_md_components(
        bundle, {'agents': ['./agents/real-agent.md', '../decoy/other-agent.md']}, 'agents', 'agents'
    )

    assert resolved == [bundle / 'agents' / 'real-agent.md']


def test_resolvers_preserve_a_leading_dot_directory_reference(tmp_path: Path):
    """Negative control: only an exact ``./`` is removed, not every leading dot."""
    bundle = tmp_path / 'bundle'
    _write(bundle / '.hidden' / 'dot-skill' / 'SKILL.md', '---\nname: dot\n---\nbody\n')
    _write(bundle / '.hidden' / 'dot-agent.md', '---\ndescription: dot\n---\nbody\n')

    skills = _resolve_skill_dirs(bundle, {'skills': ['.hidden/dot-skill']})
    agents = _resolve_md_components(bundle, {'agents': ['.hidden/dot-agent.md']}, 'agents', 'agents')

    assert skills == [bundle / '.hidden' / 'dot-skill']
    assert agents == [bundle / '.hidden' / 'dot-agent.md']
