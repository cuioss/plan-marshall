#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for plan-marshall:build-maven scripts.

Tests all Maven build operations:
- run: Execute build and auto-parse on failure (see test_maven_run.py)
- parse: Parse Maven build output
- search-markers: Search OpenRewrite markers
- check-warnings: Categorize build warnings
"""

import json
import tempfile
from pathlib import Path

from conftest import get_script_path, run_script

# Script under test - plan-marshall bundle
SCRIPT_PATH = get_script_path('plan-marshall', 'build-maven', 'maven.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'
MOCKS_DIR = Path(__file__).parent / 'mocks'

# The provenance-bearing fixture that pins the real OpenRewrite marker syntax.
# See test/plan-marshall/script-shared/fixtures/cui-rewrite/PROVENANCE.md.
PROVENANCE_SAMPLE = (
    Path(__file__).resolve().parents[1] / 'script-shared' / 'fixtures' / 'cui-rewrite' / 'MarkedSample.java'
)


def marker_close_delimiter() -> str:
    """Return the marker closing delimiter, derived from the provenance fixture."""
    text = PROVENANCE_SAMPLE.read_text(encoding='utf-8')
    start = text.index('/*~~(')
    end = text.index('*/', start) + len('*/')
    raw = text[start:end]
    return raw[raw.rindex(')') :]


# =============================================================================
# Parse Subcommand Tests
# =============================================================================


def test_parse_successful_build():
    """Test parsing successful Maven build output."""
    result = run_script(
        SCRIPT_PATH,
        'parse',
        '--log',
        str(FIXTURES_DIR / 'sample-maven-success.log'),
        '--mode',
        'structured',
        '--format',
        'json',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()

    assert data['status'] == 'success', 'Status should be success'
    assert data['data']['build_status'] == 'SUCCESS', 'Build status should be SUCCESS'


def test_parse_compilation_errors():
    """Test parsing build with compilation errors."""
    result = run_script(
        SCRIPT_PATH,
        'parse',
        '--log',
        str(FIXTURES_DIR / 'sample-maven-failure.log'),
        '--mode',
        'structured',
        '--format',
        'json',
    )
    data = result.json()

    assert data['data']['build_status'] == 'FAILURE', 'Build status should be FAILURE'
    assert data['data']['summary'].get('compilation_error', 0) > 0, 'Should detect compilation errors'


def test_parse_missing_file():
    """Test missing file handling."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', 'nonexistent.log', '--mode', 'structured')
    data = result.toon()

    assert data['status'] == 'error', 'Should return error status for missing file'


# =============================================================================
# Search-Markers Subcommand Tests
# =============================================================================


def test_search_markers_no_markers():
    """Test searching when no markers exist."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        src_dir = temp_dir / 'src' / 'main' / 'java'
        src_dir.mkdir(parents=True)
        java_file = src_dir / 'Test.java'
        java_file.write_text('public class Test {}')

        result = run_script(SCRIPT_PATH, 'search-markers', '--format', 'json', '--source-dir', str(temp_dir / 'src'))
        data = result.json()

        assert data['status'] == 'success', 'Should succeed with no markers'
        assert data['data']['total_markers'] == 0, 'Should find no markers'


# =============================================================================
# Check-Warnings Subcommand Tests
# =============================================================================


def test_check_warnings_empty():
    """Test with no warnings."""
    warnings = json.dumps([])
    acceptable = json.dumps({})

    result = run_script(SCRIPT_PATH, 'check-warnings', '--warnings', warnings, '--acceptable-warnings', acceptable)
    data = result.toon()

    assert data['status'] == 'success', 'Should succeed with no warnings'
    assert data['total'] == 0, 'Total should be 0'


def test_check_warnings_with_real_patterns():
    """Test check-warnings with real warning data and acceptable patterns (H45).

    Maven's handler uses filter_severity='WARNING', so warnings must have severity field.
    Maven uses substring matching.
    """
    warnings = json.dumps(
        [
            {'message': '[deprecation] DeprecatedApi has been deprecated', 'severity': 'WARNING'},
            {'message': '[unchecked] unchecked conversion', 'severity': 'WARNING'},
            {'message': 'some random warning', 'severity': 'WARNING'},
        ]
    )
    acceptable = json.dumps(
        {
            'patterns': ['[deprecation]', '[unchecked]'],
        }
    )

    result = run_script(SCRIPT_PATH, 'check-warnings', '--warnings', warnings, '--acceptable-warnings', acceptable)
    data = result.toon()

    assert data['status'] == 'success', 'Should succeed'
    assert data['total'] == 3, f'Should count all warnings, got: {data}'
    assert data['acceptable'] >= 2, f'Should accept deprecation and unchecked, got: {data}'


def test_search_markers_with_content():
    """Test searching when markers exist in source files (H49).

    The fixtures carry the real closing delimiter (see PROVENANCE.md), so the
    exact counts below are only reachable when the detector's pattern agrees
    with the upstream marker syntax — a `> 0` assertion would also pass on a
    detector that found a single marker by accident.
    """
    markers_dir = FIXTURES_DIR / 'source-with-markers'
    result = run_script(SCRIPT_PATH, 'search-markers', '--format', 'json', '--source-dir', str(markers_dir / 'src'))
    data = result.json()

    assert data['status'] == 'success', 'Should succeed'
    assert data['data']['total_markers'] == 4, f'Should find every fixture marker, got: {data["data"]}'
    assert data['data']['files_affected'] == 2, f'Both marked fixture files should report, got: {data["data"]}'
    assert data['data']['auto_suppress_count'] == 3, f'Two recipes are auto-suppressible, got: {data["data"]}'
    assert data['data']['ask_user_count'] == 1, f'SomeOtherRecipe needs a decision, got: {data["data"]}'


def test_search_markers_detected_markers_carry_the_provenance_delimiter():
    """Every detected marker must terminate with the fixture-derived delimiter."""
    markers_dir = FIXTURES_DIR / 'source-with-markers'
    result = run_script(SCRIPT_PATH, 'search-markers', '--format', 'json', '--source-dir', str(markers_dir / 'src'))
    data = result.json()

    close = marker_close_delimiter()
    raw_markers = [m['raw_marker'] for m in data['data']['markers']]
    assert raw_markers, 'Expected the fixture markers to be detected'
    for raw in raw_markers:
        assert raw.endswith(close), f'Marker {raw!r} does not end with the provenance delimiter {close!r}'


# =============================================================================
# Help Tests
# =============================================================================


def test_help_main():
    """Test main --help output."""
    result = run_script(SCRIPT_PATH, '--help')
    assert 'run' in result.stdout, 'Should show run subcommand'
    assert 'parse' in result.stdout, 'Should show parse subcommand'
    assert 'search-markers' in result.stdout, 'Should show search-markers subcommand'


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing contract
# =============================================================================
#
# maven.py uses the shared ``build_main()`` from ``_build_cli.py``,
# which delegates to ``resolve_project_dir`` for the four-state contract.
# The resolver semantics are pinned in
# ``test/plan-marshall/script-shared/test_build_cli.py``; here we only
# verify the parser surface so a future regression that drops one of the
# routing flags from maven's argv still fails loudly.


def test_run_subcommand_accepts_plan_id_flag():
    """maven.py's `run` subcommand MUST accept --plan-id (auto-routing flag).

    Help text is checked rather than running the full pipeline so the
    test stays hermetic — pinning the surface is enough; the resolver's
    behaviour is exercised at the unit level in test_build_cli.py.
    """
    result = run_script(SCRIPT_PATH, 'run', '--help')
    assert result.success, f'Script failed: {result.stderr}'
    assert '--plan-id' in result.stdout, 'maven run must declare --plan-id'
    assert '--project-dir' in result.stdout, 'maven run must keep --project-dir as escape hatch'


def test_run_rejects_both_plan_id_and_project_dir():
    """Both --plan-id and --project-dir together MUST yield mutually_exclusive_args."""
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--command-args',
        'verify',
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        '/tmp/explicit',
    )
    # The resolver branch prints a TOON error payload and returns exit 2.
    assert result.returncode == 2, f'Expected exit 2 (mutually_exclusive_args), got {result.returncode}'
    data = result.toon_or_error()
    assert data.get('status') == 'error'
    assert data.get('error') == 'mutually_exclusive_args'


def test_parse_subcommand_independent_of_routing_flags():
    """parse must keep working without either routing flag (no project_dir)."""
    # Pre-existing behaviour: ``parse --log <missing>`` returns a
    # structured error. The resolver is a no-op here because the parse
    # subparser does not declare project_dir/plan_id at all.
    result = run_script(SCRIPT_PATH, 'parse', '--log', 'nonexistent.log', '--mode', 'structured')
    data = result.toon()
    assert data['status'] == 'error', 'parse without routing flags must still produce a structured error'


# =============================================================================
# Main
# =============================================================================
