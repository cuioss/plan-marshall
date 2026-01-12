#!/usr/bin/env python3
"""Fix application functions for doctor-marketplace."""

from pathlib import Path
from typing import Dict, List, Optional

from _cmd_apply import apply_single_fix, load_templates
from _doctor_shared import find_bundle_for_file


def apply_safe_fixes(issues: List[Dict], marketplace_root: Path, script_dir: Path, dry_run: bool = False) -> Dict:
    """Apply all safe fixes to files."""
    results = {
        "applied": [],
        "failed": [],
        "skipped": [],
        "dry_run": dry_run
    }

    templates = load_templates(script_dir)

    # Group issues by file to avoid conflicts
    by_file: Dict[str, List[Dict]] = {}
    for issue in issues:
        file_path = issue.get("file", "")
        if file_path:
            by_file.setdefault(file_path, []).append(issue)

    for file_path, file_issues in by_file.items():
        path = Path(file_path)
        if not path.exists():
            for issue in file_issues:
                results["failed"].append({
                    "issue": issue,
                    "error": f"File not found: {file_path}"
                })
            continue

        # Find bundle directory for this file
        bundle_dir = find_bundle_for_file(path, marketplace_root)
        if not bundle_dir:
            for issue in file_issues:
                results["failed"].append({
                    "issue": issue,
                    "error": "Could not determine bundle directory"
                })
            continue

        for issue in file_issues:
            if dry_run:
                results["skipped"].append({
                    "issue": issue,
                    "reason": "dry_run"
                })
                continue

            # Convert absolute path to relative for apply_single_fix
            try:
                rel_path = str(path.relative_to(bundle_dir))
            except ValueError:
                rel_path = str(path)

            fix_data = {
                "type": issue.get("type"),
                "file": rel_path,
                "details": issue.get("details", {})
            }

            result = apply_single_fix(fix_data, bundle_dir, templates)

            if result.get("success"):
                results["applied"].append({
                    "issue": issue,
                    "result": result
                })
            else:
                results["failed"].append({
                    "issue": issue,
                    "error": result.get("error", "Unknown error")
                })

    return results
