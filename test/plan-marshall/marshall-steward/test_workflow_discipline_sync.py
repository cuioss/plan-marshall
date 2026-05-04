#!/usr/bin/env python3
"""Drift self-test for the marshall-steward workflow_discipline FIX_CONTENT block.

This test guards the canonical "Workflow Discipline (Hard Rules)" section in
the repo-root ``CLAUDE.md`` against drift from the verbatim snapshot kept in
``determine_mode.FIX_CONTENT['workflow_discipline']``. The two MUST stay in
sync — when ``check_docs`` reports the section as ``missing`` (or
``incomplete``), the fix-docs flow appends FIX_CONTENT verbatim, so any
divergence between the canonical bullets and the snapshot would silently
re-introduce stale wording into a freshly bootstrapped project.

Strategy
--------
1. Locate the canonical CLAUDE.md via ``MARKETPLACE_ROOT`` from conftest so
   the test runs from any cwd (matches the convention used by other tests
   under ``test/plan-marshall/marshall-steward/``).
2. Parse the "Workflow Discipline (Hard Rules)" section out of CLAUDE.md
   and extract the leading rule-name token from every top-level bullet.
3. Direct-import ``determine_mode`` and parse the same tokens out of
   ``FIX_CONTENT['workflow_discipline']``.
4. Assert the two token sets are equal — emit a precise diff on mismatch.
5. Assert the bullet counts are equal — catches accidental rule-name reuse
   with different prose (which would pass the set-equality check but still
   represent drift).
"""

import importlib.util
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_script_path

# =============================================================================
# Path Resolution
# =============================================================================

# MARKETPLACE_ROOT is `<repo>/marketplace/bundles`; the canonical CLAUDE.md
# lives at the repo root, two levels up.
PROJECT_ROOT = MARKETPLACE_ROOT.parent.parent
CLAUDE_MD_PATH = PROJECT_ROOT / 'CLAUDE.md'

# Direct-import determine_mode so the test sees the live FIX_CONTENT dict
# without going through the script's argparse-based CLI surface.
_DETERMINE_MODE_PATH = Path(get_script_path('plan-marshall', 'marshall-steward', 'determine_mode.py'))
_spec = importlib.util.spec_from_file_location('determine_mode', _DETERMINE_MODE_PATH)
_determine_mode = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_determine_mode)

FIX_CONTENT = _determine_mode.FIX_CONTENT


# =============================================================================
# Bullet Extraction Helpers
# =============================================================================

# Canonical bullet shape (both in CLAUDE.md and in FIX_CONTENT):
#     - **Rule name** — body text...
# The em-dash (U+2014) is significant — using a hyphen would be drift.
# The rule-name token is the bold-marked phrase between the leading `- **`
# and the closing `**` before the em-dash.
_BULLET_RULE_NAME_RE = re.compile(r'^- \*\*(?P<name>[^*]+)\*\*\s+—')


def _extract_section_bullets(content: str, section_heading: str) -> list[str]:
    """Return raw bullet lines under ``section_heading`` from ``content``.

    Matches the same scanning convention used by
    ``determine_mode.count_section_bullets``: locate the heading line by
    substring, then collect every line that begins with ``- `` (top-level
    bullet, no leading whitespace) until the next Markdown heading.
    """
    lines = content.splitlines()
    in_section = False
    bullets: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if not in_section:
            if stripped.startswith('#') and section_heading in line:
                in_section = True
            continue
        # Stop at the next heading line.
        if stripped.startswith('#'):
            hashes = len(stripped) - len(stripped.lstrip('#'))
            if hashes >= 1 and stripped[hashes : hashes + 1] == ' ':
                break
        if line.startswith('- '):
            bullets.append(line)
    return bullets


def _rule_names(bullets: list[str]) -> list[str]:
    """Extract the bold rule-name token from each bullet line.

    Bullets that do not match the canonical ``- **name** —`` shape raise
    AssertionError so drift in the bullet *prefix* (e.g., a missing em-dash
    or unbolded name) fails the test loudly rather than silently dropping
    that bullet from the comparison.
    """
    names: list[str] = []
    for bullet in bullets:
        match = _BULLET_RULE_NAME_RE.match(bullet)
        assert match is not None, f"Bullet does not match canonical '- **name** —' shape: {bullet!r}"
        names.append(match.group('name'))
    return names


# =============================================================================
# Tests
# =============================================================================


def test_canonical_claude_md_section_present():
    """CLAUDE.md must contain the 'Workflow Discipline (Hard Rules)' section.

    Pre-flight: if this fails, the parsing in the other tests is meaningless
    so we surface it as its own failure.
    """
    assert CLAUDE_MD_PATH.is_file(), f'Canonical CLAUDE.md missing at {CLAUDE_MD_PATH}'
    content = CLAUDE_MD_PATH.read_text(encoding='utf-8')
    bullets = _extract_section_bullets(content, 'Workflow Discipline (Hard Rules)')
    assert bullets, (
        f'No bullets found under "Workflow Discipline (Hard Rules)" in {CLAUDE_MD_PATH}. '
        'Either the section was removed or the heading was renamed — both are drift.'
    )


def test_fix_content_workflow_discipline_section_present():
    """FIX_CONTENT must contain a 'Workflow Discipline (Hard Rules)' bullet block.

    Pre-flight mirror of test_canonical_claude_md_section_present.
    """
    snapshot = FIX_CONTENT['workflow_discipline']
    bullets = _extract_section_bullets(snapshot, 'Workflow Discipline (Hard Rules)')
    assert bullets, (
        "FIX_CONTENT['workflow_discipline'] does not contain the expected "
        '"Workflow Discipline (Hard Rules)" section with bullets — the snapshot '
        'has been emptied or the heading was renamed.'
    )


def test_rule_names_match_canonical():
    """Set of rule-name tokens must be identical on both sides.

    Drift in either direction (a rule added/removed/renamed in CLAUDE.md but
    not mirrored in FIX_CONTENT, or vice versa) fails this test with a
    precise diff so the maintainer can see which side moved.
    """
    canonical_content = CLAUDE_MD_PATH.read_text(encoding='utf-8')
    canonical_bullets = _extract_section_bullets(canonical_content, 'Workflow Discipline (Hard Rules)')
    canonical_names = _rule_names(canonical_bullets)

    fix_content = FIX_CONTENT['workflow_discipline']
    fix_bullets = _extract_section_bullets(fix_content, 'Workflow Discipline (Hard Rules)')
    fix_names = _rule_names(fix_bullets)

    canonical_set = set(canonical_names)
    fix_set = set(fix_names)

    only_in_canonical = sorted(canonical_set - fix_set)
    only_in_fix = sorted(fix_set - canonical_set)

    assert canonical_set == fix_set, (
        'workflow_discipline FIX_CONTENT has drifted from canonical CLAUDE.md.\n'
        f'  Rules in CLAUDE.md but missing from FIX_CONTENT: {only_in_canonical}\n'
        f'  Rules in FIX_CONTENT but missing from CLAUDE.md: {only_in_fix}\n'
        '  Sync the two sides — see CLAUDE.md "Workflow Discipline (Hard Rules)" '
        "and determine_mode.FIX_CONTENT['workflow_discipline']."
    )


def test_bullet_count_matches_canonical():
    """Bullet counts must match — catches rule-name reuse with different prose.

    The set-equality check in test_rule_names_match_canonical would still
    pass if the snapshot duplicated a rule name (e.g., two bullets both
    titled ``Bash: one command per call``) while CLAUDE.md kept distinct
    bullets. This count-equality check closes that gap.
    """
    canonical_content = CLAUDE_MD_PATH.read_text(encoding='utf-8')
    canonical_bullets = _extract_section_bullets(canonical_content, 'Workflow Discipline (Hard Rules)')

    fix_content = FIX_CONTENT['workflow_discipline']
    fix_bullets = _extract_section_bullets(fix_content, 'Workflow Discipline (Hard Rules)')

    assert len(canonical_bullets) == len(fix_bullets), (
        'Bullet count drift between canonical CLAUDE.md and FIX_CONTENT.\n'
        f'  CLAUDE.md bullet count: {len(canonical_bullets)}\n'
        f'  FIX_CONTENT bullet count: {len(fix_bullets)}\n'
        '  This usually means a bullet was added or removed on one side without '
        'mirroring on the other, or a bullet was duplicated.'
    )
