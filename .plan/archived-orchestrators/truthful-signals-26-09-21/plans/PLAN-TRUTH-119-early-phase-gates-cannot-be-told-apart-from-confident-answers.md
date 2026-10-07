# PLAN-TRUTH-119: Early-phase gates cannot be told apart from confident answers

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from the `lessons-handling-26-08-26-01` drain, message `-011` (3 lessons). ⚠ The
router grouped these **by shape, not by surface**, and said so: they span three phases and three
components, and it invited a re-cut. **D0 owns that decision.**

## Objective

**Three gates in phases 1–4 produce output that cannot be distinguished from a confident answer when
they in fact examined nothing, decided nothing, or bound nothing.** This is the epic's theme at the
front of the lifecycle, where a wrong answer is cheapest to fix and most expensive to carry.

## Deliverables

1. **D0 — GATE: decide the cut before implementing.** The three members span `1-init`, `2-refine` and
   `3-outline`/`4-plan`, and share a shape rather than a surface. ⛔ **Either justify one plan or split
   into per-phase plans and re-stage** — do not implement three unrelated components under one brief
   because a router grouped them. Record the decision either way.
2. **D1 (1-init) — the domain detector cannot distinguish a match from a floor.** It returned
   `plan-marshall-plugin-dev` and nothing else with **zero narrative matches**, resolved purely from the
   `always_on` leg — on a plan whose realized footprint is **7 of 10 `.py` files**, whose request names
   `github_pr.py` throughout, and whose Verification section mandates the repo Python build. ⭐ The
   `always_on` leg is a **reasonable failsafe** that guarantees a non-empty domain set — and that is
   exactly why a zero-match result and a confident single-domain result produce the **identical output
   shape**. ⇒ Publish match provenance (`narrative_matches: N`, and `source: always_on` vs
   `source: narrative` per domain), the way `manage-lessons list-stalled` publishes `store_resolution` /
   `plans_root_state` / `scanned_plan_count` beside its count. ⚠ **Had the operator not been prompted,
   the plan would have run with `python` absent from the domain set that governs skill resolution.**
3. **D2 (2-refine) — a 100% confidence score cannot be validated at the time it is produced.** A
   post-clarification re-analysis scored **all six dimensions at 100**, lifting a plan 49.0% → 100.0% in
   one operator round. The Step 13 check flagged it — **which is the check working** — but has no
   mechanical discriminator between a genuine 100% and a self-graded one. ⭐ **The generalisable part is
   how that instance WAS resolved: against downstream evidence.** `phase-3-outline` re-ran the
   population sweep and the 3-outline Q-Gate re-derived it a third time, both reproducing it exactly
   **including corrections to two counts the original request had wrong**. ⇒ Have the check name the
   **evidence class** its justification rests on — `self-assessment` / `operator-answered` /
   `downstream-reproduced` — rather than accepting free prose. **Only the latter two are independent.**
4. **D3 (3-outline / 4-plan) — an ordering asserted in prose is inert.** The Approach section stated
   deliverable 1 is the gate and runs first; deliverable 2 declared `depends=none`. ⛔ **`phase-4-plan`
   orders tasks from `depends` metadata, never from Approach prose** — so the gate gated nothing.
   ⭐ **Prose reads as a constraint and is consumed by a human reviewer as one, which is exactly why it
   survives review; the machine that would enforce it never sees it.** ⇒ Authoring rule: any ordering
   claim in an Approach section MUST be encoded in the corresponding `depends` field **in the same
   edit**. Prose may explain an ordering; it may never be the only place the ordering exists.
5. **D4 — a deterministic Q-Gate for D3, because that instance was caught by an LLM pass and not a
   rule.** Scan Approach narrative for ordering language naming a deliverable, and cross-check for a
   corresponding `depends` edge; a prose-asserted edge with no metadata counterpart is a finding.
   ⭐ Preserve the good practice the same lesson records: the fix did not stop at the flagged field — a
   **symmetric-peer audit of all four `depends` fields** confirmed the rest were correct as authored.

## Claim Labels

- OBSERVED: all three instances, each quoting its own gate output or Q-Gate finding id — `2026-08-26-05-005`, `2026-08-08-19-007`, `2026-08-08-19-008`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D1 grounded; its exact defect (a zero-match resolved via always_on alone) is now FIXED at _cmd_domain_detect.py (commit 87782159b adds always_on/glob_matched/source/reason)
- OBSERVED: `2026-08-26-05-005` additionally corroborates against the realized footprint via `git diff 8025b2210^ 8025b2210`, so its 7-of-10 figure is measured rather than asserted
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: git diff --stat 8025b2210^ 8025b2210 shows 7 of 10 changed files end .py, matching the cited figure
- HYPOTHESIS: `2026-08-26-05-005` is a **reporting** gap rather than a **matcher-vocabulary** gap. ⚠ **The lesson itself flags these as two different defects needing two different fixes and does not settle which applies.** Confirm/refute at the narrative matcher against that specific request text (verify-at-outline). ⛔ Shipping only the provenance fields when the matcher is the real defect would make the failure legible and leave it live.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Requires the original plan request text (matcher-vocabulary vs reporting-gap); not in this checkout
- HYPOTHESIS: the three belong in one plan — ⛔ **the router's grouping by shape, explicitly offered for re-cutting.** D0 settles it.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D0 grouping-by-shape is an orchestrator staging call, not a code fact to corroborate
- Verify-first clause: before D2, settle whether `phase-2-refine` has any downstream signal available AT refine time. If it does not, the deliverable is the evidence-class label plus an explicit statement that refine cannot self-validate — never a new score that also cannot be validated.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: phase-2-refine structurally precedes phase-3-outline and 4-plan in the fixed phase sequence; no downstream signal can exist at refine time

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — the domain detector and its result shape (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-2-refine/**` — the confidence-scoring check and its Step 13 (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/**` — the `depends`-driven task ordering (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/**` — the Approach section contract and the D4 Q-Gate host (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-lessons/**` — `list-stalled`'s provenance-field pattern (expected READ-ONLY, the model being copied) (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — the deep lane’s exit condition, added 2026-09-04 by the drain fold of `documented-invocations-...-013` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py` — the section-scoped request read (D1), added 2026-09-11 by the fold of `lessons-handling-26-09-04-01-054`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_change_type_heuristic.py` — the section-scoped request read (D1), added 2026-09-11 by the fold of `-054`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/` — `recipe-match` / `aspect-classify` gaining `--request-file` (D1 secondary), added 2026-09-11 by the fold of `-054` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — the Tier-1 q-gate skip keyed on `recipe_key`, added 2026-09-11 by the fold of `-028` part A

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-093` (preference admissibility is prose where the auditor has code) — same *prose-is-not-binding* shape at a different surface. Check at emit whether D3/D4 belong there instead.
- Adjacent to: `PLAN-TRUTH-104` / `-116` / `-117` / `-118` — the sibling verdict-honesty classes. D1's remedy (publish provenance beside the count) is the same move `-117` D3 makes for set-guarding detectors.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-119-early-phase-gates-cannot-be-told-apart-from-confident-answers.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-08-31 — inbox drain (1 message(s))

- **`git-artifact-scanning-and-destructive-recovery-004.md`** — Intersect each deliverable's declared file surface with the plan's own out-of-scope boundary

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`dual-homed-hook-install-renders-identically-006.md`** — *premise verification must publish the claim SET it checked, beside its verdict.*

  `phase-2-refine` logged at `2026-09-02T15:18:01Z`:

  ```
  [REFINE:3] Source premise verification: 4 claims checked, 4 valid, 0 invalid
  ```

  Twenty minutes later `phase-3-outline` logged:

  ```
  Root-cause check refuted half the request premise: the hook check already
  discriminates the dual-homed case in prose at _claude_runtime_impl.py:2100 and
  an existing test pins it; only the display check renders identically.
  ```

  ⭐⭐ **Both statements are true.** The refine line is true of the four claims it took; the outline line is true of the request. **But `4 valid, 0 invalid` reads as a verdict on the premise, and the premise was half wrong.** Nothing in the refine record says WHICH four claims were checked, so a reader cannot tell whether the refuted claim was examined and passed or was never in the population.

  ⭐ **The sender names it as this epic’s own archetype committed by a gate: a confident count over an unpublished population.** The verification publishes its result (`4 valid`) and its size (`4 claims`) but **not its membership**, and does not state what fraction of the request’s assertions the four represent. A check that examines a subset and reports a clean total over that subset is indistinguishable, from the log alone, from one that examined everything.

  **The ask:** emit one line per checked claim with its verdict, plus an explicit statement of what was NOT checked (or a derivation of the request-assertion population the four were drawn from). ⛔ **Where the population cannot be enumerated, say so — an unenumerable population makes `4 valid, 0 invalid` a FLOOR, not a verdict.**

  ⚠ **Outcome note, and it is load-bearing for scoping:** the refutation WAS caught before any code was written and correctly narrowed the plan. **The machinery worked.** This fold is about the earlier gate’s wording, not about a missed defect — do not re-scope it into a claim that refine failed.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-013`** — *a deep-lane outline reached its Q-Gate with an EMPTY assessment substrate and nothing upstream noticed.* The plan routed `planning_lane: deep` — **the lane whose discovery pass is what normally files `CERTAIN_INCLUDE` assessments** — ran its outline, and arrived at the gate with **zero** assessments filed. Q-Gate `270654`: `assessment list --certainty CERTAIN_INCLUDE` returns `total_count: 0` with `findings_store_state: 'present'` — ⭐ **the store was genuinely resolved and scanned, and it is genuinely empty**, which is the discriminator working exactly as designed.

  ⭐⭐ **The gate’s handling was EXEMPLARY and is NOT the defect** — it refused to report green over a population it never had, named the substrate explicitly, and recorded validator 2.2 (Assessment Coverage) and Step 5 (Missing Coverage) as **UNEVALUATED rather than passed**, emitting no per-file findings because *“26 findings derived from an empty reference set would assert a conclusion the substrate cannot support.”*

  ⛔ **The residue is UPSTREAM — the plan reached that gate at all.** The remedy applied was manual (24 `CERTAIN_INCLUDE` + 3 `CERTAIN_EXCLUDE` filed at triage, each grounded rather than asserted), **which means the next deep-lane plan whose discovery pass files nothing depends on a reviewer noticing the same thing again.**

  ⭐ **The ask is one count against one field, at the point the lane ends:** a `planning_lane: deep` outline completing with `CERTAIN_INCLUDE` at `total_count: 0` over a **present** store is a lane that did not run its discovery pass — **derivable at lane exit from data the lane already has.** Report it where the lane ends rather than letting two downstream validators discover it as an absence.

## ⭐⭐ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (0 contradicted, but D1 IS ALREADY SHIPPED)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts. This is an
**applicability** change: nothing was refuted, and the plan is smaller than it was.

⭐⭐⭐ **D1's EXACT defect is FIXED, by a commit in this branch's own recent history.**
`manage-config/scripts/_cmd_domain_detect.py` at commit **`87782159b`** ("stop treating always_on-only
as plan evidence") now publishes `always_on`, `glob_matched`, `candidates`, `source` and `reason` —
**including the `over_provisioned_always_on_only` reason token.** That is precisely the
provenance-and-remedy shape D1 asks for: a zero-match resolved via `always_on` alone is now
distinguishable from a real match.

⇒ **D1 is retired with a positive account** (the commit and the named fields), not on the strength of
an absent symbol. ⛔ **Re-derive the remaining deliverables against the post-`87782159b` tree before
emitting** — a spec whose lead deliverable has shipped is a different plan, and its split-guard count
should be re-taken.

⚠ **Claim 4 corroborates a STRUCTURAL fact that survives any fix**: `phase-2-refine` precedes
`3-outline` and `4-plan` in the fixed phase sequence, so **no downstream signal can exist at refine
time**. That is the durable half of this spec and is unaffected by the shipped D1.

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (3 Token-Sheriff items, one per member)

Verified read-only at HEAD `356973d80`.

### D1 — the classifiers read a truncated body on the file-pointer path (`-054`)

On the phase-1-init file-pointer branch the spec is ingested verbatim under `## Original Input`, and any
real spec carries its own `##` headings. OBSERVED: both `manage-config/scripts/_cmd_domain_detect.py`:79-83
and `manage-status/scripts/_cmd_change_type_heuristic.py`:183-185 select a section through
`parse_document_sections`, so each reads only the lines before the spec's first embedded heading.
Measured at the sender on a 15 KB / 39-path spec: `domain-detect` → 0 alias matches →
`over_provisioned_always_on_only` (a `javascript` domain on a Java + AsciiDoc plan);
`change-type-heuristic` → every score 0.0, `ambiguous: true`, `change_type` unset, so the lane router's S3
signal could not fire. The controlled comparison is in the same run: `scope-estimate-heuristic`, already
**documented heading-blind**, read 39 paths correctly. ⇒ **The fix exists in this codebase for exactly one
of three sensors** — propagate it; do not invent one. Both wrong answers are well-formed `status: success`
verdicts indistinguishable from "nothing matched": this member's archetype exactly.
Secondary limb: `manage-config recipe-match` and `aspect-classify` accept only `--request-text`, so a
shell-hazardous spec (93 hazardous lines here) forces the caller to score a paraphrase — which the
file-pointer workflow forbids. A `--request-file` flag closes it.

### D3 — an ordering asserted in prose is inert: a second instance, at phase 4 (`-034`)

An operator TDD directive ("tests observed failing before the production change") was derived into
TASK-1 (implementation) + TASK-2 (tests, `depends_on: [TASK-1]`) whose description said to observe the
tests red first. The queue runs `depends_on`, so the red can never be observed. **Exactly D3's archetype**,
one phase later than its first instance. The executor reported the gap honestly; a less careful one would
have reported "TDD followed". Remedy menu from the sender: invert the dependency (test task first,
completion criterion = an observed assertion failure) or one task whose steps carry red → green; and
**never emit a description whose prose ordering contradicts its own `depends_on`**. Retroactive recovery
(revert only the population site, re-run, observe the assertion failure) is a repair, not a substitute.

### A gate suppressed on a premise the path does not satisfy (`-028` part A)

OBSERVED: `plan-marshall/workflow/planning-outline.md`:21 skips the q-gate-validation sibling dispatch when
`auto_route_recipe == true` AND `recipe_key` is non-empty, justified by *"the recipe's own outline shape is
already determined by the matched transformation"*; but `phase-3-outline/SKILL.md`:233-235 branches on
**`plan_source == recipe`**, and Tier-1 auto-routing sets `recipe_key` without `plan_source`. ⇒ The
Complex Track authored a **bespoke** outline and its validation was skipped on a recipe premise that was
false. The same paragraph also says "the Q-Gate auto-loop … still apply to the inline outline" — two
sentences in one section disagree about whether the gate runs. Remedy: the suppression and its rationale
must read the same fact.

### Claim labels for this fold

- OBSERVED: `_cmd_domain_detect.py` and `_cmd_change_type_heuristic.py` both read a single `parse_document_sections` section at `356973d80`.
- OBSERVED: `planning-outline.md`:21 keys the q-gate skip on `recipe_key`; `phase-3-outline/SKILL.md`:233 keys the recipe branch on `plan_source` at `356973d80`.
- HYPOTHESIS: Tier-1 auto-routing persists `recipe_key` without `plan_source=recipe` — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-1-init/` § the Tier-1 recipe-match persistence step (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-151-early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back.md` (PLAN-TRUTH-151)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
