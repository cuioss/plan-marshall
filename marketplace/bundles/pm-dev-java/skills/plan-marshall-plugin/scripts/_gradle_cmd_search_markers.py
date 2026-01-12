#!/usr/bin/env python3
"""Search-markers subcommand for OpenRewrite TODO markers."""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional


# Pattern for OpenRewrite TODO markers
MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)>\*/')

# Recipes that can be auto-suppressed
AUTO_SUPPRESS_RECIPES = {
    "CuiLogRecordPatternRecipe": {"category": "logrecord", "reason": "LogRecord warning - can be auto-suppressed for debug/trace logging"},
    "InvalidExceptionUsageRecipe": {"category": "exception", "reason": "Exception handling pattern - can be auto-suppressed for framework patterns"}
}


def extract_recipe_name(message: str) -> Optional[str]:
    """Extract recipe name from marker message."""
    for recipe in AUTO_SUPPRESS_RECIPES:
        if recipe.lower() in message.lower():
            return recipe
    match = re.match(r"(\w+Recipe):", message)
    return match.group(1) if match else None


def cmd_search_markers(args):
    """Handle search-markers subcommand."""
    if not os.path.exists(args.source_dir):
        print(json.dumps({"status": "error", "error": "source_not_found", "message": f"Source directory not found: {args.source_dir}"}, indent=2))
        return 1

    extensions = [ext.strip() if ext.strip().startswith('.') else f'.{ext.strip()}' for ext in args.extensions.split(',')]
    root = Path(args.source_dir)
    markers, files_affected, recipe_summary = [], set(), defaultdict(int)
    by_category = {"auto_suppress": [], "ask_user": []}

    for ext in extensions:
        for file_path in root.rglob(f"*{ext}"):
            if any(part in ("build", "target", ".gradle", "node_modules") for part in file_path.parts):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
            except (IOError, UnicodeDecodeError):
                continue
            for line_num, line in enumerate(content.split('\n'), start=1):
                for match in MARKER_PATTERN.finditer(line):
                    message = match.group(1).strip()
                    recipe = extract_recipe_name(message)
                    if recipe and recipe in AUTO_SUPPRESS_RECIPES:
                        info = AUTO_SUPPRESS_RECIPES[recipe]
                        category_info = {"action": "auto_suppress", "suppression_comment": f"// cui-rewrite:disable {recipe}", **info}
                    else:
                        category_info = {"action": "ask_user", "category": "other", "reason": "Unknown recipe - requires user decision"}
                    marker_info = {"file": str(file_path), "line": line_num, "column": match.start() + 1, "message": message, "recipe": recipe, "raw_marker": match.group(0), **category_info}
                    markers.append(marker_info)
                    files_affected.add(str(file_path))
                    by_category[category_info["action"]].append(marker_info)
                    if recipe:
                        recipe_summary[recipe] += 1

    result = {"status": "success", "data": {"total_markers": len(markers), "files_affected": len(files_affected), "recipe_summary": dict(recipe_summary), "by_category": by_category, "auto_suppress_count": len(by_category["auto_suppress"]), "ask_user_count": len(by_category["ask_user"]), "markers": markers}}
    print(json.dumps(result, indent=2))
    return 1 if len(by_category["ask_user"]) > 0 else 0
