# Landing analysis — PLAN-PR-065

**Plan**: `pr-065-settings-repo-accumulates-never-lands` · **PR**: #1491 — **merged** (merge queue)
**Deliverables**: 10/10 · **Finalize steps**: 23/23 · **Landing**: `-021`, `complete: true`
**Foreign half**: `cuioss/pr-agent-settings` PR #64 — merged earlier, the actual subject of the plan.
**Corroboration**: `ci pr view --pr-number 1491` → `state: merged`, first-party. ⛔ Not taken from the
narrative.

## What landed, and the ordering that made it work

⭐⭐ **The plan repaired its own instrument BEFORE using it.** D1 made `ci pr list` derive a complete
population instead of reporting a page — the exact defect this orchestrator hit at staging time, when
the verb returned 30 rows (`gh`'s default page size) against an operator-reported 46. Only then did D2
derive the real population and D3 land the newest snapshot. ⇒ The gate that decided what to close was
fixed before it decided anything. That ordering is the reusable part.

The rest as specced: a validation check worth requiring (D4), protection plus repository auto-merge
(D5), the publisher landing its own PR on **one rolling branch** (D6) so the backlog cannot
re-accumulate, the two working documents reduced to what a reader needs (D7–D9), and the published pack
set verified (D10).

## ⛔⛔ CORRECTION 2026-09-15 — the documentation deliverables DID NOT LAND

The paragraph above claims *"the two working documents reduced to what a reader needs (D7–D9)"* and the
header claims **10/10**. **Both are false for the foreign documentation half.** Verified first-party
2026-09-15 (`gh api repos/cuioss/pr-agent-settings/contents`, `gh pr list` over #50–#64):

- `README.adoc` is still **66,174 B** — byte-count identical to the monolith recorded at staging;
- `.pr_agent.toml` is still **29,484 B** — its narrative comments were not reduced;
- **no `doc/` directory exists** (`contents/doc` → HTTP 404);
- none of the 15 most recent PRs in that repository is a documentation change.

⇒ The spec's documentation deliverables (`README` decomposition into `doc/`, the decision log, the
`.pr_agent.toml` reduction) were reported done and never reached the foreign `main`. The operator
reported the loss; the ledger had recorded it as shipped. This is the **foreign-task-reports-done**
shape `PLAN-PR-023` exists to prevent, recurring on a WS-02 landing, and the landing was read as
`complete: true` because the landing payload carries no per-deliverable foreign-landing evidence.

⚠ **The spec itself also mis-captured the ask**: its D6 said relocate sections "verbatim", while the
operator asked for a REWRITE — remove all history, document as-is, decompose into a `doc/` module with a
README overview that references it. The work is carried, re-specified from the operator's wording, as
`PLAN-PR-066` D12. The shipped status of the rest of `PLAN-PR-065` (D1–D5, D10 and the local fixes) is not
disputed by this correction.

## ⭐ `PLAN-PR-039`'s precondition is DISCHARGED

D10 verified the published pack set. `packs/` now exists on that repository's `main` for the first
time, so `PLAN-PR-039` — which resolves declared pack keys against those artifacts — is no longer
structurally blocked. ⚠ It remains **unemittable for a different reason**: its `## Expected Surface`
is `prose`, so the disjointness gate has nothing to compare and its clean reading is SILENCE (ADR-019).
⛔ **That is NOT a spec-authoring gap and was deliberately left alone.** `PLAN-PR-039` carries a NAMED
exemption recorded at the 2026-08-31 cleanup: every path it declares is in a foreign repository, so
this repo's resolver can never claim one, and the spec states outright that inventing a plan-marshall
path to make the metric move would destroy the foreign-only property that makes WS-02 disjoint by
construction. ⇒ Its disjointness is established by that declared property — a claim about the spec —
**never by the gate having compared anything**, and the two must not be confused. Emitting it is
therefore an operator decision to accept a candidate the gate cannot check, not a correction to make.

## ⛔ The review coverage of THIS PR is a deliberate, recorded gap

Automated bot review was **explicitly skipped by operator decision** (`required_bots` / `optional_bots`
set empty, `skip-bot-review` applied). The stated ground: the plan's real-world impact landed in the
foreign repository, and this repo's PR carried the supporting tooling fix plus an opportunistic
plugin-doctor fix.

⛔ **Recorded as a bypass, not as a clean review.** This epic's standing rule is that a CodeRabbit
review plus finding handling is mandatory and a merge on a bypass is never a passing signal — an
operator may choose it, and the ledger must not later read the absence of findings as evidence of
quality. `0 comments found` here means **nobody looked**, which is precisely the conflation
`PLAN-PR-061` exists to end.

⚠ **And the retrospective's own reading was a false alarm**: it graded `indeterminate` over a
"roster of 3" because it reads bot rosters from `marshal.json` rather than the plan's local step-params
override. Its instrument disagreed with the run's actual (empty) roster — a config-source defect in the
retrospective step, not a coverage gap in this plan. Transferred.

## ⛔⛔ Declared vs realized, AGAIN — and this time in BOTH directions

`references.json` declared **19** `affected_files` against a **13**-path realized footprint, and the
two sets are **not nested**:

- **Realized but never declared (5)** — including `branch-cleanup.md` and
  `persona-plan-marshall-agent/standards/argument-naming.md`, the targets of TASK-012/TASK-013 appended
  during execute. The task records name the files; the declaration never absorbed them.
- **Declared but never realized (4)** — `ci_base.py`, `gitlab_ops.py` and their tests: **the GitLab
  half of the `--limit` / `truncated` contract was declared in scope and never touched**, because the
  derivation signal exists on the GitHub provider only.

⇒ **Fourth consecutive landing with a declared/realized divergence**, and the first where the
declaration also OVER-stated. ⛔ The over-statement is the more dangerous direction for this epic's
gate: a spec that declares what it will not touch makes the disjointness check sequence siblings behind
files nothing ever claims.

## ⭐⭐ The finding worth keeping — a producer fixed, its decisive consumer left reading a page

`branch-cleanup.md` calls `pr list --head {branch} --state open` with no `--limit`, takes a bare count,
and that count drives the Safety Check that **aborts branch cleanup when other open PRs use the
branch**. So D1's single most consequential consumer — the one gating a **destructive delete** — was
outside the deliverable's declared files. After the producer landed, that call site would have received
a `truncated` field it does not read and a default limit it does not set: **a page still read as a
population, in the exact code path the deliverable existed to correct.**

⭐ It was caught and migrated (TASK-013), and `branch-cleanup.md` duly appears in the realized footprint
— which is how the two findings above are the same story from two ends. ⛔ The scope-criterion
validator caught it; **nothing in the outline's own success criterion would have.** Promoted as a
lesson.

## Cost

6.5M tokens / 31h35m wall. ⚠ The review loop was absent here by decision, so this run is **not**
evidence about the review-window cost the last four landings measured — it is the control case, and it
still spent 6.5M.

## Reconciliation actions taken

1. Queue row `PLAN-PR-065` → `shipped`, `pr: 1491`, landing stamped.
2. `PLAN-PR-039`'s blocked-on-packs dependency retired. Its `prose` surface was **left untouched** —
   the exemption is named and deliberate; see above.
3. 22 inbox messages drained — one promoted, the invocation-discipline and plan-quality cluster
   transferred to `truthful-signals`, the tier-model finding recorded as a Watch.
