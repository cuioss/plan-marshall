#!/usr/bin/env python3
"""Tests for doctor-marketplace.py - batch marketplace analysis and fixing.

Tests the hybrid Phase 1 script that provides automated batch operations:
- scan: Discover all components
- analyze: Batch analyze for issues
- fix: Apply safe fixes automatically
- report: Generate comprehensive report
"""

import json
import shutil
import tempfile
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py')
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'


def marketplace_available():
    """Check if marketplace is available for integration tests."""
    return MARKETPLACE_ROOT.is_dir() and any(MARKETPLACE_ROOT.iterdir())


# =============================================================================
# Help and Basic Tests
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'scan' in combined, 'scan subcommand in help'
    assert 'analyze' in combined, 'analyze subcommand in help'
    assert 'fix' in combined, 'fix subcommand in help'
    assert 'report' in combined, 'report subcommand in help'


def test_no_command_shows_help():
    """Test that running without command shows help."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode != 0, 'Should return error without command'
    combined = result.stdout + result.stderr
    assert 'scan' in combined or 'usage' in combined.lower(), 'Should show usage information'


# =============================================================================
# Scan Subcommand Tests
# =============================================================================


def test_scan_help():
    """Test scan --help is available."""
    result = run_script(SCRIPT_PATH, 'scan', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'


def test_scan_returns_valid_json():
    """Test scan returns valid JSON structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    assert result.returncode == 0, f'Scan failed: {result.stderr}'

    data = result.json()
    assert data is not None, 'Should return valid JSON'
    assert 'bundles' in data, 'Should have bundles field'
    assert 'total_bundles' in data, 'Should have total_bundles field'
    assert 'total_components' in data, 'Should have total_components field'


def test_scan_finds_bundles():
    """Test scan finds marketplace bundles."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    data = result.json()

    assert data['total_bundles'] > 0, 'Should find at least one bundle'
    assert len(data['bundles']) == data['total_bundles'], 'Bundle list length should match total_bundles'


def test_scan_bundle_structure():
    """Test scan returns correct bundle structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    data = result.json()

    for bundle in data['bundles']:
        assert 'name' in bundle, 'Bundle should have name'
        assert 'path' in bundle, 'Bundle should have path'
        assert 'components' in bundle, 'Bundle should have components'
        assert 'counts' in bundle, 'Bundle should have counts'

        components = bundle['components']
        assert 'agents' in components, 'Components should have agents'
        assert 'commands' in components, 'Components should have commands'
        assert 'skills' in components, 'Components should have skills'
        assert 'scripts' in components, 'Components should have scripts'


def test_scan_bundle_filter():
    """Test scan with bundle filter."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    # First get a valid bundle name
    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    data = result.json()
    if not data['bundles']:
        return  # No bundles to test

    first_bundle = data['bundles'][0]['name']

    # Now filter to just that bundle
    result = run_script(SCRIPT_PATH, 'scan', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    filtered = result.json()

    assert filtered['total_bundles'] == 1, 'Should have exactly one bundle'
    assert filtered['bundles'][0]['name'] == first_bundle, f'Should be {first_bundle}'


# =============================================================================
# Analyze Subcommand Tests
# =============================================================================


def test_analyze_help():
    """Test analyze --help is available."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'type' in combined.lower(), 'Help should mention type option'


def test_analyze_returns_valid_json():
    """Test analyze returns valid JSON structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    # Analyze just one bundle for speed
    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    assert result.returncode == 0, f'Analyze failed: {result.stderr}'

    data = result.json()
    assert data is not None, 'Should return valid JSON'
    assert 'analysis' in data, 'Should have analysis field'
    assert 'summary' in data, 'Should have summary field'
    assert 'categorized' in data, 'Should have categorized field'


def test_analyze_summary_structure():
    """Test analyze summary has correct structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    data = result.json()

    summary = data['summary']
    assert 'total_components' in summary, 'Summary should have total_components'
    assert 'total_issues' in summary, 'Summary should have total_issues'
    assert 'safe_fixes' in summary, 'Summary should have safe_fixes'
    assert 'risky_fixes' in summary, 'Summary should have risky_fixes'
    assert 'unfixable' in summary, 'Summary should have unfixable'


def test_analyze_categorized_structure():
    """Test analyze categorized has correct structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    data = result.json()

    categorized = data['categorized']
    assert 'safe' in categorized, 'Categorized should have safe'
    assert 'risky' in categorized, 'Categorized should have risky'
    assert 'unfixable' in categorized, 'Categorized should have unfixable'


def test_analyze_type_filter():
    """Test analyze with type filter."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, '--type', 'agents', cwd=str(PROJECT_ROOT))
    data = result.json()

    # All analyzed components should be agents
    for item in data['analysis']:
        comp_type = item.get('component', {}).get('type')
        assert comp_type == 'agent', f'Expected agent, got {comp_type}'


# =============================================================================
# Fix Subcommand Tests
# =============================================================================


def test_fix_help():
    """Test fix --help is available."""
    result = run_script(SCRIPT_PATH, 'fix', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'dry-run' in combined.lower(), 'Help should mention dry-run option'


def test_fix_dry_run_returns_valid_json():
    """Test fix --dry-run returns valid JSON."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'fix', '--bundles', first_bundle, '--dry-run', cwd=str(PROJECT_ROOT))
    # Should succeed even if no fixes needed
    assert result.returncode == 0, f'Fix dry-run failed: {result.stderr}'

    data = result.json()
    assert data is not None, 'Should return valid JSON'
    assert 'status' in data, 'Should have status field'
    assert 'dry_run' in data, 'Should have dry_run field'
    assert data['dry_run'] is True, 'dry_run should be True'


def test_fix_dry_run_no_changes():
    """Test fix --dry-run does not modify files."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    # Get a snapshot of file modification times
    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']
    bundle_path = PROJECT_ROOT / 'marketplace' / 'bundles' / first_bundle

    # Get modification times before
    mtimes_before = {}
    for md_file in bundle_path.rglob('*.md'):
        mtimes_before[str(md_file)] = md_file.stat().st_mtime

    # Run fix with dry-run
    result = run_script(SCRIPT_PATH, 'fix', '--bundles', first_bundle, '--dry-run', cwd=str(PROJECT_ROOT))

    # Verify no files changed
    for md_file in bundle_path.rglob('*.md'):
        mtime_after = md_file.stat().st_mtime
        path_str = str(md_file)
        if path_str in mtimes_before:
            assert mtimes_before[path_str] == mtime_after, f'File modified during dry-run: {md_file}'


# =============================================================================
# Report Subcommand Tests
# =============================================================================


def test_report_help():
    """Test report --help is available."""
    result = run_script(SCRIPT_PATH, 'report', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'output' in combined.lower(), 'Help should mention output option'


def test_report_returns_valid_json():
    """Test report returns valid JSON structure with directory path."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    assert result.returncode == 0, f'Report failed: {result.stderr}'

    data = result.json()
    assert data is not None, 'Should return valid JSON'
    assert 'status' in data, 'Should have status field'
    assert data['status'] == 'success', 'Status should be success'
    assert 'report_dir' in data, 'Should have report_dir field'
    assert 'report_file' in data, 'Should have report_file field'
    assert 'findings_file' in data, 'Should have findings_file field'
    assert 'summary' in data, 'Should have summary field'
    assert data['report_dir'].endswith('.plan/temp/plugin-doctor-report'), (
        f'Report dir should end with .plan/temp/plugin-doctor-report, got {data["report_dir"]}'
    )


def test_report_summary_structure():
    """Test report summary has correct structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    data = result.json()

    # Summary is included in stdout response
    summary = data['summary']
    assert 'total_bundles' in summary, 'Summary should have total_bundles'
    assert 'total_components' in summary, 'Summary should have total_components'
    assert 'total_issues' in summary, 'Summary should have total_issues'
    assert 'safe_fixes' in summary, 'Summary should have safe_fixes'
    assert 'risky_fixes' in summary, 'Summary should have risky_fixes'


def test_report_has_llm_review_items():
    """Test report file includes LLM review items."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle, cwd=str(PROJECT_ROOT))
    response = result.json()

    # Read the actual report file
    report_path = Path(PROJECT_ROOT) / response['report_file']
    assert report_path.exists(), f'Report file should exist: {report_path}'

    with open(report_path) as f:
        report_data = json.load(f)

    assert 'llm_review_items' in report_data, 'Report should have llm_review_items'
    assert isinstance(report_data['llm_review_items'], list), 'llm_review_items should be a list'


def test_report_to_custom_dir():
    """Test report outputs to custom directory when --output specified."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan', cwd=str(PROJECT_ROOT))
    scan_data = result.json()
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    # Create a temp directory for the custom output
    output_dir = tempfile.mkdtemp()

    try:
        result = run_script(
            SCRIPT_PATH, 'report', '--bundles', first_bundle, '--output', output_dir, cwd=str(PROJECT_ROOT)
        )
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        # Verify directory contains timestamped JSON file
        json_files = list(Path(output_dir).glob('*-report.json'))
        assert len(json_files) == 1, f'Should have exactly one report JSON file, found: {json_files}'
        json_path = json_files[0]

        with open(json_path) as f:
            data = json.load(f)
        assert 'summary' in data, 'File should contain valid report'
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


# =============================================================================
# Integration Tests with Fixture
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


def test_fixture_scan():
    """Test scan with fixture marketplace."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'scan', cwd=str(temp_dir))
        assert result.returncode == 0, f'Scan failed: {result.stderr}'

        data = result.json()
        assert data['total_bundles'] == 1, 'Should find one bundle'
        assert data['bundles'][0]['name'] == 'test-bundle', 'Should be test-bundle'
    finally:
        fixture.cleanup()


def test_fixture_analyze_finds_issues():
    """Test analyze finds issues in fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'analyze', cwd=str(temp_dir))
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = result.json()
        # Should find at least one issue (Rule 6 - Task in agent)
        assert data['summary']['total_issues'] > 0, 'Should find issues in test fixture'
    finally:
        fixture.cleanup()


def test_fixture_fix_dry_run():
    """Test fix dry-run with fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'fix', '--dry-run', cwd=str(temp_dir))
        assert result.returncode == 0, f'Fix dry-run failed: {result.stderr}'

        data = result.json()
        assert data['dry_run'] is True, 'Should be dry run'
    finally:
        fixture.cleanup()


def test_fixture_report():
    """Test report with fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'report', cwd=str(temp_dir))
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        response = result.json()
        assert response['status'] == 'success', 'Status should be success'
        assert response['summary']['total_bundles'] == 1, 'Should have one bundle'
        assert 'report_dir' in response, 'Should have report_dir'
        assert 'report_file' in response, 'Should have report_file'
        assert 'findings_file' in response, 'Should have findings_file'

        # Read and verify report file
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


# =============================================================================
# Rule 11 Detection Tests
# =============================================================================


def test_fixture_analyze_detects_rule_11():
    """Test analyze detects Rule 11 violation (agent tools missing Skill)."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    # Add an agent with tools but no Skill
    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'no-skill-agent.md').write_text(
        '---\nname: no-skill-agent\ndescription: Agent without Skill\ntools: Read, Write, Edit\n---\n\n# No Skill Agent\n'
    )

    try:
        result = run_script(SCRIPT_PATH, 'analyze', cwd=str(temp_dir))
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = result.json()
        # Find rule-11-violation in all issues
        all_issues = []
        for item in data['analysis']:
            all_issues.extend(item.get('issues', []))

        rule_11_issues = [i for i in all_issues if i['type'] == 'rule-11-violation']
        assert len(rule_11_issues) >= 1, (
            f'Should detect rule-11-violation, got issues: {[i["type"] for i in all_issues]}'
        )
        assert rule_11_issues[0]['fixable'] is True, 'Rule 11 should be fixable'
        assert rule_11_issues[0]['severity'] == 'warning', 'Rule 11 should be warning severity'
    finally:
        fixture.cleanup()


def test_fixture_analyze_no_rule_11_with_skill():
    """Test analyze does NOT flag Rule 11 when Skill is present in tools."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    # Add an agent with Skill in tools
    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'has-skill-agent.md').write_text(
        '---\nname: has-skill-agent\ndescription: Agent with Skill\ntools: Read, Write, Skill\n---\n\n# Has Skill Agent\n'
    )

    try:
        result = run_script(SCRIPT_PATH, 'analyze', cwd=str(temp_dir))
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = result.json()
        all_issues = []
        for item in data['analysis']:
            if 'has-skill-agent' in item.get('component', {}).get('path', ''):
                all_issues.extend(item.get('issues', []))

        rule_11_issues = [i for i in all_issues if i['type'] == 'rule-11-violation']
        assert len(rule_11_issues) == 0, 'Should NOT detect rule-11-violation when Skill is present'
    finally:
        fixture.cleanup()


def test_fixture_analyze_no_rule_11_without_tools():
    """Test analyze does NOT flag Rule 11 when no tools field (inherits all)."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    # Add an agent without tools field
    agents_dir = fixture.marketplace_root / 'test-bundle' / 'agents'
    (agents_dir / 'no-tools-agent.md').write_text(
        '---\nname: no-tools-agent\ndescription: Agent without tools\n---\n\n# No Tools Agent\n'
    )

    try:
        result = run_script(SCRIPT_PATH, 'analyze', cwd=str(temp_dir))
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = result.json()
        all_issues = []
        for item in data['analysis']:
            if 'no-tools-agent' in item.get('component', {}).get('path', ''):
                all_issues.extend(item.get('issues', []))

        rule_11_issues = [i for i in all_issues if i['type'] == 'rule-11-violation']
        assert len(rule_11_issues) == 0, 'Should NOT detect rule-11-violation when no tools field'
    finally:
        fixture.cleanup()


# =============================================================================
# Main
# =============================================================================
