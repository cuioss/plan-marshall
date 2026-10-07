# PLAN-TRUTH-009: Config Knobs That Stay Unset Are Undiscoverable — Surface Every Knob in `marshal.json`

> Renamed from **PLAN-74** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged from an **operator design directive** (2026-07-26): *"We want to expose every possible knob,
> because the user has otherwise no chance of finding it."* The directive is not a new preference —
> it restates an **already-established house rule** the current code violates. Orchestrator-verified
> at HEAD.

## Objective

`DEFAULT_ORCHESTRATOR` seeds only `auto_emit`. The `effort` sub-block and the
`parallelization_scope` scalar are deliberately left unset so readers fall through to implicit
defaults — and a code comment documents that choice as intentional. The result is a knob that
**exists, validates, and is settable, but never appears in `marshal.json`**, so a user reading their
own config has no way to discover it. Materialise every seeded-able knob so the config file is the
discovery surface it is supposed to be.

## ⚠ Mechanism and rule-grounding — OBSERVED, verified at HEAD (2026-07-26)

- OBSERVED — `_config_defaults.py:199-201`: `DEFAULT_ORCHESTRATOR = {'auto_emit': False}`. That is
  the entire seeded shape; `sync-defaults` therefore writes only `auto_emit` into `marshal.json`.
- OBSERVED — confirmed live on a consumer at 0.1.1219 (operator-reported): its `marshal.json`
  carries exactly `"orchestrator": {"auto_emit": false}`.
- OBSERVED — confirmed live in this repo: `manage-config orchestrator get --field
  parallelization_scope` returns `value: null`, `set: false`, while the knob is fully implemented —
  validated (`_cmd_orchestrator.py:46-55`), settable (`ORCHESTRATOR_SCALAR_FIELDS`, `:43`), and
  consumed by the orchestrator's `next` verb.
- OBSERVED — `effort` is likewise a legal, writable key of the block
  (`validate_orchestrator_block` `known_keys = {'effort', 'parallelization_scope', 'auto_emit'}`,
  `:1139`; written by `_cmd_effort.py:565` via `config.setdefault('orchestrator', {})`) that never
  appears in a seeded file.
- OBSERVED — **THE HOUSE RULE THE CURRENT STATE VIOLATES.**
  `recipe-marshal-json-config-audit` **Aspect 1 — Default-surfacing completeness**: "Verify that
  every config default `setup` / `marshall-steward` is supposed to write is materialised in
  `.plan/marshal.json`. Trace each code-side default to the file and **flag any that exists in code
  but is absent from the file** (code-default-but-not-in-file gaps)." That is exactly this gap, and
  the recipe's prescribed deliverable — "materialises the missing defaults into `marshal.json`" — is
  exactly this plan.
- OBSERVED — **the violation is defended by a comment, which is why it survived.**
  `_config_defaults.py:1085-1096` states the unset-ness as deliberate design ("stay unset (implicit
  defaults) so … every orchestrator reader falls through to today's values"), and `:1278` repeats
  it. A reader auditing the block finds a rationale and moves on. **The comment must be CORRECTED,
  not preserved** — it currently documents a house-rule violation as an intentional design.
- OBSERVED — the fall-through values the comment describes are real and must be preserved
  behaviourally: `plan.effort` for the baseline effort of the read-only orchestrator surfaces, an
  unset-`max` no-op for the uplift ceiling, and a hard-coded `parallelization_scope` of 1.
  **Surfacing a knob must not change its effective default** — materialising `parallelization_scope: 1`
  must behave identically to leaving it unset.

## Deliverables

### D1 — GATE: settle what "expose every knob" means mechanically (mutates nothing)

The directive is clear in intent; the mechanics need one decision. Settle: (a) does every knob get
materialised with its effective default value (`parallelization_scope: 1`), or with a null/commented
placeholder? Value-materialisation is the reading Aspect 1 implies and is recommended — a `null`
placeholder is as undiscoverable as absence for the "what can I set?" question, and re-introduces
the fall-through ambiguity. (b) How is the `effort` **sub-block** surfaced, given it is a nested
shape rather than a scalar — the full default sub-block, or its scalar leaves? (c) Confirm the
no-behaviour-change invariant: a materialised default must resolve identically to an unset key, and
name the test that proves it.

### D2 — surface the orchestrator block's knobs

Extend `DEFAULT_ORCHESTRATOR` per D1 so `sync-defaults` materialises `parallelization_scope` and the
`effort` sub-block alongside `auto_emit`. Per `config-design-principles.md` **Rule 4**, a default
shape change must migrate **all three** config surfaces — enumerate them explicitly in the success
criteria rather than assuming the seeded copy is the only one.

### D3 — correct the comments that defend the gap

Rewrite `_config_defaults.py:1085-1096` and `:1278` so they describe the surfaced shape and the
default-surfacing rule, instead of presenting deliberate absence as correct design. Add the xref to
Aspect 1 / `config-design-principles.md` so the next reader meets the rule, not a rationale for
breaking it.

### D4 — sweep for other code-default-but-not-in-file gaps

The orchestrator block is the instance the operator hit; the rule is global. Run the Aspect-1 trace
across every `DEFAULT_*` block: for each code-side default, does it reach `marshal.json`? Produce
the gap list and materialise it. **Split guard:** if the sweep returns a large gap list, D4 splits
into its own plan rather than inflating this one — record the count at D1 and decide then.

### D5 — tests

(a) A seeded `marshal.json` contains every knob the D1 verdict says it must — the assertion that
fails against today's `DEFAULT_ORCHESTRATOR`. (b) The no-behaviour-change invariant: a materialised
default resolves identically to the unset key, for `parallelization_scope` and for `effort`.
(c) `validate_orchestrator_block` still accepts both the newly-seeded shape and a legacy file whose
block carries only `auto_emit` — **an existing consumer's file must not become invalid.**

## Expected Surface

- OBSERVED: `manage-config/scripts/_config_defaults.py` — `DEFAULT_ORCHESTRATOR` (`:199-201`), the
  commentary at `:1085-1096` and `:1278`, `validate_orchestrator_block` (`:~1130-1180`)
- HYPOTHESIS: the `sync-defaults` deep-merge path and `setup` seeding site — touched only if D1's
  shape needs merge changes rather than a bigger default dict (verify-at-outline)
- HYPOTHESIS: `doc/user/configuration.adoc` — Aspect 3 requires every surfaced key be documented;
  in scope only for keys this plan newly materialises (verify-at-outline)
- OBSERVED: tests under `test/plan-marshall/manage-config/**`
- HYPOTHESIS (D4 only): every other `DEFAULT_*` block in `_config_defaults.py` (verify-at-outline;
  the D1 count decides whether D4 stays here or splits)

**Disjointness:** `manage-config` (+ its tests, + a doc file). Disjoint from PLAN-69
(`script-shared`, `tools-script-executor`), PLAN-51 (`plan-retrospective`), PLAN-70
(`automatic-review`, `workflow-integration-github`), PLAN-55 (`phase-6-finalize`, `manage-lessons`),
and PLAN-73 (`marshall-steward`).
⚠ **OVERLAPS PLAN-TRUTH-007**, which edits `manage-config/_config_core.py` (key-order canonicalization) —
different file in the same bundle, but `normalize-keys`/`order_config_keys` acts on exactly the
shape this plan changes. **Sequence, do not parallelize**: a new seeded key must land against a
settled key-ordering contract, or the two will fight over canonical order.

## Dependencies and Sequencing

- **After PLAN-TRUTH-007** (gated on PR #1003) — TRUTH-007 settles canonical key ordering; this plan
  adds keys that ordering must then place. Running this plan first means TRUTH-007 re-canonicalizes a
  shape that just changed.
- No dependency on PLAN-47/PLAN-48 — both shipped, and **neither is implicated**: they delivered the
  block and its `auto_emit` knob correctly. This plan changes what gets *seeded*, not what exists.
- Independent of PLAN-73 despite both being consumer-provisioning findings — different bundles
  (`manage-config` vs `marshall-steward`) and different mechanisms.

## Notes

- **New archetype instance, and a notable one: a house-rule violation defended by a code comment.**
  Adjacent to PLAN-73's vacuous-ownership finding (a doc asserting a question is owned when nothing
  implements it). Same family: *documentation that makes a gap look intentional and therefore
  invisible to review.* Two independent instances found the same day argues the family deserves a
  named entry in the epic's archetype list.
- **Orchestrator self-correction, recorded deliberately.** On first analysis the orchestrator
  reported the consumer's `{auto_emit: false}`-only config as "correct and complete, not short",
  reasoning from `:1085-1096`. That was wrong: it took the code comment as the authority without
  checking it against the project's own config-governance rule. The operator's directive supplied
  the correction. This is the third recorded instance today of the orchestrator trusting a confident
  local statement over ground truth — the epic's own archetype, turned inward.

## Write-Boundary

Repository source + tests + user docs only; NO `.plan/local/orchestrator/` writes. See
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
