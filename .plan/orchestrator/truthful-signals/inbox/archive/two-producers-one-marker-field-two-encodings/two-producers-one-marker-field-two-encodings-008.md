envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=landing
created=2026-08-09T05:08:00Z

## What landed

**PLAN-TRUTH-049 — "Two producers write one marker field in two encodings, and one is not ours"** SHIPPED.

- **PR**: #1125 — `docs(orphaned-at): state existence-only invariant and fix D-1 pin-boundary confound`
- **Merged**: via the platform **merge queue (squash)** to `main` as `cf70cf7870f91044961fc874724525bf669bef91`
- **Landing verified from git state, not from a message**: the commit subject carries `(#1125)` and `git merge-base --is-ancestor cf70cf787 origin/main` exits 0. This is a real landing, not a `merged=true`-without-merge false green.

## D-1 verdict: OUTCOME (i) — our ISO `.orphaned_at` markers DO age out

The differential that outcome (ii) predicts is **absent**, and it was tested under a **matched control** rather than inferred:

- The same tree carries **both** encodings, so the foreign producer's **epoch-ms** format was the comparator — the control is matched by construction, not assembled after the fact.
- A **5.39d epoch-ms** marker and a **5.21d ISO** marker were **both still present** and **both in the sweep's `removed[]` partition**.
- Same tree, same sweep, same partition, two encodings ⇒ no encoding-dependent behaviour to observe.

**Consequence for the epic's backlog**: the inverted remedy — *"write epoch-ms to match the owning consumer"* — is **REFUTED, not deferred**. **No follow-up plan is owed for it.** Do not re-stage it.

### The bound, stated rather than hidden

The observable window is **capped at 5.39 days by OUR OWN sweep's dir-mtime pruning**, not by the foreign GC. So the finding's exact shape is:

> **no encoding differential within the observable window under a matched control**

It is **NOT** a proven expiry date, and it is not a claim about behaviour beyond 5.39d. A later reader who needs "when does the foreign GC actually expire a marker?" is still owed that measurement; what is settled is that *encoding* is not the variable.

## Deliverable outcomes

| Deliverable | Outcome |
|-------------|---------|
| **D0** | The second writer is **external — the Claude Code plugin GC**. Recorded as a **shared-field dependency**. |
| **D1 / D3 (in-repo half)** | The **existence-only invariant** is now stated at **BOTH** sanctioned read sites: the selector in `marketplace_bundles.py`, and the policy-duplicate mirror in `generate_executor._CLAUDE_RESOLVER_TEMPLATE`. The **correct retention model** is stated at its canonical home in `data-model.md`. |
| **D2** | A **population-derived** enforcement test fails if any consumer starts **parsing the marker's content**, with **matched controls proven to fire** (not a guard that can pass vacuously on an empty population). |
| **D3 (out-of-band half)** | **STILL OWED — see below.** |

## Residue the epic should track

### ⛔ D3's OUT-OF-BAND half is STILL OWED, and it is OPERATOR-OWNED

The in-repo half of D3 landed. **The deliverable is NOT complete on that half alone.** Two records carrying the now-refuted model live **only in the operator's memory store, outside this repository**, so no plan in this repo can correct them:

1. **`project_plugin_cache_orphan_gc.md`** — carries the *"7-day `.orphaned_at` retention / keep-oracle = no marker"* model. Superseded by D1/D3's existence-only invariant and by the D-1 verdict above.
2. **`project_plugin_registry_pin_orphan_inversion.md`** — carries the *"`.in_use` is the second marker that identifies the pin"* claim. Refuted.

**This cannot be closed by a plan.** It needs an operator edit to the memory store. Until then, the epic should carry D3 as **partially complete**, not done — the in-repo statement is correct while the two out-of-band records still teach the wrong model, which is exactly the confident-signal-hides-a-caveat theme this epic exists for.

## Run signals (for cross-plan context)

- `signal_qgate_pending_count: 8`, `signal_automated_review_count: 1`, `signal_script_failure_clusters_count: 0`
- Finalize-step notes worth a drain-side glance: `automatic-review` closed at *"2 comment(s) found (unified triage pending)"*, and `review-retrospective` reported *"3 bots compared, 4 actionable comments, **2 bots output never reached the store**"*.

## Already routed — do NOT re-file

`plan-retrospective` ran immediately before this message and already routed **6 `candidate-lesson` + 1 `finding`** to this epic as messages **`two-producers-one-marker-field-two-encodings-001` … `-007`** (including `-003` and `-007`). It **suppressed 8 of 14** candidates against existing coverage.

This `landing` message is deliberately the **only** additional item from this plan: the lesson/finding residue is already in the queue, and lessons-capture filed **zero** new candidates to avoid duplicating it.
