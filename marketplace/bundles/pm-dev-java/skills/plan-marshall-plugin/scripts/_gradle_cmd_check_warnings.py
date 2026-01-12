#!/usr/bin/env python3
"""Check-warnings subcommand for categorizing build warnings."""

import json
import re
import sys


# Warning types that are always considered fixable
ALWAYS_FIXABLE_TYPES = ["javadoc_warning", "compilation_error", "deprecation_warning", "unchecked_warning"]


def match_pattern(message: str, pattern: str) -> bool:
    """Check if message matches pattern."""
    if message == pattern: return True
    if pattern.endswith("*") and message.startswith(pattern[:-1]): return True
    if pattern.startswith("*") and pattern.endswith("*") and pattern[1:-1] in message: return True
    if pattern.startswith("*") and message.endswith(pattern[1:]): return True
    if pattern.startswith("^"):
        try:
            if re.match(pattern, message): return True
        except re.error:
            pass
    return False


def cmd_check_warnings(args):
    """Handle check-warnings subcommand."""
    warnings, acceptable_patterns = None, {}

    if args.warnings:
        try:
            warnings = json.loads(args.warnings)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid warnings JSON: {e}"}, indent=2))
            return 1
        if args.acceptable_warnings:
            try:
                acceptable_patterns = json.loads(args.acceptable_warnings)
            except json.JSONDecodeError:
                pass
    else:
        if sys.stdin.isatty():
            print(json.dumps({"success": False, "error": "No input provided. Use --warnings or pipe JSON to stdin."}, indent=2))
            return 1
        try:
            data = json.load(sys.stdin)
            warnings = data.get("warnings", [])
            acceptable_patterns = data.get("acceptable_warnings", {})
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid stdin JSON: {e}"}, indent=2))
            return 1

    if warnings is None or not isinstance(warnings, list):
        print(json.dumps({"success": False, "error": "warnings must be an array"}, indent=2))
        return 1

    categorized = {"acceptable": [], "fixable": [], "unknown": []}
    for warning in warnings:
        warning_type = warning.get("type", "other")
        message = warning.get("message", "")

        if warning_type in ALWAYS_FIXABLE_TYPES:
            categorized["fixable"].append({**warning, "reason": f"Type '{warning_type}' is always fixable"})
            continue

        is_acceptable, matched_category = False, None
        for category, patterns in acceptable_patterns.items():
            for pattern in patterns:
                if match_pattern(message, pattern):
                    is_acceptable, matched_category = True, category
                    break
            if is_acceptable:
                break

        if is_acceptable:
            categorized["acceptable"].append({**warning, "reason": f"Matches acceptable pattern in '{matched_category}'"})
        else:
            categorized["unknown"].append({**warning, "reason": "No matching acceptable pattern"})

    result = {"success": True, "total": len(warnings), "acceptable": len(categorized["acceptable"]), "fixable": len(categorized["fixable"]), "unknown": len(categorized["unknown"]), "categorized": categorized}
    print(json.dumps(result, indent=2))
    return 1 if result["fixable"] > 0 or result["unknown"] > 0 else 0
