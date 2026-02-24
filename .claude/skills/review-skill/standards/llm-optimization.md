# LLM Optimization Review

The primary consumer of marketplace skills is an LLM. Content should maximize the LLM's ability to act correctly and minimize token waste.

## High-value patterns (keep)

- **Decision tables** — When rules depend on conditions, a table is more reliable than prose. The LLM can index into it.
- **Concrete examples** — One good example communicates faster than three paragraphs of explanation.
- **Explicit constraints** — "Do X, never Y" is unambiguous. Prefer over hedged language.
- **Structured formats** — Frontmatter, labeled sections, consistent heading levels. The LLM can navigate these.

## Low-value patterns (flag)

- **Motivational text** — "This is important because..." / "Following best practices ensures..." The LLM doesn't need persuading. Flag if removing it loses zero decision-relevant information.
- **History/changelog** — "We previously used X, but now use Y." Only the current state matters unless the migration is ongoing.
- **Redundant emphasis** — Saying the same rule three different ways for human readers. Once is enough.
- **Obvious checklists** — Items the LLM would do without being told (e.g., "verify the file exists before reading it"). Flag checklists where >50% of items are obvious. Checklists of non-obvious items ARE valuable — don't flag those.
- **Rationale sections** — "Why this standard exists" blocks. Flag only when the rationale doesn't influence the LLM's behavior. Keep when the rationale helps the LLM decide edge cases.
- **Verbose examples** — Multiple examples showing the same pattern with minor variations. One example + the rule is sufficient.

## How to assess

For each flagged section, answer: "If I remove this, would the LLM produce different (worse) output?" If no — it's noise. If yes — keep it but consider whether it could be shorter.

## Token budget awareness

A skill loaded into context competes with the actual task content. Every unnecessary line in a skill is a line the LLM can't use for the user's code. Prioritize ruthlessly.
