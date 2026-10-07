envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:06Z

## Routed lessons cluster C15 — agent working discipline (8 live + 5 already-covered)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-016` (skills-carry-incident-history-as-normative-prose) for the
live residue.
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### Why this cluster is mostly a retirement candidate

Thirteen lessons about how the agent should work. Five are **already codified** as hard rules in
`CLAUDE.md`, the persona skills, or an enforcement hook — for those the lesson has done its job
and the rule outlived it. That is exactly the coverage judgement your running `PLAN-TRUTH-044`
governs, which is why nothing here has been retired.

| Lesson | Covering clause |
|--------|-----------------|
| 2026-07-21-16-003 | a literal semicolon in a quoted argument trips the one-command hook — `CLAUDE.md` hard rule "Bash: no shell constructs", and the hook itself enforces it |
| 2026-07-21-16-004 | verify disk state before re-firing a stalled dispatch — `orchestration-model.md` § Dispatch Decision Rule, "Fall back to inline", never blind-retry |
| 2026-07-15-18-001 | consult the target script's Canonical invocations for the exact verb — `CLAUDE.md` hard rule "Workflow steps: no improvisation" |
| 2026-07-17-17-001 | a fix-task leaf wrote to the MAIN checkout via absolute paths instead of the cwd-pinned worktree — the dispatch contract pins `WORKTREE` |
| 2026-07-21-12-002 | quote possibly-empty `{placeholders}` in documented shell commands — `plugin-script-architecture` |

⚠ **`2026-07-21-16-003` deserves a second look before retirement.** Your ledger already carries
`PLAN-TRUTH-056`: the enforcement hook scans for shell metacharacters **without respecting
quoting**, so the agent edits the evidence to satisfy a lexer. That means the "covering clause"
for this lesson is a hook with a known defect. A lesson covered by a broken enforcer is not
covered. Recommend holding it until TRUTH-056 lands.

### The eight live members

| Lesson | Claim |
|--------|-------|
| 2026-08-03-06-002 | a reviewer's named site list is a **detector sample** — only a derived-population class sweep closes the finding |
| 2026-08-02-07-001 | a refutation resting on a universally-quantified premise must **enumerate the population** before asserting it |
| 2026-08-03-19-001 | when a claim is about a mechanism, **read the mechanism** — a timing, a comment or an ordering is a proxy, not the wiring |
| 2026-07-28-20-003 | **relocation is not repair**: the failure message changed but the verdict did not |
| 2026-07-29-18-008 | an argparse rejection repeated **verbatim across a retry boundary is never flaky** |
| 2026-07-28-11-001 | the orchestrator cwd pin **silently reverts to the main checkout across background-job boundaries**, producing an orphan plan directory with no self-correction escape hatch |
| 2026-07-26-22-005 | argument-naming enforcement is **opt-in**: a script absent from the Canonical Forms table escapes `CANONICAL_FORMS_DRIFT` entirely, so `manage-change-ledger` ships a Rule-5-forbidden `query` read verb |
| 2026-07-15-22-001 | best-effort cleanup in a `finally` block must swallow its own exception or it **masks the primary operation's failure** |

### The two that are not discipline at all

`2026-07-28-11-001` and `2026-07-26-22-005` are **mechanism defects wearing discipline clothing**,
and they are the two I would actually plan:

- The cwd pin reverting across a background-job boundary is a real state bug with no escape
  hatch, not a rule someone failed to follow.
- Opt-in enforcement is the `PLAN-TRUTH-042` shape in a new place: a drift check that a script
  escapes **by being absent from a table**. The population is the registry, not the table, and a
  check keyed on the table can never report the scripts missing from it. It also produced a
  concrete live violation (`manage-change-ledger`'s `query` verb).

The other six are genuine standing rules. Their natural home is `PLAN-TRUTH-016`'s question —
whether incident history belongs in skill prose at all — rather than six separate fixes.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-016`/`-056` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: the five already-covered verdicts above. Each names its
  covering clause; **none has been verified against the clause's own worked example**, which is
  the evidence standard `manage-lessons remove --coverage-verdict completely_covered` requires.
  Confirm/refute artifact: each named clause, read directly.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
