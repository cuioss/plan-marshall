# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the OpenCode emitter (per-bundle emit + validation contract)."""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
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
    plugin_doc = (
        json.dumps(
            {
                'name': 'demo',
                'version': '0.0.1',
                'description': 'Demo bundle',
                'agents': ['./agents/demo-agent.md'],
                'commands': ['./commands/demo-cmd.md'],
                'skills': ['./skills/demo-skill'],
            },
            indent=2,
        )
        + '\n'
    )
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


def test_missing_description_in_skill_raises_unmapped_frontmatter(tmp_path: Path, opencode_config_dir: Path):
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


# =============================================================================
# Source-tree refusal, matched control (G3)
# =============================================================================
#
# This emitter is destructive in two places — ``_copy_verbatim``'s safe_rmtree
# and ``_prune_stale_outputs``'s unlink sweep — and ``safe_rmtree``'s
# containment check does NOT cover an output_dir that IS the source tree: every
# path inside the source is then inside output_dir, so the guard passes and the
# delete proceeds. The sibling Claude emitter has refused this overlap all
# along; that this one did not was an asymmetry. Both halves are pinned, because
# a refusal that also refused legitimate emits would be worse than the gap.


def test_emit_bundles_refuses_an_output_dir_inside_the_source_tree(fixture_bundle: Path, opencode_config_dir: Path):
    """Negative half: the overlap is refused and the source survives intact."""
    source_skill = fixture_bundle / 'demo' / 'skills' / 'demo-skill' / 'SKILL.md'
    source_bytes = source_skill.read_bytes()
    standards_file = fixture_bundle / 'demo' / 'skills' / 'demo-skill' / 'standards' / 'rule.md'

    with pytest.raises(ValueError, match='source tree'):
        emit_bundles(fixture_bundle, fixture_bundle, opencode_config_dir)

    assert source_skill.read_bytes() == source_bytes
    assert standards_file.is_file()


def test_emit_bundles_refuses_before_writing_or_unlinking_anything(fixture_bundle: Path, opencode_config_dir: Path):
    """The refusal precedes every side effect — no partial emit is left behind.

    Asserting only that it raises would not distinguish "refused up front" from
    "refused after wiping half the tree", and the second is the outcome that
    costs source. The emitter's own output roots are the observable: none may
    appear inside the source tree, and ``opencode.json`` — written last on the
    success path — must be absent.
    """
    before = {p.relative_to(fixture_bundle).as_posix() for p in fixture_bundle.rglob('*')}

    with pytest.raises(ValueError, match='source tree'):
        emit_bundles(fixture_bundle, fixture_bundle, opencode_config_dir)

    after = {p.relative_to(fixture_bundle).as_posix() for p in fixture_bundle.rglob('*')}
    assert after == before, f'the refused emit changed the source tree: {after ^ before}'
    assert not (fixture_bundle / 'opencode.json').exists()


def test_emit_bundles_still_emits_and_prunes_to_a_legitimate_output_dir(
    fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path
):
    """Positive half: a distinct output dir still emits, and still prunes.

    Without this direction the guard could refuse everything and every test
    above would still pass. The stale file also proves the prune sweep — the
    other destructive path the refusal protects — is still reached.
    """
    out = tmp_path / 'out'
    stale = out / 'agent' / 'removed-agent.md'
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('---\ndescription: gone from source\n---\nbody\n', encoding='utf-8')

    written = emit_bundles(fixture_bundle, out, opencode_config_dir)

    assert written
    assert (out / 'agent' / 'demo-agent.md').is_file()
    assert not stale.exists(), 'the stale-output prune must still run on a legitimate emit'


def test_emit_bundles_emits_install_script_and_readme(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    written = emit_bundles(fixture_bundle, out, opencode_config_dir)

    # 1. install.sh emission & permissions
    install_sh = out / 'install.sh'
    assert install_sh.is_file(), 'install.sh was not emitted'
    assert install_sh in written
    assert install_sh.stat().st_mode & stat.S_IXUSR, 'install.sh must be executable'

    # 2. Syntax validation
    subprocess.run(['bash', '-n', str(install_sh)], check=True)

    # 3. Help flag
    res = subprocess.run([str(install_sh), '--help'], check=True, capture_output=True, text=True)
    assert 'Plan Marshall - OpenCode Component Installer' in res.stdout

    # 4. Local install & uninstall execution
    test_dest = tmp_path / 'installed_opencode'
    subprocess.run([str(install_sh), '--target-dir', str(test_dest)], check=True)
    assert (test_dest / 'skills').is_dir()
    assert (test_dest / 'agents').is_dir()
    assert (test_dest / 'commands').is_dir()
    assert (test_dest / 'plan-marshall-README.adoc').is_file()
    assert (test_dest / 'plan-marshall-install.sh').is_file()
    assert (test_dest / 'plan-marshall-install.sh').stat().st_mode & stat.S_IXUSR

    # User-created component with plan-marshall prefix must NOT be removed (boundary test)
    custom_skill = test_dest / 'skills' / 'plan-marshalling-helper'
    custom_skill.mkdir(parents=True)
    (custom_skill / 'SKILL.md').write_text('custom', encoding='utf-8')

    # Uninstallation via local plan-marshall-install.sh
    subprocess.run([str(test_dest / 'plan-marshall-install.sh'), '--uninstall'], check=True)
    assert not any((test_dest / 'skills').glob('plan-marshall-*'))
    assert not (test_dest / 'plan-marshall-README.adoc').exists()
    assert not (test_dest / 'plan-marshall-install.sh').exists()
    assert (custom_skill / 'SKILL.md').is_file(), 'unrelated component must be preserved'

    # 5. README.adoc emission
    readme = out / 'README.adoc'
    assert readme.is_file(), 'README.adoc was not emitted'
    assert readme in written
    assert '= Installation (OpenCode)' in readme.read_text(encoding='utf-8')


def test_emit_bundles_raises_on_missing_required_template(
    fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    import marketplace.targets.opencode.emitter as oc_emitter

    monkeypatch.setattr(oc_emitter, '_INSTALL_SCRIPT_TEMPLATE', tmp_path / 'nonexistent.sh')
    with pytest.raises(FileNotFoundError, match='Required install.sh template not found'):
        emit_bundles(fixture_bundle, tmp_path / 'out', opencode_config_dir)


def _create_bundle(
    marketplace: Path,
    name: str,
    skills: list[str],
    agents: list[str] | None = None,
    commands: list[str] | None = None,
) -> None:
    bundle = marketplace / name
    agents = agents or []
    commands = commands or []
    plugin_doc = {
        'name': name,
        'version': '0.0.1',
        'description': f'{name} bundle',
        'agents': [f'./agents/{a}.md' for a in agents],
        'commands': [f'./commands/{c}.md' for c in commands],
        'skills': [f'./skills/{s}' for s in skills],
    }
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps(plugin_doc, indent=2) + '\n')
    for s in skills:
        _write(
            bundle / 'skills' / s / 'SKILL.md',
            f'---\nname: {s}\ndescription: {s} skill\n---\n# {s} body\n',
        )
    for a in agents:
        _write(
            bundle / 'agents' / f'{a}.md',
            f'---\nname: {a}\ndescription: {a} agent\nmodel: sonnet\ntools: Read, Write\n---\n{a} agent body\n',
        )
    for c in commands:
        _write(
            bundle / 'commands' / f'{c}.md',
            f'---\nname: {c}\ndescription: {c} command\n---\n{c} cmd body\n',
        )


@pytest.fixture()
def multi_bundle_repo(tmp_path: Path) -> Path:
    marketplace = tmp_path / 'multi_bundles'
    _create_bundle(marketplace, 'plan-marshall', ['core-skill'], ['core-agent'], ['core-cmd'])
    _create_bundle(marketplace, 'pm-dev-java', ['java-skill'])
    _create_bundle(marketplace, 'pm-dev-java-cui', ['java-cui-skill'])
    _create_bundle(marketplace, 'pm-dev-python', ['python-skill'])
    _create_bundle(marketplace, 'pm-documents', ['docs-skill'])
    _create_bundle(marketplace, 'pm-dev-frontend', ['fe-skill'])
    _create_bundle(marketplace, 'pm-dev-frontend-cui', ['fe-cui-skill'])
    return marketplace


def test_emit_bundles_emits_bundle_components_json(fixture_bundle: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    written = emit_bundles(fixture_bundle, out, opencode_config_dir)

    components_json = out / 'bundle-components.json'
    assert components_json.is_file()
    assert components_json in written

    data = json.loads(components_json.read_text(encoding='utf-8'))
    assert data['schema_version'] == 1
    assert data['target'] == 'opencode'
    assert 'bundles' in data
    assert 'demo' in data['bundles']
    demo_components = data['bundles']['demo']
    assert demo_components['skills'] == ['skill/demo-demo-skill']
    assert demo_components['agents'] == ['agent/demo-agent.md']
    assert demo_components['commands'] == ['command/demo-cmd.md']


def test_install_core_only(multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)
    _write(out / 'dist-manifest.json', json.dumps({'version': '1.0.0'}) + '\n')

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--core-only'], check=True)

    assert (dest / 'skills' / 'plan-marshall-core-skill').is_dir()
    assert (dest / 'agents' / 'core-agent.md').is_file()
    assert (dest / 'commands' / 'core-cmd.md').is_file()
    assert not (dest / 'skills' / 'pm-dev-java-java-skill').exists()
    assert not (dest / 'skills' / 'pm-dev-python-python-skill').exists()

    manifest = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema_version'] == 1
    assert manifest['target'] == 'opencode'
    assert manifest['installed_bundles'] == ['plan-marshall']
    assert manifest['core'] == 'plan-marshall'
    assert len(manifest['dist_manifest_sha']) == 64
    assert 'skills/plan-marshall-core-skill/SKILL.md' in manifest['managed_files']
    assert 'agents/core-agent.md' in manifest['managed_files']


def test_install_bundles_and_aliases(multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--bundles', 'pm-dev-java-cui'], check=True)

    # Core is mandatory
    assert (dest / 'skills' / 'plan-marshall-core-skill').is_dir()
    # Dependency closure pulls in base java
    assert (dest / 'skills' / 'pm-dev-java-cui-java-cui-skill').is_dir()
    assert (dest / 'skills' / 'pm-dev-java-java-skill').is_dir()
    assert not (dest / 'skills' / 'pm-dev-python-python-skill').exists()

    manifest = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert sorted(manifest['installed_bundles']) == ['plan-marshall', 'pm-dev-java', 'pm-dev-java-cui']

    # Test aliases
    dest_alias = tmp_path / 'installed_alias'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest_alias), '--bundles', 'python,docs'], check=True)
    manifest_alias = json.loads((dest_alias / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert sorted(manifest_alias['installed_bundles']) == ['plan-marshall', 'pm-dev-python', 'pm-documents']


def test_install_without_bundles(multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    subprocess.run(
        [str(out / 'install.sh'), '--target-dir', str(dest), '--without-bundles', 'java,frontend'], check=True
    )

    assert (dest / 'skills' / 'plan-marshall-core-skill').is_dir()
    assert (dest / 'skills' / 'pm-dev-python-python-skill').is_dir()
    assert (dest / 'skills' / 'pm-documents-docs-skill').is_dir()
    assert not (dest / 'skills' / 'pm-dev-java-java-skill').exists()
    assert not (dest / 'skills' / 'pm-dev-frontend-fe-skill').exists()

    # Rejection cases
    res = subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--bundles', 'unknown-bundle'])
    assert res.returncode == 2

    res = subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--without-bundles', 'plan-marshall'])
    assert res.returncode == 2

    res = subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--without-bundles', 'pm-dev-java'])
    assert res.returncode == 2


def test_install_update_lifecycle_and_rollback(multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'

    # Step 1: Initial install with python
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--bundles', 'python'], check=True)
    assert (dest / 'skills' / 'pm-dev-python-python-skill').is_dir()

    # Step 2: Update without flags reuses prior bundle selection
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--update'], check=True)
    manifest = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert sorted(manifest['installed_bundles']) == ['plan-marshall', 'pm-dev-python']

    # Step 3: Update with --without-bundles removes python
    subprocess.run(
        [str(out / 'install.sh'), '--target-dir', str(dest), '--update', '--without-bundles', 'python'], check=True
    )
    assert not (dest / 'skills' / 'pm-dev-python-python-skill').exists()
    manifest = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert manifest['installed_bundles'] == ['plan-marshall']

    # Step 4: Update with --bundles java installs java
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--update', '--bundles', 'java'], check=True)
    assert (dest / 'skills' / 'pm-dev-java-java-skill').is_dir()

    # Step 5: Rollback verification on failure
    skills_dir = dest / 'skills'
    skills_dir.chmod(0o555)
    try:
        res = subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--update', '--bundles', 'python'])
        assert res.returncode != 0
    finally:
        skills_dir.chmod(0o755)

    assert (dest / 'skills' / 'pm-dev-java-java-skill').is_dir()
    manifest_after = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert 'pm-dev-java' in manifest_after['installed_bundles']


def test_install_uninstall_selective_bundles(multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--bundles', 'java,python'], check=True)

    # Refuse uninstalling core
    res = subprocess.run([str(dest / 'plan-marshall-install.sh'), '--uninstall', '--bundles', 'plan-marshall'])
    assert res.returncode == 2

    # Refuse uninstalling base while dependent child is retained
    res = subprocess.run([str(dest / 'plan-marshall-install.sh'), '--uninstall', '--bundles', 'pm-dev-java'])
    assert res.returncode == 2

    # Selectively uninstall python
    subprocess.run([str(dest / 'plan-marshall-install.sh'), '--uninstall', '--bundles', 'python'], check=True)
    assert not (dest / 'skills' / 'pm-dev-python-python-skill').exists()
    assert (dest / 'skills' / 'pm-dev-java-java-skill').is_dir()
    assert (dest / 'skills' / 'plan-marshall-core-skill').is_dir()

    manifest = json.loads((dest / '.plan-marshall-manifest.json').read_text(encoding='utf-8'))
    assert 'pm-dev-python' not in manifest['installed_bundles']
    assert 'pm-dev-java' in manifest['installed_bundles']


def test_install_uninstall_full_with_manifest_preserves_user_files(
    multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path
):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--all'], check=True)

    # Add user custom files
    user_skill_1 = dest / 'skills' / 'my-custom-skill' / 'SKILL.md'
    user_skill_2 = dest / 'skills' / 'pm-dev-custom' / 'SKILL.md'
    user_agent = dest / 'agents' / 'my-user-agent.md'
    _write(user_skill_1, '# Custom 1\n')
    _write(user_skill_2, '# Custom 2\n')
    _write(user_agent, '# Custom Agent\n')

    # Full uninstall using manifest
    subprocess.run([str(dest / 'plan-marshall-install.sh'), '--uninstall'], check=True)

    # Managed components removed
    assert not (dest / 'skills' / 'plan-marshall-core-skill').exists()
    assert not (dest / 'skills' / 'pm-dev-java-java-skill').exists()
    assert not (dest / '.plan-marshall-manifest.json').exists()

    # User custom components preserved
    assert user_skill_1.is_file()
    assert user_skill_2.is_file()
    assert user_agent.is_file()


def test_install_uninstall_full_fallback_without_manifest_preserves_user_files(
    multi_bundle_repo: Path, tmp_path: Path, opencode_config_dir: Path
):
    out = tmp_path / 'out'
    emit_bundles(multi_bundle_repo, out, opencode_config_dir)

    dest = tmp_path / 'installed'
    subprocess.run([str(out / 'install.sh'), '--target-dir', str(dest), '--all'], check=True)

    # Remove manifest to test bundle-components.json fallback
    manifest_file = dest / '.plan-marshall-manifest.json'
    assert manifest_file.is_file()
    manifest_file.unlink()

    # Add user custom files
    user_skill_1 = dest / 'skills' / 'my-custom-skill' / 'SKILL.md'
    user_skill_2 = dest / 'skills' / 'pm-dev-custom' / 'SKILL.md'
    user_agent = dest / 'agents' / 'my-user-agent.md'
    _write(user_skill_1, '# Custom 1\n')
    _write(user_skill_2, '# Custom 2\n')
    _write(user_agent, '# Custom Agent\n')

    # Full uninstall via fallback
    subprocess.run([str(dest / 'plan-marshall-install.sh'), '--uninstall'], check=True)

    # Managed components removed
    assert not (dest / 'skills' / 'plan-marshall-core-skill').exists()
    assert not (dest / 'skills' / 'pm-dev-java-java-skill').exists()

    # User custom components preserved
    assert user_skill_1.is_file()
    assert user_skill_2.is_file()
    assert user_agent.is_file()
