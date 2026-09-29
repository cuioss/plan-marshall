# SPDX-License-Identifier: FSL-1.1-ALv2
"""Discovery coverage over a FLAT deployed root, in the shape that actually ships.

The coverage guard compares two independent readings of one tree: the
inventory scan (``scan-marketplace-inventory``) and the generator's own
enumeration (``enumerate_script_notations``). On a flat OpenCode/Antigravity
deployment both used to read NOTHING, so the guard compared two empty sets and
passed at 0/0 — vacuously green on exactly the deployments it exists to serve.

Three things had to be true for the guard to mean something there, and each has
a case below:

* **The base is the one the runtimes hand over.** ``layout bundle-cache-root``
  returns the skill root ITSELF (``~/.config/opencode/skills``), not the
  directory containing it, so every fixture here passes that directory as the
  base. The earlier flat tests passed its parent — a shape no caller produces.
* **Both sides derive the same notation.** ``{bundle}-{skill}`` cannot be split,
  so the notation comes from the identity each emitted ``SKILL.md`` records, read
  through one shared walk. The agreement test runs BOTH sides over one tree and
  asserts equal notation sets, on both layouts.
* **An unreadable flat root fails closed.** A flat root whose skills carry no
  identity yields no notation on either side; that is reported as a coverage
  failure with the unattributed count, never as a measured empty tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import deployed_layout
import pytest

from conftest import load_script_module

BUNDLE = 'plan-marshall'

_gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_flat_root_coverage')


def _scan_module():
    return load_script_module('pm-plugin-development', 'tools-marketplace-inventory', 'scan-marketplace-inventory.py')


def _identity_skill_md(bundle: str, skill: str) -> str:
    return (
        '---\n'
        f'name: {bundle}-{skill}\n'
        'description: a skill\n'
        'metadata:\n'
        f'  bundle: {bundle}\n'
        f'  skill: {skill}\n'
        '---\n# body\n'
    )


def _flat_skill(skills_root: Path, bundle: str, skill: str, scripts: dict[str, str], *, identity: bool = True) -> Path:
    """Create one flat ``{bundle}-{skill}`` directory with the given script files."""
    skill_dir = skills_root / deployed_layout.flat_skill_dir_name(bundle, skill)
    skill_dir.mkdir(parents=True)
    body = _identity_skill_md(bundle, skill) if identity else '---\nname: x\ndescription: d\n---\n'
    (skill_dir / 'SKILL.md').write_text(body, encoding='utf-8')
    for relative, content in scripts.items():
        target = skill_dir / 'scripts' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    return skill_dir


def _deployed_flat_root(tmp_path: Path) -> Path:
    """Build a flat deployment and return the base the runtimes hand over: ``skills/`` itself."""
    skills_root = tmp_path / 'opencode' / 'skills'
    _flat_skill(skills_root, BUNDLE, 'manage-status', {'manage-status.py': '#', '_helper.py': '#'})
    _flat_skill(skills_root, BUNDLE, 'script-shared', {'build/build_parse.py': '#', 'run.sh': '#'})
    _flat_skill(skills_root, 'pm-plugin-development', 'plugin-script-architecture', {'check.py': '#'})
    return skills_root


def _nested_root(tmp_path: Path) -> Path:
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundle = bundles / BUNDLE
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{"name": "plan-marshall"}', encoding='utf-8')
    scripts = bundle / 'skills' / 'manage-status' / 'scripts'
    (scripts / 'sub').mkdir(parents=True)
    (bundle / 'skills' / 'manage-status' / 'SKILL.md').write_text('---\nname: manage-status\n---\n', encoding='utf-8')
    (scripts / 'manage-status.py').write_text('#', encoding='utf-8')
    (scripts / 'sub' / 'nested.py').write_text('#', encoding='utf-8')
    (scripts / '_private.py').write_text('#', encoding='utf-8')
    return bundles


def _scan_json(base: Path, monkeypatch, capsys, *extra: str) -> dict:
    """Run the REAL inventory scan in-process against ``base`` and return its JSON payload."""
    import sys

    module = _scan_module()
    capsys.readouterr()
    monkeypatch.setattr(
        sys,
        'argv',
        ['scan-marketplace-inventory.py', '--base-path', str(base), '--direct-result', '--format', 'json', *extra],
    )
    with pytest.raises(SystemExit):
        module.main()
    payload: dict = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'success', payload
    return payload


def _scanned_notations(base: Path, monkeypatch, capsys) -> dict[str, str]:
    """Run the REAL inventory scan against ``base`` and return notation -> path."""
    payload = _scan_json(base, monkeypatch, capsys, '--resource-types', 'scripts')
    return {
        script['notation']: script['path_formats']['absolute']
        for bundle in payload['bundles'].values()
        for script in bundle.get('scripts', [])
    }


class TestTheShippedBaseShape:
    def test_the_skill_root_itself_is_a_flat_root(self, tmp_path):
        """The base the runtimes return (``.../skills``) is read as a flat root."""
        base = _deployed_flat_root(tmp_path)

        assert deployed_layout.skill_roots(base) == [base]
        assert len(deployed_layout.flat_skill_dirs(base)) == 3

    def test_the_containing_directory_still_resolves(self, tmp_path):
        """The containing directory keeps working, so neither form regresses."""
        base = _deployed_flat_root(tmp_path)

        assert deployed_layout.skill_roots(base.parent) == [base]

    def test_a_bundle_skills_dir_is_not_a_flat_root(self, tmp_path):
        """A nested bundle's own ``skills/`` has kebab-case children that are NOT flat names."""
        bundles = _nested_root(tmp_path)

        assert deployed_layout.skill_roots(bundles / BUNDLE / 'skills') == []

    def test_resolve_bundle_path_reaches_a_flat_script_from_the_shipped_base(self, tmp_path):
        """The generator's path resolver finds a flat skill from the base it is really given."""
        from marketplace_bundles import resolve_bundle_path

        base = _deployed_flat_root(tmp_path)

        resolved = resolve_bundle_path(base, BUNDLE, 'skills/manage-status/scripts/manage-status.py')

        assert resolved == base / f'{BUNDLE}-manage-status' / 'scripts' / 'manage-status.py'
        assert resolved.is_file()


class TestBothSidesDeriveOneNotationSet:
    @pytest.mark.parametrize('layout', ['flat', 'nested'])
    def test_scan_and_enumeration_agree(self, layout, tmp_path, monkeypatch, capsys):
        """The inventory scan and the coverage enumeration name the same scripts.

        Run over ONE tree per layout. A divergence in how either side derives a
        notation shows up here as unequal sets, before it can show up as a
        spurious shortfall or a vacuous pass in a real generation.
        """
        base = _deployed_flat_root(tmp_path) if layout == 'flat' else _nested_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        scanned = _scanned_notations(base, monkeypatch, capsys)
        enumerated, _excluded, _counts = _gen.enumerate_script_notations(base)

        assert enumerated, f'the {layout} fixture must enumerate something, or equality is vacuous'
        assert set(scanned) == enumerated

    def test_flat_notations_come_from_the_recorded_identity(self, tmp_path):
        """A kebab-case bundle AND skill still yield the right notation — no split involved."""
        base = _deployed_flat_root(tmp_path)

        enumerated, _excluded, counts = _gen.enumerate_script_notations(base)

        assert enumerated == {
            'plan-marshall:manage-status:manage-status',
            'plan-marshall:script-shared:build_parse',
            'plan-marshall:script-shared:run',
            'pm-plugin-development:plugin-script-architecture:check',
        }
        assert counts == {'private_module': 1, 'unattributed_flat_skill': 0}

    def test_a_complete_scan_establishes_coverage_on_a_flat_root(self, tmp_path, monkeypatch, capsys):
        base = _deployed_flat_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        coverage = _gen.assess_discovery_coverage(base, _scanned_notations(base, monkeypatch, capsys))

        assert coverage['coverage_ok'] is True
        assert coverage['scripts_enumerated'] == coverage['scripts_discovered'] == 4


class TestScannerFlatEntries:
    def test_a_bundle_in_both_shapes_is_one_merged_entry(self, tmp_path, monkeypatch, capsys):
        """JSON keys bundles by name, so a nested and a flat entry must merge, not replace."""
        base = _nested_root(tmp_path)
        _flat_skill(base / 'skills', BUNDLE, 'flat-only', {'flat_only.py': '#'})
        monkeypatch.chdir(tmp_path)

        scanned = _scanned_notations(base, monkeypatch, capsys)

        assert 'plan-marshall:manage-status:manage-status' in scanned
        assert 'plan-marshall:flat-only:flat_only' in scanned

    def test_flat_skills_honour_the_content_filter(self, tmp_path, monkeypatch, capsys):
        """A content filter applies to flat skills exactly as to nested ones."""
        base = _deployed_flat_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        payload = _scan_json(
            base, monkeypatch, capsys, '--resource-types', 'skills', '--full', '--content-pattern', 'no-such-token'
        )

        assert all(not bundle.get('skills') for bundle in payload['bundles'].values())
        assert payload['statistics']['total_skills'] == 0

    def test_a_matching_content_filter_keeps_the_flat_skills(self, tmp_path, monkeypatch, capsys):
        """Positive control: a flat row without a path would be dropped by ANY filter, matching or not."""
        base = _deployed_flat_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        payload = _scan_json(
            base, monkeypatch, capsys, '--resource-types', 'skills', '--full', '--content-pattern', 'metadata:'
        )

        assert payload['statistics']['total_skills'] == 3

    def test_a_skill_in_both_shapes_is_listed_once(self, tmp_path, monkeypatch, capsys):
        """Merging a nested and a flat entry must not list the same skill twice."""
        base = _nested_root(tmp_path)
        _flat_skill(base / 'skills', BUNDLE, 'manage-status', {'manage-status.py': '#'})
        monkeypatch.chdir(tmp_path)

        payload = _scan_json(base, monkeypatch, capsys, '--resource-types', 'skills,scripts')
        bundle = payload['bundles'][BUNDLE]

        assert [skill['name'] for skill in bundle['skills']].count('manage-status') == 1
        assert [script['notation'] for script in bundle['scripts']].count(
            'plan-marshall:manage-status:manage-status'
        ) == 1


class TestAnUnreadableFlatRootFailsClosed:
    def test_an_unattributed_skill_is_counted_not_guessed(self, tmp_path):
        base = _deployed_flat_root(tmp_path)
        _flat_skill(base, 'foreign', 'tool', {'tool.py': '#'}, identity=False)

        enumerated, _excluded, counts = _gen.enumerate_script_notations(base)

        assert counts['unattributed_flat_skill'] == 1
        assert not any(notation.startswith('foreign') for notation in enumerated)

    def test_a_flat_root_with_nothing_attributable_is_not_a_measured_zero(self, tmp_path):
        """The 0/0 this guard used to pass: a flat root it could not read at all."""
        base = tmp_path / 'opencode' / 'skills'
        _flat_skill(base, BUNDLE, 'manage-status', {'manage-status.py': '#'}, identity=False)

        coverage = _gen.assess_discovery_coverage(base, {})

        assert coverage['coverage_ok'] is False
        assert coverage['scripts_enumerated'] == 0
        assert coverage['exclusions']['unattributed_flat_skill'] == 1

    def test_a_scan_short_of_a_flat_root_names_the_shortfall(self, tmp_path):
        base = _deployed_flat_root(tmp_path)

        coverage = _gen.assess_discovery_coverage(base, {'plan-marshall:manage-status:manage-status': '/x'})

        assert coverage['coverage_ok'] is False
        assert 'pm-plugin-development:plugin-script-architecture:check' in coverage['missing_notations']


class TestFlatIdentityReader:
    def test_identity_that_does_not_rejoin_to_the_dir_name_is_refused(self, tmp_path):
        """A copied or renamed directory cannot claim a notation it does not carry."""
        skill_dir = tmp_path / 'skills' / 'plan-marshall-renamed'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(_identity_skill_md(BUNDLE, 'manage-status'), encoding='utf-8')

        assert deployed_layout.read_flat_skill_identity(skill_dir) is None

    def test_identity_is_read_from_the_metadata_map_only(self, tmp_path):
        """Top-level ``bundle:`` / ``skill:`` keys are not the recorded identity."""
        skill_dir = tmp_path / 'skills' / 'a-b'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('---\nname: a-b\nbundle: a\nskill: b\n---\n', encoding='utf-8')

        assert deployed_layout.read_flat_skill_identity(skill_dir) is None

    def test_a_recorded_identity_reads_back(self, tmp_path):
        skill_dir = tmp_path / 'skills' / 'pm-plugin-development-plugin-script-architecture'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            _identity_skill_md('pm-plugin-development', 'plugin-script-architecture'), encoding='utf-8'
        )

        assert deployed_layout.read_flat_skill_identity(skill_dir) == (
            'pm-plugin-development',
            'plugin-script-architecture',
        )


class TestSharedModuleLabel:
    def test_a_flat_shared_module_is_labelled_with_its_skill(self, tmp_path):
        """The executor's self-heal matches on the skill name, not the dash-joined dir."""
        scripts = tmp_path / 'skills' / f'{BUNDLE}-script-shared' / 'scripts'

        assert _gen.shared_module_skill_label(scripts) == 'script-shared'

    def test_a_nested_shared_module_keeps_its_parent_name(self, tmp_path):
        scripts = tmp_path / BUNDLE / 'skills' / 'tools-file-ops' / 'scripts'

        assert _gen.shared_module_skill_label(scripts) == 'tools-file-ops'
