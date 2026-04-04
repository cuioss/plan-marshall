#!/usr/bin/env python3
"""Shared marker search logic for OpenRewrite TODO markers.

Provides unified search functionality used by build-maven and build-gradle
marker search commands. Each build tool provides a thin wrapper that calls
search_openrewrite_markers() with tool-specific defaults.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

from toon_parser import serialize_toon

# Pattern for OpenRewrite TODO markers
MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)>\*/')

# Default directories to skip during search
DEFAULT_SKIP_PATTERNS = ('build', 'target', '.gradle', 'node_modules')

# Recipes that can be auto-suppressed
AUTO_SUPPRESS_RECIPES = {
    'CuiLogRecordPatternRecipe': {
        'category': 'logrecord',
        'reason': 'LogRecord warning - can be auto-suppressed for debug/trace logging',
    },
    'InvalidExceptionUsageRecipe': {
        'category': 'exception',
        'reason': 'Exception handling pattern - can be auto-suppressed for framework patterns',
    },
}


def extract_recipe_name(message: str) -> str:
    """Extract recipe name from marker message.

    Tries structured regex first (matches Recipe or Pattern suffix),
    then falls back to first word of the message.
    """
    match = re.match(r'^(\w+(?:Recipe|Pattern))', message)
    if match:
        return match.group(1)
    parts = message.split()
    return parts[0].rstrip(' -:') if parts else 'UnknownRecipe'


def search_openrewrite_markers(
    source_dir: str,
    extensions: str = '.java',
    skip_patterns: tuple[str, ...] = DEFAULT_SKIP_PATTERNS,
) -> dict:
    """Search for OpenRewrite TODO markers in source files.

    Args:
        source_dir: Root directory to search.
        extensions: Comma-separated file extensions (e.g. '.java,.kt').
        skip_patterns: Directory name patterns to skip during traversal.

    Returns:
        Result dict with status, data containing markers and summaries.
    """
    root = Path(source_dir)
    if not root.exists():
        return {
            'status': 'error',
            'error': 'source_not_found',
            'message': f'Source directory not found: {source_dir}',
        }

    ext_list = [ext.strip() if ext.strip().startswith('.') else f'.{ext.strip()}' for ext in extensions.split(',')]

    markers: list[dict] = []
    files_affected: set[str] = set()
    recipe_summary: dict[str, int] = defaultdict(int)
    by_category: dict[str, list] = {'auto_suppress': [], 'ask_user': []}

    for ext in ext_list:
        for file_path in sorted(root.rglob(f'*{ext}')):
            if any(part in skip_patterns for part in file_path.parts):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError) as e:
                logger.debug('Skipping file %s: %s', file_path, e)
                continue
            for line_num, line in enumerate(content.split('\n'), start=1):
                for match in MARKER_PATTERN.finditer(line):
                    message = match.group(1).strip()
                    recipe = extract_recipe_name(message)
                    if recipe in AUTO_SUPPRESS_RECIPES:
                        info = AUTO_SUPPRESS_RECIPES[recipe]
                        category_info = {
                            'action': 'auto_suppress',
                            'suppression_comment': f'// cui-rewrite:disable {recipe}',
                            **info,
                        }
                    else:
                        category_info = {
                            'action': 'ask_user',
                            'category': 'other',
                            'reason': 'Unknown recipe - requires user decision',
                        }
                    marker_info = {
                        'file': str(file_path),
                        'line': line_num,
                        'column': match.start() + 1,
                        'message': message,
                        'recipe': recipe,
                        'raw_marker': match.group(0),
                        **category_info,
                    }
                    markers.append(marker_info)
                    files_affected.add(str(file_path))
                    by_category[category_info['action']].append(marker_info)
                    if recipe:
                        recipe_summary[recipe] += 1

    return {
        'status': 'success',
        'data': {
            'total_markers': len(markers),
            'files_affected': len(files_affected),
            'recipe_summary': dict(recipe_summary),
            'by_category': by_category,
            'auto_suppress_count': len(by_category['auto_suppress']),
            'ask_user_count': len(by_category['ask_user']),
            'markers': markers,
        },
    }


def cmd_search_markers(args):
    """Handle search-markers subcommand.

    Standard argparse handler — reads source_dir and extensions from args,
    delegates to search_openrewrite_markers(), prints JSON result.
    """
    skip = tuple(getattr(args, 'skip_patterns', DEFAULT_SKIP_PATTERNS))
    result = search_openrewrite_markers(args.source_dir, args.extensions, skip)
    fmt = getattr(args, 'format', 'toon')
    if fmt == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(serialize_toon(result))
    if result['status'] == 'error':
        return 1
    return 1 if result['data']['ask_user_count'] > 0 else 0
