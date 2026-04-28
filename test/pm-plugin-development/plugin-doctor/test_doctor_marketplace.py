#!/usr/bin/env python3
"""Tests for doctor-marketplace.py - batch marketplace analysis and fixing.

Tests the hybrid Phase 1 script that provides automated batch operations:
- scan: Discover all components
- analyze: Batch analyze for issues
- fix: Apply safe fixes automatically
- report: Generate comprehensive report

Output format: TOON (parsed via toon_parser).

Marketplace discovery in these tests:
- Real-marketplace tests rely on script-relative discovery inside
  ``find_marketplace_root`` and therefore need no cwd/env setup.
- Fixture tests that construct a fake marketplace under ``tmp_path`` pass
  ``PM_MARKETPLACE_ROOT`` via ``env_overrides`` so the script targets the
  fixture deterministically instead of the real tree.
"""

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', 'doctor-marketplace.py')
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'

# Direct-import handle for ``_doctor_shared.find_marketplace_root`` so the
# --marketplace-root flag tests can exercise the resolution logic without
# the subprocess overhead of a full doctor-marketplace.py invocation.
_DOCTOR_SHARED_PATH = (
    PROJECT_ROOT
    / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills'
    / 'plugin-doctor' / 'scripts' / '_doctor_shared.py'
)


def _load_doctor_shared():
    spec = importlib.util.spec_from_file_location('_doctor_shared_under_test', _DOCTOR_SHARED_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules['_doctor_shared_under_test'] = mod
    spec.loader.exec_module(mod)
    return mod


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
# Scan Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_scan_help():
    """Test scan --help is available."""
    result = run_script(SCRIPT_PATH, 'scan', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'


def test_scan_returns_valid_toon():
    """Test scan returns valid TOON structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    assert result.returncode == 0, f'Scan failed: {result.stderr}'

    data = parse_output(result)
    assert data is not None, 'Should return valid TOON'
    assert 'bundles' in data, 'Should have bundles field'
    assert 'total_bundles' in data, 'Should have total_bundles field'
    assert 'total_components' in data, 'Should have total_components field'


def test_scan_finds_bundles():
    """Test scan finds marketplace bundles."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    data = parse_output(result)

    assert data['total_bundles'] > 0, 'Should find at least one bundle'
    assert len(data['bundles']) == data['total_bundles'], 'Bundle list length should match total_bundles'


def test_scan_bundle_structure():
    """Test scan returns correct bundle structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    data = parse_output(result)

    for bundle in data['bundles']:
        assert 'name' in bundle, 'Bundle should have name'
        assert 'path' in bundle, 'Bundle should have path'
        assert 'agents' in bundle, 'Bundle should have agents count'
        assert 'commands' in bundle, 'Bundle should have commands count'
        assert 'skills' in bundle, 'Bundle should have skills count'
        assert 'scripts' in bundle, 'Bundle should have scripts count'
        assert 'total' in bundle, 'Bundle should have total count'


def test_scan_bundle_filter():
    """Test scan with bundle filter."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    # First get a valid bundle name
    result = run_script(SCRIPT_PATH, 'scan')
    data = parse_output(result)
    if not data['bundles']:
        return  # No bundles to test

    first_bundle = data['bundles'][0]['name']

    # Now filter to just that bundle
    result = run_script(SCRIPT_PATH, 'scan', '--bundles', first_bundle)
    filtered = parse_output(result)

    assert filtered['total_bundles'] == 1, 'Should have exactly one bundle'
    assert filtered['bundles'][0]['name'] == first_bundle, f'Should be {first_bundle}'


# =============================================================================
# Analyze Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_analyze_help():
    """Test analyze --help is available."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'type' in combined.lower(), 'Help should mention type option'


def test_analyze_returns_valid_toon():
    """Test analyze returns valid TOON structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    # Analyze just one bundle for speed
    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle)
    assert result.returncode == 0, f'Analyze failed: {result.stderr}'

    data = parse_output(result)
    assert data is not None, 'Should return valid TOON'
    assert 'analysis' in data, 'Should have analysis field'
    assert 'total_components' in data, 'Should have total_components field'
    assert 'total_issues' in data, 'Should have total_issues field'


def test_analyze_summary_structure(plan_context):
    """Test analyze has correct summary fields.

    Uses ``plan_context`` to redirect ``PLAN_BASE_DIR`` so the
    doctor subprocess never resolves against the repo's real
    ``.plan/local/run-configuration.json``.
    """
    if not marketplace_available():
        return  # Skip if marketplace not available

    env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

    result = run_script(SCRIPT_PATH, 'scan', env_overrides=env)
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, env_overrides=env)
    data = parse_output(result)

    assert 'total_components' in data, 'Should have total_components'
    assert 'total_issues' in data, 'Should have total_issues'
    assert 'safe_fixes' in data, 'Should have safe_fixes'
    assert 'risky_fixes' in data, 'Should have risky_fixes'
    assert 'unfixable' in data, 'Should have unfixable'


def test_analyze_categorized_structure():
    """Test analyze has correct categorized fields."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle)
    data = parse_output(result)

    assert 'categorized_safe' in data, 'Should have categorized_safe'
    assert 'categorized_risky' in data, 'Should have categorized_risky'
    assert 'categorized_unfixable' in data, 'Should have categorized_unfixable'


def test_analyze_type_filter():
    """Test analyze with type filter."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'analyze', '--bundles', first_bundle, '--type', 'agents')
    data = parse_output(result)

    # All analyzed components should be agents — check via analysis table rows
    for item in data['analysis']:
        component = item.get('component', {})
        if isinstance(component, str):
            component = json.loads(component)
        comp_type = component.get('type')
        assert comp_type == 'agent', f'Expected agent, got {comp_type}'


# =============================================================================
# Fix Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_fix_help():
    """Test fix --help is available."""
    result = run_script(SCRIPT_PATH, 'fix', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'dry-run' in combined.lower(), 'Help should mention dry-run option'


def test_fix_dry_run_returns_valid_toon():
    """Test fix --dry-run returns valid TOON."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'fix', '--bundles', first_bundle, '--dry-run')
    assert result.returncode == 0, f'Fix dry-run failed: {result.stderr}'

    data = parse_output(result)
    assert data is not None, 'Should return valid TOON'
    assert 'status' in data, 'Should have status field'
    assert 'dry_run' in data, 'Should have dry_run field'
    assert data['dry_run'] is True, 'dry_run should be True'


def test_fix_dry_run_no_changes():
    """Test fix --dry-run does not modify files."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']
    bundle_path = PROJECT_ROOT / 'marketplace' / 'bundles' / first_bundle

    # Get modification times before
    mtimes_before = {}
    for md_file in bundle_path.rglob('*.md'):
        mtimes_before[str(md_file)] = md_file.stat().st_mtime

    # Run fix with dry-run
    result = run_script(SCRIPT_PATH, 'fix', '--bundles', first_bundle, '--dry-run')

    # Verify no files changed
    for md_file in bundle_path.rglob('*.md'):
        mtime_after = md_file.stat().st_mtime
        path_str = str(md_file)
        if path_str in mtimes_before:
            assert mtimes_before[path_str] == mtime_after, f'File modified during dry-run: {md_file}'


# =============================================================================
# Report Subcommand Tests (Tier 3 - subprocess, cwd-dependent)
# =============================================================================


def test_report_help():
    """Test report --help is available."""
    result = run_script(SCRIPT_PATH, 'report', '--help')
    combined = result.stdout + result.stderr
    assert 'bundles' in combined.lower(), 'Help should mention bundles option'
    assert 'output' in combined.lower(), 'Help should mention output option'


def test_report_returns_valid_toon():
    """Test report returns valid TOON structure with directory path."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle)
    assert result.returncode == 0, f'Report failed: {result.stderr}'

    data = parse_output(result)
    assert data is not None, 'Should return valid TOON'
    assert 'status' in data, 'Should have status field'
    assert data['status'] == 'success', 'Status should be success'
    assert 'report_dir' in data, 'Should have report_dir field'
    assert 'report_file' in data, 'Should have report_file field'
    assert 'findings_file' in data, 'Should have findings_file field'
    assert 'summary' in data, 'Should have summary field'
    assert str(data['report_dir']).endswith('temp/plugin-doctor-report'), (
        f'Report dir should end with temp/plugin-doctor-report, got {data["report_dir"]}'
    )


def test_report_summary_structure():
    """Test report summary has correct structure."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle)
    data = parse_output(result)

    summary = data['summary']
    assert 'total_bundles' in summary, 'Summary should have total_bundles'
    assert 'total_components' in summary, 'Summary should have total_components'
    assert 'total_issues' in summary, 'Summary should have total_issues'
    assert 'safe_fixes' in summary, 'Summary should have safe_fixes'
    assert 'risky_fixes' in summary, 'Summary should have risky_fixes'


def test_report_has_llm_review_items(plan_context):
    """Test report file includes LLM review items.

    Uses ``plan_context`` to redirect ``PLAN_BASE_DIR`` so the
    doctor subprocess writes the report under ``tmp_path`` instead of
    the repo's ``.plan/temp/plugin-doctor-report/``.
    """
    if not marketplace_available():
        return  # Skip if marketplace not available

    env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

    result = run_script(SCRIPT_PATH, 'scan', env_overrides=env)
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    result = run_script(SCRIPT_PATH, 'report', '--bundles', first_bundle, env_overrides=env)
    response = parse_output(result)

    # report_file is absolute; joining with PROJECT_ROOT preserves absolute path.
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

    result = run_script(SCRIPT_PATH, 'scan')
    scan_data = parse_output(result)
    if not scan_data['bundles']:
        return

    first_bundle = scan_data['bundles'][0]['name']

    output_dir = tempfile.mkdtemp()

    try:
        result = run_script(
            SCRIPT_PATH, 'report', '--bundles', first_bundle, '--output', output_dir
        )
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        json_files = list(Path(output_dir).glob('*-report.json'))
        assert len(json_files) == 1, f'Should have exactly one report JSON file, found: {json_files}'
        json_path = json_files[0]

        with open(json_path) as f:
            data = json.load(f)
        assert 'summary' in data, 'File should contain valid report'
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


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


def test_fixture_scan():
    """Test scan with fixture marketplace."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'scan', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
        assert result.returncode == 0, f'Scan failed: {result.stderr}'

        data = parse_output(result)
        assert data['total_bundles'] == 1, 'Should find one bundle'
        assert data['bundles'][0]['name'] == 'test-bundle', 'Should be test-bundle'
    finally:
        fixture.cleanup()


def test_fixture_analyze_finds_issues():
    """Test analyze finds issues in fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'analyze', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
        assert result.returncode == 0, f'Analyze failed: {result.stderr}'

        data = parse_output(result)
        # Should find at least one issue (Rule 6 - Task in agent)
        assert data['total_issues'] > 0, 'Should find issues in test fixture'
    finally:
        fixture.cleanup()


def test_fixture_fix_dry_run():
    """Test fix dry-run with fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'fix', '--dry-run', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
        assert result.returncode == 0, f'Fix dry-run failed: {result.stderr}'

        data = parse_output(result)
        assert data['dry_run'] is True, 'Should be dry run'
    finally:
        fixture.cleanup()


def test_fixture_report():
    """Test report with fixture."""
    fixture = TestWithTempMarketplace()
    temp_dir = fixture.setup_temp_marketplace()

    try:
        result = run_script(SCRIPT_PATH, 'report', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
        assert result.returncode == 0, f'Report failed: {result.stderr}'

        response = parse_output(result)
        assert response['status'] == 'success', 'Status should be success'

        summary = response['summary']
        assert summary['total_bundles'] == 1, 'Should have one bundle'

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
        result = run_script(SCRIPT_PATH, 'analyze', '--type', 'skills', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', '--type', 'skills', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', '--type', 'skills', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', '--type', 'skills', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
        result = run_script(SCRIPT_PATH, 'analyze', '--type', 'skills', env_overrides={'PM_MARKETPLACE_ROOT': str(temp_dir / 'marketplace'), 'PLAN_BASE_DIR': str(temp_dir / '.plan'), 'PLAN_MARSHALL_CREDENTIALS_DIR': str(temp_dir / 'credentials')})
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
# Scan --paths Flag Tests (Tier 3 - subprocess)
# =============================================================================


def test_scan_paths_valid_skill(tmp_path):
    """Test scan --paths with a valid skill directory containing SKILL.md."""
    skill_dir = tmp_path / 'my-skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text("""---
name: my-skill
description: A test skill for paths scanning
---

# My Skill

Content here.
""")

    result = run_script(SCRIPT_PATH, 'scan', '--paths', str(skill_dir))
    assert result.returncode == 0, f'Scan --paths failed: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 1, f'Should find 1 component, got {data["total_components"]}'
    assert data['components'][0]['type'] == 'skill', 'Should detect skill type'
    assert data['components'][0]['name'] == 'my-skill', 'Should use directory name as skill name'


def test_scan_paths_multiple(tmp_path):
    """Test scan --paths with multiple paths (skill and agent)."""
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

    result = run_script(SCRIPT_PATH, 'scan', '--paths', str(skill_dir), str(agents_parent))
    assert result.returncode == 0, f'Scan --paths failed: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 2, f'Should find 2 components, got {data["total_components"]}'

    types_found = {c['type'] for c in data['components']}
    assert 'skill' in types_found, 'Should find the skill component'


def test_scan_paths_invalid_path(tmp_path):
    """Test scan --paths with a non-existent path skips it with warning."""
    nonexistent = str(tmp_path / 'does-not-exist')

    result = run_script(SCRIPT_PATH, 'scan', '--paths', nonexistent)
    assert result.returncode == 0, f'Scan --paths should succeed even with invalid path: {result.stderr}'

    data = parse_output(result)
    assert data['mode'] == 'paths', 'Should report paths mode'
    assert data['total_components'] == 0, 'Should find 0 components for invalid path'
    assert 'WARNING' in result.stderr, 'Should emit warning on stderr for missing path'


def test_scan_paths_mutual_exclusion_with_bundles():
    """Test scan --paths and --bundles are mutually exclusive."""
    result = run_script(SCRIPT_PATH, 'scan', '--paths', '/some/path', '--bundles', 'plan-marshall')
    assert result.returncode != 0, 'Should fail when both --paths and --bundles are provided'


def test_scan_without_paths_or_bundles():
    """Test scan without --paths or --bundles uses default marketplace discovery."""
    if not marketplace_available():
        return  # Skip if marketplace not available

    result = run_script(SCRIPT_PATH, 'scan')
    assert result.returncode == 0, f'Default scan failed: {result.stderr}'

    data = parse_output(result)
    # Default mode should NOT have 'mode' key (only paths mode sets it)
    assert 'mode' not in data or data.get('mode') != 'paths', 'Default scan should not be in paths mode'
    assert 'total_bundles' in data, 'Default scan should have total_bundles'
    assert 'bundles' in data, 'Default scan should have bundles list'
    assert data['total_bundles'] > 0, 'Default scan should find bundles'


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
    assert resolved == fake_marketplace / 'bundles', (
        f'Expected {fake_marketplace / "bundles"}, got {resolved}'
    )


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
    assert resolved == arg_marketplace / 'bundles', (
        f'Function-arg override should win, got {resolved}'
    )
    assert resolved != env_marketplace / 'bundles', (
        'Env var path must NOT win when function-arg override is provided'
    )


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
    assert str(tmp_path) in msg, (
        f'Error message should reference the offending path {tmp_path}, got: {msg}'
    )
    # The message must clarify that the override is meant to be the parent
    # of bundles/, not bundles/ itself — this is what callers need to fix.
    assert 'marketplace root' in msg or 'parent of bundles' in msg, (
        f'Error message should clarify the parent-of-bundles contract, got: {msg}'
    )


# =============================================================================
# Main
# =============================================================================
