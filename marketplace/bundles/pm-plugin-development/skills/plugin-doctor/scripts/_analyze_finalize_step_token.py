#!/usr/bin/env python3
"""Finalize-step token scanner for the ``finalize-step-token-mismatch`` rule.

This module implements a deterministic regex-based static analyzer that
detects mismatches between the ``mark-step-done --step <token>`` argument a
finalize-step skill documents (under ``--phase 6-finalize``) and the skill's
fully-qualified manifest step_id. The documented token is the key the
dispatched finalize step records its terminal outcome under; the manifest
declares the SAME step under its canonical step_id. When the documented token
drifts away from the manifest step_id, the recording side keys ``phase_steps``
under the wrong name, the ``phase_steps_complete`` handshake reports the
canonical step missing, and the halt-and-retry recovery loop runs forever.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_historical_prose_in_skills.py`` and
``_analyze_lesson_id_in_skill_prose.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from markdown source
- stdlib-only dependencies
- no mutation of any file

Scan roots
----------
Two roots are walked:

1. **Bundle finalize-step skills** —
   ``marketplace_root/{bundle}/skills/{skill}/SKILL.md`` whose
   ``{bundle}:{skill}`` reference is a member of the authoritative
   ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` registry in
   ``manage-config/_config_defaults.py`` (the same single-source-of-truth the
   PR #629 regression anchors to). The expected step_id is that registry
   reference, i.e. ``{bundle}:{skill}``.

2. **Project-local finalize-step skills** —
   ``<repo>/.claude/skills/finalize-step-*/SKILL.md`` discovered by glob
   (resolved relative to ``marketplace_root`` exactly as the lesson-id and
   historical-prose analyzers reach the ``.claude/skills/**`` tree). The
   expected step_id is ``project:{name}`` where ``{name}`` is the skill
   directory basename.

Detection
---------
For each in-scope SKILL.md, the documented ``--step <token>`` is parsed from
the ``mark-step-done`` invocation under ``--phase 6-finalize``, reusing PR
#629's parsing contract verbatim: extract each ``mark-step-done`` command
block, require ``--phase(?:\\s+|=)6-finalize\\b``, then ``--step(?:\\s+|=)(\\S+)``
— order-independent, both ``--flag value`` (space) and ``--flag=value``
(equals) forms. Skills emitting no ``mark-step-done --phase 6-finalize``
invocation are silently skipped (no false positive). A finding is emitted when
the parsed token differs from the expected step_id.

Findings have the shape::

    {
        'rule_id': 'finalize-step-token-mismatch',
        'type': 'finalize_step_token_mismatch',
        'rule': 'scan_finalize_step_token',
        'file': '<absolute SKILL.md path>',
        'line': <int, 1-based line of the --step token>,
        'severity': 'error',
        'fixable': False,
        'message': '<human-readable mismatch description>',
        'details': {
            'documented_token': '<parsed token>',
            'expected_step_id': '<canonical step_id>',
        },
    }

Public API
----------
- ``scan_finalize_step_token(marketplace_root)``: entry point — scans the two
  roots above and returns a list of finding dicts (empty for a clean tree).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RULE_ID = 'finalize-step-token-mismatch'
RULE_NAME = 'scan_finalize_step_token'
FINDING_TYPE = 'finalize_step_token_mismatch'

# ---------------------------------------------------------------------------
# Parsing contract (verbatim from PR #629's regression helper)
# ---------------------------------------------------------------------------

# mark-step-done command block: from the literal ``mark-step-done`` up to the
# next blank line, closing code fence, or end of string.
_BLOCK_RE = re.compile(r'mark-step-done\b[\s\S]*?(?=\n\s*\n|```|$)')
# The block must carry a --phase 6-finalize argument (space or equals form).
_PHASE_RE = re.compile(r'--phase(?:\s+|=)6-finalize\b')
# The --step token (space or equals form); group 1 is the token.
_STEP_RE = re.compile(r'--step(?:\s+|=)(\S+)')


# ---------------------------------------------------------------------------
# Registry import (single source of truth for bundle finalize-step ids)
# ---------------------------------------------------------------------------


def _load_optional_bundle_finalize_steps(marketplace_root: Path) -> list[str]:
    """Import ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` from ``manage-config``.

    ``_config_defaults`` imports its sibling ``constants`` module by bare name,
    so the manage-config scripts directory must be on ``sys.path`` before the
    import resolves. Returns an empty list when the registry cannot be located
    (e.g. a synthetic ``tmp_path`` marketplace with no plan-marshall bundle).
    """
    scripts_dir = (
        marketplace_root
        / 'plan-marshall'
        / 'skills'
        / 'manage-config'
        / 'scripts'
    )
    if not scripts_dir.is_dir():
        return []
    inserted = False
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
        inserted = True
    try:
        import _config_defaults  # noqa: PLC0415

        return list(_config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEPS)
    except Exception:
        return []
    finally:
        if inserted:
            try:
                sys.path.remove(str(scripts_dir))
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Token parsing
# ---------------------------------------------------------------------------


def _documented_step_token(content: str) -> tuple[str, int] | None:
    """Parse the documented ``--step {token}`` and its 1-based line number.

    Returns ``(token, line_number)`` for the first ``mark-step-done`` block
    carrying both ``--phase 6-finalize`` and ``--step <token>`` (order
    independent, both space and equals forms). Returns ``None`` when no such
    invocation exists — the skill is then silently skipped by the caller.
    """
    for block_match in _BLOCK_RE.finditer(content):
        block = block_match.group(0)
        if not _PHASE_RE.search(block):
            continue
        step_match = _STEP_RE.search(block)
        if not step_match:
            continue
        # Compute the 1-based line of the --step token within the file.
        token_abs_offset = block_match.start() + step_match.start(1)
        line_number = content.count('\n', 0, token_abs_offset) + 1
        return step_match.group(1), line_number
    return None


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_skill(path: Path, expected_step_id: str) -> list[dict]:
    """Scan one SKILL.md and emit a finding when the documented token drifts."""
    try:
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    parsed = _documented_step_token(content)
    if parsed is None:
        # No mark-step-done --phase 6-finalize invocation — silently skip.
        return []

    documented_token, line_number = parsed
    if documented_token == expected_step_id:
        return []

    return [
        {
            'rule_id': RULE_ID,
            'type': FINDING_TYPE,
            'rule': RULE_NAME,
            'file': str(path),
            'line': line_number,
            'severity': 'error',
            'fixable': False,
            'message': (
                f'Documented mark-step-done --step token '
                f'`{documented_token}` does not match the manifest step_id '
                f'`{expected_step_id}`. The recorded phase_steps key drifts '
                f'and the phase_steps_complete handshake reports the step '
                f'missing. See rule-catalog.md.'
            ),
            'details': {
                'documented_token': documented_token,
                'expected_step_id': expected_step_id,
            },
        }
    ]


# ---------------------------------------------------------------------------
# Target enumeration
# ---------------------------------------------------------------------------


def _bundle_targets(
    marketplace_root: Path, optional_steps: list[str]
) -> list[tuple[Path, str]]:
    """Return ``(SKILL.md path, expected_step_id)`` for in-scope bundle skills.

    A bundle skill is in scope when its ``{bundle}:{skill}`` reference is a
    member of ``OPTIONAL_BUNDLE_FINALIZE_STEPS``. The expected step_id is that
    registry reference — the registry is the single source of truth, so the
    reference and the expected step_id are the same value.
    """
    if not optional_steps or not marketplace_root.is_dir():
        return []
    results: list[tuple[Path, str]] = []
    for step_ref in optional_steps:
        if ':' not in step_ref:
            continue
        bundle, skill = step_ref.split(':', 1)
        skill_md = marketplace_root / bundle / 'skills' / skill / 'SKILL.md'
        if not skill_md.is_file():
            continue
        results.append((skill_md, step_ref))
    return results


def _claude_skills_root(marketplace_root: Path) -> Path:
    """Resolve the project-local ``.claude/skills`` tree from ``marketplace_root``.

    ``marketplace_root`` is ``<repo>/marketplace/bundles``; the project-local
    skills tree is ``<repo>/.claude/skills`` — two levels up, then
    ``.claude/skills``.
    """
    return marketplace_root.parent.parent / '.claude' / 'skills'


def _project_local_targets(marketplace_root: Path) -> list[tuple[Path, str]]:
    """Return ``(SKILL.md path, expected_step_id)`` for project-local steps.

    Scope: ``<repo>/.claude/skills/finalize-step-*/SKILL.md``. The expected
    step_id is ``project:{name}`` where ``{name}`` is the skill directory
    basename.
    """
    skills_root = _claude_skills_root(marketplace_root)
    if not skills_root.is_dir():
        return []
    results: list[tuple[Path, str]] = []
    for skill_dir in sorted(skills_root.glob('finalize-step-*')):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        expected = f'project:{skill_dir.name}'
        results.append((skill_md, expected))
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan_finalize_step_token(marketplace_root: Path) -> list[dict]:
    """Scan finalize-step skills for documented-token vs manifest step_id drift.

    Walks two roots and reports every documented ``mark-step-done --step``
    token that diverges from the skill's canonical manifest step_id:

    - ``marketplace_root/{bundle}/skills/{skill}/SKILL.md`` for each
      ``{bundle}:{skill}`` in ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` (expected
      step_id = ``{bundle}:{skill}``).
    - ``<repo>/.claude/skills/finalize-step-*/SKILL.md`` (expected step_id =
      ``project:{name}``).

    Skills with no ``mark-step-done --phase 6-finalize`` invocation are
    silently skipped.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    marketplace_root = Path(marketplace_root)
    optional_steps = _load_optional_bundle_finalize_steps(marketplace_root)

    findings: list[dict] = []
    for skill_md, expected in _bundle_targets(marketplace_root, optional_steps):
        findings.extend(_scan_skill(skill_md, expected))
    for skill_md, expected in _project_local_targets(marketplace_root):
        findings.extend(_scan_skill(skill_md, expected))
    return findings
