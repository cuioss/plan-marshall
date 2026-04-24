"""Tests for finalize-step-regenerate-executor filter logic.

The finalize-step-regenerate-executor wrapper reads ``references.modified_files``
and filters for marketplace script additions before invoking the executor
generator. Since the wrapper is a SKILL.md (not a Python script), this module
validates the documented filter regex as a pure Python function, ensuring the
pattern correctly matches direct-children .py files under
``marketplace/bundles/{bundle}/skills/{skill}/scripts/`` and excludes everything
else (docs, nested subdirectories, project-local skills, .plan/ config).
"""

from __future__ import annotations

import re

_SCRIPT_ADDITION_PATTERN = re.compile(
    r'^marketplace/bundles/[^/]+/skills/[^/]+/scripts/[^/]+\.py$'
)


def filter_marketplace_scripts(modified_files: list[str]) -> list[str]:
    """Return unique marketplace script paths that warrant executor regeneration.

    Applies the documented regex:
    ``^marketplace/bundles/{bundle}/skills/{skill}/scripts/{name}.py$``

    Files in nested subdirectories of ``scripts/`` (for example
    ``script-shared/scripts/build/foo.py``) are intentionally excluded — they
    contain importable modules rather than new user-facing notations, and are
    covered by ``_ALL_SCRIPT_DIRS`` at PYTHONPATH level.

    Returns a sorted, deduplicated list.
    """
    matches: set[str] = set()
    for path in modified_files:
        if _SCRIPT_ADDITION_PATTERN.match(path):
            matches.add(path)
    return sorted(matches)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSkipWhenNoScriptsInModifiedFiles:
    """Scenario: modified_files contains no qualifying marketplace script paths.

    The wrapper must skip generator invocation — validated here by confirming
    the filter returns an empty list for non-script paths.
    """

    def test_empty_modified_files_returns_empty(self):
        assert filter_marketplace_scripts([]) == []

    def test_docs_and_config_are_filtered_out(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/foo/standards/rule.md',
            '.plan/marshal.json',
            '.claude/skills/some-skill/SKILL.md',
            'README.md',
            'test/plan-marshall/foo/test_bar.py',
        ]
        assert filter_marketplace_scripts(modified_files) == []

    def test_nested_subdirectory_scripts_are_excluded(self):
        """Files under nested subdirs (e.g. script-shared/scripts/build/) must
        NOT trigger regeneration — they expose importable modules, not
        user-facing notations."""
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/resolve_commands.py',
            'marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/look.py',
        ]
        assert filter_marketplace_scripts(modified_files) == []

    def test_agents_and_commands_are_filtered_out(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/agents/some-agent.md',
            'marketplace/bundles/plan-marshall/commands/some-command.md',
            'marketplace/bundles/plan-marshall/.claude-plugin/plugin.json',
        ]
        assert filter_marketplace_scripts(modified_files) == []


class TestInvokeGeneratorWhenScriptsModified:
    """Scenario: modified_files contains at least one qualifying script path.

    The wrapper must invoke ``generate_executor generate`` — validated here by
    confirming the filter surfaces those paths.
    """

    def test_single_added_script_is_detected(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/direct-gh-glab-usage.py',
        ]
        assert filter_marketplace_scripts(modified_files) == [
            'marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/direct-gh-glab-usage.py',
        ]

    def test_multiple_scripts_across_bundles_are_detected(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py',
            'marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/scripts/manage-maven-profiles.py',
        ]
        result = filter_marketplace_scripts(modified_files)
        assert result == [
            'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage-tasks.py',
            'marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/scripts/manage-maven-profiles.py',
        ]

    def test_mixed_scripts_and_non_scripts_surfaces_only_scripts(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/SKILL.md',
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
            'marketplace/bundles/plan-marshall/skills/foo/standards/foo-rules.md',
            'test/plan-marshall/foo/test_foo.py',
        ]
        assert filter_marketplace_scripts(modified_files) == [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
        ]

    def test_modified_existing_script_still_triggers_regen(self):
        """Any change (add or modify) under the pattern qualifies; the
        generator is idempotent so false positives are harmless."""
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage_status.py',
        ]
        assert filter_marketplace_scripts(modified_files) == [
            'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage_status.py',
        ]


class TestNonPythonFilesIgnored:
    """Scenario: scripts dir contains non-.py helpers that must not trigger."""

    def test_shell_scripts_are_ignored(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/helper.sh',
        ]
        assert filter_marketplace_scripts(modified_files) == []

    def test_json_artifacts_are_ignored(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/config.json',
        ]
        assert filter_marketplace_scripts(modified_files) == []


class TestIdempotencyAndDeduplication:
    """Scenario: repeated invocation / duplicate entries must not multiply work."""

    def test_duplicate_entries_are_deduplicated(self):
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
        ]
        assert filter_marketplace_scripts(modified_files) == [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
        ]

    def test_filter_is_pure_function(self):
        """Calling the filter twice with identical input yields identical
        output — this is the correctness invariant that backs the wrapper's
        idempotency. The generator itself is idempotent: running it on the
        same mappings produces the same file content."""
        modified_files = [
            'marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py',
            'marketplace/bundles/pm-dev-java/skills/bar/scripts/bar.py',
        ]
        first = filter_marketplace_scripts(modified_files)
        second = filter_marketplace_scripts(modified_files)
        assert first == second


class TestNoRegenForProjectLocalSkills:
    """Scenario: project-local ``.claude/skills/`` changes must NOT trigger
    executor regeneration.

    Project skills are invoked by name (``project:``) — they are not registered
    in the executor mapping table, so adding or modifying them has no bearing
    on the mapping and does not warrant regeneration.
    """

    def test_project_local_script_is_ignored(self):
        modified_files = [
            '.claude/skills/finalize-step-regenerate-executor/SKILL.md',
            '.claude/skills/my-project-skill/scripts/foo.py',
        ]
        assert filter_marketplace_scripts(modified_files) == []
