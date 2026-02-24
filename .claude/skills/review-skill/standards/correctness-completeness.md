# Correctness and Completeness Review

## What to look for

**Stale content** — Code examples referencing deprecated APIs, removed flags, or renamed classes. Cross-check tool names, parameter names, and script notations against actual files when possible (Glob/Grep to verify existence).

**Broken references** — File paths, skill names (`bundle:skill`), script notations (`bundle:skill:script`) that point to non-existent targets. Verify with Glob.

**Incomplete guidance** — The skill tells the LLM *what* to do but omits a critical constraint or edge case that would cause incorrect behavior. Look for:
- Rules stated positively ("do X") without the exception ("except when Y")
- Patterns shown without their failure modes
- Workflows missing error/abort paths

**Example quality** — Code examples that would fail if followed literally. Missing imports, wrong method signatures, outdated syntax. Flag only if the example is meant to be copy-pasteable; conceptual illustrations are fine.

**Gap detection** — Compare the skill's stated scope (frontmatter description, "What This Skill Provides") against its actual content. If it claims to cover topic X but no document addresses X, that's a gap.

## What NOT to flag

- Frontmatter correctness (plugin-doctor handles this)
- Missing enforcement blocks (plugin-doctor handles this)
- Whether examples are "best practice" — only flag if they're wrong
