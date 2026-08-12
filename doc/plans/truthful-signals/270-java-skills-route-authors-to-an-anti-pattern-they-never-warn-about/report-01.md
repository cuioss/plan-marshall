# Run report — 270-java-skills-route-authors-to-an-anti-pattern (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/java-skills-anti-pattern-1y0hs4`    **PR:** TBD    **Outcome:** in progress

## Skills loaded

- `plan-marshall:ref-code-quality` (read from bundle path) — always-load.
- `pm-plugin-development:plugin-script-architecture` (read from bundle path) — always-load.
- `pm-plugin-development:plugin-architecture` (read from bundle path) — SKILL.md / bundle-structure surface.

The plan surface is skill **documentation** (`SKILL.md` + `standards/*.md` markdown) — no Python, no
`.adoc`, no production Java. `persona-implementer` and `pm-documents:ref-asciidoc` were not needed.
All skills obtained via the bundle-path route (the reliable route in a fresh cloud clone).

## Deliverables

### D0 — GATE: verify positional rules & asserted absence (mutates nothing)

Verified every quoted rule and asserted absence against the **current** skill text (the report's table
was the reporter's, at an older bundle version). Files read: `java-null-safety/SKILL.md`,
`.../standards/null-safety-core.md`, `.../standards/null-safety-patterns.md`, `java-core/SKILL.md`,
`.../standards/java-17-features.md`, `.../standards/java-21-features.md`, `.../standards/java-25-features.md`,
`.../standards/java-core-patterns.md`, `java-lombok/SKILL.md`, `.../standards/lombok-core-annotations.md`.

**Positional rules (D1 input):**

| Position | Rule | Current status | Evidence |
|---|---|---|---|
| Return type | `Optional<T>`; never `@Nullable` | STATED | `null-safety-core.md` § "CRITICAL RULE: Never Use @Nullable for Return Types"; `SKILL.md` Key Rules table |
| Field | `@Nullable T`; never `Optional<T>` | ABSENT | examples show only non-null fields; no field nullability rule, no Optional prohibition anywhere |
| Parameter | `@Nullable T` or overload; never `Optional<T>` | PARTIAL | `@Nullable`/overload stated in `null-safety-patterns.md` § "Nullable Parameters"; the never-`Optional<T>` prohibition is ABSENT |
| Record component | `@Nullable T`; never `Optional<T>` | ABSENT | records unmentioned in the null-safety skill |

**Asserted-absence check (the higher-risk half) — reported explicitly:**

- Searched `marketplace/bundles` (all bundles, not just `pm-dev-java`) for: `record component` /
  `component.*nullab`, `Optional` (whole `pm-dev-java` bundle), `Optional.*field|field.*Optional|
  Optional.*parameter|parameter.*Optional|Serializable`, and the D3 trigger terms `else if|if/else|
  if-else|sequential.*equal|chain of|constant set` (in `java-core`).
- **Field/parameter `Optional`-prohibition:** NOT stated anywhere. The only near-match is
  `java-maintenance/standards/refactoring-triggers.md:49` — "Use @NonNull for guaranteed results,
  Optional<T> for potential absence" — which restates the **return-type** idiom, not a field or
  parameter rule. **Absence confirmed.**
- **Record-component nullability:** the only `record component` matches are Lombok's `@Builder.Default`
  limitation (`lombok-core-annotations.md`, `lombok-canonical-methods.md`) — no nullability rule.
  **Absence confirmed.**
- **"Optional is not `Serializable`" reason:** stated nowhere (all `Serializable` hits are about
  serialization contracts in maintenance/testing). Worth stating.
- **D3 `if/else`-over-constants → switch trigger:** grep returned **no matches** in `java-core`.
  **Absence confirmed.**

**"I did not find it" vs "it is not there":** the searches above cover the crawled marketplace bundle
tree via Grep over `marketplace/bundles`, reading matched files directly. This is a positive
**"it is not there"** for the inventoried skill corpus — the only place these rules could live.

**Refutation confirmed (carried forward):** `java-lombok/SKILL.md` Key Decision Guide row
"Immutable data carrier → Java record (not `@Value`)" states records over `@Value`. The premise "the
Java skills demand Lombok" is refuted first-party; the consuming project's records are compliant.
**No skill edit needed for the refutation itself** — the table already gets it right. D5 records the
residual gaps.

**Placement decisions (verified, adjusting the reporter's hypothesised surface):**

- D1 + D2 → `java-null-safety/standards/null-safety-core.md` (the core rules file, loaded for any
  null-safety work) + `java-null-safety/SKILL.md` (Key Rules table + Step-1 description).
- D3 → `java-core/standards/java-17-features.md` only, adjacent to § "Switch Expressions". The
  reporter's surface also named `java-21-features.md`, but its switch content is **type-pattern
  dispatch** (a different, already-covered trigger); the `if/else`-over-closed-constants → switch
  trigger with enum-exhaustiveness is a switch-expression (Java 14/16) concern. **No java-21 edit.**
- D4 → `java-null-safety/standards/null-safety-patterns.md` (migration-adjacent; the deliverable is
  explicitly a migration gotcha). D4 was unassigned in the reporter's "Expected surface".
- D5 → `java-lombok/SKILL.md` (gaps note; explicitly NOT a rule change).

**D0 verdict: no deliverable changes shape. Proceed to write.**

## Build gate

TBD (documentation-only expected — no `*.py` in the diff → local build skipped; merge-queue verifies).

## Findings

TBD (verification sub-agent, CI, PR review).

## Reviewer participation

TBD.

## Cost

TBD.

## Contract check (Step 9)

TBD.

## What have we learned (Step 9)

TBD.

## Residue

TBD.
