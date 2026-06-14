#!/usr/bin/env python3
"""Tests for doctor-marketplace.py - batch marketplace analysis and fixing.

Tests the hybrid Phase 1 script that provides automated batch operations:
- list-components: Enumerate all components (runs no rules)
- analyze: Batch analyze for issues
- fix: Apply safe fixes automatically
- report: Generate comprehensive report
- quality-gate: Run invariant rules as a build gate (optionally --paths scoped)

Output format: TOON (parsed via toon_parser).

Marketplace discovery in these tests:
- Real-marketplace tests rely on script-relative discovery inside
  ``find_marketplace_root`` and therefore need no cwd/env setup.
- Fixture tests that construct a fake marketplace under ``tmp_path`` pass
  ``PM_MARKETPLACE_ROOT`` via ``env_overrides`` so the script targets the
  fixture deterministically instead of the real tree.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, get_scripts_dir, load_script_module, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py')
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'

# Direct-import handle for ``_doctor_shared.find_marketplace_root`` so the
# --marketplace-root flag tests can exercise the resolution logic without
# the subprocess overhead of a full doctor-marketplace.py invocation.


def _load_doctor_shared():
    return load_script_module('pm-plugin-development', 'plugin-doctor', '_doctor_shared.py', '_doctor_shared_under_test')


_doctor_shared = _load_doctor_shared()
find_marketplace_root = _doctor_shared.find_marketplace_root


def parse_output(result):
    """Parse TOON output from script result."""
    return parse_toon(result.stdout)


def marketplace_available():
    """Check if marketplace is available for integration tests."""
    return MARKETPLACE_ROOT.is_dir() and any(MARKETPLACE_ROOT.iterdir())


# =============================================================================
# Help and Basic Tests (Tier 3 - subprocess)
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'list-components' in combined, 'list-components subcommand in help'
    assert 'analyze' in combined, 'analyze subcommand in help'
    assert 'fix' in combined, 'fix subcommand in help'
    assert 'report' in combined, 'report subcommand in help'
    assert 'quality-gate' in combined, 'quality-gate subcommand in help'
    assert 'scan' not in combined.split(), 'scan subcommand must be removed (renamed to list-components)'


def test_no_command_shows_help():
    """Test that running without command shows help."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode != 0, 'Should return error without command'
    combined = result.stdout + result.stderr
    assert 'list-components' in combined or 'usage' in combined.lower(), 'Should show usage information'


# =============================================================================
# list-components Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_list_components_help():
    """Test list-components --help is available."""
    result = run_script(SCRIPT_PATH, 'list-components', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'


def test_scan_subcommand_removed():
    """The renamed-away `scan` subcommand now fails with argparse exit 2."""
    result = run_script(SCRIPT_PATH, 'scan', '--paths', '/tmp')
    assert result.returncode == 2, f'scan must be rejected with argparse exit 2, got {result.returncode}'
    assert 'invalid choice' in (result.stdout + result.stderr).lower(), 'argparse should report invalid choice'


# Real-tree enumeration shape tests are covered in-process by the synthetic
# test_fixture_list_components / test_fixture_list_components_bundle_filter.


# =============================================================================
# Analyze Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_analyze_help():
    """Test analyze --help is available."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'type' in combined.lower(), 'Help should mention type option'


# Real-tree analyze shape tests (test_analyze_returns_valid_toon,
# test_analyze_summary_structure, test_analyze_categorized_structure,
# test_analyze_type_filter) were removed — the contract is covered in-process by
# the synthetic test_fixture_analyze_finds_issues / test_fixture_analyze_type_filter.


# =============================================================================
# Fix Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_fix_help():
    """Test fix --help is available."""
    result = run_script(SCRIPT_PATH, 'fix', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'dry-run' in combined.lower(), 'Help should mention dry-run option'


# Real-tree fix dry-run tests (test_fix_dry_run_returns_valid_toon,
# test_fix_dry_run_no_changes) were removed — the contract (status/dry_run TOON
# fields + no-mutation guarantee) is covered in-process by test_fixture_fix_dry_run.


# =============================================================================
# Report Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_report_help():
    """Test report --help is available."""
    result = run_script(SCRIPT_PATH, 'report', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'output' in combined.lower(), 'Help should mention output option'


# Real-tree report shape tests (test_report_returns_valid_toon,
# test_report_summary_structure, test_report_has_llm_review_items,
# test_report_to_custom_dir) were removed — the contract (status, summary fields,
# report_dir/file/findings, llm_review_items, --output) is covered in-process by
# the synthetic test_fixture_report / test_fixture_report_to_custom_dir.


# =============================================================================
# Integration Tests with Fixture (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


class TestWithTempMarketplace:
    """Tests using a temporary marketplace fixture."""

    def setup_temp_marketplace(self):
        """Create a temporary marketplace structure for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.marketplace_root = self.temp_dir / 'marketplace' / 'bundles'
        self.marketplace_root.mkdir(parents=True)

        # Create a test bundle
        bundle_dir = self.marketplace_root / 'test-bundle'
        bundle_dir.mkdir()

        # Create plugin.json
        plugin_dir = bundle_dir / '.claude-plugin'
        plugin_dir.mkdir()
        (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'test-bundle', 'version': '1.0.0'}))

        # Create an agent with issues
        agents_dir = bundle_dir / 'agents'
        agents_dir.mkdir()
        (agents_dir / 'test-agent.md').write_text("""---
name: test-agent
description: A test agent
tools: Read, Write, Task
---

# Test Agent

This agent does testing.
""")

        # Create a command missing tools
        commands_dir = bundle_dir / 'commands'
        commands_dir.mkdir()
        (commands_dir / 'test-command.md').write_text("""---
name: test-command
description: A test command
---

# Test Command

Run with `/test-command`.
""")

        # Create a skill
        skill_dir = bundle_dir / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text("""---
name: test-skill
description: A test skill
---

# Test Skill

This skill provides testing capabilities.
""")

        return self.temp_dir

    def cleanup(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def test_fixture_list_components():
    """Test list-components with fixture marketplace."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(
            SCRIPT_PATH,
            'list-components',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'list-components failed: {result.stderr}'

        data = parse_output(result)
        # Default enumeration (no --paths/--bundles) must NOT be in paths mode
        # (covers the former real-tree test_scan_without_paths_or_bundles).
        assert 'mode' not in data or data.get('mode') != 'paths', 'Default enumeration should not be in paths mode'
        assert 'bundles' in data, 'Should have bundles field'
        assert 'total_bundles' in data, 'Should have total_bundles field'
        assert 'total_components' in data, 'Should have total_components field'
        assert data['total_bundles'] == 1, 'Should find one bundle'
        assert len(data['bundles']) == data['total_bundles'], 'Bundle list length should match total_bundles'

        bundle = data['bundles'][0]
        assert bundle['name'] == 'test-bundle', 'Should be test-bundle'
        for field in ('name', 'path', 'agents', 'commands', 'skills', 'scripts', 'total'):
            assert field in bundle, f'Bundle should have {field}'
    finally:
        fixture.cleanup()


def test_fixture_list_components_bundle_filter():
    """Test list-components --bundles filter restricts output to the named bundle."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(
            SCRIPT_PATH,
            'list-components',
            '--bundles',
            'test-bundle',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'list-components --bundles failed: {result.stderr}'

        data = parse_output(result)
        assert data['total_bundles'] == 1, 'Should have exactly one bundle'
        assert data['bundles'][0]['name'] == 'test-bundle', 'Should be test-bundle'
    finally:
        fixture.cleanup()


def test_fixture_analyze_finds_issues():
    """Test analyze finds issues in fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        # Valid-TOON structure (from the former real-tree test_analyze_returns_valid_toon)
        assert 'analysis' in data, 'Should have analysis field'
        assert 'total_components' in data, 'Should have total_components field'
        assert 'total_issues' in data, 'Should have total_issues field'
        # Summary fields (from the former real-tree test_analyze_summary_structure)
        assert 'safe_fixes' in data, 'Should have safe_fixes'
        assert 'risky_fixes' in data, 'Should have risky_fixes'
        assert 'unfixable' in data, 'Should have unfixable'
        # Categorized fields (from the former real-tree test_analyze_categorized_structure)
        assert 'categorized_safe' in data, 'Should have categorized_safe'
        assert 'categorized_risky' in data, 'Should have categorized_risky'
        assert 'categorized_unfixable' in data, 'Should have categorized_unfixable'
        # Should find at least one issue (Rule 6 - Task in agent)
        assert data['total_issues'] > 0, 'Should find issues in test fixture'
    finally:
        fixture.cleanup()


def test_fixture_analyze_type_filter():
    """Test analyze --type agents restricts analyzed components to agents."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'agents',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        # All analyzed components should be agents — check via analysis table rows
        for item in data['analysis']:
            component = item.get('component', {})
            if isinstance(component, str):
                component = json.loads(component)
            comp_type = component.get('type')
            assert comp_type == 'agent', f'Expected agent, got {comp_type}'
    finally:
        fixture.cleanup()


def test_fixture_fix_dry_run():
    """Test fix dry-run with fixture.

    Covers the former real-tree test_fix_dry_run_returns_valid_toon (status +
    dry_run TOON fields) and test_fix_dry_run_no_changes (mtimes unchanged).
    """
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        bundle_path = fixture.marketplace_root / 'test-bundle'
        mtimes_before = {str(md): md.stat().st_mtime for md in bundle_path.rglob('*.md')}

        result = run_script(
            SCRIPT_PATH,
            'fix',
            '--dry-run',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Fix dry-run failed: {result.stderr}'

        data = parse_output(result)
        assert 'status' in data, 'Should have status field'
        assert 'dry_run' in data, 'Should have dry_run field'
        assert data['dry_run'] is True, 'Should be dry run'

        # Dry-run must not mutate any file.
        for md in bundle_path.rglob('*.md'):
            path_str = str(md)
            if path_str in mtimes_before:
                assert mtimes_before[path_str] == md.stat().st_mtime, f'File modified during dry-run: {md}'
    finally:
        fixture.cleanup()


def test_fixture_report():
    """Test report with fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(
            SCRIPT_PATH,
            'report',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        response = parse_output(result)
        assert response['status'] == 'success', 'Status should be success'

        summary = response['summary']
        assert summary['total_bundles'] == 1, 'Should have one bundle'
        # Summary structure (from the former real-tree test_report_summary_structure)
        for field in ('total_bundles', 'total_components', 'total_issues', 'safe_fixes', 'risky_fixes'):
            assert field in summary, f'Summary should have {field}'

        assert 'report_dir' in response, 'Should have report_dir'
        assert 'report_file' in response, 'Should have report_file'
        assert 'findings_file' in response, 'Should have findings_file'

        # Read and verify report file (still JSON on disk)
        report_path = temp_dir / response['report_file']
        assert report_path.exists(), f'Report file should exist: {report_path}'

        with open(report_path) as f:
            report_data = json.load(f)
        assert 'llm_review_items' in report_data, 'Report should have LLM review items'

        # Verify directory structure
        report_dir = temp_dir / response['report_dir']
        assert report_dir.is_dir(), f'Report dir should exist: {report_dir}'
    finally:
        fixture.cleanup()


def test_fixture_report_to_custom_dir():
    """Test report --output writes the report JSON to a custom directory.

    Covers the former real-tree test_report_to_custom_dir.
    """
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()
    output_dir = Path(tempfile.mkdtemp())

    try:
        result = run_script(
            SCRIPT_PATH,
            'report',
            '--output',
            str(output_dir),
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        json_files = list(output_dir.glob('*-report.json'))
        assert len(json_files) == 1, f'Should have exactly one report JSON file, found: {json_files}'

        with open(json_files[0]) as f:
            data = json.load(f)
        assert 'summary' in data, 'File should contain valid report'
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        fixture.cleanup()


# =============================================================================
# Sub-Document Analysis Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_fixture_analyze_includes_subdocuments():
    """Test analyze includes subdocuments key for skills with sub-documents."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    # Add references/ to the test skill
    skill_refs_dir = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'references'
    skill_refs_dir.mkdir(parents=True)
    (skill_refs_dir / 'guide.md').write_text('# Guide\n\nSome guidance content.\n')

    # Update SKILL.md to reference the guide
    skill_md = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'SKILL.md'
    skill_md.write_text("""---
name: test-skill
description: A test skill
user-invocable: true
---

# Test Skill

Read `references/guide.md` for standards.
""")

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'skills',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        # Find the test-skill analysis
        skill_analysis = None
        for item in data['analysis']:
            component = item.get('component', {})
            if isinstance(component, str):
                component = json.loads(component)
            if component.get('name') == 'test-skill':
                skill_analysis = item
                break

        assert skill_analysis is not None, 'Should find test-skill in analysis'
        analysis = skill_analysis.get('analysis', {})
        if isinstance(analysis, str):
            analysis = json.loads(analysis)
        assert 'subdocuments' in analysis, 'Skill analysis should include subdocuments key'
        subdocs = analysis['subdocuments']
        assert len(subdocs) >= 1, f'Should have at least 1 sub-document, got {len(subdocs)}'
        assert subdocs[0]['relative_path'] == 'references/guide.md', (
            f'Expected references/guide.md, got {subdocs[0]["relative_path"]}'
        )
    finally:
        fixture.cleanup()


def test_fixture_analyze_detects_subdoc_bloat():
    """Test analyze detects bloated sub-documents."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    skill_refs_dir = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'references'
    skill_refs_dir.mkdir(parents=True)
    bloated_content = '# Bloated Guide\n\n' + 'This is a line of content that adds to the bloat.\n' * 650
    (skill_refs_dir / 'bloated-guide.md').write_text(bloated_content)

    skill_md = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'SKILL.md'
    skill_md.write_text("""---
name: test-skill
description: A test skill
user-invocable: true
---

# Test Skill

Read `references/bloated-guide.md` for standards.
""")

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'skills',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data)

        bloat_issues = [i for i in all_issues if i['type'] == 'subdoc-bloat']
        assert len(bloat_issues) >= 1, f'Should detect subdoc-bloat, got issues: {[i["type"] for i in all_issues]}'
        assert bloat_issues[0]['classification'] == 'BLOATED', (
            f'Expected BLOATED, got {bloat_issues[0]["classification"]}'
        )
    finally:
        fixture.cleanup()


def test_fixture_analyze_no_subdoc_for_normal_files():
    """Test analyze does not flag normal-sized sub-documents."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    skill_refs_dir = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'references'
    skill_refs_dir.mkdir(parents=True)
    (skill_refs_dir / 'small-guide.md').write_text('# Small Guide\n\nJust a few lines.\n')

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'skills',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data)

        bloat_issues = [i for i in all_issues if i['type'] == 'subdoc-bloat']
        assert len(bloat_issues) == 0, f'Should NOT flag normal sub-documents, found {len(bloat_issues)}'
    finally:
        fixture.cleanup()


# =============================================================================
# Sub-document Hardcoded Path Tests (Tier 3 - subprocess)
# =============================================================================


def test_fixture_analyze_detects_subdoc_hardcoded_path():
    """Test analyze detects hardcoded script paths in sub-documents."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    skill_stds_dir = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'standards'
    skill_stds_dir.mkdir(parents=True)
    (skill_stds_dir / 'test-workflow.md').write_text(
        '# Test Workflow\n\n```bash\npython3 marketplace/bundles/my-bundle/skills/my-skill/scripts/run.py\n```\n'
    )

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'skills',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data)

        path_issues = [i for i in all_issues if i['type'] == 'subdoc-hardcoded-script-path']
        assert len(path_issues) >= 1, f'Should detect hardcoded path in subdoc, found {len(path_issues)}'
    finally:
        fixture.cleanup()


# =============================================================================
# Rule 11 Detection Tests (Tier 3 - subprocess)
# =============================================================================


def test_fixture_analyze_detects_rule_11():
    """Test analyze detects Rule 11 violation (agent tools missing Skill)."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'no-skill-agent.md').write_text(
        '---\nname: no-skill-agent\ndescription: Agent without Skill\ntools: Read, Write, Edit\n---\n\n# No Skill Agent\n'
    )

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data)

        rule_11_issues = [i for i in all_issues if i['type'] == 'agent-skill-tool-visibility']
        assert len(rule_11_issues) >= 1, (
            f'Should detect agent-skill-tool-visibility, got issues: {[i["type"] for i in all_issues]}'
        )
        assert rule_11_issues[0]['fixable'] is True, 'Rule 11 should be fixable'
        assert rule_11_issues[0]['severity'] == 'warning', 'Rule 11 should be warning severity'
    finally:
        fixture.cleanup()


def test_fixture_analyze_no_rule_11_with_skill():
    """Test analyze does NOT flag Rule 11 when Skill is present in tools."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'has-skill-agent.md').write_text(
        '---\nname: has-skill-agent\ndescription: Agent with Skill\ntools: Read, Write, Skill\n---\n\n# Has Skill Agent\n'
    )

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data, path_filter='has-skill-agent')

        rule_11_issues = [i for i in all_issues if i['type'] == 'agent-skill-tool-visibility']
        assert len(rule_11_issues) == 0, 'Should NOT detect agent-skill-tool-visibility when Skill is present'
    finally:
        fixture.cleanup()


def test_fixture_analyze_no_rule_11_without_tools():
    """Test analyze does NOT flag Rule 11 when no tools field (inherits all)."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'no-tools-agent.md').write_text(
        '---\nname: no-tools-agent\ndescription: Agent without tools\n---\n\n# No Tools Agent\n'
    )

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        all_issues = _collect_issues(data, path_filter='no-tools-agent')

        rule_11_issues = [i for i in all_issues if i['type'] == 'agent-skill-tool-visibility']
        assert len(rule_11_issues) == 0, 'Should NOT detect agent-skill-tool-visibility when no tools field'
    finally:
        fixture.cleanup()


# =============================================================================
# Skill Tool Coverage Tests (Tier 3 - subprocess)
# =============================================================================


def test_fixture_analyze_skill_has_coverage():
    """Test analyze includes tool coverage for skills (no tools declared)."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    skill_md = fixture.marketplace_root / 'test-bundle' / 'skills' / 'test-skill' / 'SKILL.md'
    skill_md.write_text("""---
name: test-skill
description: A test skill
user-invocable: true
---

# Test Skill

This skill provides testing capabilities.
""")

    try:
        result = run_script(
            SCRIPT_PATH,
            'analyze',
            '--type',
            'skills',
            env_overrides={
                'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'),
                'PLAN_BASE_DIR': str(temp_dir / '.plan'),
                'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials'),
            },
        )
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        skill_analysis = None
        for item in data['analysis']:
            component = item.get('component', {})
            if isinstance(component, str):
                component = json.loads(component)
            if component.get('name') == 'test-skill':
                skill_analysis = item
                break

        assert skill_analysis is not None, 'Should find test-skill in analysis'
        analysis = skill_analysis.get('analysis', {})
        if isinstance(analysis, str):
            analysis = json.loads(analysis)
        assert 'coverage' in analysis, f'Skill analysis should include coverage key, got keys: {list(analysis.keys())}'

        coverage = analysis['coverage']
        tool_coverage = coverage.get('tool_coverage', {})
        declared = tool_coverage.get('declared_tools', [])
        assert declared == [], f'Skills should have no declared tools, got {declared}'
    finally:
        fixture.cleanup()


# =============================================================================
# Helpers
# =============================================================================


def _collect_issues(data, path_filter=None):
    """Collect all issues from TOON analysis output."""
    all_issues = []
    for item in data.get('analysis', []):
        if path_filter:
            component = item.get('component', {})
            if isinstance(component, str):
                component = json.loads(component)
            if path_filter not in component.get('path', ''):
                continue
        issues = item.get('issues', [])
        if isinstance(issues, str):
            issues = json.loads(issues)
        all_issues.extend(issues)
    return all_issues


# =============================================================================
# list-components --paths Flag Tests (Tier 3 - subprocess)
# =============================================================================


def test_list_components_paths_valid_skill(tmp_path):
    """Test list-components --paths with a valid skill directory containing SKILL.md."""
    skill_dir = tmp_path / 'my-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text("""---
name: my-skill
description: A test skill for paths enumeration
---

# My Skill

Content here.
""")

    result = run_script(SCRIPT_PATH, 'list-components', '--paths', str(skill_dir))
    assert result.returncode == 0, f'list-components --paths failed: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 1, f'Should find 1 component, got {data["total_components"]}'
    assert data['components'][0]['type'] == 'skill', 'Should detect skill type'
    assert data['components'][0]['name'] == 'my-skill', 'Should use directory name as skill name'
    # list-components enumerates only — it must NOT carry an issues field.
    assert 'issues' not in data, 'list-components must not produce an issues field'


def test_list_components_paths_multiple(tmp_path):
    """Test list-components --paths with multiple paths (skill and agent)."""
    # Create a skill directory
    skill_dir = tmp_path / 'test-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text("""---
name: test-skill
description: A test skill
---

# Test Skill
""")

    # Create an agent directory under agents/ parent for fallback detection
    agents_parent = tmp_path / 'agents'
    agents_parent.mkdir()
    (agents_parent / 'test-agent.md').write_text("""---
name: test-agent
description: A test agent
tools: Read, Write
---

# Test Agent
""")

    result = run_script(SCRIPT_PATH, 'list-components', '--paths', str(skill_dir), str(agents_parent))
    assert result.returncode == 0, f'list-components --paths failed: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 2, f'Should find 2 components, got {data["total_components"]}'

    types_found = {c['type'] for c in data['components']}
    assert 'skill' in types_found, 'Should find the skill component'


def test_list_components_paths_invalid_path(tmp_path):
    """Test list-components --paths with a non-existent path skips it with warning."""
    nonexistent = str(tmp_path / 'does-not-exist')

    result = run_script(SCRIPT_PATH, 'list-components', '--paths', nonexistent)
    assert result.returncode == 0, f'list-components --paths should succeed even with invalid path: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 0, 'Should find 0 components for invalid path'
    assert 'WARNING' in result.stderr, 'Should emit warning on stderr for missing path'


def test_list_components_paths_mutual_exclusion_with_bundles():
    """Test list-components --paths and --bundles are mutually exclusive."""
    result = run_script(SCRIPT_PATH, 'list-components', '--paths', '/some/path', '--bundles', 'plan-marshall')
    assert result.returncode != 0, 'Should fail when both --paths and --bundles are provided'


# Real-tree test_scan_without_paths_or_bundles was removed — the default-mode
# contract (no 'mode' key, total_bundles/bundles present) is covered in-process
# by the synthetic test_fixture_list_components.


# =============================================================================
# --marketplace-root Flag Tests (Tier 2 - direct import of _doctor_shared)
# =============================================================================


def test_marketplace_root_flag_overrides_default(tmp_path, monkeypatch):
    """Test marketplace_root_override arg resolves to {override}/bundles.

    Builds a fake marketplace under ``tmp_path/marketplace`` with an empty
    ``bundles/`` subdirectory and verifies that
    ``find_marketplace_root(marketplace_root_override=...)`` returns the
    override's bundles path rather than falling through to script-relative
    or cwd-based discovery.
    """
    # Arrange: ensure no env var leaks into the override-arg path so we
    # exclusively exercise the function-arg branch.
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    fake_marketplace = tmp_path / 'marketplace'
    (fake_marketplace / 'bundles').mkdir(parents=True)

    # Act
    resolved = find_marketplace_root(marketplace_root_override=str(fake_marketplace))

    # Assert
    assert resolved == fake_marketplace / 'bundles', f'Expected {fake_marketplace / "bundles"}, got {resolved}'


def test_marketplace_root_flag_takes_precedence_over_env_var(tmp_path, monkeypatch):
    """Test function-arg override beats PM_MARKETPLACE_ROOT env var.

    Builds two distinct fake marketplaces, sets the env var to one and
    passes the override arg pointing at the other, then asserts the arg
    wins (resolves to override's bundles, never the env var's).
    """
    # Arrange: two valid marketplace roots, each with their own bundles/.
    env_marketplace = tmp_path / 'env-marketplace'
    (env_marketplace / 'bundles').mkdir(parents=True)
    arg_marketplace = tmp_path / 'arg-marketplace'
    (arg_marketplace / 'bundles').mkdir(parents=True)

    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_marketplace))

    # Act
    resolved = find_marketplace_root(marketplace_root_override=str(arg_marketplace))

    # Assert: function-arg path wins, env var path is ignored.
    assert resolved == arg_marketplace / 'bundles', f'Function-arg override should win, got {resolved}'
    assert resolved != env_marketplace / 'bundles', 'Env var path must NOT win when function-arg override is provided'


def test_marketplace_root_invalid_path_errors_clearly(tmp_path, monkeypatch):
    """Test override pointing to a path without bundles/ raises ValueError.

    Passes ``tmp_path`` (which has no ``bundles/`` subdir) as the override
    and asserts that ``find_marketplace_root`` raises ``ValueError`` whose
    message references the missing ``bundles/`` requirement.
    """
    # Arrange: ensure env var is unset so the function-arg branch is the
    # one actually evaluated.
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    # Sanity check: tmp_path must NOT contain a bundles/ subdir.
    assert not (tmp_path / 'bundles').exists(), 'Test precondition: tmp_path must lack bundles/'

    # Act / Assert
    with pytest.raises(ValueError) as exc_info:
        find_marketplace_root(marketplace_root_override=str(tmp_path))

    msg = str(exc_info.value)
    assert 'bundles' in msg, f'Error message should mention bundles/, got: {msg}'
    assert str(tmp_path) in msg, f'Error message should reference the offending path {tmp_path}, got: {msg}'
    # The message must clarify that the override is meant to be the parent
    # of bundles/, not bundles/ itself — this is what callers need to fix.
    assert 'marketplace root' in msg or 'parent of bundles' in msg, (
        f'Error message should clarify the parent-of-bundles contract, got: {msg}'
    )


# =============================================================================
# Quality-Gate Subcommand Tests
# =============================================================================


def _build_clean_fixture(temp_root: Path) -> Path:
    """Build a fixture marketplace whose components are clean of static-analysis findings."""
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)
    bundle = bundles_dir / 'qg-clean'
    bundle.mkdir()

    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir()
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'qg-clean', 'version': '1.0.0'}))

    skill_dir = bundle / 'skills' / 'noop-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text("""---
name: noop-skill
description: Does nothing
user-invocable: false
---

# Noop Skill

No-op.
""")
    return temp_root


def _build_argparse_violation_fixture(temp_root: Path) -> Path:
    """Build a fixture marketplace whose script violates argparse_safety (no allow_abbrev=False)."""
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)
    bundle = bundles_dir / 'qg-violation'
    bundle.mkdir()

    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir()
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'qg-violation', 'version': '1.0.0'}))

    skill_dir = bundle / 'skills' / 'bad-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text("""---
name: bad-skill
description: A skill with a violating script
user-invocable: false
---

# Bad Skill
""")
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir()
    (scripts_dir / 'bad_script.py').write_text(
        'import argparse\n'
        '\n'
        "parser = argparse.ArgumentParser(description='no allow_abbrev')\n"
        "parser.add_argument('--foo')\n"
    )
    return temp_root


def test_quality_gate_help():
    """Test quality-gate --help is available and explains the build-gate role."""
    result = run_script(SCRIPT_PATH, 'quality-gate', '--help')
    combined = result.stdout + result.stderr
    assert 'marketplace-root' in combined.lower(), 'Help should mention --marketplace-root override'
    # quality-gate is intentionally NOT bundle-filtered — no --bundles flag exposed
    assert '--bundles' not in combined, 'quality-gate must NOT expose a --bundles flag'
    # The optional --paths scoping flag IS exposed.
    assert '--paths' in combined, 'quality-gate should expose the --paths scoping flag'


def test_quality_gate_clean_fixture_passes(tmp_path):
    """quality-gate exits 0 with status: pass on a fixture with no findings."""
    temp_root = _build_clean_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides={
            'PM_MARKETPLACE_ROOT': str(temp_root / 'marketplace'),
            'PLAN_BASE_DIR': str(temp_root / '.plan'),
            'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_root / 'credentials'),
        },
    )
    assert result.returncode == 0, f'Expected exit 0 on clean fixture, got {result.returncode}: {result.stderr}'

    data = parse_output(result)
    assert data['status'] == 'pass', f'Expected status: pass on clean fixture, got: {data}'
    assert data['total_issues'] == 0, f'Clean fixture should have zero issues, got {data["total_issues"]}'
    assert 'rules_run' in data, 'Output should enumerate rules_run for transparency'


def test_quality_gate_argparse_violation_fails(tmp_path):
    """quality-gate exits non-zero with status: fail on argparse_safety violation."""
    temp_root = _build_argparse_violation_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides={
            'PM_MARKETPLACE_ROOT': str(temp_root / 'marketplace'),
            'PLAN_BASE_DIR': str(temp_root / '.plan'),
            'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_root / 'credentials'),
        },
    )
    assert result.returncode == 1, (
        f'Expected exit 1 on argparse_safety violation fixture, got {result.returncode}: {result.stderr}'
    )

    data = parse_output(result)
    assert data['status'] == 'fail', f'Expected status: fail on violation fixture, got: {data}'
    assert data['total_issues'] >= 1, 'Should report at least one finding'


def _build_two_skill_scope_fixture(temp_root: Path) -> tuple[Path, Path, Path]:
    """Build a fixture with a violating skill A and a clean skill B.

    Skill A carries a script that violates argparse_safety (no
    allow_abbrev=False); skill B is clean. Returns
    ``(temp_root, skill_a_dir, skill_b_dir)`` so the scoping tests can target
    each skill dir directly.
    """
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)
    bundle = bundles_dir / 'qg-scope'
    bundle.mkdir()

    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir()
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'qg-scope', 'version': '1.0.0'}))

    # Skill A — violating script.
    skill_a = bundle / 'skills' / 'skill-a'
    skill_a.mkdir(parents=True)
    (skill_a / 'SKILL.md').write_text(
        '---\nname: skill-a\ndescription: A skill with a violating script\nuser-invocable: false\n---\n\n# Skill A\n'
    )
    scripts_a = skill_a / 'scripts'
    scripts_a.mkdir()
    (scripts_a / 'bad_script.py').write_text(
        'import argparse\n'
        '\n'
        "parser = argparse.ArgumentParser(description='no allow_abbrev')\n"
        "parser.add_argument('--foo')\n"
    )

    # Skill B — clean.
    skill_b = bundle / 'skills' / 'skill-b'
    skill_b.mkdir(parents=True)
    (skill_b / 'SKILL.md').write_text(
        '---\nname: skill-b\ndescription: A clean skill\nuser-invocable: false\n---\n\n# Skill B\n'
    )
    return temp_root, skill_a, skill_b


def _quality_gate_env(temp_root: Path) -> dict:
    return {
        'PM_MARKETPLACE_ROOT': str(temp_root / 'marketplace'),
        'PLAN_BASE_DIR': str(temp_root / '.plan'),
        'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_root / 'credentials'),
    }


def test_quality_gate_paths_runs_extension_contracts_whole_tree(tmp_path):
    """validate_extension_contracts ALWAYS runs under --paths (whole-tree, unfiltered).

    Pins the documented exception: --paths scopes the file-anchored rules but
    extension-contract validation has no per-path subset, so it must still
    appear in rules_run even on a scoped run over a clean skill. The rules_run
    enumeration is the observable signal that the contract rule executed.
    """
    temp_root, _skill_a, skill_b = _build_two_skill_scope_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        '--paths',
        str(skill_b),
        env_overrides=_quality_gate_env(temp_root),
    )
    data = parse_output(result)
    rules = {entry['rule'] for entry in data['rules_run']}
    assert 'validate_extension_contracts' in rules, (
        f'validate_extension_contracts must run whole-tree even under --paths, rules_run={data["rules_run"]}'
    )


def test_quality_gate_paths_scopes_to_violating_skill(tmp_path):
    """quality-gate --paths {skill-a} surfaces skill A's violation."""
    temp_root, skill_a, _skill_b = _build_two_skill_scope_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        '--paths',
        str(skill_a),
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 1, f'Expected exit 1 scoping to the violating skill, got {result.returncode}'

    data = parse_output(result)
    assert data['status'] == 'fail', f'Scoped run over skill A should fail, got: {data}'
    assert data['total_issues'] >= 1, 'Scoped run over skill A should report the violation'
    # Every reported finding must be anchored under skill A.
    for issue in data['issues']:
        assert str(skill_a) in issue['file'], f'Scoped finding leaked outside skill A: {issue["file"]}'


def test_quality_gate_paths_clean_skill_filters_out_violation(tmp_path):
    """quality-gate --paths {skill-b} reports pass — skill A's violation is filtered out."""
    temp_root, _skill_a, skill_b = _build_two_skill_scope_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        '--paths',
        str(skill_b),
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 0, f'Expected exit 0 scoping to the clean skill, got {result.returncode}: {result.stderr}'

    data = parse_output(result)
    assert data['status'] == 'pass', f'Scoped run over clean skill B should pass, got: {data}'
    assert data['total_issues'] == 0, f'Scoped run over skill B must filter out skill A violation, got: {data}'


def test_quality_gate_no_flag_still_reports_violation(tmp_path):
    """No-flag quality-gate (whole-tree) still reports skill A's violation.

    Pins that --paths is purely additive: the no-flag default path is unchanged
    and still surfaces the marketplace-wide finding.
    """
    temp_root, skill_a, _skill_b = _build_two_skill_scope_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 1, f'No-flag whole-tree gate should fail on the violation, got {result.returncode}'

    data = parse_output(result)
    assert data['status'] == 'fail', f'No-flag gate should fail, got: {data}'
    files = {issue['file'] for issue in data['issues']}
    assert any(str(skill_a) in f for f in files), 'No-flag gate should still report skill A violation'


def test_scoped_manage_invocation_derives_per_referenced_notation(tmp_path, monkeypatch):
    """`_scoped_manage_invocation` derives ONLY the referenced notations via
    `derive_script_tree`, NEVER the eager whole-marketplace `build_script_index`.

    This is the cost contract: a --paths run must not cold-derive the entire
    in-scope script set. The test monkeypatches the module's `derive_script_tree`
    (recording the notations it is asked to derive) and asserts the scoped helper
    only derives notations referenced in the scoped markdown — and that no caller
    in the scoped path invokes `build_script_index`.
    """
    # Arrange — a scoped skill citing exactly one doctor-marketplace invocation.
    skill = tmp_path / 'marketplace' / 'bundles' / 'qg-mi' / 'skills' / 'citing-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text(
        '---\nname: citing-skill\ndescription: cites one invocation\n---\n\n'
        '# Citing Skill\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py '
        'pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate --marketplace-root marketplace\n'
        '```\n'
        '\n## Canonical invocations\n\n### quality-gate\n\n'
        '```bash\npython3 .plan/execute-script.py '
        'pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate\n```\n'
    )

    derived: list[str] = []

    def _fake_derive(notation, executor):
        derived.append(notation)
        return None  # empty surface — no findings, but the call is recorded

    # Resolve a real executor location so `_resolve_executor` returns non-None;
    # the .plan/execute-script.py only needs to exist (derive is faked).
    plan_dir = tmp_path / 'marketplace' / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'execute-script.py').write_text('# stub executor\n')

    monkeypatch.setattr(_doctor_marketplace, 'derive_script_tree', _fake_derive)

    def _fail_build_index(*_args, **_kwargs):
        raise AssertionError('scoped path must NOT call build_script_index')

    # build_script_index is imported transitively; guard the symbol the scoped
    # helper would reach if it regressed to the eager path.
    if hasattr(_doctor_marketplace, 'build_script_index'):
        monkeypatch.setattr(_doctor_marketplace, 'build_script_index', _fail_build_index)

    # Act — call the scoped helper directly. marketplace_root is the parent of
    # bundles/ (the convention the manage-invocation helpers expect).
    marketplace_root = tmp_path / 'marketplace'
    _doctor_marketplace._scoped_manage_invocation(marketplace_root, [skill])

    # Assert — exactly the one referenced notation was derived, nothing else.
    assert derived == ['pm-plugin-development:plugin-doctor:doctor-marketplace'], (
        f'Scoped helper should derive only the referenced notation, got: {derived}'
    )


# =============================================================================
# Quality-gate manage-invocation build-failing regression (deliverable D2)
# =============================================================================
#
# cmd_quality_gate already aggregates scan_manage_invocation findings into
# all_issues and returns status: fail (→ main() exit 1) when any finding is
# present, but the gate test layer only pins this for scan_argparse_safety.
# These cases pin that a manage-invocation doc-drift finding *specifically*
# flows through to a build-failing gate verdict — so a refactor that dropped
# scan_manage_invocation from the gate's rule list (or stopped counting its
# findings toward status: fail) would fail loudly instead of passing CI
# silently (the no-op-gate class of lessons 2026-06-04-00-001 /
# 2026-06-04-00-002).
#
# The fixture mirrors the synthetic-executor model used by
# test_analyze_manage_invocation.py: a real .plan/execute-script.py shim maps a
# {notation} to an on-disk argparse script and forwards --help, so the gate's
# subprocess run derives the script's true surface and a documented invocation
# citing an unregistered sub-verb produces a manage-invocation-invalid finding.

# In-process executor shim — maps {notation} → script path via notation_map.json
# and dispatches the resolved script's argparse (forwarding --help). Mirrors the
# real .plan/execute-script.py executor that _resolve_executor discovers.
_MANAGE_INVOCATION_EXECUTOR_SHIM = """#!/usr/bin/env python3
import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

_MAP = json.loads((Path(__file__).parent / 'notation_map.json').read_text())


def main():
    if len(sys.argv) < 2:
        sys.exit(2)
    notation = sys.argv[1]
    target = _MAP.get(notation)
    if target is None:
        sys.stderr.write(f'Unknown notation: {notation}\\n')
        sys.exit(2)

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    rc = 0
    saved_argv = sys.argv
    sys.argv = [target, *sys.argv[2:]]
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            runpy.run_path(target, run_name='__main__')
    except SystemExit as exc:
        code = exc.code
        if code is None:
            rc = 0
        elif isinstance(code, int):
            rc = code
        else:
            err_buf.write(f'{code}\\n')
            rc = 1
    finally:
        sys.argv = saved_argv

    sys.stdout.write(out_buf.getvalue())
    sys.stderr.write(err_buf.getvalue())
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(rc)


if __name__ == '__main__':
    main()
"""

# A minimal argparse surface: a single ``qgate`` subcommand declaring its own
# ``add`` / ``list`` sub-verbs. ``qgate banana`` is therefore an unregistered
# sub-verb the manage-invocation rule flags as ``sub_verb_unknown``.
_MANAGE_INVOCATION_SCRIPT_SOURCE = (
    'import argparse\n'
    '\n'
    'def main():\n'
    '    parser = argparse.ArgumentParser()\n'
    "    subparsers = parser.add_subparsers(dest='cmd')\n"
    "    qgate = subparsers.add_parser('qgate')\n"
    "    qgate_subs = qgate.add_subparsers(dest='sub')\n"
    "    add_p = qgate_subs.add_parser('add')\n"
    "    add_p.add_argument('--plan-id', required=True)\n"
    "    list_p = qgate_subs.add_parser('list')\n"
    "    list_p.add_argument('--plan-id', required=True)\n"
    '    parser.parse_args()\n'
    '\n'
    "if __name__ == '__main__':\n"
    '    main()\n'
)

# The in-scope notation the fixture publishes (bundle:skill:script triple keyed
# off the script file stem). ``manage-syn`` is not in _EXCLUDED_SKILLS.
_MI_NOTATION = 'plan-marshall:manage-syn:manage-syn'


def _build_manage_invocation_drift_fixture(temp_root: Path) -> Path:
    """Build a fixture marketplace with a documented manage-invocation doc-drift.

    The skill owns an argparse script (so it is in-scope) and a SKILL.md whose
    body cites an unregistered sub-verb (``qgate banana``) for that script's
    notation — a ``manage-invocation-invalid`` (``sub_verb_unknown``) finding.
    A ``## Canonical invocations`` section is included so the only finding the
    gate surfaces is the doc-drift one (no stray ``missing-canonical-block``).
    A wired ``.plan/execute-script.py`` shim lets the gate's subprocess run
    derive the script's live ``--help`` surface.
    """
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    skill_dir = bundles_dir / 'plan-marshall' / 'skills' / 'manage-syn'
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True)

    plugin_dir = bundles_dir / 'plan-marshall' / '.claude-plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}))

    (scripts_dir / 'manage-syn.py').write_text(_MANAGE_INVOCATION_SCRIPT_SOURCE)

    # SKILL.md: a valid canonical block (so no missing-canonical-block finding)
    # plus a body line citing the unregistered ``qgate banana`` sub-verb.
    (skill_dir / 'SKILL.md').write_text(
        '---\n'
        'name: manage-syn\n'
        'description: A synthetic in-scope script-bearing skill\n'
        'user-invocable: false\n'
        '---\n'
        '\n'
        '# Manage Syn\n'
        '\n'
        'Run the bogus sub-verb:\n'
        '\n'
        '```bash\n'
        f'python3 .plan/execute-script.py {_MI_NOTATION} qgate banana --plan-id p1\n'
        '```\n'
        '\n'
        '## Canonical invocations\n'
        '\n'
        '### qgate\n'
        '\n'
        '```bash\n'
        f'python3 .plan/execute-script.py {_MI_NOTATION} qgate add --plan-id p1\n'
        '```\n'
    )

    # Wire the synthetic executor + notation map so build_script_index can
    # derive the surface via --help. _resolve_executor(marketplace_root.parent)
    # probes {marketplace}/.plan/execute-script.py first.
    plan_dir = temp_root / 'marketplace' / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'execute-script.py').write_text(_MANAGE_INVOCATION_EXECUTOR_SHIM)
    (plan_dir / 'notation_map.json').write_text(json.dumps({_MI_NOTATION: str(scripts_dir / 'manage-syn.py')}))

    return temp_root


def test_quality_gate_manage_invocation_drift_fails(tmp_path):
    """quality-gate exits build-failing on a manage-invocation doc-drift finding.

    Mirrors test_quality_gate_argparse_violation_fails for the
    scan_manage_invocation rule: a documented invocation citing an unregistered
    sub-verb makes cmd_quality_gate return status: fail (exit 1), the
    scan_manage_invocation rule_summary reports a non-zero findings count, and
    the corresponding manage-invocation-invalid finding appears in issues.
    """
    temp_root = _build_manage_invocation_drift_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides={
            'PM_MARKETPLACE_ROOT': str(temp_root / 'marketplace'),
            'PLAN_BASE_DIR': str(temp_root / '.plan'),
            'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_root / 'credentials'),
        },
    )
    assert result.returncode == 1, (
        f'Expected exit 1 on manage-invocation doc-drift fixture, got {result.returncode}: {result.stderr}'
    )

    data = parse_output(result)
    assert data['status'] == 'fail', f'Expected status: fail on doc-drift fixture, got: {data}'
    assert data['total_issues'] >= 1, 'Should report at least one finding'

    # The scan_manage_invocation rule_summary must report the non-zero count —
    # proves the rule ran and contributed to the build-failing verdict.
    summaries = {entry['rule']: entry['findings'] for entry in data['rules_run']}
    assert 'scan_manage_invocation' in summaries, (
        f'scan_manage_invocation must appear in rules_run, got: {data["rules_run"]}'
    )
    assert summaries['scan_manage_invocation'] >= 1, (
        f'scan_manage_invocation should report a non-zero findings count, got: {summaries["scan_manage_invocation"]}'
    )

    # The manage-invocation-invalid (sub_verb_unknown) finding must be present
    # in issues — the gate carried it through to the verdict, not merely counted.
    mi_findings = [i for i in data['issues'] if i.get('type') == 'manage-invocation-invalid']
    assert len(mi_findings) >= 1, (
        f'manage-invocation-invalid finding must appear in issues, got types: {[i.get("type") for i in data["issues"]]}'
    )
    reasons = {i.get('details', {}).get('reason') for i in mi_findings}
    assert 'sub_verb_unknown' in reasons, (
        f'The bogus ``qgate banana`` sub-verb should surface as sub_verb_unknown, got reasons: {reasons}'
    )


# =============================================================================
# Quality-gate scan_finalize_step_token registration (deliverable D2)
# =============================================================================
#
# cmd_quality_gate must register scan_finalize_step_token in its rule list so
# the finalize-step-token-mismatch rule runs as part of every quality-gate
# sweep. A refactor that dropped the rule from cmd_quality_gate (or never wired
# it) would let a drifted ``mark-step-done --step`` token reach main silently —
# exactly the PR #629 handshake-loop regression class. The observable
# registration signal is the scan_finalize_step_token entry in rules_run; the
# rule's own detection behaviour is pinned in test_analyze_finalize_step_token.py.


def test_quality_gate_registers_scan_finalize_step_token(tmp_path):
    """quality-gate enumerates scan_finalize_step_token in rules_run.

    Runs the gate over a clean fixture (no finalize-step skills → zero
    findings) and asserts the rule is registered. The clean fixture keeps the
    test about registration, not detection — detection is covered by the
    scanner's own test module.
    """
    temp_root = _build_clean_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides={
            'PM_MARKETPLACE_ROOT': str(temp_root / 'marketplace'),
            'PLAN_BASE_DIR': str(temp_root / '.plan'),
            'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_root / 'credentials'),
        },
    )
    assert result.returncode == 0, (
        f'Expected exit 0 on clean fixture, got {result.returncode}: {result.stderr}'
    )

    data = parse_output(result)
    rules = {entry['rule'] for entry in data['rules_run']}
    assert 'scan_finalize_step_token' in rules, (
        f'scan_finalize_step_token must appear in rules_run, got: {data["rules_run"]}'
    )


# =============================================================================
# --rules opt-in flag tests (replaces PM_ARGUMENT_NAMING_ENABLED env-var gate)
# =============================================================================
#
# Pins the breaking-refactor contract from deliverable D3: the argument-naming
# rule cluster (and the verb-chain cluster) under ``plugin-doctor analyze`` is
# gated OFF by default. Activation is via ``--rules <name>[,<name>...]`` or the
# two boolean aliases ``--enable-argument-naming`` / ``--enable-verb-chain``.
# The legacy ``PM_ARGUMENT_NAMING_ENABLED`` env-var must NOT trigger any rule
# activation — zero references remain in source per the deliverable's zero-hit
# grep gate.


# Load the analyze rules helpers directly so the small-pure-function tests do
# not need a subprocess round-trip per case.
_DOCTOR_SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')


def _load_doctor_marketplace():
    """Import ``doctor-marketplace.py`` as a module for direct-call tests.

    The script is invocation-side; importing it gives access to the pure-
    function helpers (``_parse_rules_flag``, ``_resolve_active_rules``) without
    paying subprocess overhead per case.
    """
    # Add the script directory to sys.path so internal ``from _x import ...``
    # statements resolve.
    if str(_DOCTOR_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_DOCTOR_SCRIPTS_DIR))
    return load_script_module(
        'pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py', '_doctor_marketplace_under_test'
    )


_doctor_marketplace = _load_doctor_marketplace()


class _FakeArgs:
    """Minimal Namespace stand-in for ``_resolve_active_rules`` tests."""

    def __init__(self, rules=None, enable_argument_naming=False, enable_verb_chain=False):
        self.rules = rules
        self.enable_argument_naming = enable_argument_naming
        self.enable_verb_chain = enable_verb_chain


class _FakeMarketplaceArgs:
    """Minimal Namespace stand-in for ``_resolve_marketplace_root`` tests.

    The helper reads only ``args.marketplace_root`` via ``getattr``, so a
    single attribute suffices to drive its three branches.
    """

    def __init__(self, marketplace_root=None):
        self.marketplace_root = marketplace_root


def test_parse_rules_flag_none_returns_empty_set():
    """``_parse_rules_flag(None)`` returns an empty frozenset (no opt-in)."""
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag(None)

    # Assert
    assert result == frozenset()


def test_parse_rules_flag_empty_string_returns_empty_set():
    """An empty ``--rules`` value is treated the same as absence."""
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag('')

    # Assert
    assert result == frozenset()


def test_parse_rules_flag_single_name_activates_that_rule():
    """``--rules argument_naming`` activates the argument-naming cluster."""
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag('argument_naming')

    # Assert
    assert result == frozenset({'argument_naming'})


def test_parse_rules_flag_comma_separated_activates_multiple():
    """``--rules argument_naming,verb_chain`` activates both clusters."""
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag('argument_naming,verb_chain')

    # Assert
    assert result == frozenset({'argument_naming', 'verb_chain'})


def test_parse_rules_flag_drops_unknown_names_but_keeps_valid(capsys):
    """Unknown rule names are dropped but valid tokens still activate.

    Valid tokens in the same invocation continue to enable their cluster —
    only the unknown tokens are rejected. See ``test_parse_rules_flag_warns_on_unknown_tokens``
    for the warning contract.
    """
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag('argument_naming,nonsense,verb_chain')

    # Assert
    assert result == frozenset({'argument_naming', 'verb_chain'})


def test_parse_rules_flag_warns_on_unknown_tokens(capsys):
    """Unknown ``--rules`` tokens trigger a stderr warning naming the rejected
    token alongside the accepted registry — silent drops mask user typos in a
    diagnostic tool. See lesson 2026-05-08-19-003 (PR #362 review).
    """
    # Arrange + Act
    _doctor_marketplace._parse_rules_flag('argument_naming,nonsense,verb_chain')

    # Assert — warning emitted on stderr, naming both the rejected token and
    # the accepted registry so users can correct the typo.
    captured = capsys.readouterr()
    assert 'WARNING' in captured.err, f'Expected warning on stderr, got: {captured.err!r}'
    assert 'nonsense' in captured.err, f'Warning should name the rejected token: {captured.err!r}'
    assert 'argument_naming' in captured.err, f'Warning should list accepted registry: {captured.err!r}'
    assert 'verb_chain' in captured.err, f'Warning should list accepted registry: {captured.err!r}'


def test_parse_rules_flag_no_warning_on_valid_tokens(capsys):
    """No warning is emitted when every ``--rules`` token is in the registry."""
    # Arrange + Act
    _doctor_marketplace._parse_rules_flag('argument_naming,verb_chain')

    # Assert — no warning on stderr when all tokens are accepted.
    captured = capsys.readouterr()
    assert 'WARNING' not in captured.err, f'Should NOT warn on valid tokens, got: {captured.err!r}'


def test_parse_rules_flag_trims_whitespace_around_names():
    """Names are stripped of surrounding whitespace before lookup."""
    # Arrange + Act
    result = _doctor_marketplace._parse_rules_flag(' argument_naming ,  verb_chain ')

    # Assert
    assert result == frozenset({'argument_naming', 'verb_chain'})


def test_resolve_active_rules_no_flags_returns_empty():
    """No ``--rules``, no aliases → no rules active (default-off contract)."""
    # Arrange
    args = _FakeArgs()

    # Act
    result = _doctor_marketplace._resolve_active_rules(args)

    # Assert
    assert result == frozenset()


def test_resolve_active_rules_enable_argument_naming_alias_activates_rule():
    """``--enable-argument-naming`` desugars into ``argument_naming``."""
    # Arrange
    args = _FakeArgs(enable_argument_naming=True)

    # Act
    result = _doctor_marketplace._resolve_active_rules(args)

    # Assert
    assert result == frozenset({'argument_naming'})


def test_resolve_active_rules_enable_verb_chain_alias_activates_rule():
    """``--enable-verb-chain`` desugars into ``verb_chain``."""
    # Arrange
    args = _FakeArgs(enable_verb_chain=True)

    # Act
    result = _doctor_marketplace._resolve_active_rules(args)

    # Assert
    assert result == frozenset({'verb_chain'})


def test_resolve_active_rules_rules_and_alias_union():
    """``--rules`` and aliases combine — the active set is their union."""
    # Arrange
    args = _FakeArgs(rules='argument_naming', enable_verb_chain=True)

    # Act
    result = _doctor_marketplace._resolve_active_rules(args)

    # Assert
    assert result == frozenset({'argument_naming', 'verb_chain'})


# =============================================================================
# verb_chain gating — TASK-13 (PR #362 review)
# =============================================================================
#
# The verb_chain rule cluster is registered in ``_OPTIN_RULE_NAMES`` and
# surfaced via ``--rules verb_chain`` / ``--enable-verb-chain``, so it must
# only dispatch when the caller opts in. Previously the rule ran
# unconditionally inside ``analyze_component``, creating a data-contract
# drift between registry and dispatch. These tests pin the gated dispatch
# at the unit-test level via a patched ``analyze_verb_chains`` spy.


def _load_doctor_analysis():
    """Import ``_doctor_analysis.py`` for direct-call tests."""
    if str(_DOCTOR_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_DOCTOR_SCRIPTS_DIR))
    return load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_doctor_analysis.py', '_doctor_analysis_under_test'
    )


def test_analyze_component_skips_verb_chain_when_inactive(tmp_path, monkeypatch):
    """``analyze_component`` does NOT call ``analyze_verb_chains`` without opt-in.

    Pins the dispatch-gating contract introduced for TASK-13: verb_chain is
    opt-in via ``--rules verb_chain`` / ``--enable-verb-chain``; absence
    must keep the analyzer silent (no calls, no findings).
    """
    # Arrange — fixture skill directory and spy.
    skill_dir = tmp_path / 'gated-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text('---\nname: gated-skill\ndescription: x\n---\n# Gated Skill\n')
    component = {'type': 'skill', 'path': str(skill_dir), 'skill_md_path': str(skill_dir / 'SKILL.md')}

    doctor_analysis = _load_doctor_analysis()
    calls = []

    def _spy(skill_dir_arg):
        calls.append(skill_dir_arg)
        return []

    monkeypatch.setattr(doctor_analysis, 'analyze_verb_chains', _spy)

    # Act — no active rules.
    doctor_analysis.analyze_component(component)

    # Assert — spy never called.
    assert calls == [], f'verb_chain should not run without opt-in, but spy was called: {calls!r}'


def test_analyze_component_runs_verb_chain_when_active(tmp_path, monkeypatch):
    """``analyze_component`` dispatches verb_chain when ``active_rules`` opts in.

    Pins the active-path of the TASK-13 contract: with ``verb_chain`` in the
    active rule set, the analyzer is invoked exactly once per skill.
    """
    # Arrange
    skill_dir = tmp_path / 'opted-in-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text('---\nname: opted-in-skill\ndescription: x\n---\n# Opted In Skill\n')
    component = {'type': 'skill', 'path': str(skill_dir), 'skill_md_path': str(skill_dir / 'SKILL.md')}

    doctor_analysis = _load_doctor_analysis()
    calls = []

    def _spy(skill_dir_arg):
        calls.append(skill_dir_arg)
        return []

    monkeypatch.setattr(doctor_analysis, 'analyze_verb_chains', _spy)

    # Act
    doctor_analysis.analyze_component(component, active_rules=frozenset({'verb_chain'}))

    # Assert — spy called exactly once with the skill dir.
    assert len(calls) == 1, f'verb_chain should run exactly once when opted in, calls={calls!r}'


# =============================================================================
# Subprocess-level tests: argparse surface and PM_ARGUMENT_NAMING_ENABLED inertness
# =============================================================================


def test_analyze_help_documents_rules_flag():
    """``analyze --help`` mentions the ``--rules`` flag and its aliases.

    Pins the user-facing CLI surface — if the flag is renamed/removed, this
    test catches it before the change reaches users.
    """
    # Arrange + Act
    result = run_script(SCRIPT_PATH, 'analyze', '--help')

    # Assert
    assert result.returncode == 0, f'analyze --help failed: {result.stderr}'
    help_text = result.stdout
    assert '--rules' in help_text, f'--rules not documented in analyze --help: {help_text!r}'
    assert '--enable-argument-naming' in help_text, '--enable-argument-naming alias not documented'
    assert '--enable-verb-chain' in help_text, '--enable-verb-chain alias not documented'


# Real-tree test_pm_argument_naming_enabled_env_var_no_longer_recognised (2 real
# analyze subprocesses) was removed — its zero-references contract is fully covered
# by the source-grep test_zero_hit_grep_pm_argument_naming_enabled_in_source below.


def test_zero_hit_grep_pm_argument_naming_enabled_in_source():
    """Zero source-tree references to ``PM_ARGUMENT_NAMING_ENABLED`` remain.

    The deliverable's success criterion: ``PM_ARGUMENT_NAMING_ENABLED does not
    appear in the post-change source tree (zero-hit grep).`` This test scans
    the marketplace bundles for any string match and fails when one is found.
    The test directory is intentionally excluded — this very file mentions the
    legacy name in its assertion strings.
    """
    if not marketplace_available():
        pytest.skip('Real marketplace not available')

    # Arrange
    marketplace_root = MARKETPLACE_ROOT
    legacy_token = 'PM_ARGUMENT' + '_NAMING_ENABLED'  # split to avoid self-hit

    # Act
    hits = []
    for path in marketplace_root.rglob('*'):
        if not path.is_file():
            continue
        # Skip binary-ish suffixes that we never expect to source-match.
        if path.suffix in {'.pyc', '.png', '.jpg', '.so', '.zip'}:
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        if legacy_token in content:
            hits.append(str(path.relative_to(marketplace_root)))

    # Assert
    assert hits == [], (
        f'Found {len(hits)} residual reference(s) to {legacy_token} in marketplace tree: {hits}. '
        f'The breaking-refactor contract per lesson 2026-05-08-19-003 requires zero hits.'
    )


# =============================================================================
# _resolve_marketplace_root error-containment tests (deliverable 1)
# =============================================================================
#
# TASK-1 added the ``_resolve_marketplace_root`` helper so every verb shares a
# single bad-input boundary: a ``ValueError`` from ``find_marketplace_root``
# (the supplied ``--marketplace-root`` / ``PM_MARKETPLACE_ROOT`` override lacks
# a ``bundles/`` subdirectory) becomes a structured
# ``{status: error, error: invalid_marketplace_root}`` dict instead of an
# uncaught traceback that crashes the verb. These tests pin both the helper's
# branch contract (direct-call) and the end-to-end no-traceback CLI behaviour.
#
# Note: the LOW-LEVEL ``find_marketplace_root`` RAISES ``ValueError`` on a bad
# override — that contract is pinned by
# ``test_marketplace_root_invalid_path_errors_clearly`` above. THIS section
# pins the verb-entry wrapper that CONTAINS that raise.


def test_resolve_marketplace_root_invalid_override_returns_structured_error(tmp_path, monkeypatch):
    """An override lacking ``bundles/`` is contained as a structured error dict.

    ``find_marketplace_root`` raises ``ValueError`` for such an override;
    ``_resolve_marketplace_root`` must catch it and return
    ``{status: error, error: invalid_marketplace_root}`` carrying the
    underlying message verbatim — never let the raise escape.
    """
    # Arrange — tmp_path has no bundles/ subdir, so the override is invalid.
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    assert not (tmp_path / 'bundles').exists(), 'Test precondition: tmp_path must lack bundles/'
    args = _FakeMarketplaceArgs(marketplace_root=str(tmp_path))

    # Act
    result = _doctor_marketplace._resolve_marketplace_root(args)

    # Assert — structured error envelope, not a Path and not a raise.
    assert isinstance(result, dict), f'Expected an error dict, got: {result!r}'
    assert result['status'] == 'error', f'Expected status: error, got: {result}'
    assert result['error'] == 'invalid_marketplace_root', f'Expected invalid_marketplace_root, got: {result}'
    # The offending-path message from the underlying ValueError is carried through.
    assert 'bundles' in result['message'], f'Message should reference the bundles/ requirement: {result}'
    assert str(tmp_path) in result['message'], f'Message should reference the offending path: {result}'


def test_resolve_marketplace_root_valid_override_returns_bundles_path(tmp_path, monkeypatch):
    """A valid override resolves to the ``{override}/bundles`` Path (success branch)."""
    # Arrange — a fake marketplace with a bundles/ subdir.
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    fake_marketplace = tmp_path / 'marketplace'
    (fake_marketplace / 'bundles').mkdir(parents=True)
    args = _FakeMarketplaceArgs(marketplace_root=str(fake_marketplace))

    # Act
    result = _doctor_marketplace._resolve_marketplace_root(args)

    # Assert — the Path to bundles/, not an error dict.
    assert not isinstance(result, dict), f'Expected a Path on success, got an error dict: {result!r}'
    assert result == fake_marketplace / 'bundles', f'Expected {fake_marketplace / "bundles"}, got {result}'


def test_resolve_marketplace_root_not_found_returns_structured_error(monkeypatch):
    """A falsy ``find_marketplace_root`` return is contained as ``error: not_found``.

    When no marketplace candidate exists, ``find_marketplace_root`` returns
    ``None``; ``_resolve_marketplace_root`` must translate that into a
    structured ``{status: error, error: not_found}`` envelope rather than
    returning ``None`` for callers to mishandle.
    """
    # Arrange — patch the module's find_marketplace_root to return None.
    monkeypatch.setattr(_doctor_marketplace, 'find_marketplace_root', lambda _override: None)
    args = _FakeMarketplaceArgs(marketplace_root=None)

    # Act
    result = _doctor_marketplace._resolve_marketplace_root(args)

    # Assert
    assert isinstance(result, dict), f'Expected an error dict, got: {result!r}'
    assert result['status'] == 'error', f'Expected status: error, got: {result}'
    assert result['error'] == 'not_found', f'Expected not_found, got: {result}'


def test_invalid_marketplace_root_cli_no_traceback(tmp_path):
    """An invalid ``--marketplace-root`` on a verb yields structured TOON, no traceback.

    End-to-end: ``quality-gate --marketplace-root {bad}`` (a directory without
    a ``bundles/`` subdir) must exit 1 with a structured
    ``invalid_marketplace_root`` TOON error and produce NO Python ``Traceback``
    on stderr — the crash this deliverable fixes.
    """
    # Arrange — bad override: tmp_path has no bundles/ subdir.
    bad_root = tmp_path / 'no-bundles-here'
    bad_root.mkdir()
    assert not (bad_root / 'bundles').exists(), 'Test precondition: override must lack bundles/'

    # Act — run the verb against the bad override. PM_MARKETPLACE_ROOT must be
    # unset so the --marketplace-root arg is the resolution input under test.
    result = run_script(SCRIPT_PATH, 'quality-gate', '--marketplace-root', str(bad_root))

    # Assert — contained failure, not a crash.
    assert result.returncode == 1, f'Expected exit 1 on invalid --marketplace-root, got {result.returncode}'
    assert 'Traceback' not in result.stderr, f'Verb must not crash with a traceback, got stderr: {result.stderr!r}'

    data = parse_output(result)
    assert data['status'] == 'error', f'Expected status: error, got: {data}'
    assert data['error'] == 'invalid_marketplace_root', f'Expected invalid_marketplace_root, got: {data}'


# =============================================================================
# Dispatcher-guard regression: bad root → structured TOON, never a Traceback (deliverable 2)
# =============================================================================
#
# The pre-fix defect is only observable end-to-end: the uncaught ``ValueError``
# Traceback surfaced when the *real* ``main()`` dispatcher ran a verb against a
# bad ``--marketplace-root``/``PM_MARKETPLACE_ROOT``. The D1 unit tests of
# ``_resolve_marketplace_root`` cannot prove the dispatcher-level ``@safe_main``
# backstop on ``main()`` nor the absence of a raw Traceback on the process
# streams — that needs a subprocess round-trip through the script's true
# entrypoint. ``test_invalid_marketplace_root_cli_no_traceback`` (D1, above)
# pins the ``--marketplace-root`` *flag* path; the two tests below pin the
# complementary surface this deliverable owns: the ``PM_MARKETPLACE_ROOT``
# *env-var* override path, and the dispatcher-guard assertion that no
# ``Traceback (most recent call last)`` appears on the COMBINED stdout+stderr
# (the @safe_main backstop, not merely the per-verb catch).


def test_bad_marketplace_root_env_var_structured_error_no_traceback(tmp_path):
    """``PM_MARKETPLACE_ROOT`` at a bundles-less dir → structured TOON on stdout, exit 1.

    Exercises the env-var override resolution path (distinct from the
    ``--marketplace-root`` flag path pinned by D1's
    ``test_invalid_marketplace_root_cli_no_traceback``): the real ``quality-gate``
    subprocess entrypoint must emit a parseable ``invalid_marketplace_root`` TOON
    on stdout, exit 1, and print NO Python ``Traceback`` on either stream.
    """
    # Arrange — PM_MARKETPLACE_ROOT points at a dir lacking bundles/.
    bad_root = tmp_path / 'no-bundles-marketplace'
    bad_root.mkdir()
    assert not (bad_root / 'bundles').exists(), 'Test precondition: env-var root must lack bundles/'

    # Act — drive resolution via the env var (no --marketplace-root flag).
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides={
            'PM_MARKETPLACE_ROOT': str(bad_root),
            'PLAN_BASE_DIR': str(tmp_path / '.plan'),
            'PLAN_MARSHALL_CREDENTIALS_DIR': str(tmp_path / 'credentials'),
        },
    )

    # Assert — contained failure: exit 1, structured TOON on stdout, no crash.
    assert result.returncode == 1, f'Expected exit 1 on bad PM_MARKETPLACE_ROOT, got {result.returncode}'
    assert 'Traceback' not in result.stderr, f'Verb must not crash with a traceback, got stderr: {result.stderr!r}'

    # The structured error must be on STDOUT (output_toon target), not stderr.
    data = parse_toon(result.stdout)
    assert data['status'] == 'error', f'Expected status: error on stdout, got: {data}'
    assert data['error'] == 'invalid_marketplace_root', f'Expected invalid_marketplace_root, got: {data}'


def test_bad_marketplace_root_no_traceback_in_combined_streams(tmp_path):
    """The @safe_main dispatcher backstop leaves NO ``Traceback`` on either stream.

    Asserts the dispatcher-guard contract beyond the per-verb catch: the exact
    Python crash banner ``Traceback (most recent call last)`` must be absent from
    the COMBINED stdout+stderr for the bad-root invocation — proving ``main()``
    never lets an uncaught exception reach the process streams as a raw traceback.
    """
    # Arrange — bad --marketplace-root flag (dir without bundles/).
    bad_root = tmp_path / 'no-bundles-flag-root'
    bad_root.mkdir()
    assert not (bad_root / 'bundles').exists(), 'Test precondition: override must lack bundles/'

    # Act
    result = run_script(SCRIPT_PATH, 'quality-gate', '--marketplace-root', str(bad_root))

    # Assert — the raw crash banner must not appear on EITHER stream.
    combined = result.stdout + result.stderr
    assert 'Traceback (most recent call last)' not in combined, (
        f'Dispatcher guard must suppress the raw crash banner on both streams, got: {combined!r}'
    )
    # And the failure is still the contained, parseable one.
    assert result.returncode == 1, f'Expected exit 1, got {result.returncode}'
    data = parse_toon(result.stdout)
    assert data['error'] == 'invalid_marketplace_root', f'Expected invalid_marketplace_root, got: {data}'


# =============================================================================
# Sibling-cross-reference analyzer wiring (deliverable D3)
# =============================================================================
#
# doctor-marketplace.py must call BOTH analyze_markdown_link_bare_filename and
# analyze_toon_prose_status_conflation from cmd_analyze (issue stream) AND from
# cmd_quality_gate (build gate). A refactor that dropped either call site would
# let a bare ``name.md`` sibling reference or a conflated ``status: {code}``
# prose token reach main silently. The observable signals: the rule name in
# cmd_quality_gate's rules_run enumeration (registration), and the rule-typed
# issue in cmd_analyze's all_issues over a positive fixture (called-and-fired).
# Each analyzer's own detection behaviour is pinned in its dedicated module
# (test_analyze_markdown_link_bare_filename.py / test_analyze_toon_prose_status_conflation.py).


def _build_bare_filename_fixture(temp_root: Path) -> Path:
    """Build a fixture marketplace carrying a MARKDOWN_LINK_BARE_FILENAME defect.

    The skill body holds a cross-reference list whose first item is a navigable
    ``.md`` link and whose second item is a bare plain-text ``config.md`` token —
    the odd-one-out plain-text cross-reference (pattern 2) the narrowed rule
    flags. Any bundle name works — the analyzer scans every bundle's
    skills/agents/commands tree.
    """
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)
    bundle = bundles_dir / 'xref-bundle'
    bundle.mkdir()

    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir()
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'xref-bundle', 'version': '1.0.0'}))

    skill_dir = bundle / 'skills' / 'bare-link-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: bare-link-skill\ndescription: A skill citing a bare filename\n'
        'user-invocable: false\n---\n\n# Bare Link Skill\n\nSee also:\n\n'
        '- [Setup](../setup.md)\n- config.md\n'
    )
    return temp_root


def _build_status_conflation_fixture(temp_root: Path) -> Path:
    """Build a fixture marketplace whose plan-marshall skill prose conflates ``status``.

    The skill body carries an inline-code ``status: blocked`` token that conflates
    the two-tier TOON error envelope (on failure ``status`` is ALWAYS ``error``;
    the specific code lives in the ``error`` field) — the
    MANAGE_STATUS_PROSE_CONFLATION defect. The bundle MUST be named
    ``plan-marshall`` because that analyzer scopes its scan to the plan-marshall
    bundle only (TOON contracts are plan-marshall-owned prose).
    """
    bundles_dir = temp_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)
    bundle = bundles_dir / 'plan-marshall'
    bundle.mkdir()

    plugin_dir = bundle / '.claude-plugin'
    plugin_dir.mkdir()
    (plugin_dir / 'plugin.json').write_text(json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}))

    skill_dir = bundle / 'skills' / 'conflation-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(
        '---\nname: conflation-skill\ndescription: A skill conflating status prose\n'
        'user-invocable: false\n---\n\n# Conflation Skill\n\n'
        'The verb returns `status: blocked` on a guard failure.\n'
    )
    return temp_root


def test_quality_gate_registers_analyze_markdown_link_bare_filename(tmp_path):
    """quality-gate enumerates analyze_markdown_link_bare_filename in rules_run.

    Runs the gate over a clean fixture (no bare-filename defect → zero findings)
    and asserts the rule is registered. The clean fixture keeps the test about
    registration in cmd_quality_gate, not detection.
    """
    temp_root = _build_clean_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 0, f'Expected exit 0 on clean fixture, got {result.returncode}: {result.stderr}'

    data = parse_output(result)
    rules = {entry['rule'] for entry in data['rules_run']}
    assert 'analyze_markdown_link_bare_filename' in rules, (
        f'analyze_markdown_link_bare_filename must appear in rules_run, got: {data["rules_run"]}'
    )


def test_quality_gate_registers_analyze_toon_prose_status_conflation(tmp_path):
    """quality-gate enumerates analyze_toon_prose_status_conflation in rules_run.

    Runs the gate over a clean fixture (no status-conflation defect → zero
    findings) and asserts the rule is registered. The clean fixture keeps the
    test about registration in cmd_quality_gate, not detection.
    """
    temp_root = _build_clean_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 0, f'Expected exit 0 on clean fixture, got {result.returncode}: {result.stderr}'

    data = parse_output(result)
    rules = {entry['rule'] for entry in data['rules_run']}
    assert 'analyze_toon_prose_status_conflation' in rules, (
        f'analyze_toon_prose_status_conflation must appear in rules_run, got: {data["rules_run"]}'
    )


def test_quality_gate_bare_filename_defect_fails(tmp_path):
    """quality-gate exits build-failing on a MARKDOWN_LINK_BARE_FILENAME defect.

    Proves the analyzer is not merely registered but contributes to the verdict:
    a bare ``config.md`` token makes cmd_quality_gate return status: fail (exit 1),
    the analyze_markdown_link_bare_filename rule_summary reports a non-zero count,
    and the MARKDOWN_LINK_BARE_FILENAME finding appears in issues.
    """
    temp_root = _build_bare_filename_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 1, (
        f'Expected exit 1 on bare-filename defect fixture, got {result.returncode}: {result.stderr}'
    )

    data = parse_output(result)
    assert data['status'] == 'fail', f'Expected status: fail on bare-filename fixture, got: {data}'
    summaries = {entry['rule']: entry['findings'] for entry in data['rules_run']}
    assert summaries.get('analyze_markdown_link_bare_filename', 0) >= 1, (
        f'analyze_markdown_link_bare_filename should report a non-zero count, got: {data["rules_run"]}'
    )
    types = {i.get('type') for i in data['issues']}
    assert 'MARKDOWN_LINK_BARE_FILENAME' in types, (
        f'MARKDOWN_LINK_BARE_FILENAME finding must appear in issues, got types: {types}'
    )


def test_quality_gate_status_conflation_defect_fails(tmp_path):
    """quality-gate exits build-failing on a MANAGE_STATUS_PROSE_CONFLATION defect.

    Proves the analyzer contributes to the verdict: an inline-code
    ``status: blocked`` token in plan-marshall skill prose makes cmd_quality_gate
    return status: fail (exit 1), the analyze_toon_prose_status_conflation
    rule_summary reports a non-zero count, and the MANAGE_STATUS_PROSE_CONFLATION
    finding appears in issues.
    """
    temp_root = _build_status_conflation_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'quality-gate',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 1, (
        f'Expected exit 1 on status-conflation defect fixture, got {result.returncode}: {result.stderr}'
    )

    data = parse_output(result)
    assert data['status'] == 'fail', f'Expected status: fail on status-conflation fixture, got: {data}'
    summaries = {entry['rule']: entry['findings'] for entry in data['rules_run']}
    assert summaries.get('analyze_toon_prose_status_conflation', 0) >= 1, (
        f'analyze_toon_prose_status_conflation should report a non-zero count, got: {data["rules_run"]}'
    )
    types = {i.get('type') for i in data['issues']}
    assert 'MANAGE_STATUS_PROSE_CONFLATION' in types, (
        f'MANAGE_STATUS_PROSE_CONFLATION finding must appear in issues, got types: {types}'
    )


def _collect_categorized_types(data):
    """Collect issue ``type`` values from cmd_analyze's categorized buckets.

    Marketplace-wide analyzer findings (e.g. MARKDOWN_LINK_BARE_FILENAME) are not
    per-component ``analysis`` rows — cmd_analyze routes its ``all_issues`` through
    ``categorize_all_issues`` into the categorized_safe/risky/unfixable buckets.
    Non-fixable findings land in categorized_unfixable. Each entry may arrive as a
    dict or a JSON-string after TOON round-tripping, so both shapes are handled.
    """
    types = set()
    for bucket in ('categorized_safe', 'categorized_risky', 'categorized_unfixable'):
        for entry in data.get(bucket, []):
            if isinstance(entry, str):
                entry = json.loads(entry)
            issue_type = entry.get('type')
            if issue_type is not None:
                types.add(issue_type)
    return types


def test_analyze_calls_markdown_link_bare_filename(tmp_path):
    """cmd_analyze calls analyze_markdown_link_bare_filename — its finding surfaces.

    Runs ``analyze`` over a positive fixture and asserts the
    MARKDOWN_LINK_BARE_FILENAME issue appears in the analyze output stream
    (the categorized buckets, where marketplace-wide non-fixable findings land).
    The issue can only appear if cmd_analyze invoked the analyzer, so this pins
    the cmd_analyze call site (distinct from the cmd_quality_gate registration above).
    """
    temp_root = _build_bare_filename_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'analyze',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 0, f'Analyze failed: {result.stderr}'

    data = parse_output(result)
    types = _collect_categorized_types(data)
    assert 'MARKDOWN_LINK_BARE_FILENAME' in types, (
        f'cmd_analyze must surface MARKDOWN_LINK_BARE_FILENAME, got types: {types}'
    )


def test_analyze_calls_toon_prose_status_conflation(tmp_path):
    """cmd_analyze calls analyze_toon_prose_status_conflation — its finding surfaces.

    Runs ``analyze`` over a positive fixture (plan-marshall bundle) and asserts
    the MANAGE_STATUS_PROSE_CONFLATION issue appears in the analyze output stream
    (the categorized buckets, where marketplace-wide non-fixable findings land).
    The issue can only appear if cmd_analyze invoked the analyzer, so this pins
    the cmd_analyze call site.
    """
    temp_root = _build_status_conflation_fixture(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'analyze',
        env_overrides=_quality_gate_env(temp_root),
    )
    assert result.returncode == 0, f'Analyze failed: {result.stderr}'

    data = parse_output(result)
    types = _collect_categorized_types(data)
    assert 'MANAGE_STATUS_PROSE_CONFLATION' in types, (
        f'cmd_analyze must surface MANAGE_STATUS_PROSE_CONFLATION, got types: {types}'
    )


# =============================================================================
# Main
# =============================================================================
