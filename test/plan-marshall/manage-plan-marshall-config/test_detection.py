#!/usr/bin/env python3
"""Tests for project detection in plan-marshall-config.

Tests auto-detection of build systems and domains from project files.
Domain detection uses skill-domains detect to find build files at project root.
"""

import json
import shutil
from pathlib import Path

from test_helpers import SCRIPT_PATH

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script

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


# =============================================================================
# Test Fixtures - Project Structure Creators
# =============================================================================


def create_simple_maven_project(fixture_dir: Path) -> None:
    """Create a simple single-module Maven project."""
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>simple-app</artifactId>
    <version>1.0.0</version>
</project>"""
    (fixture_dir / 'pom.xml').write_text(pom_content)


def create_simple_npm_project(fixture_dir: Path) -> None:
    """Create a simple npm project."""
    package_content = json.dumps({'name': 'simple-app', 'version': '1.0.0'}, indent=2)
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
    root_pom = """<?xml version="1.0" encoding="UTF-8"?>
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
</project>"""
    (fixture_dir / 'pom.xml').write_text(root_pom)

    # Java-only modules
    for module in ['core', 'api']:
        module_dir = fixture_dir / module
        module_dir.mkdir(parents=True, exist_ok=True)
        module_pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>mixed-multi-module</artifactId>
        <version>1.0.0</version>
    </parent>
    <artifactId>{module}</artifactId>
</project>"""
        (module_dir / 'pom.xml').write_text(module_pom)

    # Java + JavaScript modules (have both pom.xml and package.json)
    for module in ['ui', 'e2e']:
        module_dir = fixture_dir / module
        module_dir.mkdir(parents=True, exist_ok=True)

        # Maven pom.xml
        module_pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>mixed-multi-module</artifactId>
        <version>1.0.0</version>
    </parent>
    <artifactId>{module}</artifactId>
</project>"""
        (module_dir / 'pom.xml').write_text(module_pom)

        # npm package.json
        package_content = json.dumps({'name': f'@example/{module}', 'version': '1.0.0'}, indent=2)
        (module_dir / 'package.json').write_text(package_content)


def create_minimal_marshal_json(fixture_dir: Path) -> Path:
    """Create minimal marshal.json for detection tests."""
    config = {
        'skill_domains': {'system': {'defaults': ['plan-marshall:general-development-rules'], 'optionals': []}},
        'system': {'retention': {'logs_days': 1}},
        'plan': {'defaults': {}},
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))
    return marshal_path


# =============================================================================
# Domain Detection Tests (skill-domains detect)
# =============================================================================


def test_detect_domains_maven_project():
    """Test detecting java domain from Maven project."""
    with PlanContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_maven_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify java domain was added
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java', cwd=ctx.fixture_dir)
        assert verify.success, 'Java domain should exist'


def test_detect_domains_npm_project():
    """Test detecting javascript domain from npm project."""
    with PlanContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_simple_npm_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify javascript domain was added
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'javascript', cwd=ctx.fixture_dir)
        assert verify.success, 'JavaScript domain should exist'


def test_detect_domains_multi_module_maven_no_javascript():
    """Test that multi-module Maven with nested npm doesn't add javascript at root."""
    with PlanContext() as ctx:
        cleanup_project_files(ctx.fixture_dir)
        create_mixed_multi_module_project(ctx.fixture_dir)
        create_minimal_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'

        # Verify java domain exists
        verify_java = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java', cwd=ctx.fixture_dir)
        assert verify_java.success, 'Java domain should exist'

        # Verify javascript domain does NOT exist at root level
        verify_js = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'javascript', cwd=ctx.fixture_dir)
        assert 'error' in verify_js.stdout.lower(), (
            'JavaScript should not be detected as root domain when only nested in modules'
        )


# =============================================================================
# Main
# =============================================================================
