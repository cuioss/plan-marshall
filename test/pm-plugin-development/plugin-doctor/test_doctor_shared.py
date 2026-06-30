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
#
# ``_doctor_shared`` re-exports the single canonical parser (imported from
# ``_dep_detection``), which returns the ``Frontmatter(present, raw, fields)``
# superset record. The raw-text consumers in this module unpack the leading
# ``(present, raw)`` — byte-identical to the pre-collapse ``(present, body)``
# pair — and discard ``fields``.
# =============================================================================


def test_extract_frontmatter_present():
    present, body, _fields = _shared.extract_frontmatter('---\nname: a\ndescription: d\n---\n\n# Body\n')

    assert present is True
    assert 'name: a' in body
    assert 'description: d' in body


def test_extract_frontmatter_absent_when_no_leading_marker():
    present, body, _fields = _shared.extract_frontmatter('# Body\n\nNo frontmatter.\n')

    assert present is False
    assert body == ''


def test_extract_frontmatter_absent_when_unterminated():
    present, _body, _fields = _shared.extract_frontmatter('---\nname: a\nno closing marker\n')

    assert present is False


def test_extract_frontmatter_fields_view_available():
    """The third element is the flat-parsed dict — the index/dict view."""
    _present, _body, fields = _shared.extract_frontmatter('---\nname: a\ndescription: d\n---\n\n# Body\n')

    assert fields == {'name': 'a', 'description': 'd'}


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


# =============================================================================
# Finding — the single uniform finding record
#
# ``Finding`` is the only finding-construction path across the migrated analyzer
# subsystem. Its ``to_dict()`` output is the exact issue-dict shape the
# downstream categorizer and the per-analyzer finding-shape tests consume. The
# tests below pin the serialization contract that makes the migration safe:
# ``_UNSET`` optional fields are OMITTED (so each rule keeps its historical key
# subset), an explicit ``line=None`` is EMITTED (component-level rules rely on
# it), ``extra`` merges verbatim at the TOP level, and ``details`` stays NESTED.
# =============================================================================


def test_finding_to_dict_minimal_always_carries_type_and_file():
    """A bare Finding serializes to exactly {type, file}; file defaults to ''."""
    result = _shared.Finding(type='some-rule').to_dict()

    assert result == {'type': 'some-rule', 'file': ''}


def test_finding_to_dict_omits_unset_optional_fields():
    """Optional fields left at the _UNSET sentinel are omitted from the dict."""
    result = _shared.Finding(type='missing-frontmatter', file='a.md').to_dict()

    assert result == {'type': 'missing-frontmatter', 'file': 'a.md'}
    for omitted in ('line', 'severity', 'fixable', 'rule_id', 'description', 'details'):
        assert omitted not in result


def test_finding_to_dict_includes_present_optional_fields():
    """Optional fields given a value are emitted verbatim."""
    result = _shared.Finding(
        type='r',
        file='f.py',
        line=12,
        severity='error',
        fixable=True,
        rule_id='r',
        description='boom',
        details={'k': 'v'},
    ).to_dict()

    assert result == {
        'type': 'r',
        'file': 'f.py',
        'line': 12,
        'severity': 'error',
        'fixable': True,
        'rule_id': 'r',
        'description': 'boom',
        'details': {'k': 'v'},
    }


def test_finding_to_dict_emits_explicit_line_none():
    """line=None is a PRESENT key with a None value — distinct from omission."""
    result = _shared.Finding(type='component-rule', file='f', line=None).to_dict()

    assert 'line' in result
    assert result['line'] is None


def test_finding_unset_sentinel_is_distinct_from_none():
    """_UNSET is a sentinel object, never None, so line=None can be emitted."""
    assert _shared._UNSET is not None
    assert _shared.Finding(type='x').line is _shared._UNSET


def test_finding_extra_is_merged_as_top_level_keys():
    """extra={} keys merge verbatim at the top level (the verb-chain rule shape)."""
    result = _shared.Finding(
        type='prose-verb-chain-consistency',
        file='f',
        rule_id='prose-verb-chain-consistency',
        extra={'script_notation': 'a:b:c', 'verb_chain': ['x', 'y']},
    ).to_dict()

    assert result['script_notation'] == 'a:b:c'
    assert result['verb_chain'] == ['x', 'y']


def test_finding_details_field_stays_nested_not_flattened():
    """details={} is a single nested key — distinct from extra's top-level merge."""
    result = _shared.Finding(
        type='refine-contract-violation',
        file='f',
        details={'tool': 'Edit', 'path': 'marketplace/x.md'},
    ).to_dict()

    assert result['details'] == {'tool': 'Edit', 'path': 'marketplace/x.md'}
    assert 'tool' not in result  # not flattened to the top level


def test_finding_extra_and_details_are_independent_channels():
    """extra (top-level merge) and details (nested key) coexist without collision."""
    result = _shared.Finding(type='r', file='f', details={'a': 1}, extra={'b': 2}).to_dict()

    assert result['details'] == {'a': 1}
    assert result['b'] == 2


def test_finding_to_dict_key_order_is_stable():
    """Serialization order: type, file, present common fields, then extra keys."""
    result = _shared.Finding(
        type='r',
        file='f',
        line=1,
        severity='error',
        fixable=False,
        rule_id='r',
        description='d',
        extra={'z_extra': 1},
    ).to_dict()

    assert list(result.keys()) == [
        'type',
        'file',
        'line',
        'severity',
        'fixable',
        'rule_id',
        'description',
        'z_extra',
    ]


def test_finding_to_dict_is_dict_equal_to_prior_handbuilt_dict():
    """For a typed migrated rule, to_dict() equals the historical hand-built dict.

    ``missing-frontmatter`` is the canonical byte-identical case: its pre-refactor
    hand-built dict carried exactly ``type``/``file``/``severity``/``fixable`` and
    no ``rule_id``/``line``/``description``. The _UNSET-omission rule reproduces
    that exact key subset.
    """
    prior_handbuilt = {
        'type': 'missing-frontmatter',
        'file': 'x.md',
        'severity': 'error',
        'fixable': True,
    }

    result = _shared.Finding(
        type='missing-frontmatter', file='x.md', severity='error', fixable=True
    ).to_dict()

    assert result == prior_handbuilt
