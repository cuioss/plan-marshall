# PLAN-TRUTH-075: the cloud lane's build gate reads one field short, and its report describes a build that ran as skipped

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from inbox message `review-apparatus-020`, routed here by the operator under the
> three-way rule: this is the standalone cloud plan lane's own build gate and run report — a signal that
> reads green over an unexamined condition — not a PR/review subject.

## Objective

`.claude/skills/cloud-plan-lane/SKILL.md` governs every plan executed from `doc/plans/`. Two of its
contract statements understate what they check, in the same direction: **toward reporting clean.**

## OBSERVED — first-party to `review-apparatus`, verified against current `main`

Both surfaced as unresolved CodeRabbit threads on **#1098** (the standalone-plan-lane PR), which merged
through the cloud lane — **a lane with no thread-resolution step, so its threads stay open regardless of
merit.** ⭐ The other 12 unresolved threads on that PR were checked and are **already fixed downstream**
(the hardcoded `/Users/oliver/…` path, the duplicate Step 8/9 labels, the LEDGER.md findings that died
with #1104's retirement). **These two are the survivors, re-verified against the file as it stands** —
they are not forwarded review comments.

### Finding 1 — the build gate omits `errors[]`, at TWO sites

`CLAUDE.md` states the rule plainly:

> After each build call, read the result TOON `status`/`errors[]` — the wrapper exits 0 even on failure.

The lane SKILL requires `status` and `total_issues` and **never mentions `errors[]`**, in both places it
states the rule:

| Site | Text |
|---|---|
| `:278` — the **per-commit** gate | *"Open the `log_file` it names and confirm `total_issues: 0`."* |
| `:376-377` — the **Step 5** build gate | *"Confirm the reported `status`, and open the `log_file` it names to confirm `total_issues: 0`"* |

⚠ **Two sites, not one.** A fix that corrects only Step 5 leaves the per-commit gate stating the weaker
rule — **and the per-commit gate is the one that runs most often.**

⭐ **Why this is the false-green shape and not a doc nit: the lane's own sentence concedes the premise** —
*"The wrapper exits 0 on failure, so the exit code proves nothing; only the log does."* It then names
**two of the three** fields that make the log conclusive. A build populating `errors[]` while reporting a
green `status` and `total_issues: 0` **satisfies the lane's stated check and is recorded as clean.**
The gate is one field short of the rule it is enforcing, and the missing field is precisely the one the
repository-wide rule adds.

### Finding 2 — the report records one of two build triggers

Step 5 defines **two** trigger surfaces deliberately, with a `> **Why the second row exists**` callout
noting that a markdown-only change can and does fail the build — *it is how the contract's own first PR
went red*:

| Changed | Run |
|---|---|
| Any `*.py` | `./pw verify` |
| No `*.py`, but any `.claude/skills/**` or `marketplace/bundles/**` | `./pw quality-gate` |
| Neither | record "no buildable footprint, build skipped" |

The run report's `## Build gate` section (`:693-695`) asks for **only the first**:

> The `git diff --name-only origin/main...HEAD -- '*.py'` verdict, and the build result — or
> "no Python changes, build skipped".

⇒ **A run that changed no Python, correctly ran `./pw quality-gate`, and passed it, reports the literal
sentence "no Python changes, build skipped".** The report says no build ran when one ran and passed.

⭐⭐ **The direction is what makes this ours: it is anti-correlated with the interesting case.** The
docs-and-skills-only change is exactly the run whose build coverage a reader would want to confirm, and
it is the run whose report is **guaranteed** to understate it. A reader auditing whether the plugin
surface was linted **cannot tell a genuine skip from a passed quality-gate**, and the report's own
vocabulary offers no way to express the difference.

⚠ **The two compound**: finding 1 weakens what *passed* means; finding 2 removes the record that a gate
ran at all.

## Deliverables

1. **D0 — GATE, and it decides this plan's severity, not just its wording.** Establish whether the build
   wrapper **can in fact emit a green `status` with a non-empty `errors[]`.** Read the wrapper's result
   construction. ⛔ **This is the claim `review-apparatus` explicitly did NOT establish and flagged as
   the discriminator.** If yes ⇒ finding 1 is a live false-green. If no ⇒ it is a defence-in-depth gap.
   **Either way the lane contradicts `CLAUDE.md`**, so D1 proceeds regardless — only the framing moves.
2. **D1 — add `errors[]` to the gate at BOTH sites**, `:278` and `:376-377`. ⛔ Fixing one is the
   documented half-fix.
3. **D2 — give the run report a vocabulary that can distinguish the three build outcomes**: `verify` ran,
   `quality-gate` ran, genuinely no buildable footprint. ⛔ **The current binary cannot express the
   middle case**, which is why it collapses to the understating sentence.
4. **D3 — a check that the two trigger tables cannot drift apart.** Step 5 defines three rows; the report
   section asks for one. **They are the same contract stated twice** — this epic's doc-contract-divergence
   archetype. Either derive one from the other or add the check that fails when they disagree.

**Four deliverables, one component.** ⛔ Resist widening into the lane's other steps: the operator routed
these two findings, not a lane audit.

## Claim Labels

- **OBSERVED (review-apparatus, first-party, verified against current `main` 2026-08-08)**: both quoted
  site texts and their line numbers; the `CLAUDE.md` rule text; the three-row Step 5 trigger table; the
  report section's single-trigger wording; that 12 sibling threads on #1098 are already fixed downstream.
  ⚠ **Second-hand to THIS orchestrator — re-verify the four line numbers at outline before scoping**;
  the file has been edited since #1098 and line numbers are the least durable part of the claim.
- ⛔ **NOT ESTABLISHED, and named as the gate**: whether the wrapper can emit green `status` with
  non-empty `errors[]`. **D0 settles it. Do not scope severity before it.**
- ⛔ **NOT ESTABLISHED**: whether any *shipped* run report actually mis-stated its build gate. Only that
  the template **requires** the understating form. ⇒ **Do not claim observed damage.**
- **HYPOTHESIS**: that no staged plan already owns this surface. Confirm/refute against
  `doc/plans/truthful-signals/` — ⚠ `030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one.md`
  exists and is **adjacent** (both concern gate signals) but names a **different** subject (required vs
  decorative checks at the merge gate, not the build gate's field set). **Verify-at-outline; fold rather
  than duplicate if 030 has since widened.**
  - verdict: contradicted | checked_at: 31211a99b | by: truthful-signals/cleanup | rescoped: yes | evidence: PLAN-TRUTH-092 (staged) declares the same file .claude/skills/cloud-plan-lane/SKILL.md in its Expected Surface; corpus cross-check now reports the overlap and could not before this pass because -092 wrote its heading as lowercase Expected surface (D-074-e). Subjects stay distinct - build gate here, merge gate there - so neither is superseded; re-scoped to a sequencing constraint in Dependencies and Sequencing

## Expected Surface

- **OBSERVED**: `.claude/skills/cloud-plan-lane/SKILL.md` — the per-commit gate (`:278`), the Step 5
  build gate (`:376-377`), the Step 5 trigger table, and the run-report `## Build gate` section (`:693-695`)
- **HYPOTHESIS**: the build wrapper's result construction — the D0 read; the exact module is named at D0
- ⛔ **NOT** `doc/plans/**` — this plan changes the lane's contract, never an individual lane plan.

## Dependencies and Sequencing

- **Depends on**: none. Disjoint from every currently-running plan (`-055`, `-070`, `-013`, `-074`).
- ⚠ **`.claude/skills/**` is the project-local surface** — a change here owes a `/sync-plugin-cache`, and
  per the standalone-lane carve-out a lane plan cannot perform one. **This plan runs in the ordinary
  lane, not the cloud lane**, precisely so it can.
- ⚠ Adjacent to `doc/plans/truthful-signals/030-…`; see the Claim Labels HYPOTHESIS.
- ⛔ **RE-SCOPED 2026-08-22 by `truthful-signals/cleanup` — the "no staged plan owns this surface"
  HYPOTHESIS is CONTRADICTED.** **PLAN-TRUTH-092** (`cloud-plan-lane-contract-and-run-report-accuracy`,
  staged) declares the same file — `.claude/skills/cloud-plan-lane/SKILL.md` — in its Expected Surface.
  ⭐ **The SUBJECTS remain distinct and neither plan is superseded**: this plan targets the **build
  gate** reading one field short (green `status` with non-empty `errors[]`); -092 targets the **merge
  gate** (§ Step 8 condition 1, the unreachable ruleset-config input, `mergeStateStatus` vs
  `mergeable_state`) plus run-report accuracy across 12 landed plans. Same file, different defects.
  ⇒ **SEQUENCE these two; do not run them concurrently.** -092 is the wider edit, so prefer landing it
  first and rebasing this one onto it.
  ⚠ **This collision was INVISIBLE until this pass.** -092 wrote its heading as `## Expected surface`
  and the surface reader matches case-sensitively (open defect **D-074-e**), so `corpus cross-check`
  parsed no surface for it and reported no overlap. The heading was normalised this pass and the
  overlap is now machine-detected.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-075-cloud-lane-build-gate-reads-one-field-short.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.


## ✅ HYPOTHESIS SETTLED 2026-08-09 — `doc/plans/truthful-signals/030-…` is PLAN-TRUTH-063's derived cloud plan

The spec carried: *"HYPOTHESIS: no staged plan already owns this surface … `030-merge-gate-…` exists and
is adjacent; verify-at-outline."* **Settled now, so outline does not have to.**

`030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one.md` is the **derived cloud plan of
`PLAN-TRUTH-063`**, which is its authored source record (per `doc/plans/cloud-bridge.md` § Path 1).

⇒ **Different gate, same file.** `-063` teaches the **merge** gate to tell a required status check from a
decorative one; this plan fixes the **build** gate's missing `errors[]` and the run report's
single-trigger wording. **No duplication** — but **both edit
`.claude/skills/cloud-plan-lane/SKILL.md`.**

⛔ **SERIALIZE against `-063`.** Whichever runs second re-grounds against the other's landing; they must
not be paired. ⭐ Note the asymmetry: `-063` already has an authored cloud plan and this one does not, so
if `-063` runs first this plan should re-check whether its own findings are better carried through the
same cloud-bridge path than as an ordinary-lane plan.
