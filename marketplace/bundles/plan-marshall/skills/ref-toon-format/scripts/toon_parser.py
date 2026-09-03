#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
TOON (Token-Oriented Object Notation) parser for workflow scripts.

Provides parsing and serialization of TOON format - a compact, human-readable
encoding optimized for LLM token efficiency.

Supports:
- Simple key-value pairs (key: value)
- Nested objects via indentation (2-space indent only)
- Uniform arrays with headers (items[N]{field1,field2}:)
- Comments (#)
- Multi-line values (|)

Limitations:
- Only 2-space indentation is supported for nesting (not tabs or 4-space)
- Percentage values (e.g., '95%') are parsed as int (lossy — '95%' becomes 95)

Stdlib-only - no external dependencies.

Usage:
    from toon_parser import parse_toon, serialize_toon, ToonParseError
"""

import json
import re
from dataclasses import dataclass
from typing import Any, NamedTuple

__version__ = '3.0'

__all__ = [
    'SimpleArrayLine',
    'ToonParseError',
    'block_scalar_body_continues',
    'block_scalar_header_indent',
    'classify_simple_array_line',
    'list_item_min_indent',
    'parse_toon',
    'parse_toon_table',
    'serialize_toon',
    'value_needs_quoting',
]


class ToonParseError(Exception):
    """Error during TOON parsing with line context."""

    def __init__(self, message: str, line_number: int = 0, line_content: str = ''):
        self.line_number = line_number
        self.line_content = line_content
        super().__init__(f'Line {line_number}: {message}\n  > {line_content}')


@dataclass
class ParseContext:
    """Internal parsing context."""

    lines: list[str]
    index: int = 0
    base_indent: int = 0


def _get_indent(line: str) -> int:
    """Get the indentation level of a line (count of leading spaces)."""
    return len(line) - len(line.lstrip())


def _parse_value(value_str: str) -> Any:
    """Parse a TOON value string into Python type."""
    value_str = value_str.strip()

    # Empty
    if not value_str:
        return ''

    # Null
    if value_str == 'null':
        return None

    # Boolean
    if value_str == 'true':
        return True
    if value_str == 'false':
        return False

    # Number (int or float)
    if re.match(r'^-?\d+$', value_str):
        return int(value_str)
    if re.match(r'^-?\d+\.\d+$', value_str):
        return float(value_str)

    # Percentage (convert to int)
    if re.match(r'^\d+%$', value_str):
        return int(value_str[:-1])

    # String (possibly quoted)
    if value_str.startswith('"') and value_str.endswith('"'):
        inner = value_str[1:-1]
        # Unescape internal quotes
        inner = inner.replace('\\"', '"')
        # Check if it's an embedded JSON array or object
        if (inner.startswith('[') and inner.endswith(']')) or (inner.startswith('{') and inner.endswith('}')):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass
        return inner

    return value_str


def _parse_csv_row(row: str, fields: list[str]) -> dict[str, Any]:
    """Parse a CSV/TSV-style row into a dictionary using field headers.

    Auto-detects separator: tabs if present, otherwise commas.
    """
    result = {}

    # Auto-detect separator: tab-separated if tabs present, else comma-separated
    if '\t' in row:
        values = [v.strip() for v in row.split('\t')]
    else:
        # Handle quoted values with commas and escaped quotes
        values = []
        current = ''
        in_quotes = False
        i = 0

        while i < len(row):
            char = row[i]
            # Handle escaped quotes within quoted strings
            if in_quotes and char == '\\' and i + 1 < len(row) and row[i + 1] == '"':
                current += '\\"'
                i += 2
                continue
            if char == '"':
                current += char
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ''
            else:
                current += char
            i += 1

        values.append(current.strip())

    # Map values to fields
    for i, field in enumerate(fields):
        if i < len(values):
            result[field] = _parse_value(values[i])
        else:
            result[field] = None

    return result


def _parse_uniform_array(ctx: ParseContext, count: int, fields: list[str], min_indent: int) -> list[dict]:
    """Parse uniform array rows.

    Args:
        ctx: Parse context
        count: Expected number of rows
        fields: Field names for CSV parsing
        min_indent: Minimum indentation for array rows (rows must be >= this)
    """
    result: list[dict[str, Any]] = []

    while ctx.index < len(ctx.lines) and len(result) < count:
        line = ctx.lines[ctx.index]

        # Skip empty lines
        if not line.strip():
            ctx.index += 1
            continue

        # Skip comments
        if line.strip().startswith('#'):
            ctx.index += 1
            continue

        indent = _get_indent(line)
        content = line.strip()

        # Check if we've exited the array (less indentation than required)
        if indent < min_indent and content:
            break

        # Parse the row if it's at the right indentation
        if indent >= min_indent and content and not content.startswith('#'):
            # Check if this looks like a new key-value pair (word followed by colon at start).
            #
            # A genuine TOON key/value pair has the structural shape `<key>:` followed by
            # either whitespace-then-value or end-of-line (for nested-block keys). The
            # `(?=\s|$)` lookahead enforces that — CSV/TSV first-column data whose first
            # field contains a colon (e.g. `plan-marshall:foo:bar,1` for the
            # `failures[N]{notation,exit_code}` table, or `lint:strict` / `coverage:enforce`
            # for CI check-name TSV rows) has `<ident>:<more-data>` with NO trailing space,
            # so the lookahead fails and the array continues parsing.
            #
            # Additional guards:
            #   - starts with `<ident>,` -> CSV row with bare identifier first column
            #   - contains a TAB -> TSV row (tabs never appear in TOON key/value pairs)
            #
            # Identifier character class includes `-` so hyphenated TOON keys
            # (`base-branch`, `worktree-path`) still terminate arrays correctly when
            # a sibling key/value pair follows the array body without an outdent.
            # The CI-stress fixtures and the
            # `failures[N]{notation,exit_code}` regression motivated the
            # lookahead.
            looks_like_key_value = (
                re.match(r'^[a-zA-Z_][\w_-]*\s*:(?=\s|$)', content)
                and not re.match(r'^[a-zA-Z_][\w_-]*,', content)
                and '\t' not in content
            )
            if looks_like_key_value:
                # This is a new key-value pair, stop parsing array
                break
            result.append(_parse_csv_row(content, fields))

        ctx.index += 1

    return result


def list_item_min_indent(header_indent: int) -> int:
    """Report the minimum indent a row must carry to belong to an array header.

    A top-level header (indent 0) admits rows at column 0 as well as indented
    ones: a document whose whole body sits at column 0 has no shallower level
    for a row to fall out of, so requiring a deeper row would reject the shape
    ``parse_toon_table``'s own documented example writes. A nested header admits
    rows at its own indent or deeper.

    Exported because it is a BOUNDARY, and any second reader that must agree
    with ``parse_toon`` about which rows belong to a list has to derive it from
    here rather than restate it — two readers deriving one boundary two ways is
    how a row becomes visible to one and invisible to the other.

    Args:
        header_indent: Leading-space count of the ``key[N]:`` header line.

    Returns:
        The minimum leading-space count an item row may carry.
    """
    return 0 if header_indent == 0 else header_indent


class SimpleArrayLine(NamedTuple):
    """One line's role while walking a simple-array body.

    Attributes:
        kind: ``item`` when the line is a list row, ``skip`` when it belongs to
            the body but carries no value (blank line, comment, malformed
            marker), ``end`` when the array has closed before this line.
        value: The raw row text after the ``- `` marker, still quoted exactly as
            written; empty unless ``kind`` is ``item``.
    """

    kind: str
    value: str


def classify_simple_array_line(line: str, min_indent: int) -> SimpleArrayLine:
    """Decide whether a line is a simple-array row, ignorable, or past the array's end.

    This is the single membership rule for a ``key[N]:`` list body. It is
    exported alongside ``list_item_min_indent`` so that a caller which has to
    walk the same body for its own purposes — collecting the raw, still-quoted
    row texts before ``parse_toon`` unquotes them, say — reads the identical
    boundary instead of approximating it.

    Args:
        line: The raw line, indentation included.
        min_indent: The array's minimum row indent, from ``list_item_min_indent``.

    Returns:
        The line's role, with the raw row text when it is an item.
    """
    content = line.strip()
    if not content or content.startswith('#'):
        return SimpleArrayLine('skip', '')
    if _get_indent(line) < min_indent:
        return SimpleArrayLine('end', '')
    if content.startswith('- '):
        return SimpleArrayLine('item', content[2:])
    if not content.startswith('-'):
        return SimpleArrayLine('end', '')
    return SimpleArrayLine('skip', '')


def _parse_simple_array(ctx: ParseContext, min_indent: int) -> list[Any]:
    """Parse a simple list with - markers.

    Args:
        ctx: Parse context
        min_indent: Minimum indentation for array items (items must be >= this)
    """
    result = []

    while ctx.index < len(ctx.lines):
        classified = classify_simple_array_line(ctx.lines[ctx.index], min_indent)
        if classified.kind == 'end':
            break
        if classified.kind == 'item':
            result.append(_parse_value(classified.value))
        ctx.index += 1

    return result


def block_scalar_header_indent(line: str) -> int | None:
    """Report the header indent when ``line`` opens a block scalar, else ``None``.

    The rule is the one ``_parse_object`` applies and nothing narrower: take the
    text up to the FIRST colon as the key, and the block opens when everything
    after that colon is exactly the ``|`` marker. The key is therefore ANY text —
    ``task.name: |`` and ``a b c: |`` open a block scalar just as ``description: |``
    does — because the parser never constrains it. Blank and comment lines are
    excluded for the same reason: ``_parse_object`` skips them before it ever
    looks for a key.

    Exported because it is a BOUNDARY. Any second reader that must agree with
    ``parse_toon`` about where opaque prose begins has to derive it from here
    rather than restate it — a stricter key class here and a permissive one in
    the parser is how a block's prose body becomes structure to one reader and
    text to the other.

    Args:
        line: The raw line, indentation included.

    Returns:
        The header's leading-space count when the line opens a block scalar,
        ``None`` otherwise.
    """
    content = line.strip()
    if not content or content.startswith('#') or ':' not in content:
        return None
    if content[content.index(':') + 1 :].strip() != '|':
        return None
    return _get_indent(line)


def block_scalar_body_continues(line: str, header_indent: int) -> bool:
    """Report whether ``line`` still belongs to the body of a block scalar.

    The body runs while lines are blank or indented deeper than the ``key: |``
    header, and closes at the first non-blank line indented at or outside it.

    Exported for the same reason as ``block_scalar_header_indent``: the extent of
    a block scalar is a boundary two readers must agree on, so both consume this
    predicate instead of each deriving it.

    Args:
        line: The raw line, indentation included.
        header_indent: Leading-space count of the ``key: |`` header line.

    Returns:
        ``True`` while the line is part of the body, ``False`` at its end.
    """
    return not line.strip() or _get_indent(line) > header_indent


def _parse_multiline_value(ctx: ParseContext, base_indent: int) -> str:
    """Parse a multi-line string value (indicated by |)."""
    lines = []

    while ctx.index < len(ctx.lines):
        line = ctx.lines[ctx.index]
        if not block_scalar_body_continues(line, base_indent):
            break

        # Empty line within multi-line is preserved
        if not line.strip():
            lines.append('')
        else:
            lines.append(line[base_indent + 2 :] if len(line) > base_indent + 2 else line.strip())
        ctx.index += 1

    return '\n'.join(lines).strip()


def _parse_object(ctx: ParseContext, base_indent: int) -> dict[str, Any]:
    """Parse a TOON object at the given indentation level."""
    result: dict[str, Any] = {}

    while ctx.index < len(ctx.lines):
        line = ctx.lines[ctx.index]

        # Skip empty lines
        if not line.strip():
            ctx.index += 1
            continue

        # Skip comments
        if line.strip().startswith('#'):
            ctx.index += 1
            continue

        indent = _get_indent(line)
        content = line.strip()

        # Check if we've exited this indentation level
        if indent < base_indent:
            break

        # Check if this is at our level
        if indent > base_indent:
            ctx.index += 1
            continue

        # Parse key: value
        if ':' in content:
            # Check for uniform array pattern: key[N]{fields}:
            # Note: Key can contain hyphens (e.g., oauth-sheriff-core[1]{...}:)
            array_match = re.match(r'^([\w_-]+)\[(\d+)\]\{([^}]+)\}:\s*$', content)
            if array_match:
                key = array_match.group(1)
                count = int(array_match.group(2))
                fields = [f.strip() for f in array_match.group(3).split(',')]
                ctx.index += 1
                result[key] = _parse_uniform_array(ctx, count, fields, list_item_min_indent(indent))
                continue

            # Check for simple array pattern: key[N]:
            # Note: Key can contain hyphens (e.g., oauth-sheriff-core[1]:)
            simple_array_match = re.match(r'^([\w_-]+)\[(\d+)\]:\s*$', content)
            if simple_array_match:
                key = simple_array_match.group(1)
                ctx.index += 1
                result[key] = _parse_simple_array(ctx, list_item_min_indent(indent))
                continue

            # Regular key: value
            colon_pos = content.index(':')
            key = content[:colon_pos].strip()
            value_part = content[colon_pos + 1 :].strip()

            ctx.index += 1

            # Check for multi-line value — the block-scalar rule lives in
            # ``block_scalar_header_indent`` so second readers consume it rather
            # than approximating it.
            if block_scalar_header_indent(line) is not None:
                result[key] = _parse_multiline_value(ctx, indent)
            # Check for nested object (no value after colon)
            elif not value_part:
                # Peek ahead to see if there's actually nested content
                has_nested_content = False
                peek_idx = ctx.index
                while peek_idx < len(ctx.lines):
                    peek_line = ctx.lines[peek_idx]
                    if not peek_line.strip():
                        peek_idx += 1
                        continue
                    if peek_line.strip().startswith('#'):
                        peek_idx += 1
                        continue
                    # Check if next non-empty line is indented more than current
                    peek_indent = _get_indent(peek_line)
                    if peek_indent > indent:
                        has_nested_content = True
                    break

                if has_nested_content:
                    result[key] = _parse_object(ctx, indent + 2)
                else:
                    result[key] = ''
            else:
                result[key] = _parse_value(value_part)
        else:
            # Unknown line format, skip
            ctx.index += 1

    return result


def parse_toon(content: str) -> dict[str, Any]:
    """Parse TOON content into a Python dictionary.

    Args:
        content: TOON formatted string

    Returns:
        Parsed dictionary

    Raises:
        ToonParseError: If parsing fails

    Example:
        >>> toon = '''
        ... name: Alice
        ... age: 30
        ... roles[2]{id,name}:
        ... 1,admin
        ... 2,user
        ... '''
        >>> parse_toon(toon)
        {'name': 'Alice', 'age': 30, 'roles': [{'id': 1, 'name': 'admin'}, {'id': 2, 'name': 'user'}]}
    """
    lines = content.split('\n')
    ctx = ParseContext(lines=lines)

    try:
        return _parse_object(ctx, 0)
    except Exception as e:
        raise ToonParseError(
            str(e), line_number=ctx.index + 1, line_content=ctx.lines[ctx.index] if ctx.index < len(ctx.lines) else ''
        ) from e


def parse_toon_table(content: str, key: str, *, null_markers: set[str] | None = None) -> list[dict[str, Any]]:
    """Extract a uniform array table from TOON content.

    Convenience wrapper around parse_toon() for extracting a single table
    from TOON output. Useful when a script returns TOON with a table and
    the caller only needs the table rows.

    Args:
        content: TOON formatted string
        key: Key of the uniform array to extract (e.g., 'comments', 'issues')
        null_markers: Optional set of value strings to convert to None
                      (e.g., {'-', '~'} for tabular data where '-' means empty)

    Returns:
        List of dictionaries from the table, or empty list if key not found

    Example:
        >>> toon = '''
        ... status: success
        ... total: 2
        ... users[2]{id,name,active}:
        ... 1\\tAlice\\ttrue
        ... 2\\t-\\tfalse
        ... '''
        >>> parse_toon_table(toon, 'users', null_markers={'-'})
        [{'id': 1, 'name': None, 'active': True}, {'id': 2, 'name': None, 'active': False}]
    """
    parsed = parse_toon(content)
    table = parsed.get(key, [])
    if not isinstance(table, list):
        return []
    rows = [row for row in table if isinstance(row, dict)]
    if null_markers:
        return [{k: None if v in null_markers else v for k, v in row.items()} for row in rows]
    return rows


def value_needs_quoting(value: str, table_separator: str = ',') -> bool:
    """Report whether ``serialize_toon`` would wrap ``value`` in outer double-quotes.

    This is the serializer's own quoting decision, exposed as a named predicate so
    consumers can discriminate a quote the serializer was OBLIGED to add from a
    quote a human added by hand. Re-deriving the rule at a call site would
    duplicate the decision and let the two copies drift; consult this function
    instead.

    Args:
        value: The raw (unquoted) string the serializer is about to emit.
        table_separator: The separator in force for the current uniform-array
            table (``','`` for CSV rows, ``'\\t'`` for TSV rows). A value
            containing the active separator must be quoted or it would split the
            row.

    Returns:
        ``True`` when the value must be quoted, ``False`` when it may be emitted
        bare.
    """
    return bool(
        table_separator in value
        or ',' in value
        or ':' in value
        or '\n' in value
        or '"' in value
        or value.startswith('#')
        or value.startswith('- ')
        or value in ('true', 'false', 'null', '')
        or re.match(r'^-?\d+$', value)
        or re.match(r'^-?\d+\.\d+$', value)
        or re.match(r'^\d+%$', value)
    )


def _serialize_value(value: Any, table_separator: str = ',') -> str:
    """Serialize a Python value to TOON format.

    Args:
        value: Value to serialize
        table_separator: Current table separator (values containing it need quoting)

    Returns:
        TOON formatted string (may be multi-line for complex types)
    """
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Quote if contains separator, special characters, or would be misinterpreted
        if value_needs_quoting(value, table_separator):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        return value
    if isinstance(value, dict):
        # Serialize dict as JSON string (wrapped in quotes, internal quotes escaped)
        json_str = json.dumps(value).replace('"', '\\"')
        return f'"{json_str}"'
    if isinstance(value, list):
        # Serialize list as JSON string (wrapped in quotes, internal quotes escaped)
        json_str = json.dumps(value).replace('"', '\\"')
        return f'"{json_str}"'
    return str(value)


def _is_uniform_array(arr: list) -> tuple[bool, list[str]]:
    """Check if array is uniform (all dicts with compatible keys).

    Returns True if all items are dicts. Uses union of all keys found,
    allowing optional fields (missing keys serialize as empty).

    Args:
        arr: List to check

    Returns:
        Tuple of (is_uniform, field_names)
    """
    if not arr:
        return False, []

    if not all(isinstance(item, dict) for item in arr):
        return False, []

    # Collect union of all keys across all items (preserves order from first occurrence)
    all_keys = []
    seen_keys = set()
    for item in arr:
        for key in item.keys():
            if key not in seen_keys:
                all_keys.append(key)
                seen_keys.add(key)

    return True, all_keys


def serialize_toon(data: dict[str, Any], indent: int = 0, table_separator: str = ',') -> str:
    """Serialize a Python dictionary to TOON format.

    Args:
        data: Dictionary to serialize
        indent: Current indentation level (internal use)
        table_separator: Separator for uniform array rows (',' or '\\t')

    Returns:
        TOON formatted string

    Example:
        >>> data = {'name': 'Alice', 'active': True}
        >>> print(serialize_toon(data))
        name: Alice
        active: true
    """
    lines = []
    prefix = '  ' * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f'{prefix}{key}:')
            lines.append(serialize_toon(value, indent + 1, table_separator))
        elif isinstance(value, list):
            is_uniform, fields = _is_uniform_array(value)
            if is_uniform and fields:
                # Uniform array with headers
                lines.append(f'{prefix}{key}[{len(value)}]{{{",".join(fields)}}}:')
                for item in value:
                    row_values = [_serialize_value(item.get(f, ''), table_separator) for f in fields]
                    lines.append(f'{prefix}  {table_separator.join(row_values)}')
            else:
                # Simple array
                lines.append(f'{prefix}{key}[{len(value)}]:')
                for item in value:
                    lines.append(f'{prefix}  - {_serialize_value(item)}')
        else:
            lines.append(f'{prefix}{key}: {_serialize_value(value)}')

    return '\n'.join(lines)
