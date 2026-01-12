#!/usr/bin/env python3
"""Search-markers subcommand for OpenRewrite TODO markers."""

import json
import os
import re
from pathlib import Path


# Pattern for OpenRewrite TODO markers
MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)>\*/')

# Recipes that can be auto-suppressed
AUTO_SUPPRESS_RECIPES = {
    "CuiLogRecordPatternRecipe": {"category": "logrecord", "reason": "LogRecord warning - can be auto-suppressed for debug/trace logging"},
    "InvalidExceptionUsageRecipe": {"category": "exception", "reason": "Exception handling pattern - can be auto-suppressed for framework patterns"}
}


def extract_recipe_name(message: str) -> str:
    """Extract recipe name from marker message."""
    match = re.match(r'^(\w+(?:Recipe|Pattern))', message)
    if match:
        return match.group(1)
    parts = message.split()
    return parts[0].rstrip(' -:') if parts else "UnknownRecipe"


def cmd_search_markers(args):
    """Handle search-markers subcommand."""
    if not os.path.exists(args.source_dir):
        print(json.dumps({"status": "error", "error": "source_not_found", "message": f"Source directory not found: {args.source_dir}"}, indent=2))
        return 1

    extensions = [ext.strip() if ext.strip().startswith('.') else f'.{ext.strip()}' for ext in args.extensions.split(',')]
    files = []
    for ext in extensions:
        files.extend(Path(args.source_dir).rglob(f"*{ext}"))

    all_markers = []
    files_with_markers = set()

    for file_path in sorted(files):
        try:
            content = file_path.read_text(encoding='utf-8')
        except (IOError, UnicodeDecodeError):
            continue
        for line_num, line in enumerate(content.split('\n'), start=1):
            for match in MARKER_PATTERN.finditer(line):
                message = match.group(1).strip()
                recipe = extract_recipe_name(message)
                if recipe in AUTO_SUPPRESS_RECIPES:
                    info = AUTO_SUPPRESS_RECIPES[recipe]
                    category_info = {"action": "auto_suppress", "suppression_comment": f"// cui-rewrite:disable {recipe}", **info}
                else:
                    category_info = {"action": "ask_user", "category": "other", "reason": "Unknown recipe - requires user decision"}
                all_markers.append({"file": str(file_path), "line": line_num, "column": match.start() + 1, "message": message, "recipe": recipe, "raw_marker": match.group(0), **category_info})
                files_with_markers.add(str(file_path))

    auto_suppress = [m for m in all_markers if m["action"] == "auto_suppress"]
    ask_user = [m for m in all_markers if m["action"] == "ask_user"]

    result = {"status": "success", "data": {"total_markers": len(all_markers), "files_affected": len(files_with_markers), "by_category": {"auto_suppress": auto_suppress, "ask_user": ask_user}, "auto_suppress_count": len(auto_suppress), "ask_user_count": len(ask_user), "markers": all_markers}}
    print(json.dumps(result, indent=2))
    return 1 if len(ask_user) > 0 else 0
