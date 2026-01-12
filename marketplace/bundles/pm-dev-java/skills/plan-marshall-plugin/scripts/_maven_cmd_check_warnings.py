#!/usr/bin/env python3
"""Check-warnings subcommand for categorizing build warnings."""

import json
import re
import sys
from typing import List


# Warning types that are always considered fixable
ALWAYS_FIXABLE_TYPES = ["javadoc_warning", "compilation_error", "deprecation_warning", "unchecked_warning"]


def is_acceptable(warning_message: str, patterns: List[str]) -> bool:
    """Check if a warning matches any acceptable pattern."""
    for pattern in patterns:
        clean_pattern = pattern[9:].strip() if pattern.startswith('[WARNING]') else pattern
        if clean_pattern in warning_message:
            return True
        try:
            if re.search(clean_pattern, warning_message, re.IGNORECASE):
                return True
        except re.error:
            pass
    return False


def flatten_patterns(acceptable_warnings: dict) -> List[str]:
    """Flatten acceptable_warnings object into a list of patterns."""
    patterns = []
    if isinstance(acceptable_warnings, dict):
        for value in acceptable_warnings.values():
            if isinstance(value, list):
                patterns.extend(str(p) for p in value if p)
    elif isinstance(acceptable_warnings, list):
        patterns.extend(str(p) for p in acceptable_warnings if p)
    return patterns


def cmd_check_warnings(args):
    """Handle check-warnings subcommand."""
    warnings = None
    patterns = []

    if args.warnings:
        try:
            warnings = json.loads(args.warnings)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON in --warnings: {e}"}, indent=2))
            return 1
        if args.patterns:
            try:
                patterns = json.loads(args.patterns)
            except json.JSONDecodeError as e:
                print(json.dumps({"success": False, "error": f"Invalid JSON in --patterns: {e}"}, indent=2))
                return 1
        elif args.acceptable_warnings:
            try:
                patterns = flatten_patterns(json.loads(args.acceptable_warnings))
            except json.JSONDecodeError as e:
                print(json.dumps({"success": False, "error": f"Invalid JSON in --acceptable-warnings: {e}"}, indent=2))
                return 1
    else:
        if sys.stdin.isatty():
            print(json.dumps({"success": False, "error": "No input provided. Use --warnings/--patterns or pipe JSON to stdin."}, indent=2))
            return 1
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON from stdin: {e}"}, indent=2))
            return 1
        warnings = input_data.get("warnings", [])
        patterns = input_data.get("patterns", []) or flatten_patterns(input_data.get("acceptable_warnings", {}))

    if warnings is None or not isinstance(warnings, list):
        print(json.dumps({"success": False, "error": "warnings must be an array"}, indent=2))
        return 1

    warning_items = [w for w in warnings if w.get("severity") == "WARNING"]
    acceptable, fixable, unknown = [], [], []

    for w in warning_items:
        wtype = w.get("type", "other")
        if wtype in ALWAYS_FIXABLE_TYPES:
            fixable.append(w)
        elif is_acceptable(w.get("message", ""), patterns):
            acceptable.append(w)
        elif wtype in ["compilation_error", "test_failure", "dependency_error"]:
            fixable.append(w)
        elif wtype == "openrewrite_info":
            acceptable.append(w)
        elif wtype in ["other", "other_warnings"]:
            unknown.append({**w, "requires_classification": True})
        else:
            fixable.append(w)

    result = {"success": True, "total": len(warning_items), "acceptable": len(acceptable), "fixable": len(fixable), "unknown": len(unknown), "categorized": {"acceptable": acceptable, "fixable": fixable, "unknown": unknown}}
    print(json.dumps(result, indent=2))
    return 1 if len(fixable) > 0 or len(unknown) > 0 else 0
