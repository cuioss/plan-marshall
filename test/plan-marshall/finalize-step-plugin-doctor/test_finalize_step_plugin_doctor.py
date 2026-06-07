"""Tests for finalize-step-plugin-doctor skill directory extraction logic.

The finalize-step-plugin-doctor wrapper reads ``references.modified_files``,
extracts skill directory paths, and passes them to ``plugin-doctor scan --paths``.

Since the wrapper is a SKILL.md (not a Python script), this module validates the
documented regex extraction patterns as a pure Python function, ensuring the
patterns correctly identify and deduplicate skill directories from file paths.
"""

from __future__ import annotations

import re
from pathlib import Path

_MARKETPLACE_PATTERN = re.compile(r'marketplace/bundles/[^/]+/skills/[^/]+')
_PROJECT_LOCAL_PATTERN = re.compile(r'\.claude/skills/[^/]+')

# Repo root resolved from this test file:
# test/plan-marshall/finalize-step-plugin-doctor/test_*.py -> repo root is 3 parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_WRAPPER_SKILL_MD = _REPO_ROOT / '.claude' / 'skills' / 'finalize-step-plugin-doctor' / 'SKILL.md'

# The planning-workflow docs whose documentation_only Verification citations
# use the scopeable `quality-gate --paths ... --marketplace-root` gate.
_PLANNING_DOCS = (
    _REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md',
    _REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md',
    _REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md',
)

# default:commit-push resolves to order 10 in the phase-6-finalize seed; the
# wrapper MUST gate before it.
_COMMIT_PUSH_ORDER = 10


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
    rest = content[start + len('### Step 5'):]
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
        assert 'list-components --paths' not in block, (
            'Step 5 must not use the rule-less `list-components` as the gate'
        )


class TestGateOrderingBeforeCommitPush:
    """The wrapper is ordered before default:commit-push (order 10)."""

    def test_order_strictly_precedes_commit_push(self):
        order = _read_frontmatter_order(_WRAPPER_SKILL_MD)
        assert order < _COMMIT_PUSH_ORDER, (
            f'finalize-step-plugin-doctor order={order} must be < default:commit-push '
            f'order={_COMMIT_PUSH_ORDER} so structural lint gates before push'
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
