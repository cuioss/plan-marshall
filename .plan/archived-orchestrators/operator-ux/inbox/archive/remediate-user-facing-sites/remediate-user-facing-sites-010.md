envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:49:00Z

component=plan-marshall:plan-marshall
category=bug
created=2026-09-08
source_plan=remediate-user-facing-sites
source_signal=automated-review

# Triage has no route to `rejected`, so an in-triage refutation is recorded as `taken_into_account` and generalized into the opposite hint

## What was observed

PR #1447 (plan `remediate-user-facing-sites`) carried 29 `pr-comment` findings. Nine were resolved `taken_into_account`; **zero** were resolved `rejected`. Two of the nine are not "considered and folded in" — they are explicit refutations, and their own `resolution_detail` says so:

- `43956d` — CodeRabbit *Security & Privacy / Major*, CWE-78 OS command injection on `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md:303`. Recorded rationale: *"The CWE-78 External reachability classification does not hold here: `branch_name` resolves either from `git symbolic-ref` or from the operator's own free-text answer to their own wizard prompt in their own session, so there is no external input crossing a trust boundary."*
- `8d8a87` — CodeRabbit *Security & Privacy / Major*, CWE-78 on `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:929`. Recorded rationale opens: *"Not applied — assessed on the merits and **found to be a false positive** whose proposed remedy would be a net regression."*

Both refute the finding's premise. Neither is a deliberate tolerated tradeoff, and neither is a standing concern the project folds into its work.

## Root cause — the workflow offers no correct disposition, so this is not an operator slip

`manage-findings` declares `rejected` and reserves it for a refuted false positive: *"set by the validity-verification (`ext-point-verify`) stage when it refutes a finding as a false positive."*

But `plan-marshall:plan-marshall/workflow/triage.md` — the workflow that actually decided these two — has **no action body that produces `rejected`**:

- Step 3b's batched outcome vocabulary is `FIX | SUPPRESS | ACCEPT | ASK_USER_QUESTION`.
- Step 3c's action bodies resolve `fixed`, `suppressed`, `accepted`, or `taken_into_account`.
- The Step 3b-pre reconciliation guard and the Step 3c passage-absent path both prescribe `taken_into_account`.
- The Step 4 and Step 6 option tables offer only `taken_into_account` / `accepted` / `fixed`.
- The single occurrence of `rejected` in the whole document is Sonar-only and verify-conditioned (Step 3c, `do_transition == true`: *"or `rejected` when the verify pre-stage already refuted it"*).

So when no verify pre-stage refutes a `pr-comment` finding, a triager who assesses it and concludes "false positive" has only `taken_into_account` available. The triager picked the closest available value correctly; the vocabulary is what is wrong. Step 1's note — *"refuted false positives are already non-pending and never appear in the pending query"* — assumes the verify pre-stage is the only place a refutation can occur, and on this run it was not.

## Why the distinction is load-bearing, beyond bookkeeping

**1. It writes the inverse of the refutation into the architecture-hints store.** `phase-6-finalize/standards/disposition-to-hint-routing.md` § (a) maps `taken_into_account` to *"the project repeatedly folds this finding class into its work as a standing concern"*, generalized as an **insight**: *"the project treats {finding-class} as a standing consideration in {module}"*. `rejected` appears nowhere in that table and produces no hint.

Both findings are admissible preference evidence — they carry `bot_kind: coderabbit` (a present, recognized reviewer identity, so § (e) admits them on either basis) and both carry a `file_path` that resolves to a real module, so § (d)'s unattributed-`default` drop does not catch them either. The recurrence key `(module, CWE-78 shell-interpolation, taken_into_account)` therefore stands at 2 and is gated only by the surface-owned threshold. If it clears, the pipeline enriches `enriched.json` with an insight asserting that the project treats command-injection findings as a standing consideration in exactly the two places it explicitly established they do not apply — and that insight surfaces in every future `phase-3-outline` `## Architecture Hints` section. The refutation does not merely fail to be recorded; it is inverted and amplified.

**2. It makes reviewer value unmeasurable.** With 0 findings on `rejected`, the measured reviewer false-positive rate for this PR reads **0%**. Counting the two refutations against the 23 substantive code findings (29 total less 6 review-status / acknowledgement records) gives **~8.7%**. Anyone later assessing whether a review bot earns its slot reads the wrong number, in the direction that flatters the bot.

## Proposed corrective

Give `triage.md` an explicit refutation route so a disposition the store already declares is reachable from the workflow that needs it:

1. Add `REFUTE` to the Step 3b batched outcome vocabulary, defined as *the finding's premise is factually wrong* — distinct from ACCEPT (a real issue tolerated) and from `taken_into_account` (a real issue folded in as a standing concern).
2. Give it a Step 3c action body that applies no source edit and resolves `--resolution rejected` with a reviewer-ready `resolution_detail`, so the RESPOND loop still transmits the reasoning to the PR thread.
3. Add a fourth option to the Step 4 deferral table — *"Refute: recorded as a false positive; nothing changes and the finding does not count as a standing concern"* — so an escalated refutation has somewhere to land too.
4. State the discriminator once, where the vocabulary is defined: **`taken_into_account` asserts the finding is real; `rejected` asserts it is not.** Any rationale whose text refutes the premise belongs on `rejected`.

## Verification

The two mis-recorded findings on PR #1447 should be re-resolved `rejected`, and any preference recurrence already derived from them re-computed — otherwise the inverted insight lands regardless of the workflow fix.
