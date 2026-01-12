#!/usr/bin/env python3
"""
Configure .gitignore for the planning system.

Ensures .plan/* contents are ignored while marshal.json is tracked.
Uses .plan/* (not .plan/) to allow exceptions - .plan/ ignores the entire
directory making exceptions impossible.

Usage:
    python3 gitignore-setup.py [--dry-run]

Options:
    --dry-run              Show what would be done without making changes

Output (TOON format):
    status	created
    gitignore_path	/path/to/.gitignore
    entries_added	2

    status	updated
    gitignore_path	/path/to/.gitignore
    entries_added	1

    status	unchanged
    gitignore_path	/path/to/.gitignore
    entries_added	0
"""

import argparse
import sys
from pathlib import Path

# Lines to add to .gitignore
# Use .plan/* (not .plan/) to allow exceptions - .plan/ ignores entire directory
GITIGNORE_COMMENT = "# Planning system (managed by /marshall-steward)"
GITIGNORE_PLAN_DIR = ".plan/*"
GITIGNORE_MARSHAL_EXCEPTION = "!.plan/marshal.json"
GITIGNORE_ARCHITECTURE_EXCEPTION = "!.plan/project-architecture/"


def check_gitignore_status(gitignore_path: Path) -> dict:
    """
    Check current state of .gitignore regarding .plan/ entries.

    Args:
        gitignore_path: Path to .gitignore file

    Returns:
        Dict with:
        - exists: bool
        - has_plan_dir: bool
        - has_marshal_exception: bool
        - has_architecture_exception: bool
        - content: str (if exists)
    """
    result = {
        "exists": gitignore_path.exists(),
        "has_plan_dir": False,
        "has_marshal_exception": False,
        "has_architecture_exception": False,
        "content": ""
    }

    if result["exists"]:
        result["content"] = gitignore_path.read_text()
        lines = result["content"].splitlines()

        for line in lines:
            stripped = line.strip()
            # Accept both .plan/* (correct) and .plan/ or .plan (legacy)
            if stripped in (".plan/*", ".plan/", ".plan"):
                result["has_plan_dir"] = True
            if stripped == GITIGNORE_MARSHAL_EXCEPTION:
                result["has_marshal_exception"] = True
            if stripped == GITIGNORE_ARCHITECTURE_EXCEPTION:
                result["has_architecture_exception"] = True

    return result


def setup_gitignore(project_root: Path, dry_run: bool = False) -> dict:
    """
    Configure .gitignore for planning system.

    Args:
        project_root: Project root directory containing .gitignore
        dry_run: If True, don't make changes

    Returns:
        Dict with status, path, and entries_added count
    """
    gitignore_path = project_root / ".gitignore"
    status = check_gitignore_status(gitignore_path)

    entries_to_add = []

    if not status["has_plan_dir"]:
        entries_to_add.append(GITIGNORE_PLAN_DIR)
    if not status["has_marshal_exception"]:
        entries_to_add.append(GITIGNORE_MARSHAL_EXCEPTION)
    if not status["has_architecture_exception"]:
        entries_to_add.append(GITIGNORE_ARCHITECTURE_EXCEPTION)

    result = {
        "gitignore_path": str(gitignore_path.absolute()),
        "entries_added": len(entries_to_add),
        "dry_run": dry_run
    }

    if not entries_to_add:
        result["status"] = "unchanged"
        return result

    if not status["exists"]:
        # Create new .gitignore
        result["status"] = "created"
        new_content = f"{GITIGNORE_COMMENT}\n{GITIGNORE_PLAN_DIR}\n{GITIGNORE_MARSHAL_EXCEPTION}\n{GITIGNORE_ARCHITECTURE_EXCEPTION}\n"
    else:
        # Update existing .gitignore
        result["status"] = "updated"
        content = status["content"]

        # Ensure content ends with newline
        if content and not content.endswith("\n"):
            content += "\n"

        # Add blank line before comment if content exists and doesn't end with blank line
        if content and not content.endswith("\n\n"):
            content += "\n"

        # Add comment and entries
        content += f"{GITIGNORE_COMMENT}\n"
        for entry in entries_to_add:
            content += f"{entry}\n"

        new_content = content

    if not dry_run:
        gitignore_path.write_text(new_content)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure .gitignore for planning system"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()
    project_root = Path(args.project_root)

    if not project_root.exists():
        print("status\terror", file=sys.stderr)
        print("error\tproject_root_not_found", file=sys.stderr)
        print(f"path\t{project_root}", file=sys.stderr)
        return 1

    result = setup_gitignore(project_root, args.dry_run)

    # Output in TOON format
    print(f"status\t{result['status']}")
    print(f"gitignore_path\t{result['gitignore_path']}")
    print(f"entries_added\t{result['entries_added']}")
    if result['dry_run']:
        print("dry_run\ttrue")

    return 0


if __name__ == "__main__":
    sys.exit(main())
