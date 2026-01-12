#!/usr/bin/env python3
"""Extract subcommand for extracting fixable issues from diagnosis."""

import json

from _fix_shared import FIXABLE_ISSUE_TYPES, read_json_input


def is_fixable(issue_type: str) -> bool:
    """Check if an issue type is fixable."""
    return issue_type in FIXABLE_ISSUE_TYPES


def extract_fixable_issues(diagnosis: dict) -> dict:
    """Extract only fixable issues from diagnosis results."""
    issues = diagnosis.get("issues", [])

    fixable_issues = []
    for issue in issues:
        issue_type = issue.get("type", "")
        if is_fixable(issue_type) or issue.get("fixable", False):
            fixable_issues.append(issue)

    return {
        "fixable_issues": fixable_issues,
        "total_count": len(fixable_issues),
        "source_bundle": diagnosis.get("bundle", "unknown"),
        "original_total": len(issues),
        "filtered_count": len(issues) - len(fixable_issues)
    }


def cmd_extract(args) -> int:
    """Extract fixable issues from diagnosis JSON."""
    data, error = read_json_input(args.input)

    if error:
        result = {"error": error, "fixable_issues": [], "total_count": 0}
        print(json.dumps(result, indent=2))
        return 1

    if not data:
        result = {
            "fixable_issues": [],
            "total_count": 0,
            "source_bundle": "unknown",
            "original_total": 0,
            "filtered_count": 0,
            "error": None
        }
        print(json.dumps(result, indent=2))
        return 0

    result = extract_fixable_issues(data)
    result["error"] = None
    print(json.dumps(result, indent=2))
    return 0
