#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Lane-frontmatter validation analyzer (build-failing under ``quality-gate``).

Every lane-participating workflow element (phase skill, phase-6 finalize step,
q-gate / adversarial validator) self-declares its lane membership through a
``lane:`` frontmatter block consumed by the ``manage-execution-manifest`` lane
resolver. This analyzer asserts that **every** ``lane:`` block in the marketplace
tree is well-formed: a valid closed-enum ``class``, a valid ``cost_size`` from the
six-size scale, a ``prunable_when`` present iff ``class: prunable``, and a valid
``tier`` (when present). A malformed block would make the composer mis-resolve or
silently mis-prune the element.

The closed enums, the class→default-tier table, and the predicate vocabulary are
owned by ``plan-marshall:extension-api/standards/ext-point-lane-element.md`` — this
analyzer is the structural backstop that reads those enums and flags drift. It
does NOT enforce that a given element MUST declare a ``lane:`` block; it validates
every block that exists.

A recipe lane SEED block (a ``profile:`` posture plus optional ``steps:``
per-element overrides, declared on a ``recipe-*`` SKILL.md and consumed by the
recipe-scoring reader) is a DIFFERENT contract that happens to share the ``lane:``
key. It is identified by its ``profile`` sub-key and is skipped here — recipe
seeds are validated by ``script-shared:recipe_scoring``, not the element-lane rule.

Pattern alignment
-----------------
Mirrors ``_analyze_role_field.py`` and ``_analyze_metadata_field_validity.py``:
each analyzer builds uniform :class:`Finding` objects (from ``_doctor_shared``)
and serialises them via :meth:`Finding.to_dict`, and exposes a module-level
``RULE_DESCRIPTOR`` (from ``_rule_registry``) collected by the central registry.

- ``analyze_lane_frontmatter(marketplace_root)``: entry point — scans every
  ``.md`` file under the bundles root, validates each ``lane:`` block, and returns
  a list of finding dicts (one per defect). Returns an empty list when the tree is
  absent. Findings are declarative and suppressible through the standard
  per-rule / frontmatter disable surface applied by the caller.
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]
from _rule_registry import RuleDescriptor

RULE_ID = 'lane-frontmatter-invalid'
RULE_NAME = 'analyze_lane_frontmatter'
FINDING_TYPE = 'lane_frontmatter_invalid'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='file-local',
)

# Closed enums — the single source of truth is
# extension-api/standards/ext-point-lane-element.md. Mirrored here as the
# structural validation set (a closed enum, so drift is a contract change).
_VALID_CLASSES = ('derived-state', 'core', 'adversarial', 'prunable')
_VALID_TIERS = ('minimal', 'auto', 'full')
_VALID_COST_SIZES = ('XS', 'S', 'M', 'L', 'XL', 'XXL')


def _parse_lane_block(text: str) -> tuple[dict[str, str], int] | None:
    """Parse the nested ``lane:`` frontmatter block from a markdown file's text.

    Returns ``(lane_subkeys, lane_line_number)`` when the leading ``---``-fenced
    frontmatter declares a top-level ``lane:`` key, else ``None``. The block's
    2-space-indented scalar sub-keys are collected until the block dedents. The
    line number (1-based) points at the ``lane:`` line for the finding location.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    lane: dict[str, str] = {}
    lane_line = 0
    in_frontmatter = False
    in_lane = False
    for index, line in enumerate(lines):
        if index == 0:
            if line.strip() != '---':
                return None
            in_frontmatter = True
            continue
        if not in_frontmatter:
            break
        if line.strip() == '---':
            break
        if not in_lane:
            if line.rstrip() == 'lane:':
                in_lane = True
                lane_line = index + 1
            continue
        if line.startswith('  ') and ':' in line:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            key, _, value = stripped.partition(':')
            lane[key.strip()] = value.strip().strip('"').strip("'")
        else:
            # A dedented (column-0) line ends the lane block.
            break
    if lane_line == 0:
        return None
    return lane, lane_line


def _validate_lane_block(lane: dict[str, str]) -> list[str]:
    """Return a list of human-readable defect messages for a ``lane:`` block.

    An empty list means the block is well-formed.
    """
    defects: list[str] = []

    cls = lane.get('class')
    if cls is None:
        defects.append('missing required `class`')
    elif cls not in _VALID_CLASSES:
        defects.append(f'invalid `class` {cls!r} (expected one of {list(_VALID_CLASSES)})')

    cost_size = lane.get('cost_size')
    if cost_size is None:
        defects.append('missing required `cost_size`')
    elif cost_size not in _VALID_COST_SIZES:
        defects.append(f'invalid `cost_size` {cost_size!r} (expected one of {list(_VALID_COST_SIZES)})')

    tier = lane.get('tier')
    if tier is not None and tier not in _VALID_TIERS:
        defects.append(f'invalid `tier` {tier!r} (expected one of {list(_VALID_TIERS)})')

    prunable_when = lane.get('prunable_when')
    if cls == 'prunable' and not prunable_when:
        defects.append('`class: prunable` requires a `prunable_when` predicate id')
    elif cls is not None and cls != 'prunable' and prunable_when:
        defects.append('`prunable_when` is only allowed when `class: prunable`')

    return defects


def analyze_lane_frontmatter(marketplace_root: Path) -> list[dict]:
    """Validate every ``lane:`` frontmatter block under ``marketplace_root``.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). Walks every ``.md`` file,
    validates each declared ``lane:`` block, and returns a finding per defect.
    Returns an empty list when the tree is absent; unreadable files are skipped
    silently (an unreadable file is not this analyzer's failure mode).
    """
    if not marketplace_root.is_dir():
        return []

    findings: list[Finding] = []
    for md_path in sorted(marketplace_root.rglob('*.md')):
        try:
            text = md_path.read_text(encoding='utf-8')
        except OSError:
            continue
        parsed = _parse_lane_block(text)
        if parsed is None:
            continue
        lane, lane_line = parsed
        # A recipe lane SEED block (``profile:`` posture + optional ``steps:``
        # overrides) is a DIFFERENT contract from a per-element lane block
        # (``class`` / ``cost_size``) — both share the ``lane:`` key. Recipe seeds
        # are validated by the recipe-scoring reader, not this element-lane rule,
        # so skip any block that declares ``profile`` (the recipe-seed marker).
        if 'profile' in lane:
            continue
        for defect in _validate_lane_block(lane):
            findings.append(
                Finding(
                    type=FINDING_TYPE,
                    file=str(md_path),
                    line=lane_line,
                    severity='error',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        f'malformed `lane:` block — {defect}. See '
                        'plan-marshall:extension-api/standards/ext-point-lane-element.md '
                        'for the closed `lane.class` / `cost_size` enums and the '
                        '`prunable_when` requirement.'
                    ),
                    extra={'rule': RULE_NAME, 'snippet': md_path.stem},
                )
            )
    return [f.to_dict() for f in findings]
