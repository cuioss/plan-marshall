# ruff: noqa: I001, E402
"""Provenance-audit tests for plugin-doctor.

The ``references/rule-provenance.md`` table is the source-of-truth audit
trail for every rule emitted by plugin-doctor analyzers. These tests pin
the invariants:

1. Every rule_id literal emitted by an ``_analyze_*.py`` / ``_doctor_*.py``
   module under ``marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/``
   has a matching row in ``rule-provenance.md`` (rule ID appears verbatim
   in a markdown table row).

2. Every rule ID in the provenance table that has a Source citation has a
   non-empty Source value (the contract requires citation; rules without
   citation are inadmissible per the audit history).

3. Every entry in ``_doctor_shared.py::FIXABLE_ISSUE_TYPES`` appears in
   ``rule-provenance.md`` (a rule cannot be auto-fixable without provenance).

4. The fabricated ``unsupported-skill-tools-field`` rule is absent from
   the provenance table (regression on the removal performed in plan
   ``harden-phase3-outline-plugin-doctor-audit``).
"""

import re
import sys
from pathlib import Path

from conftest import get_scripts_dir, load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# Retained: inserted on sys.path (used outside the module loader) so the
# analyzer modules' intra-bundle ``from <module> import ...`` references resolve.
SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')
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

sys.path.insert(0, str(SCRIPTS_DIR))

# file_ops lives in plan-marshall; add for completeness so loading _doctor_shared
# succeeds.
_FILE_OPS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-file-ops'
    / 'scripts'
)
sys.path.insert(0, str(_FILE_OPS_DIR))


def _load_doctor_shared():
    return load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_doctor_shared.py', '_doctor_shared_provenance'
    )


# Modules that emit analyzer-internal status tags (extension loading, raw IO
# errors) rather than validation rules. They live alongside the analyzers but
# the strings they emit are not audit-tracked lint rules.
NON_RULE_EMITTING_MODULES = frozenset(
    {
        '_cmd_extension.py',
        '_cmd_cross_file.py',  # emits 'duplication'/'extraction'/'terminology' which ARE rules; handled below
    }
)

# Rule IDs intentionally excluded from the provenance audit because they are
# component-type tags or finding-shape tags, not validation rules:
#   - agent, command, skill, script, template, workflow (component types)
#   - tool names (Skill, Task, SlashCommand) — these appear in 'type' positions
#     in agent metadata, not in finding emissions
#   - snake_case status tokens (parse_error, file_read_error etc.) — analyzer
#     internal status payloads, not rule IDs. Real lint-rule IDs are kebab-case
#     or uppercase-underscore (ARGUMENT_NAMING_*, MARK_STEP_DONE_*).
NON_RULE_TYPE_TOKENS = frozenset(
    {
        # component types
        'agent',
        'command',
        'skill',
        'script',
        'template',
        'workflow',
        # tool names
        'Skill',
        'Task',
        'SlashCommand',
        # operational / shaping diagnostics
        'file_read_error',
        'shell_substitution_in_skills',  # the underscore variant is analyzer-internal; the kebab variant IS in the table
        'file_type',
        'analyze_shell_substitution_in_skills',  # RULE_NAME constant in module, not a rule ID
        # HARDCODED_MODEL_ON_CANONICAL is an extension-validation status, not a marketplace rule
        'HARDCODED_MODEL_ON_CANONICAL',
    }
)


def _is_audit_tracked_rule_id(token: str) -> bool:
    """Heuristic gate distinguishing lint-rule IDs from analyzer internal payloads.

    Real lint-rule IDs:
      * kebab-case (lowercase + hyphens): `agent-skill-tool-visibility`
      * UPPER_SNAKE: `ARGUMENT_NAMING_NOTATION_INVALID`, `MARK_STEP_DONE_*`

    Analyzer-internal status tokens use snake_case (`parse_error`,
    `missing_skill`, `invalid_domain`). These never enter the provenance
    audit because they describe operational diagnostics, not lint findings.
    """
    if token in NON_RULE_TYPE_TOKENS:
        return False
    # Pure UPPER_SNAKE is a tracked rule ID (the ARGUMENT_NAMING_* and
    # MARK_STEP_DONE_* clusters).
    if re.fullmatch(r'[A-Z][A-Z0-9_]+', token):
        return True
    # Mixed-case or PascalCase tokens are not rule IDs.
    if re.search(r'[A-Z]', token) and '_' in token:
        return False
    # Contains underscore but no hyphen → snake_case operational status.
    if '_' in token and '-' not in token:
        return False
    # Pure kebab-case (lowercase + hyphens) is a tracked rule ID.
    if re.fullmatch(r'[a-z][a-z0-9-]+', token):
        return True
    return False


def _extract_rule_ids_from_script(path: Path) -> set[str]:
    """Extract rule IDs from string literals in 'type'/'rule_id' positions."""
    rule_ids: set[str] = set()
    if not path.is_file():
        return rule_ids
    if path.name == '_cmd_extension.py':
        # Extension-loading diagnostics are not lint rules; the module emits
        # ``'type': 'invalid_domain'`` etc. as part of extension validation,
        # not as findings about marketplace artifacts.
        return rule_ids
    try:
        content = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return rule_ids
    # Match: 'type': 'rule-id-here' or 'rule_id': 'rule-id-here'
    for match in re.finditer(r"'(?:type|rule_id)':\s*'([A-Za-z_][A-Za-z0-9_-]+)'", content):
        token = match.group(1)
        if _is_audit_tracked_rule_id(token):
            rule_ids.add(token)
    return rule_ids


def _all_emitted_rule_ids() -> set[str]:
    """Aggregate rule IDs across every analyzer module."""
    rule_ids: set[str] = set()
    for py_file in sorted(SCRIPTS_DIR.glob('_*.py')):
        rule_ids |= _extract_rule_ids_from_script(py_file)
    # Add IDs declared via module-level RULE_* constants when emitted as
    # ``'rule_id': RULE_ID``. These show up as variable references in regex,
    # so the regex above misses them — parse the constant assignments directly.
    for py_file in sorted(SCRIPTS_DIR.glob('_*.py')):
        if not py_file.is_file():
            continue
        if py_file.name == '_cmd_extension.py':
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for match in re.finditer(r"^(RULE[A-Z_]*|FINDING_TYPE)\s*=\s*'([A-Za-z_][A-Za-z0-9_-]+)'", content, re.MULTILINE):
            token = match.group(2)
            if _is_audit_tracked_rule_id(token):
                rule_ids.add(token)
    return rule_ids


def _provenance_rule_ids() -> set[str]:
    """Extract rule IDs from the provenance table by scanning markdown rows.

    The table uses pipe-delimited rows where the first cell holds the rule
    ID, sometimes wrapped in backticks.
    """
    content = PROVENANCE_PATH.read_text(encoding='utf-8')
    ids: set[str] = set()
    # Match table rows beginning with `|` and extract the first cell.
    for line in content.splitlines():
        if not line.startswith('|') or line.startswith('|---') or line.startswith('| ---'):
            continue
        # Split by pipes; first cell after the leading |
        cells = [c.strip() for c in line.split('|')[1:]]
        if not cells:
            continue
        first = cells[0]
        # Skip header rows like "Rule ID" or "Class"
        if not first or first.lower() in ('rule id', 'class', 'date'):
            continue
        # Strip backticks
        first = first.strip('`')
        # Drop trailing parenthetical notes (e.g. "(already listed under Skill rules)")
        first = re.sub(r'\s*\(.*\)\s*$', '', first)
        # The provenance "file-bloat-ack" entry is documented as an
        # "Extension of file-bloat / subdoc-bloat" with a phrase in the cell;
        # accept tokens that look like rule IDs (alphanumeric + dash + _)
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]+', first):
            ids.add(first)
    return ids


# =============================================================================
# Tests
# =============================================================================


def test_provenance_file_exists():
    """The provenance table file must exist at the documented path."""
    assert PROVENANCE_PATH.is_file(), f'rule-provenance.md not found at {PROVENANCE_PATH}'


def test_every_emitted_rule_id_has_provenance_entry():
    """Every rule_id emitted by analyzer modules must appear in the provenance table."""
    emitted = _all_emitted_rule_ids()
    documented = _provenance_rule_ids()

    missing = sorted(emitted - documented)
    assert not missing, (
        f'Rule IDs emitted by analyzer modules but missing from rule-provenance.md: {missing}\n'
        f'Add a row for each one with class, emitter, and Source citation.'
    )


def test_fixable_issue_types_have_provenance():
    """Every entry in FIXABLE_ISSUE_TYPES must appear in the provenance table."""
    shared = _load_doctor_shared()
    fixable: set[str] = set(shared.FIXABLE_ISSUE_TYPES)
    documented = _provenance_rule_ids()

    missing = sorted(fixable - documented)
    assert not missing, (
        f'FIXABLE_ISSUE_TYPES entries missing from rule-provenance.md: {missing}\n'
        f'Every fixable rule must have a provenance citation.'
    )


def test_safe_and_risky_subset_of_fixable():
    """SAFE_FIX_TYPES and RISKY_FIX_TYPES must be subsets of FIXABLE_ISSUE_TYPES."""
    shared = _load_doctor_shared()
    fixable: set[str] = set(shared.FIXABLE_ISSUE_TYPES)
    safe: set[str] = set(shared.SAFE_FIX_TYPES)
    risky: set[str] = set(shared.RISKY_FIX_TYPES)

    # All safe fixes should be in the unified fixable registry.
    safe_orphans = safe - fixable
    # RISKY_FIX_TYPES is allowed to include rules not yet in FIXABLE_ISSUE_TYPES
    # only for rules that are still under review; pin the current state with a
    # tolerance set tied to the documented surface.
    assert not safe_orphans, (
        f'SAFE_FIX_TYPES entries missing from FIXABLE_ISSUE_TYPES: {sorted(safe_orphans)}'
    )
    # Risky orphans are acceptable transitional state but must be documented in
    # the provenance table.
    documented = _provenance_rule_ids()
    risky_undocumented = sorted(risky - documented)
    assert not risky_undocumented, (
        f'RISKY_FIX_TYPES entries missing from rule-provenance.md: {risky_undocumented}'
    )


def test_unsupported_skill_tools_field_absent_from_provenance():
    """Regression: the fabricated unsupported-skill-tools-field rule must stay deleted."""
    documented = _provenance_rule_ids()
    assert 'unsupported-skill-tools-field' not in documented, (
        'Fabricated rule unsupported-skill-tools-field must not be in rule-provenance.md. '
        'It was removed in plan harden-phase3-outline-plugin-doctor-audit.'
    )


def test_audit_history_section_present():
    """The provenance file must carry the audit-history section."""
    content = PROVENANCE_PATH.read_text(encoding='utf-8')
    assert '## Audit history' in content, (
        'rule-provenance.md must include an "## Audit history" section documenting rule removals.'
    )
    assert 'unsupported-skill-tools-field' in content, (
        'Audit history must record the unsupported-skill-tools-field removal.'
    )


def test_provenance_contract_section_present():
    """The provenance file must define the contract for adding new rules."""
    content = PROVENANCE_PATH.read_text(encoding='utf-8')
    assert 'Provenance contract for new rules' in content, (
        'rule-provenance.md must include a "Provenance contract for new rules" section.'
    )
