# PLAN-TRUTH-007: `normalize-keys` Reports `normalized` For Keys It Cannot Order — And `upgrade` Never Calls It

> Renamed from **PLAN-67** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced by the operator's 2026-07-25 `/marshall-steward upgrade` session
> (PR #1003), where a non-canonical top-level key order reached CI. Two defects in ONE causal chain,
> so they ship together: the canonicalizer cannot report what it failed to order, and the verb that
> should run it never does. Grounded at HEAD by the orchestrator, 2026-07-25.
>
> **GATED: do not emit until PR #1003 lands** — it is open on
> `chore/steward-landing-provisioned-version-1212` and touches this surface.

## Objective

`manage-config normalize-keys` claims to impose the canonical top-level key order on
`marshal.json`. It returns `action: 'normalized'` unconditionally — including when the resolved
version's `CANONICAL_TOP_LEVEL_KEY_ORDER` does not contain a key present in the file, in which case
that key is silently appended last. The caller is told the file was normalized; the file is not
canonical, and nothing names the key that fell through.

Compounding it: the `upgrade` verb's Stage 2 runs `sync-defaults` and `steps-sort` but **never**
`normalize-keys` — that call exists only in the interactive menu's Re-Run Remediation Pass. So the
one flow an operator uses after a version bump is structurally incapable of producing a canonical
key order. That is how the non-canonical order in PR #1003 reached CI.

Make the canonicalizer honest about what it could not order, and make `upgrade` actually call it.

## ⚠ Mechanism — OBSERVED, verified at HEAD by the orchestrator (2026-07-25)

- OBSERVED — `_config_core.py:96-114` `order_config_keys`: emits keys in
  `CANONICAL_TOP_LEVEL_KEY_ORDER` first, then `for key in config: if key not in ordered:` appends
  every unrecognized key afterwards (`:111-113`). The docstring frames this as deliberate
  preserve-don't-drop, which is defensible — **the defect is the signal, not the fallback.**
- OBSERVED — `_config_core.py:717-731` `normalize_keys`: `require_initialized()`, `load_config()`,
  `save_config(config)`, then `return {'action': 'normalized'}`. The return is a constant. It has no
  access to, and does not report, the set of keys `order_config_keys` had to append — so
  "normalized" is returned identically whether the result is canonical or not.
- OBSERVED — `save_config` (`:117-121`) routes through `order_config_keys`, so the append-last
  behaviour is on every write path, not just this verb.
- OBSERVED — `marshall-steward/references/upgrade-flow.md:294-306` Stage 2 `reconcile-config` runs
  exactly `manage-config sync-defaults` (`:299`) and `manage-config steps-sort` (`:303`). No
  `normalize-keys`.
- OBSERVED — `marshall-steward/SKILL.md:408-418` places `normalize-keys` as step **(a)** of the
  **Re-Run Remediation Pass**, reachable via the interactive menu. The `upgrade` verb bypasses the
  menu entirely (`SKILL.md:146-156`: "bypass both the mode routing and the Main Menu entirely").
- OBSERVED (operator report, corroborated by the above): a non-canonical key order reached CI on
  PR #1003 and was caught only by key-order tests.

## Deliverables

### D1 — GATE: settle the honest-signal shape and the reachability fix (mutates nothing)

Decide (a) what `normalize-keys` returns when unrecognized keys were appended — the epic's
established shape is a non-clean status naming the offenders (cf. PLAN-51's `sections_omitted`), so
prefer `action: 'normalized'` + `unrecognized_keys: [...]` with a warning-grade status over a bare
success; (b) whether an unrecognized top-level key is ever legitimate (a consumer project's own
block?) — if yes the signal is a warning, if no it is an error; (c) where `normalize-keys` belongs in
Stage 2's ordering relative to `sync-defaults` (which may ADD keys) and `steps-sort`. Ordering is
load-bearing: normalizing before `sync-defaults` adds a block would re-introduce the defect.

### D2 — `normalize-keys` names what it could not order

`order_config_keys` (or a thin sibling) reports the appended-unrecognized set; `normalize_keys`
surfaces it per the D1 verdict. A caller can no longer read `action: 'normalized'` and conclude the
file is canonical when it is not.

### D3 — `upgrade` Stage 2 runs the canonicalizer

Add `normalize-keys` to the Stage 2 `reconcile-config` sub-steps at the D1-decided position, so the
post-version-bump flow can produce a canonical order. Update the upgrade-flow doc and any emitted
`sub_steps` plan/manifest that enumerates Stage 2, in lock-step.

### D4 — tests

(a) A config carrying a top-level key absent from `CANONICAL_TOP_LEVEL_KEY_ORDER` produces the
D1-decided non-clean signal naming that key — never a bare `action: 'normalized'`. (b) An
already-canonical file stays byte-stable and reports clean (idempotence preserved). (c) Stage 2's
sub-step list contains `normalize-keys` at the decided position — pins D3 against silent removal.

## Expected surface

- OBSERVED: `manage-config/scripts/_config_core.py` — `order_config_keys` (`:96-114`),
  `normalize_keys` (`:717-731`)
- OBSERVED: `manage-config/SKILL.md` — the `normalize-keys` Canonical invocations block (return shape
  changes, and plugin-doctor reads this section as source-of-truth)
- OBSERVED: `marshall-steward/references/upgrade-flow.md` — Stage 2 (`:294-306`)
- OBSERVED: `marshall-steward/SKILL.md` — Re-Run Remediation Pass step (a) (`:408-418`), which must
  stay consistent with the new Stage 2 wiring
- HYPOTHESIS: the `upgrade — plan` emitter that produces Stage 2's `sub_steps` list — confirm/refute
  at `marshall-steward/scripts/upgrade.py` § the Stage 2 sub-step table (verify-at-outline). If the
  sub-steps are emitted from code rather than read from the doc, D3 must edit BOTH.
- OBSERVED: tests under `test/plan-marshall/manage-config/**` and the steward upgrade test module

**Disjointness:** `manage-config/_config_core.py` + `marshall-steward` docs. Disjoint from the four
in flight (PLAN-66 `manage-locks`, PLAN-53 `marshall-orchestrator`, PLAN-51 `plan-retrospective`,
PLAN-57 `manage-status/_cmd_planning_lane.py`) and from PLAN-TRUTH-008 (`tools-script-executor`).
⚠ **Adjacent to PLAN-47/48's shipped surface** — both touched `_config_core.py`'s
`CANONICAL_TOP_LEVEL_KEY_ORDER`; both are landed, so this is history, not a live collision.

## Notes

- Flagship archetype instance: a tool returns success while suppressing the caveat that makes the
  answer wrong — the same shape as PLAN-51 (`sections_omitted` under `success`), #979 (routed-build
  false green), PLAN-43 (architecture-find), PLAN-46 (title non-delivery).
- **Also a vacuous-guard instance, in the reachability half**: the Re-Run Remediation Pass documents
  normalize-keys as "silent, unconditional" — true within the menu, but the predicate never fires for
  anyone who upgrades via the verb, which is the normal post-bump path.
- The two halves MUST ship together. A loud normalize-keys that `upgrade` still never calls changes
  nothing; a wired-up normalize-keys that lies about its result just moves the false green.

## Second defect in the same surface — cache freshness is blind to upstream skew

**The defect (consumer-machine report, orchestrator-verified first-party):**
`marshall-steward/scripts/cache_freshness.py` `check_freshness` compares the cache against the
**local clone** manifest (`:163-174`) with **no upstream leg** — so a clone that is itself behind
makes both agree ⇒ `fresh`, `refuses_upgrade: false`, and the upgrade runs against a stale world
reporting "nothing drifted". Same shape as this plan's own defect: a green that is *locally
consistent* rather than *actually current*.

**On top of it, a vacuous-authority instance:** `references/upgrade-flow.md:157-161` asserts that a
sub-step "owns" cache-versus-upstream skew — **nothing implements it.** That is the same
documented-owner-implements-nothing shape this plan already closes for `normalize-keys`, which is the
substantive reason the two belong together.

**Deliverables for this half:**
- **GATE (mutates nothing) — decide what `fresh` is allowed to mean.** Settle whether an
  upstream-blind comparison may return `fresh` at all, or must declare inapplicability.
- **Implement the gate's verdict in the implementing source** — give `check_freshness` a real
  upstream leg, or make it declare its inapplicability rather than return a confident `fresh`.
- **Retire the vacuous ownership claim** — reconcile `upgrade-flow.md:157-161` to what is actually
  implemented.
- ⛔ **Correct the remediation text (operator, 2026-07-26): it is WRONG.** It says uninstall+install;
  `/plugin update plan-marshall` is sufficient and non-destructive, and must be followed by a
  version-verify step. ⚠ **The wrong guidance is TEST-ENFORCED** — `test_cache_freshness.py:235-237`
  asserts the literal uninstall/install strings. **Test-pins-the-defect: the test must be corrected
  with the text, and verified to FAIL against the corrected behaviour first.**
- **Tests** covering the upstream-skew path and the corrected remediation text.

⚠ Sequencing: prefer running **after PLAN-TRUTH-008** (`tools-script-executor` preflight), whose
residue this compounds — paired with the shipped PLAN-69, the version-freshness story still has no
end-to-end truthful signal.

⚠ **Split guard:** this fold takes the plan to roughly seven deliverables. **Evaluate a split at
outline and record the verdict** — do not proceed unsplit silently.

## ⚠ BOUNDARY 2026-08-02 — `PLAN-TRUTH-043` lands in this same file; split the ownership explicitly

`PLAN-TRUTH-043` (staged, from an API-Sheriff `marshall-steward upgrade` at 0.1.1286) targets
`manage-config/scripts/_config_core.py` — **this plan's file**. ⛔ **SERIALIZATION PAIR. Do not run
concurrently.**

Proposed ownership split, to be confirmed by whichever runs first:

| Concern | Owner |
|---|---|
| key-order canonicalization being unreachable / false-green | **this plan** |
| unguarded whole-document read-modify-write (lost update) | 043 |
| `order_config_keys`'s docstring asserting two routed write paths when **five sites exist and ≥3 bypass it** | ⚠ **contested — see below** |

⭐ **The contested row is genuinely ambiguous.** 043 found it while verifying the lost-update defect and
classified it as defending-documentation; but "writes that bypass the ordering authority" is *this
plan's* subject stated from the other side. ⛔ **Whichever plan runs first must claim or disclaim it
explicitly in its D0 and say so in its landing** — an unclaimed row between two serialized plans on one
file is how a defect survives both.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -043

**Component:** `manage-config (`_config_core.py` write path)` · **Deliverables after merge: 10** (raised cap is 12).

These two were already declared a **serialization pair on `_config_core.py`** with a **CONTESTED row**
between them — *"whichever runs first must claim or disclaim the ordering-bypass row in D0."* **The merge
resolves the contest by removing it.**

- **`-007`** — `normalize-keys` claims to impose canonical key order. ✅ **CONFIRMED at HEAD:
  `_config_core.py` returns `{'action': 'normalized'}` from a single unconditional return** — it reports
  success without establishing that anything was normalised.
- **`-043`** — every config write is a lost update waiting to happen, and `added_count` reports
  **intent** rather than effect (`sync-defaults` reported `success, added_count: 1` while adding nothing).

⭐ **Both are the same defect in one file**: *a config write reports what it meant to do, not what it
did.* `normalize-keys` returns `normalized` unconditionally; `sync-defaults` returns `added_count` from
the plan rather than the result. **One honest-return-value deliverable covers both**, which is why the
contested row was contested — it belonged to neither plan alone.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
