#!/usr/bin/env python3
"""Find-project subcommand for Gradle project discovery.

Delegates constants and settings parsing to _gradle_cmd_discover to avoid duplication.
"""

import re
from pathlib import Path

from _build_discover import EXCLUDE_DIRS
from _gradle_cmd_discover import (
    BUILD_GRADLE,
    BUILD_GRADLE_KTS,
    find_settings_file,
    parse_included_projects,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]


def get_root_project_name(settings_path: Path) -> str | None:
    """Extract rootProject.name from settings file."""
    with open(settings_path, encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'rootProject\.name\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def find_build_files(root: Path) -> list[Path]:
    """Find all build.gradle and build.gradle.kts files, excluding non-source dirs."""
    build_files = []
    for pattern in [f'**/{BUILD_GRADLE}', f'**/{BUILD_GRADLE_KTS}']:
        for path in root.glob(pattern):
            if not any(part.startswith('.') or part in EXCLUDE_DIRS for part in path.relative_to(root).parts):
                build_files.append(path)
    return build_files


def project_path_to_gradle_notation(root: Path, project_dir: Path) -> str:
    """Convert file path to Gradle project notation."""
    try:
        resolved_root = Path(root).resolve()
        resolved_dir = Path(project_dir).resolve()
        relative = resolved_dir.relative_to(resolved_root)
        parts = relative.parts
        return ':' + ':'.join(parts) if parts else ':'
    except ValueError:
        return ':'


def _format_output(data: dict) -> str:
    """Format output as TOON for consistency with other build subcommands."""
    return serialize_toon(data)


def cmd_find_project(args):
    """Handle find-project subcommand."""
    root = Path(args.root).resolve()
    if not root.exists():
        print(
            _format_output(
                {'status': 'error', 'error': 'root_not_found', 'message': f'Root directory not found: {args.root}'}
            )
        )
        return 1

    if args.project_path:
        dir_path = (
            args.project_path.lstrip(':').replace(':', '/') if args.project_path.startswith(':') else args.project_path
        )
        full_path = root / dir_path
        if not full_path.exists():
            print(
                _format_output(
                    {
                        'status': 'error',
                        'error': 'path_not_found',
                        'message': f'Project path does not exist: {args.project_path}',
                    }
                )
            )
            return 1
        build_file = None
        for ext in ['.kts', '']:
            candidate = full_path / f'build.gradle{ext}'
            if candidate.exists():
                build_file = str(candidate.resolve().relative_to(root))
                break
        if not build_file:
            print(
                _format_output(
                    {
                        'status': 'error',
                        'error': 'no_build_file',
                        'message': f'No build.gradle(.kts) found in: {args.project_path}',
                    }
                )
            )
            return 1
        gradle_path = ':' + dir_path.replace('/', ':')
        parts = dir_path.split('/')
        parent_projects = [':' + ':'.join(parts[:i]) for i in range(1, len(parts))]
        print(
            _format_output(
                {
                    'status': 'success',
                    'project_name': full_path.name,
                    'project_path': gradle_path,
                    'build_file': build_file,
                    'parent_projects': ','.join(parent_projects) if parent_projects else '',
                    'gradle_p_argument': f'-p {dir_path}',
                }
            )
        )
        return 0

    settings_file = find_settings_file(root)
    included_projects = parse_included_projects(settings_file) if settings_file else []
    root_project_name = get_root_project_name(settings_file) if settings_file else None

    if root_project_name and args.project_name == root_project_name:
        for ext in ['.kts', '']:
            candidate = root / f'build.gradle{ext}'
            if candidate.exists():
                print(
                    _format_output(
                        {
                            'status': 'success',
                            'project_name': args.project_name,
                            'project_path': ':',
                            'build_file': f'build.gradle{ext}',
                            'parent_projects': '',
                            'gradle_p_argument': '',
                        }
                    )
                )
                return 0

    matches = []
    for project in included_projects:
        project_last = project.split(':')[-1]
        if project_last == args.project_name or project == f':{args.project_name}':
            matches.append(project)

    for build_file in find_build_files(root):
        if build_file.parent.name == args.project_name:
            project_path = project_path_to_gradle_notation(root, build_file.parent)
            if project_path not in matches:
                matches.append(project_path)

    if not matches:
        print(
            _format_output(
                {
                    'status': 'error',
                    'error': 'project_not_found',
                    'message': f"No project found with name '{args.project_name}'",
                }
            )
        )
        return 1
    if len(matches) > 1:
        print(
            _format_output(
                {
                    'status': 'error',
                    'error': 'ambiguous_project_name',
                    'message': f"Multiple projects found for name '{args.project_name}'. Select one.",
                    'choices': ','.join(matches),
                }
            )
        )
        return 1

    project_path = matches[0]
    dir_path = project_path.lstrip(':').replace(':', '/')
    build_file = None
    for ext in ['.kts', '']:
        candidate = root / dir_path / f'build.gradle{ext}'
        if candidate.exists():
            build_file = str(candidate.resolve().relative_to(root))
            break

    parts = project_path.lstrip(':').split(':')
    parent_projects = [':' + ':'.join(parts[:i]) for i in range(1, len(parts))]
    print(
        _format_output(
            {
                'status': 'success',
                'project_name': args.project_name,
                'project_path': project_path,
                'build_file': build_file,
                'parent_projects': ','.join(parent_projects) if parent_projects else '',
                'gradle_p_argument': f'-p {dir_path}' if dir_path else '',
            }
        )
    )
    return 0
