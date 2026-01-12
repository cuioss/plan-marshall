#!/usr/bin/env python3
"""Tests for project detection in plan-marshall-config.

Tests auto-detection of build systems and domains from project files.
Module detection is now handled by project-structure skill creating raw-project-data.json.

Architecture:
- raw-project-data.json: Single source of truth for module facts (from project-structure skill)
- marshal.json: Contains module_config for command configuration
- plan-marshall-config: Reads module facts from raw-project-data.json
"""

import json
import shutil
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH


# =============================================================================
# Test Cleanup - Ensure Isolation Between Tests
# =============================================================================

def cleanup_project_files(fixture_dir: Path) -> None:
    """Remove all project files from fixture directory to ensure test isolation.

    When tests run via run-tests.py, they share a fixture directory.
    This function ensures clean state before each test.
    """
    # Remove root build files
    for filename in ['pom.xml', 'package.json', 'build.gradle', 'build.gradle.kts']:
        filepath = fixture_dir / filename
        if filepath.exists():
            filepath.unlink()

    # Remove module directories
    for module_name in ['core', 'api', 'web', 'ui', 'e2e']:
        module_dir = fixture_dir / module_name
        if module_dir.exists():
            shutil.rmtree(module_dir)

    # Remove raw-project-data.json if exists
    raw_data = fixture_dir / 'raw-project-data.json'
    if raw_data.exists():
        raw_data.unlink()


# =============================================================================
# Test Fixtures - Project Structure Creators
# =============================================================================

def create_simple_maven_project(fixture_dir: Path) -> None:
    """Create a simple single-module Maven project."""
    pom_content = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>simple-app</artifactId>
    <version>1.0.0</version>
</project>'''
    (fixture_dir / 'pom.xml').write_text(pom_content)


def create_simple_npm_project(fixture_dir: Path) -> None:
    """Create a simple npm project."""
    package_content = json.dumps({
        "name": "simple-app",
        "version": "1.0.0"
    }, indent=2)
    (fixture_dir / 'package.json').write_text(package_content)


def create_mixed_multi_module_project(fixture_dir: Path) -> None:
    """Create a multi-module Maven project with nested npm modules.

    Structure like nifi-extensions:
    - Root pom.xml (maven parent)
    - core/ (Java only)
    - api/ (Java only)
    - ui/ (Java + JavaScript - has package.json)
    - e2e/ (Java + JavaScript - has package.json for playwright)
    """
    root_pom = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>mixed-multi-module</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>
    <modules>
        <module>core</module>
        <module>api</module>
        <module>ui</module>
        <module>e2e</module>
    </modules>
</project>'''
    (fixture_dir / 'pom.xml').write_text(root_pom)

    # Java-only modules
    for module in ['core', 'api']:
        module_dir = fixture_dir / module
        module_dir.mkdir(parents=True, exist_ok=True)
        module_pom = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>mixed-multi-module</artifactId>
        <version>1.0.0</version>
    </parent>
    <artifactId>{module}</artifactId>
</project>'''
        (module_dir / 'pom.xml').write_text(module_pom)

    # Java + JavaScript modules (have both pom.xml and package.json)
    for module in ['ui', 'e2e']:
        module_dir = fixture_dir / module
        module_dir.mkdir(parents=True, exist_ok=True)

        # Maven pom.xml
        module_pom = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>mixed-multi-module</artifactId>
        <version>1.0.0</version>
    </parent>
    <artifactId>{module}</artifactId>
</project>'''
        (module_dir / 'pom.xml').write_text(module_pom)

        # npm package.json
        package_content = json.dumps({
            "name": f"@example/{module}",
            "version": "1.0.0"
        }, indent=2)
        (module_dir / 'package.json').write_text(package_content)


def create_minimal_marshal_json(fixture_dir: Path) -> Path:
    """Create minimal marshal.json for detection tests."""
    config = {
        "skill_domains": {
            "system": {
                "defaults": ["plan-marshall:general-development-rules"],
                "optionals": []
            }
        },
        "module_config": {},
        "system": {"retention": {"logs_days": 1}},
        "plan": {"defaults": {}}
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))
    return marshal_path


def create_raw_project_data_multi_module_maven(fixture_dir: Path) -> Path:
    """Create raw-project-data.json for multi-module Maven project (Java only)."""
    raw_data = {
        "project": {"name": "multi-module-app"},
        "modules": [
            {"name": "core", "path": "core", "parent": None, "build_systems": ["maven"], "packaging": "jar"},
            {"name": "api", "path": "api", "parent": None, "build_systems": ["maven"], "packaging": "jar"},
            {"name": "web", "path": "web", "parent": None, "build_systems": ["maven"], "packaging": "jar"}
        ]
    }
    raw_path = fixture_dir / 'raw-project-data.json'
    raw_path.write_text(json.dumps(raw_data, indent=2))
    return raw_path


def create_raw_project_data_mixed(fixture_dir: Path) -> Path:
    """Create raw-project-data.json for mixed multi-module project.

    - core, api: Maven only (Java)
    - ui, e2e: Maven + npm (Java + JavaScript)
    """
    raw_data = {
        "project": {"name": "mixed-multi-module"},
        "modules": [
            {"name": "core", "path": "core", "parent": None, "build_systems": ["maven"], "packaging": "jar"},
            {"name": "api", "path": "api", "parent": None, "build_systems": ["maven"], "packaging": "jar"},
            {"name": "ui", "path": "ui", "parent": None, "build_systems": ["maven", "npm"], "packaging": "war"},
            {"name": "e2e", "path": "e2e", "parent": None, "build_systems": ["maven", "npm"], "packaging": "pom"}
        ]
    }
    raw_path = fixture_dir / 'raw-project-data.json'
    raw_path.write_text(json.dumps(raw_data, indent=2))
    return raw_path


# =============================================================================
# Build Systems Detection Tests
# =============================================================================

def test_detect_build_systems_maven_only():
    """Test detecting Maven as build system."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_maven_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'maven' in result.stdout.lower()
        assert 'npm' not in result.stdout.lower()


def test_detect_build_systems_npm_only():
    """Test detecting npm as build system."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_npm_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'npm' in result.stdout.lower()
        assert 'maven' not in result.stdout.lower()


def test_detect_build_systems_multi_module_maven_no_npm():
    """Test that multi-module Maven project with nested package.json does NOT detect npm at root."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_mixed_multi_module_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'build-systems', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        # Should detect maven (root pom.xml)
        assert 'maven' in result.stdout.lower()
        # Should NOT detect npm (no root package.json, only nested in modules)
        assert 'npm' not in result.stdout.lower(), \
            "Should not detect npm - package.json is nested in modules, not at root"


# =============================================================================
# Module Reading Tests (from raw-project-data.json)
# =============================================================================

def test_modules_list_from_raw_project_data():
    """Test modules list reads from raw-project-data.json."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_multi_module_maven(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'modules', 'list', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'core' in result.stdout
        assert 'api' in result.stdout
        assert 'web' in result.stdout


def test_modules_get_build_systems_maven_only():
    """Test that Java-only modules only have maven build system."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_mixed(ctx.fixture_dir)

        # Verify core module only has maven build system
        result = run_script(SCRIPT_PATH, 'modules', 'get-build-systems', '--module', 'core', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'maven' in result.stdout.lower()
        assert 'npm' not in result.stdout.lower(), \
            "Module without package.json should not have npm build system"


def test_modules_get_build_systems_hybrid():
    """Test that hybrid modules have both maven and npm build systems."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_mixed(ctx.fixture_dir)

        # Verify ui module has both build systems
        result = run_script(SCRIPT_PATH, 'modules', 'get-build-systems', '--module', 'ui', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'maven' in result.stdout.lower()
        assert 'npm' in result.stdout.lower(), \
            "Module with package.json should have npm build system"


# =============================================================================
# Domain Inference Tests (modules infer-domains)
# =============================================================================

def test_infer_domains_from_maven():
    """Test that Maven modules get java domain inferred."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_multi_module_maven(ctx.fixture_dir)

        # Infer domains from build_systems
        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'java' in result.stdout.lower()
        assert 'core' in result.stdout


def test_infer_domains_from_npm():
    """Test that npm modules get javascript domain inferred."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        # Create raw-project-data with npm-only module
        raw_data = {
            "project": {"name": "npm-project"},
            "modules": [
                {"name": "frontend", "path": "frontend", "parent": None, "build_systems": ["npm"], "packaging": None}
            ]
        }
        (ctx.fixture_dir / 'raw-project-data.json').write_text(json.dumps(raw_data, indent=2))

        # Infer domains
        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'javascript' in result.stdout.lower()


def test_infer_domains_hybrid_module():
    """Test that hybrid modules get both java and javascript domains."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_mixed(ctx.fixture_dir)

        # Infer domains
        result = run_script(SCRIPT_PATH, 'modules', 'infer-domains', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"
        # UI module should have both domains inferred
        assert 'ui' in result.stdout

        # Read marshal.json to verify domains were persisted
        marshal = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        ui_config = marshal.get('module_config', {}).get('ui', {})
        domains = ui_config.get('domains', [])

        assert 'java' in domains, "UI module should have java domain"
        assert 'javascript' in domains, "UI module should have javascript domain"


def test_infer_domains_java_only_module():
    """Test that Java-only modules don't have javascript domain."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)
        create_raw_project_data_mixed(ctx.fixture_dir)

        # Infer domains
        run_script(SCRIPT_PATH, 'modules', 'infer-domains', cwd=ctx.fixture_dir)

        # Read marshal.json to verify domains
        marshal = json.loads((ctx.fixture_dir / 'marshal.json').read_text())
        core_config = marshal.get('module_config', {}).get('core', {})
        domains = core_config.get('domains', [])

        assert 'java' in domains, "Core module should have java domain"
        assert 'javascript' not in domains, "Core module should not have javascript domain"


# =============================================================================
# Domain Detection Tests (skill-domains detect)
# =============================================================================

def test_detect_domains_maven_project():
    """Test detecting java domain from Maven project."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_maven_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify java domain was added
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java', cwd=ctx.fixture_dir)
        assert verify.success, "Java domain should exist"


def test_detect_domains_npm_project():
    """Test detecting javascript domain from npm project."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_npm_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify javascript domain was added
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'javascript', cwd=ctx.fixture_dir)
        assert verify.success, "JavaScript domain should exist"


def test_detect_domains_multi_module_maven_no_javascript():
    """Test that multi-module Maven with nested npm doesn't add javascript at root."""
    with PlanTestContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_mixed_multi_module_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify java domain exists
        verify_java = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java', cwd=ctx.fixture_dir)
        assert verify_java.success, "Java domain should exist"

        # Verify javascript domain does NOT exist at root level
        verify_js = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'javascript', cwd=ctx.fixture_dir)
        assert 'error' in verify_js.stdout.lower(), \
            "JavaScript should not be detected as root domain when only nested in modules"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Build systems detection
        test_detect_build_systems_maven_only,
        test_detect_build_systems_npm_only,
        test_detect_build_systems_multi_module_maven_no_npm,
        # Module reading (from raw-project-data.json)
        test_modules_list_from_raw_project_data,
        test_modules_get_build_systems_maven_only,
        test_modules_get_build_systems_hybrid,
        # Domain inference (modules infer-domains)
        test_infer_domains_from_maven,
        test_infer_domains_from_npm,
        test_infer_domains_hybrid_module,
        test_infer_domains_java_only_module,
        # Domain detection (skill-domains detect)
        test_detect_domains_maven_project,
        test_detect_domains_npm_project,
        test_detect_domains_multi_module_maven_no_javascript,
    ])
    sys.exit(runner.run())
