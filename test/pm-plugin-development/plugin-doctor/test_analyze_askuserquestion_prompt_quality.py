# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for _analyze_askuserquestion_prompt_quality.py.

Covers the askuserquestion-prompt-quality analyzer:

- Governing acceptance test: the operator's `api-sheriff` prompt produces
  findings, and a conformant rewrite of the same decision produces none
- check A flags a step number, a tool-API type name, and an internal-mechanics
  noun in a preamble or in an option label / description
- check B flags an option with no description and one that restates its label
- Declared blind spots: a prompt violating only obligation 3, or only
  obligation 4, produces nothing
- Does NOT flag a prose mention of the tool outside an invocation block
- Does NOT flag a bare `AskUserQuestion:` header with no invocation-block body
- Finding shape: all required fields present, `population_size` published
- Clean baseline: an empty tree produces no findings
- The rule appears in the doctor-marketplace rule registry (provenance table)
"""
from pathlib import Path

from conftest import PROJECT_ROOT, load_script_module

from _plugin_doctor_fixtures import assert_analyzer_findings


# Called with literals rather than through a wrapper so the loader-collision
# guard in test_conftest_loader_contract.py can resolve this call site
# statically — a wrapped call is invisible to it.
_aapq = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_askuserquestion_prompt_quality.py',
    '_analyze_askuserquestion_prompt_quality',
)
analyze_askuserquestion_prompt_quality = _aapq.analyze_askuserquestion_prompt_quality
RULE_ID = _aapq.RULE_ID
RULE_NAME = _aapq.RULE_NAME
FINDING_TYPE = _aapq.FINDING_TYPE

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

# The two recorded verbatim fragments of the operator's `api-sheriff` prompt —
# checked-in literals, never resolved from a git object at test time. Options 1-3
# of that prompt are not part of the record and are deliberately not invented.
_API_SHERIFF_PREAMBLE = (
    'Domain detection returned ambiguous (no narrative match). '
    'Per Step 7 this requires an operator multiSelect'
)
_API_SHERIFF_OPTION_4 = (
    'pick this only if you want the plan to avoid loading the Java/CUI standard sets'
)

_API_SHERIFF_BLOCK = (
    'AskUserQuestion:\n'
    f'  question: "{_API_SHERIFF_PREAMBLE}"\n'
    '  options:\n'
    f'    - label: "{_API_SHERIFF_OPTION_4}"\n'
)

# The conformant rewrite of the same decision: the reader still picks the review
# standards, stated without a step number, a tool-API type, or an option that can
# only be evaluated by reasoning about what the system loads internally.
_CONFORMANT_BLOCK = (
    'AskUserQuestion:\n'
    '  question: "Your files match no single language clearly, so the review '
    'standards cannot be picked automatically. Which should this plan apply?"\n'
    '  options:\n'
    '    - label: "Java (recommended)"\n'
    '      description: "Reviews your code against the Java conventions for '
    'naming, null-safety, and tests."\n'
    '    - label: "Python"\n'
    '      description: "Reviews your code against the Python conventions for '
    'typing, packaging, and pytest."\n'
    '    - label: "Neither"\n'
    '      description: "Reviews your code against language-neutral rules only; '
    'no language-specific findings are raised."\n'
)


def _make_skill_doc(tmp_path: Path, content: str, *, skill: str = 'fixture-skill') -> Path:
    """Create a fake bundle skill markdown file under tmp_path.

    Replicates the layout the scanner walks:
    ``<marketplace_root>/<bundle>/skills/<skill>/SKILL.md``.
    """
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Governing acceptance test — the operator's api-sheriff prompt
# ---------------------------------------------------------------------------


class TestApiSheriffAcceptance:
    def test_api_sheriff_prompt_produces_findings(self, tmp_path):
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK)
        findings = analyze_askuserquestion_prompt_quality(tmp_path)
        assert findings, 'the api-sheriff prompt must not pass the rule'
        assert {f['rule_id'] for f in findings} == {RULE_ID}

    def test_api_sheriff_preamble_is_flagged_for_both_vocabulary_families(self, tmp_path):
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK)
        findings = analyze_askuserquestion_prompt_quality(tmp_path)
        preamble = [f for f in findings if 'preamble' in f['description']]
        assert len(preamble) == 1
        assert 'Step 7' in preamble[0]['description']
        assert 'multiselect' in preamble[0]['description']

    def test_api_sheriff_option_is_flagged_by_both_checks(self, tmp_path):
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK)
        findings = analyze_askuserquestion_prompt_quality(tmp_path)
        option = [f for f in findings if f['snippet'] == _API_SHERIFF_OPTION_4]
        # check A (internal-mechanics noun) and check B (no description).
        assert len(option) == 2
        descriptions = ' '.join(f['description'] for f in option)
        assert 'standard set' in descriptions
        assert 'no description' in descriptions

    def test_conformant_rewrite_produces_nothing(self, tmp_path):
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _CONFORMANT_BLOCK)
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])


# ---------------------------------------------------------------------------
# check A — preamble / option vocabulary
# ---------------------------------------------------------------------------


class TestVocabularyCheck:
    def test_step_number_in_preamble_flagged(self, tmp_path):
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "Per Step 4b the caller must choose"\n'
            '  options:\n'
            '    - label: "Go"\n'
            '      description: "Runs the change against your working copy."\n',
        )
        assert_analyzer_findings(
            analyze_askuserquestion_prompt_quality, tmp_path, [RULE_ID]
        )

    def test_internal_noun_in_option_description_flagged(self, tmp_path):
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "How should the change be applied?"\n'
            '  options:\n'
            '    - label: "Isolated"\n'
            '      description: "Applies the change inside a worktree."\n'
            '    - label: "In place"\n'
            '      description: "Applies the change to the files you have open."\n',
        )
        assert_analyzer_findings(
            analyze_askuserquestion_prompt_quality, tmp_path, [RULE_ID]
        )


# ---------------------------------------------------------------------------
# check B — option missing consequence
# ---------------------------------------------------------------------------


class TestConsequenceCheck:
    def test_description_restating_label_flagged(self, tmp_path):
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "How should the branch land?"\n'
            '  options:\n'
            '    - label: "Squash"\n'
            '      description: "Squash."\n'
            '    - label: "Rebase"\n'
            '      description: "Each commit lands separately and history is kept."\n',
        )
        assert_analyzer_findings(
            analyze_askuserquestion_prompt_quality, tmp_path, [RULE_ID]
        )

    def test_flow_style_option_with_description_is_not_flagged(self, tmp_path):
        # ``- label: "X"  description: "Y"`` on one line is a described option;
        # reading only the first key would report it as description-less.
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "How should the branch land?"\n'
            '  options:\n'
            '    - label: "Squash"  description: "The branch lands as one commit."\n'
            '    - label: "Rebase"  description: "Every commit lands separately."\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])


# ---------------------------------------------------------------------------
# Declared blind spots — obligations 3 and 4 are deliberately NOT evaluated
# ---------------------------------------------------------------------------


class TestDeclaredBlindSpots:
    def test_unmarked_recommendation_ordered_last_produces_nothing(self, tmp_path):
        # Obligation 3 violated (the sensible default is last and unmarked) —
        # a declared blind spot, so a clean result here is deliberate.
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "The run timed out before it finished. How should it continue?"\n'
            '  options:\n'
            '    - label: "Stop"\n'
            '      description: "Discards the partial result and ends the run."\n'
            '    - label: "Retry with more time"\n'
            '      description: "Runs again with the limit raised to ten minutes."\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])

    def test_contextless_question_produces_nothing(self, tmp_path):
        # Obligation 4 violated (the question states nothing already known) —
        # the second declared blind spot.
        _make_skill_doc(
            tmp_path,
            'AskUserQuestion:\n'
            '  question: "What type of plan for this task?"\n'
            '  options:\n'
            '    - label: "Simple"\n'
            '      description: "Ends as soon as the change is made."\n'
            '    - label: "Verified"\n'
            '      description: "Runs a build over the change before it ships."\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])


# ---------------------------------------------------------------------------
# Invocation-shape matching — prose and bare headers are not invocations
# ---------------------------------------------------------------------------


class TestInvocationShape:
    def test_prose_mention_not_flagged(self, tmp_path):
        # Carries violating vocabulary on purpose: the recognizer, not the
        # vocabulary, is what keeps prose out of scope.
        _make_skill_doc(
            tmp_path,
            '# Fixture\n\n'
            'Per Step 7 the orchestrator fires an AskUserQuestion multiSelect here.\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])

    def test_bare_header_without_block_body_not_flagged(self, tmp_path):
        _make_skill_doc(
            tmp_path,
            '# Fixture\n\nAskUserQuestion:\n\nPer Step 7 a multiSelect is raised.\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])

    def test_sibling_subkey_at_header_indent_not_flagged(self, tmp_path):
        # The sub-key sits at the header's own indentation, so it is OUTSIDE the
        # block _block_body extracts. Carries violating vocabulary on purpose:
        # the indent boundary, not the vocabulary, is what keeps it out of scope.
        _make_skill_doc(
            tmp_path,
            '# Fixture\n\nAskUserQuestion:\nquestion: "Per Step 7, pick a multiSelect"\n',
        )
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])

    def test_sibling_subkey_block_does_not_inflate_population(self, tmp_path):
        # The regression this pins: a sibling sub-key once CONFIRMED the header
        # while _block_body excluded it, so the header counted into
        # population_size with an empty body — a block reported as examined that
        # no check ever saw.
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK, skill='offender')
        _make_skill_doc(
            tmp_path,
            '# Fixture\n\nAskUserQuestion:\nquestion: "Per Step 7, pick a multiSelect"\n',
            skill='sibling',
        )
        findings = analyze_askuserquestion_prompt_quality(tmp_path)
        assert findings
        assert {f['population_size'] for f in findings} == {1}

    def test_empty_tree_is_clean(self, tmp_path):
        assert_analyzer_findings(analyze_askuserquestion_prompt_quality, tmp_path, [])


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_finding_carries_every_required_field(self, tmp_path):
        md = _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK)
        finding = analyze_askuserquestion_prompt_quality(tmp_path)[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == FINDING_TYPE
        assert finding['rule'] == RULE_NAME
        assert finding['file'] == str(md)
        assert isinstance(finding['line'], int) and finding['line'] > 0
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['description']
        assert len(finding['snippet']) <= 80

    def test_population_size_counts_examined_invocation_blocks(self, tmp_path):
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _API_SHERIFF_BLOCK, skill='offender')
        _make_skill_doc(tmp_path, '# Fixture\n\n' + _CONFORMANT_BLOCK, skill='clean')
        findings = analyze_askuserquestion_prompt_quality(tmp_path)
        assert findings
        # Both blocks were examined, including the one that produced nothing.
        assert {f['population_size'] for f in findings} == {2}


# ---------------------------------------------------------------------------
# Registry / provenance
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
