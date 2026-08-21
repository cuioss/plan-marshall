# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``no-incident-references`` rule analyzer.

The analyzer detects references to specific past plan-marshall PRs/issues used
as narration inside marketplace bundle documents AND scripts — under
``marketplace/bundles/*/{skills,agents,commands}/**/*.{md,py}``.

Test layers:
  * (a) Positive cases — each narration form triggers a finding, on markdown
        AND on python scripts. The positive strings are the EXACT pre-fix
        incident forms plan truthful-signals/130 removed, so a green positive
        suite is the "would have caught the pre-fix tree" evidence.
  * (b) Corrected-mechanism cases — the D3 replacement prose does NOT fire.
        This is the load-bearing negative layer: it proves the rule was built
        for REPLACE (name the mechanism), not DELETE — a rule that fired on the
        corrected prose would push a future author back toward deleting the
        concept.
  * (c) Population cases — the examined file population is derived and asserted
        non-empty over the real marketplace, so a clean verdict over an empty
        set is distinguishable from a clean tree.
  * (d) Skip-context cases — frontmatter, fenced blocks, Source: lines, and
        inline-code (back-ticked) references produce no findings.
  * (e) Per-file frontmatter disable (Granularity-3).
  * (f) Suppression-substrate delegation — the rule ships unconditional (no
        registered exemption prefix), and the shared config predicate returns
        False for every path.
  * (g) Real-marketplace zero-findings invariant — the tree is clean post-D3.
"""

from pathlib import Path

from conftest import PROJECT_ROOT, get_script_path, load_script_module

from _plugin_doctor_fixtures import assert_analyzer_findings

REAL_BUNDLES_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_air = _load_module(
    '_analyze_incident_reference_in_docs',
    '_analyze_incident_reference_in_docs.py',
)

analyze_incident_reference_in_docs = _air.analyze_incident_reference_in_docs
incident_reference_targets = _air.incident_reference_targets
RULE_ID = _air.RULE_ID
_is_allowlisted = _air._is_allowlisted
load_default_suppression_config = _air.load_default_suppression_config


def _make_skill_file(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/skills/{skill}/{filename}`` under ``tmp_path``."""
    skill_dir = tmp_path / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True)
    target = skill_dir / filename
    target.write_text(content, encoding='utf-8')
    return tmp_path, target


# ===========================================================================
# (a) Positive cases — the exact pre-fix incident forms fire
# ===========================================================================


class TestPositiveDetection:
    """Each narration form is flagged (markdown and python)."""

    def test_observed_on_plan_marshall_ref_fires(self, tmp_path: Path) -> None:
        """D5(a): the canonical ``Observed on plan-marshall#NNNN`` narrative fires."""
        content = (
            'Nothing downstream could distinguish reviewed from forced. '
            'Observed on plan-marshall#1045: the fix commit was reviewed by CodeRabbit '
            'and never by the required bot, and the step went done through the hatch.\n'
        )
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])
        assert findings[0]['type'] == 'incident_reference'

    def test_plan_marshall_ref_shape_fires(self, tmp_path: Path) -> None:
        """A ``plan-marshall#NNNN`` reference fires."""
        content = 'A later barrier could merge a tree the operator never saw (the plan-marshall#1067 shape).\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_term_of_art_failure_mode_fires(self, tmp_path: Path) -> None:
        """``the PR #866 failure mode`` (ref bound to an incident noun) fires."""
        content = 'An immediate merge here would close the PR unmerged (the PR #866 failure mode).\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_term_of_art_signature_fires(self, tmp_path: Path) -> None:
        """``the #1081 signature`` fires."""
        content = 'The #1081 signature is exactly a verb that reported a merge that never landed.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_term_of_art_with_hyphenated_qualifier_fires(self, tmp_path: Path) -> None:
        """``the #948 sibling-worktree shape`` (qualifier between ref and noun) fires."""
        content = 'An absent plan under this scope is unknown, not authoritative absence — the #948 sibling-worktree shape.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_reversed_term_of_art_fires(self, tmp_path: Path) -> None:
        """``the failure mode #866`` — the noun BEFORE the reference — fires.

        The shipped term-of-art family required the reference first, so the
        ordering English prose reaches for at least as often passed a rule whose
        own brief named it.
        """
        content = 'This is the failure mode #866 that closed the PR unmerged.\n'
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(
            analyze_incident_reference_in_docs, root, [RULE_ID]
        )
        assert findings[0]['pattern_family'] == 'incident_term_of_art_reversed'

    def test_reversed_term_of_art_with_hyphenated_qualifier_fires(self, tmp_path: Path) -> None:
        """``the shape sibling-worktree #948`` keeps the optional qualifier slot."""
        content = 'An absent plan is unknown here — the shape sibling-worktree #948.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_dated_narration_fires(self, tmp_path: Path) -> None:
        """``As of 2025-10-27:`` pins prose to a moment and fires.

        Prose anchored to a date states when something WAS true rather than what
        IS true — the same provenance-as-normative-prose defect a ``#ref``
        carries, without a reference to carry it.
        """
        content = 'As of 2025-10-27:\n- universal git access is provided.\n'
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(
            analyze_incident_reference_in_docs, root, [RULE_ID]
        )
        assert findings[0]['pattern_family'] == 'dated_narration'

    def test_version_pinned_narration_fires(self, tmp_path: Path) -> None:
        """``since 1.2.3`` pins prose to a release the same way a date does."""
        content = 'The resolver has behaved this way since 1.2.3 was released.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_temporal_pre_narration_fires(self, tmp_path: Path) -> None:
        """``pre-#NNNN`` temporal narration fires."""
        content = 'The pre-#1067 defect: a resolver id appended behind a bare falsiness check with no dedup.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_temporal_post_narration_fires(self, tmp_path: Path) -> None:
        """``post-#NNNN`` temporal narration fires."""
        content = 'The materialized roster is the CURRENT (post-#895/#896/#898) model.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])

    def test_fires_inside_python_script(self, tmp_path: Path) -> None:
        """A python script comment carrying an incident label fires (scripts are in scope)."""
        content = (
            '# This verb merges straight into the #866 signature: on a base branch\n'
            '# with a required queue, an immediate merge closes the PR unmerged.\n'
            'def cmd_pr_merge():\n'
            '    return None\n'
        )
        root, _ = _make_skill_file(tmp_path, content, filename='_github_pr.py')
        findings = assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])
        assert findings[0]['file'].endswith('_github_pr.py')

    def test_bare_ref_after_backticked_ref_on_same_line_fires(self, tmp_path: Path) -> None:
        """A back-ticked reference must NOT mask a bare reference later on the same line.

        Regression for the ``search()``-only scan: the analyzer must iterate all
        matches per family (``finditer``) so a code-token reference early on a
        line does not bypass a real narration reference after it.
        """
        content = 'See `plan-marshall#100` for context, but plan-marshall#101 is the live shape.\n'
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])
        assert findings[0]['snippet'] == 'plan-marshall#101'

    def test_legitimate_version_constraint_is_not_flagged(self, tmp_path: Path) -> None:
        """A version REQUIREMENT is not dated narration.

        The load-bearing negative for the dated-narration family: "requires
        Python 3.12", "Node 20.1.0 or newer" and ">= 1.2.3" all state a
        requirement that holds NOW, not a moment prose is pinned to. The
        temporal preposition is what separates the two, and a family that fired
        on every version number would flag most dependency documentation in the
        tree.
        """
        content = (
            'Requires Python 3.12 or newer.\n'
            'The frontend targets Node 20.1.0.\n'
            'Pin the resolver at >= 1.2.3 in the lockfile.\n'
        )
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_reversed_term_of_art_with_a_backticked_ref_stays_exempt(self, tmp_path: Path) -> None:
        """The inline-code exemption applies to the REVERSED form too.

        The exemption is tested at the ``#NNNN`` inside the match rather than at
        the match's first character — which for this form is the noun, outside
        the backticks. Testing the match start would fire on a back-ticked
        reference, narrowing a convention published across the rule catalogue,
        the provenance table, a named test and a sibling rule.
        """
        content = 'This is the failure mode `#866` that closed the PR unmerged.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Finding carries the expected shape fields."""
        content = 'Observed on plan-marshall#1045: the required bot never reviewed.\n'
        root, target = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])
        f = findings[0]
        assert f['type'] == 'incident_reference'
        assert f['rule'] == 'analyze_incident_reference_in_docs'
        assert f['file'] == str(target)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'warning'
        assert f['fixable'] is False
        assert 'snippet' in f
        assert 'description' in f
        assert 'pattern_family' in f


# ===========================================================================
# (b) Corrected-mechanism cases — the D3 replacement prose does NOT fire
# ===========================================================================


class TestCorrectedMechanismProseNotFlagged:
    """The load-bearing negative layer: the mechanism prose D3 substituted for
    each incident label must NOT fire. A rule that fired here would push a
    future author back toward DELETE — the opposite of the REPLACE arm.
    """

    def test_close_unmerged_failure_mode_not_flagged(self, tmp_path: Path) -> None:
        content = 'An immediate merge here would close the PR unmerged (the close-unmerged failure mode).\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_accepted_not_landed_signature_not_flagged(self, tmp_path: Path) -> None:
        content = 'The accepted-not-landed signature is exactly a verb that reported a merge that never landed.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_sibling_worktree_shape_not_flagged(self, tmp_path: Path) -> None:
        content = 'An absent plan under this scope is unknown, not authoritative absence (the sibling-worktree shape).\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_pre_fix_defect_not_flagged(self, tmp_path: Path) -> None:
        content = 'The pre-fix defect: a resolver id appended behind a bare falsiness check with no dedup.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_unbound_consent_shape_not_flagged(self, tmp_path: Path) -> None:
        content = 'A later barrier could merge a tree the operator never saw (the unbound-consent shape).\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])


# ===========================================================================
# (b') Boundary — genuinely-referential and out-of-scope forms do NOT fire
# ===========================================================================


class TestReferentialAndBoundaryNotFlagged:
    """Forms deliberately left alone: bare provenance, lowercase observation
    records, external-tracker issues, and syntax examples.
    """

    def test_bare_pr_number_without_incident_noun_not_flagged(self, tmp_path: Path) -> None:
        """A bare provenance citation with no incident noun is not narration."""
        content = 'The parsing contract is transcribed verbatim from PR #629 review.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_lowercase_observed_on_not_flagged(self, tmp_path: Path) -> None:
        """A bot data-sheet's lowercase ``observed on #NNNN`` is an observation record."""
        content = 'refusal_patterns:  # EMPTY — no refusal of any kind observed on #103 or #1078.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_external_tracker_issue_not_flagged(self, tmp_path: Path) -> None:
        """An external-project issue reference with no incident noun is not flagged."""
        content = 'OpenCode does not expose a session id (issue #9292); tracked upstream.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_commit_footer_example_not_flagged(self, tmp_path: Path) -> None:
        """A syntax-teaching commit-footer example is not incident narration."""
        content = 'Close the issue when the commit merges with `Fixes #123` in the footer.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_clean_present_tense_prose_no_finding(self, tmp_path: Path) -> None:
        content = 'Route a destructive decision through a main-anchored staleness verdict.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])


# ===========================================================================
# (c) Population — derived and asserted non-empty
# ===========================================================================


class TestPopulationPublished:
    """The examined population is published so a clean verdict over an empty
    set is distinguishable from a clean tree.
    """

    def test_targets_non_empty_over_real_marketplace(self) -> None:
        """D5(c): the derived file population over the real tree is non-empty."""
        targets = incident_reference_targets(REAL_BUNDLES_ROOT)
        assert len(targets) > 0, 'incident_reference_targets must derive a non-empty population'

    def test_targets_include_both_md_and_py(self) -> None:
        """The population spans docs AND scripts."""
        targets = incident_reference_targets(REAL_BUNDLES_ROOT)
        suffixes = {p.suffix for p, _ in targets}
        assert '.md' in suffixes
        assert '.py' in suffixes

    def test_targets_are_bundles_relative_pairs(self, tmp_path: Path) -> None:
        """Each target is an ``(absolute_path, rel_to_bundles)`` pair."""
        _make_skill_file(tmp_path, 'clean prose.\n')
        targets = incident_reference_targets(tmp_path)
        assert targets
        for abs_path, rel in targets:
            assert abs_path.is_absolute()
            assert not rel.startswith('/')

    def test_targets_empty_for_missing_root(self, tmp_path: Path) -> None:
        """A non-existent root yields an empty population, not an error."""
        assert incident_reference_targets(tmp_path / 'does-not-exist') == []

    def test_empty_population_emits_anti_vacuity_finding(self, tmp_path: Path) -> None:
        """An empty derived population is surfaced at runtime, not a silent clean pass.

        This is the runtime half of the anti-vacuity guard (the epic's namesake):
        a clean verdict over an unread population must not read as a clean tree.
        """
        empty_root = tmp_path / 'empty-bundles'
        empty_root.mkdir()
        findings = assert_analyzer_findings(analyze_incident_reference_in_docs, empty_root, [RULE_ID])
        assert findings[0]['pattern_family'] == 'empty_population'
        assert findings[0]['population_size'] == 0


# ===========================================================================
# (d) Skip-context cases
# ===========================================================================


class TestSkipContextExemption:
    """Incident references in structured contexts produce no findings."""

    def test_yaml_frontmatter_is_exempt(self, tmp_path: Path) -> None:
        content = (
            '---\n'
            'name: test\n'
            'note: the #866 failure mode\n'
            '---\n'
            'Normal body content.\n'
        )
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_fenced_code_block_is_exempt(self, tmp_path: Path) -> None:
        content = '```text\nObserved on plan-marshall#1045: inside a code fence.\n```\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_source_line_is_exempt(self, tmp_path: Path) -> None:
        content = 'Source: the #866 failure mode provenance citation.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_backticked_inline_code_ref_is_exempt(self, tmp_path: Path) -> None:
        """A back-ticked ``#NNNN`` reference is a code token, not narration.

        The WHOLE narration phrase is quoted, so the family's match starts
        inside the code span and is skipped. Two earlier framings of this
        fixture were vacuous for different reasons, and both are worth naming:
        "the `#812` end_time-presence check" matched no family at all, and
        "the `#812` failure mode" puts a backtick between the reference and the
        noun, which breaks the pattern before the exemption is ever consulted.
        The paired positive below is the control.
        """
        content = 'The `#812 failure mode` is documented elsewhere.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_the_same_sentence_unquoted_is_flagged(self, tmp_path: Path) -> None:
        """The control for the exemption: without the backticks the rule fires.

        This pair is what makes the exemption test evidence — one sentence, one
        difference, opposite verdicts.
        """
        content = 'The #812 failure mode is documented elsewhere.\n'
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(
            analyze_incident_reference_in_docs, root, [RULE_ID]
        )
        assert findings[0]['pattern_family'] == 'incident_term_of_art'
        assert findings[0]['snippet'] == '#812 failure mode'


# ===========================================================================
# (e) Per-file frontmatter disable (Granularity-3)
# ===========================================================================


class TestFrontmatterDisable:
    """A ``plugin-doctor-disable: [no-incident-references]`` frontmatter key
    suppresses every finding in that file.
    """

    def test_inline_list_disable_suppresses_whole_file(self, tmp_path: Path) -> None:
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable: [no-incident-references]\n'
            '---\n'
            'Observed on plan-marshall#1045: suppressed per-file.\n'
        )
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_disable_list_for_other_rule_does_not_suppress(self, tmp_path: Path) -> None:
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable: [some-other-rule]\n'
            '---\n'
            'Observed on plan-marshall#1045: this rule is NOT in the disable list.\n'
        )
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [RULE_ID])


# ===========================================================================
# (f) Suppression-substrate delegation — unconditional (no registered prefix)
# ===========================================================================


class TestUnconditionalExemptionPosture:
    """The rule ships unconditional: no prefix registered under ``RULE_ID`` in
    the shipped default config, so ``_is_allowlisted`` is False for every path.
    A future maintainer may register a prefix; today the mechanism carries zero
    entries rather than a token unused exemption.
    """

    def test_default_config_carries_no_prefixes_for_rule(self) -> None:
        config = load_default_suppression_config()
        assert config.get(RULE_ID, []) == [], (
            'no-incident-references ships unconditional: it must carry zero exemption prefixes'
        )

    def test_is_allowlisted_false_for_any_path(self) -> None:
        config = load_default_suppression_config()
        assert _is_allowlisted('plan-marshall/skills/manage-locks/SKILL.md', config) is False
        assert _is_allowlisted('pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md', config) is False


# ===========================================================================
# (g) Real-marketplace zero-findings invariant
# ===========================================================================


def test_real_marketplace_has_zero_findings() -> None:
    """After the D3 cleanup, the real marketplace tree carries no incident references.

    A non-empty result names the offending files so a regression is actionable.
    """
    findings = analyze_incident_reference_in_docs(REAL_BUNDLES_ROOT)
    assert findings == [], (
        'Unexpected incident references in the marketplace tree: '
        f'{[(f["file"], f["line"], f["snippet"]) for f in findings]}'
    )


def test_analyzer_is_registered_in_runner() -> None:
    """The analyzer is wired into the runner's quality-gate and analyze passes."""
    runner_source = get_script_path(
        'pm-plugin-development', 'plugin-doctor', '_runner.py'
    ).read_text(encoding='utf-8')
    assert 'analyze_incident_reference_in_docs' in runner_source


class TestBacktickExemptionIsTestedAtTheReference:
    """The inline-code exemption is tested at the REFERENCE, not the match start.

    Four of the six families have a match that begins before the reference, but
    the count is not the discriminator: what decides whether the two offsets can
    land on opposite sides of a code-span boundary is whether the pattern permits
    a backtick BETWEEN them. Two do — ``observed_on`` (up to 80 arbitrary
    characters before the ref) and the reversed term-of-art form. Under a
    match-start test a back-ticked reference still fired in those, making them
    the exceptions to a convention published project-wide.
    """

    def test_observed_on_with_a_backticked_ref_is_exempt(self, tmp_path: Path) -> None:
        """``Observed on … `#812` `` is a code token like every other quoted ref.

        This WIDENED ``observed_on``'s exemption: before the offset change the
        same line fired, making it the one family in which the back-tick
        convention did not hold. Bounded — over the whole derived population
        zero ``observed_on`` lines have a verdict the change flips.
        """
        content = 'Observed on the run log: `#812` was the culprit.\n'
        root, _ = _make_skill_file(tmp_path, content)
        assert_analyzer_findings(analyze_incident_reference_in_docs, root, [])

    def test_observed_on_with_a_bare_ref_still_fires(self, tmp_path: Path) -> None:
        """The control: the exemption widened, it did not disable the family."""
        content = 'Observed on the run log: #812 was the culprit.\n'
        root, _ = _make_skill_file(tmp_path, content)
        findings = assert_analyzer_findings(
            analyze_incident_reference_in_docs, root, [RULE_ID]
        )
        assert findings[0]['pattern_family'] == 'observed_on'


class TestExemptionOffsetMechanism:
    """The offset rule is a property of each PATTERN, not a count of families.

    Pinned because the count is the thing a maintainer adding a seventh family
    would reuse to decide whether theirs is in scope, and the count was twice
    written down wrong.
    """

    def test_four_families_match_before_the_reference(self) -> None:
        """Executed per pattern, not reasoned from the regexes."""
        probes = {
            'plan_marshall_ref': 'See `plan-marshall#123` here.',
            'observed_on': 'Observed on the run log: `#812` was the culprit.',
            'temporal_narration': 'The behaviour changed `post-#900` in the resolver.',
            'incident_term_of_art': 'The `#948 sibling-worktree shape` recurs.',
            'incident_term_of_art_reversed': 'This `failure mode #866` closed the PR.',
            'dated_narration': 'Green `as of 2026-07` on the check.',
        }
        differ = set()
        for name, pattern in _air._PATTERNS:
            match = pattern.search(probes[name])
            assert match is not None, f'{name} does not match its own probe'
            if match.start() != _air._exemption_offset(match):
                differ.add(name)

        assert differ == {
            'plan_marshall_ref',
            'observed_on',
            'temporal_narration',
            'incident_term_of_art_reversed',
        }

    def test_only_two_families_admit_a_backtick_between_start_and_reference(self) -> None:
        """The discriminator: can a code-span boundary fall strictly between them.

        ``plan-marshall#NNNN`` is contiguous, and ``since #``/``post-#``/``pre-#``
        stop matching the moment a backtick is inserted — so for those two the
        offsets always land on the same side of any boundary, however far apart
        they are.
        """
        probes = {
            'plan_marshall_ref': 'See plan-marshall`#123` here.',
            'observed_on': 'Observed on the run log: `#812` was the culprit.',
            'temporal_narration': 'It changed since `#900` landed.',
            'incident_term_of_art_reversed': 'This is the failure mode `#866` we hit.',
        }
        flips = set()
        for name, pattern in _air._PATTERNS:
            if name not in probes:
                continue
            line = probes[name]
            match = pattern.search(line)
            if match is None:
                continue
            spans = _air._inline_code_spans(line)
            if _air._offset_in_inline_code(match.start(), spans) != _air._offset_in_inline_code(
                _air._exemption_offset(match), spans
            ):
                flips.add(name)

        assert flips == {'observed_on', 'incident_term_of_art_reversed'}

    def test_the_change_narrows_as_well_as_widens(self) -> None:
        """A quoted OPENER with a bare reference fires, where it was exempt before.

        Both directions follow from the same rule — the exemption is about the
        reference being a code token — and describing the change as a widening
        alone is half of it.
        """
        line = '`Observed on the run log` shows #812.'
        match = _air._OBSERVED_ON_RE.search(line)
        assert match is not None
        spans = _air._inline_code_spans(line)

        assert _air._offset_in_inline_code(match.start(), spans) is True
        assert _air._offset_in_inline_code(_air._exemption_offset(match), spans) is False
