# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``thinking-directive-in-workflow-doc`` rule analyzer.

The analyzer (`analyze_thinking_directive_in_workflow_docs`) is a pure,
regex-driven static scanner that detects in-prose directives instructing the
model to adopt a reasoning *level* or narrate a reasoning *process* inside
dispatched workflow docs. The population is DERIVED from each doc's
``implements: …ext-point-execution-context-workflow`` frontmatter — every
``SKILL.md`` / ``workflow/*.md`` under ``marketplace/bundles/*/skills/*/`` that
declares the ext-point — never a hardcoded path list.

Why the directive is a defect: model and effort are pinned by the dispatched
``execution-context-{level}`` variant filename, so an in-doc reasoning-level
directive is inert (the *vacuous guard* archetype).

Test layers:
  * (a) Positive — each of the six directive families fires, and the five
        real directives removed by the plan's D1 fire.
  * (b) Negative — procedural sequencing prose, the "careful analysis" review
        label, "step-by-step workflow/analysis", and checklists do NOT fire.
        The false-positive boundary is the load-bearing half.
  * (c) Population derivation — only docs declaring the ext-point are scanned;
        a directive in a non-declaring doc is invisible.
  * (d) Structural exemptions — frontmatter, fenced code, and inline-code
        spans are exempt.
  * (e) Population-size publication — every finding carries the roster size.
  * (f) Empty-population anti-vacuity guard — an empty population fires ONLY
        when the ext-point is defined in the tree; a minimal tree is clean.
  * (g) Finding shape.
  * (h) Real-marketplace — the population is non-empty (a floor), and the real
        tree produces zero findings (the D1 + D2 regression anchor).
"""

from pathlib import Path

import pytest
from conftest import MARKETPLACE_ROOT, load_script_module
from _fixtures import assert_analyzer_findings


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_mod = _load_module(
    '_analyze_thinking_directive_in_workflow_docs',
    '_analyze_thinking_directive_in_workflow_docs.py',
)

analyze = _mod.analyze_thinking_directive_in_workflow_docs
enumerate_docs = _mod.enumerate_execution_context_workflow_docs
RULE_ID = _mod.RULE_ID
RULE_NAME = _mod.RULE_NAME
FINDING_TYPE = _mod.FINDING_TYPE
EMPTY_POPULATION_TYPE = _mod.EMPTY_POPULATION_TYPE
EXT_POINT = _mod.EXT_POINT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_doc(
    root: Path,
    body: str,
    *,
    bundle: str = 'plan-marshall',
    skill: str = 'fixture-skill',
    name: str = 'x.md',
    subdir: str = 'workflow',
    implements: str | None = EXT_POINT,
) -> Path:
    """Materialize a workflow doc (or SKILL.md) under a scratch bundles root.

    ``root`` is treated as the bundles root the analyzer walks. When
    ``implements`` is set the doc declares that ext-point in its frontmatter;
    ``None`` writes a doc with no ``implements:`` key (out of population).
    """
    if subdir == 'SKILL':
        target = root / bundle / 'skills' / skill / 'SKILL.md'
    else:
        target = root / bundle / 'skills' / skill / subdir / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if implements is not None:
        content = f'---\nimplements: {implements}\n---\n\n# Fixture\n\n{body}\n'
    else:
        content = f'# Fixture\n\n{body}\n'
    target.write_text(content, encoding='utf-8')
    return target


def _write_ext_point_anchor(root: Path) -> None:
    """Create the ext-point standard doc — the empty-population guard's anchor."""
    anchor = (
        root / 'plan-marshall' / 'skills' / 'extension-api' / 'standards' / 'ext-point-execution-context-workflow.md'
    )
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text('# Extension Point: Execution-Context Workflow\n', encoding='utf-8')


# ===========================================================================
# (a) Positive — each family fires; the five D1 directives fire
# ===========================================================================


class TestPositive:
    """Each directive family, and each real removed directive, is flagged."""

    @pytest.mark.parametrize(
        'body, family',
        [
            ('Use **ultrathink mode** for deep analysis and synthesis.', 'ultrathink'),
            ('Enable ultrathink for the synthesis step.', 'ultrathink'),
            ('Use extended thinking for this analysis.', 'extended-thinking'),
            ('Uses careful step-by-step reasoning for tone analysis.', 'careful-reasoning'),
            ('Reason carefully about each claim.', 'careful-reasoning'),
            ('Think step by step before deciding.', 'step-by-step-reasoning'),
            ('Apply step-by-step reasoning to the constraints.', 'step-by-step-reasoning'),
            ('Think carefully about the trade-offs.', 'think-imperative'),
            ('Think deeply about the edge cases.', 'think-imperative'),
            ('Please take your time and be thorough.', 'take-your-time'),
        ],
    )
    def test_family_fires(self, tmp_path: Path, body: str, family: str) -> None:
        doc = _write_doc(tmp_path, body)

        findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])

        assert findings[0]['file'] == str(doc)
        assert findings[0]['details']['family'] == family

    @pytest.mark.parametrize(
        'body',
        [
            # The three ultrathink directives removed from research-best-practices.md.
            'Use **ultrathink mode** for deep analysis and synthesis of research findings.',
            'consider using ultrathink to formulate the most effective search query strategy',
            'use ultrathink at the start of this step for comprehensive analysis.',
            # The two directives removed from content-review.md.
            'Uses careful step-by-step reasoning for tone and style analysis.',
            'Use careful step-by-step reasoning for comprehensive tone assessment',
        ],
    )
    def test_removed_d1_directives_fire(self, tmp_path: Path, body: str) -> None:
        """Mutation guard: the exact prose D1 removed is detected."""
        _write_doc(tmp_path, body)

        assert_analyzer_findings(analyze, tmp_path, [RULE_ID])

    def test_skill_md_target_is_scanned(self, tmp_path: Path) -> None:
        """A SKILL.md declaring the ext-point is in the population."""
        _write_doc(tmp_path, 'Use ultrathink mode here.', subdir='SKILL')

        assert_analyzer_findings(analyze, tmp_path, [RULE_ID])

    def test_live_directive_after_inline_code_mention_fires(self, tmp_path: Path) -> None:
        """A live directive later on a line whose first match is in inline code
        is still caught — ``search`` would have stopped at the in-code mention."""
        _write_doc(tmp_path, 'Mention `ultrathink`, then use ultrathink mode.')

        findings = assert_analyzer_findings(analyze, tmp_path, [RULE_ID])

        assert findings[0]['details']['family'] == 'ultrathink'


# ===========================================================================
# (b) Negative — the false-positive boundary
# ===========================================================================


class TestNegativeBoundary:
    """Procedural sequencing prose and review-methodology labels do NOT fire."""

    @pytest.mark.parametrize(
        'body',
        [
            'Step-by-step workflow for creating a solution outline.',
            'Follow the process step by step to completion.',
            'Apply the careful analysis decision framework to script findings.',
            'This is the Careful Analysis Application section.',
            'Perform a step-by-step analysis of the data.',
            'Read the phrase in isolation, then flag it for review.',
            'Check for contradictions and conflicts across sources.',
            'Consider the context to determine if the contradiction is real.',
            'The dispatcher retries three times before escalating.',
            'This framework distinguishes factual descriptions from promotional language.',
            # Descriptive (non-directive) mentions of the bare-term families: a
            # statement ABOUT the feature is not an instruction to use it.
            'Extended thinking is configured by the dispatcher.',
            'The ultrathink feature is documented elsewhere.',
            # A cue in an unrelated clause on the same line must not bind to the
            # term across the clause boundary.
            'Use the search tool; ultrathink is documented below.',
        ],
    )
    def test_procedural_prose_does_not_fire(self, tmp_path: Path, body: str) -> None:
        _write_doc(tmp_path, body)

        assert_analyzer_findings(analyze, tmp_path, [])


# ===========================================================================
# (c) Population derivation — only ext-point docs are scanned
# ===========================================================================


class TestPopulationDerivation:
    """The population is derived from the ext-point frontmatter declaration."""

    def test_doc_without_ext_point_is_out_of_population(self, tmp_path: Path) -> None:
        # Same directive, but the doc declares no ext-point → not scanned.
        _write_doc(tmp_path, 'Use ultrathink mode here.', implements=None)

        assert analyze(tmp_path) == []

    def test_doc_with_other_ext_point_is_out_of_population(self, tmp_path: Path) -> None:
        _write_doc(
            tmp_path,
            'Use ultrathink mode here.',
            implements='plan-marshall:extension-api/standards/ext-point-finalize-step',
        )

        assert analyze(tmp_path) == []

    def test_enumerate_finds_both_surfaces(self, tmp_path: Path) -> None:
        _write_doc(tmp_path, 'clean body', skill='s-one', subdir='SKILL')
        _write_doc(tmp_path, 'clean body', skill='s-two', name='wf.md')
        _write_doc(tmp_path, 'clean body', skill='s-three', implements=None)

        population = enumerate_docs(tmp_path)

        rels = {str(p.relative_to(tmp_path)) for p in population}
        assert rels == {
            'plan-marshall/skills/s-one/SKILL.md',
            'plan-marshall/skills/s-two/workflow/wf.md',
        }

    def test_block_sequence_implements_is_recognized(self, tmp_path: Path) -> None:
        """A block-sequence ``implements:`` list containing the ext-point counts."""
        target = tmp_path / 'plan-marshall' / 'skills' / 'multi' / 'workflow' / 'x.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '---\n'
            'implements:\n'
            '  - plan-marshall:extension-api/standards/ext-point-finalize-step\n'
            f'  - {EXT_POINT}\n'
            '---\n\n'
            '# F\n\nUse ultrathink mode here.\n',
            encoding='utf-8',
        )

        assert_analyzer_findings(analyze, tmp_path, [RULE_ID])


# ===========================================================================
# (d) Structural exemptions
# ===========================================================================


class TestExemptions:
    """Frontmatter, fenced code, and inline-code spans are exempt."""

    def test_fenced_code_block_is_exempt(self, tmp_path: Path) -> None:
        _write_doc(tmp_path, '```text\nUse ultrathink mode here.\n```')

        assert analyze(tmp_path) == []

    def test_tilde_fence_is_exempt(self, tmp_path: Path) -> None:
        """A directive inside a ``~~~`` fence is exempt, not just a backtick one."""
        _write_doc(tmp_path, '~~~\nUse ultrathink mode here.\n~~~')

        assert analyze(tmp_path) == []

    def test_four_backtick_fence_is_exempt(self, tmp_path: Path) -> None:
        """A fence of more than three backticks is still a fence."""
        _write_doc(tmp_path, '````\nUse ultrathink mode here.\n````')

        assert analyze(tmp_path) == []

    def test_inline_code_span_is_exempt(self, tmp_path: Path) -> None:
        _write_doc(tmp_path, 'The token `ultrathink` is Claude reasoning jargon.')

        assert analyze(tmp_path) == []

    def test_frontmatter_is_exempt(self, tmp_path: Path) -> None:
        # A directive-looking value inside frontmatter must not fire; the body
        # is clean.
        target = tmp_path / 'plan-marshall' / 'skills' / 's' / 'workflow' / 'x.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f'---\nimplements: {EXT_POINT}\ndescription: use ultrathink mode\n---\n\n# F\n\nOrdinary body prose.\n',
            encoding='utf-8',
        )

        assert analyze(tmp_path) == []


# ===========================================================================
# (e) Population-size publication
# ===========================================================================


def test_population_size_published_in_finding(tmp_path: Path) -> None:
    """Every finding carries the derived population size it examined."""
    _write_doc(tmp_path, 'Use ultrathink mode here.', skill='hit')
    _write_doc(tmp_path, 'clean body', skill='clean-one')
    _write_doc(tmp_path, 'clean body', skill='clean-two')

    findings = analyze(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['population_size'] == len(enumerate_docs(tmp_path))
    assert findings[0]['details']['population_size'] == 3


# ===========================================================================
# (f) Empty-population anti-vacuity guard
# ===========================================================================


class TestEmptyPopulationGuard:
    """An empty population fires ONLY when the ext-point is defined in the tree."""

    def test_defined_ext_point_but_empty_population_fires(self, tmp_path: Path) -> None:
        _write_ext_point_anchor(tmp_path)

        findings = analyze(tmp_path)

        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == EMPTY_POPULATION_TYPE
        assert f['details']['population_size'] == 0
        assert f['details']['reason'] == 'empty_population'

    def test_minimal_tree_without_ext_point_is_clean(self, tmp_path: Path) -> None:
        # No anchor, no population — a legitimate minimal tree, not a defect.
        (tmp_path / 'some-bundle' / 'skills' / 's').mkdir(parents=True)

        assert analyze(tmp_path) == []


# ===========================================================================
# (g) Finding shape
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, 'Use ultrathink mode here.')

    findings = analyze(tmp_path)

    assert len(findings) == 1
    f = findings[0]
    assert f['rule_id'] == RULE_ID
    assert f['type'] == FINDING_TYPE
    assert f['rule'] == RULE_NAME
    assert f['file'] == str(doc)
    assert isinstance(f['line'], int) and f['line'] >= 1
    assert f['severity'] == 'error'
    assert f['fixable'] is False
    assert isinstance(f['message'], str) and f['message']
    assert isinstance(f['snippet'], str) and f['snippet']
    assert set(f['details']) == {'family', 'population_size'}


def test_one_finding_per_line(tmp_path: Path) -> None:
    """A line matching multiple families yields exactly one finding."""
    _write_doc(tmp_path, 'Use careful step-by-step reasoning for the task.')

    findings = analyze(tmp_path)

    assert len(findings) == 1
    # careful-reasoning wins over step-by-step-reasoning (checked first).
    assert findings[0]['details']['family'] == 'careful-reasoning'


# ===========================================================================
# (h) Real-marketplace anchors
# ===========================================================================


def _marketplace_available() -> bool:
    return MARKETPLACE_ROOT.is_dir() and any(MARKETPLACE_ROOT.iterdir())


def test_real_marketplace_population_is_non_empty() -> None:
    """The derived population is non-empty — the anti-vacuity floor.

    If the derivation breaks (frontmatter reader, ext-point constant), this
    fails, so the zero-findings result below can never be a vacuous pass over
    an unread population.
    """
    if not _marketplace_available():
        pytest.skip('Real marketplace not available')

    population = enumerate_docs(MARKETPLACE_ROOT)

    assert len(population) >= 20, (
        f'Derived execution-context-workflow population is {len(population)}, '
        f'expected >= 20 — the population derivation may have broken.'
    )


def test_real_marketplace_tree_produces_zero_findings() -> None:
    """The real bundles tree carries no in-prose reasoning-level directives.

    The D1 + D2 regression anchor: every dispatched workflow doc runs at a
    level pinned by the dispatched variant, so none may instruct the model
    about its own reasoning level.
    """
    if not _marketplace_available():
        pytest.skip('Real marketplace not available')

    findings = analyze(MARKETPLACE_ROOT)

    assert findings == [], (
        f'Found {len(findings)} in-prose reasoning-level directive(s) in the real '
        f'marketplace tree: '
        f'{[(f["file"], f.get("snippet")) for f in findings]}. '
        f'Remove each directive; the level is pinned by the dispatched '
        f'execution-context-{{level}} variant.'
    )
