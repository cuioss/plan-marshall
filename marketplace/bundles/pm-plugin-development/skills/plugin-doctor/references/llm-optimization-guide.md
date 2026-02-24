# LLM Optimization Guide

Cross-cutting reference for evaluating marketplace components for LLM consumption efficiency. The primary consumer of marketplace skills, agents, and commands is an LLM — content should maximize the LLM's ability to act correctly and minimize token waste.

## High-Value Patterns (keep)

- **Decision tables** — When rules depend on conditions, a table is more reliable than prose. The LLM can index into it.
- **Concrete examples** — One good example communicates faster than three paragraphs of explanation.
- **Explicit constraints** — "Do X, never Y" is unambiguous. Prefer over hedged language.
- **Structured formats** — Frontmatter, labeled sections, consistent heading levels. The LLM can navigate these.
- **Delta-only references** — Standards files that contain only component-specific content, deferring to a common pattern in the parent document.

## Low-Value Patterns (flag)

- **Motivational text** — "This is important because..." / "Following best practices ensures..." Flag if removing it loses zero decision-relevant information.
- **History/changelog** — "We previously used X, but now use Y." Only the current state matters unless migration is ongoing.
- **Redundant emphasis** — Saying the same rule multiple ways for human readers. Once is enough.
- **Obvious checklists** — Items the LLM would do without being told (e.g., "verify the file exists before reading it"). Flag checklists where >50% of items are obvious.
- **Rationale sections** — "Why this standard exists" blocks. Flag only when the rationale doesn't influence the LLM's behavior. Keep when it helps decide edge cases.
- **Verbose examples** — Multiple examples showing the same pattern with minor variations. One example + the rule is sufficient.
- **Duplicated content** — Rules defined in multiple places. Each rule should have a single source of truth with cross-references elsewhere.

## Human-Audience Content Separation

All human-targeted content — verbose descriptions, ASCII diagrams, flowcharts, architecture overviews, motivational prose — belongs in separate companion files (`*-diagrams.md`, `*-overview.md`), not inline. These files use `<!-- audience: human-visual -->` markers. The LLM skips them during execution. See `skills-guide.md` "Human-Audience Content Separation" for the full convention.

## Assessment Criteria

For each flagged section, answer: "If I remove this, would the LLM produce different (worse) output?" If no — it's noise. If yes — keep it but consider whether it could be shorter.

## Token Budget Awareness

A skill loaded into context competes with the actual task content. Every unnecessary line in a skill is a line the LLM can't use for the user's code. Prioritize ruthlessly.

**Guidelines**:
- Skills: Target <400 lines for SKILL.md (standards files separate)
- Commands: Target <100 lines (thin wrapper pattern)
- Agents: Target <300 lines
- Reference guides: Target <200 lines each
