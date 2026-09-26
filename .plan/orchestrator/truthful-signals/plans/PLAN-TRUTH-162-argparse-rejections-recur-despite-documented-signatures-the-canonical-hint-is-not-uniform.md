# PLAN-TRUTH-162: Argparse rejections (paraphrased verbs, invented flags, missing required flags) recur despite five documented recurrence signatures, because the canonical-verb hint is not uniform across the manage-* surface

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15. Upgraded from epic Watch **W-1483-b** ("verb-paraphrase remains the dominant argparse
rejection despite the recurrence checklist"), which was absorbed rather than staged because it "needs the
rejection population behind it before anyone acts." That population is now available, independently, from
THREE separate plan landings on the same day: `PLAN-TRUTH-148` (17 failures, 10 unique, 8 components —
`inbox/plan-truth-148-007.md` + `-055..-061,-063.md`), `PLAN-TRUTH-157` (6 more, including the recurrence
signature recurring verbatim inside finalize — `inbox/plan-truth-157-006.md` + `-028..-031.md`), and
`PLAN-PR-065` via a `review-apparatus` transfer (10 more, including the SAME invented verb re-invented
three times hours apart after the correct form had already been printed —
`inbox/review-apparatus-041.md` § A).

## Objective

**`persona-plan-marshall-agent`'s recurrence checklist already documents five rejection signatures, and
the population across three independent runs shows the checklist is not changing behaviour: the failure
is not missing knowledge, it is that a rejection costs nothing and is re-attempted faster than it is
read.** One mitigation already exists and works — `manage-solution-outline`'s unknown-verb rejection
prints `Use <canonical form>` and the call recovered in one attempt with no `--help` round-trip — but it
is not applied uniformly across the `manage-*` surface. Rejections that print a bare argparse usage block
cost strictly more than the one that prints the canonical form.

**Corroborating detail, not a separate cause.** `review-apparatus-041.md` § C-003 independently names WHY
the paraphrase is induced at at least one site: a skill's own description says "deliverable extraction"
while the registered verb is `list-deliverables` — the paraphrase the agent invents matches the skill's
OWN prose, not a random guess. `plan-truth-148-007.md` reproduced exactly this call
(`manage-solution-outline extract-deliverables`) live during its own retrospective and recovered via the
canonical-form hint on the next attempt.

**A distinct defect in the same population, NOT the same fix.** `review-apparatus-041.md` § A-014: the
generated executor rejected a flag the dispatched script itself declares, and two full executor
regenerations did not clear it — a real tooling defect, not an agent-invocation mistake, and the one case
in this population where reading the registered set would not have helped. Folded into `PLAN-TRUTH-154`
(operator-facing authority surfaces that answer confidently and wrongly) instead of this spec, since it is
a generator/registry-parity bug, not a calling-convention gap.

## Deliverables

Three deliverables. D0 is a gate.

**D0 — GATE: derive the full population across all three sources and classify by failure shape.**
Combine and de-duplicate the ~30 raw instances into the closed set of signatures: invented/paraphrased
verb, undeclared flag, missing required flag, misplaced positional flag (`--plan-id` after the
subcommand), and the one misclassification instance (a resolution-subprocess timeout labelled
`argparse_rejection` — folded separately into `PLAN-TRUTH-150`, not counted here). Publish the population
and its size per signature before choosing the fix's exact shape.

**D1 — Make the canonical-invocation hint uniform across the `manage-*` surface.** On an unknown verb,
undeclared flag, or missing required flag, print the accepted set AND a `Use <full canonical invocation>`
line naming the closest match — the way `manage-solution-outline` already does for unknown verbs. The
`ARGUMENT_NAMING_*` plugin-doctor cluster guards the authoring side (that a script's flags are named
consistently); this guards the CALLING side, which is where every one of these failures was actually paid.

**D2 — Where a skill's own description induces the paraphrase, correct the description to match the
registered verb**, per the `review-apparatus-041` § C-003 evidence — the fix at the calling site (D1) does
not close the fix at the inducing site.

## ⚠ RE-GROUNDING NOTE 2026-09-15 (cleanup) — D0 should read this before deriving the population

`manage-solution-outline.py` itself carries NO custom unknown-verb handler. The `Use ...` hint claim 0
cites traces to `execute-script.py.template`'s shared `_closest_spelling` suggestion logic (verb-level
~L891-943, flag-level ~L1151-1153) — the GENERATED EXECUTOR every `.plan/execute-script.py` call already
routes through, not a per-script feature. This means the hint mechanism this spec's D1 proposes to "make
uniform" may **already be uniform** at the executor layer. D0's population derivation should confirm
whether the real gap is (a) call sites that bypass the executor entirely, or (b) something about how the
suggestion fires that this cleanup pass did not check (e.g. a threshold that only some rejections cross) —
rather than assuming the fix is "add the hint to more scripts," which the executor-layer finding may make
unnecessary or much narrower than staged.

## Claim Labels

- OBSERVED: `manage-solution-outline`'s unknown-verb rejection already prints
  `Use plan-marshall:manage-solution-outline:manage-solution-outline list-deliverables` and the call
  recovered in one attempt (re-verified live in `plan-truth-148-007.md`'s own retrospective; re-confirm
  at outline the behaviour is unchanged at HEAD).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-solution-outline.py itself has no custom unknown-verb handler; the 'Use ...' hint traces to execute-script.py.template's shared _closest_spelling suggestion logic (lines 891-943 verb-level, 1151-1153 flag-level), which every script invocation already routes through. IMPORTANT for D0: this suggests the hint mechanism may ALREADY be uniform at the executor layer rather than missing elsewhere -- D0's population derivation should confirm whether the real gap is non-executor-routed call sites, not a per-script feature gap
- OBSERVED: three independent landings on 2026-09-14 each logged multiple argparse-rejection instances
  of this shape (PLAN-TRUTH-148: 17; PLAN-TRUTH-157: 6; PLAN-PR-065 via review-apparatus: 10) — the
  message ids are named in Provenance above; re-derive the combined, de-duplicated population at outline
  rather than trusting this restated count (verify-at-outline, per this epic's own standing rule against
  restated counts).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The combined cross-landing population (17+6+10=33 raw instances) was not independently re-derived from the cited inbox messages at cleanup time -- those messages are already archived; this epic's own standing rule requires D0 to re-derive rather than trust the restated count
- OBSERVED: `review-apparatus-041.md` § A-007 and § A-012 each report the SAME rejection recurring
  verbatim within one run, after the correct form had already been displayed — corroborated independently
  by `plan-truth-148-056.md` (the same paraphrase fired during execute AND again during the retrospective
  hours later).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: review-apparatus-041.md and plan-truth-148-056.md are both already archived (consumed by this session's own drain fork); the same-rejection-recurring-verbatim claim was not re-read from the archive at cleanup time
- ⚠ HYPOTHESIS: correcting the inducing skill descriptions (D2) measurably reduces the paraphrase rate.
  ⛔ Reasoned from one instance (`list-deliverables`/"extraction"); D0's population derivation may find
  the inducement pattern does not generalize (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The claim that description-correction reduces paraphrase rate is reasoned from one instance and explicitly flagged by the spec itself as not generalized; D0 owns this

**D3 — ABSORBED from PLAN-TRUTH-159: a documented invocation the runtime refuses is corrected to the
invocation that runs.** `project:finalize-step-deploy-target` documents `./pw generate-claude` as its
Step 1 — a command this repository's PreToolUse rule R4 unconditionally denies — and R4's own redirect is a
dead end (`architecture resolve --command generate-claude` returns `Command not found`, because a generator
alias is not a canonical build command). ⛔ **Operator decision, already taken 2026-09-13 and binding:** the
skill adopts the executor invocation; R4 gains NO carve-out (an unconditional deny rule's whole value is
being unconditional), and `architecture resolve` is NOT taught the alias (that would be a resolver-contract
change). A second member is `phase-6-finalize/standards/branch-cleanup.md` line 600, which prescribes
pacing a poll with a standalone `sleep` the harness blocks.

**D4 — ABSORBED from PLAN-TRUTH-159: a lint-time detector for a documented invocation the runtime would
refuse — hook rule OR harness.** D0's population derivation widens accordingly: documented Bash
invocations across `.claude/skills/**` AND the marketplace `phase-6-finalize` workflows, classified by
which refusal source would reject them. ⚠ `architecture-refresh.md` § 2b's `rm -rf` is a known third
member and is owned by `post-run-quality` PLAN-PRQ-06 D4 — **cross-epic; report it, do not re-fix it.**

⭐ **Why these merged rather than staying two plans.** Both are *a documented invocation that the enforced
surface rejects*, and both remedies are the same act: correct the doc to match what runs, then add the
detector that keeps it true. `-159`'s population (`./pw`-prefixed invocations) and `-162`'s (argparse
paraphrases) are two slices of one sweep over the same documentation corpus, and running them as two plans
would sweep that corpus twice. ⚠ **Confident merge** — the deliverables are disjoint and the shared D0
becomes cheaper, not larger.

## Expected Surface

- HYPOTHESIS: the shared argparse-rejection formatting seam every `manage-*` script's router goes
  through — exact file(s) owed by D0 (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
  — the existing canonical-hint implementation D1 generalizes from
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` — the
  "deliverable extraction" description D2 corrects (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`
  — the five documented recurrence signatures, cross-referenced (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/**` — coverage for the uniform hint across a representative sample of
  `manage-*` scripts (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` and the standards it loads —
  the non-canonical `manage-plan-documents` / `get-deliverable` renderings (folded 2026-09-15 (c))
  (verify-at-outline)
- OBSERVED: `.claude/skills/finalize-step-deploy-target/SKILL.md` — the documented `./pw generate-claude` Step 1 (D3; absorbed from PLAN-TRUTH-159)
- HYPOTHESIS: `.claude/skills/**` — D0's widened population sweep and D4's correction sites (D3, D4) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the harness-blocked `sleep` pacing (D3; absorbed from PLAN-TRUTH-159)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md` — rule R4 and the refusal sources D4's detector reads (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Adjacent to but distinct from `PLAN-TRUTH-154`'s D1 (an invocation rejection suggests a notation it has
  not validated) — that deliverable is about the SUGGESTED remediation being unverified; this spec is
  about the hint not existing uniformly in the first place. Not merged; `review-apparatus-041` § A-014
  (the executor-registration bug) goes to `PLAN-TRUTH-154`, not here.
- plan-truth-148 and plan-truth-157 had already landed when this plan was staged.

## ⭐ FOLDED 2026-09-15 (c) — PHASE-4-PLAN: THREE REJECTIONS IN ONE ENVELOPE, ONE RETRIED WITHOUT THE HINT

Forwarded from `lessons-handling-26-09-04-01-063.md` (Token-Sheriff PR #744, bundling its `-011`/`-012`).
Expected Surface extended in the same act (`phase-4-plan/SKILL.md`, above). A further population member for
D0, from a consuming repo:

1. `manage-plan-documents` exit 2 — a top-level verb where the `request` noun's `read` sub-verb was meant
   (`lessons-capture.md` already warns about this paraphrase, so a doc `phase-4-plan` loads may still
   present it non-canonically).
2. `manage-solution-outline get-deliverable` exit 2 — **twice, one second apart, the identical call
   repeated without applying the declared-flag hint** (`deliverable-number`, `plan-id`). That repeat is the
   direct evidence for this spec's thesis: a hint that exists is still not consumed.

Two leads for D0/D1: audit `phase-4-plan` and its loaded standards for non-canonical renderings of both
reads; and record the REJECTED argv in the `script_failure` log line — today the log does not name the
invented verb or flag, so every occurrence leaves its source to be guessed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-162-argparse-rejections-recur-despite-documented-signatures-the-canonical-hint-is-not-uniform.md"
```

## ⭐ FOLDED 2026-09-22 — two more instances of D3's class, one first-party-verified

Two inbox lessons relayed via `lessons-handling-26-09-22-01`, both `.claude/skills/**` — already D3/D4's
declared population, no surface change.

- `2026-09-20-07-001`: `finalize-step-deploy-target` documents a bare `./pw generate-claude`, blocked by
  the hard-rule hook; `architecture resolve` has no registered canonical form for it either. ⛔ Routing
  hazard avoided: this is NOT a `PLAN-TRUTH-159` item — that spec's first six lines read "MERGED OUT
  2026-09-18 (cleanup A5) — RETIRED, substance now lives in PLAN-TRUTH-162 as D3/D4." Pure recurrence of
  D3's already-corroborated (`checked_at: 7a028157e`) claim, including the redirect dead-end half
  (`architecture resolve --command generate-claude` → `Command not found`) and the binding operator
  decision (no R4 carve-out).
- `2026-09-20-07-002`: **corroborated first-party at `7d82d5d90`, twice.**
  `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:175` still prescribes
  `python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done …`; running it
  live returns `SCRIPT_ERROR … Unknown notation … Correct format: plan-marshall:manage-status:manage-status
  manage_status`. The step's own documented § 4 "Mark step complete" is an invocation the enforced surface
  rejects on every run — D3's exact class. Second-order finding for D4's design: a detector for this
  already exists (`plugin-doctor/scripts/_analyze_notation_staleness.py`) and this site survives it,
  because `.claude/skills/**` is outside the architecture inventory (`architecture search --content` over
  3,097 files returns 154 `manage_status` hits in 78 files, none under `.claude/`) — D4's lint-time
  detector must not be built on the inventory or it inherits the same blind spot. ⚠ Never pair `-162` with
  `-154` in a parallel launch: PLAN-TRUTH-154's Expected Surface declares this same
  `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` path.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
