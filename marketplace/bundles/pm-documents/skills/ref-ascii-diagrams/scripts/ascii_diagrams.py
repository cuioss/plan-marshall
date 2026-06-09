#!/usr/bin/env python3
"""
ASCII box-diagram alignment validator.

Detects and repairs misaligned box-drawing diagrams inside code/literal blocks
of Markdown (``.md``) and AsciiDoc (``.adoc``) files. A box is a run of lines
beginning with a ``┌…┐`` top rule and ending with the matching ``└…┘`` bottom
rule at the same indent; interior lines are ``│…│`` content lines. Alignment
means the right border of every box line sits in the same column and the
top/bottom rules span the same inner width.

Usage:
    ascii_diagrams.py check [--path PATH]
    ascii_diagrams.py fix [--path PATH]
    ascii_diagrams.py --help

Subcommands:
    check   Detect misaligned boxes; report offending file + line numbers.
            Non-mutating (exit data only).
    fix     Re-pad interior lines and rebuild top/bottom borders to a
            consistent width. Mutating; idempotent.
"""

import argparse
from pathlib import Path

from file_ops import output_toon, safe_main  # type: ignore[import-not-found]

# Box-drawing characters used to recognise box runs.
TOP_LEFT = '┌'
TOP_RIGHT = '┐'
BOTTOM_LEFT = '└'
BOTTOM_RIGHT = '┘'
HORIZONTAL = '─'
VERTICAL = '│'

# Code-block fences and delimiters.
MD_FENCE = '```'
ADOC_LITERAL = '----'


def _leading_ws(line: str) -> str:
    """Return the leading-whitespace prefix of ``line``."""
    stripped = line.lstrip(' ')
    return line[: len(line) - len(stripped)]


def is_top_rule(line: str) -> bool:
    """True when ``line`` (ignoring indent) is a box top rule ``┌─…─┐``."""
    body = line.strip()
    return len(body) >= 2 and body[0] == TOP_LEFT and body[-1] == TOP_RIGHT


def is_bottom_rule(line: str) -> bool:
    """True when ``line`` (ignoring indent) is a box bottom rule ``└─…─┘``."""
    body = line.strip()
    return len(body) >= 2 and body[0] == BOTTOM_LEFT and body[-1] == BOTTOM_RIGHT


def is_box_line(line: str) -> bool:
    """True when ``line`` (ignoring indent) is a box interior line ``│…│``.

    An interior line both starts and ends with a vertical border so that
    flow-lines (a single ``│`` connector that is not ``│``-bounded on both
    sides) are not mistaken for box content.
    """
    body = line.strip()
    return len(body) >= 2 and body[0] == VERTICAL and body[-1] == VERTICAL


def _box_run_lines(lines: list[str], top_index: int) -> int | None:
    """Return the index of the matching bottom rule for the top rule at
    ``top_index``, or ``None`` when no matching bottom rule exists at the same
    indent.

    The matching bottom rule is the first ``└…┘`` line at the same indent as
    the top rule, with only ``│…│`` interior lines (at that indent) in between.
    A line at the same indent that is neither an interior line nor the bottom
    rule terminates the search (the run is not a well-formed box).
    """
    indent = _leading_ws(lines[top_index])
    for j in range(top_index + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            # Blank line breaks a box run.
            return None
        if _leading_ws(line) != indent:
            # Deeper / shallower indent is interior content of this box or a
            # nested box — treated as interior, never as the run boundary.
            continue
        if is_bottom_rule(line):
            return j
        if is_box_line(line):
            continue
        # Same-indent line that is neither interior nor bottom rule → not a box.
        return None
    return None


def _target_inner_width(lines: list[str], top_index: int, bottom_index: int) -> int:
    """Compute the target inner width for the box spanning ``top_index`` to
    ``bottom_index`` (inclusive).

    The inner width is the maximum over the box's own border lines of the
    character span between the left and right border characters. Only lines at
    the box's own indent that carry both borders contribute; deeper-indented
    (nested) content does not force the enclosing box wider than its own
    borders already require, but its rendered length is still respected because
    nested lines sit between this box's borders.
    """
    indent = _leading_ws(lines[top_index])
    indent_len = len(indent)
    width = 0
    for j in range(top_index, bottom_index + 1):
        body = lines[j][indent_len:].rstrip('\n')
        # Inner width = total body length minus the two border characters.
        inner = len(body) - 2
        if inner > width:
            width = inner
    return width


def _rebuild_rule(indent: str, left: str, right: str, inner_width: int) -> str:
    """Build a top/bottom rule line: indent + left + ─*inner_width + right."""
    return f'{indent}{left}{HORIZONTAL * inner_width}{right}'


def _rebuild_box_line(indent: str, body: str, inner_width: int) -> str:
    """Re-pad a single ``│…│`` interior line to ``inner_width``.

    ``body`` is the line with its indent already stripped. The interior text
    between the two vertical borders is right-padded (or left unchanged if it
    already meets the width) so the closing border lands in the target column.
    """
    interior = body[1:-1]
    if len(interior) < inner_width:
        interior = interior + ' ' * (inner_width - len(interior))
    return f'{indent}{VERTICAL}{interior}{VERTICAL}'


def rebuild_box(lines: list[str], top_index: int, bottom_index: int) -> list[str]:
    """Return the rebuilt lines for the box spanning ``top_index`` to
    ``bottom_index`` (inclusive), aligning every border to a consistent width.

    Interior lines that are NOT box lines at this box's own indent (nested
    boxes, deeper content) are returned verbatim — they are interior content,
    not separately re-ruled.
    """
    indent = _leading_ws(lines[top_index])
    inner_width = _target_inner_width(lines, top_index, bottom_index)
    rebuilt: list[str] = []
    for j in range(top_index, bottom_index + 1):
        line = lines[j]
        if j == top_index:
            rebuilt.append(_rebuild_rule(indent, TOP_LEFT, TOP_RIGHT, inner_width))
        elif j == bottom_index:
            rebuilt.append(_rebuild_rule(indent, BOTTOM_LEFT, BOTTOM_RIGHT, inner_width))
        elif _leading_ws(line) == indent and is_box_line(line):
            rebuilt.append(_rebuild_box_line(indent, line[len(indent):], inner_width))
        else:
            # Nested box / deeper interior content — verbatim.
            rebuilt.append(line)
    return rebuilt


def _normalize_block_region(lines: list[str], start: int, end: int) -> tuple[list[str], list[int]]:
    """Normalize all box runs in the line region ``lines[start:end]``.

    Returns ``(new_lines, changed_indices)`` where ``new_lines`` is the
    rebuilt slice of the region and ``changed_indices`` lists the 0-based
    indices (relative to the whole file) of lines whose content changed.
    """
    region = lines[start:end]
    out: list[str] = []
    changed: list[int] = []
    i = 0
    n = len(region)
    while i < n:
        if is_top_rule(region[i]):
            bottom = _box_run_lines(region, i)
            if bottom is not None:
                rebuilt = rebuild_box(region, i, bottom)
                for offset, new_line in enumerate(rebuilt):
                    if region[i + offset] != new_line:
                        changed.append(start + i + offset)
                    out.append(new_line)
                i = bottom + 1
                continue
        out.append(region[i])
        i += 1
    return out, changed


def _iter_block_regions(lines: list[str], suffix: str) -> list[tuple[int, int]]:
    """Yield ``(start, end)`` half-open line ranges for each code/literal block.

    For ``.md`` files the delimiter is a ``` ``` ``` fence. For ``.adoc`` files
    both ``` ``` ``` fenced blocks and ``----`` literal blocks are scanned. The
    returned ranges exclude the delimiter lines themselves.
    """
    regions: list[tuple[int, int]] = []
    in_block = False
    block_start = 0
    open_delim = ''
    delimiters = [MD_FENCE]
    if suffix == '.adoc':
        delimiters = [MD_FENCE, ADOC_LITERAL]
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not in_block:
            for delim in delimiters:
                if stripped == delim or (delim == MD_FENCE and stripped.startswith(MD_FENCE)):
                    in_block = True
                    open_delim = delim
                    block_start = idx + 1
                    break
        else:
            is_close = stripped == open_delim or (
                open_delim == MD_FENCE and stripped.startswith(MD_FENCE)
            )
            if is_close:
                regions.append((block_start, idx))
                in_block = False
                open_delim = ''
    return regions


def _process_file(path: Path) -> tuple[list[str], list[int]]:
    """Process a single file: return ``(new_lines, changed_indices)``.

    Scans every code/literal block in the file and normalizes the box runs
    within. Lines outside any block — and non-box content inside a block — are
    preserved verbatim.
    """
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    suffix = path.suffix.lower()
    result = list(lines)
    changed: list[int] = []
    for start, end in _iter_block_regions(lines, suffix):
        new_region, region_changed = _normalize_block_region(result, start, end)
        result[start:end] = new_region
        changed.extend(region_changed)
    return result, sorted(set(changed))


def _collect_files(target: Path) -> list[Path]:
    """Collect candidate ``.md`` / ``.adoc`` files under ``target``.

    When ``target`` is a file it is returned as-is (if it has a supported
    suffix); when a directory, it is walked recursively.
    """
    suffixes = {'.md', '.adoc'}
    if target.is_file():
        return [target] if target.suffix.lower() in suffixes else []
    return sorted(p for p in target.rglob('*') if p.is_file() and p.suffix.lower() in suffixes)


def cmd_check(args: argparse.Namespace) -> None:
    """``check`` subcommand: report misaligned boxes without mutating files."""
    target = Path(args.path)
    files = _collect_files(target)
    findings: list[dict[str, object]] = []
    checked = 0
    for f in files:
        checked += 1
        try:
            _new_lines, changed = _process_file(f)
        except (OSError, UnicodeDecodeError):
            continue
        for line_index in changed:
            findings.append(
                {
                    'file': str(f),
                    'line': line_index + 1,
                    'message': 'misaligned box border',
                }
            )
    output_toon(
        {
            'status': 'success',
            'operation': 'check',
            'files_checked': checked,
            'misaligned_count': len(findings),
            'findings': findings,
        }
    )


def cmd_fix(args: argparse.Namespace) -> None:
    """``fix`` subcommand: re-pad and rebuild box borders; write changed files."""
    target = Path(args.path)
    files = _collect_files(target)
    fixed_files: list[str] = []
    checked = 0
    total_lines_changed = 0
    for f in files:
        checked += 1
        try:
            new_lines, changed = _process_file(f)
        except (OSError, UnicodeDecodeError):
            continue
        if changed:
            f.write_text('\n'.join(new_lines), encoding='utf-8')
            fixed_files.append(str(f))
            total_lines_changed += len(changed)
    output_toon(
        {
            'status': 'success',
            'operation': 'fix',
            'files_checked': checked,
            'files_fixed': len(fixed_files),
            'lines_changed': total_lines_changed,
            'fixed_files': fixed_files,
        }
    )


@safe_main
def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='ASCII box-diagram alignment validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser(
        'check', help='Detect misaligned boxes (non-mutating)', allow_abbrev=False
    )
    check_parser.add_argument('--path', default='.', help='File or directory to check')
    check_parser.set_defaults(func=cmd_check)

    fix_parser = subparsers.add_parser(
        'fix', help='Repair misaligned boxes (mutating, idempotent)', allow_abbrev=False
    )
    fix_parser.add_argument('--path', default='.', help='File or directory to fix')
    fix_parser.set_defaults(func=cmd_fix)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    main()
