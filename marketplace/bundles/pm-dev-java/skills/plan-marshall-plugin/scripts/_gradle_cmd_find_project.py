#!/usr/bin/env python3
"""Find-project subcommand for Gradle project discovery."""

import json
import os
import re
from pathlib import Path


def find_settings_file(root: Path) -> Path | None:
    """Find settings.gradle or settings.gradle.kts."""
    for name in ["settings.gradle.kts", "settings.gradle"]:
        settings_path = root / name
        if settings_path.exists(): return settings_path
    return None


def parse_included_projects(settings_path: Path) -> list[str]:
    """Parse included projects from settings file."""
    with open(settings_path, encoding="utf-8") as f:
        content = f.read()
    projects = []
    for pattern in [r'include\s*\(\s*([^)]+)\s*\)', r"include\s+(['\"][^'\"]+['\"](?:\s*,\s*['\"][^'\"]+['\"])*)"]:
        for match in re.finditer(pattern, content):
            for quoted in re.findall(r'["\']([^"\']+)["\']', match.group(1)):
                projects.append(quoted if quoted.startswith(":") else f":{quoted}")
    return list(set(projects))


def get_root_project_name(settings_path: Path) -> str | None:
    """Extract rootProject.name from settings file."""
    with open(settings_path, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'rootProject\.name\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def find_build_files(root: Path) -> list[Path]:
    """Find all build.gradle and build.gradle.kts files."""
    build_files = []
    for pattern in ["**/build.gradle", "**/build.gradle.kts"]:
        for path in root.glob(pattern):
            if not any(part.startswith(".") or part in ("build", "target", ".gradle") for part in path.parts):
                build_files.append(path)
    return build_files


def project_path_to_gradle_notation(root: Path, project_dir: Path) -> str:
    """Convert file path to Gradle project notation."""
    try:
        resolved_root = Path(os.path.realpath(root))
        resolved_dir = Path(os.path.realpath(project_dir))
        relative = resolved_dir.relative_to(resolved_root)
        parts = relative.parts
        return ":" + ":".join(parts) if parts else ":"
    except ValueError:
        return ":"


def cmd_find_project(args):
    """Handle find-project subcommand."""
    root = Path(os.path.realpath(args.root))
    if not root.exists():
        print(json.dumps({"status": "error", "error": "root_not_found", "message": f"Root directory not found: {args.root}"}, indent=2))
        return 1

    if args.project_path:
        dir_path = args.project_path.lstrip(":").replace(":", "/") if args.project_path.startswith(":") else args.project_path
        full_path = root / dir_path
        if not full_path.exists():
            print(json.dumps({"status": "error", "error": "path_not_found", "message": f"Project path does not exist: {args.project_path}"}, indent=2))
            return 1
        build_file = None
        for ext in [".kts", ""]:
            candidate = full_path / f"build.gradle{ext}"
            if candidate.exists():
                build_file = str(Path(os.path.realpath(candidate)).relative_to(root))
                break
        if not build_file:
            print(json.dumps({"status": "error", "error": "no_build_file", "message": f"No build.gradle(.kts) found in: {args.project_path}"}, indent=2))
            return 1
        gradle_path = ":" + dir_path.replace("/", ":")
        parts = dir_path.split("/")
        parent_projects = [":" + ":".join(parts[:i]) for i in range(1, len(parts))]
        print(json.dumps({"status": "success", "data": {"project_name": full_path.name, "project_path": gradle_path, "build_file": build_file, "parent_projects": parent_projects, "gradle_p_argument": f"-p {dir_path}"}}, indent=2))
        return 0

    settings_file = find_settings_file(root)
    included_projects = parse_included_projects(settings_file) if settings_file else []
    root_project_name = get_root_project_name(settings_file) if settings_file else None

    if root_project_name and args.project_name == root_project_name:
        for ext in [".kts", ""]:
            candidate = root / f"build.gradle{ext}"
            if candidate.exists():
                print(json.dumps({"status": "success", "data": {"project_name": args.project_name, "project_path": ":", "build_file": f"build.gradle{ext}", "parent_projects": [], "gradle_p_argument": ""}}, indent=2))
                return 0

    matches = []
    for project in included_projects:
        project_last = project.split(":")[-1]
        if project_last == args.project_name or project == f":{args.project_name}":
            matches.append(project)

    for build_file in find_build_files(root):
        if build_file.parent.name == args.project_name:
            project_path = project_path_to_gradle_notation(root, build_file.parent)
            if project_path not in matches:
                matches.append(project_path)

    if not matches:
        print(json.dumps({"status": "error", "error": "project_not_found", "message": f"No project found with name '{args.project_name}'"}, indent=2))
        return 1
    if len(matches) > 1:
        print(json.dumps({"status": "error", "error": "ambiguous_project_name", "message": f"Multiple projects found for name '{args.project_name}'. Select one.", "choices": matches}, indent=2))
        return 1

    project_path = matches[0]
    dir_path = project_path.lstrip(":").replace(":", "/")
    build_file = None
    for ext in [".kts", ""]:
        candidate = root / dir_path / f"build.gradle{ext}"
        if candidate.exists():
            build_file = str(Path(os.path.realpath(candidate)).relative_to(root))
            break

    parts = project_path.lstrip(":").split(":")
    parent_projects = [":" + ":".join(parts[:i]) for i in range(1, len(parts))]
    print(json.dumps({"status": "success", "data": {"project_name": args.project_name, "project_path": project_path, "build_file": build_file, "parent_projects": parent_projects, "gradle_p_argument": f"-p {dir_path}" if dir_path else ""}}, indent=2))
    return 0
