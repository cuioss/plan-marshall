#!/usr/bin/env python3
"""
Shared test infrastructure for plan-marshall marketplace scripts.

This module provides base classes, fixtures, and utilities for testing
Python scripts in the marketplace bundles. Uses only Python stdlib.

Usage:
    from conftest import ScriptTestCase, run_script, create_temp_file

See test/README.md for full documentation.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest import TestCase

# =============================================================================
# Path Constants
# =============================================================================

TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'
PLAN_DIR_NAME = '.plan'  # Configurable plan directory name
TEST_FIXTURE_BASE = PROJECT_ROOT / PLAN_DIR_NAME / 'temp' / 'test-fixture'


# =============================================================================
# Pytest Collection Configuration
# =============================================================================

# Pre-existing issues: duplicate test file basenames cause pytest collection errors
# These need to be renamed to unique names in a separate cleanup
collect_ignore = [
    # Duplicate: test_permission.py exists in permission-doctor and permission-fix
    'plan-marshall/permission-fix/test_permission.py',
    # Duplicate: test_discover_modules.py exists in multiple bundles
    'pm-dev-java/plan-marshall-plugin/test_discover_modules.py',
    # Duplicate: test_extension.py exists in extension-api and plugin-doctor
    'pm-plugin-development/plugin-doctor/test_extension.py',
    # Module structure issue: integration directories without proper __init__.py
    'pm-dev-frontend/integration/discover_modules/test_npm_discover_modules.py',
    'pm-dev-java/integration/discover_modules/test_gradle_discover_modules.py',
    'pm-dev-java/integration/discover_modules/test_maven_discover_modules.py',
    # Import issue: imports from non-existent 'extension' module
    'plan-marshall/integration/module_aggregation/test_hybrid_merge.py',
]


# =============================================================================
# Cross-Skill Import Setup (mirrors executor PYTHONPATH)
# =============================================================================


def _setup_marketplace_pythonpath() -> list[str]:
    """
    Set up sys.path for cross-skill imports, mirroring executor behavior.

    The executor (.plan/execute-script.py) builds PYTHONPATH from all script
    directories so scripts can import from any skill. This function does the
    same for tests.

    Returns:
        List of directories added to sys.path
    """
    script_dirs = set()

    # Scan marketplace for all scripts/ directories
    for bundle_dir in MARKETPLACE_ROOT.iterdir():
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.exists():
            continue
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / 'scripts'
            if scripts_dir.exists():
                script_dirs.add(str(scripts_dir))

    # Add to sys.path (avoid duplicates)
    added = []
    for script_dir in sorted(script_dirs):
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            added.append(script_dir)

    return added


# Set up PYTHONPATH immediately on import
_MARKETPLACE_SCRIPT_DIRS = _setup_marketplace_pythonpath()


# =============================================================================
# Script Runner
# =============================================================================


class ScriptResult:
    """Result from running a script."""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def success(self) -> bool:
        """True if script exited with code 0."""
        return self.returncode == 0

    def json(self) -> dict[str, Any]:
        """Parse stdout as JSON. Raises ValueError if invalid."""
        if not self.stdout.strip():
            raise ValueError(f'Empty stdout. stderr: {self.stderr}')
        data: dict[str, Any] = json.loads(self.stdout)
        return data

    def json_or_error(self) -> dict[str, Any]:
        """Parse stdout as JSON, or stderr if stdout is empty."""
        if self.stdout.strip():
            data: dict[str, Any] = json.loads(self.stdout)
            return data
        if self.stderr.strip():
            data = json.loads(self.stderr)
            return data
        return {'error': 'No output'}

    def __repr__(self) -> str:
        return f'ScriptResult(returncode={self.returncode}, stdout={len(self.stdout)}b, stderr={len(self.stderr)}b)'


def run_script(
    script_path: str | Path, *args: str, input_data: str | None = None, cwd: str | Path | None = None, timeout: int = 30
) -> ScriptResult:
    """
    Run a Python script and capture its output.

    Args:
        script_path: Path to the script to run
        *args: Command line arguments to pass
        input_data: Optional stdin input
        cwd: Working directory (defaults to current)
        timeout: Timeout in seconds (default 30)

    Returns:
        ScriptResult with returncode, stdout, stderr

    Example:
        result = run_script(SCRIPT_PATH, '--mode', 'structured', input_data=content)
        assert result.success
        data = result.json()
    """
    # Build environment with PYTHONPATH for cross-skill imports
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath

    result = subprocess.run(
        [sys.executable, str(script_path)] + list(args),
        capture_output=True,
        text=True,
        input=input_data,
        cwd=cwd,
        timeout=timeout,
        env=env,
    )
    return ScriptResult(result.returncode, result.stdout, result.stderr)


def get_script_path(bundle: str, skill: str, script: str) -> Path:
    """
    Get the path to a marketplace script.

    Args:
        bundle: Bundle name (e.g., 'pm-workflow')
        skill: Skill name (e.g., 'plan-files')
        script: Script filename (e.g., 'parse-plan.py')

    Returns:
        Absolute path to the script

    Raises:
        FileNotFoundError: If script doesn't exist
    """
    path = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts' / script
    if not path.exists():
        raise FileNotFoundError(f'Script not found: {path}')
    return path


# =============================================================================
# Temp File Helpers
# =============================================================================


def create_temp_file(content: str, suffix: str = '.md', dir: str | Path | None = None) -> Path:
    """
    Create a temporary file with content.

    Args:
        content: File content
        suffix: File extension (default .md)
        dir: Directory to create in (default system temp)

    Returns:
        Path to created file (caller must delete)

    Example:
        temp_file = create_temp_file("# Test\\nContent")
        try:
            result = run_script(SCRIPT, str(temp_file))
        finally:
            temp_file.unlink()
    """
    fd, path = tempfile.mkstemp(suffix=suffix, dir=dir)
    try:
        os.write(fd, content.encode('utf-8'))
    finally:
        os.close(fd)
    return Path(path)


def create_temp_dir() -> Path:
    """
    Create a temporary directory.

    Returns:
        Path to created directory (caller must delete with shutil.rmtree)
    """
    return Path(tempfile.mkdtemp())


# =============================================================================
# Base Test Case
# =============================================================================


class ScriptTestCase(TestCase):
    """
    Base class for script tests with common setup/teardown.

    Provides:
        - Automatic temp directory management
        - Script path resolution
        - Common assertion helpers

    Example:
        class TestParseConfig(ScriptTestCase):
            bundle = 'pm-workflow'
            skill = 'plan-files'
            script = 'parse-config.py'

            def test_basic_config(self):
                result = self.run_script_with_file(CONFIG_CONTENT)
                self.assert_success(result)
                data = result.json()
                self.assertEqual(data['plan_type'], 'implementation')
    """

    # Override in subclass
    bundle: str = ''
    skill: str = ''
    script: str = ''
    # Set dynamically by setUpClass/setUp
    script_path: Path | None = None
    temp_dir: Path
    temp_files: list[Path]

    @classmethod
    def setUpClass(cls):
        """Resolve script path once per test class."""
        if cls.bundle and cls.skill and cls.script:
            cls.script_path = get_script_path(cls.bundle, cls.skill, cls.script)
        else:
            cls.script_path = None

    def setUp(self):
        """Create temp directory for each test."""
        self.temp_dir = create_temp_dir()
        self.temp_files = []

    def tearDown(self):
        """Clean up temp files and directory."""
        for f in self.temp_files:
            try:
                f.unlink()
            except FileNotFoundError:
                pass
        try:
            shutil.rmtree(self.temp_dir)
        except FileNotFoundError:
            pass

    def create_temp_file(self, content: str, suffix: str = '.md') -> Path:
        """Create temp file tracked for cleanup."""
        path = create_temp_file(content, suffix=suffix, dir=self.temp_dir)
        self.temp_files.append(path)
        return path

    def run_script(self, *args: str, **kwargs) -> ScriptResult:
        """Run the test script with arguments."""
        if not self.script_path:
            raise ValueError('Set bundle, skill, script class attributes')
        return run_script(self.script_path, *args, **kwargs)

    def run_script_with_file(self, content: str, *extra_args: str, suffix: str = '.md') -> ScriptResult:
        """Create temp file with content and run script with it as first arg."""
        temp_file = self.create_temp_file(content, suffix=suffix)
        return self.run_script(str(temp_file), *extra_args)

    # Assertion helpers
    def assert_success(self, result: ScriptResult, msg: str | None = None):
        """Assert script succeeded."""
        self.assertEqual(result.returncode, 0, msg or f'Script failed: {result.stderr}')

    def assert_failure(self, result: ScriptResult, msg: str | None = None):
        """Assert script failed."""
        self.assertNotEqual(result.returncode, 0, msg or 'Expected script to fail')

    def assert_json_field(self, result: ScriptResult, field: str, expected: Any):
        """Assert JSON output has field with expected value."""
        data = result.json()
        self.assertIn(field, data, f'Missing field: {field}')
        self.assertEqual(data[field], expected, f'Field {field} mismatch')


# =============================================================================
# Pytest Fixtures
# =============================================================================

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_cwd():
    """Safety net fixture to restore cwd after each test.

    This ensures test isolation even if a test changes cwd without
    restoring it. Scripts should use script-relative paths, but this
    provides defense-in-depth against test pollution.
    """
    original_cwd = os.getcwd()
    yield
    if os.getcwd() != original_cwd:
        os.chdir(original_cwd)


@pytest.fixture
def fixture_dir(tmp_path):
    """
    Pytest-native temp directory fixture.

    Provides a temporary directory that is automatically cleaned up after the test.
    Use tmp_path directly for simple cases, or this fixture for consistency with
    legacy code.

    Returns:
        Path: Temporary directory path
    """
    return tmp_path


@pytest.fixture
def plan_context(tmp_path):
    """
    Pytest fixture for plan-based tests.

    Creates a plan directory structure and sets up the PLAN_BASE_DIR environment
    variable. Automatically cleans up after the test.

    Yields:
        PlanContext: Context object with fixture_dir, plan_id, and plan_dir attributes
    """
    plan_id = 'pytest-test'
    plan_dir = tmp_path / 'plans' / plan_id
    plan_dir.mkdir(parents=True)

    original_base = os.environ.get('PLAN_BASE_DIR')
    original_name = os.environ.get('PLAN_DIR_NAME')
    os.environ['PLAN_BASE_DIR'] = str(tmp_path)
    os.environ['PLAN_DIR_NAME'] = PLAN_DIR_NAME

    class Context:
        def __init__(self):
            self.fixture_dir = tmp_path
            self.plan_id = plan_id
            self.plan_dir = plan_dir

    yield Context()

    if original_base is None:
        os.environ.pop('PLAN_BASE_DIR', None)
    else:
        os.environ['PLAN_BASE_DIR'] = original_base
    if original_name is None:
        os.environ.pop('PLAN_DIR_NAME', None)
    else:
        os.environ['PLAN_DIR_NAME'] = original_name


@pytest.fixture
def build_context(tmp_path):
    """
    Pytest fixture for build-operations tests.

    Creates a complete test environment with .plan directory and marshal.json.
    Automatically cleans up after the test.

    Yields:
        BuildContext: Context object with temp_dir, plan_dir, and helper methods
    """
    ctx = BuildContext()
    ctx.temp_dir = tmp_path
    ctx.plan_dir = tmp_path / '.plan'
    ctx.plan_dir.mkdir()
    create_marshal_json(tmp_path)
    yield ctx


# =============================================================================
# Utilities
# =============================================================================


def assert_json_structure(data: dict, expected_keys: list, context: str = ''):
    """
    Assert JSON has expected top-level keys.

    Args:
        data: Parsed JSON dict
        expected_keys: List of required keys
        context: Optional context for error message
    """
    missing = [k for k in expected_keys if k not in data]
    if missing:
        raise AssertionError(f'Missing keys {missing} in {context or "data"}: {list(data.keys())}')


def load_fixture(fixture_path: str | Path) -> str:
    """Load fixture file content."""
    path = Path(fixture_path)
    if not path.is_absolute():
        # Assume relative to test file's directory
        path = Path(os.getcwd()) / path
    return path.read_text()


# =============================================================================
# Plan Test Context
# =============================================================================


def get_test_fixture_dir() -> Path:
    """
    Get the test fixture directory.

    When run via test/run-tests.py, uses the TEST_FIXTURE_DIR environment variable.
    When run standalone, creates a directory in .plan/temp/test-fixture/.

    Returns:
        Path to the test fixture directory
    """
    env_dir = os.environ.get('TEST_FIXTURE_DIR')
    if env_dir:
        return Path(env_dir)

    # Fallback for standalone execution
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    fixture_dir = TEST_FIXTURE_BASE / f'standalone-{timestamp}'
    fixture_dir.mkdir(parents=True, exist_ok=True)
    return fixture_dir


class PlanContext:
    """
    Context manager for tests that need PLAN_BASE_DIR.

    Uses centralized test fixture directory instead of system temp.
    When run via test/run-tests.py, the fixture directory is managed
    by the runner and cleaned up automatically after all tests.

    Usage:
        with PlanContext(plan_id='my-plan') as ctx:
            result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'my-plan', ...)
            # ctx.fixture_dir contains the base directory
            # ctx.plan_dir contains the plan directory

    Attributes:
        fixture_dir: Base test fixture directory
        plan_id: The plan identifier
        plan_dir: Path to .../plans/{plan_id}
    """

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self, plan_id: str = 'test-plan'):
        """
        Initialize the test context.

        Args:
            plan_id: Plan identifier (kebab-case)
        """
        self.plan_id = plan_id
        self.fixture_dir: Path | None = None
        self.plan_dir: Path | None = None
        self._original_plan_base_dir: str | None = None
        self._is_standalone: bool = False

    def __enter__(self) -> 'PlanContext':
        """Set up the test context."""
        self.fixture_dir = get_test_fixture_dir()
        self._is_standalone = 'TEST_FIXTURE_DIR' not in os.environ

        # Create plan directory structure
        self.plan_dir = self.fixture_dir / 'plans' / self.plan_id
        self.plan_dir.mkdir(parents=True, exist_ok=True)

        # Set PLAN_BASE_DIR and PLAN_DIR_NAME environment variables
        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        self._original_plan_dir_name = os.environ.get('PLAN_DIR_NAME')
        os.environ['PLAN_BASE_DIR'] = str(self.fixture_dir)
        os.environ['PLAN_DIR_NAME'] = PLAN_DIR_NAME

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test context."""
        # Clean up the plan_dir to ensure test isolation
        # (when via runner, fixture_dir is shared but each test should get fresh plan_dir)
        if self.plan_dir and self.plan_dir.exists():
            shutil.rmtree(self.plan_dir, ignore_errors=True)

        # Clean up common files and directories to ensure test isolation
        if self.fixture_dir:
            files_to_clean = ['marshal.json', 'raw-project-data.json']
            for filename in files_to_clean:
                filepath = self.fixture_dir / filename
                if filepath.exists():
                    filepath.unlink()
            # Clean up directories that tests may create
            dirs_to_clean = [
                'project-architecture',
                PLAN_DIR_NAME,  # .plan directory - critical for run-config tests
            ]
            for dirname in dirs_to_clean:
                dirpath = self.fixture_dir / dirname
                if dirpath.exists():
                    shutil.rmtree(dirpath, ignore_errors=True)

        # Restore original PLAN_BASE_DIR
        if self._original_plan_base_dir is None:
            os.environ.pop('PLAN_BASE_DIR', None)
        else:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir

        # Restore original PLAN_DIR_NAME
        if self._original_plan_dir_name is None:
            os.environ.pop('PLAN_DIR_NAME', None)
        else:
            os.environ['PLAN_DIR_NAME'] = self._original_plan_dir_name

        # Only cleanup fixture_dir if running standalone (not via run-tests.py)
        if self._is_standalone and self.fixture_dir and self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir, ignore_errors=True)


# =============================================================================
# Marshal.json Schema Constants
# =============================================================================

# Key names - use these constants instead of hardcoding strings
MARSHAL_KEY_SKILL_DOMAINS = 'skill_domains'
MARSHAL_KEY_SYSTEM = 'system'
MARSHAL_KEY_PLAN = 'plan'

# Default schema for marshal.json
MARSHAL_SCHEMA_DEFAULT: dict[str, Any] = {
    MARSHAL_KEY_SKILL_DOMAINS: {'system': {}},
    MARSHAL_KEY_SYSTEM: {'retention': {}},
    MARSHAL_KEY_PLAN: {
        'phase-1-init': {'branch_strategy': 'direct'},
        'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
        'phase-5-execute': {
            'commit_strategy': 'per_deliverable',
            'verification_max_iterations': 5,
            'verification_1_quality_check': True,
            'verification_2_build_verify': True,
            'verification_domain_steps': {},
        },
        'phase-6-finalize': {
            'max_iterations': 3,
            '1_commit_push': True,
            '2_create_pr': True,
            '3_automated_review': True,
            '4_sonar_roundtrip': True,
            '5_knowledge_capture': True,
            '6_lessons_capture': True,
        },
    },
}


def create_marshal_json(base_dir: Path, skill_domains: dict | None = None, extra: dict | None = None) -> Path:
    """
    Create marshal.json with proper schema.

    Args:
        base_dir: Directory to create .plan/marshal.json in (or directory containing marshal.json)
        skill_domains: Skill domains dict (optional, defaults to {"system": {}})
        extra: Additional top-level keys to merge (optional)

    Returns:
        Path to created marshal.json

    Example:
        marshal_path = create_marshal_json(temp_dir, skill_domains={
            "system": {"defaults": [...], "task_executors": {...}}
        })
    """
    # Determine the correct location for marshal.json
    plan_dir = base_dir / '.plan'
    if not plan_dir.exists():
        plan_dir.mkdir(parents=True)
    marshal_path = plan_dir / 'marshal.json'

    # Build the data structure
    data = MARSHAL_SCHEMA_DEFAULT.copy()
    if skill_domains is not None:
        data[MARSHAL_KEY_SKILL_DOMAINS] = skill_domains
    if extra:
        data.update(extra)

    marshal_path.write_text(json.dumps(data, indent=2))
    return marshal_path


def create_raw_project_data(
    base_dir: Path,
    modules: list | None = None,
    module_details: dict | None = None,
    project_name: str | None = None,
    frameworks: list | None = None,
) -> Path:
    """
    Create raw-project-data.json with module facts.

    Args:
        base_dir: Directory to create .plan/raw-project-data.json in
        modules: List of module dicts with name, path, build_systems, packaging
        module_details: Dict of module_name -> enrichment data (packages, dependencies)
        project_name: Project name (defaults to base_dir.name)
        frameworks: List of detected frameworks

    Returns:
        Path to created raw-project-data.json

    Example:
        raw_data_path = create_raw_project_data(temp_dir, modules=[
            {"name": "core", "path": "core", "build_systems": ["maven"], "packaging": "jar"},
            {"name": "web", "path": "web", "build_systems": ["maven"], "packaging": "war"}
        ])
    """
    plan_dir = base_dir / '.plan'
    if not plan_dir.exists():
        plan_dir.mkdir(parents=True)
    raw_data_path = plan_dir / 'raw-project-data.json'

    data = {
        'project': {'name': project_name or base_dir.name},
        'frameworks': frameworks or [],
        'documentation': {'readme': '', 'doc_files': []},
        'modules': modules or [],
        'module_details': module_details or {},
    }

    raw_data_path.write_text(json.dumps(data, indent=2))
    return raw_data_path


# =============================================================================
# Build Test Context
# =============================================================================


class BuildContext:
    """
    Context manager for build-operations tests.

    Provides a complete test environment with:
    - Temporary directory for project files
    - .plan directory with marshal.json
    - Optional raw-project-data.json
    - Automatic cleanup

    Usage:
        with BuildContext() as ctx:
            # Create a pom.xml
            (ctx.temp_dir / 'pom.xml').write_text('<project></project>')

            # Run project-structure script
            result = run_script(SCRIPT_PATH, 'collect-raw-data', '--project-root', str(ctx.temp_dir))

            # Check marshal.json
            config = ctx.load_marshal_json()
            assert 'skill_domains' in config

    Attributes:
        temp_dir: Root directory for test files
        plan_dir: The .plan directory
    """

    __test__ = False  # Not a test class - prevent pytest collection warning

    def __init__(self, modules: list | None = None, module_details: dict | None = None):
        """
        Initialize the build test context.

        Args:
            modules: Initial modules list for raw-project-data.json
            module_details: Initial module_details for raw-project-data.json
        """
        self.temp_dir: Path | None = None
        self.plan_dir: Path | None = None
        self._initial_modules = modules
        self._initial_module_details = module_details

    def __enter__(self) -> 'BuildContext':
        """Set up the test context."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plan_dir = self.temp_dir / '.plan'
        self.plan_dir.mkdir()

        # Create initial marshal.json
        create_marshal_json(self.temp_dir)

        # Create raw-project-data.json if modules provided
        if self._initial_modules is not None:
            create_raw_project_data(
                self.temp_dir, modules=self._initial_modules, module_details=self._initial_module_details
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the test context."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def load_marshal_json(self) -> dict[str, Any]:
        """Load and return the current marshal.json content."""
        assert self.plan_dir is not None, 'BuildContext not entered'
        marshal_path = self.plan_dir / 'marshal.json'
        if not marshal_path.exists():
            raise FileNotFoundError(f'marshal.json not found at {marshal_path}')
        data: dict[str, Any] = json.loads(marshal_path.read_text())
        return data

    def load_raw_project_data(self) -> dict[str, Any]:
        """Load and return the current raw-project-data.json content."""
        assert self.plan_dir is not None, 'BuildContext not entered'
        raw_data_path = self.plan_dir / 'raw-project-data.json'
        if not raw_data_path.exists():
            raise FileNotFoundError(f'raw-project-data.json not found at {raw_data_path}')
        data: dict[str, Any] = json.loads(raw_data_path.read_text())
        return data

    def create_pom(
        self,
        path: str = '.',
        packaging: str = 'jar',
        artifact_id: str = 'test-module',
        with_quarkus: bool = False,
        profiles: list | None = None,
    ) -> Path:
        """
        Create a pom.xml file.

        Args:
            path: Relative path from temp_dir (default: root)
            packaging: Maven packaging type (jar, war, pom)
            artifact_id: Artifact ID
            with_quarkus: Include Quarkus plugin
            profiles: List of profile IDs to include

        Returns:
            Path to created pom.xml
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Build pom content
        parts = ['<project>']
        if packaging != 'jar':  # jar is default, no need to specify
            parts.append(f'  <packaging>{packaging}</packaging>')
        parts.append(f'  <artifactId>{artifact_id}</artifactId>')

        if with_quarkus:
            parts.append("""  <build>
    <plugins>
      <plugin>
        <groupId>io.quarkus</groupId>
        <artifactId>quarkus-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>""")

        if profiles:
            parts.append('  <profiles>')
            for profile_id in profiles:
                parts.append(f"""    <profile>
      <id>{profile_id}</id>
    </profile>""")
            parts.append('  </profiles>')

        parts.append('</project>')

        pom_path = target_dir / 'pom.xml'
        pom_path.write_text('\n'.join(parts))
        return pom_path

    def create_parent_pom(self, modules: list) -> Path:
        """
        Create a parent pom.xml with modules section.

        Args:
            modules: List of module directory names

        Returns:
            Path to created pom.xml
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        modules_xml = '\n'.join(f'    <module>{m}</module>' for m in modules)
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
{modules_xml}
  </modules>
</project>"""
        pom_path = self.temp_dir / 'pom.xml'
        pom_path.write_text(content)
        return pom_path

    def create_package_json(self, path: str = '.', name: str = 'test-module', version: str = '1.0.0') -> Path:
        """
        Create a package.json file.

        Args:
            path: Relative path from temp_dir (default: root)
            name: Package name
            version: Package version

        Returns:
            Path to created package.json
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        content = json.dumps({'name': name, 'version': version}, indent=2)
        pkg_path = target_dir / 'package.json'
        pkg_path.write_text(content)
        return pkg_path

    def create_build_gradle(
        self, path: str = '.', with_war: bool = False, with_quarkus: bool = False, kotlin: bool = False
    ) -> Path:
        """
        Create a build.gradle or build.gradle.kts file.

        Args:
            path: Relative path from temp_dir (default: root)
            with_war: Include war plugin
            with_quarkus: Include Quarkus plugin
            kotlin: Use Kotlin DSL (.kts)

        Returns:
            Path to created build file
        """
        assert self.temp_dir is not None, 'BuildContext not entered'
        target_dir = self.temp_dir / path if path != '.' else self.temp_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        if kotlin:
            plugins = ['java']
            if with_war:
                plugins.append('war')
            if with_quarkus:
                plugins.append('id("io.quarkus")')
            plugin_lines = '\n    '.join(plugins)
            content = f"""plugins {{
    {plugin_lines}
}}"""
            filename = 'build.gradle.kts'
        else:
            plugins = ['"java"']
            if with_war:
                plugins.append('"war"')
            plugin_block = ' '.join(f'id {p}' for p in plugins)
            content = f'plugins {{ {plugin_block} }}'
            if with_quarkus:
                content = 'plugins { id "java"\n    id "io.quarkus" }'
            filename = 'build.gradle'

        build_path = target_dir / filename
        build_path.write_text(content)
        return build_path
