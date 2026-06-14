#!/usr/bin/env python3
"""Shared utilities for analyze subcommands."""

from __future__ import annotations

import re
from pathlib import Path


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from content."""
    if not content.startswith('---'):
        return False, ''

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        return True, match.group(1)
    return False, ''


def check_yaml_validity(frontmatter: str) -> bool:
    """Basic YAML validity check."""
    return bool(re.search(r'^[a-z_]*:', frontmatter, re.MULTILINE))


def count_lines(file_path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(file_path, encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def detect_component_type(file_path: str) -> str:
    """Detect component type from file path."""
    if '/commands/' in file_path:
        return 'command'
    elif '/agents/' in file_path:
        return 'agent'
    elif '/skills/' in file_path:
        return 'skill'
    return 'unknown'


def remove_code_blocks(content: str) -> str:
    """Remove code blocks from content."""
    result = []
    in_codeblock = False

    for line in content.split('\n'):
        if line.startswith('```'):
            in_codeblock = not in_codeblock
            continue
        if not in_codeblock:
            result.append(line)

    return '\n'.join(result)


def _frontmatter_declares_glob_tool(frontmatter: str) -> bool:
    """Return True if YAML frontmatter ``tools:`` field includes ``Glob`` token.

    Handles both inline form ``tools: Read, Write, Glob`` and YAML block-list
    form (``tools:`` followed by ``  - Glob`` lines). Word-bounded match prevents
    substring false positives (e.g., "GlobalState" would not match).
    """
    inline_match = re.search(r'^tools:\s*(.+)$', frontmatter, re.MULTILINE)
    if inline_match:
        inline_value = inline_match.group(1).strip()
        # Inline form may still spill into block-list (e.g., "tools:" then "  - Glob")
        if inline_value:
            # Strip optional brackets and split on commas
            stripped = inline_value.strip('[]')
            tokens = [t.strip().strip('"').strip("'") for t in stripped.split(',')]
            if 'Glob' in tokens:
                return True

    # Block-list form: walk lines after ``tools:`` until indentation breaks
    lines = frontmatter.split('\n')
    in_tools_block = False
    for line in lines:
        if re.match(r'^tools:\s*$', line):
            in_tools_block = True
            continue
        if in_tools_block:
            # Block items are indented dash lists; stop on a top-level key
            if re.match(r'^\s*-\s*Glob\s*$', line):
                return True
            if re.match(r'^[A-Za-z_][A-Za-z0-9_-]*:', line):
                # New top-level field — block ended
                in_tools_block = False

    return False


def _frontmatter_declares_forwards_tool_capabilities(frontmatter: str) -> bool:
    """Return True if YAML frontmatter declares ``forwards_tool_capabilities: true``.

    Matches a top-level key on its own line, case-sensitive value ``true``
    (unquoted, as per YAML boolean convention). Quoted forms (``"true"`` or
    ``'true'``) and ``True``/``yes`` are NOT accepted — the canonical form
    enforced by plugin-doctor is the lowercase YAML boolean.
    """
    return bool(
        re.search(
            r'^forwards_tool_capabilities\s*:\s*true\s*$',
            frontmatter,
            re.MULTILINE,
        )
    )


def check_agent_glob_resolver_workaround(file_path: str, content: str) -> list:
    """Check agent-glob-resolver-workaround: agent declares Glob without exemption flag.

    Returns a list of finding dicts ``{line, message}``. Empty when the agent
    does not declare ``Glob`` or declares it together with
    ``forwards_tool_capabilities: true`` in the YAML frontmatter.

    Detection scope is enforced by the caller (only ``agents/*.md`` files);
    this function inspects content unconditionally so it can be unit tested
    in isolation.
    """
    findings: list = []

    # Extract frontmatter; bail out if missing
    has_frontmatter, frontmatter = extract_frontmatter(content)
    if not has_frontmatter:
        return findings

    if not _frontmatter_declares_glob_tool(frontmatter):
        return findings

    # Exemption is declared in the frontmatter as a typed boolean flag
    # `forwards_tool_capabilities: true`. No body scanning — the structural
    # intent is captured by the typed field, not by free-form prose.
    if _frontmatter_declares_forwards_tool_capabilities(frontmatter):
        return findings

    findings.append(
        {
            'line': 1,  # Frontmatter declaration is the offense; anchor at top of file
            'message': (
                'Agent declares `Glob` in tools without `forwards_tool_capabilities: true` '
                'in frontmatter (agent-glob-resolver-workaround)'
            ),
        }
    )
    return findings


# ===========================================================================
# Declarative suppression substrate
# ---------------------------------------------------------------------------
# Three composing granularities, consulted before any finding is emitted:
#
#   layer 3 (highest): per-file frontmatter  ``plugin-doctor-disable: [...]``
#   layer 2:           project config        ``.plan/plugin-doctor.yml``
#   layer 1 (lowest):  shipped default       ``<bundle>/config/default-suppression.yml``
#
# A finding for rule ``R`` against file ``F`` is suppressed when ANY layer
# matches. Frontmatter is file-scoped (rule-id in the file's disable set);
# the two config layers are path-prefix-scoped (rule-id maps to a list of
# path prefixes; a match is ``rel_to_bundles.startswith(prefix)``).
#
# Config format (constrained, stdlib-parseable — NO ``import yaml``):
# a flat mapping of top-level keys to lists of strings. Each key is either a
# rule-id (value = path-prefix list) or the literal ``disable`` (value =
# rule-id list). Lists are accepted in inline form (``key: [a, b]``) and
# YAML block-list form (``key:`` then ``  - a`` lines). The ``.yml``
# extension is retained for author familiarity only.
# ===========================================================================

# Shipped default config location, resolved relative to this module:
#   <plugin-doctor>/scripts/_analyze_shared.py  ->  <plugin-doctor>/config/default-suppression.yml
_DEFAULT_SUPPRESSION_CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'default-suppression.yml'

# Project-level config path, relative to an invocation root.
_PROJECT_SUPPRESSION_CONFIG_RELPATH = Path('.plan') / 'plugin-doctor.yml'

# Frontmatter key carrying the per-file disabled-rule list.
_FRONTMATTER_DISABLE_KEY = 'plugin-doctor-disable'


def _strip_inline_comment(value: str) -> str:
    """Strip a trailing ``# ...`` comment from a scalar/inline-list value.

    Only strips when the ``#`` is preceded by whitespace or starts the
    fragment, so a ``#`` inside a token (rare for rule-ids/paths) is left
    intact.
    """
    m = re.search(r'(?:^|\s)#', value)
    if m:
        return value[: m.start()].rstrip()
    return value


def _parse_inline_list(raw: str) -> list[str]:
    """Parse an inline list ``[a, b, c]`` (or a bare comma-separated scalar)."""
    raw = raw.strip()
    if raw.startswith('[') and raw.endswith(']'):
        raw = raw[1:-1]
    items: list[str] = []
    for token in raw.split(','):
        token = token.strip().strip('"').strip("'").strip()
        if token:
            items.append(token)
    return items


def parse_flat_yaml_config(content: str) -> dict[str, list[str]]:
    """Parse the constrained flat-YAML suppression config subset (stdlib only).

    Supported shape — a flat mapping of top-level keys to lists of strings:

        rule-id-one:
          - path/prefix/a/
          - path/prefix/b/
        rule-id-two: [path/prefix/c/, path/prefix/d/]
        disable:
          - some-rule-id

    Returns a ``{key: [value, ...]}`` mapping. Keys with an empty value list
    are retained as ``key: []``. Lines that are blank, comments, or document
    markers (``---``) are ignored. Inline (``key: [..]``) and block-list
    (``key:`` then ``  - item``) forms are both accepted; an inline scalar
    value (``key: single``) is normalised to a single-element list.

    No third-party YAML dependency is used — the accepted subset is
    deliberately flat so a small line scanner suffices.
    """
    result: dict[str, list[str]] = {}
    current_key: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        # Document markers / full-line comments.
        if stripped == '---' or stripped.startswith('#'):
            continue

        # Block-list item belonging to the current key.
        block_item = re.match(r'^\s*-\s+(.*)$', line)
        if block_item and current_key is not None:
            item = _strip_inline_comment(block_item.group(1)).strip().strip('"').strip("'").strip()
            if item:
                result.setdefault(current_key, []).append(item)
            continue

        # Top-level ``key:`` or ``key: value`` line.
        kv = re.match(r'^([A-Za-z0-9_][A-Za-z0-9_.-]*)\s*:\s*(.*)$', line)
        if kv:
            key = kv.group(1).strip()
            value = _strip_inline_comment(kv.group(2)).strip()
            current_key = key
            result.setdefault(key, [])
            if value:
                if value.startswith('['):
                    result[key].extend(_parse_inline_list(value))
                else:
                    scalar = value.strip('"').strip("'").strip()
                    if scalar:
                        result[key].append(scalar)
            continue

        # Anything else (unexpected indentation/format) is ignored — the
        # subset is intentionally narrow and fail-soft.

    return result


def read_frontmatter_disable_list(content: str) -> set[str]:
    """Return the set of rule-ids disabled via the ``plugin-doctor-disable`` key.

    Parses the per-file frontmatter ``plugin-doctor-disable`` key, accepting
    both the inline-list form::

        ---
        plugin-doctor-disable: [no-historical-prose-in-skills, verb-check]
        ---

    and the YAML block-list form::

        ---
        plugin-doctor-disable:
          - no-historical-prose-in-skills
          - verb-check
        ---

    Returns an empty set when there is no frontmatter or the key is absent.
    """
    has_frontmatter, frontmatter = extract_frontmatter(content)
    if not has_frontmatter:
        return set()

    parsed = parse_flat_yaml_config(frontmatter)
    return set(parsed.get(_FRONTMATTER_DISABLE_KEY, []))


def load_default_suppression_config() -> dict[str, list[str]]:
    """Load the shipped default suppression config from the bundle.

    The config path is resolved relative to this module
    (``<plugin-doctor>/config/default-suppression.yml``). Returns an empty
    mapping when the file does not exist or cannot be read — the substrate is
    fail-soft, so a missing default config means "no default exemptions".
    """
    path = _DEFAULT_SUPPRESSION_CONFIG_PATH
    if not path.is_file():
        return {}
    try:
        return parse_flat_yaml_config(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError):
        return {}


def load_project_suppression_config(invocation_root: str | Path) -> dict[str, list[str]]:
    """Load the project-level suppression config from ``.plan/plugin-doctor.yml``.

    ``invocation_root`` is the directory the project config is resolved
    against (typically the marketplace invocation root or the current working
    directory). Returns an empty mapping when the file is absent — an absent
    project config is a no-op.
    """
    path = Path(invocation_root) / _PROJECT_SUPPRESSION_CONFIG_RELPATH
    if not path.is_file():
        return {}
    try:
        return parse_flat_yaml_config(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError):
        return {}


def _config_layer_suppresses(
    rule_id: str,
    rel_to_bundles: str,
    config: dict[str, list[str]],
) -> bool:
    """Return True if a config layer exempts ``rule_id`` for ``rel_to_bundles``.

    A config layer maps each rule-id to a list of path prefixes. The rule is
    suppressed when ``rel_to_bundles`` starts with any of the prefixes
    registered for ``rule_id``. An empty prefix string matches every path
    (rule disabled tool-wide for the layer).
    """
    prefixes = config.get(rule_id)
    if not prefixes:
        return False
    for prefix in prefixes:
        if prefix == '' or rel_to_bundles.startswith(prefix):
            return True
    return False


def is_rule_suppressed(
    rule_id: str,
    abs_path: str | Path,
    rel_to_bundles: str,
    content: str,
    default_cfg: dict[str, list[str]],
    project_cfg: dict[str, list[str]],
) -> bool:
    """Return True if ``rule_id`` is suppressed for the given file.

    Composes the three suppression granularities in precedence order
    (highest first); the first matching layer wins:

    1. **Frontmatter** (layer 3) — ``rule_id`` appears in the file's
       ``plugin-doctor-disable`` set.
    2. **Project config** (layer 2) — ``rel_to_bundles`` matches a path
       prefix registered for ``rule_id`` in the project config.
    3. **Shipped default** (layer 1) — same path-prefix match against the
       default config.

    ``abs_path`` is accepted for API symmetry and future use (e.g. resolving
    an absolute-path allowlist); suppression today is decided from the
    frontmatter ``content`` and the ``rel_to_bundles`` relative path.
    """
    del abs_path  # Reserved for future absolute-path layers; not used today.

    # Layer 3 (highest precedence): per-file frontmatter.
    if rule_id in read_frontmatter_disable_list(content):
        return True

    # Layer 2: project config.
    if _config_layer_suppresses(rule_id, rel_to_bundles, project_cfg):
        return True

    # Layer 1 (lowest precedence): shipped default config.
    if _config_layer_suppresses(rule_id, rel_to_bundles, default_cfg):
        return True

    return False
