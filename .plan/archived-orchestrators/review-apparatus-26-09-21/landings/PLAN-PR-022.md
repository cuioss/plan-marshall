# Landing: PLAN-PR-022 — A generic charter cannot see a language-specific defect

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-09
plan_marshall_plan_id: `generic-charter-language-specific-defect`

> Landing analysis. Every claim below is either CORROBORATED first-party by this orchestrator or
> labelled as the run's own report. The operator's run report is a **lead, not a fact**; where the
> two disagree, the corroboration wins and the divergence is recorded rather than smoothed over.

## Corroboration — all five landings verified from PR state

Verified via `gh pr view --json state,mergedAt,mergeCommit`, not from any merge command's return
value (the `#1081` false-green class). **All five MERGED.**

| Repository | PR | Merged (UTC) | Merge commit | Size |
|---|---|---|---|---|
| `cuioss/plan-marshall` | #1130 | 16:17:06 | `f5493b437` | +2258/−132, 28f |
| `cuioss/pr-agent-settings` | #14 | 18:19:32 | `1cc5af4ec` | +195/−7, 2f |
| `cuioss/cuioss-organization` | #237 | 18:19:58 | `7dc1890f0` | +23/−4, 1f |
| `cuioss/TokenSheriff` | #643 | 18:30:52 | `2297e081c` | +50/−0, 2f |
| `cuioss/API-Sheriff` | #202 | 18:36:29 | `3e8f7a73f` | +223/−0, 2f |

✅ **The dependency-order claim is EXACT.** D7's central config (18:19:32) landed **26 seconds**
before D6's label gate (18:19:58), so `/improve` gates on a config block that exists rather than
falling back to upstream defaults on the one path that writes into the diff. Corroborated to the
second, not accepted as narrative.

✅ **D8 verified at the artifact, not the commit.** `AGENTS.md` now resolves in both Java repos —
API-Sheriff 7657 bytes, TokenSheriff 9148 bytes. Both were previously unreachable to the reviewer:
API-Sheriff had none at all (its run log said `Repo context file is empty or missing: AGENTS.md`),
TokenSheriff had one under a lowercase name a case-sensitive container could never open.

⚠ Note the host PR landed **~2h before** the four foreign ones (16:17 vs 18:19–18:36). That ordering
is the visible signature of the finding-1 recovery below, not a sequencing choice.

## What the plan actually established, and what it did not

**Established.** The instruction gap is closed: the reviewer now receives domain-scoped vocabulary,
and the two Java repos have a context file it can read. The composed-pack shape holds any N-domain
pack at exactly ten categories, so the org's observed ten-category ceiling is respected **by
construction** rather than by discipline — and the regression guard was WIDENED to cover the composed
shape rather than relaxed to admit it. That is the right direction and worth recording as precedent.

**NOT established, and the spec said so in advance.** The spec labelled the causal claim
`HYPOTHESIS` and named its confirm/refute artifact. That verification remains **UNRUN**. The Java
zero-finding result has a plausible cause removed; it does not have a measured fix. The falsifiable
check is unchanged: re-review a closed Java PR that CodeRabbit found in-charter defects on —
**API-Sheriff#185** (26 CodeRabbit inline items) or **#154** (47) — with the pack installed, against
this reviewer's recorded zero on those same diffs.

⭐ **The spec's advance labelling is why this reads as an honest partial rather than an overclaim.**
The verify-first contract did its job here: a plan shipped, its premise stayed labelled, and the
landing can state the gap without re-litigating the scope.

## Findings this landing files

### F1 — ⛔⛔ Foreign-task done-ness is measured at the commit, and three of eight deliverables nearly shipped nowhere

Finalize completed with **four foreign branches committed and pushed and ZERO PRs opened**. Phase 5
recorded the gap correctly and three times — each artifact line ending in the literal words
*"PR not yet opened"* — and **every task still reported `done`**.

⭐⭐ **The mechanism, stated precisely: task done-ness is measured at the commit.** That is right for a
host task, where the PR carries the commit. It is structurally wrong for a foreign task, where
nothing does. **The log line naming the gap is read by no gate.**

The instance was recovered (all four branches re-verified on their remotes before PRs were opened),
but ⛔ **the mechanism is unchanged and will recur on the next foreign-repo plan.** This is the third
time this epic has been bitten by foreign-repo bookkeeping (PLAN-PR-002 is still parked on the same
class), and it is now a mechanism with a named cause rather than an incident.

⇒ **Staged as PLAN-PR-023.** It is not folded into an existing spec: no staged plan owns
task-completion semantics, and folding it into a review-apparatus spec would bury a finalize-layer
defect under a review-layer subject.

### F2 — ⭐⭐ The self-review gate caught the plan falsifying its own premise

Self-review hard-failed with four findings. The sharpest: `AGENTS.md` still enumerated the
generator's targets as `claude/opencode/all` **after this plan registered a third** — and `AGENTS.md`
is the exact file the plan had just made load-bearing as the reviewer's context source. **A stale
claim the reviewer itself would consume.**

⭐ All four were fixed by **describing sets by rule rather than adding another copy** (`e59f3ad96`) —
the same remedy shape as lesson `2026-08-08-21-003` (*restated counts are the blast radius; the fix is
deletion, not correction*), arrived at independently one day later. That is the second observation of
that remedy shape in two runs. ⭐ The re-run verified remedies **against the live tree** rather than
against the resolution records, which is the discipline that makes a green re-run mean something.

### F3 — ⛔ A file-scoped grep confirms a key exists and says nothing about the section being configured

`enable_intro_text` was set under `[pr_code_suggestions]`, where it **does not exist**. The key is
real but scoped to `[pr_reviewer]` — which is precisely why a file-scoped grep confirmed it and
misled. `enable_help_text` alone appears in **nine** sections with differing defaults.

⇒ **Rule: section-scope every key check in a sectioned config.** Generalises well beyond
`.pr_agent.toml` to any INI/TOML surface, and is cheap to apply.
⚠ This was the **third** research refutation of the run — the first two (`inline_code_comments` does
not exist at the pinned tag; `restricted_mode` gates only `push_code`) both landed in the spec's
favour, confirming the label gate was the correct and only route. A plan whose research refuted two
of its own design assumptions **before** implementation and a third during recovery is a plan whose
verify-first discipline was live throughout.

### F4 — ⛔⛔ The host PR merged with NO external reviewer having read the diff

PR #1130's quorum passed **vacuously**: the only required bot returned `participated_but_empty`,
CodeRabbit refused on a recoverable rate window, Sourcery on hard quota. **Zero comments meant no
reviewer produced content — not that a 27-file diff was clean.**

⛔⛔ **This is the empty-quorum shape for the THIRD time in three days** — #1118, #1122, now #1130 —
and it is now the epic's most-reproduced defect. It is already folded into **PLAN-PR-008** (D1 must
derive both directions) and **PLAN-PR-021** (the false-clean polarity). This landing adds the third
instance and, more usefully, the sharpest one: **the plan whose entire subject is review quality
merged without a review.**

⚠ Merging proceeded on the operator's explicit decision, recorded as a HEAD-bound, gap-class-bound
authorization naming what was and was not proven. That is the mechanism working as designed — the
gap was disclosed and consciously accepted, not hidden. ⭐ **The four foreign PRs DID draw real
reviewer participation**, so the host repo is the outlier, which sharpens rather than weakens F4.

### F5 — ⭐ A gate was re-fired rather than re-stamped, and the distinction was made correctly

Two finalize commits advanced HEAD past the quality gate's anchor. The first was documentation-only
with gates freshly run on byte-identical content → anchor **re-stamped**, reason recorded. The second
changed two Python files → gate genuinely **re-run** (61s quality-gate, 388s whole-tree tests).

⭐ Recorded as a **positive** precedent: that discrimination is the entire point of anchoring a verdict
to a SHA, and it is the first observation of the anchor being used to distinguish rather than merely
to block.

### F6 — ⚠ Merge-queue guards refused three merges that would have closed PRs unmerged

Three of five repos have required queues on `main`; in each case the CI abstraction **refused** the
direct merge — the `#1081` failure mode (reported success while deleting a branch) did not recur. The
two direct merges that did run returned real corroboration (`state=MERGED` with timestamp), not a
bare success flag. ⭐ Reads as the `#1087` remedy holding on a five-repo, mixed-topology run — the
first multi-repo exercise it has had.

## Divergences from the run report — corroboration wins

### D1 — ⛔⛔ "No registry pin file exists at any usual location" is REFUTED

The report attributes the cache split to an absent registry pin. **The registry exists and is
internally consistent.** First-party, double-sampled 14s apart with both samples agreeing:

| Consumer | Value |
|---|---|
| Registry `installPath` | `0.1.1331` |
| Registry `version` | `0.1.1331` ✅ (the 1326/1327 field split seen on 08-08 is GONE) |
| Executor | **`0.1.1334`** |
| Unmarked cache dirs | **`0.1.1331` AND `0.1.1334`** — two where one should be |

⇒ **The correct diagnosis is not "no pin" but "the pin and the executor disagree, and the unmarked set
contains both, so the loader may follow either."** That is **incident 14** of the `#896` trap, and the
remedy differs from the one an absent-pin reading implies: this needs **convergence on a named
version**, not pin creation.

⭐⭐ **Which version is settled by content, not preference.** The 1331↔1334 delta is four markdown
files, and one of them is
`automatic-review/standards/pr-agent.md` — **this plan's own shipped target surface**. So `1334` is the
post-#1130 sync and `1331` predates it. ⇒ Converge on **1334**: orphan-mark `1331`, move the registry
pin to `1334`, leaving `unmarked == [1334] == executor == pin`.
⛔ **Repair is operator-only** (classifier-blocked for the agent), and **only a full restart re-seats
skill markdown** — `/reload-plugins` does not.

⭐ **14/14: the gap contained the launching plan's own target surface.** This is no longer a
coincidence worth noting; it is a reliable property of the trap, and `pr-agent.md` is the cleanest
instance yet.

### D2 — the inbox carries 17 messages, not 13, and THREE are landings from this one plan

`inbox list` reports **17 queued, 0 invalid** — not the report's 13. Of these, **three are `landing`
messages from `generic-charter-language-specific-defect`**, written at 17:04:41, 17:52:24 and
18:38:03.

⭐⭐ **That is PLAN-PR-010's exact subject occurring live, and it is the best evidence that plan has
ever had.** PR-010 (`landing-message-carries-the-outcome-post-merge`) exists because a landing message
is composed before the outcome is known. Here the plan wrote its landing **three times** as the
outcome kept changing — once at finalize, once after the foreign PRs were opened, once after they all
merged. Only the 18:38 message can be authoritative, and **nothing in the channel says so**; a drain
that consumed 006 or 012 first would reconcile against a superseded outcome.

⇒ Folded into **PLAN-PR-010** as its first live multi-emission instance. ⭐ Note the interaction with
F1: the three emissions are the same root cause as the missing foreign PRs — an outcome that was not
final when the machinery declared it final.

### D3 — the report's own token caveat is correct and is preserved

The report states its token cells measure the dispatched-subagent population and that inline
main-context spend is not additively comparable. ✅ **Kept verbatim rather than summed.** Per the
standing rule, the three populations must never be added; the headline figures (4.78M / 102.6M
billing-weighted) are recorded as the report's own, unrecomputed by this orchestrator.

## Queue reconciliation

- **PLAN-PR-022 → `shipped`**, `pr=1130`, `landing=landings/PLAN-PR-022.md`,
  `plan_marshall_plan_id=generic-charter-language-specific-defect`.
- **PLAN-PR-004 (`pr-agent-charter-unverified-in-effect`) → RETIRED, absorbed.** The staging decision
  flagged it as a probable subset of D6; that is now confirmed — this plan shipped the charter's
  effective-state verification as its regression guard, plus the central config record. ⛔ Do not
  re-open; its residue is the unrun HYPOTHESIS check, which belongs to PLAN-PR-023 § verification, not
  to a separate charter plan.
- **PLAN-PR-023 staged** (see F1) — foreign-task done-ness measured at the commit, plus the unrun
  Java confirm/refute check as an explicit deliverable so the HYPOTHESIS does not lapse silently.
- **No parallelization collision.** PR-022 ran alone at R=1/N=1; nothing to record.

## Residue carried, not closed

- ⛔ **Five knowledge-type findings from the simplify sweep** — recorded, not applied (each touches a
  public element, user-facing string, or test-coverage claim). Most concrete and **CORROBORATED
  first-party in current main**: `marshall-steward/scripts/determine_mode.py:580-582` interpolates
  `entry["file"]` on BOTH sides of the `wrong_case` message, rendering the tautology *"AGENTS.md
  exists under a different case — rename it to AGENTS.md"*. ⚠ Note the irony worth keeping: the
  message that cannot tell you the wrong case is the one this plan needed while fixing TokenSheriff's
  wrong case.
- ⚠ **plugin-doctor ran scoped, not whole-tree** — 31 rules, zero findings over three touched skills,
  but scoped mode does not evaluate the cross-skill rule class, so a divergence there would first
  surface at CI.
- ⛔ **The Java confirm/refute check is unrun** (see above). It is the single most valuable follow-up
  this landing leaves.
