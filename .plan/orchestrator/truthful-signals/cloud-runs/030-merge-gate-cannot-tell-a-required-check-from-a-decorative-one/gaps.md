# Gaps — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one

**Source:** verification.md (same directory)   **Open items:** 4

Two items deliberately **not** filed as gaps, and why:

- **D1's landed text enumerated only `BLOCKED` and `UNSTABLE`, omitting `clean`** — a real defect this plan
  shipped, but closed later by `3a5e2ca0` (#1177), now `SKILL.md:1229-1232`. Superseded, not open.
  (Re-derived: `git log -S 'both report the required' -- .claude/skills/cloud-plan-lane/SKILL.md` → `3a5e2ca0`;
  `git show 991f3e5f -- .claude/skills/cloud-plan-lane/SKILL.md` confirms the landed text defined only the two.)
- **D0's STOP condition was reinterpreted rather than obeyed** — the run did not halt when the ruleset-config
  API proved unreachable. It disclosed this (finding #2, § What have we learned #2), the STOP's stated
  purpose (no hand-maintained list of required checks in the contract) was honoured, and #1147 wrote the
  unreachability into the contract at `SKILL.md:56`. The forward-looking half is closed; the backward-looking
  half is a record, not an action. It is, however, the reason the plan's headline verdict is
  **partially-implemented** rather than implemented-with-gaps (see verification.md § Adversarial review).
  G3 below carries only the residual, actionable part.

---

## G1 — Settle the documented merge-queue arming command: the tree's evidence is contradictory, not one-sided

- **Kind:** doc-drift
- **Severity:** low  *(re-severitied from `medium` during adversarial review — see § Refuted during
  adversarial review, item R1: the production-code evidence originally cited as supporting the defect was
  mischaracterised, and when executed it points the other way.)*
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1290` — § Step 8, the merge command block; and
  `.claude/skills/cloud-plan-lane/SKILL.md:70` — the `gh` ↔ GitHub MCP mapping row
- **What is wrong:** Both sites document `gh pr merge {N} --squash --auto` as the way to arm auto-merge on
  this merge-queue repository, and **nothing in the tree or in any run establishes whether that form works
  here.** Plan D3 asserted (from PR #1111) that `--squash` is *rejected* on a queue-gated base and leaves
  auto-merge unarmed; the run could not re-derive it (no `gh` CLI in a cloud session) and dropped D3, and
  `report-01.md` § Residue carries the question forward unanswered. The tree supplies evidence on **both**
  sides and settles neither:
  - *For* the plan's premise: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:1911`
    (`cmd_pr_merge_queue`) builds `['pr', 'merge', identifier, '--auto']` with **no** strategy flag, under the
    comment "Neither `--strategy` nor `--delete-branch` is forwarded: the merge queue's own branch-protection
    configuration dictates the merge method." Note the same comment attributes outright *rejection* only to
    `--delete-branch`; for `--strategy` it claims redundancy, not error.
  - *Against* it: `_github_pr.py:1631` (`cmd_pr_auto_merge`) builds `['pr', 'merge', identifier, '--auto',
    f'--{args.strategy}']` and runs it on a **queue-configured** base too, treating a non-zero exit as an
    error. Executed on 2026-08-18 against a stubbed `run_gh` with the base-queue probe forced to
    `MERGE_QUEUE_ELIGIBLE_CONFIGURED`: the emitted argv is `['pr', 'merge', '42', '--auto', '--squash']` and
    the verb returns `{'status': 'success', 'disposition': 'enqueued'}`. So this repository's own
    `ci pr auto-merge` verb issues exactly the documented form against a queue-gated `main` and expects it to
    succeed; `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:39`
    documents `--strategy {merge|squash|rebase}` for that verb with no queue caveat. If `gh` rejected the flag
    on this base, that verb would be broken on this repository.
- **Why it matters:** Low, not medium, because the audience of this contract is a **cloud** run, which
  § Cloud session affordances (`SKILL.md:53`) says has no `gh` CLI and uses `enable_pr_auto_merge` instead —
  and that MCP path was observed to arm without error with `mergeMethod: SQUASH` (`report-01.md` § D3). So no
  cloud run executes the possibly-wrong form. What is actually at stake is a documented command of unknown
  correctness, and a plan residue that has been open since #1137 with contradictory evidence accumulating on
  both sides of it.
- **Fix:** From a session that has the `gh` CLI (or from the operator directly), run
  `gh pr merge {N} --squash --auto` against a real open PR whose base is `main`, and record the exit code,
  stderr, and whether `gh pr view {N} --json autoMergeRequest` is non-null afterwards.
  - If it errors or leaves `autoMergeRequest: null`: change `SKILL.md:1290` to `gh pr merge {N} --auto`, add
    one line stating that the strategy flag is omitted because the merge queue's branch-protection
    configuration dictates the merge method, update the `SKILL.md:70` mapping row to the same form — **and**
    file a defect against `_github_pr.py:1631`, which would then be emitting a rejected flag on every
    queue-gated `pr auto-merge`.
  - If it succeeds and arms: leave `SKILL.md:1290` and `SKILL.md:70` unchanged and record the refutation in
    this plan's `report-01.md` § Residue, so the deferred D3 closes as refuted rather than staying open.
- **Done when:** a recorded observation of `gh pr merge {N} --squash --auto` on a `main`-based PR exists (exit
  code + `autoMergeRequest` state), `SKILL.md:1290` and `SKILL.md:70` match what it showed, and this plan's
  § Residue entry "D3 doc edit deferred" is marked settled with that observation cited.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Step 8 merge gate / § Cloud session affordances mapping

## G2 — Make the "which context blocks" derivation executable on the cloud path

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1245-1252` — § Step 8 condition 1, final paragraph
- **What is wrong:** The paragraph instructs: "When `mergeStateStatus` is `BLOCKED`, derive **which** context
  blocks from (required contexts ∩ non-green contexts)." Computing that intersection requires enumerating the
  required-context set. Forty lines earlier, the same condition states that is impossible here:
  "**The ruleset-config API itself is not reachable on the cloud MCP path** …, so 'read it from the ruleset'
  means read `mergeStateStatus` — never a ruleset-config API call, which returns `403` here"
  (`SKILL.md:1205-1208`), a limitation restated in the affordances table at `SKILL.md:56`. Re-checked at HEAD:
  the GitHub MCP server exposes no branch-protection or ruleset tool, and `mergeStateStatus` /
  `pull_request_read get_status` carry no per-context required flag — `get_status` on #1112 returns two
  contexts (`CodeRabbit`, `license/cla`) with `state` and nothing about required-ness. A cloud run therefore
  cannot enumerate the left operand of the intersection it is told to compute. (Provenance checked:
  `git log -S 'never from whichever pending status is loudest'` → `a3eb36bb` (#1147); this paragraph arrived
  after PR #1137 and is not text this plan shipped.)
- **Why it matters:** This is the operator-disclosure path for a blocked merge. A run that cannot perform the
  named derivation will either invent a required set or fall back to the very "whichever pending status is
  loudest" heuristic the paragraph forbids — reproducing the mis-attribution the paragraph was written to
  prevent, while believing it followed the contract.
- **Fix:** In `SKILL.md:1245-1252`, add the unobtainable-operand case the paragraph currently omits. Concretely:
  after the existing sentence "Derive the blocker from the intersection", add a clause stating that on a path
  where the required set is not enumerable (the cloud MCP path — § Cloud session affordances), the run
  **names no blocker at all** and instead discloses the two facts it can establish, in this shape:
  "`mergeable_state: BLOCKED`; the required set is not enumerable on this access path; the non-green contexts
  on head `{sha}` are X, Y." Keep the existing prohibition on promoting a salient non-required status to "the
  blocker". ⛔ Do **not** close this by writing a list of this repository's required checks into condition 1 —
  the plan's D1 Done-when requires that the condition **name no individual check**, and its D0 STOP forbids a
  hand-maintained required-check list as a fallback. The remedy is an explicit "cannot determine" branch, not
  a hardcoded set.
- **Done when:** § Step 8 condition 1 contains no instruction whose inputs the same section declares
  unobtainable — every path through the `BLOCKED` paragraph terminates in a disclosure a cloud run can
  actually produce — and the condition still names no individual check.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Step 8 merge gate, condition 1

## G3 — Condition 1's "required contexts" has no referent, while the same contract names one 1050 lines earlier

- **Kind:** omission
- **Severity:** low
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1200-1252` — § Step 8 condition 1 (every rule in it is
  phrased over "required contexts"); `SKILL.md:150` — § Step 2, which does name one; `SKILL.md:56` —
  § Cloud session affordances, "Ruleset-config API" row
- **What is wrong:** D0's Done-when required "the required set … recorded in the report with the API surface
  it came from". No **enumerated** required-context set is recorded in `report-01.md`, in `SKILL.md`, or
  anywhere else in the tree — only the negative fact that `license/cla` is not required, inferred from two
  merge-queue admissions. Re-derived at HEAD: `grep -n "required context" .claude/skills/cloud-plan-lane/SKILL.md`
  yields ten hits, all definitions and rules, never an enumeration.
  But the contract is not silent on the subject either, and this is the sharper half: `SKILL.md:150` states
  that a PR "produces the required `verify / conclusion` check", and `CLAUDE.md:21` says the same
  ("the required `verify / conclusion` check still reports green, so the merge queue admits it"). So the one
  required context this repository has is named twice in prose the run already reads — and **condition 1,
  the section that consumes required-ness, references neither**, while the affordances row at `SKILL.md:56`
  tells the run it cannot read the set at all.
- **Why it matters:** G2's derivation consumes this set directly, and every rule in condition 1 is phrased
  over it. A reader of condition 1 alone concludes the noun is unresolvable; a reader of § Step 2 already has
  its (apparently complete) value. Those two readings are inconsistent, which is how the D0 gate came to be
  satisfied by inference rather than by reading.
- **Fix:** Add one sentence to the `SKILL.md:56` "Ruleset-config API" row, after the existing "Read
  required-ness from `mergeStateStatus`": "On this repository the required context is `verify / conclusion`
  (§ Step 2, `CLAUDE.md` § Branch Naming) — **operator-maintained**, re-read whenever the `main` ruleset
  changes; a run never derives or extends this list for itself." Cross-reference that row from condition 1's
  `BLOCKED` paragraph as the approximation G2's disclosure may cite. This keeps the rule itself free of any
  named check (D1's Done-when) and keeps the list operator-owned rather than run-invented, which is what
  D0's STOP actually forbade.
- **Done when:** `SKILL.md:56` names the required context(s) for `main` with their provenance and an explicit
  operator-maintained / re-read-on-ruleset-change marker, condition 1 points at that row instead of leaving
  "required contexts" unresolved, and condition 1's own text still names no individual check — **or** a
  recorded decision states the set stays unrecorded, in which case `SKILL.md:150` and `CLAUDE.md:21` are
  corrected so no part of the tree claims to know it either.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Cloud session affordances / § Step 8 condition 1

## G4 — D1 shipped a disclosure obligation with no report artifact, and the Step-9 self-check passes without it

- **Kind:** omission
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1241-1243` — condition 1's non-required-context
  disclosure; `SKILL.md:1407` — the Step-9 contract-check "8 Merge gate" row; `SKILL.md:1456-1562` — the
  § Report required-content template
- **What is wrong:** D1 shipped the rule that a non-required context which is pending, failed, or absent
  "**does not block** the merge but **is disclosed** to the operator … State it in words before arming
  auto-merge". Nothing in the contract requires the report to evidence that this happened. The Step-9
  contract-check row for the merge gate (`SKILL.md:1407`) reads "Conditions 1–3 met and auto-merge armed …" —
  it demands no artifact for the disclosure. The § Report template (`SKILL.md:1456-1562`) has **no** merge-gate
  section at all: its required sections are Skills loaded, Deliverables, Build gate, Findings, Reviewer
  participation, Cost, Contract check, What have we learned, Residue. The asymmetry is exact and is what makes
  this a defect rather than a style choice: the **sibling** disclosure D1 was modelled on — condition 4's
  review-coverage shortfall — *does* carry a report obligation, at `SKILL.md:1530`: "State the coverage as
  N-of-M, and whether the § Step 8 shortfall disclosure fired and what it said." Condition 1's disclosure got
  the rule and not the receipt.
- **Why it matters:** This is the epic's own defect class. A run that armed auto-merge with a non-required
  check pending and said nothing about it produces a Step-9 contract check that reports "8 Merge gate: done"
  — a completed self-check that proves nothing about the disclosure it is supposed to attest. `report-01.md`
  § Merge gate item 4 did record the `license/cla` disclosure, but voluntarily, in a section the template does
  not ask for; the next run has no obligation to repeat it and no check that notices if it does not.
- **Fix:** Two edits, both in `.claude/skills/cloud-plan-lane/SKILL.md`:
  1. In the Step-9 contract-check table row `| 8 Merge gate |` (`SKILL.md:1407`), append: "and, where any
     non-required context was pending, failed, or absent at arm time, the report states which contexts they
     were and that the condition-1 disclosure was made — or states that every context on the head was green."
  2. In the § Report required-content template (`SKILL.md:1456-1562`), add a `## Merge gate` section between
     `## Reviewer participation` and `## Cost`, requiring: the `mergeable_state` read and the head SHA it was
     read at; conditions 1–3 with their evidence; and the condition-1 non-required-context disclosure verbatim
     (or "every context green").
- **Done when:** the "8 Merge gate" contract-check row names an artifact for the condition-1 disclosure, the
  § Report template has a section that artifact lands in, and a run that armed with a pending non-required
  context and did not disclose it is reported as **not done** at Step 9 rather than done.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — § Step 8 condition 1 / § Step 9 contract check / § Report

---

## Refuted during adversarial review

No gap was refuted in full. Two load-bearing **rationale clauses** were, and are recorded here because the
next reader must not re-derive the same wrong mechanism from the same two line numbers.

- **R1 — "`_github_pr.py:1631` is the *non-queue* auto-merge path, and the two paths are separated by an
  explicit queue-configured discriminator."** Asserted in the original G1 and in verification.md § D3.
  **Refuted by execution**, not by reading. `cmd_pr_auto_merge` (`_github_pr.py:1592`) is a single verb that
  runs on **both** kinds of base: it calls `_resolve_base_queue_state` *before* the `gh` call, forwards
  `f'--{args.strategy}'` unconditionally at line 1631, and uses the discriminator only **after** a
  zero exit, to label the outcome `enqueued` vs `enabled`. Executed with the probe forced to
  `MERGE_QUEUE_ELIGIBLE_CONFIGURED` and `strategy='squash'`: argv = `['pr', 'merge', '42', '--auto', '--squash']`,
  result `{'status': 'success', 'disposition': 'enqueued'}`. The discriminator therefore selects a *label*,
  never a command form, and 1631 is not a "non-queue path". Consequence: the tree does **not** corroborate
  D3's premise — it contradicts it, because this verb would be broken on a queue-gated `main` if `gh` rejected
  the flag. G1 survives as an *unsettled* question rather than a one-sided doc-drift, and is re-severitied to
  `low`. (Corroborating: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_merge.py:1349`
  asserts success + `disposition: enqueued` for exactly this configuration, with `strategy='squash'` as the
  namespace default at line 1320.)
- **R2 — "No positive required-context set is recorded in `report-01.md`, in `SKILL.md`, or anywhere else in
  the tree."** Asserted in the original G3. **Refuted by reading:** `SKILL.md:150` — inside the very same
  contract — states that a PR "produces the required `verify / conclusion` check", and `CLAUDE.md:21` states
  it again. What is genuinely absent is an *enumeration presented as the required set* and any link from
  condition 1 to the two places that already name it. G3 is rewritten around that narrower, true claim and
  stays at `low`.
