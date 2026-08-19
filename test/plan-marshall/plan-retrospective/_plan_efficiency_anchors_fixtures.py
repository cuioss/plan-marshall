#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``plan efficiency anchors`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

# ---------------------------------------------------------------------------
# Source anchors — every one of these is a LIVE source, never a copied value
# ---------------------------------------------------------------------------

#: The document under guard: its § 2 table is the anchors key space.
_ANCHORS_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'references'
    / 'plan-efficiency.md'
)


#: Authoritative source of the canonical change_type vocabulary.
_CHANGE_TYPES_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'ref-workflow-architecture'
    / 'standards'
    / 'change-types.md'
)


#: The audit skill's deterministic computation core (no executor notation — it
#: runs via a direct ``python3 .../audit.py``, so it is loaded by file location).
_AUDIT_SCRIPT = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'audit-archived-plan-retrospectives'
    / 'scripts'
    / 'audit.py'
)


#: Heading prefixes the section slicer anchors on.
_ANCHORS_SECTION_HEADING = '### 2. Calibration anchors table'


_CANONICAL_CHANGE_TYPE_HEADING = '## Change-Type Definitions'


#: The two key columns of the § 2 anchors table, in order.
_ANCHOR_KEY_COLUMNS = ('scope_estimate', 'change_type')


#: A pair guaranteed to be outside the live cross-product — both halves are
#: retired keys the § 2 "Remapped calibration data" note names. Used only to
#: mutate a COPY of the document in the discrimination test; its
#: outside-ness is asserted there rather than assumed.
_RETIRED_PAIR = ('cross_cutting', 'refactor')


# ---------------------------------------------------------------------------
# Markdown table parsing (shared by both axes and by the mutation tests)
# ---------------------------------------------------------------------------

_SEPARATOR_CELL_RE = re.compile(r'^:?-{2,}:?$')


def _heading_level(line: str) -> int:
    """Return the ATX heading level of ``line`` (0 when it is not a heading)."""
    stripped = line.lstrip()
    if not stripped.startswith('#'):
        return 0
    return len(stripped) - len(stripped.lstrip('#'))


def _table_cells(line: str) -> list[str]:
    """Split one markdown table row into trimmed cells (``[]`` when not a row)."""
    stripped = line.strip()
    if not (stripped.startswith('|') and stripped.endswith('|') and len(stripped) > 1):
        return []
    return [cell.strip() for cell in stripped[1:-1].split('|')]


def _is_separator_row(cells: list[str]) -> bool:
    """True for a ``|---|---|`` alignment row."""
    return bool(cells) and all(_SEPARATOR_CELL_RE.match(cell) for cell in cells)


def _section_block(content: str, heading_prefix: str) -> str:
    """Return the body under ``heading_prefix``, up to the next same-or-higher heading.

    Slicing to the owning section is what keeps the parser from picking up an
    unrelated table elsewhere in the document.
    """
    lines = content.splitlines()
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = index + 1
            level = _heading_level(line)
            break
    if start is None:
        raise AssertionError(
            f'Section heading starting with {heading_prefix!r} not found. The '
            f'anchors guard slices the document by heading; a rename must be '
            f'reflected here.'
        )
    end = len(lines)
    for index in range(start, len(lines)):
        found = _heading_level(lines[index])
        if found and found <= level:
            end = index
            break
    return '\n'.join(lines[start:end])


def _parse_keyed_table(block: str, key_columns: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Return one key tuple per data row of the table headed by ``key_columns``.

    Cells are stripped of markdown code ticks so a backticked header/key
    (``| `analysis` |``) compares equal to its bare form. Rows are returned as a
    LIST (not a set) so duplicate keys stay observable.
    """
    rows: list[tuple[str, ...]] = []
    in_table = False
    width = len(key_columns)
    for line in block.splitlines():
        cells = _table_cells(line)
        if not cells:
            in_table = False
            continue
        if _is_separator_row(cells):
            continue
        key = tuple(cell.strip('`') for cell in cells[:width])
        if not in_table:
            if key == key_columns:
                in_table = True
            continue
        rows.append(key)
    return rows


def _anchor_keys(content: str) -> list[tuple[str, str]]:
    """Parse the § 2 anchors table into its ``(scope_estimate, change_type)`` keys."""
    block = _section_block(content, _ANCHORS_SECTION_HEADING)
    rows = _parse_keyed_table(block, _ANCHOR_KEY_COLUMNS)
    if not rows:
        raise AssertionError(
            f'No anchors table rows parsed from {_ANCHORS_DOC}. The § 2 table must '
            f'be headed by | {" | ".join(_ANCHOR_KEY_COLUMNS)} | ... |.'
        )
    return [(row[0], row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Live axes — re-derived from their owning sources, never hand-copied
# ---------------------------------------------------------------------------


def _live_scope_estimates() -> set[str]:
    """The live ``scope_estimate`` enum, imported from its owning script."""
    outline = load_script_module(
        'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py'
    )
    return set(outline.SCOPE_ESTIMATE_VALUES)


def _canonical_change_types() -> set[str]:
    """The canonical change_type vocabulary, parsed from change-types.md."""
    block = _section_block(
        _CHANGE_TYPES_DOC.read_text(encoding='utf-8'), _CANONICAL_CHANGE_TYPE_HEADING
    )
    keys = {row[0] for row in _parse_keyed_table(block, ('Key',))}
    if not keys:
        raise AssertionError(
            f'No canonical change types parsed from {_CHANGE_TYPES_DOC}; the '
            f'Change-Type Definitions table shape changed.'
        )
    return keys


def _router_change_types() -> set[str]:
    """The change_type values the live planning-lane router actually scores."""
    lane = load_script_module('plan-marshall', 'manage-status', '_cmd_planning_lane.py')
    return set(lane._DEEP_CHANGE_TYPES)


def _live_change_types() -> set[str]:
    """The live change_type axis: canonical vocabulary ∪ router-scored values."""
    return _canonical_change_types() | _router_change_types()


def _expected_cross_product() -> set[tuple[str, str]]:
    """The exact ``(scope_estimate, change_type)`` key space the table must carry."""
    return {
        (scope, change_type)
        for scope in _live_scope_estimates()
        for change_type in _live_change_types()
    }


def _key_diff(
    parsed: list[tuple[str, str]], expected: set[tuple[str, str]]
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Return ``(extra, missing)`` — dead/non-canonical keys and unanchored pairs."""
    parsed_set = set(parsed)
    return parsed_set - expected, expected - parsed_set


# ---------------------------------------------------------------------------
# Document mutation helpers (used only against in-memory copies)
# ---------------------------------------------------------------------------


def _remove_anchor_row(content: str, key: tuple[str, str]) -> str:
    """Return ``content`` with the § 2 row for ``key`` deleted."""
    scope, change_type = key
    row_re = re.compile(rf'^\|\s*{re.escape(scope)}\s*\|\s*{re.escape(change_type)}\s*\|')
    kept = [line for line in content.splitlines() if not row_re.match(line)]
    if len(kept) == len(content.splitlines()):
        raise AssertionError(f'Mutation helper found no row to remove for {key}.')
    return '\n'.join(kept)


def _insert_anchor_row(content: str, key: tuple[str, str]) -> str:
    """Return ``content`` with a row for ``key`` inserted into the § 2 table."""
    lines = content.splitlines()
    for index, line in enumerate(lines):
        cells = _table_cells(line)
        if tuple(cells[: len(_ANCHOR_KEY_COLUMNS)]) == _ANCHOR_KEY_COLUMNS:
            row = f'| {key[0]} | {key[1]} | fallback | — | — | Section 1 ratios |'
            # +2 skips the header row and its alignment separator.
            lines.insert(index + 2, row)
            return '\n'.join(lines)
    raise AssertionError('Mutation helper found no anchors-table header row.')


# ---------------------------------------------------------------------------
# audit.py loading + metrics fixtures
# ---------------------------------------------------------------------------


#: sys.modules key the audit core is registered under while it executes.
_AUDIT_MODULE_NAME = 'audit_anchors_under_test'


def _load_audit() -> Any:
    """Load the audit computation core by file location (it has no notation).

    The module MUST be registered in ``sys.modules`` BEFORE ``exec_module``:
    ``audit.py`` defines ``@dataclass`` types at import time, and
    ``dataclasses._is_type`` resolves ``sys.modules.get(cls.__module__)`` while
    processing each class. Executing an unregistered module makes that lookup
    return ``None`` and the import dies with ``AttributeError: 'NoneType' object
    has no attribute '__dict__'`` — the same registration ``conftest``'s
    ``load_script_module`` performs for exactly this reason.
    """
    cached = sys.modules.get(_AUDIT_MODULE_NAME)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(_AUDIT_MODULE_NAME, _AUDIT_SCRIPT)
    assert spec is not None, f'Failed to load module spec for {_AUDIT_SCRIPT}'
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[_AUDIT_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(_AUDIT_MODULE_NAME, None)
        raise
    return module


def _write_metrics(plan_dir: Path, body: str) -> Path:
    """Write ``work/metrics.toon`` under ``plan_dir`` and return the plan dir."""
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'metrics.toon').write_text(body, encoding='utf-8')
    return plan_dir
