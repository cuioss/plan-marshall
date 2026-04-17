---
name: skill-with-noun-suffix
description: Fixture whose parent directory ends in -executor to trigger skill-naming-noun-suffix
user-invocable: false
---

# Noun-Suffix Fixture Skill

This fixture exists to exercise the `skill-naming-noun-suffix` rule in
`pm-plugin-development:plugin-doctor`. The enclosing directory is named
`skill-with-noun-suffix` on purpose; tests rename or symlink the parent
directory to reserved-suffix variants (e.g. `something-executor`,
`something-managers`) at fixture-load time and verify that
`analyze_skill_structure` sets `noun_suffix.violation = true`.

The skill itself has no workflow — it only needs a valid SKILL.md so that
structure analysis can progress past the frontmatter check and reach the
naming-convention check.
