#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for scan-marketplace-inventory.py script.

In-process unit tests: the script's ``main()`` is loaded via
``load_script_module`` and driven against a SMALL synthetic marketplace built
under ``tmp_path`` (see the ``synthetic_marketplace`` / ``scan`` fixtures).
The synthetic tree is anchored by setting ``PM_MARKETPLACE_ROOT`` so the
script's ``get_base_path('auto')`` resolves there, and the test chdir's into
the synthetic root so ``safe_relative_path`` produces repo-relative paths
exactly as in production.

This replaces the previous Tier-3 design where every test spawned a subprocess
that re-walked the REAL ``marketplace/bundles/`` tree (~70 scans). The handful
of real-tree smoke tests live in the sibling ``integration/`` directory and are
excluded from the default ``module-tests`` run via the root conftest's
``collect_ignore`` list.

The synthetic marketplace is intentionally minimal but exercises every filter,
pattern, field, and content-filtering branch the assertions need:

- bundle ``alpha-bundle``: agents (``execution-context``, ``alpha-agent``),
  commands (``cmd-one``, ``cmd-two``), skills (``plan-alpha`` with a ```` ```toon ````
  block + ``## Workflow`` + ``## Error Handling`` sections and a ``standards/``
  subdir containing a ```` ```json ```` file; ``manage-beta`` plain skill), and
  scripts (public ``run-alpha.py`` + private ``_internal.py``).
- bundle ``beta-bundle``: one skill (``beta-skill``), one agent (``beta-agent``).
- bundle ``gamma-bundle``: one skill (``gamma-skill``) only.

Bundle counts: 3. Agent count: 3. Command count: 2. Skill count: 4.
Script count (public): 1.
"""

from pathlib import Path
from typing import Any

from toon_parser import parse_toon  # type: ignore[import-not-found]

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import load_script_module

# Keys that are metadata, not bundle names
METADATA_KEYS = {
    'status',
    'scope',
    'base_path',
    'statistics',
    'content_filter_stats',
    'content_pattern',
    'content_exclude',
}


def get_bundles(data: dict) -> list[dict[str, Any]]:
    """Extract bundle dicts from TOON data where bundles are top-level keys.

    The TOON format has bundles as top-level keys (e.g., 'alpha-bundle:')
    rather than a 'bundles' list. This helper extracts them as a list of dicts
    with 'name' field added.
    """
    bundles = []
    for key, value in data.items():
        if key not in METADATA_KEYS and isinstance(value, dict):
            bundle = {'name': key, **value}
            bundles.append(bundle)
    return bundles


# =============================================================================
# Synthetic marketplace fixture + in-process driver
# =============================================================================


_PLUGIN_JSON = '{\n  "name": "{name}",\n  "version": "0.1.0"\n}\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _build_synthetic_marketplace(root: Path) -> Path:
    """Create a minimal synthetic ``marketplace/bundles`` tree under ``root``.

    Returns the ``marketplace/bundles`` directory path. See the module docstring
    for the exact shape and the resource counts the assertions rely on.
    """
    bundles = root / 'marketplace' / 'bundles'

    # ----- alpha-bundle ------------------------------------------------------
    alpha = bundles / 'alpha-bundle'
    _write(alpha / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'alpha-bundle'))

    # agents
    _write(
        alpha / 'agents' / 'execution-context.md',
        '---\nname: execution-context\ndescription: Generic execution dispatcher\n---\n# Execution Context\n',
    )
    _write(
        alpha / 'agents' / 'alpha-agent.md',
        '---\nname: alpha-agent\ndescription: Alpha helper agent\n---\n```json\n{"x": 1}\n```\n',
    )

    # commands
    _write(
        alpha / 'commands' / 'cmd-one.md',
        '---\nname: cmd-one\ndescription: First command\n---\n# Command One\n',
    )
    _write(
        alpha / 'commands' / 'cmd-two.md',
        '---\nname: cmd-two\ndescription: Second command\n---\n# Command Two\n',
    )

    # skill plan-alpha: has ```toon, ## Workflow, ## Error Handling, a standards/ json file, scripts
    _write(
        alpha / 'skills' / 'plan-alpha' / 'SKILL.md',
        '---\nname: plan-alpha\ndescription: Plan alpha skill\nuser-invocable: true\n---\n'
        '# Plan Alpha\n\n## Workflow\n\n```toon\nstatus: ok\n```\n\n## Error Handling\n\nHandle errors.\n',
    )
    _write(
        alpha / 'skills' / 'plan-alpha' / 'standards' / 'guide.md',
        '# Guide\n\n```json\n{"k": "v"}\n```\n',
    )
    _write(
        alpha / 'skills' / 'plan-alpha' / 'standards' / 'plain.md',
        '# Plain standard\n\nNo code fences here.\n',
    )
    _write(
        alpha / 'skills' / 'plan-alpha' / 'scripts' / 'run-alpha.py',
        '#!/usr/bin/env python3\nprint("alpha")\n',
    )
    _write(
        alpha / 'skills' / 'plan-alpha' / 'scripts' / '_internal.py',
        '# private module, must be excluded\n',
    )

    # skill manage-beta: plain, no toon block, no Error Handling
    _write(
        alpha / 'skills' / 'manage-beta' / 'SKILL.md',
        '---\nname: manage-beta\ndescription: Manage beta skill\n---\n# Manage Beta\n\nPlain skill body.\n',
    )

    # ----- beta-bundle -------------------------------------------------------
    beta = bundles / 'beta-bundle'
    _write(beta / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'beta-bundle'))
    _write(
        beta / 'agents' / 'beta-agent.md',
        '---\nname: beta-agent\ndescription: Beta agent\n---\n# Beta Agent\n',
    )
    _write(
        beta / 'skills' / 'beta-skill' / 'SKILL.md',
        '---\nname: beta-skill\ndescription: Beta skill\n---\n# Beta Skill\n\n## Workflow\n\nSteps.\n',
    )

    # ----- gamma-bundle ------------------------------------------------------
    gamma = bundles / 'gamma-bundle'
    _write(gamma / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'gamma-bundle'))
    _write(
        gamma / 'skills' / 'gamma-skill' / 'SKILL.md',
        '---\nname: gamma-skill\ndescription: Gamma skill\n---\n# Gamma Skill\n',
    )

    return bundles


class _ScanResult:
    """Result of an in-process ``main()`` invocation."""

    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ''


def _make_runner(module, monkeypatch, capsys):
    """Return a ``run(*args)`` callable driving ``module.main()`` in-process.

    Sets ``sys.argv`` to the synthetic command line, invokes ``main()`` (which
    always ``sys.exit``s via the ``@safe_main`` wrapper), and captures stdout.
    Argparse validation errors raise ``SystemExit(2)`` and are surfaced as a
    non-zero ``returncode`` exactly as a subprocess would report them.
    """

    def run(*args: str) -> _ScanResult:
        import sys

        # Drain any output buffered from a previous call so capsys.readouterr()
        # returns only this invocation's stdout.
        capsys.readouterr()
        monkeypatch.setattr(sys, 'argv', ['scan-marketplace-inventory.py', *args])
        code = 0
        try:
            module.main()
        except SystemExit as exc:  # @safe_main always exits
            code = int(exc.code) if exc.code is not None else 0
        captured = capsys.readouterr()
        return _ScanResult(code, captured.out)

    return run


def _scan_module():
    """Load the scan-marketplace-inventory module in-process."""
    return load_script_module(
        'pm-plugin-development',
        'tools-marketplace-inventory',
        'scan-marketplace-inventory.py',
    )


import pytest  # noqa: E402


@pytest.fixture
def synthetic_marketplace(tmp_path, monkeypatch):
    """Build a synthetic marketplace under ``tmp_path`` and anchor the scan to it.

    - Sets ``PM_MARKETPLACE_ROOT`` so ``get_base_path('auto')`` resolves the
      synthetic ``marketplace/bundles`` tree (branch 2 of the four-step
      resolution chain), short-circuiting before any git-root / cwd discovery
      that would reach the real repo.
    - chdir's into the synthetic root so ``safe_relative_path`` yields
      repo-relative paths (matching production output) and content-filter file
      reads resolve those relative paths correctly.

    Yields the ``marketplace/bundles`` directory.
    """
    bundles = _build_synthetic_marketplace(tmp_path)
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(tmp_path))
    monkeypatch.chdir(tmp_path)
    yield bundles


@pytest.fixture
def scan(synthetic_marketplace, monkeypatch, capsys):
    """In-process ``run(*args)`` driver bound to the synthetic marketplace."""
    module = _scan_module()
    return _make_runner(module, monkeypatch, capsys)


# =============================================================================
# Tests - Basic Discovery
# =============================================================================


def test_default_scan_finds_bundles(scan):
    """Direct-result scan finds all synthetic bundles."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_bundles = data.get('statistics', {}).get('total_bundles', 0)
    assert total_bundles == 3, f'Should find 3 bundles, found {total_bundles}'


def test_default_scan_finds_agents(scan):
    """Direct-result scan finds the synthetic agents."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 3, f'Should find 3 agents, found {total_agents}'


def test_default_scan_finds_commands(scan):
    """Direct-result scan finds the synthetic commands."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands == 2, f'Should find 2 commands, found {total_commands}'


def test_default_scan_finds_skills(scan):
    """Direct-result scan finds the synthetic skills."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills == 4, f'Should find 4 skills, found {total_skills}'


def test_default_scope_is_auto(scan):
    """Default scope is auto (tries marketplace first, then plugin-cache)."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    scope = data.get('scope')
    assert scope == 'auto', f"Default scope should be 'auto', got '{scope}'"


# =============================================================================
# Tests - Resource Filtering
# =============================================================================


def test_agents_only_no_commands(scan):
    """Agents-only filter has no commands."""
    result = scan('--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands == 0, f'Agents-only should have 0 commands, found {total_commands}'


def test_agents_only_no_skills(scan):
    """Agents-only filter has no skills."""
    result = scan('--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills == 0, f'Agents-only should have 0 skills, found {total_skills}'


def test_agents_only_has_agents(scan):
    """Agents-only filter has agents."""
    result = scan('--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 3, f'Agents-only should have 3 agents, found {total_agents}'


def test_commands_only_no_agents(scan):
    """Commands-only filter has no agents."""
    result = scan('--direct-result', '--resource-types', 'commands')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 0, f'Commands-only should have 0 agents, found {total_agents}'


def test_commands_only_has_commands(scan):
    """Commands-only filter has commands."""
    result = scan('--direct-result', '--resource-types', 'commands')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands == 2, f'Commands-only should have 2 commands, found {total_commands}'


def test_skills_only_no_agents(scan):
    """Skills-only filter has no agents."""
    result = scan('--direct-result', '--resource-types', 'skills')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 0, f'Skills-only should have 0 agents, found {total_agents}'


def test_skills_only_has_skills(scan):
    """Skills-only filter has skills."""
    result = scan('--direct-result', '--resource-types', 'skills')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills == 4, f'Skills-only should have 4 skills, found {total_skills}'


def test_multiple_types_has_both(scan):
    """Multiple types filter has both agents and commands."""
    result = scan('--direct-result', '--resource-types', 'agents,commands')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_agents == 3, f'Multiple types should have 3 agents, found {total_agents}'
    assert total_commands == 2, f'Multiple types should have 2 commands, found {total_commands}'


# =============================================================================
# Tests - Description Extraction
# =============================================================================


def test_no_descriptions_returns_null(scan):
    """Direct-result mode has no description fields without flag."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    has_desc_count = sum(
        1
        for bundle in bundles
        for agent in bundle.get('agents', [])
        if isinstance(agent, dict) and 'description' in agent
    )
    assert has_desc_count == 0, (
        f'Should have no description fields without --include-descriptions, found {has_desc_count}'
    )


def test_with_descriptions_extracts_desc(scan):
    """--full extracts descriptions."""
    import json

    result = scan('--direct-result', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    desc_count = sum(
        1
        for bundle in bundles_dict.values()
        for agent in bundle.get('agents', [])
        if isinstance(agent, dict) and agent.get('description') is not None
    )
    assert desc_count > 0, f'Should find descriptions with --full, found {desc_count}'


# =============================================================================
# Tests - TOON Validity
# =============================================================================


def test_direct_result_produces_valid_toon(scan):
    """--direct-result produces valid TOON."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'Direct result mode should produce valid TOON: {e}') from e


def test_with_descriptions_produces_valid_toon(scan):
    """--include-descriptions with --direct-result produces valid TOON."""
    result = scan('--direct-result', '--include-descriptions')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'With descriptions should produce valid TOON: {e}') from e


def test_filtered_produces_valid_toon(scan):
    """Filtered mode with --direct-result produces valid TOON."""
    result = scan('--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'Filtered mode should produce valid TOON: {e}') from e


# =============================================================================
# Tests - Bundle Structure
# =============================================================================


def test_bundles_have_required_fields(scan):
    """Bundles have required fields."""
    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) > 0, 'Should have at least one bundle'

    first_bundle = bundles[0]
    assert 'name' in first_bundle, 'Bundle should have name'
    assert 'path' in first_bundle, 'Bundle should have path'


# =============================================================================
# Tests - Script Discovery
# =============================================================================


def test_script_count_matches_discovery(scan):
    """Script count reflects public scripts only (private modules excluded)."""
    result = scan('--direct-result', '--resource-types', 'scripts')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    actual_count = data.get('statistics', {}).get('total_scripts', 0)
    # Synthetic tree has one public script (run-alpha.py); _internal.py excluded.
    assert actual_count == 1, f'Script count should be 1 (public only), got {actual_count}'


def test_scripts_have_path_formats(scan):
    """Scripts have path_formats structure when using --full flag."""
    import json

    result = scan('--direct-result', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    scripts_with_paths = sum(
        1
        for bundle in bundles_dict.values()
        for script in bundle.get('scripts', [])
        if isinstance(script, dict) and script.get('path_formats', {}).get('absolute') is not None
    )
    total_scripts = data.get('statistics', {}).get('total_scripts', 0)

    assert scripts_with_paths == total_scripts and total_scripts != 0, (
        f'All scripts should have path_formats: {scripts_with_paths} vs {total_scripts}'
    )


def test_scripts_have_notation_field(scan):
    """All scripts have notation field in {bundle}:{skill}:{script} format."""
    import json

    result = scan('--direct-result', '--resource-types', 'scripts', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    for bundle_name, bundle in bundles_dict.items():
        for script in bundle.get('scripts', []):
            assert 'notation' in script, f'Script {script["name"]} missing notation field'
            notation = script['notation']
            skill_name = script['skill']
            script_name = script['name']
            expected = f'{bundle_name}:{skill_name}:{script_name}'
            assert notation == expected, f"Script notation mismatch: expected '{expected}', got '{notation}'"


def test_scripts_notation_format_valid(scan):
    """Notation follows {bundle}:{skill}:{script} format with two colons."""
    import json

    result = scan('--direct-result', '--resource-types', 'scripts', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    for bundle in bundles_dict.values():
        for script in bundle.get('scripts', []):
            notation = script.get('notation', '')
            parts = notation.split(':')
            assert len(parts) == 3, f"Notation '{notation}' should have exactly two colons"
            assert parts[0], f"Notation '{notation}' should have non-empty bundle"
            assert parts[1], f"Notation '{notation}' should have non-empty skill"
            assert parts[2], f"Notation '{notation}' should have non-empty script"


def test_scripts_exclude_private_modules(scan):
    """Underscore-prefixed files (private modules) are excluded from scripts."""
    result = scan('--direct-result', '--resource-types', 'scripts')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    for bundle in bundles:
        for script in bundle.get('scripts', []):
            script_name = script if isinstance(script, str) else script.get('name', '')
            assert not script_name.startswith('_'), (
                f"Private module '{script_name}' should not be included (underscore prefix = internal)"
            )


# =============================================================================
# Tests - Name Pattern Filtering
# =============================================================================


def test_name_pattern_filters_agents(scan):
    """--name-pattern filters agents by pattern."""
    result = scan('--direct-result', '--resource-types', 'agents', '--name-pattern', 'execution-*')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, 'Should find at least 1 execution-context agent'

    for bundle in bundles:
        for agent in bundle.get('agents', []):
            agent_name = agent if isinstance(agent, str) else agent.get('name', '')
            assert agent_name.startswith('execution-'), f'Agent {agent_name} should match execution-* pattern'


def test_name_pattern_multiple_patterns(scan):
    """--name-pattern with multiple pipe-separated patterns."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'agents',
        '--name-pattern',
        'execution-*|*-agent',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, 'Should find at least 1 agent matching execution-* or *-agent patterns'

    for bundle in bundles:
        for agent in bundle.get('agents', []):
            agent_name = agent if isinstance(agent, str) else agent.get('name', '')
            assert agent_name.startswith('execution-') or agent_name.endswith('-agent'), (
                f'Agent {agent_name} should match execution-* or *-agent pattern'
            )


def test_name_pattern_no_matches(scan):
    """--name-pattern with pattern that matches nothing."""
    result = scan('--direct-result', '--name-pattern', 'nonexistent-xyz-pattern')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total_resources = data.get('statistics', {}).get('total_resources', 0)
    assert total_resources == 0, 'Should find 0 resources with non-matching pattern'


def test_name_pattern_skills_filter(scan):
    """--name-pattern filters skills."""
    result = scan('--direct-result', '--resource-types', 'skills', '--name-pattern', 'plan-*')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills >= 1, 'Should find at least 1 skill starting with plan-'

    for bundle in bundles:
        for skill in bundle.get('skills', []):
            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
            assert skill_name.startswith('plan-'), f'Skill {skill_name} should start with plan-'


# =============================================================================
# Tests - Bundle Filtering
# =============================================================================


def test_bundles_filter_single(scan):
    """--bundles filters to single bundle."""
    result = scan('--direct-result', '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 1, f'Should have exactly 1 bundle, found {len(bundles)}'
    assert bundles[0]['name'] == 'alpha-bundle', f"Bundle should be 'alpha-bundle', got '{bundles[0]['name']}'"


def test_bundles_filter_multiple(scan):
    """--bundles filters to multiple bundles."""
    result = scan('--direct-result', '--bundles', 'alpha-bundle,beta-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    bundle_names = {b['name'] for b in bundles}
    assert bundle_names == {'alpha-bundle', 'beta-bundle'}, (
        f'Expected alpha-bundle and beta-bundle, got {bundle_names}'
    )


def test_bundles_filter_nonexistent(scan):
    """--bundles with nonexistent bundle returns empty."""
    result = scan('--direct-result', '--bundles', 'nonexistent-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 0, f'Should have 0 bundles for nonexistent filter, found {len(bundles)}'


# =============================================================================
# Tests - Combined Filtering
# =============================================================================


def test_combined_bundle_and_name_pattern(scan):
    """Combining --bundles and --name-pattern filters."""
    result = scan(
        '--direct-result',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'agents',
        '--name-pattern',
        'execution-*',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have exactly 1 bundle'
    assert bundles[0]['name'] == 'alpha-bundle', 'Bundle should be alpha-bundle'

    agents = bundles[0].get('agents', [])
    assert len(agents) >= 1, 'Should find at least 1 agent in alpha-bundle'
    agent_names = [a if isinstance(a, str) else a.get('name', '') for a in agents]
    assert any('execution-context' in n for n in agent_names), f'Should find execution-context, got: {agent_names}'


# =============================================================================
# Tests - File Output (Default Behavior)
# =============================================================================


def test_default_file_output_creates_file(scan, tmp_path, monkeypatch):
    """Default mode (no --direct-result) creates a TOON file and prints summary."""
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = scan('--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    output = result.stdout
    assert 'status: success' in output, 'Summary should contain status: success'
    assert 'output_mode: file' in output, 'Summary should contain output_mode: file'
    assert 'output_file:' in output, 'Summary should contain output_file path'
    assert 'next_step:' in output, 'Summary should contain next_step'

    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, f'Should create exactly one inventory file, found {len(files)}'


def test_default_file_output_summary_has_statistics(scan, tmp_path, monkeypatch):
    """Default file mode summary includes statistics."""
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    output = result.stdout
    assert 'statistics:' in output, 'Summary should contain statistics'
    assert 'total_bundles:' in output, 'Summary should contain total_bundles'
    assert 'total_skills:' in output, 'Summary should contain total_skills'


def test_default_file_output_with_filters(scan, tmp_path, monkeypatch):
    """Default file mode works with bundle filter and writes filtered content."""
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = scan('--bundles', 'beta-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, 'Should create inventory file with filter'

    content = files[0].read_text()
    assert 'beta-bundle' in content, 'Inventory file should contain beta-bundle bundle'


def test_default_file_output_creates_parent_dirs(scan, tmp_path, monkeypatch):
    """Default file mode creates parent directories if needed."""
    plan_dir = tmp_path / 'nested' / 'deeply' / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = scan('--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    assert expected_dir.exists(), 'Should create nested directories'

    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, 'Should create inventory file in nested directory'


def test_file_output_respects_plan_base_dir(scan, tmp_path, monkeypatch):
    """File output uses PLAN_BASE_DIR environment variable."""
    plan_dir = tmp_path / 'custom-plan-dir'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = scan('--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, f'Should create file in {expected_dir}'


# =============================================================================
# Tests - Custom Output Path (--output)
# =============================================================================


def test_output_param_creates_file_at_path(scan, tmp_path):
    """--output parameter writes to specified path."""
    output_file = tmp_path / 'custom-inventory.toon'

    result = scan('--output', str(output_file), '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    assert output_file.exists(), f'Should create file at {output_file}'

    content = output_file.read_text()
    data = parse_toon(content)
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have one bundle'
    assert bundles[0]['name'] == 'alpha-bundle', 'Bundle should be alpha-bundle'


def test_output_param_creates_parent_dirs(scan, tmp_path):
    """--output parameter creates parent directories if needed."""
    output_file = tmp_path / 'nested' / 'deeply' / 'inventory.toon'

    result = scan('--output', str(output_file), '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    assert output_file.exists(), f'Should create file and parent dirs at {output_file}'


def test_output_param_summary_shows_custom_path(scan, tmp_path):
    """--output parameter summary includes the custom path."""
    output_file = tmp_path / 'my-inventory.toon'

    result = scan('--output', str(output_file), '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    summary = parse_toon(result.stdout)
    assert summary.get('output_file') == str(output_file), (
        f'Summary should show custom path, got {summary.get("output_file")}'
    )


def test_output_param_ignores_plan_base_dir(scan, tmp_path, monkeypatch):
    """--output parameter takes precedence over PLAN_BASE_DIR."""
    plan_dir = tmp_path / 'plan-base'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    output_file = tmp_path / 'custom-output' / 'inventory.toon'

    result = scan('--output', str(output_file), '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    assert output_file.exists(), 'Should create file at --output path'
    plan_base_files = list((plan_dir / 'temp').glob('**/*.toon')) if plan_dir.exists() else []
    assert len(plan_base_files) == 0, 'Should NOT create file in PLAN_BASE_DIR when --output is specified'


def test_output_param_with_filters(scan, tmp_path):
    """--output parameter works with resource and bundle filters."""
    output_file = tmp_path / 'filtered-inventory.toon'

    result = scan(
        '--output',
        str(output_file),
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
        '--name-pattern',
        'plan-*',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    assert output_file.exists(), f'Should create file at {output_file}'

    data = parse_toon(output_file.read_text())
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have one bundle'

    bundle = bundles[0]
    assert len(bundle.get('agents', [])) == 0, 'Should have 0 agents'
    assert len(bundle.get('commands', [])) == 0, 'Should have 0 commands'
    assert len(bundle.get('scripts', [])) == 0, 'Should have 0 scripts'
    assert len(bundle.get('skills', [])) >= 1, 'Should have at least 1 skill'


# =============================================================================
# Tests - Error Handling
# =============================================================================


def test_invalid_scope_returns_error(scan):
    """Invalid scope returns error (argparse validation)."""
    result = scan('--scope', 'invalid')
    assert result.returncode != 0, 'Invalid scope should return error (argparse validation)'


def test_invalid_resource_type_returns_error(scan):
    """Invalid resource type returns error (in TOON output)."""
    result = scan('--resource-types', 'invalid')
    assert result.returncode == 0, 'Expected exit 0 (error in TOON output)'
    assert 'error' in result.stdout.lower()


# =============================================================================
# Tests - Content Pattern Filtering
# =============================================================================


def test_content_pattern_requires_descriptions_or_full(scan):
    """--content-pattern without --include-descriptions or --full returns error."""
    result = scan('--content-pattern', '```json', '--direct-result')
    assert result.returncode == 0, 'Expected exit 0 (error in TOON output)'
    assert 'require --include-descriptions or --full' in result.stdout


def test_content_exclude_requires_descriptions_or_full(scan):
    """--content-exclude without --include-descriptions or --full returns error."""
    result = scan('--content-exclude', '```json', '--direct-result')
    assert result.returncode == 0, 'Expected exit 0 (error in TOON output)'


def test_content_pattern_include_single_regex(scan):
    """--content-pattern with single regex pattern filters correctly."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```toon',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)

    assert 'content_filter_stats' in data, 'Should include content_filter_stats'
    stats = data['content_filter_stats']
    assert stats['input_count'] > 0, 'Should have input files'
    assert stats['matched_count'] >= 1, 'Should match at least 1 file with ```toon'
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills == stats['matched_count'], 'Total skills should equal matched_count'


def test_content_pattern_include_multiple_or_logic(scan):
    """--content-pattern with multiple pipe-separated patterns (OR logic)."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```toon|## Error Handling',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    assert 'content_filter_stats' in data

    stats = data['content_filter_stats']
    assert stats['matched_count'] >= 1, 'Should match files with ```toon OR ## Error Handling'


def test_content_exclude_single_pattern(scan):
    """--content-exclude excludes matching files."""
    result_without = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--include-descriptions',
    )
    assert result_without.returncode == 0
    data_without = parse_toon(result_without.stdout)
    count_without = data_without.get('statistics', {}).get('total_skills', 0)

    result_with = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-exclude',
        '## Workflow',
        '--include-descriptions',
    )
    assert result_with.returncode == 0, f'Script returned error: {result_with.stdout}'
    data_with = parse_toon(result_with.stdout)
    count_with = data_with.get('statistics', {}).get('total_skills', 0)

    assert count_with < count_without, (
        f'Exclude pattern should reduce count: {count_with} should be < {count_without}'
    )


def test_content_include_and_exclude_combined(scan):
    """Combining --content-pattern and --content-exclude."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```toon',
        '--content-exclude',
        '## Error Handling',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    assert 'content_filter_stats' in data

    stats = data['content_filter_stats']
    assert stats['input_count'] > 0, 'Should have input files to filter'


def test_content_pattern_output_includes_pattern(scan):
    """Output includes the content_pattern used."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```json',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    assert data.get('content_pattern') == '```json', 'Output should include content_pattern used'


def test_content_pattern_with_bundles_filter(scan):
    """Content filtering works with bundle filter."""
    result = scan(
        '--direct-result',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```toon',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    assert len(bundles) <= 1, 'Should have at most one bundle (alpha-bundle)'
    if bundles:
        assert bundles[0]['name'] == 'alpha-bundle'


def test_content_pattern_no_matches_returns_empty(scan):
    """Content pattern that matches nothing returns zero results."""
    result = scan(
        '--direct-result',
        '--resource-types',
        'skills',
        '--content-pattern',
        'NONEXISTENT_UNIQUE_STRING_XYZ123',
        '--include-descriptions',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    total = data.get('statistics', {}).get('total_skills', 0)
    assert total == 0, 'Should find 0 skills with non-matching pattern'


# =============================================================================
# Tests - Include Tests Flag
# =============================================================================


def test_include_tests_discovers_test_files(scan, synthetic_marketplace):
    """--include-tests discovers test files for bundles.

    ``discover_tests`` reads ``test/{bundle-name}/`` relative to cwd, which the
    fixture set to the synthetic root — so we create a synthetic test tree there.
    """
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / 'test' / 'alpha-bundle' / 'test_alpha.py',
        'def test_alpha():\n    assert True\n',
    )

    result = scan('--direct-result', '--include-tests', '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have exactly 1 bundle'

    bundle = bundles[0]
    tests = bundle.get('tests', [])
    assert len(tests) >= 1, f'Should find at least 1 test file, found {len(tests)}'


def test_include_tests_includes_conftest(scan, synthetic_marketplace):
    """--include-tests includes conftest.py files when present in test directories."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(root / 'test' / 'alpha-bundle' / 'test_alpha.py', 'def test_alpha():\n    assert True\n')
    _write(root / 'test' / 'alpha-bundle' / 'conftest.py', '# conftest\n')

    result = scan('--direct-result', '--include-tests', '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    # In default (non-full) mode tests are name strings; verify conftest present.
    conftest_names = []
    for bundle in bundles:
        for test in bundle.get('tests', []):
            test_name = test if isinstance(test, str) else test.get('name', '')
            if test_name == 'conftest':
                conftest_names.append(bundle['name'])
    assert 'alpha-bundle' in conftest_names, 'conftest.py should be discovered for alpha-bundle'


def test_include_tests_maps_to_bundles(scan, synthetic_marketplace):
    """--include-tests correctly maps test directories to bundles (--full paths)."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(root / 'test' / 'alpha-bundle' / 'test_alpha.py', 'def test_alpha():\n    assert True\n')

    result = scan(
        '--direct-result', '--include-tests', '--full', '--format', 'json', '--bundles', 'alpha-bundle'
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    import json

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})
    bundle = bundles_dict.get('alpha-bundle', {})
    for test in bundle.get('tests', []):
        if isinstance(test, dict) and 'path' in test:
            assert 'test/alpha-bundle' in test['path'], (
                f'Test path should be in test/alpha-bundle: {test["path"]}'
            )


def test_include_tests_updates_statistics(scan, synthetic_marketplace):
    """--include-tests adds total_tests to statistics."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(root / 'test' / 'alpha-bundle' / 'test_alpha.py', 'def test_alpha():\n    assert True\n')

    result = scan('--direct-result', '--include-tests')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    stats = data.get('statistics', {})
    assert 'total_tests' in stats, 'Statistics should include total_tests'
    assert stats['total_tests'] >= 1, 'total_tests should reflect the discovered synthetic test'


def test_include_tests_without_flag_has_no_tests(scan, synthetic_marketplace):
    """Without --include-tests flag has no tests in output."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(root / 'test' / 'alpha-bundle' / 'test_alpha.py', 'def test_alpha():\n    assert True\n')

    result = scan('--direct-result', '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    for bundle in bundles:
        tests = bundle.get('tests', [])
        assert len(tests) == 0, f'Without --include-tests, tests should be empty, found {len(tests)}'


# =============================================================================
# Tests - Include Project Skills Flag
# =============================================================================


def test_include_project_skills_discovers_skills(scan, synthetic_marketplace):
    """--include-project-skills discovers project-level skills via the active target's roots.

    Project-skill discovery routes through the platform-runtime layout op
    (``marketplace_paths.iter_project_skill_dirs``). With no marshal.json the
    helper falls back to the Claude default root (``.claude/skills``), so a
    skill written under ``.claude/skills`` is still discovered. The pseudo-
    bundle is target-named ``project-skills`` (no longer the Claude-only
    ``.claude/skills`` literal in the ``path`` field).
    """
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )

    result = scan('--direct-result', '--include-project-skills')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    project_skills = next((b for b in bundles if b['name'] == 'project-skills'), None)
    assert project_skills is not None, 'project-skills pseudo-bundle should be present'
    assert project_skills['path'] == 'project-skills', 'project-skills path should be the target-agnostic label'
    skills = project_skills.get('skills', [])
    assert len(skills) >= 1, 'Should find at least 1 project skill'


def test_include_project_skills_discovers_scripts(scan, synthetic_marketplace):
    """--include-project-skills discovers scripts in project skills."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )
    _write(root / '.claude' / 'skills' / 'proj-skill' / 'scripts' / 'do-thing.py', 'print("x")\n')

    result = scan('--direct-result', '--include-project-skills', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    import json

    data = json.loads(result.stdout)
    project_skills = data.get('bundles', {}).get('project-skills', {})
    scripts = project_skills.get('scripts', [])
    assert len(scripts) >= 1, 'Should discover project-skill scripts'
    for script in scripts:
        if isinstance(script, dict):
            assert 'notation' in script, 'Script should have notation field'
            assert script['notation'].startswith('project-skills:'), 'Notation should start with project-skills:'


def test_include_project_skills_scans_both_layout_roots(synthetic_marketplace, monkeypatch, capsys):
    """--include-project-skills scans every project-local-skill root (both layouts).

    On OpenCode the layout op reports a multi-root list. The scanner routes
    through ``iter_project_skill_dirs``; this test forces a two-root layout
    (mirroring the OpenCode executor's multi-root discovery) and asserts a
    skill under EACH root is discovered, proving the scanner is no longer bound
    to the single Claude ``.claude/skills`` tree.
    """
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'claude-skill' / 'SKILL.md',
        '---\nname: claude-skill\ndescription: Claude tree skill\n---\n# Claude Skill\n',
    )
    _write(
        root / '.opencode' / 'skill' / 'opencode-skill' / 'SKILL.md',
        '---\nname: opencode-skill\ndescription: OpenCode tree skill\n---\n# OpenCode Skill\n',
    )

    module = _scan_module()
    monkeypatch.setattr(
        module,
        'iter_project_skill_dirs',
        lambda base=None: [
            root / '.claude' / 'skills' / 'claude-skill',
            root / '.opencode' / 'skill' / 'opencode-skill',
        ],
    )
    run = _make_runner(module, monkeypatch, capsys)
    # --full --format json yields structured skill dicts (default/TOON mode
    # flattens skill entries to name strings).
    result = run('--direct-result', '--include-project-skills', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    import json

    data = json.loads(result.stdout)
    project_skills = data.get('bundles', {}).get('project-skills', {})
    skills = project_skills.get('skills', [])
    names = {s['name'] if isinstance(s, dict) else s for s in skills}
    assert names == {'claude-skill', 'opencode-skill'}, f'both layout roots should be scanned, got {names}'


def test_include_project_skills_without_flag_no_pseudo_bundle(scan, synthetic_marketplace):
    """Without --include-project-skills flag has no project-skills bundle."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )

    result = scan('--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    project_skills = next((b for b in bundles if b['name'] == 'project-skills'), None)
    assert project_skills is None, 'Without --include-project-skills, project-skills bundle should not exist'


def test_include_project_skills_with_bundle_filter(scan, synthetic_marketplace):
    """--include-project-skills respects bundle filter."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )

    result = scan('--direct-result', '--include-project-skills', '--bundles', 'alpha-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    bundle_names = {b['name'] for b in bundles}

    assert 'alpha-bundle' in bundle_names
    assert 'project-skills' not in bundle_names, 'project-skills should be filtered out when not in --bundles'


def test_include_project_skills_explicitly_in_bundle_filter(scan, synthetic_marketplace):
    """--include-project-skills included when explicitly in bundle filter."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )

    result = scan('--direct-result', '--include-project-skills', '--bundles', 'project-skills')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    for bundle in bundles:
        assert bundle['name'] == 'project-skills', f'Only project-skills should be present, found {bundle["name"]}'


# =============================================================================
# Tests - Combined Flags
# =============================================================================


def test_include_tests_and_project_skills_combined(scan, synthetic_marketplace):
    """Both --include-tests and --include-project-skills can be used together."""
    root = synthetic_marketplace.parent.parent  # tmp_path
    _write(root / 'test' / 'alpha-bundle' / 'test_alpha.py', 'def test_alpha():\n    assert True\n')
    _write(
        root / '.claude' / 'skills' / 'proj-skill' / 'SKILL.md',
        '---\nname: proj-skill\ndescription: Project skill\n---\n# Proj Skill\n',
    )

    result = scan(
        '--direct-result',
        '--include-tests',
        '--include-project-skills',
        '--bundles',
        'alpha-bundle',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    alpha = next((b for b in bundles if b['name'] == 'alpha-bundle'), None)
    assert alpha is not None, 'Should have alpha-bundle bundle'
    tests = alpha.get('tests', [])
    assert len(tests) >= 1, 'Should find tests for alpha-bundle'


# =============================================================================
# Tests - Full Mode with Content Pattern (Subdocument Filtering)
# =============================================================================


def test_full_with_content_pattern_filters_subdocs(scan):
    """--full with --content-pattern filters subdocuments by the same pattern."""
    import json

    result = scan(
        '--direct-result',
        '--full',
        '--format',
        'json',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```json',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    for bundle in bundles_dict.values():
        for skill in bundle.get('skills', []):
            for subdir_name in ['standards', 'templates', 'references', 'knowledge', 'examples', 'documents']:
                for subdoc_path in skill.get(subdir_name, []):
                    subdoc_file = Path(subdoc_path)
                    if subdoc_file.exists():
                        content = subdoc_file.read_text()
                        assert '```json' in content, (
                            f"Subdoc {subdoc_path} should contain ```json when filtered with --content-pattern"
                        )


def test_full_without_content_pattern_includes_all_subdocs(scan):
    """--full without content pattern includes all subdocuments."""
    import json

    result = scan(
        '--direct-result',
        '--full',
        '--format',
        'json',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
    )
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    total_subdoc_files = 0
    for bundle in bundles_dict.values():
        for skill in bundle.get('skills', []):
            for subdir_name in ['standards', 'templates', 'references', 'knowledge', 'examples', 'documents']:
                total_subdoc_files += len(skill.get(subdir_name, []))

    # alpha-bundle's plan-alpha skill has a standards/ directory with two files.
    assert total_subdoc_files >= 1, 'Should include subdocuments with --full and no content pattern'


def test_full_content_pattern_excludes_non_matching_subdocs(scan):
    """--full --content-pattern excludes subdocs that don't match the pattern."""
    import json

    result_all = scan(
        '--direct-result',
        '--full',
        '--format',
        'json',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
    )
    assert result_all.returncode == 0
    data_all = json.loads(result_all.stdout)

    total_all = 0
    for bundle in data_all.get('bundles', {}).values():
        for skill in bundle.get('skills', []):
            for subdir_name in ['standards', 'templates', 'references', 'knowledge', 'examples', 'documents']:
                total_all += len(skill.get(subdir_name, []))

    result_filtered = scan(
        '--direct-result',
        '--full',
        '--format',
        'json',
        '--bundles',
        'alpha-bundle',
        '--resource-types',
        'skills',
        '--content-pattern',
        '```json',
    )
    assert result_filtered.returncode == 0
    data_filtered = json.loads(result_filtered.stdout)

    total_filtered = 0
    for bundle in data_filtered.get('bundles', {}).values():
        for skill in bundle.get('skills', []):
            for subdir_name in ['standards', 'templates', 'references', 'knowledge', 'examples', 'documents']:
                total_filtered += len(skill.get(subdir_name, []))

    # plan-alpha/standards/ has guide.md (```json) + plain.md (no fence); filtering
    # to ```json must drop plain.md, so the filtered count is strictly smaller.
    assert total_filtered < total_all, (
        f'Content-filtered subdocs ({total_filtered}) should be < total ({total_all})'
    )


# =============================================================================
# Tests - Path Resolution Regression (no cache fallback)
# =============================================================================
#
# These exercise the shared ``marketplace_paths`` helper directly with synthetic
# inputs — no real-tree walk — so they stay in the default unit suite. The
# git-root / real-tree resolution variants live in the sibling ``integration/``
# directory (excluded from the default run via the root conftest collect_ignore).


def test_find_marketplace_path_returns_none_outside_any_repo(tmp_path, monkeypatch):
    """find_marketplace_path() returns None when cwd is outside any git repo.

    With the script-relative anchor removed, an "outside-repo" cwd with no
    explicit anchor and no PM_MARKETPLACE_ROOT exhausts every branch: param
    (none) -> env (none) -> git-root (not a repo) -> cwd (no marketplace). The
    contract is fail-closed rather than silently anchoring on the helper's own
    file location.
    """
    from marketplace_paths import find_marketplace_path

    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    monkeypatch.chdir(tmp_path)
    result = find_marketplace_path()
    assert result is None, (
        f'Resolution from outside any git repo with no anchor should return None, got {result}'
    )


def test_find_marketplace_path_explicit_override_wins(tmp_path, monkeypatch):
    """The explicit marketplace_root parameter wins over env var and cwd discovery."""
    from marketplace_paths import find_marketplace_path

    fake_marketplace = tmp_path / 'fake_root'
    (fake_marketplace / 'marketplace' / 'bundles').mkdir(parents=True)

    monkeypatch.setenv('PM_MARKETPLACE_ROOT', '/nonexistent/env/value')
    result = find_marketplace_path(marketplace_root=fake_marketplace)
    assert result == fake_marketplace / 'marketplace' / 'bundles', (
        f'Explicit marketplace_root should take precedence over the env var, got {result}'
    )


def test_get_base_path_auto_resolves_explicit_anchor(tmp_path, monkeypatch):
    """get_base_path('auto') resolves the synthetic anchor via PM_MARKETPLACE_ROOT.

    Exercises the branch-2 (env-var anchor) path of find_marketplace_path
    without touching the real tree: a synthetic ``marketplace/bundles`` under
    ``tmp_path`` is resolved when PM_MARKETPLACE_ROOT points at it.
    """
    from marketplace_paths import get_base_path as shared_get_base_path

    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(tmp_path))
    result = shared_get_base_path('auto')
    assert result == tmp_path / 'marketplace' / 'bundles', (
        f"get_base_path('auto') should resolve the synthetic anchor, got {result}"
    )
