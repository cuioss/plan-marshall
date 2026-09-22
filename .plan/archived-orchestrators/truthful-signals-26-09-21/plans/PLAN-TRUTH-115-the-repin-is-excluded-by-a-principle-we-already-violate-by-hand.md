# PLAN-TRUTH-115: The re-pin is excluded by a principle we already violate by hand, ~daily

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-26 on operator question: *"Can't this be fixed at the level of the synchronize step?
same like the regenerate executor"* — asked against the ~daily pin-gap prompt, now at **19 recorded
incidents**.

⭐⭐ **The proposal is correct and it was CONSIDERED AND REJECTED ON PRINCIPLE by a plan that shipped.**
This spec exists to re-open that one decision with the evidence that has accumulated since — not to
re-derive the mechanism, which `PLAN-TRUTH-059` already established and this orchestrator re-confirmed
first-party at `91a07aaa4`.

## Objective

**`PLAN-TRUTH-059` (shipped #1213) named this exact mechanism as its organising claim and then
deliberately scoped the fix OUT**, at its `## ⛔ Scope — the fix is not ours; the DETECTION is`:

> `installed_plugins.json` is **the plugin manager's file.** ⛔ **Do not write it, and do not propose
> writing it** — a third-party store with a second writer is `PLAN-TRUTH-049` with the plugin system as
> the other producer.

⇒ It shipped **detection only** (D1 detector, D2 mid-run assertion, D3 operator-facing remedy), with
D-list line 83 reading *"⛔ **Do NOT widen into fixing the registry**"*.

**Two things have since falsified the premise that exclusion rested on.**

⛔⛔ **(1) WE ALREADY WRITE THAT STORE — by hand, under time pressure, ~daily.** The exclusion frames the
choice as *"become a second writer, or don't"*. That is not the live choice. The live choice is
**"write it once per landing from inside a sanctioned script, or write it ad-hoc from an operator-run
temp script"** — `.plan/temp/repair-plugin-pin.py`, whose whole body is
`entry["installPath"] = str(CACHE / bundle / target)` over the `@plan-marshall` registry keys. The
second option is strictly worse and is what we do today: the epic records the repair script's own
**stale-hardcoded-`TARGET` trap firing three times**, and its `POST-CHECK FAILED: unmarked=[]` line
firing on a **successful** repair. ⇒ **The second-writer risk was not avoided by the exclusion; it was
relocated to the least reliable possible carrier.**

⛔⛔ **(2) THE DETECTION `-059` SHIPPED INSTEAD IS ITSELF DEAD.** `cleanup restart-check`'s
`registry_parity` signal reports **`not_available`**, is **excluded from the verdict floor**, and names
**`PLAN-TRUTH-059` — a CLOSED plan — as the spec that owns it** (epic W-088-d). ⇒ **We have neither the
fix nor a working detector**, and the one signal that would observe the gap is permanently
unobservable and attributed to a plan that cannot act.

⭐ **The operator's analogy is exact and is the shape of the remedy.** Executor regeneration already
rides the finalize sync step (`project:finalize-step-sync-plugin-cache`); `sync.py` itself only emits
`_regenerate_hint()`. The registry re-pin is **the missing third write at the same trigger**:
sync cache → regenerate executor → re-pin registry.

⚠ **State the ceiling honestly in the shipped doc.** A re-pin at sync time does **NOT** re-seat skill
bodies in an already-running session — that still needs a restart. What it fixes is that the gap never
**OPENS**: today every landing widens it by one version (W-088-b: *"one version per landing, confirmed
across two consecutive landings"*), so steady state becomes **zero** and a NEW session starts
consistent. Selling it as a fix for in-session staleness would be this epic's own theme.

## Deliverables

Four deliverables. D0 is a gate on the reversal itself.

**D0 — GATE: re-decide the `-059` § Scope exclusion, in writing, and record the outcome either way.**
⛔ **Do not silently reverse a shipped plan's recorded decision** — state it as a supersession naming
`-059` § Scope, the two falsifying facts above, and the verdict. If the exclusion is UPHELD, D1–D3 are
dropped and the deliverable is the recorded rationale plus an owner for `registry_parity`; the plan
still ships. ⚠ **The second-writer concern is real and must be answered, not waved past**: name what
happens when the plugin manager rewrites the entry between our write and the next read, and whether
our write is idempotent under that race.

**D1 — fold the re-pin into the sync step, at the same trigger as the executor regeneration.** Re-point
every `@plan-marshall` registry entry's `installPath` at the version the sync just minted. ⛔ **It must
report what it did** — the before/after version and the entry count — because a silent re-pin is
indistinguishable from a skipped one, and that is the failure this epic exists to close. ⚠ Read the
registry defensively: `-059` D1 established that **`unmarked == []` is a failure state too**, and the
epic has since RETIRED `unmarked == [pin]` as the oracle in both directions — **the gate is
`executor == installPath`**.

**D2 — retire `.plan/temp/repair-plugin-pin.py` as the operator path, or state why it survives.** If D1
lands, the hand repair becomes recovery-only, not routine. ⛔ **Do not leave both live without saying
which is authoritative** — two remedies for one fault is how the stale-`TARGET` trap fired three times.

**D3 — give `restart-check`'s signal vocabulary an honest not-applicable, starting with
`registry_parity`.** The signal exists, reports `not_available`, and points at a closed plan. Either
implement it or remove it — ⛔ **a permanently `not_available` signal excluded from the floor is a
detector that cannot fail**, which reads as health.

⭐⭐ **WIDENED 2026-08-27 by a fold** (from the `lessons-handling-26-08-26-01` cleanup pass, operator
paste, **reproduced first-party at `91a07aaa4`**): `registry_parity` is the only signal handled
correctly, and **the vocabulary it demonstrates is missing where it is needed.**
`cleanup restart-check --slug lessons-handling-26-08-26-01` returns `verdict: not_ready` whose **sole**
failing signal is:

```text
corpus_reconciliation,not_ready,19 row(s) without a spec and 0 spec(s) without a row,19 queue row(s) and 0 spec file(s)
```

⛔ **What it reports is what a ROUTER epic IS.** A lessons-drain epic stages no `plans/PLAN-*.md`
specs — its queue rows are routing decisions delivered as inbox messages — so `19 rows without a spec`
is the healthy steady state, not a gap. The signal has no notion of an epic that stages no specs, so it
cannot distinguish **a spec is missing** from **this epic has none by design**, and the floor over
participating signals renders a healthy epic `not_ready`.

⇒ **`registry_parity` is the shape to copy**: a `not_applicable` verdict, NAMED, excluded from the
floor, with its reason stated. ⚠ **The trigger must be derived, not assumed** — `specs_total == 0` on an
epic whose rows are all routing decisions, not merely `specs_total == 0`, or a real corpus that failed
to load becomes silently "not applicable". **That distinction is the whole deliverable**; getting it
wrong converts a true failure into an exclusion, which is strictly worse than today's false alarm.
⚠ Shares a root with `-113`'s 2026-08-27 fold (**both verbs assume every epic carries a spec corpus**),
but they are **separate call sites** — `cmd_corpus_cross_check` vs `cmd_cleanup_restart_check` — and the
reporter labelled the one-fix theory a HYPOTHESIS. ⛔ **Do not assume one fix serves both; verify at
outline.**

## Claim Labels

- OBSERVED: `PLAN-TRUTH-059` is `shipped` at PR #1213, and its `## ⛔ Scope` section forbids writing the registry in the words quoted above — read at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-059-….md`:52-59 and :83
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-059.md:52-56 Scope text matches verbatim (do not write installed_plugins.json); line 83 Do NOT widen into fixing the registry confirmed
- OBSERVED: nothing in the sync path writes the registry — a repo-wide sweep for `installed_plugins` across `marketplace/`, `.claude/` and `build.py` returns exactly ONE file, `pm-plugin-development/skills/plugin-script-architecture/references/notation-spec.md`, which is documentation and not a writer. Measured 2026-08-26 at `91a07aaa4`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Sweep of marketplace/ plus .claude/ for installed_plugins returns exactly 1 file, notation-spec.md -- documentation, not a writer
- OBSERVED: `sync.py` mints `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/` and emits `_regenerate_hint()` rather than performing the executor regeneration itself — read at `.claude/skills/sync-plugin-cache/scripts/sync.py`:7-17 § module docstring and :358 § `_regenerate_hint`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: sync.py docstring confirms the mint path plus _regenerate_hint helper; sync.py contains zero installed_plugins or installPath references
- OBSERVED: the operator repair's entire re-pin operation is one assignment — `entry["installPath"] = str(CACHE / bundle / target)` — read at `.plan/temp/repair-plugin-pin.py`:83
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: .plan/temp/repair-plugin-pin.py:83 reads entry installPath = str(CACHE / bundle / target) verbatim
- OBSERVED: the live registry currently pins `0.1.1556` across all 10 `@plan-marshall` keys with `lastUpdated: 2026-08-26T19:51:04Z`, while the cache holds `0.1.1547`, `0.1.1550`, `0.1.1554`, `0.1.1556` — so the registry is FRESH at this instant and a pin state is a snapshot, never a status (`-059`'s own standing caveat)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Version-pinned snapshot (0.1.1556); the current registry shows 0.1.1592 uniformly across all 10 keys -- the value has moved, only the snapshot-not-status point survives
- OBSERVED: `cleanup restart-check` reports `registry_parity` as `not_available`, excluded from the verdict floor, naming `PLAN-TRUTH-059` as owner — read at `plan-orchestrator/SKILL.md` § Canonical invocations → `cleanup restart-check`, and corroborated by the epic's W-088-d
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: orchestrator.py _registry_parity_signal always returns not_available naming REGISTRY_PARITY_OWNER PLAN-TRUTH-059, and is outside READINESS_ORDER so never scored
- HYPOTHESIS: the plugin manager rewrites `installed_plugins.json` on its own schedule (install, enable/disable, marketplace refresh), so our write is one of two producers and may be clobbered — confirm/refute at `~/.claude/plugins/installed_plugins.json` § the `lastUpdated` / `installedAt` field provenance across consecutive syncs (verify-at-outline). ⛔ **This is D0's central question and the strongest form of the `-059` objection.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to verify-at-outline; requires reading live plugin-manager provenance fields across consecutive syncs
- HYPOTHESIS: `sync.py` is a meta-project-only surface (`.claude/skills/`), so a re-pin folded there does NOT reach consumer projects of plan-marshall — confirm/refute at `.claude/skills/sync-plugin-cache/SKILL.md` § Bundle vs marketplace artifacts (verify-at-outline). If true, state the reach limit in the shipped doc rather than implying a general fix.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to verify-at-outline; not checked here
- OBSERVED *(2026-08-27 cleanup, first-party at `5f972ac15`)*: **D3's claim demonstrated, not argued.** `cleanup restart-check` returned **`verdict: ready`** with all five scored signals `ready` — on a machine whose plugin registry was **six versions behind** the executor (`0.1.1556` vs `0.1.1562`), a state this orchestrator had measured minutes earlier. The one signal that would have seen it, `registry_parity`, reported `not_available` and was excluded from the floor. ⇒ **A detector that cannot fail did not merely stay silent; it let a clean overall verdict be published over a genuinely unhealthy machine.** ⭐ This is stronger evidence than D3's original abstract argument, and it is the shape to cite when deciding between implementing the signal and removing it.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Version-pinned historical snapshot from the 2026-08-27 cleanup; not independently re-derivable now
- OBSERVED *(2026-08-27, first-party)*: `pm-code-intelligence` exists in `marketplace/bundles/` and in the cache (topping out at `0.1.1547`) but has **no key in `installed_plugins.json` at all** — so the repair script's `WARNING: pm-code-intelligence has no 0.1.1562 dir - skipping` is the script correctly declining to invent a pin for an unregistered bundle, not a gap it leaves open. ⚠ It also explains `sync-plugin-cache`'s "10 bundles" against 11 in source; **that pairing is consistent and is NOT drift.** ⛔ Do not scope work on it from this plan.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Current installed_plugins.json plugins map has zero pm-code-intelligence keys, confirmed this session
- Verify-first clause: before scoping D1, settle whether re-pinning while a session is live can BREAK that session (it resolves skills through the registry). If a mid-session re-pin can strand a running plan, D1 must fire at a quiescent point or be gated, and the deliverable re-scopes accordingly.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on D1 scoping; not yet executed
- OBSERVED: `2026-08-25-15-002` in full — the 8 findings, the rebase provenance, and that regeneration cleared them with **zero source edits**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: References the full content of an inbox message not independently re-derivable in this pass
- HYPOTHESIS: the two version-gap contradictions (`0.1.1240` vs `0.1.1541`; Branch B4's two contracts). ⛔ **Both are TITLE-ONLY STUBS** — `add` allocated them, `set-body` never ran, no body exists. Their titles name specific version numbers and a specific contradiction, which is what makes them usable at all. Confirm/refute by reading both paths' bodies at the named versions — `automatic-review/SKILL.md` § Producer: FIND for the `--enabled-bots` claim, and `phase-6-finalize/standards/lessons-capture.md` § Branch B4 for the landing claim (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Spec itself flags both as title-only stubs pending verify-at-outline; no body exists to check
- ⛔⛔ **These are VERSION-PINNED claims about a MUTABLE cache.** Whether they still hold depends on what has been synced since. **Verify against the pin state at the moment of outline, never against these version numbers.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Explicit caveat that pin state is a snapshot of a mutable cache, not a standalone checkable claim
- HYPOTHESIS: the served-path gap and the worktree-executor gap share a remedy. ⛔ **The router's inference from co-location, and it flags the doubt itself** — the two have different mechanisms (a **registry pin** vs a **per-worktree derived artifact**) and may not. Confirm/refute at outline. ⚠ **This plan's D0/D1 are about the registry pin; the worktree-executor half may need its own owner.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to verify-at-outline; not checked here

## Expected Surface

- OBSERVED: `.claude/skills/sync-plugin-cache/scripts/sync.py` — the mint path and `_regenerate_hint`
- OBSERVED: `.claude/skills/sync-plugin-cache/SKILL.md` — § Workflow Step 1/2b, and the reach limit
- OBSERVED: `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` — the finalize trigger
- OBSERVED: `.plan/temp/repair-plugin-pin.py` — the operator repair being retired or re-scoped (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `cleanup restart-check`'s `registry_parity` row (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/**` — if the preflight surface is the right home for the `executor == installPath` gate (verify-at-outline)
- HYPOTHESIS: `doc/developer/marketplace-build.adoc`, `doc/developer/manual-sync-recovery.adoc` — the recovery docs that name the hand repair (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none in the live queue — no staged spec declares `.claude/skills/sync-plugin-cache/`.
- Adjacent to: `PLAN-TRUTH-049` (shipped #1125, two producers write one marker field in two encodings) — the precedent `-059` § Scope invokes. D0 must read it: it is the argument AGAINST this plan, and answering it is the gate.
- Adjacent to: `PLAN-TRUTH-069` (shipped #1223, collapse the version-selection machinery) — same store family, already landed; check it did not settle part of this.
- ⛔ Supersedes a decision, not a plan: `-059` stays `shipped` and is NOT reopened or re-staged.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-115-the-repin-is-excluded-by-a-principle-we-already-violate-by-hand.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐⭐ FOLDED 2026-08-27 — the reframing that removes the judgement call, plus the worktree analogue

From the `lessons-handling-26-08-26-01` drain, message `-008` (3 lessons). Its suggested fold target
was `PLAN-TRUTH-059`, which is **SHIPPED** — this plan is that surface's live successor.

⛔⛔ **THE REFRAMING IS THE POINT: the pin gap is a CORRECTNESS hazard producing duplicate landings, not
a version delta.** `2026-08-25-09-001` records the served `0.1.1240` `lessons-capture` body saying
Branch B4 emits a landing **unconditionally**, while main-source says it emits **none**. ⇒ **Two agents
on the same repo at the same moment follow contradictory instructions, and the observable is a
DUPLICATE LANDING RECORD — not a stale doc.**

⭐ **Why that reframing matters for this plan's D0:** treating the gap as *"we are N versions behind"*
invites a judgement call about whether N is large enough to matter — and this epic's own operating
memory records grading the gap against the steps still ahead, twice. **Treating it as "two
contradictory contracts are simultaneously live" does not admit that judgement call at all.** Adopt the
second framing in the shipped doc.

**A second version-gap contradiction, same shape:** `2026-08-25-06-002` — dispatched agents load
`automatic-review/SKILL.md` from the **0.1.1240 registered-marketplace path** while scripts resolve
**0.1.1541**; the served body prescribes an `--enabled-bots` flag **neither script declares**, and
defaults the roster to a list **excluding the required bot**.

### ⭐⭐ The worktree analogue — a full body, a clean diagnosis, and a DIFFERENT mechanism

`2026-08-25-15-002`: `finalize-step-plugin-doctor` reported **8 `ARGUMENT_NAMING_NOTATION_INVALID`
findings** against a skill that arrived from upstream **during** `finalize-step-sync-baseline`'s rebase.
The worktree's generated executor predated it. **Regenerating cleared all 8 with zero source edits.**

⭐⭐ **The failure mode is NOT a false positive — it is an UNFALSIFIABLE verdict.** The finding can be
neither confirmed nor refuted against source, **because the substrate it was computed over no longer
matches the tree.** ⛔ Triaging it as a defect wastes the round; **triaging it as a false positive
records a refutation that was never established.**

⭐ **The diagnostic tell is cheap and reliable:** the findings name a component the plan's own diff never
touches. **That asymmetry — findings on untouched, newly-arrived files — distinguishes this class from a
real regression the plan introduced.**

⇒ **Regenerate the derived state after any rebase, BEFORE reading a single finding.** The general shape:
**a rebase moves SOURCE into the tree but does not move the DERIVED state built from it, and every gate
reading the derived state attributes the mismatch to the source file it is inspecting.** ⚠ Stated
impact: *"applies to every plan whose finalize rebases in upstream commits, which is most of them under
a busy main."*

## Claim Labels — folded 2026-08-27

> ↪ The bullets filed here on 2026-08-27 were merged into `## Claim Labels` above.
> `_parse_claims` reads ONE `## Claim Labels` section, so claims under a decorated
> second heading were structurally unstampable — the R97/R102 class, self-inflicted.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-154-operator-facing-authority-surfaces-that-answer-confidently-and-wrongly.md` (PLAN-TRUTH-154)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
