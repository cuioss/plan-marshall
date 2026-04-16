"""Tests for finalize-step-plugin-doctor skill directory extraction logic.

The finalize-step-plugin-doctor wrapper reads ``references.modified_files``,
extracts skill directory paths, and passes them to ``plugin-doctor scan --paths``.

Since the wrapper is a SKILL.md (not a Python script), this module validates the
documented regex extraction patterns as a pure Python function, ensuring the
patterns correctly identify and deduplicate skill directories from file paths.
"""

from __future__ import annotations

import re

_MARKETPLACE_PATTERN = re.compile(r'marketplace/bundles/[^/]+/skills/[^/]+')
_PROJECT_LOCAL_PATTERN = re.compile(r'\.claude/skills/[^/]+')


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
