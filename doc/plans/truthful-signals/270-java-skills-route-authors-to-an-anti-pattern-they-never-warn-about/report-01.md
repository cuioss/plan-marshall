# Run report — 270-java-skills-route-authors-to-an-anti-pattern (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/java-skills-anti-pattern-1y0hs4`    **PR:** [#1195](https://github.com/cuioss/plan-marshall/pull/1195)    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` (loaded first, as Step 1 requires — the working contract governing this run).
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

The **complete** changed-path set — `git diff --name-only origin/main...HEAD` — is seven files, **all
Markdown** (`doc/plans/**` + `pm-dev-java` `SKILL.md`/`standards/*.md`); the `-- '*.py'` filter returns
empty, and no Java or other buildable file is present either. **No buildable footprint — local build
skipped.** The merge queue's `merge_group` run verifies the docs-only change before it lands
(`.github/workflows/python-verify.yml` `skip-on-docs-only`). Verdict derived from git, not assumed.

## Findings

### Cold read (the plan's central check) — PASS

An independent sub-agent was given ONLY the three null-safety guidance files (no plan, no diff, no
report — the answer was never leaked) and asked to model an absent configuration value in three
positions. Result: `@Nullable String` in **all three** —

| Position | Agent wrote | Correct? |
|---|---|---|
| Record component (`AppConfig`) | `@Nullable String configValue` | ✅ |
| Field (`AppService`) | `@Nullable String configValue` | ✅ |
| Parameter (`void configure(...)`) | `@Nullable String configValue`, and named the overload as the preferred alternative | ✅ |

The agent explicitly stated `Optional<String>` is forbidden in all three positions and cited the
reasons (not `Serializable`, allocation/dereference cost, caller-wrap). The guidance now leads a fresh
reader to `@Nullable T` in exactly the positions where the old guidance failed silently. **Disposition:
pass — no change.**

### Deliverable-vs-plan review (with beyond-diff staleness sweep) — PASS

An independent sub-agent verified all six deliverables against the plan and swept the `pm-dev-java`
bundle beyond the diff. Verdict: **PASS on D0–D5**, no out-of-scope violation (no consuming-project
edit, no record→`@Value` conversion, return-type rule preserved verbatim), and **no genuinely-stale
consumer** found. Non-defect notes, each recorded and dispositioned:

- `java-maintenance/standards/refactoring-triggers.md:49` ("Optional<T> for potential absence") —
  **not stale**: the enclosing "Inconsistent API Contracts" trigger is return-scoped. **Disposition:
  no change (correctly scoped to returns).**
- `java-maintenance/standards/compliance-checklist.md:36` ("No `@Nullable` on return types") —
  **not stale** (a correct return-rule check), only *less complete* than the widened rule. Extending
  it to also check "no `Optional` fields/params/components" is in a different skill (`java-maintenance`)
  and outside this plan's declared deliverables and expected surface. **Disposition: rejected —
  out of scope; it is a correct signal, not a misleading one.** Recorded as residue.
- `java-core/standards/java-17-features.md` § "Optional Usage", `java-performance-patterns.md`,
  `javadoc/**` — all `Optional` examples are **returns**; none show a field/parameter/component
  `Optional` as idiomatic. **Not stale. Disposition: no change.**
- Pre-existing imprecise xref `refactoring-triggers.md:48` → java-null-safety "section 'Optional
  Usage'" (that section actually lives in `java-core/java-17-features.md`). **Predates this change,
  not made stale by it.** **Disposition: rejected — pre-existing and out of scope.** Recorded as
  residue for a future plan.

The two pre-PR sub-agents required no code change; CodeRabbit's PR review (below) did.

### CodeRabbit PR review (7 findings) — round 1 on `0d90640`

CodeRabbit posted 7 actionable findings (6 inline threads + 1 that failed to post to a thread). Each,
with disposition:

- **`null-safety-core.md` record-component example (Major) — FIXED.** The `@Nullable Duration validity`
  component was *defaulted* to non-null inside the compact constructor, so its generated accessor
  advertised an absence that could never occur — the exact misleading-signal defect this plan targets.
  Redesigned the Records section: a genuinely-absent component is `@Nullable T` with **no** default
  (accessor honestly nullable); defaulting is shown with a **non-null** component + a static factory
  that normalizes the nullable input. Same fix resolves the "wrong-pattern example" Minor finding —
  the contrived `name == null` guard under `@NullMarked` is gone, replaced by construct/read call-site
  comments.
- **`null-safety-core.md` serialization/cost rationale (Minor) — FIXED.** Scoped the absolute claims:
  "not `Serializable`" → "under default Java serialization"; "an allocation and a dereference on every
  access" → "adds a wrapper object (a heap allocation the JIT is not guaranteed to elide), unwrapped on
  read". Accurate, and the point stands.
- **`report-01.md` complete the report (Major) — FIXED.** All TBD sections completed in this commit.
- **`report-01.md` record the `cloud-plan-lane` load (Major) — FIXED (partial).** Added `cloud-plan-lane`
  to Skills loaded (it was loaded first, per Step 1). The finding's second half — "add a guard outside
  the report to enforce the stop" — is **rejected as N/A by design**: this lane is agent-followed, not
  machine-enforced; there is deliberately no dispatcher (`.plan/` is git-ignored, absent in a cloud
  clone). The enforcement is the loaded contract, not a runner.
- **`report-01.md` check all changed paths (Minor) — clarified.** The build-gate verdict already rested
  on the full changed set being Markdown, not merely on the `-- '*.py'` filter; strengthened the wording
  to state the complete-path check explicitly. `git diff --name-only origin/main...HEAD` = 7 files, all
  `.md`.
- **`plan.md` synchronize the expected surface (Major, failed to post) — rejected, documented.** The
  plan's "Expected surface" is the reporter's **hypothesis** (the plan itself flags it as unverified and
  makes D0 re-verify it). The authoritative placement — D4 → `null-safety-patterns.md`, no `java-21`
  edit — is recorded in this report's D0 section. The plan is the input record; it is not rewritten to
  match the verified outcome. No resolvable thread existed for this one (it failed to post).

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each registry doc under
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/` (`coderabbit.md`, `pr-agent.md`,
`sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`. M = 3.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `reviewed` | Posted a full review on `0d90640`: summary walkthrough + "Actionable comments posted: 7" with 6 inline review threads. Findings dispositioned above. |
| `cuioss-review-bot` | `reviewed` | Posted its `## PR Reviewer Guide 🔍`: "No security concerns identified / No major issues detected / No relevant tests" — clean (the 🧪 negative is expected and non-actionable for a docs-only change). |
| `sourcery-ai` | `rate-limited` | Posted only a refusal notice: "you have reached your weekly rate limit of 500000 diff characters" — matches Sourcery's `refusal_patterns` (`hard_quota`, weekly quota; not awaitable in a useful window). No review of this diff. |

**Coverage: 2 of 3 reviewed.** The § Step 8 shortfall disclosure fired: `sourcery-ai` rate-limited
(weekly diff-character quota — outside our control, not awaitable), disclosed before arming auto-merge.
Merge proceeds on the disclosure, not blocked by it (per the contract, a rate-limit is disclosed, never
a merge blocker).

## Cost

- **Tokens:** not available to the agent as a reliable figure in this Claude Code cloud session — stated
  plainly rather than estimated.
- **Wall-clock:** run start ~21:35 UTC to auto-merge arm ~21:5x UTC (single session); source — PR
  created 21:42:29 UTC, CodeRabbit round-1 review 21:51 UTC.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under a different
  per-task billing boundary this interactive session does not share.

## Contract check (Step 9)

GitHub access path: **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/*`
(kept as-is per the contract). A cloud run owes **no** `/sync-plugin-cache` (machine-local build step).

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — `cloud-plan-lane` (first), `ref-code-quality`, `plugin-script-architecture`, `plugin-architecture`; named in the report |
| 2 Branch | Done — `claude/java-skills-anti-pattern-1y0hs4` on `origin` (harness-assigned, pushed before any work) |
| 3 Plan directory | Done — `plan.md` in place, opens with the first-instruction block |
| 4 Implement | Done — D0–D5 addressed; commits carry the `Co-Authored-By: Claude` trailer |
| 4 Per-commit gate | N/A — no commit touched `*.py`; no quality gate owed |
| 4 Pushed | Done — no unpushed commit remains after each push |
| 5 Build gate | Done — full changed set is Markdown (no `*.py`); local build skipped; merge-queue verifies |
| 6 Verification sub-agent | Done — cold read PASS (all three positions `@Nullable T`); deliverable review PASS; findings + dispositions recorded |
| 7 PR cycle | Done — PR #1195; all 3 comment surfaces read; every comment dispositioned |
| 8 Merge gate | Conditions 1–3 met on the fix head; shortfall (2-of-3) disclosed; auto-merge armed |
| 8 Bridge | Done — writes confined to this plan's directory; report carries PR # and per-deliverable outcome |
| 9 This check | Done — this table |
| 9 What have we learned | One minor observation recorded below |

## What have we learned (Step 9)

**One minor, evidence-backed observation — recorded, not shipped.** CodeRabbit flagged the report's
"Skills loaded" section for omitting `cloud-plan-lane`, the skill Step 1 loads *first*. The contract's
report template (`## Skills loaded`) and Step-1 table do not explicitly say a run must list its own
`cloud-plan-lane` load — a run can reasonably treat it as implied, which is what happened here. A
one-line clarification to the report template ("include the `cloud-plan-lane` load itself") would close
that gap. Per Step 9, a contract change is **not self-approved**: this is presented for the operator's
decision and **not** shipped as a separate PR absent approval. No other contract gap surfaced — the
durability-vs-review-integrity tension, the docs-only build skip, and the MCP merge-gate field
(`mergeable_state`) all behaved as the contract describes.

## Residue

- `java-maintenance/standards/compliance-checklist.md:36` is correct but less complete than the widened
  positional rule (checks only "no `@Nullable` returns", not "no `Optional` fields/params/components").
  A future `java-maintenance` pass could extend it; out of scope here.
- Pre-existing imprecise xref `java-maintenance/standards/refactoring-triggers.md:48` points to a
  java-null-safety "section 'Optional Usage'" that actually lives in `java-core/java-17-features.md`.
  Predates this change; a future doc-hygiene pass should correct it.
- `sourcery-ai` did not review this diff (weekly quota). If a fresh Sourcery pass is wanted, it needs a
  smaller diff or a quota reset — neither is actionable from this run.
