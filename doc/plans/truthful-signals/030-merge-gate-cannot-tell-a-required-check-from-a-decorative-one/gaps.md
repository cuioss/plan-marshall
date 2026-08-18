# Gaps — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one

**Source:** verification.md (same directory)   **Open items:** 3

Two items deliberately **not** filed as gaps, and why:

- **D1's landed text enumerated only `BLOCKED` and `UNSTABLE`, omitting `clean`** — a real defect this plan
  shipped, but closed later by `3a5e2ca0` (#1177), now `SKILL.md:1229-1232`. Superseded, not open.
- **D0's STOP condition was reinterpreted rather than obeyed** — the run did not halt when the ruleset-config
  API proved unreachable. It disclosed this (finding #2, § What have we learned #2), the STOP's stated
  purpose (no hand-maintained list of required checks in the contract) was honoured, and #1147 wrote the
  unreachability into the contract at `SKILL.md:56`. The forward-looking half is closed; the backward-looking
  half is a record, not an action. G3 below carries only the residual, actionable part.

---

## G1 — Correct or refute the documented merge-queue arming command

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1290` — § Step 8, the merge command block; and
  `.claude/skills/cloud-plan-lane/SKILL.md:70` — the `gh` ↔ GitHub MCP mapping row
- **What is wrong:** Both sites document `gh pr merge {N} --squash --auto` as the way to arm auto-merge on
  this merge-queue repository. This repository's own production enqueue path does the opposite:
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:1911`
  (`cmd_pr_merge_queue`) builds `['pr', 'merge', identifier, '--auto']` with **no** strategy flag, under the
  comment "Neither `--strategy` nor `--delete-branch` is forwarded: the merge queue's own branch-protection
  configuration dictates the merge method." The sibling non-queue path at `_github_pr.py:1631` does forward
  `f'--{args.strategy}'`, and the two are selected by an explicit queue-configured discriminator — so the
  omission on the queue path is deliberate, not an oversight. Plan D3 asserted this and was dropped only
  because the run had no `gh` CLI to re-derive it with; the report's § Residue carries it forward explicitly.
- **Why it matters:** A cloud run following the contract literally issues a command form that this repo's own
  code avoids on a queue-gated base. If the flag is rejected there (as the plan's #1111 observation claims),
  the run stalls at the merge gate with auto-merge unarmed — the exact failure D3 existed to prevent. If it is
  merely inert, the contract is teaching a misleading form and the residue can be closed as refuted. Either
  outcome is better than the current unresolved state.
- **Fix:** From a session that has the `gh` CLI (or from the operator directly), run
  `gh pr merge {N} --squash --auto` against a real open PR on this repo and record the exit code, stderr, and
  whether `gh pr view {N} --json autoMergeRequest` is non-null afterwards. If it errors or leaves
  `autoMergeRequest: null`, change `SKILL.md:1290` to `gh pr merge {N} --auto` and add one line stating that
  the strategy flag is omitted because the merge queue's branch-protection configuration dictates the merge
  method (cross-referencing `_github_pr.py:1911`); update the `SKILL.md:70` mapping row to the same form. If
  it succeeds and arms, leave both unchanged and record the refutation so the residue closes.
- **Done when:** `SKILL.md:1290` and `SKILL.md:70` either carry the verified working form with its one-line
  reason, or a recorded observation exists confirming the documented form works — and this plan's § Residue
  entry "D3 doc edit deferred" is settled either way.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Step 8 merge gate / § Cloud session affordances mapping

## G2 — Make the "which context blocks" derivation executable on the cloud path

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1245-1252` — § Step 8 condition 1, final paragraph
- **What is wrong:** The paragraph instructs: "When `mergeStateStatus` is `BLOCKED`, derive **which** context
  blocks from (required contexts ∩ non-green contexts)." Computing that intersection requires enumerating the
  required-context set. Forty lines earlier, the same condition states the opposite is possible:
  "**The ruleset-config API itself is not reachable on the cloud MCP path** …, so 'read it from the ruleset'
  means read `mergeStateStatus` — never a ruleset-config API call, which returns `403` here"
  (`SKILL.md:1205-1208`), a limitation restated in the affordances table at `SKILL.md:56`. A cloud run
  therefore cannot enumerate the left operand of the intersection it is told to compute. (Provenance checked:
  `git log -S 'never from whichever pending status is loudest'` → `a3eb36bb` (#1147); this paragraph arrived
  after PR #1137 and is not text this plan shipped.)
- **Why it matters:** This is the operator-disclosure path for a blocked merge. A run that cannot perform the
  named derivation will either invent a required set or fall back to the very "whichever pending status is
  loudest" heuristic the paragraph forbids — reproducing the mis-attribution the paragraph was written to
  prevent, while believing it followed the contract.
- **Fix:** In `SKILL.md:1245-1252`, state how the required set is approximated on a path where the
  ruleset-config API is unreachable, and make the fallback explicit. A workable form: intersect the non-green
  contexts with the checks that carry a required-looking identity on this repo (the `verify / conclusion`
  aggregate check the merge queue enforces), and where the required set genuinely cannot be established, say
  so in the disclosure — "`mergeStateStatus: BLOCKED`; required set not enumerable on this path; non-green
  contexts are X, Y" — rather than naming a blocker. Keep the existing prohibition on promoting a salient
  non-required status to "the blocker".
- **Done when:** § Step 8 condition 1 contains no instruction whose inputs the same section declares
  unobtainable, and a reader on the cloud MCP path can produce a blocked-merge disclosure by following it
  literally.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Step 8 merge gate, condition 1

## G3 — Record what `main` actually requires, or retire the expectation that a run can

- **Kind:** omission
- **Severity:** low
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:56` — § Cloud session affordances, "Ruleset-config API"
  row; and this plan's `report-01.md` § D0
- **What is wrong:** D0's Done-when required "the required set … recorded in the report with the API surface
  it came from". No positive required-context set is recorded in `report-01.md`, in `SKILL.md`, or anywhere
  else in the tree — only the negative fact that `license/cla` is not required, inferred from two merge-queue
  admissions. Re-derived at HEAD: `grep -rn "required context"` across the contract yields definitions and
  rules, never an enumeration. The contract now tells a run that it *cannot* read the set (`SKILL.md:56`),
  which makes the omission permanent for any cloud run rather than an accident of one session.
- **Why it matters:** Every rule in condition 1 is phrased over "required contexts", and G2's derivation
  consumes that set directly. With the set nowhere written and nowhere derivable on the declared path, the
  contract's central noun has no referent a run can resolve — which is how the D0 gate came to be satisfied
  by inference rather than by reading.
- **Fix:** The operator (who has repository-admin access and is not subject to the `403`) reads the branch
  ruleset for `main` once and records the required contexts — as of this verification, the evidence points to
  `verify / conclusion` — in the affordances table at `SKILL.md:56`, alongside the existing note that a run
  cannot read it for itself. Mark the entry as operator-maintained and state when it must be re-read (any
  ruleset change), so it is an operator-owned fact with a stated staleness condition rather than the
  hand-maintained in-contract list D0's STOP condition forbade a *run* from inventing.
- **Done when:** `SKILL.md:56` names the required contexts for `main` with their provenance and their
  operator-maintained status, or records a deliberate decision that the set stays unrecorded and states what a
  run should do instead.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Cloud session affordances
