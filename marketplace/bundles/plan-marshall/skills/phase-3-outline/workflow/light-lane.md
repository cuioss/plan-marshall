---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Light-Lane Collapsed Scoping Workflow

Single-envelope collapsed planning lane for `planning_lane == light` plans. It folds **refine-no-loop** (read the clarified request + declared affected files, no clarification iteration), **Simple-outline** (derive Simple-Track deliverables directly), and **deliverable-derivation** into ONE `execution-context` dispatch — replacing the deep lane's refine-loop → Complex-outline → q-gate-validation pipeline for the surgical / single-module band the lane router classified light.

Discovery is **bounded by construction** (DQ2): the lane reads ONLY the declared affected files plus their one-hop direct neighbours, capped at `AFFECTED_NEIGHBOUR_CAP = 25` files — there is NO codebase-sweep step. A monotonic one-way escalation ratchet (DQ3) self-promotes the plan to the deep lane the moment evidence contradicts the cheap light classification; the leaf returns `outcome: escalate_to_deep` and the orchestrator owns the deep-lane re-dispatch.

This workflow reuses the existing [Deliverable Template](../SKILL.md#deliverable-template-inline-reference), the [File-type classifier](../standards/outline-workflow-detail.md#file-type-classifier), and the [Step 9c design-intent classification](../standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) verbatim — it introduces no new deliverable schema and no new script entry point.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-plan-documents` (request read), `plan-marshall:manage-solution-outline` (outline write), `plan-marshall:manage-references` (scope/track persist), `plan-marshall:manage-status` (metadata read + escalation), `plan-marshall:manage-architecture` (bounded neighbour resolution), `plan-marshall:manage-lessons` (prospective lessons consult), `plan-marshall:manage-logging` (decision + work entries).

## Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `AFFECTED_NEIGHBOUR_CAP` | `25` | Hard cap on the bounded read set (`\|A\| + \|neighbours\| ≤ 25`). Hitting the cap is itself an escalation trigger (DQ3). |
| `SINGLE_BAND_MAX` | `8` | The surgical/single-module declared-file band. `\|A\| > SINGLE_BAND_MAX` is an escalation trigger. |

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Workflow

### Step 1: Read the Clarified Request and Seed Set A (no clarification loop)

Read the clarified request narrative (falling back to the original input) — this is the refine-no-loop collapse: there is NO iterate-to-confidence loop in the light lane. The cheap lane router already decided the request was concrete enough to plan directly.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read --plan-id {plan_id} --section clarified_request
```

`--section clarified_request` falls back to `original_input` automatically when the clarified section is absent. Extract the **declared affected files** — the explicit repo-relative file paths named in the request body. This is the seed set `A`. Resolution uses the same path regex the lane router's S5 concreteness signal uses; do NOT discover files the request did not name.

### Step 2: Resolve the DQ2 Bounded Read Set (A + one-hop neighbours, capped)

For each file `f ∈ A`, resolve exactly ONE hop of direct neighbours — never transitive, never a sweep:

1. **Imports/includes that `f` itself declares** — parse `f`'s own import/from/require lines, resolve each to an in-repo path. The neighbour's own imports are NOT followed.
2. **The paired test (or paired production file)** of `f` via the deterministic test-path mapping (`marketplace/bundles/{b}/skills/{s}/scripts/x.py` ↔ `test/{b}/{s}/test_x.py`).
3. **The owning `SKILL.md`** — the `marketplace/bundles/{b}/skills/{s}/SKILL.md` enclosing `f`, so the Step 9c design-intent read is satisfiable without discovery.

Neighbour resolution uses the **structured architecture inventory**, never a Grep/Glob sweep:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  which-module --path {f}
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  files --module {module}
```

**Cap check (DQ2 / DQ3 trigger):** if `|A| + |neighbours| > AFFECTED_NEIGHBOUR_CAP` (25), the light lane does NOT silently truncate. The cap-hit is the cheap structural proxy for "this change is bigger than declared" — record `discovery_bound_hit: true` with the file count and jump directly to **Step 4 (Escalation Ratchet)** with `trigger = explosion`. Otherwise record the bounded read set and continue.

Log the bound for auditability:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-3-outline:light-lane) Bounded read set: |A|={a_count} + neighbours={neighbour_count} = {total} (cap {cap})"
```

### Step 3: Minimal Premise-Check (cheap refine Step 3c)

Run the **minimal premise-check** — the cheap version of the deep refine's premise / narrative-vs-code safety check (refine Step 3c). Reading ONLY the bounded set from Step 2, verify that the request's premise is consistent with the read code: the files the request says it will change exist and are shaped the way the request assumes (the "looks concrete but the fix is wrong/obsolete" lesson-derived failure mode).

**On a premise contradiction** (the request's stated premise contradicts the read code): jump to **Step 4 (Escalation Ratchet)** with `trigger = premise`.

The premise-check is gated by `plan.phase-2-refine.revalidation` (read via `manage-config plan phase-2-refine get --field revalidation`) — when that gate resolves to `never`, skip the check (the operator owns the risk). `auto` / `always` run it.

### Step 4: Escalation Ratchet (DQ3 — one-way light→deep)

The ratchet is monotonic light→deep; it never reverts. ANY of the following triggers fires escalation:

1. **Affected-file-set explosion** — the Step 2 cap-hit (`|A| + |neighbours| > 25`), OR the declared count alone exceeds the band (`|A| > SINGLE_BAND_MAX = 8`).
2. **Premise-check failure** — Step 3 found the request premise contradicts the read code.
3. **Cross-cutting impact** — a declared affected file is a published cross-bundle public symbol whose one-hop neighbour resolution reveals consumers OUTSIDE the bounded set.

On a fire, escalate via the D4 one-way escalate verb (see `manage-status` Canonical invocations → `planning-lane`), set the trigger, and return the escalate signal to the orchestrator. The leaf does NOT dispatch the deep lane itself (leaf-cannot-dispatch) — it returns `outcome: escalate_to_deep` and the orchestrator owns the deep-lane re-dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id {plan_id} --trigger {explosion|premise|cross_cutting} --persist
```

The escalate verb sets `status.metadata.planning_lane = deep`, `lane_escalated = true`, and `escalation_trigger`; the flag is sticky and there is no downgrade. Then return the escalate TOON (see Output § escalate). When NO trigger fires, continue to Step 5.

### Step 5: Derive Simple-Track Deliverables and Write the Outline

No clarification loop, no Complex-Track discovery — derive the deliverables directly from the bounded read set, reusing the existing Simple-Track authoring rules verbatim:

1. **Classify each deliverable's `affected_files`** against the [File-type classifier](../standards/outline-workflow-detail.md#file-type-classifier) (six buckets) BEFORE assigning `profiles[]`. Record the resolved bucket in the `<!-- bucket: ... -->` comment on the `**Profiles:**` line.
2. **For any deliverable that touches an existing skill**, run the [Step 9c design-intent classification](../standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) and emit the resulting `**Design notes:**` block — the owning `SKILL.md` is already in the bounded read set (Step 2), so this needs no extra discovery.
3. **Author each deliverable** using the [Deliverable Template](../SKILL.md#deliverable-template-inline-reference) verbatim (field order, `**Intent gloss:**` where the title head morpheme is a planning-domain verb, per-file `(intent)` markers). Resolve verification commands via `architecture resolve`.

Write `solution_outline.md` via the standard three-step path-allocate flow (resolve path → Write tool → validate). Use `write` on first entry, `update` on re-entry:

```bash
# 1. Resolve the target path
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
# 2. Write the outline content (title, plan_id, compatibility header, Summary,
#    Overview, Deliverables) directly to the resolved path via the Write tool.
# 3. Validate on disk
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

Persist the (possibly refined) scope/track to references.json so phase-4-plan reads a consistent value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  set --plan-id {plan_id} --field scope_estimate --value {scope_estimate}
```

Then re-run the deterministic classification-validation gate, because this persist overwrites the pre-route band that phase-1-init's Step 8a.5 heuristic wrote:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status classification-validate \
  --plan-id {plan_id}
```

The gate is **flag-not-block** — it records Q-Gate findings and never halts the lane. This call site is load-bearing for the `scale_mismatch_light_routing` class specifically: a light-lane plan never enters phase-2-refine's clarification loop, so the refine-side re-validation never runs for it, and inside `planning-lane route` the gate runs immediately after the Step 8a.5 heuristic wrote the band with the *same* measurement logic the detector re-derives — where disagreement is impossible by construction. Without this call the detector could never fire for the very population its name targets. Parse `mismatch_count` to see whether the gate fired; the finding itself is already persisted by the verb as a Q-Gate finding against phase `2-refine`, read later via `manage-findings qgate list --plan-id {plan_id} --phase 2-refine` (or the unified `--include-qgate` sweep). The Q-Gate store — not this workflow's return TOON — is the carry-forward channel, so no `mismatch_count` / `classification_validation` field is added to the `## Output` contract below. Never treat a mismatch as a halt.

Log completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-3-outline:light-lane) Derived {deliverable_count} deliverable(s) from bounded read set — light lane, no escalation"
```

### Step 5b: Prospective Lessons Consult

The light lane is **not exempt** from the consult obligation — the consult is lane-agnostic by design, and exempting the light lane would make it vacuous for the majority of plans. Fire it here, after the outline is written and validated and before the phase transitions:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons consult \
  --plan-id {plan_id}
```

Record exactly one disposition (`heeded` / `not_applicable` / `stale`) plus a one-line rationale for every surfaced lesson in the outline's `## Lessons Consulted` section, emit that section even when `surfaced_count: 0`, and never auto-apply a surfaced lesson. On a `heeded` lesson, revise the deliverables and re-validate with `manage-solution-outline update` within this same envelope.

The authoritative procedure lives in [`standards/outline-workflow-detail.md` § Prospective lessons consult](../standards/outline-workflow-detail.md#prospective-lessons-consult); the section's structural spec is owned by [`manage-solution-outline` standards/solution-outline-standard.md](../../manage-solution-outline/standards/solution-outline-standard.md) § Lessons Consulted. Do NOT restate either here.

### Step 5c: Domain Narrowing

The light lane is **not exempt** from the narrowing obligation either, and for the same structural reason the consult above is fired here: Step 4c of [`../SKILL.md`](../SKILL.md) states that the inline Steps 5-12 are NOT run for a light-lane plan, so a step added only to Step 12 would never fire on this lane. Fire it here, after the outline is written and validated and before the phase transitions.

1. Refresh the declared footprint so the verb reads a current one:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-references:manage-references sync-affected-files \
     --plan-id {plan_id}
   ```

   Nothing is joined into a footprint string: the verb reads `references.affected_files` itself and keeps it a list end to end, so a path containing a comma survives and no repository-controlled path is interpolated into a command line.

   **Branch on the returned `status` BEFORE continuing.** The refresh fails the same way `domain-narrow` does in step 2 — `status: error` with a **zero exit code**, so the exit code is not the signal. `outline_not_found`, `outline_unreadable`, and `no_deliverables_parsed` each return `status: error` and write nothing.

   On `status: error`: STOP the narrowing step here. Do NOT invoke `domain-narrow`, do NOT run steps 3, 3b or 4, and do NOT write `domains` or `domains_provenance`. Surface the returned `error` and `message` via a decision-log entry:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level WARNING \
     --message "(plan-marshall:phase-3-outline:light-lane) Domain narrowing could not start — sync-affected-files returned {error}: {message}. No domains or domains_provenance write was made."
   ```

   Why a failed refresh must stop the step rather than fall through to the downstream error branch — the stale-but-present footprint that lets `domain-narrow` publish a confident verdict for a pass that never saw the current footprint — is stated once in [`../SKILL.md`](../SKILL.md) § Domain Narrowing; do not restate the reasoning here.

2. Invoke the narrowing verb, which reads that footprint itself:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config domain-narrow \
     --plan-id {plan_id}
   ```

   **Branch on `status` BEFORE parsing anything else.** The verb has three outcomes, not two, and on the third none of the success fields exist:

   - **`status: error`** — the verb could not evaluate. The reason codes are `plan_dir_not_found`, `domains_unreadable`, `marshal_not_readable`, `no_skill_domains_configured`, `footprint_unreadable`, `footprint_empty`, and `task_leg_unreadable`; the canonical set with the condition each names is owned by [`manage-config` § Canonical invocations → `domain-narrow`](../../manage-config/SKILL.md), which is the source to re-check this list against. `retained`, `dropped`, `provenance`, `report`, and `narrowed` are ABSENT from the payload. STOP the narrowing step here: do NOT parse the success fields, do NOT run steps 3, 3b or 4, and do NOT write `domains` or `domains_provenance`. Surface the returned `error` and `message` instead, via a decision-log entry:

     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       decision --plan-id {plan_id} --level WARNING \
       --message "(plan-marshall:phase-3-outline:light-lane) Domain narrowing could not evaluate — domain-narrow returned {error}: {message}. No domains or domains_provenance write was made."
     ```

     Improvising past this branch is the prohibited move: a fabricated `domains_provenance` value, an invented empty `report`, or a `set-list` call with no values would each render a verb that could not look as one that looked and found nothing. Leaving both keys unwritten is correct here: an absent `domains_provenance` means "never examined", which is precisely what happened.

   - **`status: success`** — and only then, parse `retained`, `dropped`, `provenance`, `report`, and `narrowed`, and continue to step 2b.

2b. **Domain-alphabet gate — it runs HERE, immediately after `status: success` and before steps 3, 3b and 4.**

   Confirm that every domain name in `{retained_csv}` (step 3), in `{provenance_rendering}` (step 3b), **and in `{report}` (step 4)** matches the domain alphabet `^[a-z][a-z0-9-]*$`.

   The report is in scope because `_compose_report` EMBEDS the dropped domain names in it, and step 4 interpolates `{report}` into a `manage-logging decision --message "..."` command line — so the report is a third interpolation of the same repository-controlled text, not a derived summary that launders it.

   **On a violation the refusal is TERMINAL for the whole narrowing step.** Make no write, do NOT run steps 3, 3b or 4, and do NOT emit the report to the decision log. The refusal entry below is the ONLY output of this branch and MUST stay a fixed string carrying no interpolated value of any kind:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level WARNING \
     --message "(plan-marshall:phase-3-outline:light-lane) Domain narrowing wrote nothing and withheld its report: a domain name falls outside the documented alphabet, and that name is embedded in the report as well as in both writes, so all three interpolations were refused."
   ```

   **`domain_narrow_report` is OMITTED from the envelope return on this branch**, the same treatment § Output already gives a `status: error` return — the report was withheld rather than absent, and the refusal entry above is the record that one existed.

   Why the alphabet is checked rather than assumed — no upstream write path guarantees it — and why the report counts as a third interpolation site are stated once in [`../SKILL.md`](../SKILL.md) § Domain Narrowing; do not restate the reasoning here.

3. On `narrowed: true`, persist the retained set:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
     --plan-id {plan_id} --field domains --values "{retained_csv}"
   ```

   The placeholder is double-quoted because `retained_csv` is legitimately empty when every domain was dropped — `narrowed` is `true` whenever anything was dropped, so an all-dropped run reaches this call with nothing to interpolate. `--values` is REQUIRED and takes no default, so an unquoted empty interpolation renders a bare `--values` and argparse rejects the call; quoted, it passes the empty string, which `set-list` accepts as "clear the list" — the correct outcome for that state.

3b. On **both** outcomes — the write is NOT gated on `narrowed` — persist the provenance, so a plan the pass examined and found nothing droppable in stays distinguishable from one the pass never ran on:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
     --plan-id {plan_id} --field domains_provenance --value "{provenance_rendering}"
   ```

   `{provenance_rendering}` is the compact one-line `{domain}={legs}` form described in [`manage-references` § Schema Fields](../../manage-references/SKILL.md) — `none` where no leg claimed the domain. Do NOT invent a rendering here: both lanes write the same key, so the format has exactly one home.

   The quotes here address a different failure than step 3's — the rendering separates domains with `;`, a shell command separator, so an unquoted interpolation truncates the write at the first domain and runs each remaining `{domain}={legs}` word as its own command — but they are **not** the injection defence for either call, because quoting does not neutralize `$(...)`, backticks, or backslashes. What makes both calls safe is the domain-alphabet gate at step 2b, which has already run by the time this one is reached and refuses the whole step — both writes and the report — when any domain name falls outside the alphabet.

4. Emit the returned `report` verbatim — on **both** success outcomes, including `narrowed: false` — to its two declared sinks. First, a decision-log entry:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-3-outline) {report}"
   ```

   Second, the envelope's return TOON `domain_narrow_report` field (see § Output), which carries the report **verbatim** off this envelope without the 80-ASCII-character cap `display_detail` is bound by. `display_detail` is deliberately NOT a sink for it: its shape is fixed by the Output contract below, so it cannot carry the report verbatim and does not claim to.

   ⛔ **The decision log is the report's only CONSUMED sink today.** `domain_narrow_report` has no reader — `plan-marshall/workflow/planning-outline.md` does not consume it. The field is emitted so a consumer CAN be wired without re-shaping the return; wiring it is owed follow-up, not present behaviour, and this document must not state that the orchestrator surfaces it.

The verb owns the narrowing decision; this envelope invokes it, persists its result, and reports it. The rationale for the rule — why end-of-outline is the site, why a `narrowed: false` outcome is recorded rather than skipped, and the three-legged safety bound the verb applies — lives in [`../SKILL.md`](../SKILL.md) § Domain Narrowing. Do NOT restate it here.

### Step 6: Transition Phase

The light lane completes the outline phase in one envelope; transition to phase-4-plan:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} --completed 3-outline
```

**`3-outline` is the only phase this envelope transitions.** The `2-refine` transition is owned by the **orchestrator**, which issues it — together with the paired `phase_handshake capture --phase 2-refine` and the `2-refine → 3-outline` boundary stamp — *before* this envelope is dispatched; **this envelope does not own it and must not issue it.** The split is not arbitrary: the boundary stamp has to precede the dispatch or `manage-metrics enrich` attributes this envelope's whole spend to a still-open `2-refine` window, and the capture has to precede it or the Phase Entry Protocol's `phase_handshake verify --phase 2-refine` at this envelope's own entry would be verifying a row that does not yet exist. See [`plan-marshall/workflow/planning.md`](../../plan-marshall/workflow/planning.md) § "Light-lane branch" step 2 for the three calls and the evidence behind the placement.

## Output

The minimum contract this workflow doc (an `ext-point-execution-context-workflow` implementor) MUST return:

```toon
status: success | error
display_detail: "<≤80 char ASCII summary, no trailing period>"
```

### success (deliverables derived)

```toon
status: success
display_detail: "light lane: {deliverable_count} deliverables, no escalation"
plan_id: {plan_id}
planning_lane: light
deliverable_count: {N}
discovery_bound_hit: false
qgate_validation_required: false
domain_narrow_report: {the domain-narrow report, verbatim; see Step 5c}
```

`domain_narrow_report` carries the `report` string returned by `manage-config domain-narrow`, verbatim and unedited, on **both** of the verb's success outcomes — a `narrowed: false` run reports too. It exists because `display_detail`'s fixed shape above and its 80-character ASCII cap cannot carry the report itself. ⛔ **It has no reader today** — `plan-marshall/workflow/planning-outline.md` does not consume it, so the decision-log entry at Step 5c is the report's only consumed sink; see that step's note. The field is **omitted** when the verb returned `status: error` — nothing was evaluated, so there is no report, and an empty string would render a pass that could not look as one that looked and found nothing. It is **omitted on the domain-alphabet refusal branch too** (Step 5c step 2b): there the verb did produce a report and the step withheld it, so carrying the field while its decision-log sink was refused would leave the two sinks disagreeing about whether the step reported. It is absent from the escalate shape below by construction: the ratchet returns at Step 4, before Step 5c ever runs.

`qgate_validation_required` is always `false` on the light lane — the bounded read set + premise-check + escalation ratchet are the light lane's verification, and the deep-lane q-gate-validation is reached only via escalation.

### escalate (DQ3 ratchet fired)

```toon
status: success
display_detail: "escalate_to_deep: {trigger}"
plan_id: {plan_id}
outcome: escalate_to_deep
escalation_trigger: {explosion|premise|cross_cutting}
planning_lane: deep
lane_escalated: true
```

The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads `outcome: escalate_to_deep` and re-dispatches the deep lane (refine-loop + Complex-outline) fresh. The leaf never dispatches it.

## Related

- [`phase-3-outline/SKILL.md`](../SKILL.md) — the lane-routing preamble that dispatches this doc when `planning_lane == light`, and the Deliverable Template / File-type classifier this doc reuses.
- [`manage-status` Canonical invocations → `planning-lane`](../../manage-status/SKILL.md#planning-lane) — the D4 `route` / `escalate` subcommand contract.
- [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) — why the light lane collapses three phases into one envelope (bundle when steps share context).
