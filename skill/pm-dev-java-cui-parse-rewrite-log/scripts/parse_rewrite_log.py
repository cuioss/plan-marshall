#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Domain-owned OpenRewrite log-line finding parser for the java-cui domain.

This is Signal B of the two-signal OpenRewrite model (see
``../search-markers/standards/marker-detection.md``): it parses the structured
per-run WARN lines that ``cui-open-rewrite`` #118 emits into the Maven build
log, extracting one structured finding per line and classifying each as
newly-detected vs pre-existing. It is the log-parse sibling of
``pm-dev-java-cui:search-markers`` (tree-scan, Signal A) — it complements, never
replaces, the tree-scan detector.

The WARN-line format below describes log lines emitted by recipes this bundle's
domain governs, so the parser lives here rather than in the core build layer.
Core ``build-maven`` reaches it through the ``rewrite-log-parse`` domain verb
this bundle declares via ``provides_domain_verb()``, and resolves it to null
when the java-cui domain is not active.

The line format is pinned by a provenance-bearing corpus checked in verbatim
from the upstream recipe project's own source — see the fixture's
PROVENANCE.md. Never re-derive the format from memory.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from toon_parser import serialize_toon

logger = logging.getLogger(__name__)

# The application log-record prefix cui-java-tools' LogRecordModel.format renders
# is ``"%s-%s".formatted(prefix, identifier)`` followed by ``": "`` (AFTER_PREFIX),
# i.e. ``CUI_REWRITE-100: `` / ``CUI_REWRITE-101: ``. The recipe emits two WARN
# templates (RecipeLogMessages.java):
#   identifier 100 → "Finding detected at %s:%s:%s by %s: %s"     (newly-detected)
#   identifier 101 → "Finding pre-existing at %s:%s:%s by %s: %s" (pre-existing)
# whose five ``%s`` fields are: source path, line, column, recipe name, message.
RECIPE_LOG_PREFIX = 'CUI_REWRITE'
IDENTIFIER_NEWLY_DETECTED = '100'
IDENTIFIER_PRE_EXISTING = '101'

# Machine classification keyed off the structured identifier (the authoritative
# newly-detected-vs-pre-existing signal), not off the human verb word.
CLASSIFICATION_BY_IDENTIFIER = {
    IDENTIFIER_NEWLY_DETECTED: 'newly_detected',
    IDENTIFIER_PRE_EXISTING: 'pre_existing',
}

# Pattern for a single #118 WARN finding line. Pinned to the checked-in corpus;
# never re-derive it from memory. Key constraints, each load-bearing:
#   * The identifier prefix is matched as a SUBSTRING (no leading ``^`` anchor),
#     because the surrounding log layout (JUL formatter / Maven / OpenRewrite
#     console) prepends a timestamp / level tag / logger name the recipe itself
#     never emits.
#   * ``path`` and ``recipe`` are non-greedy so the literal separators
#     (``:line:column``, `` by ``, `` : ``) anchor the field boundaries.
#   * ``message`` is captured GREEDILY to end-of-line, because a marker message
#     can itself contain ``": "`` (e.g. "TODO: Throw specific not RuntimeException").
FINDING_PATTERN = re.compile(
    rf'{re.escape(RECIPE_LOG_PREFIX)}-(?P<identifier>10[01]): '
    r'Finding (?:detected|pre-existing) at '
    r'(?P<path>.+?):(?P<line>\d+):(?P<column>\d+) '
    r'by (?P<recipe>.+?): '
    r'(?P<message>.*)$'
)


def parse_finding_line(line: str) -> dict | None:
    """Parse a single log line into a structured finding, or None if it is not a finding.

    Args:
        line: One line of build-log text (without the trailing newline).

    Returns:
        A finding dict with ``path``, ``line``, ``column``, ``recipe``,
        ``message``, ``identifier``, ``classification``, and ``raw_line``; or
        ``None`` when the line carries no #118 WARN finding.
    """
    match = FINDING_PATTERN.search(line)
    if match is None:
        return None
    identifier = match.group('identifier')
    return {
        'path': match.group('path'),
        'line': int(match.group('line')),
        'column': int(match.group('column')),
        'recipe': match.group('recipe'),
        'message': match.group('message'),
        'identifier': identifier,
        'classification': CLASSIFICATION_BY_IDENTIFIER[identifier],
        'raw_line': line,
    }


def parse_rewrite_log(text: str) -> dict:
    """Parse #118 WARN finding lines out of build-log text.

    Args:
        text: The full build-log text to scan.

    Returns:
        Result dict with ``status`` and ``data`` carrying the findings list and
        newly-detected / pre-existing summary counts.
    """
    findings: list[dict] = []
    # splitlines (not split('\n')) so a CRLF-terminated log does not leave a
    # trailing '\r' swallowed into the greedy end-of-line message capture.
    for line in text.splitlines():
        finding = parse_finding_line(line)
        if finding is not None:
            findings.append(finding)

    newly_detected = sum(1 for f in findings if f['classification'] == 'newly_detected')
    pre_existing = sum(1 for f in findings if f['classification'] == 'pre_existing')

    return {
        'status': 'success',
        'data': {
            'total_findings': len(findings),
            'newly_detected_count': newly_detected,
            'pre_existing_count': pre_existing,
            'findings': findings,
        },
    }


def parse_rewrite_log_file(log_file: str) -> dict:
    """Read a build-log file and parse its #118 WARN finding lines.

    Args:
        log_file: Path to the build-log file to parse.

    Returns:
        The ``parse_rewrite_log`` result dict, or a ``status: error`` dict when
        the file cannot be read.
    """
    path = Path(log_file)
    if not path.exists():
        return {
            'status': 'error',
            'error': 'log_not_found',
            'message': f'Build-log file not found: {log_file}',
        }
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return {
            'status': 'error',
            'error': 'log_unreadable',
            'message': f'Build-log file unreadable: {log_file}: {exc}',
        }
    return parse_rewrite_log(text)


def cmd_parse(args: argparse.Namespace) -> int:
    """Handle the parse subcommand.

    Exit-code contract: ``1`` when the parse itself failed (``status: error``,
    e.g. an unreadable ``--log-file``), or when ANY finding was parsed
    (``total_findings > 0``); ``0`` only when the parse succeeded and the log
    carried no finding. Callers distinguish the two ``1`` cases by the payload's
    ``status`` field.
    """
    result = parse_rewrite_log_file(args.log_file)
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(serialize_toon(result))
    if result['status'] == 'error':
        return 1
    return 1 if result['data']['total_findings'] > 0 else 0


def main() -> int:
    """Parse arguments and dispatch the subcommand."""
    parser = argparse.ArgumentParser(
        description='Domain-owned OpenRewrite log-line finding parser for the java-cui domain',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    parse_parser = subparsers.add_parser(
        'parse', help='Parse #118 WARN finding lines from a build-log file', allow_abbrev=False
    )
    parse_parser.add_argument('--log-file', required=True, help='Path to the build-log file to parse')
    parse_parser.add_argument('--format', choices=['toon', 'json'], default='toon', help='Output format')

    args = parser.parse_args()

    if args.command == 'parse':
        return cmd_parse(args)

    print(serialize_toon({'status': 'error', 'error': f'Unknown command: {args.command}'}))
    return 2


if __name__ == '__main__':
    sys.exit(main() or 0)
