# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""In-process unit tests for the pure helper functions in ``doctor-marketplace.py``.

These functions (CSV/rule parsers, marketplace-root resolver, component
collectors, scope/suppression filters, the ``--paths`` enumerator, and the
validator-registry loader) are exercised only via subprocess by the sibling
``test_doctor_marketplace.py`` suite, so coverage never observed them. Here each
is loaded in-process via ``load_script_module`` and driven with real inputs so
its branches are both counted and behaviorally asserted.
"""

import json
import types
from pathlib import Path

from conftest import load_script_module

_doctor = load_script_module(
    'pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py', 'doctor_marketplace_under_test'
)


def _ns(**overrides):
    """Build an argparse-shaped namespace with permissive defaults."""
    defaults = {
        'marketplace_root': None,
        'bundles': None,
        'type': None,
        'name': None,
        'paths': None,
        'rules': None,
        'enable_argument_naming': False,
        'enable_verb_chain': False,
        'dry_run': False,
        'output': None,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_bundle(bundles_root: Path, name: str) -> Path:
    """Materialize a minimal bundle (plugin.json + one agent + one skill)."""
    bundle = bundles_root / name
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'name': name, 'version': '1.0.0'}), encoding='utf-8'
    )
    agents = bundle / 'agents'
    agents.mkdir()
    (agents / 'an-agent.md').write_text(
        '---\nname: an-agent\ndescription: d\ntools: Read, Skill\n---\n\n# An Agent\n', encoding='utf-8'
    )
    skill = bundle / 'skills' / 'a-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text(
        '---\nname: a-skill\ndescription: d\nuser-invocable: false\n---\n\n# A Skill\n', encoding='utf-8'
    )
    return bundle


# =============================================================================
# parse_csv_filter
# =============================================================================


def test_parse_csv_filter_none_returns_none():
    assert _doctor.parse_csv_filter(None) is None


def test_parse_csv_filter_empty_string_returns_none():
    assert _doctor.parse_csv_filter('') is None


def test_parse_csv_filter_splits_and_trims():
    assert _doctor.parse_csv_filter(' alpha , beta ,, gamma ') == {'alpha', 'beta', 'gamma'}


# =============================================================================
# _parse_rules_flag / _resolve_active_rules
# =============================================================================


def test_parse_rules_flag_none_is_empty():
    assert _doctor._parse_rules_flag(None) == frozenset()


def test_parse_rules_flag_keeps_known_tokens():
    assert _doctor._parse_rules_flag('argument_naming,verb_chain') == frozenset(
        {'argument_naming', 'verb_chain'}
    )


def test_parse_rules_flag_drops_unknown_and_warns(capsys):
    result = _doctor._parse_rules_flag('argument_naming,bogus_rule')

    assert result == frozenset({'argument_naming'})
    stderr = capsys.readouterr().err
    assert 'bogus_rule' in stderr, 'rejected token must be named on stderr'
    assert 'argument_naming' in stderr, 'accepted registry must be advertised in the warning'


def test_resolve_active_rules_unions_rules_and_alias_flags():
    args = _ns(rules='verb_chain', enable_argument_naming=True)

    assert _doctor._resolve_active_rules(args) == frozenset({'verb_chain', 'argument_naming'})


def test_resolve_active_rules_verb_chain_alias_only():
    args = _ns(enable_verb_chain=True)

    assert _doctor._resolve_active_rules(args) == frozenset({'verb_chain'})


# =============================================================================
# _resolve_marketplace_root
# =============================================================================


def test_resolve_marketplace_root_returns_bundles_path_from_override(tmp_path):
    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor._resolve_marketplace_root(args)

    assert isinstance(result, Path)
    assert result == tmp_path / 'marketplace' / 'bundles'


def test_resolve_marketplace_root_invalid_override_returns_error_envelope(tmp_path):
    args = _ns(marketplace_root=str(tmp_path))  # no bundles/ subdir

    result = _doctor._resolve_marketplace_root(args)

    assert isinstance(result, dict)
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_marketplace_root'


def test_resolve_marketplace_root_not_found_returns_error_envelope(monkeypatch):
    monkeypatch.setattr(_doctor, 'find_marketplace_root', lambda _override: None)

    result = _doctor._resolve_marketplace_root(_ns())

    assert isinstance(result, dict)
    assert result['error'] == 'not_found'


# =============================================================================
# collect_filtered_components
# =============================================================================


def test_collect_filtered_components_type_filter_restricts_to_skills(tmp_path):
    bundle = _make_bundle(tmp_path / 'bundles', 'b1')

    collected = _doctor.collect_filtered_components([bundle], {'skills'}, None)

    assert collected, 'should collect the skill component'
    assert all(c['type'] == 'skill' for c in collected)
    assert all(c['_bundle_name'] == 'b1' for c in collected)


def test_collect_filtered_components_name_filter_drops_unmatched(tmp_path):
    bundle = _make_bundle(tmp_path / 'bundles', 'b1')

    collected = _doctor.collect_filtered_components([bundle], None, {'does-not-exist'})

    assert collected == []


def test_collect_filtered_components_no_filter_includes_agent_and_skill(tmp_path):
    bundle = _make_bundle(tmp_path / 'bundles', 'b1')

    collected = _doctor.collect_filtered_components([bundle], None, None)

    types_found = {c['type'] for c in collected}
    assert {'agent', 'skill'} <= types_found


# =============================================================================
# _rel_to_bundles
# =============================================================================


def test_rel_to_bundles_inside_tree_returns_relative(tmp_path):
    root = tmp_path / 'bundles'
    target = root / 'b' / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('x', encoding='utf-8')

    assert _doctor._rel_to_bundles(str(target), root) == 'b/skills/s/SKILL.md'


def test_rel_to_bundles_outside_tree_returns_none(tmp_path):
    root = tmp_path / 'bundles'
    root.mkdir()
    outside = tmp_path / 'elsewhere' / 'file.md'
    outside.parent.mkdir(parents=True)
    outside.write_text('x', encoding='utf-8')

    assert _doctor._rel_to_bundles(str(outside), root) is None


# =============================================================================
# _resolve_scope_dirs / _finding_in_scope
# =============================================================================


def test_resolve_scope_dirs_dir_stays_file_becomes_parent_missing_dropped(tmp_path):
    a_dir = tmp_path / 'skill-a'
    a_dir.mkdir()
    a_file = tmp_path / 'skill-b' / 'SKILL.md'
    a_file.parent.mkdir()
    a_file.write_text('x', encoding='utf-8')
    missing = tmp_path / 'gone'

    resolved = _doctor._resolve_scope_dirs([str(a_dir), str(a_file), str(missing)])

    assert a_dir.resolve() in resolved
    assert a_file.parent.resolve() in resolved
    assert missing.resolve() not in resolved


def test_finding_in_scope_true_when_under_scope_dir(tmp_path):
    scope = tmp_path / 'skill'
    scope.mkdir()
    finding = {'file': str(scope / 'standards' / 'x.md')}

    assert _doctor._finding_in_scope(finding, [scope.resolve()]) is True


def test_finding_in_scope_false_without_file_key(tmp_path):
    assert _doctor._finding_in_scope({'message': 'no file'}, [tmp_path.resolve()]) is False


def test_finding_in_scope_false_when_outside_scope(tmp_path):
    scope = tmp_path / 'in'
    scope.mkdir()
    other = tmp_path / 'out' / 'file.md'
    other.parent.mkdir()

    assert _doctor._finding_in_scope({'file': str(other)}, [scope.resolve()]) is False


# =============================================================================
# filter_suppressed_findings
# =============================================================================


def test_filter_suppressed_findings_empty_input_short_circuits():
    assert _doctor.filter_suppressed_findings([], Path('/x/bundles'), {}, {}) == []


def test_filter_suppressed_findings_non_suppressible_rule_passes_through(tmp_path):
    findings = [{'rule_id': 'some-other-rule', 'file': str(tmp_path / 'f.md')}]

    kept = _doctor.filter_suppressed_findings(findings, tmp_path, {}, {})

    assert kept == findings


def test_filter_suppressed_findings_suppressible_without_file_is_kept():
    findings = [{'rule_id': 'no-historical-prose-in-skills'}]

    kept = _doctor.filter_suppressed_findings(findings, Path('/x/bundles'), {}, {})

    assert kept == findings


def test_filter_suppressed_findings_suppressible_unconfigured_is_kept(tmp_path):
    bundles = tmp_path / 'bundles'
    f = bundles / 'b' / 'skills' / 's' / 'SKILL.md'
    f.parent.mkdir(parents=True)
    f.write_text('# clean body\n', encoding='utf-8')
    findings = [{'rule_id': 'no-lesson-id-in-skill-prose', 'file': str(f)}]

    kept = _doctor.filter_suppressed_findings(findings, bundles, {}, {})

    assert kept == findings, 'no config + no frontmatter disable means nothing is suppressed'


# =============================================================================
# _list_components_paths
# =============================================================================


def test_list_components_paths_no_valid_paths(capsys):
    result = _doctor._list_components_paths(['/definitely/not/here'])

    assert result['mode'] == 'paths'
    assert result['total_components'] == 0
    assert result['components'] == []
    assert 'WARNING' in capsys.readouterr().err


def test_list_components_paths_skill_uses_dir_name(tmp_path):
    skill = tmp_path / 'my-skill'
    skill.mkdir()
    (skill / 'SKILL.md').write_text('---\nname: my-skill\ndescription: d\n---\n\n# My Skill\n', encoding='utf-8')

    result = _doctor._list_components_paths([str(skill)])

    assert result['total_components'] == 1
    entry = result['components'][0]
    assert entry['type'] == 'skill'
    assert entry['name'] == 'my-skill'


def test_list_components_paths_agent_uses_file_stem(tmp_path):
    agents = tmp_path / 'agents'
    agents.mkdir()
    agent_md = agents / 'worker-agent.md'
    agent_md.write_text('---\nname: worker-agent\ndescription: d\ntools: Read\n---\n\n# Worker\n', encoding='utf-8')

    result = _doctor._list_components_paths([str(agent_md)])

    assert result['total_components'] == 1
    entry = result['components'][0]
    assert entry['type'] == 'agent'
    assert entry['name'] == 'worker-agent'


# =============================================================================
# _load_validator_registry
# =============================================================================


def test_load_validator_registry_none_path_returns_empty():
    assert _doctor._load_validator_registry(None) == []


def test_load_validator_registry_missing_file_returns_empty(tmp_path):
    assert _doctor._load_validator_registry(str(tmp_path / 'absent.json')) == []


def test_load_validator_registry_non_list_json_returns_empty(tmp_path):
    reg = tmp_path / 'reg.json'
    reg.write_text(json.dumps({'not': 'a list'}), encoding='utf-8')

    assert _doctor._load_validator_registry(str(reg)) == []


def test_load_validator_registry_keeps_only_complete_entries(tmp_path):
    reg = tmp_path / 'reg.json'
    reg.write_text(
        json.dumps(
            [
                {'validator_path': 'v.py', 'regex_constant': 'PATTERN', 'list_command': 'cmd'},
                {'validator_path': 'incomplete.py'},  # missing keys → dropped
                'not-a-dict',  # → dropped
            ]
        ),
        encoding='utf-8',
    )

    cleaned = _doctor._load_validator_registry(str(reg))

    assert len(cleaned) == 1
    assert cleaned[0] == {'validator_path': 'v.py', 'regex_constant': 'PATTERN', 'list_command': 'cmd'}


def test_load_validator_registry_invalid_json_returns_empty(tmp_path):
    reg = tmp_path / 'reg.json'
    reg.write_text('{not valid json', encoding='utf-8')

    assert _doctor._load_validator_registry(str(reg)) == []
