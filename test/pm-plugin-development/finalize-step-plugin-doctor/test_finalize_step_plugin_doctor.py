# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for finalize-step-plugin-doctor skill directory extraction logic.

The finalize-step-plugin-doctor wrapper derives its gate scope from two reads —
the plan's realized footprint (``manage-references compute-footprint``) united
with the declared ``affected_files`` list — extracts skill directory paths from
that union, and passes them to ``plugin-doctor quality-gate --paths``.

Since the wrapper is a SKILL.md (not a Python script), this module validates the
documented derivation as pure Python functions: the regex extraction patterns
identify and deduplicate skill directories from file paths, the union keeps a
declared-but-untouched directory in scope, and the F1 whole-tree trigger is
evaluated against the union rather than against either list alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import PROJECT_ROOT, get_skill_dir

_MARKETPLACE_PATTERN = re.compile(r'marketplace/bundles/[^/]+/skills/[^/]+')
_PROJECT_LOCAL_PATTERN = re.compile(r'\.claude/skills/[^/]+')

_WRAPPER_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-plugin-doctor' / 'SKILL.md'

# The planning-workflow docs whose documentation_only Verification citations
# use the scopeable `quality-gate --paths ... --marketplace-root` gate.
#
# phase-5-execute/SKILL.md is intentionally excluded: per ADR-004 documentation
# has no build owner, so the phase-5 derived ladder classifies a marketplace
# skill `.md` change to `none` (zero rungs) rather than a `docs-validate` rung
# that ran the plugin-doctor gate. phase-5-execute therefore no longer cites the
# `quality-gate --paths ... --marketplace-root` doc gate.
_PHASE_3_OUTLINE_DIR = get_skill_dir('plan-marshall', 'phase-3-outline')
_PLANNING_DOCS = (
    _PHASE_3_OUTLINE_DIR / 'standards' / 'outline-workflow-detail.md',
    _PHASE_3_OUTLINE_DIR / 'SKILL.md',
)

# default:push resolves to order 11 in the phase-6-finalize seed; the
# wrapper MUST gate before it.
_PUSH_ORDER = 11


def _read_frontmatter_order(skill_md: Path) -> int:
    """Parse the integer `order:` field from a SKILL.md YAML frontmatter block."""
    content = skill_md.read_text(encoding='utf-8')
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    assert fm_match, f'No YAML frontmatter found in {skill_md}'
    order_match = re.search(r'^order:\s*(\d+)\s*$', fm_match.group(1), re.MULTILINE)
    assert order_match, f'No `order:` field in {skill_md} frontmatter'
    return int(order_match.group(1))


def _step5_gate_block(content: str) -> str:
    """Return the Step 5 gate block of the wrapper SKILL.md.

    Anchored from the `### Step 5` heading to the next `## ` (or `### Step`)
    heading so an enumeration mention elsewhere in the doc cannot false-trip
    the gate-operation assertions.
    """
    start = content.find('### Step 5')
    assert start != -1, 'Wrapper SKILL.md should declare a Step 5 gate section'
    rest = content[start + len('### Step 5') :]
    end_candidates = [pos for pos in (rest.find('\n## '), rest.find('\n### Step 6')) if pos != -1]
    end = min(end_candidates) if end_candidates else len(rest)
    return rest[:end]


def extract_skill_dirs(modified_files: list[str]) -> list[str]:
    """Extract unique skill directory paths from a list of modified files.

    Applies two regex patterns:
    - ``marketplace/bundles/{bundle}/skills/{skill}`` for marketplace skills
    - ``.claude/skills/{skill}`` for project-local skills

    Returns a sorted, deduplicated list of skill directory paths.
    """
    dirs: set[str] = set()
    for path in modified_files:
        m = _MARKETPLACE_PATTERN.search(path)
        if m:
            dirs.add(m.group(0))
            continue
        m = _PROJECT_LOCAL_PATTERN.search(path)
        if m:
            dirs.add(m.group(0))
    return sorted(dirs)


# The F1 whole-tree trigger: a changed plugin-doctor / plan-doctor analyzer or
# rule script re-classifies skills the diff never touched.
_F1_TRIGGER_PREFIXES = (
    'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/',
    'marketplace/bundles/plan-marshall/skills/plan-doctor/',
)


def gate_scope(realized_footprint: list[str], declared_files: list[str]) -> list[str]:
    """Return the wrapper's gate scope: realized footprint ∪ declared files.

    Mirrors Step 1 of the wrapper document. Both operands are required — the
    documented indeterminate branch covers a failed read, which is not modelled
    here because a missing operand yields no union at all.
    """
    return sorted(set(realized_footprint) | set(declared_files))


def f1_trigger_fires(scope: list[str]) -> bool:
    """Return whether the scope touches a plugin-doctor / plan-doctor rule script."""
    return any(path.startswith(_F1_TRIGGER_PREFIXES) for path in scope)


def _step1_scope_block(content: str) -> str:
    """Return the Step 1 section of the wrapper SKILL.md, up to the Step 2 heading."""
    start = content.find('### Step 1')
    assert start != -1, 'Wrapper SKILL.md should declare a Step 1 scope section'
    end = content.find('\n### Step 2', start)
    assert end != -1, 'Wrapper SKILL.md should declare a Step 2 section after Step 1'
    return content[start:end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMarketplaceSkillChanges:
    """Scenario 1: modified_files containing only marketplace skill paths."""

    def test_extracts_skill_dirs_from_marketplace_paths(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/pm-dev-java/skills/bar/standards/x.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            'marketplace/bundles/plan-marshall/skills/foo',
            'marketplace/bundles/pm-dev-java/skills/bar',
        ]


class TestProjectLocalSkillChanges:
    """Scenario 2: modified_files containing only project-local skill paths."""

    def test_extracts_skill_dirs_from_project_local_paths(self):
        modified_files = [
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
        ]


class TestMixedSkillChanges:
    """Scenario 3: both marketplace and project-local skill paths."""

    def test_extracts_both_marketplace_and_project_local(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md',
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
            'marketplace/bundles/pm-dev-java/skills/junit-core/standards/patterns.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
            'marketplace/bundles/plan-marshall/skills/phase-5-execute',
            'marketplace/bundles/pm-dev-java/skills/junit-core',
        ]


class TestNoSkillChanges:
    """Scenario 4: modified_files with no skill-related paths."""

    def test_returns_empty_for_non_skill_paths(self):
        modified_files = [
            'test/foo.py',
            '.plan/marshal.json',
            'README.md',
            'marketplace/bundles/plan-marshall/README.md',
            'marketplace/bundles/plan-marshall/agents/some-agent.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == []


class TestDeduplication:
    """Scenario 5: multiple files in the same skill directory."""

    def test_deduplicates_same_skill_dir(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/foo/standards/bar.md',
            'marketplace/bundles/plan-marshall/skills/foo/scripts/baz.py',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            'marketplace/bundles/plan-marshall/skills/foo',
        ]

    def test_deduplicates_project_local_same_dir(self):
        modified_files = [
            '.claude/skills/my-skill/SKILL.md',
            '.claude/skills/my-skill/standards/rules.md',
        ]
        result = extract_skill_dirs(modified_files)
        assert result == [
            '.claude/skills/my-skill',
        ]


# ---------------------------------------------------------------------------
# Gate scope: realized footprint united with the declared list
# ---------------------------------------------------------------------------


class TestGateScopeUnion:
    """The gate covers what the plan changed AND what it declared."""

    def test_union_gates_declared_and_realized_skill_dirs(self):
        # Arrange
        declared_files = [
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md',
        ]
        realized_footprint = [
            '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
        ]

        # Act
        result = extract_skill_dirs(gate_scope(realized_footprint, declared_files))

        # Assert
        assert result == [
            '.claude/skills/finalize-step-plugin-doctor',
            'marketplace/bundles/plan-marshall/skills/extension-api',
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize',
        ]

    def test_declared_list_alone_misses_the_realized_only_skill_dir(self):
        """Negative control: the pre-union scope does not contain the third directory."""
        # Arrange
        declared_files = [
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md',
        ]

        # Act
        result = extract_skill_dirs(declared_files)

        # Assert
        assert '.claude/skills/finalize-step-plugin-doctor' not in result
        assert len(result) == 2

    def test_union_deduplicates_a_path_present_in_both_reads(self):
        # Arrange
        shared = 'marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md'

        # Act
        result = gate_scope([shared], [shared])

        # Assert
        assert result == [shared]


class TestF1TriggerOverUnion:
    """The F1 whole-tree trigger is evaluated against the union."""

    def test_trigger_fires_when_rule_script_is_in_realized_set_only(self):
        # Arrange
        declared_files = ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md']
        realized_footprint = [
            'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py',
        ]

        # Act
        fires_on_union = f1_trigger_fires(gate_scope(realized_footprint, declared_files))
        fires_on_declared_alone = f1_trigger_fires(declared_files)

        # Assert
        assert fires_on_union
        assert not fires_on_declared_alone

    def test_trigger_fires_for_plan_doctor_path(self):
        # Arrange
        scope = gate_scope(['marketplace/bundles/plan-marshall/skills/plan-doctor/scripts/plan_doctor.py'], [])

        # Act / Assert
        assert f1_trigger_fires(scope)

    def test_trigger_does_not_fire_without_a_rule_script(self):
        # Arrange
        scope = gate_scope(
            ['.claude/skills/finalize-step-plugin-doctor/SKILL.md'],
            ['marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md'],
        )

        # Act / Assert
        assert not f1_trigger_fires(scope)


class TestStep1NamesBothReads:
    """Step 1 of the wrapper document names both reads and their union."""

    def test_step1_names_compute_footprint_with_both_flags(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert 'manage-references compute-footprint' in block
        assert '--plan-id {plan_id} --worktree-path {worktree_path}' in block

    def test_step1_names_the_declared_affected_files_read(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert '--field affected_files' in block

    def test_step1_states_the_scope_is_the_union(self):
        # Arrange
        block = _step1_scope_block(_WRAPPER_SKILL_MD.read_text(encoding='utf-8'))

        # Assert
        assert 'union' in block, 'Step 1 must state that the gate scope is the union of the two reads'

    def test_f1_trigger_and_skip_clean_are_stated_against_the_union(self):
        # Arrange
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        step_2_5 = content[content.find('### Step 2.5') : content.find('### Step 3')]
        step_3 = content[content.find('### Step 3') : content.find('### Step 4')]

        # Assert
        assert step_2_5 and step_3, 'Steps 2.5 and 3 must both be locatable in the wrapper document'
        assert 'Step 1 union' in step_2_5, 'the F1 trigger must be evaluated against the Step 1 union'
        assert 'union' in step_3, 'the skip-clean exit must be stated against the union'


# ---------------------------------------------------------------------------
# Scopeable rule-running gate + ordering regression (D7)
# ---------------------------------------------------------------------------


class TestRuleRunningScopeableGate:
    """The wrapper's Step 5 gate uses the scopeable rule-running quality-gate."""

    def test_step5_uses_quality_gate_with_paths_and_marketplace_root(self):
        """Step 5 invokes `quality-gate` with both `--paths` and `--marketplace-root`."""
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        block = _step5_gate_block(content)
        assert 'quality-gate' in block, 'Step 5 must invoke the quality-gate verb'
        assert '--paths' in block, 'Step 5 quality-gate must scope via --paths'
        assert '--marketplace-root' in block, 'Step 5 quality-gate must pass --marketplace-root'

    def test_step5_does_not_use_noop_enumerate_verb_as_gate(self):
        """Step 5 does NOT use the rule-less `scan`/`list-components` as the gate."""
        content = _WRAPPER_SKILL_MD.read_text(encoding='utf-8')
        block = _step5_gate_block(content)
        # The gate operation must be quality-gate, never a bare enumerate verb.
        assert 'doctor-marketplace \\\n  scan' not in block and 'doctor-marketplace scan' not in block, (
            'Step 5 must not use the rule-less `scan` subcommand as the gate'
        )
        assert 'list-components --paths' not in block, 'Step 5 must not use the rule-less `list-components` as the gate'


class TestGateOrderingBeforePush:
    """The wrapper is ordered before default:push (order 11)."""

    def test_order_strictly_precedes_push(self):
        order = _read_frontmatter_order(_WRAPPER_SKILL_MD)
        assert order < _PUSH_ORDER, (
            f'finalize-step-plugin-doctor order={order} must be < default:push '
            f'order={_PUSH_ORDER} so structural lint gates before push'
        )


class TestPlanningDocCitations:
    """The planning-workflow docs cite the scopeable rule-running gate, not bare scan."""

    def test_no_bare_scan_paths_documentation_verification_citation(self):
        """No planning doc cites `doctor-marketplace scan --paths` as a verification gate."""
        for doc in _PLANNING_DOCS:
            content = doc.read_text(encoding='utf-8')
            assert 'doctor-marketplace scan --paths' not in content, (
                f'{doc} still cites the rule-less `scan --paths` as a verification gate'
            )
            assert 'doctor-marketplace list-components --paths' not in content, (
                f'{doc} cites `list-components --paths` as a verification gate (rule-less enumerate verb)'
            )

    def test_corrected_quality_gate_paths_shape_present(self):
        """Each planning doc cites the corrected `quality-gate --paths ... --marketplace-root` shape."""
        for doc in _PLANNING_DOCS:
            content = doc.read_text(encoding='utf-8')
            assert 'quality-gate --paths' in content and '--marketplace-root' in content, (
                f'{doc} should cite the scopeable `quality-gate --paths ... --marketplace-root` gate'
            )
