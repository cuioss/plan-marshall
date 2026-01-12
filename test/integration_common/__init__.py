#!/usr/bin/env python3
"""Shared infrastructure for integration tests.

Integration tests validate discovery and build operations against real
projects in the local git directory.
"""

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


# Project root (plan-marshall)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default git directory (parent of plan-marshall)
DEFAULT_GIT_DIR = PROJECT_ROOT.parent

# Base directory for integration test output
INTEGRATION_TEST_OUTPUT_DIR = PROJECT_ROOT / ".plan" / "temp" / "integration-tests"


@dataclass
class TestProject:
    """A test project configuration."""
    name: str
    relative_path: str  # Relative to git directory
    description: str

    def absolute_path(self, git_dir: Path = DEFAULT_GIT_DIR) -> Path:
        """Get absolute path to the project."""
        return git_dir / self.relative_path

    def exists(self, git_dir: Path = DEFAULT_GIT_DIR) -> bool:
        """Check if the project exists."""
        return self.absolute_path(git_dir).exists()


class IntegrationTestContext:
    """Context manager for integration tests.

    Manages:
    - Output directory creation and cleanup
    - Project existence validation
    - Result persistence
    """

    def __init__(self, output_dir: Path, clean_before: bool = True):
        """Initialize the context.

        Args:
            output_dir: Directory for test output (e.g., .plan/temp/test-results-npm)
            clean_before: Whether to clean the output directory before tests
        """
        self.output_dir = output_dir
        self.clean_before = clean_before
        self.git_dir = DEFAULT_GIT_DIR
        self.results: dict[str, dict] = {}
        self.skipped: list[str] = []
        self.errors: list[str] = []

    def __enter__(self):
        if self.clean_before and self.output_dir.exists():
            for f in self.output_dir.glob("*.json"):
                f.unlink()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def validate_project(self, project: TestProject) -> bool:
        """Check if a project exists, log if missing."""
        if not project.exists(self.git_dir):
            self.skipped.append(
                f"{project.name}: Not found at {project.absolute_path(self.git_dir)}"
            )
            return False
        return True

    def save_result(self, project: TestProject, data: list | dict) -> Path:
        """Save discovery result to JSON file."""
        filename = project.name.lower().replace(" ", "-").replace("/", "-")
        output_path = self.output_dir / f"{filename}.json"
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        self.results[project.name] = {"path": output_path, "data": data}
        return output_path

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'=' * 60}")
        print("Integration Test Summary")
        print(f"{'=' * 60}")
        print(f"Tested: {len(self.results)}")
        print(f"Skipped: {len(self.skipped)}")
        print(f"Errors: {len(self.errors)}")

        if self.skipped:
            print("\nSkipped projects (not found):")
            for msg in self.skipped:
                print(f"  - {msg}")

        if self.errors:
            print("\nErrors:")
            for msg in self.errors:
                print(f"  - {msg}")


def assert_no_null_values(
    data: dict | list,
    path: str = "",
    allowed_null_suffixes: list[str] | None = None
) -> list[str]:
    """Recursively check for null values in data structure.

    Args:
        data: The data structure to check
        path: Current path (used for recursion)
        allowed_null_suffixes: List of path suffixes where null is acceptable
                               (e.g., [".readme", ".description"])

    Returns list of paths where null values were found.
    """
    allowed = allowed_null_suffixes or []
    nulls = []

    def is_allowed(p: str) -> bool:
        return any(p.endswith(suffix) for suffix in allowed)

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if value is None:
                if not is_allowed(current_path):
                    nulls.append(current_path)
            else:
                nulls.extend(assert_no_null_values(value, current_path, allowed))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            if item is None:
                if not is_allowed(current_path):
                    nulls.append(current_path)
            else:
                nulls.extend(assert_no_null_values(item, current_path, allowed))
    return nulls


def assert_paths_exist(modules: list[dict], project_root: Path) -> list[str]:
    """Verify all paths in modules exist relative to project root.

    Checks:
    - paths.descriptor
    - paths.sources (each directory)
    - paths.tests (each directory)
    - paths.readme (if present)

    Returns list of missing paths.
    """
    missing = []
    for module in modules:
        name = module.get("name", "unknown")
        paths = module.get("paths", {})

        # Check descriptor
        descriptor = paths.get("descriptor")
        if descriptor:
            full_path = project_root / descriptor
            if not full_path.exists():
                missing.append(f"{name}: descriptor '{descriptor}' not found")

        # Check sources
        for src in paths.get("sources", []):
            full_path = project_root / src
            if not full_path.exists():
                missing.append(f"{name}: source '{src}' not found")

        # Check tests
        for test in paths.get("tests", []):
            full_path = project_root / test
            if not full_path.exists():
                missing.append(f"{name}: test '{test}' not found")

        # Check readme (optional)
        readme = paths.get("readme")
        if readme:
            full_path = project_root / readme
            if not full_path.exists():
                missing.append(f"{name}: readme '{readme}' not found")

    return missing


# =============================================================================
# Technology-Specific Assertions
# =============================================================================

def assert_npm_module_structure(modules: list[dict]) -> list[str]:
    """Validate npm-specific module structure.

    Checks:
    - build_systems contains "npm"
    - paths.descriptor ends with "package.json"
    - dependencies follow format "npm:{name}:{scope}"
    - metadata.type is "module" or "commonjs" (if present)
    - commands contain npm execute-script pattern

    Returns list of validation errors.
    """
    errors = []
    valid_dep_scopes = {"compile", "test", "provided", "runtime"}
    valid_module_types = {"module", "commonjs"}

    for module in modules:
        name = module.get("name", "unknown")

        # Check build_systems contains npm
        build_systems = module.get("build_systems", [])
        if "npm" not in build_systems:
            errors.append(f"{name}: build_systems should contain 'npm', got {build_systems}")

        # Check descriptor path
        paths = module.get("paths", {})
        descriptor = paths.get("descriptor", "")
        if not descriptor.endswith("package.json"):
            errors.append(f"{name}: descriptor should end with 'package.json', got '{descriptor}'")

        # Check dependencies format
        for dep in module.get("dependencies", []):
            if not isinstance(dep, str):
                errors.append(f"{name}: dependency should be string, got {type(dep).__name__}")
                continue
            parts = dep.split(":")
            if len(parts) != 3:
                errors.append(f"{name}: dependency '{dep}' should have format 'npm:name:scope'")
            elif parts[0] != "npm":
                errors.append(f"{name}: dependency '{dep}' should start with 'npm:'")
            elif parts[2] not in valid_dep_scopes:
                errors.append(f"{name}: dependency '{dep}' has invalid scope '{parts[2]}'")

        # Check metadata.type if present
        metadata = module.get("metadata", {})
        module_type = metadata.get("type")
        if module_type is not None and module_type not in valid_module_types:
            errors.append(f"{name}: metadata.type should be 'module' or 'commonjs', got '{module_type}'")

        # Check commands contain npm pattern
        commands = module.get("commands", {})
        for cmd_name, cmd_value in commands.items():
            if not isinstance(cmd_value, str):
                errors.append(f"{name}: command '{cmd_name}' should be string")
            elif "pm-dev-frontend:plan-marshall-plugin:npm" not in cmd_value:
                errors.append(f"{name}: command '{cmd_name}' missing npm execute-script pattern")

    return errors


def assert_maven_module_structure(modules: list[dict]) -> list[str]:
    """Validate Maven-specific module structure.

    Checks:
    - build_systems contains "maven"
    - paths.descriptor ends with "pom.xml"
    - dependencies follow format "{group}:{artifact}:{scope}"
    - metadata has artifact_id and group_id (required)
    - commands contain maven execute-script pattern

    Returns list of validation errors.
    """
    errors = []
    valid_dep_scopes = {"compile", "test", "provided", "runtime", "system", "import"}

    for module in modules:
        name = module.get("name", "unknown")

        # Check build_systems contains maven
        build_systems = module.get("build_systems", [])
        if "maven" not in build_systems:
            errors.append(f"{name}: build_systems should contain 'maven', got {build_systems}")

        # Check descriptor path
        paths = module.get("paths", {})
        descriptor = paths.get("descriptor", "")
        if not descriptor.endswith("pom.xml"):
            errors.append(f"{name}: descriptor should end with 'pom.xml', got '{descriptor}'")

        # Check dependencies format: {group}:{artifact}:{scope} or {group}:{artifact}:{version}:{scope}
        for dep in module.get("dependencies", []):
            if not isinstance(dep, str):
                errors.append(f"{name}: dependency should be string, got {type(dep).__name__}")
                continue
            parts = dep.split(":")
            if len(parts) == 3:
                scope = parts[2]
            elif len(parts) == 4:
                # Format: group:artifact:version:scope
                scope = parts[3]
            else:
                errors.append(f"{name}: dependency '{dep}' should have format 'group:artifact:scope' or 'group:artifact:version:scope'")
                continue
            if scope not in valid_dep_scopes:
                errors.append(f"{name}: dependency '{dep}' has invalid scope '{scope}'")

        # Check metadata has required fields
        metadata = module.get("metadata", {})
        if "artifact_id" not in metadata:
            errors.append(f"{name}: metadata missing required 'artifact_id'")
        if "group_id" not in metadata:
            errors.append(f"{name}: metadata missing required 'group_id'")

        # Check commands contain maven pattern
        commands = module.get("commands", {})
        for cmd_name, cmd_value in commands.items():
            if not isinstance(cmd_value, str):
                errors.append(f"{name}: command '{cmd_name}' should be string")
            elif "pm-dev-java:plan-marshall-plugin:maven" not in cmd_value:
                errors.append(f"{name}: command '{cmd_name}' missing maven execute-script pattern")

    return errors


def assert_gradle_module_structure(modules: list[dict]) -> list[str]:
    """Validate Gradle-specific module structure.

    Checks:
    - build_systems contains "gradle"
    - paths.descriptor ends with "build.gradle" or "build.gradle.kts"
    - dependencies follow format "{group}:{artifact}:{scope}" or "project:{name}:{scope}"
    - commands contain gradle execute-script pattern
    - handles modules with errors gracefully

    Returns list of validation errors.
    """
    errors = []
    valid_dep_scopes = {"compile", "test", "provided", "runtime", "implementation", "api", "testImplementation"}

    for module in modules:
        name = module.get("name", "unknown")

        # Check build_systems contains gradle
        build_systems = module.get("build_systems", [])
        if "gradle" not in build_systems:
            errors.append(f"{name}: build_systems should contain 'gradle', got {build_systems}")

        # Skip further validation if module has error (e.g., version incompatibility)
        if "error" in module:
            continue

        # Check descriptor path
        paths = module.get("paths", {})
        descriptor = paths.get("descriptor", "")
        if not (descriptor.endswith("build.gradle") or descriptor.endswith("build.gradle.kts")):
            errors.append(f"{name}: descriptor should end with 'build.gradle' or 'build.gradle.kts', got '{descriptor}'")

        # Check dependencies format
        for dep in module.get("dependencies", []):
            if not isinstance(dep, str):
                errors.append(f"{name}: dependency should be string, got {type(dep).__name__}")
                continue
            parts = dep.split(":")
            if len(parts) != 3:
                errors.append(f"{name}: dependency '{dep}' should have format 'group:artifact:scope'")
            elif parts[2] not in valid_dep_scopes:
                errors.append(f"{name}: dependency '{dep}' has invalid scope '{parts[2]}'")

        # Check commands contain gradle pattern
        commands = module.get("commands", {})
        for cmd_name, cmd_value in commands.items():
            if not isinstance(cmd_value, str):
                errors.append(f"{name}: command '{cmd_name}' should be string")
            elif "pm-dev-java:plan-marshall-plugin:gradle" not in cmd_value:
                errors.append(f"{name}: command '{cmd_name}' missing gradle execute-script pattern")

    return errors


def assert_has_root_aggregator(
    modules: list[dict],
    project_root: Path | None = None,
    root_descriptors: list[str] | None = None
) -> list[str]:
    """Verify multi-module projects include a root aggregator module.

    For projects with multiple modules, there should be a root module at path "."
    that coordinates the build (pom aggregator for Maven, root package.json for npm).

    Args:
        modules: List of discovered modules
        project_root: Path to project root (for checking if root descriptor exists)
        root_descriptors: List of possible root descriptor filenames (e.g., ["pom.xml", "package.json"])
                         If provided with project_root, only check for aggregator if descriptor exists

    Checks:
    - If len(modules) > 1, one module should have paths.module = "."
    - Root module should have "clean" command
    - Root module should have "quality-gate" command (for aggregate analysis)

    Returns list of validation errors.
    """
    errors = []

    if len(modules) <= 1:
        return errors  # Single module projects don't need aggregator

    # Skip if all modules have errors (can't determine proper structure)
    valid_modules = [m for m in modules if "error" not in m]
    if not valid_modules:
        return errors  # All modules have errors, skip assertion

    # If project_root and root_descriptors provided, check if root descriptor exists
    if project_root and root_descriptors:
        has_root_descriptor = any(
            (project_root / desc).exists() for desc in root_descriptors
        )
        if not has_root_descriptor:
            return errors  # No root descriptor, so no aggregator expected

    # Find root module
    root_modules = [m for m in modules if m.get("paths", {}).get("module") == "."]

    if not root_modules:
        errors.append("Multi-module project missing root aggregator (paths.module='.')")
        return errors

    root = root_modules[0]
    root_name = root.get("name", "unknown")
    commands = root.get("commands", {})

    if "clean" not in commands:
        errors.append(f"Root aggregator '{root_name}' missing 'clean' command")

    if "quality-gate" not in commands:
        errors.append(f"Root aggregator '{root_name}' missing 'quality-gate' command")

    return errors
