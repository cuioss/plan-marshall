# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Meta-tests for the provenance contract.

These tests pin the documentation-level invariants of the provenance
contract (separate from the table-level invariants exercised by
``test_rule_provenance_table.py``):

1. ``rule-catalog.md`` must declare the contract under a clearly-named
   "Provenance Contract for New Rules" section.

2. ``rule-catalog.md`` must enumerate every required artifact:
   emitter, provenance row, catalog row, test, fix-handler triple,
   `_doctor_shared.py::FIXABLE_ISSUE_TYPES`.

3. ``plugin-architecture/references/skill-design.md`` must reference
   the provenance contract so authors of new skills know the
   requirement before they start.

4. Each entry in ``rule-provenance.md`` (rows under the per-section
   markdown tables) must carry a non-empty Source citation cell. This
   is the runtime equivalent of "rules without Source are inadmissible".
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROVENANCE_PATH = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'references'
    / 'rule-provenance.md'
)
RULE_CATALOG_PATH = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'references'
    / 'rule-catalog.md'
)
SKILL_DESIGN_PATH = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-architecture'
    / 'references'
    / 'skill-design.md'
)


# =============================================================================
# rule-catalog.md: Provenance Contract section
# =============================================================================


def test_rule_catalog_has_provenance_contract_section():
    """rule-catalog.md must declare the Provenance Contract section."""
    content = RULE_CATALOG_PATH.read_text(encoding='utf-8')
    assert '## Provenance Contract for New Rules' in content, (
        'rule-catalog.md must include a "## Provenance Contract for New Rules" section.'
    )


def test_rule_catalog_provenance_contract_lists_required_artifacts():
    """The contract section must enumerate every required artifact."""
    content = RULE_CATALOG_PATH.read_text(encoding='utf-8')
    # Find the contract section by anchoring on its heading and reading to the next H2 / EOF.
    match = re.search(
        r'## Provenance Contract for New Rules\s*\n(.*?)(?=\n## |\Z)',
        content,
        re.DOTALL,
    )
    assert match, 'Could not isolate the Provenance Contract section body'
    body = match.group(1)
    # Required artifacts that must be enumerated:
    required_phrases = [
        'rule-provenance.md',
        'rule-catalog.md',
        '_cmd_apply.py',
        '_cmd_verify.py',
        'fix-catalog.md',
        'FIXABLE_ISSUE_TYPES',
        'Source',  # the citation requirement
    ]
    missing = [p for p in required_phrases if p not in body]
    assert not missing, f'Provenance Contract section missing required phrases: {missing}'


def test_rule_catalog_provenance_contract_names_audit_gate():
    """The contract must name the regression test gate that enforces it."""
    content = RULE_CATALOG_PATH.read_text(encoding='utf-8')
    assert 'test_rule_provenance_table.py' in content, (
        'Provenance Contract must reference the test_rule_provenance_table.py audit gate.'
    )


# =============================================================================
# skill-design.md: cross-reference to the contract
# =============================================================================


def test_skill_design_references_provenance_contract():
    """plugin-architecture/skill-design.md must reference the provenance contract."""
    content = SKILL_DESIGN_PATH.read_text(encoding='utf-8')
    # Tolerate any of the canonical phrasings.
    canonical_phrases = [
        'Provenance Contract',
        'rule-provenance.md',
    ]
    found = [p for p in canonical_phrases if p in content]
    assert found, (
        f'skill-design.md must reference the provenance contract via one of {canonical_phrases}'
    )


def test_skill_design_explains_rationale():
    """The skill-design.md mention must include a rationale, not just a link."""
    content = SKILL_DESIGN_PATH.read_text(encoding='utf-8')
    # Locate the provenance-related block.
    match = re.search(
        r'(Plugin-Doctor Rule Provenance Contract|Provenance Contract).{20,2000}',
        content,
        re.DOTALL,
    )
    assert match, 'Could not locate the provenance reference in skill-design.md'
    block = match.group(0)
    # The block must mention either "Source" (citation requirement) or
    # "rule-provenance.md" (the registry).
    assert 'Source' in block or 'rule-provenance.md' in block, (
        'skill-design.md provenance reference must name the Source citation requirement '
        'or the rule-provenance.md registry.'
    )


# =============================================================================
# rule-provenance.md: every row carries a Source citation
# =============================================================================


def _is_section_header(line: str) -> bool:
    """A line is a section header if it starts with ## or ###."""
    return line.startswith('## ') or line.startswith('### ')


def _is_table_separator(line: str) -> bool:
    """A line is a table separator if it consists of pipes and dashes."""
    stripped = line.replace('|', '').replace('-', '').replace(' ', '').replace(':', '')
    return stripped == '' and '|' in line and '-' in line


def _is_table_header(line: str) -> bool:
    """A line is a table header if it starts with | and contains 'Rule ID' or 'Date'."""
    return line.startswith('|') and ('Rule ID' in line or 'Date' in line or 'Class' in line)


def _extract_rule_rows():
    """Yield (rule_id, source_cell) for every rule row in the provenance table."""
    content = PROVENANCE_PATH.read_text(encoding='utf-8')
    for line in content.splitlines():
        if not line.startswith('|'):
            continue
        if _is_table_separator(line):
            continue
        if _is_table_header(line):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) < 2:
            continue
        first = cells[0].strip('`')
        # Drop parenthetical notes ("(already listed under ...)")
        first_clean = re.sub(r'\s*\(.*\)\s*$', '', first)
        # Skip non-rule rows (audit history table uses Date / Plan / etc.)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]+', first_clean):
            continue
        # The Source cell is typically the last cell for rule rows (Rule ID,
        # Class, Emitter, Source). For audit-history rows the columns differ;
        # we already skipped those above by requiring the first cell to be a
        # valid rule-ID-shaped token.
        source = cells[-1].strip()
        yield first_clean, source


def test_every_provenance_row_has_non_empty_source():
    """Every rule row in rule-provenance.md must have a non-empty Source cell."""
    missing = [rule_id for rule_id, source in _extract_rule_rows() if not source]
    assert not missing, (
        f'Rules in rule-provenance.md with empty Source citation: {missing}\n'
        f'Every rule must cite a lesson, architectural standard, or decision.log entry.'
    )


def test_provenance_audit_history_table_present():
    """The audit history section must include a removed-rules table."""
    content = PROVENANCE_PATH.read_text(encoding='utf-8')
    # Find the audit history section
    match = re.search(r'## Audit history\s*\n(.*)', content, re.DOTALL)
    assert match, 'rule-provenance.md missing "## Audit history" section'
    body = match.group(1)
    # The audit history must include at least one row documenting the
    # unsupported-skill-tools-field removal.
    assert 'unsupported-skill-tools-field' in body, (
        'Audit history must record the unsupported-skill-tools-field removal '
        '(plan harden-phase3-outline-plugin-doctor-audit).'
    )
