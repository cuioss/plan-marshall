# Final verification: multiplattform archive completely implemented?

Standalone OpenCode task. No plan-marshall lifecycle, no phases, no status.json, no worktree —
read the listed documents, verify each requirement against the repository tree, write the two
output documents. Work directly on `main` (or your current checkout); create no branches, open
no PRs, change no source files. Read-only against the tree except for the two output documents.

## Objective

Decide, for every task/requirement recorded in the multiplattform archived documents, whether
it is completely implemented in the current tree — and for anything that is not, say exactly
which of the three non-complete states holds.

## Scope (closed population — 14 files, nothing else)

All paths rooted at `.plan/orchestrator/multiplattform/archive/`:

- `010-runtime-seam-neutrality/plan.md` + `report-01.md`
- `020-target-scoped-components/plan.md` + `report-01.md`
- `030-claude-literal-residuals/plan.md` + `report-01.md`
- `original-staged-specs/040-sync-opencode-inner-loop.md`
- `original-staged-specs/050-structural-directive-coverage.md`
- `original-staged-specs/060-authoring-surface-target-awareness.md`
- `original-staged-specs/070-runtime-fact-prose-and-single-sources.md`
- `original-staged-specs/080-permission-skills-through-the-registry.md`
- `README.md`, `report-authoring-01.md`, `report-authoring-02.md` (context + methodology only;
  requirements come from the plan/spec files above, not from these three)

The requirement population is: every numbered deliverable (D1…) **with its done-when clause**
in the three `plan.md` files, plus every deliverable/requirement in the staged specs
040–080. The `report-01.md` files and the staged specs' own claims are leads, never verdicts.

## Verdict taxonomy (exactly one per requirement — no fifth state, no hedging)

- **completely implemented** — the done-when clause holds against the implementing source
  at the current HEAD. Name the file(s) and symbol(s) that settle it.
- **partially implemented, missing aspects** — done-when holds in part. Name precisely which
  aspects hold and which are missing, each anchored to a file/symbol or its absence.
- **refuted to implement, reason** — deliberately not (going) to be done. Quote or cite the
  recorded reason (review rejection, superseding decision, explicit non-goal) and where it
  is recorded. "Nobody did it" is not a reason.
- **still open** — neither implemented nor refuted. Name what remains and where it should live.

## Method (in this order, no shortcuts)

1. Enumerate the requirement population first, as a flat list with IDs
   (`010-D1`, `010-D2`, …, `040-D1`, …). Counts ride with their population: state how many
   requirements each document contributes. Re-derive counts from the documents — never carry
   a count from prose.
2. Verify each requirement against the **implementing source** — the code, script, test, or
   generated artifact that enacts it — never against a standards doc, an ADR, a report, or
   the requirement's own prose, all of which merely restate the claim. Reports (`report-01.md`)
   tell you where to look; the tree decides.
3. Label every claim in your outputs OBSERVED (read at a named file/symbol) or HYPOTHESIS
   (with the named artifact that would settle it). An unlabelled claim is a defect in the
   output. An asserted absence ("X does not exist") is verified exactly as strictly as an
   asserted presence — search the tree, name the search.
4. Watch for these known traps in this corpus (leads, re-derive each):
   - Staged specs 040–080 may never have executed — a spec existing is not implementation.
   - `report-01.md` files describe runs that predate later landings; a "complete" there may
     have regressed or been superseded since. Verify at current HEAD.
   - Done-when clauses with counts or enumerations (operation counts, hit lists, residual
     sets) — re-derive at HEAD; act on what the tree says.

## Outputs (exactly two documents)

1. **Analysis**: `doc/plans/multiplattform/final-verification-analysis.md` — one row per
   requirement: ID, source document, one-line requirement, verdict, evidence (file + symbol
   or search statement), and for non-complete verdicts the missing aspects / reason / remainder.
   End with tally tables: verdict counts per plan file and overall, each with its population.
2. **Still-open tasks**: `doc/plans/multiplattform/final-verification-open-tasks.md` — only
   the `partially implemented` and `still open` rows, each rewritten as an actionable task
   (what, where in the tree, how to verify done). `refuted` rows are excluded (their reasons
   live in the analysis); state that exclusion explicitly.

## Done when

- Both documents exist at the paths above.
- Every requirement in the population carries exactly one of the four verdicts — no blanks,
  no "unknown", no fifth wording.
- Every `completely implemented` verdict names its settling file(s)/symbol(s); every other
  verdict names what's missing, why not, or what remains.
- Tallies reconcile: per-file counts sum to the population total, and every population is
  stated beside its count.
