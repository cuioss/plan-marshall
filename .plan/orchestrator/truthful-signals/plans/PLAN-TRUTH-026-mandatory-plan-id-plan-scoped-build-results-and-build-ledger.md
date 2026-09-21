# PLAN-TRUTH-026: mandatory plan-id for build operations, plan-scoped build results, and a traceable build ledger

epic: truthful-signals
workstream: WS-01

## Objective

Make `plan_id` **mandatory** on every build-class operation (using the existing `NO_PLAN` sentinel
rather than a nullable field), relocate build output from the shared `.plan/temp/build-output/` tree
into a **`build-results/` subdirectory of the plan directory** so every build log becomes a plan
artifact, and extend the existing `kind=build` change-ledger entry to record the **actual resolved
build command** and the **outcome TOON** (which carries the path to the build result) — so every build
is traceable from the plan that caused it to the command that ran and the output it produced.

The three parts are one chain: build results cannot be plan-scoped until a plan id is guaranteed, and
the ledger cannot point at a plan-scoped result until the result has moved.

## Provenance and prior art

Operator request, 2026-07-31. Grounded against repo source in the same pass — see Claim Labels.

⚠ **A `kind=build` ledger ALREADY EXISTS and is more complete than the request assumes.** This is the
single most important scoping fact in this spec: `manage-change-ledger` already writes `kind=build`
rows carrying `notation`, `plan_id`, `args`, `exit_code`, `status`, `worktree_sha`, `log_file`, and
`timestamp_iso`. ⇒ **D3 is an EXTENSION of an existing substrate, not a new ledger.** Building a
second build-log would duplicate a working mechanism — the exact anti-pattern this epic's standing
rule *"where a copy exists, delete the copy"* exists to prevent.

The genuine gaps D3 closes are two, and they are narrower than "add a build ledger":

1. The row records the **executor notation plus args**, NOT the **actual resolved command line**. The
   API-Sheriff PLAN-35 incident recovered its decisive command line from the marshalld job log because
   the ledger could not supply it.
2. The row carries `log_file` but not the **outcome TOON** the wrapper returned.

## Deliverables

1. **D0 — GATE (mutates nothing): derive the population of build-class call sites and ledger writers.**
   Enumerate every build entry point, every `--plan-id` / `--audit-plan-id` acceptance point, and every
   writer of a `kind=build` or `kind=job` row. ⛔ **The four wrappers named in Expected Surface are a
   SAMPLE the orchestrator found by grep, not the population** — the epic's standing rule is that a
   stated count states a sample. Report population size and per-site status separately.
   ⚠ **D0 also decides whether this plan splits** (see § Scope note).
2. **D1 — `plan_id` becomes mandatory across build operations.** Every build wrapper accepts and
   requires `--plan-id`; genuinely plan-less callers pass the `NO_PLAN` sentinel explicitly rather than
   omitting the flag. The `kind=build` ledger field changes from `str|null` to `str`. ⭐ **The point is
   that "no plan" becomes a STATED value instead of an absence** — an absence is indistinguishable from
   a caller that simply forgot, which is precisely the ambiguity that made the phases-1-4 gap invisible.
3. **D2 — build results relocate to `{plan_dir}/build-results/`.** Change the resolution seam so build
   logs land under the resolving plan's directory. For `NO_PLAN`, results land under the sentinel's own
   directory — which is the shared, permanent, main-checkout-anchored plan dir, so the plan-less path
   stays well-defined rather than falling back to the old shared tree.
4. **D3 — the `kind=build` row records the actual command, the duration, and the outcome TOON.** Add
   the **resolved command line as executed** (the argv the build process actually received, not the
   notation), the **`duration_seconds`**, and the wrapper's **outcome TOON**, whose `log_file` field is
   the pointer to the build result under D2's new location.
   ⭐ **`duration_seconds` is not new data — it is data being THROWN AWAY.** Every build result already
   carries it as a REQUIRED field (`success_result`, `error_result`, and `timeout_result` all set it),
   and the change-ledger scripts contain **zero `duration` tokens**. The wrapper measures the duration
   of every build and the ledger boundary discards it. ⇒ This is the epic's own theme — machinery
   silently losing information it was handed — and it makes D3 a **plumbing** change, not a measurement
   change. ⛔ **Extend the existing entry; do not create a second ledger.**
5. **D4 — retention, GC, and deletion-safety for the new location.** Build results inside a plan
   directory inherit plan archival and every artifact sweep that walks plan dirs. Establish what now
   collects them, and confirm a build result is not offered as safe-to-delete while its plan is live.
   ⛔ **This is the deliverable most likely to be under-scoped**, because the relocation's whole point
   is to make these files durable artifacts — and the sweep that would silently undo that is a known
   live defect (see § Dependencies, PLAN-TRUTH-017).
6. **D5 — tests, each verified to FAIL pre-fix, plus doc reconciliation.** (a) A build invocation
   without `--plan-id` is refused rather than defaulting to null. (b) A build result lands under the
   resolving plan's `build-results/`, asserted for both a real plan id and `NO_PLAN`. (c) A `kind=build`
   row carries the actual command and an outcome TOON whose result path resolves to a real file.
   (d) D0's population derivation is asserted non-empty and contains the known members. Reconcile the
   documented paths in `extension-api/standards/build-execution.md`, `build-api-reference.md`, and
   `manage-change-ledger/SKILL.md` in the same change — **the docs state the old path in at least six
   places and they are part of the contract, not commentary.**

## Scope note — six deliverables, split evaluated

Six deliverables meets the presumptive split threshold. **Proceeding unsplit, with rationale recorded:**
D2 is impossible without D1 (no guaranteed plan id ⇒ no plan directory to write into), and D3's result
pointer is meaningless without D2's location. All three mutate the *same* resolution seam and the *same*
four wrappers, so a split would have the second plan rebasing onto the first across identical functions
and re-grounding everything it touched. The operator's request states the chain explicitly.
⛔ **D0 is the designed escape hatch**: if the derived population is materially larger than the sampled
surface, split at outline along the D1 / D2+D3 boundary and record the decision.

## Claim Labels

- **OBSERVED**: the `NO_PLAN` sentinel exists and is production infrastructure — `resolve_plan_context`
  in `tools-file-ops/scripts/file_ops.py` is the single plan-context resolver and accepts it; it
  resolves to `{base_dir}/plans/NO_PLAN`, is auto-created on first use, and for the sentinel the
  working-tree root is ALWAYS the main checkout. Documented at `tools-file-ops/SKILL.md`
  § "The `NO_PLAN` sentinel".
- **OBSERVED**: build logs currently resolve to `.plan/temp/build-output/{scope}/{tool}-{timestamp}.log`
  via `_LOG_SUBPATH`, `_resolve_log_base_dir`, and `create_log_file` in
  `script-shared/scripts/build/_build_result.py` — **a single seam**, which is what makes D2 tractable.
- **OBSERVED**: `REQUIRED_FIELDS` in `_build_result.py` is
  `{status, exit_code, duration_seconds, log_file, command}` — the outcome TOON already carries a
  `command` field, so D3 must establish whether it holds the resolved argv or a summary before adding
  a second one.
- **OBSERVED — duration is produced and then discarded.** `duration_seconds` is a REQUIRED build-result
  field set by all three constructors (`success_result`, `error_result`, `timeout_result`), while
  `manage-change-ledger/scripts/**` contains **zero `duration` tokens** (grepped this pass) and the
  documented `kind=build` field list omits it. ⇒ The measurement exists at the producer and is dropped
  at the ledger boundary; D3 plumbs it through rather than introducing new instrumentation.
- **OBSERVED**: the `kind=build` ledger entry already exists with the field set quoted in § Provenance —
  read at `manage-change-ledger/SKILL.md` § the three kinds, and its canonical `append --kind build`
  invocation. `plan_id` is explicitly documented `str|null`, null for an orchestrator global-tier build.
- **OBSERVED — the mechanism, and it is the crux**: the executor template resolves the ledger plan_id as
  `extract_plan_id(script_args) or audit_plan_id`, in
  `tools-script-executor/templates/execute-script.py.template`. It **sniffs the dispatched script's own
  argv** for a plan id and falls back to the executor's `--audit-plan-id`. ⇒ **A wrapper that has no
  `--plan-id` flag can never contribute one**, and the row silently stamps null.
- **OBSERVED**: `build-maven/scripts/maven.py` contains **no `plan_id` token in any spelling** (both
  spellings grepped, zero hits), while `build-pyproject/scripts/pyproject_build.py` **does** accept
  `--plan-id` (for footprint resolution). ⇒ **The build wrappers are already inconsistent with each
  other** — this is not a uniform gap being uniformly closed.
- **HYPOTHESIS**: `build-gradle` and `build-npm` match `build-maven` (no plan-id). **Confirm/refute at
  D0** — the orchestrator grepped only the pyproject/gradle/npm trio for `plan.id` and read the result
  for pyproject only. Confirm/refute artifact: the argparse surface of `gradle.py` and `npm.py`.
- **HYPOTHESIS**: `build-server-client`'s `kind=job` writer takes the same nullable `plan_id` and needs
  the same treatment. **Confirm/refute at D0.** Confirm/refute artifact: the `submit` verb's ledger
  append in `build-server-client`.
- **HYPOTHESIS**: `.plan/temp/build-output` appears in exactly the six doc locations grepped.
  **Confirm/refute at D0 — a single-token grep states a sample.**
- **Verify-first clause**: D3 must read the existing `kind=build` row's `args` field against a real
  ledger entry before adding a command field. If `args` already reconstructs the actual command line,
  D3 re-scopes to *documenting and pointing at* it rather than adding a duplicate field — and the
  standing rule *"where a copy exists, delete the copy"* governs the outcome.

## Expected Surface

- **OBSERVED**: `plan-marshall/skills/script-shared/scripts/build/_build_result.py` — `_LOG_SUBPATH`,
  `_resolve_log_base_dir`, `create_log_file`, `REQUIRED_FIELDS` (by symbol, not line)
- **OBSERVED**: `plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` —
  the `kind=build` writer and `extract_plan_id` / `extract_audit_plan_id`
- **OBSERVED**: `plan-marshall/skills/manage-change-ledger/**` — the entry schema and `append` surface
- **OBSERVED**: `plan-marshall/skills/build-maven/scripts/maven.py` (no plan-id today)
- **OBSERVED**: `plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` (has plan-id)
- **HYPOTHESIS**: `build-gradle/**`, `build-npm/**`, `build-server-client/**` (verify-at-outline, D0)
- **OBSERVED**: `plan-marshall/skills/extension-api/standards/build-execution.md` and
  `build-api-reference.md` — documented output paths
- **HYPOTHESIS**: `tools-file-ops` if the plan-dir `build-results/` subdirectory needs a resolver
  (verify-at-outline)
- **HYPOTHESIS**: tests under `test/plan-marshall/{script-shared,tools-script-executor,manage-change-ledger,build-*}/**`

## Dependencies and Sequencing

- **Depends on**: none.
- ⛔ **SERIALIZATION PAIR with PLAN-TRUTH-010** (`fail-closed-signal-integrity`). TRUTH-010 owns the
  defect where `resolve-test-scope`, `--help`, and `parse --log` write a **false `kind=build` success
  row**, flipping freshness stale→fresh — **the same executor dispatch boundary and the same ledger row
  this plan modifies.** These two MUST NOT run concurrently, and whichever lands second re-grounds.
  ⭐ Consider whether TRUTH-010's "which invocations are genuinely build-class" question should be
  settled FIRST — making `plan_id` mandatory on a set that wrongly includes `--help` would propagate
  the misclassification into a stricter contract.
- ⚠ **PLAN-TRUTH-017 interaction — the relocation moves INTO its blast radius.** TRUTH-017 is the live
  defect where `detect-artifacts` offers a running plan's own live artifacts as safe-to-delete. Moving
  build results into the plan directory makes them exactly that class of file. ⇒ **D4 must not assume
  plan-dir placement is inherently safe**; it is safe only once TRUTH-017's D3 invariant (an active
  plan's own artifacts are never offered) holds. Sequence or cross-check deliberately.
- ⚠ **Adjacent, verify before pairing — PLAN-TRUTH-005** (emitted 2026-07-31, `manage-build-server`).
  Different skill from `build-server-client`, so believed disjoint, but both sit in the build-server
  family. **Re-derive at emit rather than trusting this line.**
- ⚠ **PLAN-TRUTH-019** (`build-gate-coverage-parity`) touches the local gate's build invocations —
  check for overlap at outline.
- **Adjacent to**: `code-intelligence-substrate`'s `truthful-signals-021` (see below) — the consumer of
  this plan's D1, not a competing implementation.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-026-mandatory-plan-id-plan-scoped-build-results-and-build-ledger.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
