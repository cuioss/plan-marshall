#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build-verify-step canonicals-contract analyzer (build-failing under ``quality-gate``).

A build-verify-step doc declares its membership through an ``implements:``
frontmatter marker naming ``plan-marshall:extension-api/standards/ext-point-build-verify-step``
and enumerates the canonical commands it backs through a ``canonicals:`` list.
The discovery query (``extension_discovery.find_implementors``) expands each
entry ``C`` into a ``default:verify:{C}`` step ID, in list order — so the
``canonicals:`` list IS the built-in build-verify-step set. A verify-step
implementor whose ``canonicals:`` list is MISSING or EMPTY declares no runnable
canonical: the discovery query surfaces the doc but seeds nothing, so the step
silently contributes zero verification coverage.

This analyzer is the static backstop for lesson ``2026-06-25-08-001``: every
``ext-point-build-verify-step`` implementor MUST carry a non-empty ``canonicals:``
list. It flags an implementor doc whose ``canonicals:`` key is absent, or present
but resolving to zero non-empty entries.

Pattern alignment
-----------------
Mirrors ``_analyze_lane_frontmatter.py``: pure static frontmatter parsing,
stdlib-only, no target-script imports, no file mutation. Builds uniform
:class:`Finding` objects and exposes a module-level ``RULE_DESCRIPTOR`` collected
by the central registry. The ``implements:`` / ``canonicals:`` contract is owned
by ``plan-marshall:extension-api/standards/ext-point-build-verify-step.md``; this
analyzer reads that contract and flags drift.

Public API
----------
- ``analyze_verify_step_contract(marketplace_root)``: entry point — scans every
  ``.md`` file under the bundles root, keeps the build-verify-step implementors,
  and returns a finding per implementor with a missing/empty ``canonicals:`` list
  (empty list for a compliant tree).
"""

from __future__ import annotations

from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'verify-step-canonicals-required'
RULE_NAME = 'analyze_verify_step_contract'
FINDING_TYPE = 'verify_step_canonicals_missing'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='file-local',
)

# The canonical ``implements:`` value identifying a build-verify-step doc. The
# contract lives in the central standard —
# plan-marshall:extension-api/standards/ext-point-build-verify-step.md.
_BUILD_VERIFY_STEP_EXT_POINT = 'ext-point-build-verify-step'


def _frontmatter_lines(text: str) -> list[str] | None:
    """Return the frontmatter body lines (between the leading ``---`` fences).

    Returns ``None`` when the file has no leading ``---``-fenced frontmatter
    block. The returned list excludes both fence lines.
    """
    if not text.startswith('---'):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == '---':
            return body
        body.append(line)
    # No closing fence — malformed frontmatter; treat as absent.
    return None


def _read_key_values(fm_lines: list[str], key: str) -> tuple[bool, list[str]]:
    """Read a frontmatter ``key`` as a scalar / inline-list / block-sequence.

    Returns ``(present, values)``:

    - ``present`` — whether the top-level ``key:`` appears in the frontmatter.
    - ``values`` — the non-empty string values: a scalar yields a one-item list;
      an inline ``[a, b]`` list yields its items; a block sequence yields its
      ``  - item`` entries. An empty scalar / empty ``[]`` / empty block yields
      ``[]``.

    Only top-level (column-0) keys are matched, so a nested sub-key of the same
    name never registers.
    """
    prefix = f'{key}:'
    for index, line in enumerate(fm_lines):
        # Top-level key: no leading indentation, comment-tolerant.
        if line.startswith((' ', '\t')) or not line.startswith(prefix):
            continue
        remainder = line[len(prefix) :].strip()
        if remainder and remainder != '[]':
            # Scalar or inline list.
            if remainder.startswith('[') and remainder.endswith(']'):
                inner = remainder[1:-1]
                items = [v.strip().strip('"').strip("'") for v in inner.split(',')]
                return True, [v for v in items if v]
            return True, [remainder.strip('"').strip("'")]
        if remainder == '[]':
            return True, []
        # Block sequence: collect the following ``  - item`` lines.
        values: list[str] = []
        for follow in fm_lines[index + 1 :]:
            stripped = follow.strip()
            if stripped.startswith('#') or not stripped:
                if not follow.startswith((' ', '\t')) and stripped:
                    break
                continue
            if follow.startswith((' ', '\t')) and stripped.startswith('- '):
                item = stripped[2:].strip().strip('"').strip("'")
                if item:
                    values.append(item)
                continue
            # A dedented / non-list line ends the block.
            break
        return True, values
    return False, []


def _implements_build_verify_step(fm_lines: list[str]) -> bool:
    """Return True when the frontmatter ``implements:`` names the build-verify ext-point."""
    present, values = _read_key_values(fm_lines, 'implements')
    if not present:
        return False
    return any(_BUILD_VERIFY_STEP_EXT_POINT in value for value in values)


def analyze_verify_step_contract(marketplace_root: Path) -> list[dict]:
    """Flag every build-verify-step implementor with a missing/empty ``canonicals:`` list.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). Walks every ``.md`` file,
    keeps those whose ``implements:`` frontmatter names the build-verify-step
    ext-point, and returns a finding for each whose ``canonicals:`` list is absent
    or empty. Returns an empty list when the tree is absent; unreadable files are
    skipped silently.
    """
    marketplace_root = Path(marketplace_root)
    if not marketplace_root.is_dir():
        return []

    findings: list[Finding] = []
    for md_path in sorted(marketplace_root.rglob('*.md')):
        try:
            text = md_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        fm_lines = _frontmatter_lines(text)
        if fm_lines is None or not _implements_build_verify_step(fm_lines):
            continue
        present, canonicals = _read_key_values(fm_lines, 'canonicals')
        if canonicals:
            continue
        defect = (
            'missing required `canonicals:` list'
            if not present
            else 'empty `canonicals:` list'
        )
        findings.append(
            Finding(
                type=FINDING_TYPE,
                file=str(md_path),
                line=1,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    f'build-verify-step implementor has a {defect} — every '
                    '`implements: ...ext-point-build-verify-step` doc MUST declare a '
                    'non-empty `canonicals:` list, else the discovery query seeds no '
                    'runnable `default:verify:{canonical}` step and the doc contributes '
                    'zero verification coverage (lesson 2026-06-25-08-001). See '
                    'plan-marshall:extension-api/standards/ext-point-build-verify-step.md.'
                ),
                extra={'rule': RULE_NAME, 'snippet': md_path.stem},
            )
        )
    return [f.to_dict() for f in findings]
