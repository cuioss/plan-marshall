# HANDOVER — Token-Optimization Roadmap (live status + ordered queue)

> ## ▶ START HERE (fresh session, 2026-07-17 — full-scale cleanup)
> **The core token-optimization roadmap is CLOSED (finale plan-8 #899) AND the entire aggregated
> findings/lessons queue (P1–P9 + design-first SS) has SHIPPED.** What remains is a small, clean
> **wave-2 queue** of plans distilled from the open defects those landings surfaced (§4), plus P7
> (docs-contract), plus parked/deferred items. No cost-driver plans remain.
>
> **The plan-server epic (Rung 1 `plan-global-home-root` → Rung 2 `marshalld` build server) is
> tracked SEPARATELY in [`../plan-server/00-README.md`](../plan-server/00-README.md) — NOT in this
> doc.** It is the highest-leverage remaining work (it fixes the harness-killed-build / unrunnable-
> coverage class that dogged the whole wave), but it is not this roadmap's queue. Do not track it here.
>
> **A fresh session reads:** §4 (the wave-2 queue) → §5 (open defects held for data) → §6 (watches),
> and acts. §1–§2 are enduring context; **§3 is a pointer only — the full shipped record is in
> HISTORY.md Snapshots 1–4.**
>
> **Standing operator actions owed (not plans — one pass clears most):** `/marshall-steward` to
> (a) prune sunset `gemini` from `enabled_bots`, (b) RE-PROVISION the merge queue to SQUASH (P8 #919
> shipped the reconcile but every plan since rode the old MERGE queue — **per-repo**, meta + each
> consumer), (c) refresh stale `marshal.json` provisioning stamps. Also: shepherd **PR #924** (P6
> doc-residue) to merge; re-home the two consumer-filed plan-marshall lessons (nifi build-maven bug,
> API-Sheriff surfacer bug) under fresh native IDs; verify the 2 dormated-audit chores already shipped
> in #799 then strike them; **inspect the abandoned P9 worktree** left on disk after Rung 1's
> stale-merge-lock incident (`.plan/local/.../worktrees/metrics-corpus-integrity/`, no plan dir on
> main — P9 #922 already shipped, so it is very likely safe to remove, but confirm before destroying).

**Full historical record:** [`HISTORY.md`](HISTORY.md) Snapshots 1–3 (the roadmap proper, #811→#899)
+ [`HISTORY-snapshot-4-queue-wave.md`](HISTORY-snapshot-4-queue-wave.md) (the TAIL + orchestrator
#915 + the P1–P9/SS wave, #906→#922). Topic detail: the `project_*_shipped` memories indexed in
`MEMORY.md`.

**Convention:** one plan document = one command — every queued plan is a self-contained spec under
[`plans/`](plans/), run with `/plan-marshall task="implement .plan/plan-optimization/plans/<doc>"`.
Once a plan RUNS its spec doc is FROZEN (late fallout → follow-up doc or §5 row). Every plan retires
its folded lessons at landing and updates §3-pointer/§4/§5 here + `00-README.md`.

## 1. The effort in one paragraph

A token-usage audit of the plan-marshall corpus (lesson `2026-06-30-08-001`, 58 plans) found ~73%
of every plan's tokens are framework overhead around the edit, a hard ~1.0M-token per-plan floor,
and that the *edit* is the smallest cost bucket. The dominant fixable drains were
dispatch-multiplication bugs and finalize's N find-and-triage dispatches — not sizing knobs. The
lane feature (#811) right-sizes *which* steps run; the roadmap plans fixed *how many contexts*
the rest costs.

## 2. Design contract + current verdict

**Target dispatch topology (operator decision, 2026-07-05 — every plan aligns to this):**
1-init INLINE in main context (shipped #862) · 2-refine/3-outline/4-plan exactly ONE
execution-context each, operator input BATCHED (plan-1 invariant) · adversarial validators
(q-gates, automatic-review, self-review, security-audit) are the only sanctioned sibling
dispatches · lane pruning composes on top (#811) · finalize consolidated (one find → one
ingestion → ONE triage → one respond; script ci-verify — P2 #920 unified the per-producer triage).
"Coalesce phases 1–4 into one leaf" is RETIRED — do not resurrect (rationale: HISTORY §2).

**Verdict as of 2026-07-17:** the lane/routing machinery is DONE (light lane, minimal/auto/full
postures, escalation ratchet, classify-before-route — all proven live). At-target proof ×2: #866
(1.11M, minimal) and #883 (1.17M, `auto` incl. bots). Targets: surgical ≤1.2M · single_module ≤1.5M
· multi_module ≤2.5M (comparable basis, native since #876 D6). **Both original cost drivers are
addressed:** (1) leaf-backgrounded builds — plan-6 D6 (#893) compose-time `execution_tier` guard
(one residual: the INITIAL-envelope call site, now queued in `manifest-compose-gaps`); (2) finalize
wait-loops under queue traffic — plan-8 #899 consolidated the wait onto the Monitor primitive.
**The one remaining structural cost is topological:** a dispatched-leaf phase can't sub-dispatch its
adversarial validator, so self-review/automatic-review run INLINE (#893: 1.44M / 52% of a 4.2M plan)
— now queued as `leaf-validator-yield` (§4). Everything else is bounded correctness fixes.

**Scope-bloat guard (operative):** outline >~6 deliverables → SPLIT. Prose, not machinery — the
operator enforces it at the outline gate.

## 3. Shipped — POINTER ONLY

> **The full shipped record is archived — nothing actionable here.** The token-optimization roadmap
> (#811→#899) is in [`HISTORY.md`](HISTORY.md) Snapshots 1–3. The post-roadmap TAIL, the
> `marshall-orchestrator` epic (#915), and the entire P1–P9 + SS aggregated-queue wave (#906→#922)
> are in [`HISTORY-snapshot-4-queue-wave.md`](HISTORY-snapshot-4-queue-wave.md). At-target proof:
> #866 (1.11M minimal), #883 (1.17M auto incl. bots). Open follow-ups spawned by shipped plans live
> in §4 (queue) and §5 (defects), NOT here.

## 4. The queue (wave 2)

**Operating rules:** NO concurrency cap (operator, 2026-07-12) — pair by surface disjointness, not
count. Second finisher pays one rebase-revalidation; shared-file pairs resolve by rebase. Every
landing analysis actively checks for parallel-execution optimizations (§6). Era stamp is a
DELIVERABLE resolved pre-push (wired `project:finalize-step-era-stamp-fill`).

### ▶ Startable now — 4 plans, grouped by disjoint surface for parallelism

| Plan (GROUP) | Surface | Absorbs (from §5) | Command |
|---|---|---|---|
| **manifest-compose-gaps** (MANIFEST) | `manage-execution-manifest.py` + `_manifest_rules.py` + phase-4 compose | P4-C1 aspect-wiring (docs-only plans STILL build — the real product defect); #897 initial-envelope `execution_tier` guard gap | `…/plans/plan-manifest-compose-gaps.md` |
| **finalize-step-integrity** (FINALIZE) | phase-6-finalize step scripts + bodies | plugin-doctor scoped-vs-whole-tree false-green; self-review surfacer whole-tree-scan; P1 arm-6 freshness-gate; `prepare_execute` re-entry idempotency | `…/plans/plan-finalize-step-integrity.md` |
| **leaf-validator-yield** (EXEC-CONTEXT) | `execution-context` topology + step body/topology docs | dispatched-leaf can't sub-dispatch its validator ⇒ self-review runs inline (1.44M/52% cost, #893) | `…/plans/plan-leaf-validator-yield.md` |
| **P7 docs-contract-consistency** (DOCS) | phase-6 SKILL.md prose + config-knob docs + persona standards | `loop_back_without_asking` HALT-vs-doc + `*_without_asking` family + stale `auto_merge_after_ci` + diagnosis-discipline standard | `…/plans/plan-docs-contract-consistency.md` |

**Parallelism:** **MANIFEST ∥ EXEC-CONTEXT ∥ {FINALIZE or DOCS}** run fully concurrently (3 disjoint
surfaces). FINALIZE and DOCS both touch phase-6 → **same GROUP** — run them serially, or accept one
rebase for the second finisher (their file overlap is small: FINALIZE edits step scripts, DOCS edits
SKILL prose). So **up to 3 concurrent cleanly, 4th follows or rebases.**

> **⚠ Anti-orphan discipline (learned the hard way — P1, P2, P6 each shipped without the follow-ups
> parked on them).** These 4 plans' `Absorbs` lists are CONTRACTS, not "may absorb at outline." If an
> outline drops an absorbed item, it must say so explicitly and re-home it — silent de-scoping is what
> created the orphan pile in the first place.

### Parked / deferred (not startable as-is)

| Item | State |
|---|---|
| **ci-pr-safe-merge** | RESUME (parked at 3-outline; not a new doc). `/plan-marshall plan=ci-pr-safe-merge`. Merge-queue surface (#869/#897); org-wide bypass deferred→steward. |
| **Consumer migrations** | DEFERRED by operator (2026-07-16). `upgrade-regen-safety` #908 un-gated them — run `/marshall-steward upgrade` from inside each consumer, one at a time. Order: **API-Sheriff first** (the repo Leg B bricked ⇒ sharpest acceptance test), then cui-jsf-test-basic, TokenSheriff, nifi (now free). No unattended reminder exists (steward warn is pull-only) — candidate small item: upstream-availability warn. |
| **TT terminal-title stale `build-busy`** | `title_token=build-busy` (🔨) is plan-scoped state with no phase-transition reset. **Re-scope at outline: BK #912's state-gate-first wake path may already have dissolved the dangling case.** `…/plans/plan-terminal-title-stale-build-busy.md`. |

### Handed OFF to the plan-server epic (tracked in `../plan-server/00-README.md`, NOT here)

Two open defects are worktree-context-resolution bugs on exactly the credentials-dir / change-ledger
surface Rung 1 just relocated (Rung 1 SHIPPED #923, but WITHOUT fixing these — they're Rung-1
follow-ups now) — so they belong to the plan-server epic, not this queue:
- **credentials `--scope all` over-broad enumeration** during sonar-token resolution (TokenSheriff #577) → narrow to the specific provider; relevant to Rung 1's cred-dir move + plan-server S4.
- **build-maven `kind=build` ledger auto-append NO-OPs in worktrees** (nifi #454) → same surface as BK #912; may mean the truthful-status/`classify-outcome`/freshness machinery reads an incomplete ledger. Verify the change-ledger append path's worktree-CWD-vs-git-common-dir resolution.

## 5. Open defects — held for data (NOT yet plan-worthy)

> **§5 lists ONLY open defects NOT in a plan.** Everything that graduated to a spec doc has been
> MOVED into that plan (see §4's `Absorbs` column) and struck from here. Resolved rows: HISTORY
> Snapshot 2 §5. The plan-server-routed items are in §4's hand-off block, not duplicated here.

**Consumer lesson re-home (bookkeeping) — structural fix SHIPPED, residue owed.** The manage-lessons
wrong-store REFUSAL guard shipped as P6 #921 D3 (future writes can't mis-file). But two already-filed
plan-marshall bugs sit in consumer stores and need re-homing under fresh native IDs (never port by
ID): the build-maven ledger no-op (in nifi's store) and — if a lesson was captured — the self-review
surfacer bug (API-Sheriff). Small manual task.

- **Tier-1 recipe floor rejects pre-diagnosed surgical requests** — recipe tier COLD post-#875
  (2 wrongful rejections: #881, #883). Severity LOW (`signal_set` delivers the identical seed).
  **Held for data** — recalibrate the SHAPE floor or retire the recipe tier as redundant belt on a
  3rd occurrence.
- **Self-review surfacer blind to template STRING-CONSTANT pairs** (`2026-06-30-20-001`, recurrence
  #3; open residue of the #894 cache-resolver work). **Plan-worthy on a further recurrence.** (Note:
  distinct from the surfacer *file-scope* bug now in `finalize-step-integrity` D2 — this is about
  WHAT the surfacer can see inside a file, not WHICH files it scans.)
- **⚠ COUNTER-EVIDENCE to `00-README` headline finding #3 ("refine is conditional, mostly
  confirm-work") — KEEP, do not act on finding #3 without re-deriving it.** Six consecutive tail
  plans showed refine/outline invalidating the *source premise*, which is load-bearing, not
  confirm-work: **#911 (WT)** shipped ZERO production code because the outline falsified the premise
  (the requested gate already existed); **#906 (EV)** dropped 2 invalid premises pre-code; **#909**
  contradicted the filed issue on 3 code-verified points ("the issue's own fix would have left the
  symptom intact"); **#908** injected a root cause the frozen spec never carried; **TokenSheriff
  #572** caught 2 blocking Q-Gate premise errors pre-code. The n=58 corpus measured refine against
  mostly-sound premises; the tail is premise-lossy (queued docs age, filed issues are hand-written,
  lesson IDs go stale). Confidence ≥95% measured the *plan's* confidence, never the *input's*
  validity — different quantities. Do not make refine conditional on that basis.

## 6. Watches (not plans; plan-worthy on recurrence — closed watches: HISTORY Snapshot 2 §6)

**Standing checks at every landing:**
- **Finalize wait-loops under queue traffic — ADDRESSED by plan-8 #899 (Cluster B).** Residual watch:
  confirm the D6 before/after delta is a real reduction (not re-shaped waits) on post-#899 landings.
  Driver history (for calibration): #881 (69%), #884 (~7.8h), TokenSheriff #565 (~79% finalize / 66%
  total — largest), #575 (54%), #576 (docs-only, lighter). The #868 BACKGROUND ci-wait was repeatedly
  harness-KILLED → the Monitor primitive is the reliable path (BK #912 hardened this).
- **Sibling-collision detector**: 1 confirmed same-file miss (pr-strategy ∥ steward). Armed live test
  fired CLEAN at #893 init (F∥6 rebase auto-resolved). No 2nd miss; not yet plan-worthy.
- **CHECK_ERA is a serial conflict point** (#876/#877, #881/#883/#884, #885 rebases) — era-stamp-fill
  should make stamps conflict-free (append-safe), not just automatic.
- **base_branch init-detection gap + silent reconcile heal** (LOW/verify): `base_branch` defaults to
  hardcoded `main` at init rather than detecting the remote default; `_maybe_auto_update_stale_base_branch`
  then silently heals `main`→`master`. Same "config must be authoritative" principle. Fix direction:
  detect the remote default at init/steward; make the heal loud/config-checked. **Candidate fold into
  P7** (config-authoritative doc-contract family) if it recurs.
- **Merge queue** serializes landings cleanly (×10+) — watch for new contention classes (lock-wait,
  rate-cap throttling, staleness pileups). **Active drift:** MERGE-vs-squash until re-provisioned (§START-HERE).
- **Routing-render guard** scans only literal `--aspect` keys (`2026-06-20-17-003`, n=1) — plan-worthy
  on a 2nd occurrence.

**Dated / acceptance watches:**
- **plan-17 barrier standing check**: every PR merge shows the pre-merge comment-completeness barrier
  active — a merge with unread bot comments is now a REGRESSION. (⚠ Gemini-sunset grind until pruned.)
- **Worktree staleness** (3 obs, all graceful — #885 latest). First non-graceful → promote to a plan.
- **Merge lock not released at archive** (1×, #879). Recurrence → release-on-archive-barrier fix.
- **Outline silently drops a spec deliverable** (1×, #863; candidate Q-Gate check). **NOTE: this
  recurred as the orphan-pile pattern** — P1/P2/P6 each dropped parked follow-ups at outline. The
  wave-2 `Absorbs`-as-contract discipline (§4) is the mitigation; promote to a Q-Gate check if it
  happens again despite that.
- **Post-remediation re-verify leg falls off the CI abstraction** (1×, TokenSheriff #560). Adjacent
  class (#565, `2026-07-14-00-001`): flipping a secure default in shared cui-http transport needs
  EVERY runtime consumer's config opted back in (a missed quarkus surface went CI-red, skipITs-gated
  locally). Plan-worthy on a meta recurrence.
- **Run-session bookkeeping drift**: 1 skip (#876) vs full compliance. Wire lifecycle steps into the
  manifest only on a 2nd skip.

## 7. Standing operating constraints

- **Retire-what-you-replace, completely.** Every plan that removes/restructures a dispatch/step MUST
  sweep the dead config surface (`_config_defaults.py`, marshal.json seed, `configuration.adoc`) AND
  all concept docs describing the old behavior (grep old payload keys tree-wide; enumerate, don't
  sample). Clean-slate, no deprecation shims.
- **Folded lessons MUST leave the corpus when their plan lands** (`manage-lessons remove --force` with
  a coverage-citing reason). A folded lesson still active after its plan landed is a bookkeeping defect.
- **Landing-analysis routine** (each landed PR): read the archived plan's metrics.md + logs/decision.log;
  verify deliverable fidelity vs the traveled spec doc; verify folded-lesson retirement; check the era
  stamp landed with the REAL PR value; check routing lines + merge-queue behavior; reconcile
  §3-pointer/§4/§5 here + memory; respect the frozen-doc rule when folding fallout.
- **Absorbs-as-contract** (new, 2026-07-17): a plan's `Absorbs` list is a commitment. An outline that
  drops an absorbed item must say so and re-home it — never silently.
