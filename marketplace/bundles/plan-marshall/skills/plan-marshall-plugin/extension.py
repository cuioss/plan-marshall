#!/usr/bin/env python3
"""Extension API for plan-marshall bundle - build system discovery.

Consolidates module discovery for Maven, Gradle, npm, and Python build systems.
Build execution scripts live in sibling skill directories (build-maven, build-gradle,
build-npm, build-python).
"""

import json
import sys
import tomllib
from pathlib import Path

from extension_base import ExtensionBase, build_module_base, discover_descriptors  # type: ignore[import-not-found]

# Add sibling skill script directories to path
SKILLS_DIR = Path(__file__).parent.parent  # plan-marshall/skills/
for skill_name in ['build-maven', 'build-gradle', 'build-npm', 'build-python']:
    scripts_dir = SKILLS_DIR / skill_name / 'scripts'
    if scripts_dir.exists() and str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

from _build_wrapper import has_wrapper  # type: ignore[import-not-found]  # noqa: E402
from npm import execute_direct  # type: ignore[import-not-found]  # noqa: E402

# Build file constants
POM_XML = 'pom.xml'
BUILD_GRADLE = 'build.gradle'
BUILD_GRADLE_KTS = 'build.gradle.kts'
SETTINGS_GRADLE = 'settings.gradle'
SETTINGS_GRADLE_KTS = 'settings.gradle.kts'
PACKAGE_JSON = 'package.json'
PYPROJECT_TOML = 'pyproject.toml'

# Marketplace identification (Python discovery skips plan-marshall itself)
MARKETPLACE_JSON = 'marketplace/.claude-plugin/marketplace.json'
PLAN_MARSHALL_NAME = 'plan-marshall'


def _is_plan_marshall_marketplace(project_root: str) -> bool:
    """Check if this is the plan-marshall marketplace by name.

    The plan-marshall marketplace is handled by pm-plugin-development,
    so Python discovery should skip module discovery for it.
    """
    marketplace_json = Path(project_root) / MARKETPLACE_JSON
    if not marketplace_json.exists():
        return False
    try:
        data = json.loads(marketplace_json.read_text(encoding='utf-8'))
        name = data.get('name')
        return isinstance(name, str) and name == PLAN_MARSHALL_NAME
    except (OSError, json.JSONDecodeError):
        return False


class Extension(ExtensionBase):
    """Build system discovery extension for plan-marshall bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata - build domain with no profiles."""
        return {
            'domain': {
                'key': 'build',
                'name': 'Build Systems',
                'description': 'Maven, Gradle, npm, and Python build detection and execution',
            },
            'profiles': {},
        }

    # =========================================================================
    # discover_modules() - Consolidated build system discovery
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules across Maven, Gradle, npm, and Python.

        Delegates to build-system-specific discovery logic:
        - Maven: _maven_cmd_discover.discover_maven_modules()
        - Gradle: _gradle_cmd_discover.discover_gradle_modules()
        - npm: package.json scanning with npm commands
        - Python: pyproject.toml parsing for pyprojectx aliases
        """
        modules = []

        # Maven modules
        modules.extend(self._discover_maven(project_root))

        # Gradle modules (avoid duplicates with Maven)
        modules.extend(self._discover_gradle(project_root, modules))

        # npm modules
        modules.extend(self._discover_npm(project_root))

        # Python modules
        modules.extend(self._discover_python(project_root))

        return modules

    # =========================================================================
    # Maven Discovery
    # =========================================================================

    def _discover_maven(self, project_root: str) -> list:
        """Discover Maven modules via pom.xml analysis."""
        root = Path(project_root)
        if not (root / POM_XML).exists():
            return []

        from _maven_cmd_discover import discover_maven_modules

        return discover_maven_modules(project_root)

    # =========================================================================
    # Gradle Discovery
    # =========================================================================

    def _discover_gradle(self, project_root: str, existing_modules: list) -> list:
        """Discover Gradle modules, excluding those already found by Maven."""
        root = Path(project_root)
        gradle_files = [BUILD_GRADLE_KTS, BUILD_GRADLE, SETTINGS_GRADLE_KTS, SETTINGS_GRADLE]
        has_gradle = any((root / bf).exists() for bf in gradle_files)
        if not has_gradle:
            return []

        from _gradle_cmd_discover import discover_gradle_modules

        maven_paths = {m['paths']['module'] for m in existing_modules if 'paths' in m}
        gradle_modules = discover_gradle_modules(project_root)

        result = []
        for gm in gradle_modules:
            # Error-only modules (no paths) are always included
            if 'error' in gm or gm['paths']['module'] not in maven_paths:
                result.append(gm)
        return result

    # =========================================================================
    # npm Discovery (from pm-dev-frontend)
    # =========================================================================

    def _discover_npm(self, project_root: str) -> list:
        """Discover npm modules with complete metadata."""
        descriptors = discover_descriptors(project_root, PACKAGE_JSON)
        if not descriptors:
            return []

        root_package_json = Path(project_root) / PACKAGE_JSON
        has_root_package_json = root_package_json.exists()

        modules = []
        discovered_paths: set[str] = set()

        for desc_path in descriptors:
            base = build_module_base(project_root, str(desc_path))

            if base.paths.module in discovered_paths:
                continue
            discovered_paths.add(base.paths.module)

            module_dir = Path(project_root) / base.paths.module if base.paths.module != '.' else Path(project_root)

            workspaces = self._get_workspaces_from_npm(str(module_dir))
            if workspaces and base.paths.module == '.':
                continue

            module_data = self._enrich_npm_module(base, project_root, has_root_package_json)
            if module_data:
                modules.append(module_data)

        return modules

    def _get_workspaces_from_npm(self, module_dir: str) -> list:
        """Get workspaces from npm pkg get."""
        result = execute_direct(
            args='pkg get workspaces', command_key='npm:discover-workspaces', default_timeout=30, working_dir=module_dir
        )

        if result['status'] != 'success':
            return []

        try:
            log_content = Path(result['log_file']).read_text().strip()
            if not log_content or log_content == 'undefined' or log_content == '{}':
                return []
            data = json.loads(log_content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('packages', [])
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def _enrich_npm_module(self, base, project_root: str, has_root_package_json: bool) -> dict | None:
        """Enrich base module with npm-specific data using npm commands."""
        root = Path(project_root)
        module_path = root / base.paths.module if base.paths.module != '.' else root

        pkg_metadata = self._get_npm_metadata(str(module_path))
        if pkg_metadata is None:
            return None

        name = pkg_metadata.get('name', base.name)

        source_dirs_local = self._discover_npm_source_dirs(module_path, pkg_metadata)
        test_dirs_local = self._discover_npm_test_dirs(module_path, pkg_metadata)

        module_prefix = base.paths.module
        if module_prefix == '.':
            source_dirs = source_dirs_local
            test_dirs = test_dirs_local
        else:
            source_dirs = [f'{module_prefix}/{d}' for d in source_dirs_local]
            test_dirs = [f'{module_prefix}/{d}' for d in test_dirs_local]

        paths = {
            k: v
            for k, v in {
                'module': base.paths.module,
                'descriptor': base.paths.descriptor,
                'sources': source_dirs,
                'tests': test_dirs,
                'readme': base.paths.readme,
            }.items()
            if v is not None
        }

        metadata = {
            k: v
            for k, v in {
                'type': pkg_metadata.get('type'),
                'description': pkg_metadata.get('description'),
            }.items()
            if v is not None
        }

        packages = self._discover_npm_packages(module_path, pkg_metadata, base.paths.module)
        dependencies = self._get_npm_dependencies(str(module_path))

        source_files = self._count_js_files(module_path, source_dirs_local)
        test_files = self._count_js_files(module_path, test_dirs_local)

        scripts = pkg_metadata.get('scripts', {})
        commands = self._build_npm_commands(base.paths.module, scripts, has_root_package_json)

        return {
            'name': name,
            'build_systems': ['npm'],
            'paths': paths,
            'metadata': metadata,
            'packages': packages,
            'dependencies': dependencies,
            'stats': {'source_files': source_files, 'test_files': test_files},
            'commands': commands,
        }

    def _get_npm_metadata(self, module_dir: str) -> dict | None:
        """Get module metadata from npm pkg get."""
        result = execute_direct(
            args='pkg get name description type scripts exports',
            command_key='npm:discover-metadata',
            default_timeout=30,
            working_dir=module_dir,
        )

        if result['status'] != 'success':
            return None

        try:
            log_content = Path(result['log_file']).read_text().strip()
            if not log_content or log_content == '{}':
                return {}
            return json.loads(log_content)
        except (json.JSONDecodeError, OSError):
            return None

    def _get_npm_dependencies(self, module_dir: str) -> list:
        """Get dependencies from npm ls."""
        result = execute_direct(
            args='ls --json --depth=0',
            command_key='npm:discover-dependencies',
            default_timeout=60,
            working_dir=module_dir,
        )

        dependencies = []

        if result['status'] != 'success':
            pass

        try:
            log_content = Path(result['log_file']).read_text().strip()
            if not log_content or log_content == '{}':
                return []

            data = json.loads(log_content)
            deps = data.get('dependencies', {})

            for name, info in deps.items():
                if isinstance(info, dict) and info.get('dev', False):
                    scope = 'test'
                elif isinstance(info, dict) and info.get('peer', False):
                    scope = 'provided'
                else:
                    scope = 'compile'
                dependencies.append(f'{name}:{scope}')

        except (json.JSONDecodeError, OSError):
            pass

        return dependencies

    def _discover_npm_source_dirs(self, module_path: Path, pkg: dict) -> list:
        """Discover source directories for an npm module."""
        source_dirs = []
        for src_dir in ['src', 'lib', 'source']:
            if (module_path / src_dir).exists():
                source_dirs.append(src_dir)
                break
        return source_dirs

    def _discover_npm_test_dirs(self, module_path: Path, pkg: dict) -> list:
        """Discover test directories for an npm module."""
        test_dirs = []
        for test_dir in ['test', 'tests', '__tests__', 'spec']:
            if (module_path / test_dir).exists():
                test_dirs.append(test_dir)

        jest_config = pkg.get('jest', {})
        if isinstance(jest_config, dict) and not test_dirs:
            test_match = jest_config.get('testMatch', [])
            for pattern in test_match:
                if '__tests__' in pattern:
                    test_dirs.append('__tests__')
                    break

        return test_dirs

    def _discover_npm_packages(self, module_path: Path, pkg: dict, relative_path: str) -> dict:
        """Discover npm packages from exports or directories."""
        packages = {}
        module_rel = relative_path if relative_path else '.'

        exports = pkg.get('exports', {})
        if isinstance(exports, dict):
            for export_key, export_value in exports.items():
                if export_key == '.' or not export_key.startswith('./'):
                    continue
                pkg_name = export_key[2:]
                if pkg_name:
                    export_path = export_value if isinstance(export_value, str) else None
                    pkg_path = f'{module_rel}/src/{pkg_name}' if module_rel != '.' else f'src/{pkg_name}'
                    pkg_entry: dict = {'path': pkg_path}
                    if export_path:
                        pkg_entry['exports'] = export_key
                    pkg_dir = module_path / 'src' / pkg_name
                    if pkg_dir.exists():
                        direct_files = sorted(
                            f.name for f in pkg_dir.iterdir()
                            if f.is_file() and f.suffix in {'.js', '.ts', '.mjs', '.cjs'}
                            and not f.name.endswith('.d.ts')
                        )
                        if direct_files:
                            pkg_entry['files'] = direct_files
                    packages[pkg_name] = pkg_entry

        if not packages:
            for src_dir_name in ['src', 'lib']:
                src_dir = module_path / src_dir_name
                if src_dir.exists() and src_dir.is_dir():
                    for subdir in src_dir.iterdir():
                        if subdir.is_dir() and not subdir.name.startswith('.'):
                            pkg_name = subdir.name
                            if module_rel != '.':
                                pkg_path = f'{module_rel}/{src_dir_name}/{pkg_name}'
                            else:
                                pkg_path = f'{src_dir_name}/{pkg_name}'
                            pkg_entry = {'path': pkg_path}
                            direct_files = sorted(
                                f.name for f in subdir.iterdir()
                                if f.is_file() and f.suffix in {'.js', '.ts', '.mjs', '.cjs'}
                                and not f.name.endswith('.d.ts')
                            )
                            if direct_files:
                                pkg_entry['files'] = direct_files
                            packages[pkg_name] = pkg_entry
                    break

        return packages

    def _build_npm_commands(self, module_path: str, scripts: dict, has_root_package_json: bool = True) -> dict:
        """Build canonical command mappings based on available scripts."""
        commands = {}
        base = 'python3 .plan/execute-script.py plan-marshall:build-npm:npm run'

        if module_path == '.':
            routing = ''
        elif has_root_package_json:
            routing = f' --workspace={module_path}'
        else:
            routing = f'--prefix {module_path} '

        def _cmd(npm_cmd: str) -> str:
            if routing.startswith('--prefix'):
                return f'{routing}{npm_cmd}'
            else:
                return f'{npm_cmd}{routing}'

        if 'clean' in scripts:
            commands['clean'] = f'{base} --command-args "{_cmd("run clean")}"'

        if 'build' in scripts:
            commands['compile'] = f'{base} --command-args "{_cmd("run build")}"'

        if 'test' in scripts:
            commands['module-tests'] = f'{base} --command-args "{_cmd("test")}"'

        if 'lint' in scripts:
            commands['quality-gate'] = f'{base} --command-args "{_cmd("run lint")}"'

        if 'build' in scripts and 'test' in scripts:
            commands['verify'] = f'{base} --command-args "{_cmd("run build && npm test")}"'
        elif 'test' in scripts:
            commands['verify'] = f'{base} --command-args "{_cmd("test")}"'

        return commands

    def _count_js_files(self, module_path: Path, directories: list) -> int:
        """Count JavaScript/TypeScript files in directories."""
        count = 0
        js_extensions = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}

        for dir_name in directories:
            dir_path = module_path / dir_name
            if dir_path.exists():
                for file in dir_path.rglob('*'):
                    if file.is_file() and file.suffix in js_extensions:
                        count += 1

        return count

    # =========================================================================
    # Python Discovery (from pm-dev-python)
    # =========================================================================

    def _discover_python(self, project_root: str) -> list:
        """Discover Python modules via runtime inspection."""
        if _is_plan_marshall_marketplace(project_root):
            return []

        root = Path(project_root)
        pyproject = root / PYPROJECT_TOML

        if not pyproject.exists():
            return []

        aliases = self._discover_python_aliases(pyproject)
        if not aliases:
            return []

        if not self._has_python_wrapper(root):
            return []

        commands = self._map_python_to_canonical(aliases)
        return [self._build_python_root_module(project_root, commands)]

    def _discover_python_aliases(self, pyproject: Path) -> dict:
        """Parse [tool.pyprojectx.aliases] from pyproject.toml."""
        try:
            with open(pyproject, 'rb') as f:
                data = tomllib.load(f)
            aliases = data.get('tool', {}).get('pyprojectx', {}).get('aliases', {})
            return dict(aliases) if isinstance(aliases, dict) else {}
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def _has_python_wrapper(self, project_root: Path) -> bool:
        """Check if pyprojectx wrapper exists."""
        return bool(has_wrapper(project_root, 'pw', 'pw.bat'))

    def _map_python_to_canonical(self, aliases: dict) -> dict:
        """Map pyprojectx aliases to canonical command strings."""
        base = 'python3 .plan/execute-script.py plan-marshall:build-python:python_build run'

        CANONICAL_MAPPING = {
            'compile': 'compile',
            'test-compile': 'test-compile',
            'module-tests': 'module-tests',
            'quality-gate': 'quality-gate',
            'verify': 'verify',
            'clean': 'clean',
            'coverage': 'coverage',
        }

        commands = {}
        for canonical, alias_name in CANONICAL_MAPPING.items():
            if alias_name in aliases:
                commands[canonical] = f'{base} --command-args "{canonical}"'

        return commands

    def _build_python_root_module(self, project_root: str, commands: dict) -> dict:
        """Build root module descriptor for Python project."""
        root = Path(project_root)

        source_dirs = []
        for src_dir in ['src', 'marketplace/bundles', 'lib']:
            if (root / src_dir).exists():
                source_dirs.append(src_dir)

        test_dirs = []
        for test_dir in ['test', 'tests']:
            if (root / test_dir).exists():
                test_dirs.append(test_dir)

        readme = None
        for name in ['README.md', 'README', 'readme.md', 'Readme.md', 'README.adoc']:
            if (root / name).exists():
                readme = name
                break

        paths: dict = {
            'module': '.',
            'descriptor': PYPROJECT_TOML,
            'sources': source_dirs,
            'tests': test_dirs,
        }
        if readme:
            paths['readme'] = readme

        metadata = {
            'build_tool': 'pyprojectx',
            'package_manager': 'uv',
        }

        source_files = 0
        for dir_name in source_dirs:
            dir_path = root / dir_name
            if dir_path.exists():
                for file in dir_path.rglob('*.py'):
                    if file.is_file():
                        source_files += 1

        test_files = 0
        for dir_name in test_dirs:
            dir_path = root / dir_name
            if dir_path.exists():
                for file in dir_path.rglob('*.py'):
                    if file.is_file():
                        test_files += 1

        return {
            'name': '.',
            'build_systems': ['python'],
            'paths': paths,
            'metadata': metadata,
            'packages': {},
            'dependencies': [],
            'stats': {'source_files': source_files, 'test_files': test_files},
            'commands': commands,
        }
