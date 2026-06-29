# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Behavioral tests for the discovery / parsing utilities in ``_doctor_shared.py``.

Covers the bundle/component discovery walkers, component-type detection,
bundle-name extraction, frontmatter / JSON-input parsing, issue categorization,
and the report-path helpers. Each function is loaded in-process and driven with
synthetic marketplace trees under ``tmp_path`` so the discovery branches (filter,
dedup, fallback detection, error paths) are exercised on real on-disk inputs.
"""

import io
import json
import sys
from pathlib import Path

from conftest import load_script_module

_shared = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_doctor_shared.py', '_doctor_shared_behavior'
)


def _bundle(bundles_root: Path, name: str) -> Path:
    bundle = bundles_root / name
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'name': name}), encoding='utf-8'
    )
    return bundle


# =============================================================================
# extract_frontmatter
# =============================================================================


def test_extract_frontmatter_present():
    present, body = _shared.extract_frontmatter('---\nname: a\ndescription: d\n---\n\n# Body\n')

    assert present is True
    assert 'name: a' in body
    assert 'description: d' in body


def test_extract_frontmatter_absent_when_no_leading_marker():
    present, body = _shared.extract_frontmatter('# Body\n\nNo frontmatter.\n')

    assert present is False
    assert body == ''


def test_extract_frontmatter_absent_when_unterminated():
    present, body = _shared.extract_frontmatter('---\nname: a\nno closing marker\n')

    assert present is False


# =============================================================================
# read_json_input
# =============================================================================


def test_read_json_input_valid_file(tmp_path):
    f = tmp_path / 'in.json'
    f.write_text(json.dumps({'k': 'v'}), encoding='utf-8')

    data, error = _shared.read_json_input(str(f))

    assert error is None
    assert data == {'k': 'v'}


def test_read_json_input_empty_file_yields_empty_dict(tmp_path):
    f = tmp_path / 'empty.json'
    f.write_text('   \n', encoding='utf-8')

    data, error = _shared.read_json_input(str(f))

    assert error is None
    assert data == {}


def test_read_json_input_missing_file_reports_error(tmp_path):
    data, error = _shared.read_json_input(str(tmp_path / 'gone.json'))

    assert data is None
    assert error is not None
    assert 'not found' in error.lower()


def test_read_json_input_invalid_json_reports_error(tmp_path):
    f = tmp_path / 'bad.json'
    f.write_text('{not valid', encoding='utf-8')

    data, error = _shared.read_json_input(str(f))

    assert data is None
    assert 'Invalid JSON' in error


def test_read_json_input_from_stdin(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps({'from': 'stdin'})))

    data, error = _shared.read_json_input('-')

    assert error is None
    assert data == {'from': 'stdin'}


# =============================================================================
# categorize_all_issues
# =============================================================================


def test_categorize_all_issues_splits_safe_risky_unfixable():
    issues = [
        {'type': 'trailing-whitespace', 'fixable': True},  # safe
        {'type': 'agent-task-tool-prohibited', 'fixable': True},  # risky
        {'type': 'some-warning', 'fixable': False},  # unfixable
    ]

    result = _shared.categorize_all_issues(issues)

    assert [i['type'] for i in result['safe']] == ['trailing-whitespace']
    assert [i['type'] for i in result['risky']] == ['agent-task-tool-prohibited']
    assert [i['type'] for i in result['unfixable']] == ['some-warning']


# =============================================================================
# get_report_filename / ensure_report_dir
# =============================================================================


def test_get_report_filename_with_scope():
    assert _shared.get_report_filename('20260101-000000', 'plan-marshall') == (
        '20260101-000000-plan-marshall-report.json'
    )


def test_get_report_filename_without_scope():
    assert _shared.get_report_filename('20260101-000000') == '20260101-000000-report.json'


def test_get_report_filename_generates_default_timestamp():
    name = _shared.get_report_filename()

    assert name.endswith('-report.json')
    assert len(name) > len('-report.json')


def test_ensure_report_dir_creates_directory(tmp_path):
    target = tmp_path / 'nested' / 'report-dir'

    result = _shared.ensure_report_dir(target)

    assert result == target
    assert target.is_dir()


# =============================================================================
# find_bundles
# =============================================================================


def test_find_bundles_sorted_by_name(tmp_path):
    bundles_root = tmp_path / 'bundles'
    _bundle(bundles_root, 'zeta')
    _bundle(bundles_root, 'alpha')

    found = _shared.find_bundles(bundles_root)

    assert [b.name for b in found] == ['alpha', 'zeta']


def test_find_bundles_applies_filter(tmp_path):
    bundles_root = tmp_path / 'bundles'
    _bundle(bundles_root, 'keep')
    _bundle(bundles_root, 'drop')

    found = _shared.find_bundles(bundles_root, {'keep'})

    assert [b.name for b in found] == ['keep']


# =============================================================================
# discover_components
# =============================================================================


def test_discover_components_finds_each_type(tmp_path):
    bundle = _bundle(tmp_path / 'bundles', 'b')
    (bundle / 'agents').mkdir()
    (bundle / 'agents' / 'ag.md').write_text('---\nname: ag\n---\n\n# Ag\n', encoding='utf-8')
    (bundle / 'commands').mkdir()
    (bundle / 'commands' / 'cmd.md').write_text('---\nname: cmd\n---\n\n# Cmd\n', encoding='utf-8')
    skill = bundle / 'skills' / 'sk'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: sk\n---\n\n# Sk\n', encoding='utf-8')
    (skill / 'scripts').mkdir()
    (skill / 'scripts' / 'run.py').write_text('# script\n', encoding='utf-8')

    components = _shared.discover_components(bundle)

    assert len(components['agents']) == 1
    assert len(components['commands']) == 1
    assert len(components['skills']) == 1
    assert len(components['scripts']) == 1
    assert components['skills'][0]['name'] == 'sk'
    assert components['scripts'][0]['skill'] == 'sk'


# =============================================================================
# _detect_component_type / resolve_component_paths
# =============================================================================


def test_detect_component_type_skill_by_skill_md(tmp_path):
    skill = tmp_path / 'sk'
    skill.mkdir()
    (skill / 'SKILL.md').write_text('---\nname: sk\n---\n\n# Sk\n', encoding='utf-8')

    assert _shared._detect_component_type(skill) == 'skill'


def test_detect_component_type_agent_by_tools_frontmatter(tmp_path):
    d = tmp_path / 'agents'
    d.mkdir()
    (d / 'a.md').write_text('---\nname: a\ntools: Read, Skill\n---\n\n# A\n', encoding='utf-8')

    assert _shared._detect_component_type(d) == 'agent'


def test_detect_component_type_command_by_allowed_tools_frontmatter(tmp_path):
    d = tmp_path / 'commands'
    d.mkdir()
    (d / 'c.md').write_text('---\nname: c\nallowed-tools: Read\n---\n\n# C\n', encoding='utf-8')

    assert _shared._detect_component_type(d) == 'command'


def test_detect_component_type_fallback_by_parent_dir(tmp_path):
    skills_parent = tmp_path / 'skills'
    child = skills_parent / 'thing'
    child.mkdir(parents=True)

    assert _shared._detect_component_type(child) == 'skill'


def test_detect_component_type_unknown(tmp_path):
    d = tmp_path / 'whatever'
    d.mkdir()

    assert _shared._detect_component_type(d) == 'unknown'


def test_resolve_component_paths_detects_skill_and_warns_on_missing(tmp_path, capsys):
    skill = tmp_path / 'sk'
    skill.mkdir()
    (skill / 'SKILL.md').write_text('---\nname: sk\n---\n\n# Sk\n', encoding='utf-8')
    missing = str(tmp_path / 'absent')

    resolved = _shared.resolve_component_paths([str(skill), missing])

    assert len(resolved) == 1
    assert resolved[0][1] == 'skill'
    assert 'WARNING' in capsys.readouterr().err


# =============================================================================
# find_bundle_for_file
# =============================================================================


def test_find_bundle_for_file_returns_bundle(tmp_path):
    bundles_root = tmp_path / 'bundles'
    bundle = _bundle(bundles_root, 'b')
    target = bundle / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('x', encoding='utf-8')

    assert _shared.find_bundle_for_file(target, bundles_root) == bundle


def test_find_bundle_for_file_none_when_no_plugin_json(tmp_path):
    bundles_root = tmp_path / 'bundles'
    bundles_root.mkdir()
    loose = bundles_root / 'loose' / 'file.md'
    loose.parent.mkdir(parents=True)
    loose.write_text('x', encoding='utf-8')

    assert _shared.find_bundle_for_file(loose, bundles_root) is None


# =============================================================================
# extract_bundle_name
# =============================================================================


def test_extract_bundle_name_from_bundles_path():
    path = '/repo/marketplace/bundles/plan-marshall/skills/s/SKILL.md'

    assert _shared.extract_bundle_name(path) == 'plan-marshall'


def test_extract_bundle_name_unknown_without_bundles_segment():
    assert _shared.extract_bundle_name('/somewhere/else/file.md') == 'unknown'


# =============================================================================
# resolve_runtime_target / resolve_project_skill_trees
# =============================================================================


def test_resolve_runtime_target_returns_string():
    target = _shared.resolve_runtime_target()

    assert isinstance(target, str)
    assert target != ''


def test_resolve_project_skill_trees_returns_existing_dirs(tmp_path):
    marketplace_root = tmp_path / 'marketplace' / 'bundles'
    marketplace_root.mkdir(parents=True)
    (tmp_path / '.claude' / 'skills').mkdir(parents=True)

    trees = _shared.resolve_project_skill_trees(marketplace_root)

    assert isinstance(trees, list)
    assert all(p.is_dir() for p in trees), 'only on-disk directories are returned'
