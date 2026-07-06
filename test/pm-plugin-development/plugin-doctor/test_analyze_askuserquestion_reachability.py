# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for _analyze_askuserquestion_reachability.py.

Covers the askuserquestion-in-dispatched-workflow analyzer:

- Flags an ``AskUserQuestion:`` invocation block inside a dispatched-leaf
  workflow doc (declared via the execution-context ``implements:`` marker or a
  ``phase-*/SKILL.md``)
- Does NOT flag a prose-only mention of the tool
- Does NOT flag a main-context (non-dispatched) workflow — a doc carrying a
  ``Task:`` dispatch directive
- Does NOT flag a non-workflow doc (no ``implements:`` marker, not a phase skill)
- Does NOT flag a bare ``AskUserQuestion:`` header with no invocation-block body
- Finding shape: all required fields present and correctly typed
- Clean baseline: an empty tree produces no findings
- The rule appears in the doctor-marketplace rule registry (provenance table)
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aar = _load_module(
    '_analyze_askuserquestion_reachability',
    '_analyze_askuserquestion_reachability.py',
)
analyze_askuserquestion_reachability = _aar.analyze_askuserquestion_reachability
RULE_ID = _aar.RULE_ID
RULE_NAME = _aar.RULE_NAME
FINDING_TYPE = _aar.FINDING_TYPE

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

# A frontmatter block declaring the execution-context workflow-body marker.
_IMPLEMENTS_FM = (
    '---\n'
    'implements: plan-marshall:extension-api/standards/'
    'ext-point-execution-context-workflow\n'
    '---\n'
)

# A canonical AskUserQuestion invocation block (header + questions: sub-key).
_ASKUSER_BLOCK = (
    'AskUserQuestion:\n'
    '  questions:\n'
    '    - question: "Which option?"\n'
    '      header: "Choose"\n'
    '      options:\n'
    '        - label: "A"\n'
    '          description: "first"\n'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workflow_doc(
    tmp_path: Path,
    content: str,
    *,
    bundle: str = 'plan-marshall',
    skill: str = 'fixture-skill',
    filename: str = 'SKILL.md',
    subdir: str | None = None,
) -> Path:
    """Create a fake bundle skill markdown file under tmp_path.

    Replicates the layout the scanner walks:
    ``<marketplace_root>/<bundle>/skills/<skill>[/<subdir>]/<filename>``.
    """
    skill_dir = tmp_path / bundle / 'skills' / skill
    if subdir:
        skill_dir = skill_dir / subdir
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / filename
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Flags: AskUserQuestion invocation block inside a dispatched-leaf doc
# ---------------------------------------------------------------------------


class TestFlagsDispatchedLeaf:
    def test_block_in_implements_marked_doc_flagged(self, tmp_path):
        content = _IMPLEMENTS_FM + '\n# Fixture\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_block_in_phase_skill_flagged(self, tmp_path):
        # A phase-*/SKILL.md is a dispatched-leaf even without the implements
        # frontmatter marker.
        content = '# Phase Skill\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content, skill='phase-2-refine')
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_block_in_workflow_subdir_doc_flagged(self, tmp_path):
        content = _IMPLEMENTS_FM + '\n# Body\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content, subdir='workflow', filename='body.md')
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1

    def test_question_subkey_variant_flagged(self, tmp_path):
        content = (
            _IMPLEMENTS_FM
            + '\n# Fixture\n\n'
            + 'AskUserQuestion:\n'
            + '  question: "single question form"\n'
        )
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1

    def test_multiple_blocks_each_flagged(self, tmp_path):
        content = (
            _IMPLEMENTS_FM
            + '\n# Fixture\n\n'
            + _ASKUSER_BLOCK
            + '\nProse between blocks.\n\n'
            + _ASKUSER_BLOCK
        )
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 2


# ---------------------------------------------------------------------------
# Does NOT flag: prose, main-context orchestrators, non-workflow docs
# ---------------------------------------------------------------------------


class TestDoesNotFlag:
    def test_prose_mention_not_flagged(self, tmp_path):
        content = (
            _IMPLEMENTS_FM
            + '\n# Fixture\n\n'
            + 'Do NOT fire `AskUserQuestion` here — return a prompt-required '
            + 'envelope so the orchestrator owns the AskUserQuestion instead.\n'
        )
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []

    def test_main_context_orchestrator_not_flagged(self, tmp_path):
        # A doc that dispatches (carries a Task: directive) is a main-context
        # orchestrator; its AskUserQuestion blocks are reachable and must NOT be
        # flagged.
        content = (
            _IMPLEMENTS_FM
            + '\n# Orchestrator\n\n'
            + 'Dispatch the phase:\n\n'
            + '```text\n'
            + 'Task: plan-marshall:execution-context-3\n'
            + '  prompt: |\n'
            + '    name: phase-1-init\n'
            + '```\n\n'
            + 'Then prompt the operator:\n\n'
            + _ASKUSER_BLOCK
        )
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []

    def test_non_workflow_doc_not_flagged(self, tmp_path):
        # No implements marker and not a phase skill — an ordinary knowledge
        # doc that happens to carry an AskUserQuestion block is out of scope.
        content = (
            '---\n'
            'name: ordinary-skill\n'
            'mode: knowledge\n'
            '---\n\n'
            '# Ordinary\n\n'
            + _ASKUSER_BLOCK
        )
        _make_workflow_doc(tmp_path, content, skill='ordinary-skill')
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []

    def test_bare_header_without_subkey_not_flagged(self, tmp_path):
        # A bare AskUserQuestion: line whose next non-blank line is not a
        # questions:/question:/options: sub-key is not an invocation block.
        content = (
            _IMPLEMENTS_FM
            + '\n# Fixture\n\n'
            + 'AskUserQuestion:\n'
            + 'some following prose, not a sub-key.\n'
        )
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        content = _IMPLEMENTS_FM + '\n# Fixture\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == RULE_NAME
        assert isinstance(f['file'], str)
        assert isinstance(f['line'], int)
        assert f['severity'] == 'warning'
        assert f['fixable'] is False
        assert isinstance(f['snippet'], str)
        assert isinstance(f['description'], str)

    def test_line_number_is_the_header_line(self, tmp_path):
        # Frontmatter (3 lines) + blank + "# Fixture" + blank => AskUserQuestion:
        # header lands on line 7 (1-based).
        content = _IMPLEMENTS_FM + '\n# Fixture\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1
        assert findings[0]['line'] == 7

    def test_file_path_is_absolute(self, tmp_path):
        content = _IMPLEMENTS_FM + '\n# Fixture\n\n' + _ASKUSER_BLOCK
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert len(findings) == 1
        assert Path(findings[0]['file']).is_absolute()


# ---------------------------------------------------------------------------
# Clean baseline
# ---------------------------------------------------------------------------


class TestCleanBaseline:
    def test_empty_marketplace_root_no_findings(self, tmp_path):
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []

    def test_dispatched_leaf_without_askuserquestion_no_findings(self, tmp_path):
        content = _IMPLEMENTS_FM + '\n# Fixture\n\nJust some prose, no prompt.\n'
        _make_workflow_doc(tmp_path, content)
        findings = analyze_askuserquestion_reachability(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Rule registry presence
# ---------------------------------------------------------------------------


class TestRuleRegistry:
    """The rule must be registered in the doctor-marketplace provenance table.

    ``rule-provenance.md`` is the source-of-truth registry that
    ``test_rule_provenance_table.py`` audits against every emitted rule_id.
    """

    def test_rule_id_appears_in_a_table_row(self):
        content = PROVENANCE_PATH.read_text(encoding='utf-8')
        rows = [
            line
            for line in content.splitlines()
            if line.startswith('|') and RULE_ID in line
        ]
        assert rows, (
            f'{RULE_ID} must appear in a pipe-delimited table row in '
            f'rule-provenance.md, not only in prose.'
        )
        first_cell = rows[0].split('|')[1].strip().strip('`')
        assert first_cell == RULE_ID
