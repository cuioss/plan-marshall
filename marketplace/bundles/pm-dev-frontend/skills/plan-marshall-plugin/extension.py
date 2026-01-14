#!/usr/bin/env python3
"""Extension API for pm-dev-frontend bundle.

Provides build system detection, module discovery for npm/JavaScript projects.

Uses npm commands for discovery per extension-api specification:
- npm pkg get: metadata extraction
- npm ls: dependency extraction

Implementation logic resides in scripts/ directory.
"""

import json
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from extension_base import ExtensionBase, build_module_base, discover_descriptors  # type: ignore[import-not-found]
from npm import execute_direct  # type: ignore[import-not-found]

# Build file constant
PACKAGE_JSON = "package.json"


class Extension(ExtensionBase):
    """npm/JavaScript extension for pm-dev-frontend bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            "domain": {
                "key": "javascript",
                "name": "JavaScript Development",
                "description": "Modern JavaScript, ESLint, Jest testing, npm builds"
            },
            "profiles": {
                "core": {
                    "defaults": ["pm-dev-frontend:cui-javascript"],
                    "optionals": ["pm-dev-frontend:cui-jsdoc", "pm-dev-frontend:cui-javascript-project"]
                },
                "implementation": {
                    "defaults": [],
                    "optionals": ["pm-dev-frontend:cui-javascript-linting", "pm-dev-frontend:cui-javascript-maintenance"]
                },
                "module_testing": {
                    "defaults": ["pm-dev-frontend:cui-javascript-unit-testing"],
                    "optionals": ["pm-dev-frontend:cui-cypress"]
                },
                "quality": {
                    "defaults": [],
                    "optionals": []
                }
            }
        }

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return "pm-dev-frontend:ext-triage-js"

    # =========================================================================
    # discover_modules() Implementation
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all npm modules with complete metadata.

        Uses npm commands for discovery per extension-api specification:
        - npm pkg get: metadata extraction (name, version, description, type, scripts)
        - npm ls: dependency extraction

        Returns comprehensive module information including metadata, dependencies,
        and stats per build-project-structure.md specification.
        """
        # Use base library to find all package.json files recursively
        descriptors = discover_descriptors(project_root, PACKAGE_JSON)

        # Detect if root package.json exists (for routing decision: --workspace vs --prefix)
        root_package_json = Path(project_root) / PACKAGE_JSON
        has_root_package_json = root_package_json.exists()

        modules = []
        discovered_paths = set()

        for desc_path in descriptors:
            # Build base module info using base library
            base = build_module_base(project_root, str(desc_path))

            # Skip if already discovered (same module path)
            if base.paths.module in discovered_paths:
                continue
            discovered_paths.add(base.paths.module)

            # Get module directory for npm commands
            module_dir = Path(project_root) / base.paths.module if base.paths.module != "." else Path(project_root)

            # Check for workspaces to skip workspace roots
            workspaces = self._get_workspaces_from_npm(str(module_dir))
            if workspaces and base.paths.module == ".":
                # This is a workspace root - children will be discovered separately
                continue

            # Enrich with npm-specific data using npm commands
            module_data = self._enrich_npm_module(base, project_root, has_root_package_json)
            if module_data:
                modules.append(module_data)

        return modules

    def _get_workspaces_from_npm(self, module_dir: str) -> list:
        """Get workspaces from npm pkg get.

        Args:
            module_dir: Directory containing package.json

        Returns:
            List of workspace patterns or empty list
        """
        result = execute_direct(
            args="pkg get workspaces",
            command_key="npm:discover-workspaces",
            default_timeout=30,
            working_dir=module_dir
        )

        if result["status"] != "success":
            return []

        try:
            log_content = Path(result["log_file"]).read_text().strip()
            if not log_content or log_content == "undefined" or log_content == "{}":
                return []
            data = json.loads(log_content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("packages", [])
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def _enrich_npm_module(self, base, project_root: str, has_root_package_json: bool) -> dict | None:
        """Enrich base module with npm-specific data using npm commands.

        Uses npm pkg get and npm ls commands per extension-api specification:
        - npm pkg get name description type scripts: metadata extraction
        - npm ls --json --depth=0: dependency extraction

        Args:
            base: ModuleBase from build_module_base()
            project_root: Project root directory
            has_root_package_json: Whether project has root package.json (for routing detection)

        Returns structure per build-project-structure.md specification:
        - build_systems: ["npm"] (array)
        - paths: {module, descriptor, sources, tests, readme}
        - metadata: npm-specific fields (type, description)
        - packages: {} (object keyed by package name)
        - dependencies: ["name:scope", ...] (string format, e.g., "lit:compile")
        - stats: {source_files, test_files}
        - commands: {} (canonical command mappings)
        """
        root = Path(project_root)
        module_path = root / base.paths.module if base.paths.module != "." else root

        # Get metadata from npm pkg get
        pkg_metadata = self._get_npm_metadata(str(module_path))
        if pkg_metadata is None:
            return None

        # Use name from npm, fallback to base name
        name = pkg_metadata.get("name", base.name)

        # Discover source and test directories (module-relative)
        source_dirs_local = self._discover_source_dirs(module_path, pkg_metadata)
        test_dirs_local = self._discover_test_dirs(module_path, pkg_metadata)

        # Convert to repo-root relative paths
        module_prefix = base.paths.module
        if module_prefix == ".":
            source_dirs = source_dirs_local
            test_dirs = test_dirs_local
        else:
            source_dirs = [f"{module_prefix}/{d}" for d in source_dirs_local]
            test_dirs = [f"{module_prefix}/{d}" for d in test_dirs_local]

        # Build paths object (extending base), filtering out None values
        paths = {
            k: v for k, v in {
                "module": base.paths.module,
                "descriptor": base.paths.descriptor,
                "sources": source_dirs,
                "tests": test_dirs,
                "readme": base.paths.readme
            }.items() if v is not None
        }

        # Build npm-specific metadata for planning context, filtering out None values
        metadata = {
            k: v for k, v in {
                "type": pkg_metadata.get("type"),  # "module" (ESM) or "commonjs" - affects imports
                "description": pkg_metadata.get("description")
            }.items() if v is not None
        }

        # Discover packages (from exports or directories)
        packages = self._discover_npm_packages(module_path, pkg_metadata, base.paths.module)

        # Get dependencies from npm ls
        dependencies = self._get_npm_dependencies(str(module_path))

        # Calculate stats (use module-relative dirs since module_path is the base)
        source_files = self._count_js_files(module_path, source_dirs_local)
        test_files = self._count_js_files(module_path, test_dirs_local)

        # Build commands based on available scripts
        scripts = pkg_metadata.get("scripts", {})
        commands = self._build_npm_commands(base.paths.module, scripts, has_root_package_json)

        return {
            "name": name,
            "build_systems": ["npm"],
            "paths": paths,
            "metadata": metadata,
            "packages": packages,
            "dependencies": dependencies,
            "stats": {
                "source_files": source_files,
                "test_files": test_files
            },
            "commands": commands
        }

    def _get_npm_metadata(self, module_dir: str) -> dict | None:
        """Get module metadata from npm pkg get.

        Runs: npm pkg get name description type scripts exports

        Args:
            module_dir: Directory containing package.json

        Returns:
            Dict with metadata fields or None on failure
        """
        result = execute_direct(
            args="pkg get name description type scripts exports",
            command_key="npm:discover-metadata",
            default_timeout=30,
            working_dir=module_dir
        )

        if result["status"] != "success":
            return None

        try:
            log_content = Path(result["log_file"]).read_text().strip()
            if not log_content or log_content == "{}":
                return {}
            return json.loads(log_content)
        except (json.JSONDecodeError, OSError):
            return None

    def _get_npm_dependencies(self, module_dir: str) -> list:
        """Get dependencies from npm ls.

        Runs: npm ls --json --depth=0

        Args:
            module_dir: Directory containing package.json

        Returns:
            List of "{name}:{scope}" strings (e.g., "lit:compile", "@testing-library/dom:test")
        """
        result = execute_direct(
            args="ls --json --depth=0",
            command_key="npm:discover-dependencies",
            default_timeout=60,
            working_dir=module_dir
        )

        dependencies = []

        if result["status"] != "success":
            # npm ls returns non-zero for missing deps, try to parse anyway
            pass

        try:
            log_content = Path(result["log_file"]).read_text().strip()
            if not log_content or log_content == "{}":
                return []

            data = json.loads(log_content)
            deps = data.get("dependencies", {})

            for name, info in deps.items():
                # Determine scope based on dev flag
                if isinstance(info, dict) and info.get("dev", False):
                    scope = "test"
                elif isinstance(info, dict) and info.get("peer", False):
                    scope = "provided"
                else:
                    scope = "compile"
                dependencies.append(f"{name}:{scope}")

        except (json.JSONDecodeError, OSError):
            pass

        return dependencies

    def _discover_source_dirs(self, module_path: Path, pkg: dict) -> list:
        """Discover source directories for an npm module.

        Returns list of source directory paths relative to module.
        """
        source_dirs = []
        common_src_dirs = ["src", "lib", "source"]
        for src_dir in common_src_dirs:
            if (module_path / src_dir).exists():
                source_dirs.append(src_dir)
                break
        return source_dirs

    def _discover_test_dirs(self, module_path: Path, pkg: dict) -> list:
        """Discover test directories for an npm module.

        Returns list of test directory paths relative to module.
        """
        test_dirs = []
        common_test_dirs = ["test", "tests", "__tests__", "spec"]
        for test_dir in common_test_dirs:
            if (module_path / test_dir).exists():
                test_dirs.append(test_dir)

        # Check Jest configuration for custom test locations
        jest_config = pkg.get("jest", {})
        if isinstance(jest_config, dict) and not test_dirs:
            test_match = jest_config.get("testMatch", [])
            for pattern in test_match:
                if "__tests__" in pattern:
                    test_dirs.append("__tests__")
                    break

        return test_dirs

    def _find_readme(self, module_path: Path, relative_path: str) -> str | None:
        """Find README file and return its path.

        Returns path relative to project root, or None if not found.
        """
        readme_names = ["README.md", "README", "readme.md", "Readme.md", "README.adoc"]
        for name in readme_names:
            if (module_path / name).exists():
                if relative_path:
                    return f"{relative_path}/{name}"
                return name
        return None

    def _discover_npm_packages(self, module_path: Path, pkg: dict, relative_path: str) -> dict:
        """Discover npm packages from exports or directories.

        Per build-project-structure.md:
        - Discover from package.json exports field (subpath exports)
        - Fall back to top-level directories under src/ or lib/
        - Returns object keyed by package name with {path, exports?}
        """
        packages = {}
        module_rel = relative_path if relative_path else "."

        # Check for subpath exports in package.json
        exports = pkg.get("exports", {})
        if isinstance(exports, dict):
            for export_key, export_value in exports.items():
                # Skip main export "." and conditional exports
                if export_key == "." or not export_key.startswith("./"):
                    continue
                # Extract package name from export key (e.g., "./utils" -> "utils")
                pkg_name = export_key[2:]  # Remove "./"
                if pkg_name:
                    # Resolve export path
                    export_path = export_value if isinstance(export_value, str) else None
                    pkg_entry = {
                        "path": f"{module_rel}/src/{pkg_name}" if module_rel != "." else f"src/{pkg_name}"
                    }
                    if export_path:
                        pkg_entry["exports"] = export_key
                    packages[pkg_name] = pkg_entry

        # Fall back to top-level directories under src/ or lib/
        if not packages:
            for src_dir_name in ["src", "lib"]:
                src_dir = module_path / src_dir_name
                if src_dir.exists() and src_dir.is_dir():
                    for subdir in src_dir.iterdir():
                        if subdir.is_dir() and not subdir.name.startswith('.'):
                            pkg_name = subdir.name
                            if module_rel != ".":
                                pkg_path = f"{module_rel}/{src_dir_name}/{pkg_name}"
                            else:
                                pkg_path = f"{src_dir_name}/{pkg_name}"
                            packages[pkg_name] = {"path": pkg_path}
                    break  # Only check first existing src directory

        return packages

    def _build_npm_commands(self, module_path: str, scripts: dict, has_root_package_json: bool = True) -> dict:
        """Build canonical command mappings based on available scripts.

        Per canonical-commands.md for npm:
        - clean: npm run clean (if "clean" script exists)
        - compile: npm run build (if "build" script exists)
        - module-tests: npm test (if "test" script exists)
        - quality-gate: npm run lint (if "lint" script exists)
        - verify: npm run build && npm test (if both scripts exist)

        Routing is embedded in --commandArgs:
        - Root modules: no routing needed
        - Submodules with root package.json: use --workspace=path (recommended)
        - Submodules without root package.json: use --prefix path (fallback)

        Args:
            module_path: Module path relative to project root ("." for root)
            scripts: Dict of npm scripts from package.json
            has_root_package_json: Whether project has root package.json (enables workspace routing)
        """
        commands = {}
        base = "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run"

        # Determine routing mechanism embedded in commandArgs
        if module_path == ".":
            routing = ""
        elif has_root_package_json:
            # Workspace routing (recommended) - appended to npm command
            routing = f" --workspace={module_path}"
        else:
            # Prefix routing (fallback for non-workspace projects) - prepended to npm command
            routing = f"--prefix {module_path} "

        def _cmd(npm_cmd: str) -> str:
            """Build full commandArgs with routing embedded."""
            if routing.startswith("--prefix"):
                # Prefix goes before npm command
                return f'{routing}{npm_cmd}'
            else:
                # Workspace goes after npm command
                return f'{npm_cmd}{routing}'

        if "clean" in scripts:
            commands["clean"] = f'{base} --commandArgs "{_cmd("run clean")}"'

        if "build" in scripts:
            commands["compile"] = f'{base} --commandArgs "{_cmd("run build")}"'

        if "test" in scripts:
            commands["module-tests"] = f'{base} --commandArgs "{_cmd("test")}"'

        if "lint" in scripts:
            commands["quality-gate"] = f'{base} --commandArgs "{_cmd("run lint")}"'

        # verify: build + test combined
        if "build" in scripts and "test" in scripts:
            commands["verify"] = f'{base} --commandArgs "{_cmd("run build && npm test")}"'
        elif "test" in scripts:
            # If no build script, verify is just test
            commands["verify"] = f'{base} --commandArgs "{_cmd("test")}"'

        return commands

    def _count_js_files(self, module_path: Path, directories: list) -> int:
        """Count JavaScript/TypeScript files in directories."""
        count = 0
        js_extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

        for dir_name in directories:
            dir_path = module_path / dir_name
            if dir_path.exists():
                for file in dir_path.rglob("*"):
                    if file.is_file() and file.suffix in js_extensions:
                        count += 1

        return count
