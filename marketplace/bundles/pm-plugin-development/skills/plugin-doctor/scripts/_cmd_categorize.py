#!/usr/bin/env python3
"""Categorize subcommand for categorizing fixes as safe or risky."""

import json

from _fix_shared import SAFE_FIX_TYPES, RISKY_FIX_TYPES, read_json_input


def categorize_fix(issue: dict) -> str:
    """Categorize a single issue as 'safe' or 'risky'."""
    issue_type = issue.get("type", "")

    if issue_type in SAFE_FIX_TYPES:
        return "safe"
    elif issue_type in RISKY_FIX_TYPES:
        return "risky"
    else:
        return "risky"


def categorize_issues(extracted: dict) -> dict:
    """Categorize all fixable issues into safe and risky categories."""
    issues = extracted.get("fixable_issues", [])

    safe_fixes = []
    risky_fixes = []

    for issue in issues:
        category = categorize_fix(issue)
        if category == "safe":
            safe_fixes.append(issue)
        else:
            risky_fixes.append(issue)

    return {
        "safe": safe_fixes,
        "risky": risky_fixes,
        "summary": {
            "safe_count": len(safe_fixes),
            "risky_count": len(risky_fixes),
            "total_count": len(issues)
        },
        "source_bundle": extracted.get("source_bundle", "unknown")
    }


def cmd_categorize(args) -> int:
    """Categorize fixable issues as safe or risky."""
    data, error = read_json_input(args.input)

    if error:
        result = {
            "error": error,
            "safe": [],
            "risky": [],
            "summary": {"safe_count": 0, "risky_count": 0, "total_count": 0}
        }
        print(json.dumps(result, indent=2))
        return 1

    if not data:
        result = {
            "safe": [],
            "risky": [],
            "summary": {"safe_count": 0, "risky_count": 0, "total_count": 0},
            "error": None
        }
        print(json.dumps(result, indent=2))
        return 0

    result = categorize_issues(data)
    result["error"] = None
    print(json.dumps(result, indent=2))
    return 0
