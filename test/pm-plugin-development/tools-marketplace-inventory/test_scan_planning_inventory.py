#!/usr/bin/env python3
"""Tests for scan-planning-inventory.py script.

In-process unit tests: the script's ``main()`` is loaded via
``load_script_module`` and driven against a SMALL synthetic marketplace built
once per session under a ``tmp_path_factory`` directory (see the
``synthetic_marketplace`` / ``scan`` fixtures).

``scan-planning-inventory.py`` shells out to its sibling
``scan-marketplace-inventory.py`` via ``subprocess.run`` with a fixed
``--bundles plan-marshall,pm-plugin-development`` + planning ``--name-pattern``
filter. We anchor that inner subprocess to the synthetic tree by:

- setting ``PM_MARKETPLACE_ROOT`` so the subprocess's
  ``get_base_path('auto')`` resolves the synthetic ``marketplace/bundles`` tree
  (branch 2 of the four-step resolution chain), short-circuiting before any
  git-root / cwd discovery that would reach the real repo, and
- exporting ``PYTHONPATH`` (the same script dirs ``conftest`` already added to
  ``sys.path``) into ``os.environ`` so the spawned interpreter can import the
  shared ``marketplace_paths`` / ``file_ops`` / ``toon_parser`` modules, and
- ``chdir``-ing into the synthetic root so ``safe_relative_path`` yields
  repo-relative paths exactly as in production.

This replaces the previous Tier-3 design where every test re-ran a real
whole-marketplace planning scan (~16 scans, each spawning a second subprocess
that re-walked the REAL ``marketplace/bundles/`` tree). The single retained
real-tree smoke lives in the sibling ``integration/`` directory and is excluded
from the default ``module-tests`` run via the root conftest's ``collect_ignore``
list.

Synthetic planning shape (only the two scanned PLANNING_BUNDLES carry planning
components; the java/frontend bundles are present so the "not in derived"
assertion exercises a real categorization pass):

Core bundle ``plan-marshall`` planning components (all match a planning
name-pattern):
- skills (8): ``plan-marshall`` (user-invocable), ``manage-tasks``,
  ``manage-files``, ``manage-config``, ``manage-status``, ``manage-lessons``,
  ``execute-task``, ``workflow-pr-doctor`` (user-invocable).
- agents (1): ``plan-agent``.
- commands (1): ``manage-cmd``.
- scripts (1 public): ``manage-tasks/scripts/manage-tasks.py`` (``_helper.py``
  is private and excluded).

Derived bundle ``pm-plugin-development`` planning components:
- skills (2): ``plugin-task-plan`` (``*-task-plan``), ``plugin-plan-implement``
  (``*-plan-*``).

Non-planning bundles (NOT in PLANNING_BUNDLES, never categorized):
- ``pm-dev-java`` (skill ``java-core``), ``pm-dev-frontend`` (skill
  ``javascript``).

Derived counts: bundles=1, agents=0, commands=0, skills=2, scripts=0, total=2.
Core counts: agents=1, commands=1, skills=8, scripts=1, total=11.
total_components = 11 + 2 = 13.
"""

from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

# Import shared infrastructure (conftest.py sets up PYTHONPATH and exposes
# the script-dir list the inner subprocess needs on its own PYTHONPATH).
from conftest import _MARKETPLACE_SCRIPT_DIRS, load_script_module

# =============================================================================
# Expected synthetic counts (single source of truth for the assertions)
# =============================================================================

EXPECTED_CORE_SKILLS = 8
EXPECTED_CORE_AGENTS = 1
EXPECTED_CORE_COMMANDS = 1
EXPECTED_CORE_SCRIPTS = 1
EXPECTED_CORE_TOTAL = (
    EXPECTED_CORE_SKILLS + EXPECTED_CORE_AGENTS + EXPECTED_CORE_COMMANDS + EXPECTED_CORE_SCRIPTS
)

EXPECTED_DERIVED_BUNDLES = 1
EXPECTED_DERIVED_SKILLS = 2
EXPECTED_DERIVED_AGENTS = 0
EXPECTED_DERIVED_COMMANDS = 0
EXPECTED_DERIVED_SCRIPTS = 0
EXPECTED_DERIVED_TOTAL = (
    EXPECTED_DERIVED_SKILLS + EXPECTED_DERIVED_AGENTS + EXPECTED_DERIVED_COMMANDS + EXPECTED_DERIVED_SCRIPTS
)

EXPECTED_TOTAL_COMPONENTS = EXPECTED_CORE_TOTAL + EXPECTED_DERIVED_TOTAL


# =============================================================================
# Synthetic marketplace builder
# =============================================================================

_PLUGIN_JSON = '{\n  "name": "{name}",\n  "version": "0.1.0"\n}\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _skill(bundle: Path, name: str, *, user_invocable: bool = False) -> None:
    """Write a minimal SKILL.md for ``name`` under ``bundle``."""
    invocable_line = f'user-invocable: {"true" if user_invocable else "false"}\n'
    _write(
        bundle / 'skills' / name / 'SKILL.md',
        f'---\nname: {name}\ndescription: {name} skill\n{invocable_line}---\n# {name}\n',
    )


def _build_synthetic_marketplace(root: Path) -> Path:
    """Create a minimal synthetic ``marketplace/bundles`` tree under ``root``.

    Returns the ``marketplace/bundles`` directory path. See the module docstring
    for the exact shape and the resource counts the assertions rely on.
    """
    bundles = root / 'marketplace' / 'bundles'

    # ----- plan-marshall (core) ---------------------------------------------
    core = bundles / 'plan-marshall'
    _write(core / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'plan-marshall'))

    # skills (8) — all match a planning name-pattern
    _skill(core, 'plan-marshall', user_invocable=True)
    _skill(core, 'manage-tasks')
    _skill(core, 'manage-files')
    _skill(core, 'manage-config')
    _skill(core, 'manage-status')
    _skill(core, 'manage-lessons')
    _skill(core, 'execute-task')
    _skill(core, 'workflow-pr-doctor', user_invocable=True)

    # one public script under manage-tasks (matches manage-*); _helper.py excluded
    _write(
        core / 'skills' / 'manage-tasks' / 'scripts' / 'manage-tasks.py',
        '#!/usr/bin/env python3\nprint("manage-tasks")\n',
    )
    _write(
        core / 'skills' / 'manage-tasks' / 'scripts' / '_helper.py',
        '# private module, must be excluded\n',
    )

    # one agent + one command, both matching a planning name-pattern
    _write(
        core / 'agents' / 'plan-agent.md',
        '---\nname: plan-agent\ndescription: Planning agent\n---\n# Plan Agent\n',
    )
    _write(
        core / 'commands' / 'manage-cmd.md',
        '---\nname: manage-cmd\ndescription: Manage command\n---\n# Manage Command\n',
    )

    # ----- pm-plugin-development (derived) ----------------------------------
    plugin = bundles / 'pm-plugin-development'
    _write(plugin / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'pm-plugin-development'))
    _skill(plugin, 'plugin-task-plan')  # matches *-task-plan
    _skill(plugin, 'plugin-plan-implement')  # matches *-plan-*
    # a non-planning skill that must NOT be matched by any planning pattern
    _skill(plugin, 'plugin-architecture')

    # ----- pm-dev-java / pm-dev-frontend (NOT in PLANNING_BUNDLES) -----------
    java = bundles / 'pm-dev-java'
    _write(java / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'pm-dev-java'))
    _skill(java, 'java-core')

    frontend = bundles / 'pm-dev-frontend'
    _write(frontend / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON.replace('{name}', 'pm-dev-frontend'))
    _skill(frontend, 'javascript')

    return bundles


# =============================================================================
# In-process driver
# =============================================================================


class _ScanResult:
    """Result of an in-process ``main()`` invocation."""

    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ''


def _planning_module():
    """Load the scan-planning-inventory module in-process."""
    return load_script_module(
        'pm-plugin-development',
        'tools-marketplace-inventory',
        'scan-planning-inventory.py',
    )


def _make_runner(module, monkeypatch, capsys):
    """Return a ``run(*args)`` callable driving ``module.main()`` in-process.

    Sets ``sys.argv`` to the synthetic command line, invokes ``main()`` (which
    always ``sys.exit``s via the ``@safe_main`` wrapper), and captures stdout.
    The script's internal ``subprocess.run`` to ``scan-marketplace-inventory.py``
    inherits ``os.environ`` (with ``PM_MARKETPLACE_ROOT`` + ``PYTHONPATH`` set by
    the ``synthetic_marketplace`` fixture) and therefore resolves the synthetic
    tree, not the real one.
    """

    def run(*args: str) -> _ScanResult:
        import sys

        # Drain output buffered from a previous call so capsys.readouterr()
        # returns only this invocation's stdout.
        capsys.readouterr()
        monkeypatch.setattr(sys, 'argv', ['scan-planning-inventory.py', *args])
        code = 0
        try:
            module.main()
        except SystemExit as exc:  # @safe_main always exits
            code = int(exc.code) if exc.code is not None else 0
        captured = capsys.readouterr()
        return _ScanResult(code, captured.out)

    return run


@pytest.fixture
def synthetic_marketplace(tmp_path, monkeypatch):
    """Build a synthetic marketplace under ``tmp_path`` and anchor the scan to it.

    - Sets ``PM_MARKETPLACE_ROOT`` so both the in-process ``get_base_path`` calls
      and the spawned ``scan-marketplace-inventory.py`` subprocess resolve the
      synthetic ``marketplace/bundles`` tree.
    - Exports ``PYTHONPATH`` (the conftest script-dir list) so the subprocess can
      import the shared ``marketplace_paths`` / ``file_ops`` / ``toon_parser``
      modules.
    - ``chdir``s into the synthetic root so ``safe_relative_path`` yields
      repo-relative paths matching production output.

    Yields the ``marketplace/bundles`` directory.
    """
    import os

    bundles = _build_synthetic_marketplace(tmp_path)
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(tmp_path))

    # The inner subprocess needs the shared script dirs on PYTHONPATH. conftest
    # added them to this process's sys.path but not to os.environ; export them
    # (preserving any pre-existing PYTHONPATH) so the child interpreter inherits.
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    existing = os.environ.get('PYTHONPATH')
    if existing:
        pythonpath = pythonpath + os.pathsep + existing
    monkeypatch.setenv('PYTHONPATH', pythonpath)

    monkeypatch.chdir(tmp_path)
    yield bundles


@pytest.fixture
def scan(synthetic_marketplace, monkeypatch, capsys):
    """In-process ``run(*args)`` driver bound to the synthetic marketplace."""
    module = _planning_module()
    return _make_runner(module, monkeypatch, capsys)


# =============================================================================
# Tests - Basic Execution
# =============================================================================


def test_default_execution_succeeds(scan):
    """Test default execution completes successfully against the synthetic tree."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'


def test_default_produces_valid_toon(scan):
    """Test default mode produces valid TOON."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'Default mode should produce valid TOON: {e}') from e


# =============================================================================
# Tests - Output Structure
# =============================================================================


def test_full_format_has_required_fields(scan):
    """Test full format has required top-level fields."""
    result = scan('--format', 'full')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    assert 'patterns' in data, 'Should have patterns field'
    assert 'bundles_scanned' in data, 'Should have bundles_scanned field'
    assert 'core' in data, 'Should have core field'
    assert 'derived' in data, 'Should have derived field'
    assert 'statistics' in data, 'Should have statistics field'


def test_core_has_required_fields(scan):
    """Test core section has required fields."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core = data.get('core', {})
    assert 'bundle' in core, 'Core should have bundle field'
    assert core['bundle'] == 'plan-marshall', "Core bundle should be 'plan-marshall'"
    assert 'agents' in core, 'Core should have agents field'
    assert 'commands' in core, 'Core should have commands field'
    assert 'skills' in core, 'Core should have skills field'


def test_derived_is_list(scan):
    """Test derived section is a list."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    derived = data.get('derived', [])
    assert isinstance(derived, list), 'Derived should be a list'


def test_statistics_has_required_fields(scan):
    """Test statistics section has required fields."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    stats = data.get('statistics', {})
    assert 'core' in stats, 'Statistics should have core field'
    assert 'derived' in stats, 'Statistics should have derived field'
    assert 'total_components' in stats, 'Statistics should have total_components field'


# =============================================================================
# Tests - Core Components
# =============================================================================


def test_core_has_plan_skills(scan):
    """Test core bundle contains planning-related skills (plan-/manage-/task-)."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    planning_skills = [s for s in skill_names if 'plan' in s or s.startswith('manage-') or s.startswith('task-')]
    # plan-marshall + 5 manage-* = 6 planning-related skills in the synthetic core.
    assert len(planning_skills) == 6, f'Expected 6 planning-related skills, found {len(planning_skills)}'


def test_core_has_manage_skills(scan):
    """Test core bundle contains manage-* skills."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    manage_skills = [s for s in skill_names if s.startswith('manage-')]
    # Synthetic core has exactly 5 manage-* skills.
    assert len(manage_skills) == 5, f'Expected 5 manage-* skills, found {len(manage_skills)}'


def test_core_has_workflow_skills(scan):
    """Test core bundle contains execute-* skills for workflow execution."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    execute_skills = [s for s in skill_names if s.startswith('execute-')]
    assert len(execute_skills) == 1, f'Expected 1 execute-* skill, found {len(execute_skills)}'
    assert 'execute-task' in skill_names, 'Should have execute-task skill'


def test_core_has_user_invocable_skills(scan):
    """Test core bundle contains user-invocable skills (commands were absorbed into skills)."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])

    skill_names = [s['name'] for s in core_skills]
    expected_skills = ['execute-task', 'workflow-pr-doctor', 'plan-marshall']
    for expected in expected_skills:
        assert expected in skill_names, f'Should have {expected} skill'


def test_core_skill_count_is_exact(scan):
    """Test core skill count equals the synthetic count."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    assert len(core_skills) == EXPECTED_CORE_SKILLS, (
        f'Expected {EXPECTED_CORE_SKILLS} core skills, found {len(core_skills)}'
    )


# =============================================================================
# Tests - Derived Components
# =============================================================================


def test_derived_plugin_has_plan_components(scan):
    """Test pm-plugin-development derived bundle has plan components."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    derived = data.get('derived', [])

    plugin_bundle = next((d for d in derived if d['bundle'] == 'pm-plugin-development'), None)
    assert plugin_bundle is not None, 'Should find pm-plugin-development in derived'

    skill_names = [s['name'] for s in plugin_bundle.get('skills', [])]
    assert 'plugin-task-plan' in skill_names, 'Should have plugin-task-plan skill'
    assert 'plugin-plan-implement' in skill_names, 'Should have plugin-plan-implement skill'
    # plugin-architecture does not match any planning pattern and must be filtered out.
    assert 'plugin-architecture' not in skill_names, 'Non-planning skill should be filtered out'


def test_java_and_frontend_not_in_derived(scan):
    """Test pm-dev-java and pm-dev-frontend are NOT in derived (not planning bundles)."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    derived = data.get('derived', [])
    bundle_names = [d['bundle'] for d in derived]

    assert 'pm-dev-java' not in bundle_names, 'pm-dev-java should NOT be in derived'
    assert 'pm-dev-frontend' not in bundle_names, 'pm-dev-frontend should NOT be in derived'


def test_derived_includes_plugin_tools(scan):
    """Test derived includes pm-plugin-development bundle."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    derived = data.get('derived', [])
    bundle_names = [d['bundle'] for d in derived]
    assert 'pm-plugin-development' in bundle_names, 'Derived should include pm-plugin-development'


# =============================================================================
# Tests - Summary Format
# =============================================================================


def test_summary_format_has_required_fields(scan):
    """Test summary format has required fields."""
    result = scan('--format', 'summary')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    assert 'core_bundle' in data, 'Summary should have core_bundle field'
    assert 'core_components' in data, 'Summary should have core_components field'
    assert 'derived_bundles' in data, 'Summary should have derived_bundles field'
    assert 'statistics' in data, 'Summary should have statistics field'


def test_summary_core_components_structure(scan):
    """Test summary core_components has correct structure."""
    result = scan('--format', 'summary')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_components = data.get('core_components', [])

    assert isinstance(core_components, list), 'core_components should be a list'
    for component in core_components:
        assert 'type' in component, 'Each component should have type'
        assert 'names' in component, 'Each component should have names'
        assert isinstance(component['names'], list), 'names should be a list'


def test_summary_derived_bundles_structure(scan):
    """Test summary derived_bundles has correct structure."""
    result = scan('--format', 'summary')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    derived_bundles = data.get('derived_bundles', [])

    assert isinstance(derived_bundles, list), 'derived_bundles should be a list'
    for bundle in derived_bundles:
        assert 'bundle' in bundle, 'Each derived bundle should have bundle name'


# =============================================================================
# Tests - Statistics
# =============================================================================


def test_statistics_totals_are_consistent(scan):
    """Test statistics totals are consistent with component counts."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    stats = data.get('statistics', {})
    core = data.get('core', {})
    derived = data.get('derived', [])

    core_stats = stats.get('core', {})
    assert core_stats.get('agents') == len(core.get('agents', [])), 'Core agent count mismatch'
    assert core_stats.get('commands') == len(core.get('commands', [])), 'Core command count mismatch'
    assert core_stats.get('skills') == len(core.get('skills', [])), 'Core skill count mismatch'

    derived_stats = stats.get('derived', {})
    actual_derived_agents = sum(len(d.get('agents', [])) for d in derived)
    assert derived_stats.get('agents') == actual_derived_agents, 'Derived agent count mismatch'


def test_statistics_match_synthetic_counts(scan):
    """Test statistics equal the exact synthetic component counts."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    stats = data.get('statistics', {})

    core_stats = stats.get('core', {})
    assert core_stats.get('agents') == EXPECTED_CORE_AGENTS, 'Core agents mismatch'
    assert core_stats.get('commands') == EXPECTED_CORE_COMMANDS, 'Core commands mismatch'
    assert core_stats.get('skills') == EXPECTED_CORE_SKILLS, 'Core skills mismatch'
    assert core_stats.get('scripts') == EXPECTED_CORE_SCRIPTS, 'Core scripts mismatch'
    assert core_stats.get('total') == EXPECTED_CORE_TOTAL, 'Core total mismatch'

    derived_stats = stats.get('derived', {})
    assert derived_stats.get('bundles') == EXPECTED_DERIVED_BUNDLES, 'Derived bundles mismatch'
    assert derived_stats.get('skills') == EXPECTED_DERIVED_SKILLS, 'Derived skills mismatch'
    assert derived_stats.get('total') == EXPECTED_DERIVED_TOTAL, 'Derived total mismatch'

    assert stats.get('total_components') == EXPECTED_TOTAL_COMPONENTS, 'total_components mismatch'


def test_total_components_is_sum(scan):
    """Test total_components equals core + derived totals."""
    result = scan()
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    stats = data.get('statistics', {})

    core_total = stats.get('core', {}).get('total', 0)
    derived_total = stats.get('derived', {}).get('total', 0)
    total_components = stats.get('total_components', 0)

    assert total_components == core_total + derived_total, (
        f'Total components ({total_components}) should equal core ({core_total}) + derived ({derived_total})'
    )


# =============================================================================
# Tests - Description Extraction
# =============================================================================


def test_include_descriptions_adds_descriptions(scan):
    """Test --include-descriptions adds description fields."""
    result = scan('--include-descriptions')
    assert result.returncode == 0, f'Script returned error: {result.stdout}'

    data = parse_toon(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])

    skills_with_desc = [s for s in core_skills if s.get('description')]
    assert len(skills_with_desc) > 0, 'Should have at least one skill with description'
