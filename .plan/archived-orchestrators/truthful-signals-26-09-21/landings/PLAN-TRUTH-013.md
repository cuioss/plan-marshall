# Landing Analysis: PLAN-TRUTH-013 — hook timeout unit confusion, and the R1 guard that ignores quoting

epic: truthful-signals
workstream: WS-01
pr: #1131 — merged as `6053382ab`

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as `6053382ab` via the merge queue | corroborated | `git log origin/main` — `6053382ab fix(platform-runtime): correct hook timeouts and R1 quoting (#1131)` |
| 10 files, platform-runtime only | corroborated | `git show --stat` — 10 files, 1800+/163−, entirely `platform-runtime/**` plus the two `marshall-steward` menu references |
| Plan archived, worktree removed | corroborated | absent from `manage-status list` |
| Row reconciled by the orchestrator | ✅ **yes this time** | the row was still `running` with empty result fields when this analysis began — **unlike #1132, nothing had pre-stamped it.** Recorded because it establishes that the #1132 crossing was not a general finalize behaviour |

## Deliverable Fidelity vs Spec

| Deliverable | Verdict |
|---|---|
| D1 correct the hook timeout literals **+ installer migrate-on-stale** | shipped, **widened correctly** |
| D2 make the R1 shell-construct matcher quoting-aware | shipped-as-specified |

### ⭐⭐ The fix that would have been vacuous, and the plan said so before shipping it

The three hook-entry builders emitted `"timeout": 5000` — a millisecond-shaped literal in a field Claude
Code reads as **seconds**, i.e. a bound 1000× larger than intended.

> **Correcting the literal alone would have been vacuous.** Both installers **dedup on the hook command
> string and never inspect `timeout`**, so every already-provisioned settings file would keep `5000`
> forever *while the test suite stayed green.*

⇒ The plan added a **migration arm** so an already-installed stale timeout is repaired in place. ⭐ This
is the epic's archetype caught **prospectively rather than in a retrospective**: a passing test over a
deployed state the fix cannot reach. ⛔ **The generalisable obligation is the second half — "already
deployed wrong value needs repair, not just a corrected emit site"** — and it applies to every
dedup-on-identity installer in the tree, not just this one.

### ⚠ D2 is a LOOSENING, and it changes how the tooling behaves for everyone

The R1 one-command guard matched shell metacharacters **with no quoting awareness**, so a metacharacter
*inside a quoted string* was read as a live compound-command operator and the call was denied. The fix
adds quote-masked views (`_quote_masked_views`) and corrects escape handling — an escaped newline is now
a line continuation.

⛔ **Calls previously denied for a quoted metacharacter now pass, and any assumption that "R1 denies
every `;`" is now FALSE.** Anything written to route around a quoted `;` no longer needs the workaround.
⭐ **This directly retires a standing note in the operator's own memory** (*"a literal `;` anywhere in an
argument trips the one-command hook"*) — corrected at the source rather than annotated beside.

## Metrics — and the cost mechanism is NAMED, which is the valuable part

**7.9M tokens / 109M billing-weighted, 7h11m worked over 9h38m wall — for a 10-file fix. Finalize was
70%.** ⚠ Per-phase figures stay retired as evidence; the mechanism below is not a per-phase figure.

⭐⭐ **The plan named the mechanism, and it is actionable:**

> Each settle-band fix commit **re-staled every `head_dependent` step**, so `lessons-housekeeping` ran
> **5×**, `plugin-doctor` **7×**, self-review **7×** — mostly re-confirming identical verdicts.

⛔ **And #1126 — *"perf(finalize): scope self-review and pre-push-gate re-runs to delta"* — had ALREADY
LANDED** (`72982d3d4`, before this plan's finalize). ⇒ **Delta-scoping the re-runs did not stop the
re-fires**, which means the cost is driven by the *re-stale trigger*, not by the *scope of each re-run*.
That is a different lever and it is currently unowned. **This is the single most valuable datum in the
landing for the token-reduction priority.**

### ⛔⛔ AND THE TWO LEDGERS UNDER-COUNT IDENTICALLY, SO CROSS-CHECKING THEM PROVES NOTHING

The retrospective found the re-fires **emit no `[STEP]` bracket**, so the **step ledger** and the
**dispatch-boundary ledger** under-count *the same events in the same direction*.

> **Cross-checking them looks like corroboration and isn't.**

⭐⭐ This is the sharpest methodological finding this epic has received: **two witnesses that share a
bias are one witness.** It is the same defect as the pin oracle counting the unmarked set as independent
corroboration of the registry — **second instance of the shared-bias-reads-as-agreement shape, in a
completely unrelated component.** ⇒ Folded into `PLAN-TRUTH-045`, which owns both ledgers.

## Routing and Merge Behavior

- **One phase-6 loop-back** (`6-finalize → 5-execute` at 18:17:18Z) executing **5 review-derived fix
  tasks** — triggered by automated-review findings, **not by a failed gate**.
- **17 findings, 0 pending at close.** 11 `pr-comment` all `fixed`; 6 `test-failure` auto-resolved by a
  later green build — five were installer/capture-entry tests, one was a `subprocess.TimeoutExpired`
  after 30 s on `architecture module`, an **infrastructure-flake shape, not a product defect**, cleared
  on re-run. ⭐ Naming the flake as a flake *and saying why* is the right treatment; a silent re-run
  would have been the wrong one.
- ⛔ **`pr-agent` — the only REQUIRED bot — returned `participated_but_empty` on BOTH rounds**, so review
  depth rested entirely on CodeRabbit and Sourcery (2 reviewers, 10 actionable comments, `10 → 0`).
  ⇒ **Fifth consecutive plan** in which the required-bot quorum was satisfied by a bot that produced
  nothing (#1122, #1123, #1125, #1132, #1131). Routed to `review-apparatus`.
- ⚠ **Judgment call, recorded as such by the plan**: the worktree was **force-removed** after
  `git worktree remove` timed out mid-deletion, on operator go-ahead, after enumerating the residue as
  build cache plus already-migrated `.plan/` state. ✅ Accepted — the enumeration before the force is
  what makes it acceptable, and it is the difference between this and a blind `-f`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1131` · `landing` = `landings/PLAN-TRUTH-013.md` · `plan_marshall_plan_id` = `hook-timeout-unit-confusion`
- [x] landing message `hook-timeout-unit-confusion-008.md` consumed and archived
- [x] the re-stale/`[STEP]`-bracket finding folded into `PLAN-TRUTH-045`
- [x] the R1 loosening propagated to the operator's standing note (corrected at source)
- [ ] the 7 queued `candidate-lesson` messages — **deliberately left for the next full drain**; `-055`
      and `-074` are still at 6-finalize and actively emitting

## Follow-Ups

1. ⛔ **Two residuals the plan routed rather than fixed, both outside its footprint:**
   - **`hook-authoring-guide.md`** still says eight render entries and denies `SessionStart:clear`.
     ⭐⭐ **Worse than first reported, and the reason is the interesting part**:
     `terminal-title-architecture.md` ruling **(a)** and ruling **(d)** *both* name that file in their
     "artifacts this ruling edits" lists — **(a) landed, (d) did not, and nothing distinguishes them.**
     ⇒ A document that records *which artifacts a ruling edits* but not *whether the edit happened*
     cannot answer "is this ruling applied?" — the file's own provenance is ambiguous by construction.
   - **Trigger-A re-review read `matched`/`timed_out` only** and therefore took a **CodeRabbit
     rate-limit refusal as proof of review.** ⛔ The producer *does* emit `head_sha_verified`,
     `matched_signal`, `refusal_detected` — **those fields appear in its code, its docs and its tests,
     and in NO consumer.** ⇒ A field set that exists, is tested, and is read by nobody: the tests prove
     the producer works and prove nothing about the signal reaching a decision. **PR/review subject ⇒
     routes to `review-apparatus`.**
2. **The unit-confusion class.** A literal whose unit is carried only by convention is the root shape;
   the durable half is the **migration obligation**. Worth a sweep for other dedup-on-identity
   installers — no plan owns it yet.
