#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Domain-owned OpenRewrite marker detector for the java-cui domain.

The cui-rewrite marker format and the recipe table below describe recipes this
bundle itself defines (see ``pm-dev-java-cui:recipe-cui-logging-enforce``), so
the detector lives here rather than in the core build layer. Core dispatches it
through the ``marker-detect`` domain verb declared by this bundle's
``provides_domain_verb()`` hook, and resolves it to null when the java-cui
domain is not active.

Marker syntax is pinned by a provenance-bearing fixture taken verbatim from the
upstream recipe project's own test resources — see the fixture's PROVENANCE.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from toon_parser import serialize_toon

logger = logging.getLogger(__name__)

# Pattern for OpenRewrite TODO markers.
# The closing delimiter is `)~~>*/` — OpenRewrite's SearchResult printer emits
# `/*~~(<message>)~~>*/`. Never re-derive it from memory; it is pinned by the
# checked-in provenance fixture.
MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)~~>\*/')

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


def cmd_search(args: argparse.Namespace) -> int:
    """Handle the search subcommand.

    Exit-code contract: `1` when the search itself failed, or when ANY marker
    was detected; `0` only when the scan succeeded and the source is
    marker-free. Auto-suppressible recipes are a *categorization* — they still
    populate `by_category.auto_suppress`, `auto_suppress_count`, and the
    per-marker `suppression_comment` — but they are not an exemption from the
    non-zero exit. A gate that exits `0` on auto-suppressible markers reports
    clean while leaving the markers in the source.
    """
    skip = tuple(getattr(args, 'skip_patterns', None) or DEFAULT_SKIP_PATTERNS)
    result = search_openrewrite_markers(args.source_dir, args.extensions, skip)
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(serialize_toon(result))
    if result['status'] == 'error':
        return 1
    return 1 if result['data']['total_markers'] > 0 else 0


def main() -> int:
    """Parse arguments and dispatch the subcommand."""
    parser = argparse.ArgumentParser(
        description='Domain-owned OpenRewrite marker detection for the java-cui domain',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    search_parser = subparsers.add_parser(
        'search', help='Search OpenRewrite TODO markers in source files', allow_abbrev=False
    )
    search_parser.add_argument('--source-dir', default='src', help='Directory to search (default: src)')
    search_parser.add_argument(
        '--extensions', default='.java', help='Comma-separated file extensions (default: .java)'
    )
    search_parser.add_argument(
        '--skip-patterns',
        default=None,
        help=f'Comma-separated directory names to skip (default: {",".join(DEFAULT_SKIP_PATTERNS)})',
    )
    search_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format')

    args = parser.parse_args()

    if getattr(args, 'skip_patterns', None):
        args.skip_patterns = tuple(p.strip() for p in args.skip_patterns.split(',') if p.strip())

    if args.command == 'search':
        return cmd_search(args)

    print(serialize_toon({'status': 'error', 'error': f'Unknown command: {args.command}'}))
    return 2


if __name__ == '__main__':
    sys.exit(main() or 0)
