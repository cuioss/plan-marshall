#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Data-not-code registry loader for the automatic-review bot pipeline.

Every reviewer bot the ``plan-marshall:automatic-review`` finalize step drives
ships one machine-readable record — a fenced-YAML data block embedded in its
``standards/{bot_kind}.md`` doc. This module parses those blocks ONCE at import
time and exposes stable accessors so the finding store, the re-review strategy
registry, and the producer pre-filter DERIVE what they need (the bot-kind set,
the login->bot_kind map, each bot's re-review trigger comment, its
skip-label-honoring flag, its ignore patterns, and its severity map) instead of
hard-coding three bots across three code files.

The loader is deliberately generic — there is no per-bot branch anywhere in it.
Adding, removing, or re-configuring a bot is a pure data edit to a
``standards/{bot_kind}.md`` block; no code changes.

Data-block shape (one per ``standards/{bot_kind}.md``)::

    ```yaml
    bot_kind: coderabbit
    author_login: coderabbitai
    trigger_comment: "@coderabbitai review"
    honors_skip_label: true
    ignore_patterns:
      - "## Walkthrough"
      - "No actionable comments were generated"
    severity_map:
      potential_issue_critical: critical
      nitpick: low
    ```

Stdlib-only (no PyYAML): the block is a tightly-constrained subset — top-level
scalars, one list (``ignore_patterns``), and one nested map (``severity_map``) —
parsed by a small deterministic reader below. Load order is the sorted
``standards/*.md`` filename order, so ``bot_kinds()`` is stable across runs.
"""

import re
from pathlib import Path
from typing import Any

# The per-bot standards docs live one level up from this scripts/ dir. Anchoring
# on ``__file__`` keeps resolution correct in both the source tree and the
# plugin cache (the scripts/ <-> standards/ sibling layout is preserved by the
# build), with no dependence on the process cwd.
STANDARDS_DIR = Path(__file__).resolve().parent.parent / 'standards'

# The registry data block is a fenced ``yaml`` code block. A standards doc may
# carry other fenced blocks (bash examples, etc.); the registry block is the one
# whose body declares a top-level ``bot_kind:`` key.
_BOT_KIND_LINE = re.compile(r'(?m)^bot_kind:')


# ---------------------------------------------------------------------------
# Minimal constrained-YAML reader (stdlib-only)
# ---------------------------------------------------------------------------


def _strip_inline_comment(text: str) -> str:
    """Drop a trailing ``#`` comment that sits OUTSIDE any quoted span.

    A ``#`` begins a YAML comment only when it is at line start or preceded by
    whitespace and is not inside a single/double-quoted string. This preserves a
    ``#`` that is part of a quoted value (e.g. an HTML comment marker) while
    stripping the rationale comments the data blocks append after values.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(text):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '#' and not in_single and not in_double and (i == 0 or text[i - 1] in ' \t'):
            return text[:i]
    return text


def _coerce(value: str) -> Any:
    """Coerce a scalar string to a bool where YAML would, else return the string."""
    if value == 'true':
        return True
    if value == 'false':
        return False
    return value


def _scalar(raw: str) -> Any:
    """Parse one scalar value: strip its inline comment, unquote, coerce booleans."""
    text = _strip_inline_comment(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1]
    return _coerce(text)


def _parse_block(block: str) -> dict[str, Any]:
    """Parse a constrained registry data block into a plain dict.

    Handles exactly the shape the ``standards/{bot_kind}.md`` blocks use:
    indent-0 ``key: value`` scalars, an indent-0 ``key:`` opening either a
    ``- item`` list or a ``key: value`` nested map. Unknown/blank/comment lines
    are skipped. No anchors, flow collections, or multi-line scalars — those are
    not present in the data blocks and are intentionally unsupported.
    """
    data: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in block.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith('#'):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(' '))

        if indent == 0:
            key, sep, rest = stripped.partition(':')
            if not sep:
                continue
            key = key.strip()
            value = _scalar(rest)
            if value == '':
                # Opening a nested block (list or map); its kind is decided by
                # the first child line encountered below.
                data[key] = None
                current_key = key
            else:
                data[key] = value
                current_key = None
            continue

        # Indented line: a child of the currently-open block key.
        if current_key is None:
            continue
        if stripped.startswith('- '):
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(_scalar(stripped[2:]))
        elif stripped == '-':
            continue
        else:
            child_key, sep, rest = stripped.partition(':')
            if not sep:
                continue
            if not isinstance(data.get(current_key), dict):
                data[current_key] = {}
            data[current_key][child_key.strip()] = _scalar(rest)

    # A block key that opened but gathered no children normalizes to an empty
    # list (harmless — the shipped blocks always carry children).
    for key, value in list(data.items()):
        if value is None:
            data[key] = []
    return data


def _extract_registry_block(md_text: str) -> str | None:
    """Return the body of the first fenced ``yaml`` block declaring ``bot_kind:``."""
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == '```yaml':
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != '```':
                body.append(lines[i])
                i += 1
            block_text = '\n'.join(body)
            if _BOT_KIND_LINE.search(block_text):
                return block_text
        i += 1
    return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class BotRegistry:
    """In-memory index of the per-bot registry records, loaded from standards docs.

    Construction parses every ``standards/*.md`` data block once; the accessors
    are pure reads over the cached index. A single module-level instance
    (:data:`REGISTRY`) backs the module-level convenience functions.
    """

    def __init__(self, standards_dir: Path = STANDARDS_DIR) -> None:
        self._standards_dir = standards_dir
        self._by_kind: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._standards_dir.is_dir():
            return
        for md_path in sorted(self._standards_dir.glob('*.md')):
            try:
                md_text = md_path.read_text(encoding='utf-8')
            except OSError:
                continue
            block = _extract_registry_block(md_text)
            if block is None:
                continue
            record = _parse_block(block)
            bot_kind = record.get('bot_kind')
            if isinstance(bot_kind, str) and bot_kind:
                self._by_kind[bot_kind] = record

    def bot_kinds(self) -> list[str]:
        """Return the registered bot-kind keys in deterministic sorted order."""
        return sorted(self._by_kind)

    def login_to_bot_kind(self) -> dict[str, str]:
        """Return the ``author_login`` -> ``bot_kind`` map across all records."""
        mapping: dict[str, str] = {}
        for bot_kind, record in self._by_kind.items():
            login = record.get('author_login')
            if isinstance(login, str) and login:
                mapping[login] = bot_kind
        return mapping

    def trigger_comment(self, bot_kind: str) -> str:
        """Return the re-review trigger comment for ``bot_kind`` (``''`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('trigger_comment', '')
        return value if isinstance(value, str) else ''

    def honors_skip_label(self, bot_kind: str) -> bool:
        """Return whether ``bot_kind`` honors the shared skip-bot-review label."""
        return bool(self._by_kind.get(bot_kind, {}).get('honors_skip_label', False))

    def ignore_patterns(self, bot_kind: str) -> list[str]:
        """Return the per-bot whole-comment ignore patterns (``[]`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('ignore_patterns', [])
        return list(value) if isinstance(value, list) else []

    def severity_map(self, bot_kind: str) -> dict[str, str]:
        """Return the per-bot marker->severity map (``{}`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('severity_map', {})
        return dict(value) if isinstance(value, dict) else {}


# Single process-wide instance parsed at import time. Consumers import either
# this object (``bot_registry.REGISTRY.bot_kinds()``) or the module-level
# functions below (``bot_registry.bot_kinds()``) — both read the same index.
REGISTRY = BotRegistry()


def bot_kinds() -> list[str]:
    """Registered bot-kind keys in deterministic sorted order."""
    return REGISTRY.bot_kinds()


def login_to_bot_kind() -> dict[str, str]:
    """The ``author_login`` -> ``bot_kind`` map across all registered bots."""
    return REGISTRY.login_to_bot_kind()


def trigger_comment(bot_kind: str) -> str:
    """The re-review trigger comment for ``bot_kind`` (``''`` if unknown)."""
    return REGISTRY.trigger_comment(bot_kind)


def honors_skip_label(bot_kind: str) -> bool:
    """Whether ``bot_kind`` honors the shared skip-bot-review label."""
    return REGISTRY.honors_skip_label(bot_kind)


def ignore_patterns(bot_kind: str) -> list[str]:
    """The per-bot whole-comment ignore patterns for ``bot_kind`` (``[]`` if unknown)."""
    return REGISTRY.ignore_patterns(bot_kind)


def severity_map(bot_kind: str) -> dict[str, str]:
    """The per-bot marker->severity map for ``bot_kind`` (``{}`` if unknown)."""
    return REGISTRY.severity_map(bot_kind)
