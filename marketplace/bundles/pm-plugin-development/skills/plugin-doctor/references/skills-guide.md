# Skill Quality Standards

Skills are knowledge repositories providing standards, workflows, and reusable logic. Invoked via `Skill: bundle:skill-name`.

## Skill Directory Structure

```
skill-name/
├── SKILL.md              (required: frontmatter + workflows)
├── scripts/              (optional: deterministic logic, stdlib-only)
├── references/           (optional: WHAT rules to apply)
├── workflows/            (optional: HOW to execute)
├── templates/            (optional: output templates)
└── assets/               (optional: images, diagrams)
```

Each directory serves one purpose: `references/` = criteria/standards, `workflows/` = procedures/steps, `templates/` = boilerplate with placeholders. Do not mix content types within a directory.

## SKILL.md Frontmatter

```yaml
---
name: skill-name                    # kebab-case, matches directory name
description: One-sentence purpose
user-invokable: true                # true = slash menu, false = internal
---
```

Required fields: `name`, `description`, `user-invokable`.

Skills do **not** support `tools` or `allowed-tools` fields (silently ignored by the plugin schema). Common errors: misspelling `user-invokable` as `user-invocable`, declaring unsupported `allowed-tools` field.

## Progressive Disclosure

Load one reference guide per workflow, not all at once.

**Pattern**: SKILL.md (~800 lines) loads one reference (~500 lines) per workflow = ~1,300 lines per workflow instead of ~3,300 for all.

```markdown
## Workflow 1: First Task
### Step 2: Load Standards
Read references/first-guide.md  # only for this workflow
```

Reference guide target: 400-600 lines each.

## Relative Paths

All internal references use relative paths for portability across installation locations (marketplace, global `~/.claude`, project `.claude`).

- `scripts/script.sh` (correct)
- `references/guide.md` (correct)
- `/Users/.../scripts/script.sh` (wrong — absolute path)
- `marketplace/bundles/.../scripts/script.sh` (wrong — hardcoded install path)

## Structure Score

| Criterion | Points |
|-----------|--------|
| SKILL.md exists | +30 |
| YAML valid | +20 |
| No missing files (referenced but don't exist) | +25 |
| No unreferenced files (exist but not referenced) | +25 |

Target: 100 (perfect). Thresholds: >= 90 Excellent, >= 70 Good, >= 50 Needs improvement, < 50 Poor.

## Standards File Quality

**Minimize-without-loss principle**: remove zero-information content, duplication, ambiguity, and inconsistent formatting while preserving actionable guidance, specific requirements, and technical specifications.

Remove: generic platitudes ("it is important to..."), filler phrases ("as we all know..."), excessive motivation, repeated statements.

Preserve: actionable guidance, specific thresholds, clear examples, technical specs.

## Standards Coherence

For skills with multiple standards files:
- No conflicting requirements (e.g., different thresholds for same rule)
- No coverage gaps (e.g., missing testing standards)
- Consistent terminology across files

## Script Documentation

Skills with scripts document each in SKILL.md: purpose, input, output format (JSON), usage with executor notation.

Scripts must be stdlib-only, have executable permissions, support `--help`, output JSON, handle errors with exit codes.

## Skill Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| Multi-Workflow | Single skill, multiple related workflows | plugin-doctor (9 workflows) |
| Reference Library | Pure reference, no execution logic | plugin-architecture |
| Script Automation | Deterministic validation via scripts | plugin-create |
| Standards | Comprehensive standards with progressive disclosure | cui-java-core |

## Human-Audience Content Separation

Human-targeted content (ASCII diagrams, architecture overviews, motivational text) belongs in companion files (`*-diagrams.md`, `*-overview.md`) with `<!-- audience: human-visual -->` header. SKILL.md references them briefly. Keep inline only decision tables, concrete examples adjacent to rules, and explicit action instructions.

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Missing SKILL.md | Score = 0 | Create with proper frontmatter |
| Invalid YAML | Score = 30 | Fix syntax (colons, indentation, delimiters) |
| Low structure score | Missing/unreferenced files | Create missing files or add references |
| No progressive disclosure | All references loaded upfront | Refactor to per-workflow loading |
| Absolute paths | Hardcoded installation paths | Use relative paths |

## Summary Checklist

- SKILL.md exists with valid YAML frontmatter
- `user-invokable` field present (true or false)
- No `allowed-tools` or `tools` field (unsupported for skills)
- Structure score >= 90
- No missing or unreferenced files
- Progressive disclosure implemented
- Relative paths for all references
- Scripts documented in SKILL.md (if any)
- Standards follow minimize-without-loss principle
- No cross-skill duplication
- Integrated standards coherence (no conflicts or gaps)
