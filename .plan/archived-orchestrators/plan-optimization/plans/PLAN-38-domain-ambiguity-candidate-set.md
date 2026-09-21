# PLAN-38: Domain-Ambiguity Prompt Cannot Offer a Configured-But-Unmatched Domain

epic: plan-optimization
workstream: WS-10

> Staged 2026-07-21 from the same **consumer-repo run (API-Sheriff)** as PLAN-37.
> Mechanism labels per the binding practice (lesson `2026-07-21-22-001`).

## Objective

When domain detection is ambiguous, the operator is offered **only the domains the detector
already matched**. A domain that is **configured and mandated by the project but absent from the
narrative** is **not selectable** — the operator has to notice its absence and inject it by hand.

**Observed on a real consumer run.** Detection matched `java` and `documentation`, so the
multiSelect fired with those two options. `java-cui` is a configured domain and *"this project
mandates CUI standards throughout (CuiLogger/LogRecord, CUI test generator)"* — yet it was not
offered. The operator had to ask *"add java-cui as well?"* and the assistant then reasoned it in.
**A correct outcome reached by operator vigilance, not by the mechanism.**

## Root cause — OBSERVED (read directly from the contract)

`phase-1-init/SKILL.md` Step 7 defines two branches, and the option set differs between them:

> *"**Ambiguous** (`ambiguous: true`): … Fire a native **multiSelect** `AskUserQuestion` at this
> site, offering the **`candidates`** list as the selectable options … **When the detector
> zero-matched, `candidates` carries the configured non-system domains.**"*

and `candidates` is defined as *"the detector's narrative matches, offered as the multiSelect
options"*.

**So the fallback to "all configured non-system domains" exists — but only on the ZERO-match
branch.** On the **multi-match** branch the options are exactly the narrative matches, and a
configured-but-unmatched domain is unreachable through the prompt.

That asymmetry is the defect: the mechanism already knows the right wider set and declines to
offer it precisely when the operator is being asked to disambiguate.

## ⚠ What is OBSERVED vs HYPOTHESIS

- **OBSERVED**: the two branches and their differing option sets, quoted above from
  `phase-1-init/SKILL.md` Step 7; and the live consequence on the API-Sheriff run.
- **HYPOTHESIS**: that the right fix site is the **detector's `candidates` construction**
  (`manage-config` domain-detect) rather than the prompt-assembly prose in `phase-1-init`.
  **Confirm/refute artifact**: read the `domain-detect` implementation and establish where
  `candidates` is populated and whether the zero-match widening already lives there. If the
  widening is in the script, extend it there; if it is only in the SKILL.md prose, the fix is
  documentation plus whatever the script must return to support it. **Do not assume — the
  zero-match widening being script-side vs prose-side changes the whole fix.**
- **HYPOTHESIS**: that always offering the full configured set is acceptable UX. It may be noisy
  on projects with many domains. **Consider distinguishing the two groups visually** (detected
  candidates first, then "other configured domains") rather than flattening them — the operator's
  own phrasing (*"add java-cui as well?"*) suggests they think of it as an addition to the
  detected set, not a peer.

## Deliverables

1. **Settle the fix site (GATE).** Read the `domain-detect` implementation; establish where
   `candidates` is built and where the zero-match widening lives. Record the verdict; it
   determines whether D2 is a script change, a doc change, or both.
2. **Make configured-but-unmatched domains selectable on the ambiguous branch.** The multi-match
   prompt must offer the detected candidates **plus** the remaining configured non-system domains,
   so a mandated domain absent from the narrative can be chosen without operator improvisation.
   Preserve the existing union semantics (selections ∪ `always_on` ∪ `glob_matched`) — this
   changes only what is *offerable*, not how the result is merged.
3. **Regression covering the exact shape.** Detector multi-matches two domains while a third is
   configured and unmatched; assert the third appears in the offered set. Use the API-Sheriff
   shape (`java` + `documentation` matched, `java-cui` configured-but-unmatched).

Three deliverables, well under the split guard. D1 gates D2.

## Out of scope

- Do **not** rework detection itself — the detector matching only `java`/`documentation` from that
  narrative is defensible; the defect is what the *prompt* may offer, not what the detector finds.
- Do **not** make `java-cui` or any domain implicitly always-on for consumers. If a project wants
  a domain unconditionally, `always_on` already exists and is the correct lever; this plan does not
  substitute for configuring it. **Worth telling the operator**: API-Sheriff mandating CUI
  standards throughout may be an `always_on` candidate independent of this fix.

## Expected Surface

- `phase-1-init/SKILL.md` Step 7 (the branch contract and prompt shape)
- `manage-config` domain-detect implementation + its `candidates` field (locate at D1 — do NOT
  assume a path)
- `manage-config/SKILL.md` canonical block, if the verb's return shape changes
- tests under the manage-config suite

## Dependencies and Sequencing

- Depends on: none. **Emittable immediately** — disjoint from all four running plans.
- ⚠ **Adjacency cluster in `manage-config`**: **PLAN-35** (staged) touches `_cmd_build_map.py` /
  `_cmd_aspect_classify.py`, **PLAN-37** (staged) may touch `_config_core.py`, and this plan
  touches the domain-detect path. Three different files in one skill — check before running any
  two concurrently.
- Related: PLAN-25 (#965) shipped ADR-010 on domain-conditional loading and
  `ext-point-domain-verb`; its `references.domains` seeding is the consumer of what this prompt
  resolves. Re-ground against it at outline — a domain the operator could not select is a domain
  ADR-010's gating will treat as inactive.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-38-domain-ambiguity-candidate-set.md"

OBSERVED (read directly from phase-1-init/SKILL.md Step 7, not inferred): the ambiguous branch fires a multiSelect AskUserQuestion offering the `candidates` list, where candidates is defined as "the detector's narrative matches"; and the widening to "the configured non-system domains" is documented ONLY for the zero-match case. So on a MULTI-MATCH ambiguity the operator can only choose among domains the detector already found, and a configured-but-unmatched domain is unreachable through the prompt. Live consequence on a consumer run (API-Sheriff): detection matched java and documentation, java-cui was configured and mandated by the project ("CUI standards throughout — CuiLogger/LogRecord, CUI test generator") but was NOT offered; the operator had to ask "add java-cui as well?" and have it reasoned in. The correct outcome was reached by operator vigilance, not by the mechanism.

HYPOTHESIS, and deliverable 1 is the gate: that the fix site is the detector's `candidates` construction in manage-config domain-detect rather than the prompt-assembly prose in phase-1-init. CONFIRM/REFUTE ARTIFACT: read the domain-detect implementation, establish where candidates is populated, and determine whether the zero-match widening already lives script-side. If the widening is in the script, extend it there; if it exists only in SKILL.md prose, the fix is documentation plus whatever the script must return to support it. Do NOT assume — script-side vs prose-side changes the whole fix.

SECOND HYPOTHESIS worth testing rather than assuming: that offering the full configured set is acceptable UX. It may be noisy on projects with many domains. Consider presenting detected candidates first and remaining configured domains second rather than flattening them — the operator's own phrasing ("add java-cui as WELL") suggests they think of it as an addition to the detected set, not a peer of it.

OUT OF SCOPE, do not expand: do NOT rework detection itself — the detector matching only java/documentation from that narrative is defensible, and the defect is what the PROMPT may offer, not what the detector finds. Do NOT make any domain implicitly always-on for consumers; `always_on` already exists and is the correct lever for a project that wants a domain unconditionally. Preserve the existing union semantics (operator selections ∪ always_on ∪ glob_matched) — this plan changes only what is OFFERABLE.

Four plans run concurrently (PLAN-32 script-shared/build, PLAN-33 platform-runtime, PLAN-34 marshall-steward, PLAN-36 phase-6-finalize) — all disjoint from your phase-1-init + manage-config domain-detect footprint. ⚠ PLAN-35 and PLAN-37 are staged against OTHER files in manage-config (_cmd_build_map.py / _cmd_aspect_classify.py, and _config_core.py) — flag the adjacency if your work pulls you into either.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-38.md is recorded}
