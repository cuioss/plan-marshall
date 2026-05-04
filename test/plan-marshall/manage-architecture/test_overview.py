#!/usr/bin/env python3
"""Tests for overview renderer + module --full --budget option."""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_client = _load_module('_cmd_client', '_cmd_client.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched

render_overview = _cmd_client.render_overview
render_module_markdown = _cmd_client.render_module_markdown
cmd_overview = _cmd_client.cmd_overview
cmd_module = _cmd_client.cmd_module
DEFAULT_OVERVIEW_BUDGET = _cmd_client.DEFAULT_OVERVIEW_BUDGET

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')


# =============================================================================
# Fixture helpers
# =============================================================================


def _seed_project(
    tmpdir: str,
    project_name: str,
    project_description: str,
    derived: dict[str, dict],
    enriched: dict[str, dict] | None = None,
) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` / ``enriched.json``."""
    save_project_meta(
        {
            'name': project_name,
            'description': project_description,
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in derived},
        },
        tmpdir,
    )
    for name, data in derived.items():
        save_module_derived(name, data, tmpdir)
    if enriched:
        for name, data in enriched.items():
            save_module_enriched(name, data, tmpdir)


def _create_three_module_project(tmpdir: str, with_enrichment: bool = True) -> None:
    derived = {
        'api': {
            'name': 'api',
            'paths': {'module': 'api'},
            'internal_dependencies': [],
            'commands': {},
        },
        'core': {
            'name': 'core',
            'paths': {'module': 'core'},
            'internal_dependencies': ['api'],
            'commands': {},
        },
        'service': {
            'name': 'service',
            'paths': {'module': 'service'},
            'internal_dependencies': ['core', 'api'],
            'commands': {},
        },
    }
    enriched = None
    description = ''
    if with_enrichment:
        description = 'A demo project for overview rendering tests.'
        enriched = {
            'api': {
                'purpose': 'library',
                'responsibility': 'HTTP API surface',
                'skills_by_profile': {
                    'implementation': {
                        'defaults': [{'skill': 'pm-dev-java:java-core', 'description': 'core'}],
                        'optionals': [],
                    },
                },
            },
            'core': {
                'purpose': 'library',
                'responsibility': 'Business logic',
            },
            'service': {
                'purpose': 'application',
                'responsibility': 'Wires API and core into a deployable service',
            },
        }
    _seed_project(tmpdir, 'demo', description, derived, enriched)


def _create_minimal_project(tmpdir: str) -> None:
    """Project with no enrichment so skills_by_profile section is omitted."""
    _seed_project(
        tmpdir,
        'minimal',
        '',
        {
            'solo': {
                'name': 'solo',
                'paths': {'module': 'solo'},
                'internal_dependencies': [],
                'commands': {},
            },
        },
    )


# =============================================================================
# render_overview tests
# =============================================================================


def test_overview_default_budget_under_200_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        out = render_overview(tmpdir, DEFAULT_OVERVIEW_BUDGET)
        assert len(out.splitlines()) <= DEFAULT_OVERVIEW_BUDGET


def test_overview_deterministic_byte_identical():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        first = render_overview(tmpdir)
        second = render_overview(tmpdir)
        assert first == second


def test_overview_sections_in_priority_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        out = render_overview(tmpdir)
        idx_modules = out.index('## Modules')
        idx_adjacency = out.index('## Adjacency')
        idx_skills = out.index('## Skills by Profile')
        assert idx_modules < idx_adjacency < idx_skills


def test_overview_truncation_marker_when_budget_too_small():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        full = render_overview(tmpdir)
        full_lines = len(full.splitlines())
        budget = max(full_lines - 5, 1)
        truncated = render_overview(tmpdir, budget)
        assert len(truncated.splitlines()) <= budget
        assert '... (truncated to fit budget=' in truncated
        assert f'budget={budget}' in truncated


def test_overview_omits_skills_section_when_absent():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_minimal_project(tmpdir)
        out = render_overview(tmpdir)
        assert '## Skills by Profile' not in out
        # Modules section must still be present
        assert '## Modules' in out


def test_overview_drops_trailing_skills_first_under_budget_pressure():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        full = render_overview(tmpdir)
        # Pick a budget that fits modules + adjacency but not skills
        # Assuming the skills section is the last block, render with a small budget
        out = render_overview(tmpdir, 16)
        assert '## Skills by Profile' not in out
        # Modules section is highest priority and should remain
        assert '## Modules' in out
        # And the marker must appear because we truncated
        assert '... (truncated' in out
        # Sanity: full version is materially larger
        assert len(full.splitlines()) > 16


# =============================================================================
# render_module_markdown tests
# =============================================================================


def test_module_markdown_respects_budget():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        out = render_module_markdown('service', tmpdir, budget=80)
        assert len(out.splitlines()) <= 80
        assert '# service' in out


def test_module_markdown_deterministic():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        first = render_module_markdown('core', tmpdir, budget=80)
        second = render_module_markdown('core', tmpdir, budget=80)
        assert first == second


def test_module_markdown_truncates_with_marker_when_tight():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        # Header alone is ~5 lines; pick a tight budget
        out = render_module_markdown('service', tmpdir, budget=4)
        assert len(out.splitlines()) <= 4
        assert '... (truncated to fit budget=' in out


# =============================================================================
# CLI handler tests
# =============================================================================


def test_cmd_overview_returns_markdown_string():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        args = Namespace(project_dir=tmpdir, budget=200)
        result = cmd_overview(args)
        assert isinstance(result, str)
        assert result.startswith('# demo')


def test_cmd_module_full_with_budget_returns_markdown_string():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        args = Namespace(project_dir=tmpdir, module='service', full=True, budget=80)
        result = cmd_module(args)
        assert isinstance(result, str)
        assert '# service' in result


def test_cmd_module_full_without_budget_returns_dict():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        args = Namespace(project_dir=tmpdir, module='service', full=True, budget=None)
        result = cmd_module(args)
        assert isinstance(result, dict)
        assert result['status'] == 'success'


def test_cmd_module_budget_without_full_is_noop():
    """--budget without --full keeps TOON output (no markdown rendering)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        args = Namespace(project_dir=tmpdir, module='service', full=False, budget=80)
        result = cmd_module(args)
        assert isinstance(result, dict)
        assert result['status'] == 'success'


# =============================================================================
# Argparse-wiring tests via subprocess
# =============================================================================


def test_argparse_wiring_overview_subcommand():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'overview', '--budget', '200')
        assert result.returncode == 0, result.stderr
        assert result.stdout.startswith('# demo')
        assert len(result.stdout.splitlines()) <= 200


def test_argparse_wiring_module_full_budget():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        result = run_script(
            SCRIPT_PATH, '--project-dir', tmpdir, 'module', '--module', 'service', '--full', '--budget', '80'
        )
        assert result.returncode == 0, result.stderr
        # Output should be markdown, not TOON
        assert '# service' in result.stdout
        assert 'status: success' not in result.stdout


def test_argparse_overview_default_budget():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'overview')
        assert result.returncode == 0, result.stderr
        assert len(result.stdout.splitlines()) <= 200


def test_argparse_subprocess_overview_byte_identical():
    """Two consecutive invocations of architecture overview must produce byte-identical stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        first = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'overview', '--budget', '200')
        second = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'overview', '--budget', '200')
        assert first.returncode == 0
        assert second.returncode == 0
        assert first.stdout == second.stdout


# =============================================================================
# Edge case
# =============================================================================


def test_overview_negative_budget_returns_marker_only_or_clamped():
    """Pathological tiny budget still produces output without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        out = render_overview(tmpdir, 1)
        # The truncation marker is one line; with budget=1 we expect no crash
        # and at most 1 line.
        assert len(out.splitlines()) <= 1


def test_module_markdown_without_enrichment():
    """Module rendering survives missing enriched data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_minimal_project(tmpdir)
        out = render_module_markdown('solo', tmpdir, budget=80)
        assert '# solo' in out


def test_module_markdown_unknown_module_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_three_module_project(tmpdir)
        with pytest.raises(_architecture_core.ModuleNotFoundInProjectError):
            render_module_markdown('does-not-exist', tmpdir, budget=80)
