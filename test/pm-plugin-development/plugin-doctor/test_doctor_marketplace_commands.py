# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""In-process command tests for ``doctor-marketplace.py`` subcommand entry points.

The ``cmd_*`` functions (list-components, analyze, fix, report, quality-gate,
test-conventions, validate-contracts) are exercised end-to-end only via
subprocess by the sibling ``test_doctor_marketplace.py``, so coverage never
attributed their many orchestration lines. Here each is invoked in-process
against a synthetic marketplace built under ``tmp_path`` with an argparse-shaped
namespace, so the dispatch + rule-orchestration paths are counted and their
result envelopes asserted.
"""

import json
import types
from pathlib import Path

from conftest import load_script_module

_doctor = load_script_module(
    'pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py', 'doctor_marketplace_cmds'
)


def _ns(**overrides):
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
        'test_root': None,
        'registry': None,
        'extension_type': None,
        'skill': None,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _build_clean_marketplace(root: Path) -> Path:
    """A marketplace whose single skill is clean of static-analysis findings."""
    bundles = root / 'marketplace' / 'bundles'
    bundle = bundles / 'qg-clean'
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps({'name': 'qg-clean', 'version': '1.0.0'}))
    _write(
        bundle / 'skills' / 'noop-skill' / 'SKILL.md',
        '---\nname: noop-skill\ndescription: Does nothing\nuser-invocable: false\nmode: knowledge\n---\n\n# Noop\n\nNo-op.\n',
    )
    return root


def _build_defective_marketplace(root: Path) -> Path:
    """A marketplace with an agent declaring the prohibited Task tool."""
    bundles = root / 'marketplace' / 'bundles'
    bundle = bundles / 'def-bundle'
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps({'name': 'def-bundle', 'version': '1.0.0'}))
    _write(
        bundle / 'agents' / 'bad-agent.md',
        '---\nname: bad-agent\ndescription: An agent with Task\ntools: Read, Write, Task\n---\n\n# Bad Agent\n',
    )
    return root


def _build_argparse_violation_marketplace(root: Path) -> Path:
    """A marketplace whose script omits ``allow_abbrev=False`` (a gate violation)."""
    bundles = root / 'marketplace' / 'bundles'
    bundle = bundles / 'qg-violation'
    _write(bundle / '.claude-plugin' / 'plugin.json', json.dumps({'name': 'qg-violation', 'version': '1.0.0'}))
    _write(
        bundle / 'skills' / 'bad-skill' / 'SKILL.md',
        '---\nname: bad-skill\ndescription: d\nuser-invocable: false\nmode: knowledge\n---\n\n# Bad\n',
    )
    _write(
        bundle / 'skills' / 'bad-skill' / 'scripts' / 'bad_script.py',
        "import argparse\n\nparser = argparse.ArgumentParser(description='no allow_abbrev')\nparser.add_argument('--foo')\n",
    )
    return root


# =============================================================================
# cmd_list_components
# =============================================================================


def test_cmd_list_components_enumerates_bundle(tmp_path):
    _build_clean_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_list_components(args)

    assert result['status'] == 'success'
    assert result['total_bundles'] == 1
    assert result['bundles'][0]['name'] == 'qg-clean'
    assert result['bundles'][0]['skills'] == 1


def test_cmd_list_components_bundle_filter_excludes_others(tmp_path):
    _build_clean_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), bundles='no-such-bundle')

    result = _doctor.cmd_list_components(args)

    assert result['total_bundles'] == 0


def test_cmd_list_components_paths_mode(tmp_path):
    skill = tmp_path / 'lone-skill'
    skill.mkdir()
    (skill / 'SKILL.md').write_text('---\nname: lone-skill\ndescription: d\n---\n\n# Lone\n', encoding='utf-8')
    args = _ns(paths=[str(skill)])

    result = _doctor.cmd_list_components(args)

    assert result['mode'] == 'paths'
    assert result['total_components'] == 1


def test_cmd_list_components_invalid_root_returns_error(tmp_path):
    args = _ns(marketplace_root=str(tmp_path))  # no bundles/

    result = _doctor.cmd_list_components(args)

    assert result['status'] == 'error'


# =============================================================================
# cmd_analyze
# =============================================================================


def test_cmd_analyze_returns_categorized_envelope(tmp_path):
    _build_clean_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_analyze(args)

    assert result['status'] == 'success'
    for field in (
        'total_components',
        'total_issues',
        'safe_fixes',
        'risky_fixes',
        'unfixable',
        'analysis',
        'categorized_safe',
        'categorized_risky',
        'categorized_unfixable',
    ):
        assert field in result, f'analyze envelope must carry {field}'


def test_cmd_analyze_detects_task_tool_defect(tmp_path):
    _build_defective_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_analyze(args)

    assert result['total_issues'] >= 1
    all_issues = (
        result['categorized_safe'] + result['categorized_risky'] + result['categorized_unfixable']
    )
    types_found = {i.get('type') for i in all_issues}
    assert 'agent-task-tool-prohibited' in types_found


def test_cmd_analyze_type_filter_limits_components(tmp_path):
    _build_defective_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), type='agents')

    result = _doctor.cmd_analyze(args)

    for item in result['analysis']:
        assert item['component']['type'] == 'agent'


# =============================================================================
# cmd_fix
# =============================================================================


def test_cmd_fix_dry_run_does_not_mutate(tmp_path):
    _build_defective_marketplace(tmp_path)
    agent_md = tmp_path / 'marketplace' / 'bundles' / 'def-bundle' / 'agents' / 'bad-agent.md'
    before = agent_md.read_text(encoding='utf-8')
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), dry_run=True)

    result = _doctor.cmd_fix(args)

    assert result['dry_run'] is True
    assert agent_md.read_text(encoding='utf-8') == before, 'dry-run must not modify files'


def test_cmd_fix_clean_tree_leaves_source_untouched(tmp_path):
    _build_clean_marketplace(tmp_path)
    skill_md = tmp_path / 'marketplace' / 'bundles' / 'qg-clean' / 'skills' / 'noop-skill' / 'SKILL.md'
    before = skill_md.read_text(encoding='utf-8')
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), dry_run=False)

    result = _doctor.cmd_fix(args)

    # A finding-free skill yields no safe fixes, so a non-dry-run leaves it intact.
    assert skill_md.read_text(encoding='utf-8') == before
    assert result.get('failed', 0) == 0


# =============================================================================
# cmd_quality_gate
# =============================================================================


def test_cmd_quality_gate_clean_tree_passes(tmp_path):
    _build_clean_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_quality_gate(args)

    assert result['status'] == 'pass'
    assert result['total_issues'] == 0
    assert 'rules_run' in result


def test_cmd_quality_gate_argparse_violation_fails(tmp_path):
    _build_argparse_violation_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_quality_gate(args)

    assert result['status'] == 'fail'
    assert result['total_issues'] >= 1


def test_cmd_quality_gate_paths_scope_excludes_unrelated_finding(tmp_path):
    _build_argparse_violation_marketplace(tmp_path)
    # Scope to an unrelated, finding-free directory: the argparse violation
    # lives under bad-skill, so scoping elsewhere filters it out → pass.
    unrelated = tmp_path / 'marketplace' / 'bundles' / 'qg-violation' / 'skills' / 'bad-skill' / 'references'
    unrelated.mkdir(parents=True)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), paths=[str(unrelated)])

    result = _doctor.cmd_quality_gate(args)

    assert result['status'] == 'pass', 'a scope with no in-scope findings must pass'


# =============================================================================
# cmd_report
# =============================================================================


def test_cmd_report_writes_json_report(tmp_path):
    _build_clean_marketplace(tmp_path)
    out_dir = tmp_path / 'report-out'
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), output=str(out_dir))

    result = _doctor.cmd_report(args)

    assert result['status'] == 'success'
    report_path = Path(result['report_file'])
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding='utf-8'))
    assert 'summary' in data
    assert result['summary']['total_bundles'] == 1


# =============================================================================
# cmd_test_conventions
# =============================================================================


def test_cmd_test_conventions_clean_test_tree_passes(tmp_path):
    _build_clean_marketplace(tmp_path)
    test_root = tmp_path / 'test'
    test_root.mkdir()
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), test_root=str(test_root))

    result = _doctor.cmd_test_conventions(args)

    assert result['status'] == 'pass'
    assert result['total_issues'] == 0


def test_cmd_test_conventions_flags_generic_fixture_basename(tmp_path):
    _build_clean_marketplace(tmp_path)
    test_root = tmp_path / 'test'
    _write(test_root / 'pkg' / '_fixtures.py', '# generic basename collides\n')
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'), test_root=str(test_root))

    result = _doctor.cmd_test_conventions(args)

    assert result['status'] == 'fail'
    assert result['total_issues'] >= 1


# =============================================================================
# cmd_validate_contracts
# =============================================================================


def test_cmd_validate_contracts_clean_tree_has_no_errors(tmp_path):
    _build_clean_marketplace(tmp_path)
    args = _ns(marketplace_root=str(tmp_path / 'marketplace'))

    result = _doctor.cmd_validate_contracts(args)

    assert result.get('errors', []) == []
