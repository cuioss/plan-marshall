# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Architecture-level assertions for the uniform-``Finding`` migration (D3).

These tests pin the ACHIEVED ``Finding`` architecture across the plugin-doctor
analyzer subsystem — the structural shape the migration converged on:

  * The four pure-normalization ``extract_issues_from_*`` shims (``verb_chain``,
    ``manage_findings``, ``refine_contract``, ``notation_staleness``) and the
    ``rule_id`` fallback normalization were DELETED. The only surviving
    ``extract_issues_from_*`` functions are the three INTERPRETATION functions,
    which translate a raw analysis record into issues (genuine logic, not a
    passthrough shim).
  * The ~30 migrated analyzers plus the canonical construction sites in
    ``_doctor_analysis.py`` construct ``Finding`` objects and import the
    dataclass from the single source ``_doctor_shared``.
  * The three interpretation functions
    (``extract_issues_from_markdown_analysis`` / ``_coverage_analysis`` /
    ``_subdoc_analysis``) are RETAINED — they build ``Finding`` internally and
    emit ``Finding``-shaped dicts. They are asserted to EMIT ``Finding``, NOT to
    be deleted.
  * The typeless-dict analyzers (whose historical output carries no ``type``
    key, keying on ``rule_id`` instead) and the intermediate-record analyzers
    are intentionally NOT on ``Finding``. ``Finding.to_dict()`` always emits a
    ``type`` key, so migrating these would change their serialized shape and
    break byte-identical output.
"""

import re
from pathlib import Path

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')

# The four pure-normalization shims removed in the migration.
_DELETED_SHIMS = ('verb_chain', 'manage_findings', 'refine_contract', 'notation_staleness')

# The three interpretation functions that survive and emit Finding internally.
_INTERPRETATION_FNS = (
    'extract_issues_from_markdown_analysis',
    'extract_issues_from_coverage_analysis',
    'extract_issues_from_subdoc_analysis',
)

# Typeless-dict / intermediate-record analyzers intentionally NOT migrated.
# Their finding output keys on ``rule_id`` and carries no ``type`` key; routing
# them through ``Finding`` (which always emits ``type``) would break the
# byte-identical serialization the migration preserves.
_NOT_ON_FINDING = (
    '_analyze_cmd_root_anchoring.py',
    '_analyze_executor_path_in_production.py',
    '_analyze_fail_closed_gate_reads.py',
    '_analyze_metadata_field_validity.py',
    '_analyze_orphan_argparse_flags.py',
    '_analyze_plan_path_in_scripts.py',
    '_analyze_resolution_branch_markers.py',
    '_analyze_shell_active_tokens.py',
)

_FINDING_CALL = re.compile(r'\bFinding\(')
_FINDING_IMPORT = 'from _doctor_shared import Finding'


def _scripts() -> list[Path]:
    return sorted(_SCRIPTS_DIR.glob('*.py'))


def _modules_constructing_finding() -> list[str]:
    return [s.name for s in _scripts() if _FINDING_CALL.search(s.read_text(encoding='utf-8'))]


# ---------------------------------------------------------------------------
# Deleted normalization shims
# ---------------------------------------------------------------------------


def test_normalization_shims_are_deleted():
    """No analyzer defines a pure-normalization extract_issues_from_<shim> function."""
    offenders = []
    for script in _scripts():
        text = script.read_text(encoding='utf-8')
        for shim in _DELETED_SHIMS:
            if re.search(rf'^def extract_issues_from_{shim}\b', text, re.MULTILINE):
                offenders.append(f'{script.name}: extract_issues_from_{shim}')
    assert offenders == [], f'normalization shims must be deleted, found: {offenders}'


def test_only_interpretation_extract_issues_functions_remain():
    """The only surviving extract_issues_from_* defs are the three interpretation fns."""
    found = []
    for script in _scripts():
        text = script.read_text(encoding='utf-8')
        found.extend(re.findall(r'^def (extract_issues_from_\w+)', text, re.MULTILINE))
    assert sorted(found) == sorted(_INTERPRETATION_FNS)


# ---------------------------------------------------------------------------
# Interpretation functions are retained and emit Finding-shaped dicts
# ---------------------------------------------------------------------------

_analysis = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_doctor_analysis.py', '_doctor_analysis_migration'
)


def test_interpretation_functions_are_retained_and_callable():
    for fn in _INTERPRETATION_FNS:
        assert callable(getattr(_analysis, fn, None)), f'{fn} must be retained and callable'


def test_markdown_interpretation_emits_finding_shaped_dict():
    """extract_issues_from_markdown_analysis builds Finding internally and emits its dict."""
    issues = _analysis.extract_issues_from_markdown_analysis(
        {'frontmatter': {'present': False}}, 'a.md', 'skill'
    )

    assert issues == [
        {'type': 'missing-frontmatter', 'file': 'a.md', 'severity': 'error', 'fixable': True}
    ]


def test_coverage_interpretation_emits_finding_shaped_dict():
    """extract_issues_from_coverage_analysis builds Finding internally and emits its dict."""
    issues = _analysis.extract_issues_from_coverage_analysis(
        {'critical_violations': {'has_task_declared': True}}, 'agent.md', 'agent'
    )

    assert issues == [
        {
            'type': 'agent-task-tool-prohibited',
            'file': 'agent.md',
            'severity': 'warning',
            'fixable': True,
            'description': 'Agent declares Task tool (agent-task-tool-prohibited)',
        }
    ]


def test_subdoc_interpretation_emits_finding_shaped_dict():
    """extract_issues_from_subdoc_analysis builds Finding internally and emits its dict."""
    issues = _analysis.extract_issues_from_subdoc_analysis(
        [{'path': 'sub.md', 'issues': [
            {'type': 'subdoc-bloat', 'classification': 'BLOATED', 'line_count': 500},
        ]}],
        'skill-dir',
    )

    assert len(issues) == 1
    finding = issues[0]
    assert finding['type'] == 'subdoc-bloat'
    assert finding['file'] == 'sub.md'
    assert finding['fixable'] is False
    # ``extra`` keys merge verbatim at the top level.
    assert finding['classification'] == 'BLOATED'
    assert finding['line_count'] == 500


# ---------------------------------------------------------------------------
# Migrated analyzers construct Finding from the single source
# ---------------------------------------------------------------------------


def test_doctor_analysis_is_the_canonical_construction_site():
    text = (_SCRIPTS_DIR / '_doctor_analysis.py').read_text(encoding='utf-8')

    assert _FINDING_IMPORT in text
    assert len(_FINDING_CALL.findall(text)) >= 20


def test_representative_analyzers_are_migrated_to_finding():
    migrated = _modules_constructing_finding()
    for required in (
        '_analyze_frontmatter.py',
        '_analyze_argument_naming.py',
        '_analyze_verb_chains.py',
        '_analyze_phase2_refine_contract.py',
        '_analyze_notation_staleness.py',
        '_analyze_manage_findings_invocation.py',
    ):
        assert required in migrated, f'{required} must construct Finding'


def test_roughly_thirty_analyzers_migrated_to_finding():
    """The migration moved ~30 analyzers onto the uniform Finding constructor."""
    migrated = _modules_constructing_finding()

    assert len(migrated) >= 25, f'expected ~30 migrated analyzers, found {len(migrated)}'


def test_every_finding_constructor_imports_from_shared():
    """No analyzer defines its own Finding — all import the single dataclass."""
    for name in _modules_constructing_finding():
        text = (_SCRIPTS_DIR / name).read_text(encoding='utf-8')
        assert _FINDING_IMPORT in text, (
            f'{name} constructs Finding but does not import it from _doctor_shared'
        )


# ---------------------------------------------------------------------------
# Typeless / intermediate-record analyzers intentionally stay off Finding
# ---------------------------------------------------------------------------


def test_typeless_and_intermediate_analyzers_stay_off_finding():
    """These analyzers preserve byte-identical (typeless) output by avoiding Finding."""
    for name in _NOT_ON_FINDING:
        path = _SCRIPTS_DIR / name
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        assert not _FINDING_CALL.search(text), (
            f'{name} must stay off Finding to preserve byte-identical (typeless) output'
        )
        assert _FINDING_IMPORT not in text, f'{name} must not import Finding'
