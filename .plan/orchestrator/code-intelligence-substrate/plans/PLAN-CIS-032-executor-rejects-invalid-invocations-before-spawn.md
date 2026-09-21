# PLAN-CIS-032: The Argument-Naming Guard Checks Authoring; The Failures Happen At Call Time

epic: code-intelligence-substrate
workstream: WS-01

> Staged 2026-08-03 from the PLAN-CIS-028 drain (inbox `…-013`), **first-party measurement of this
> epic's own run**. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and
> carries no brief.

## Objective

`.plan/execute-script.py` spawns a subprocess for **any** invocation it is handed. When the
subcommand or a flag is wrong, argparse rejects it with `exit_code: 2` **and the script body never
runs** — a failure that is silent by shape, because a workflow that does not read the exit code
proceeds as if the call succeeded.

The executor already embeds the full `SCRIPTS` mapping. **Validate before spawning**, and return the
canonical form in a structured TOON error, so a rejected call becomes a corrective the caller can act
on in one hop instead of a wasted round trip.

## The measurement (OBSERVED — first-party, PLAN-CIS-028 / PR #1080)

`script-failure-analysis` over one run: **20 non-zero-exit script calls, 14 unique signatures** — in
a repository whose own domain is these very scripts.

| subtype | count |
|---------|------:|
| `invented_flag` | 7 |
| `missing_required_flag` | 4 |
| `invented_subcommand` | 2 |
| `script_internal_error` | 1 |

Representative:

- `manage-solution-outline get-deliverable` without `--deliverable-number` — **5 times**
- `manage-references list-add` — verb does not exist (canonical: `add-list`); the retry then omitted
  `--values`
- `manage-files read --tail 25` / `--tail 40` — flag does not exist, twice
- `manage-findings list --format json` — flag does not exist
- `manage-status metadata --field …` issued at top level, then without `--field`
- `ci --pr-number 1080` at top level (the flag is verb-scoped)
- `build_server preflight --plan-id …` — flag does not exist
- `build-server-client:build_server_client` — 3-part notation with a subcommand in the script slot

⭐ **The retrospective reproduced the class once more while writing the report**
(`manage-findings qgate list --fields …`) — the cleanest possible evidence that the recurrence is
not corrected.

## Why the existing guard cannot catch it

The `ARGUMENT_NAMING_*` plugin-doctor rule cluster is a **documentation-authoring** guard: it runs
under `quality-gate` over skill source and catches drift between a doc's stated invocation and the
script's declared argparse surface. **It is structurally incapable of observing a call the model
composes at runtime from surrounding workflow prose** — which is where all 14 of these originated.

⛔ **The four canonical recurrence signatures are already written down** in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md`, and **all 14 failures match one of
them**. ⇒ **Documentation of the failure mode is at saturation and the failure rate is not moving.**
Adding more prose is the defending-documentation archetype (lesson `2026-08-03-06-003`); **put the
check where the call happens.**

## Why this is ours

Lookup/resolution at the executor seam — the same substrate concern as the rest of WS-01, and a
direct token cost under the Priority-1 directive: every rejected call is a wasted round trip whose
tool result still enters context and is then re-read on every subsequent turn.

## Deliverables

1. **D1 — GATE: derive the failure population, not this run's sample (mutates nothing).** Sweep the
   archived corpus for non-zero-exit executor calls and classify them. Report the population size and
   the per-signature frequency. ⛔ **The 14 signatures above are ONE run's sample** — the epic's own
   standing rule (lesson `2026-08-03-06-002`) forbids treating a named list as an enumeration.
   **Prioritise by derived frequency, not by plausibility.**
2. **D2 — pre-spawn validation in `.plan/execute-script.py`.** Reject an unknown subcommand or flag
   **before** the subprocess starts, using the `SCRIPTS` mapping the executor already embeds.
   ⛔ **Fail-closed on the validator's own uncertainty**: a script the mapping cannot describe must
   **spawn as today**, never be rejected — a false rejection breaks working workflows and is strictly
   worse than the defect being fixed.
3. **D3 — the rejection is a corrective, not just an error.** Return structured TOON naming the
   canonical form (`did you mean add-list?`, `--deliverable-number is required`), so the caller
   recovers in one hop. ⭐ `manage-solution-outline get-deliverable` alone was **5 of 20** failures —
   a single missing required flag repeated — so one good message removes a quarter of the run's
   script failures.
4. **D4 — the silent-by-shape half.** ⛔ **A pre-spawn rejection that is itself ignored changes
   nothing.** `exit_code: 2` today means the script body never ran, yet any workflow not reading the
   exit code proceeds as if it succeeded — **the same class as the unchecked-persist family the
   epics already track: a call whose failure is invisible at the call site.** Settle how the
   rejection surfaces so it cannot be stepped over.

Four deliverables (D1 a gate) — below the ~6 split guard, no split rationale owed.

## ⭐ SECOND MEASURED POPULATION, and it strengthens the case for the shim (folded 2026-08-03 from `…-008`, PR #1086)

**Eleven argparse rejections in one plan, across NINE distinct scripts** — an independent run from
the #1080 measurement (20 rejections / 14 signatures).

⛔⛔ **The decisive detail**: **two of the eleven match signatures the `ARGUMENT_NAMING_*` rule already
names VERBATIM.** ⇒ The documented signature was present, correct, and did not prevent the call.
**This is the strongest possible evidence for D2's thesis** — the guard is an authoring-time check
and the failures happen at call time — and it removes the remaining case for answering this with more
documentation.

⭐ **Two independent runs, two epics' worth of plans, converging on the same failure classes** is a
better basis for D1's population sweep than either alone. **D1 should include both runs and report
whether the signature distribution is stable across them** — a stable distribution means the shim can
be prioritised by frequency, an unstable one means it must be derived from the argparse surface
rather than from observed failures.

## ✅ RE-GROUNDED 2026-08-08 AT EMIT TIME (the `next`-verb obligation under § Structural Findings F0)

Every premise this spec rests on was re-read against the implementing source immediately before the
emit. **All three hold — and the pass found one concrete hazard D2 must handle.**

| Premise | Verdict | Evidence |
|---|---|---|
| The executor embeds the `SCRIPTS` mapping D2 would validate against | ✅ **HOLDS** | `.plan/execute-script.py:194` — `SCRIPTS = {` |
| `ARGUMENT_NAMING_*` exists and is an authoring-time guard | ✅ **HOLDS** | `plugin-doctor/references/rule-catalog.md` + `rule-provenance.md`; the contract lives in `persona-plan-marshall-agent/standards/argument-naming.md` |
| The four canonical signatures are already written down | ✅ **HOLDS** | `agent-behavior-rules.md:339-342` — *"four canonical argparse-rejection signatures"*, with worked invented-vs-canonical examples |

### ⛔⛔ NEW — D2 HAS A NAMED FALSE-REJECTION HAZARD, AND IT IS NOT HYPOTHETICAL

D2's fail-closed clause says a script the mapping cannot describe must spawn as today. **There is a
sharper case it must also handle: subcommands that ARE valid but are DECLARED AS ALIASES.** Verified
first-party in the argparse source:

```
manage-status.py:150    add_parser('read', aliases=['get'])
manage-lessons.py:1235  add_parser('get',  aliases=['read'])
manage-tasks.py:251     add_parser('read', aliases=['get'])
```

⇒ **`manage-status get`, `manage-lessons read` and `manage-tasks get` are all legitimate and all
resolve to the same handler as their canonical spelling.** ⛔ **A naive pre-spawn validator that
compares the subcommand against the primary `choices` list would reject all three — breaking working
calls in the three most-used scripts in the repository.**

⭐ **This is the plan's own anti-pattern pointed at itself**: `argument-naming.md` § "Rule 2 —
Read-verb canonicalization" already carves these out **precisely because they are not
verb-paraphrases**, and a validator built from the recurrence-signature list rather than from the live
argparse surface would re-introduce the confusion the carve-out exists to prevent. ⇒ **D2 MUST derive
its accept-set from the argparse declaration INCLUDING `aliases=`, never from the primary choice name
and never from the signature checklist.** ⚠ This also sharpens the standing HYPOTHESIS below about how
machine-readable the argparse surface is: **aliases are part of what must be readable**, so a
generation-time extraction that captures `choices` but drops `aliases` is not sufficient.

## Claim Labels

- **OBSERVED (first-party, PLAN-CIS-028)**: the 20/14 counts, the subtype table, and every
  representative signature above.
- **OBSERVED (orchestrator, 2026-08-08, re-grounding pass)**: the three re-verified premises in the
  table above, and the three `aliases=` declarations at the exact lines cited.
- **OBSERVED**: `.plan/execute-script.py` is generated and embeds the `SCRIPTS` mapping.
  ⛔ **Never edit the generated executor directly** — the change belongs in its generator.
- **HYPOTHESIS**: that argparse's declared surface is machine-readable enough at generation time to
  validate flags as well as subcommands. **Confirm/refute at outline** — if only subcommands are
  cheaply derivable, D2 legitimately narrows to those and D1's frequency table says whether that
  still covers most failures (`invented_subcommand` was 2 of 14; `invented_flag` was 7).
- **HYPOTHESIS**: the `ARGUMENT_NAMING_*` cluster's scope boundary is as described (verify-at-outline).

## Expected Surface

- **HYPOTHESIS**: the executor **generator** (never `.plan/execute-script.py` itself) —
  `plan-marshall:tools-script-executor`; resolve via `architecture which-module` at outline.
- **HYPOTHESIS**: the `ARGUMENT_NAMING_*` plugin-doctor rule cluster, if D1 shows the boundary should
  move (verify-at-outline).
- **OBSERVED**: `persona-plan-marshall-agent/standards/agent-behavior-rules.md` — the four canonical
  signatures. ⚠ **Reference it; do NOT extend it.** More prose there is the thing this plan exists to
  replace.

## Dependencies and Sequencing

- **Depends on**: nothing. Wave-1 eligible.
- ⛔ **Regenerating the executor is a meta-project surface** — after landing, the executor must be
  regenerated and the plugin cache synced, and by the epic's non-self-exercisability rule (lesson
  `2026-08-03-06-004`) **this plan cannot exercise its own change**. Declare that in the outline and
  name the observation point.
- **Disjoint from** CIS-030 (metrics instrumentation), CIS-031 (self-review rounds), CIS-001
  (content-search seam). ⚠ Check against CIS-024/CIS-025 at emit — both are WS-01.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-032-executor-rejects-invalid-invocations-before-spawn.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
