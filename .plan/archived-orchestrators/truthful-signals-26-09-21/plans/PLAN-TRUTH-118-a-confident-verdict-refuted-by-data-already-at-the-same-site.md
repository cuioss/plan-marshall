# PLAN-TRUTH-118: A confident verdict refuted by data already at the same site

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from the `lessons-handling-26-08-26-01` drain, message `-004` (5 lessons).

## Objective

**The discriminating data was present, at the same site, in the same payload — and the check read the
wrong field.** ⭐ **This is the cluster's argument for existing separately from its two siblings: the
discriminating evidence is already at the site, so no member needs new plumbing to OBSERVE the defect.**

⛔ **RE-SCOPED 2026-08-27 — do not read that as "these are the cheapest fixes in the corpus", which is
how this spec was first written and is REFUTED.** Cheap *observation* does not imply cheap *remedy*: at
least two of the five need a new call rather than a different field read (`26-09-001`'s liveness probe,
first-party refuted at HEAD; `26-15-001`'s per-PR membership read). **D0 sizes each member
individually.**

The boundary against the siblings is exact and must survive into the shipped docs:

| Cluster | What went wrong |
|---|---|
| `PLAN-TRUTH-104` empty-population | The check looked at **nothing** |
| `PLAN-TRUTH-116` cannot-fail test | The test's **arrangement** made its subject unreachable |
| **This plan** | The refuting data was **already there** and the check read the wrong field |

## Deliverables

1. **D0 — GATE: derive the population, and per member decide read-a-different-field vs new-call.**
   ⛔ The router's "all five are fixable by reading an already-present field" claim **holds by
   inspection for two members and is NOT established for a third** (see Claim Labels). Settle it per
   member before scoping; a member needing a new call is a different-sized deliverable.
2. **D1 — `pre-commit-verify-freshness` corroborates a full test run from a lint run.** It reports
   `status: fresh`, `notation_cross_check: corroborated`, while the **same ledger row** carries
   `tests_run: 0`, `analyses_examined: compile, lint`, `command: ./pw quality-gate plan-marshall`.
   ⛔ Every build canonical shares one notation, so a notation-only filter **cannot** distinguish a lint
   run from a full test run — and the fields that would are already on the row.
3. **D2 — `files_exist` reports a glob absent that its sibling check expands to 431 files.** In the
   **same pass**, `declared_scope_reconciliation` expands `marketplace/bundles/**/*.py` to 431 files
   while `files_exist` reports it *"does not exist"* and remediates *"create the file"*. Reproduced
   across **all five declared globs in one pass**. ⇒ Share the expansion helper, or state why two
   expansions exist.
4. **D3 — `_start_daemon` returns `running: True` on both branches**, the post-spawn one with **no
   liveness re-probe**: a structural constant named like an observation, in a result dict whose own
   prose invites callers to *"gate on a field that can report failure"*.
5. **D4 — `ci pr merge-queue`'s `enqueued: true` is a claim about the branch rule, not this PR.** Its
   corroboration string is *"merge_queue rule active on branch"* — a property of **branch protection
   config**. `landing-state` stayed `pr_open` across ~25 minutes and three polls; the queue was
   `externally_managed`, so **membership is not something the branch rule can report**. ⭐ The upstream
   doc already concedes it: `standards/pr-operations.md` calls the GitHub arm *"a pre-enqueue probe …
   run BEFORE the `gh` call"* ⇒ **a documented PRE-condition consumed as a POST-condition.** The defect
   is the reading the field's name invites, not a lie in the code. **Practical rule to ship:** after
   `pr merge-queue`, confirm with `pr auto-merge` (which reports `disposition: enabled | enqueued`) or
   by polling `pr view` for `state: merged`.
6. **D5 — `baseline-reconcile` counts merge-tree informational lines as conflicts.** ⚠ Title-derived
   only (see Claim Labels); confirm before scoping.

⭐ **The shape to copy is in the same run as D4:** `merge-queue` reported unverified success while
`safe-merge` **refused honestly** with a specific explanation — catching the #1081 false-green landing
defect at the tool layer — and `auto-merge` worked. **The honest refusal is the model.**

## Claim Labels

- OBSERVED: the four full-body instances with their quoted payloads and named sites — `2026-08-26-06-001`, `2026-08-25-17-001`, `2026-08-26-09-001`, `2026-08-26-15-001`
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D1 and D3 mechanisms grounded in real code; D1 is now FIXED (_freshness_crosscheck.py) while D3 remains open (manage_build_server.py:560-565)
- OBSERVED, and unusually strong: `2026-08-26-15-001` was **independently confirmed by a second observer, twice, in a different session** — the `truthful-signals` orchestrator hit it landing PRs #1347 and #1350 and recorded it BEFORE draining the lesson. ⭐ Two independent observations, not one narrative echoed. This epic's own R114 carries it.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The merge_queue rule active on branch string is still present unchanged in github_ops.py at HEAD
- HYPOTHESIS: `2026-08-24-14-001` (D5) belongs in this cluster. ⛔ **It is UNRESOLVABLE** — `manage-lessons list` enumerates it `active` and `get` returns `not_found`, so its body was read by nothing in that run and the assignment rests on its `list` title alone. Confirm/refute at the lesson file once the corpus-integrity defect is fixed (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-08-24-14-001 body unreachable per the spec own note (list says active, get says not_found)
- ⛔ **RE-SCOPED 2026-08-27 — the "all five are fixable by reading an already-present field" claim is REFUTED for at least TWO of the five, so the cluster's cheapness premise does not hold uniformly.** It holds by inspection for `26-06-001` (the lesson says so explicitly) and `25-17-001` (a shared expansion helper). It does **not** hold for `26-15-001` (a per-PR membership read may be a new API call), and it is now **first-party refuted for `26-09-001`**: `_start_daemon`'s post-spawn branch calls `_spawn_detached(...)` and returns `'running': True` **with no `_running_pid()` re-probe between them** — read at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py`:558-566 at HEAD `91a07aaa4`. ⇒ **Its remedy is a liveness PROBE — a new call — not a different field read.** The cluster is still coherent (a verdict contradicted by same-site evidence) but **D0 must size each member individually rather than inheriting "cheapest fixes in the corpus" from the router's framing.**
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage_build_server.py _start_daemon still calls _spawn_detached then returns running:True with no _running_pid() re-probe between them
- Verify-first clause: settle D4's remedy shape before scoping — if per-PR membership requires a new API call, D4 is not a cheap field-read and belongs sized accordingly.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: No isInMergeQueue-style per-PR field found in the codebase; the new-call-vs-field-read question for D4 is not settleable here

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/**` — the `merge-queue` / `auto-merge` verbs (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md` — the pre-enqueue-probe concession (D4) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`:982 — the branch-rule probe that emits the `enqueue_corroboration` string (D4); added 2026-09-11 by the fold of `api-sheriff-deployment-configurability-007`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/**` — `_start_daemon` (D3) (verify-at-outline)
- HYPOTHESIS: the pre-commit freshness verifier and its ledger reader (D1); the `files_exist` / `declared_scope_reconciliation` pass (D2); `baseline-reconcile` (D5) — ⛔ **paths NOT re-derived by the router; resolve each by symbol at outline before declaring the surface** (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Overlaps with `PLAN-TRUTH-105`** (build-execution verdicts) at D1 if that plan touches the ledger row's reader. Re-run `corpus cross-check` at emit.
- ⚠ **TWO LIVE-PLAN overlaps, measured 2026-08-27 at `91a07aaa4` (1 file each):** `a-failing-ci-call-reports-success` (review-apparatus `PLAN-PR-027`, at `5-execute`) and `plan-footprint-is-unknowable-to-its-own-graders` (`PLAN-TRUTH-098`, running). ⛔ **At N=1 these are SEQUENCING notes, not blockers** — no two plans run together — but this spec must not be emitted while either is in flight without re-checking that one file. ⭐ Also overlaps `PLAN-CIS-060` (`verdict-field-read-and-write-integrity`) in a sibling epic; **a duplicate held in another ledger is invisible to this epic's queue**, so confirm against `manage-status list` at emit, never against this queue alone.
- Adjacent to: `PLAN-TRUTH-104`, `PLAN-TRUTH-116`, `PLAN-TRUTH-117` — the four sibling classes of this epic's theme. Keep the boundary table above in the shipped doc; it is the thing that stops them being merged.
- ⚠ D4's practical rule is ALREADY IN FORCE operationally (this epic's R114 and lesson `2026-08-26-15-001`); this plan makes it mechanical, and must not present it as a new discovery.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-118-a-confident-verdict-refuted-by-data-already-at-the-same-site.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 — inbox drain (2 message(s))

- **`deployment-and-refresh-gaps-023`** (relayed from Token-Sheriff, observed across PRs #697/#698/#699) — *`pr safe-merge --strategy squash` is silently ignored on a merge-queue-enabled repository, and nothing documents that.* The call printed `The merge strategy for main is set by the merge queue` and **the flag was ignored**: the call only ENQUEUED the PR and the queue applied its own configured strategy. ⛔ `tools-integration-ci/SKILL.md:328` **advertises `[--strategy merge|squash|rebase]` on the wrapper’s own surface**, and a search of the marketplace skills tree finds **no statement anywhere that a merge queue overrides it**. The parameter is accepted, shape-validated, and then has no bearing on the outcome — **the only indication is a line of upstream stdout the caller may never surface.**

  ⭐⭐ **The sharpest framing, and the reason it belongs in this spec: “the flag is not wrong, it is UNANSWERABLE — and an unanswerable parameter reported as accepted is indistinguishable, at the call site, from one that took effect.”** It does not return a wrong value; it returns **no signal at all**, which the caller reads as confirmation. ⚠ It is more than cosmetic because **the strategy decides the shape of the landed history the plan then reconciles against**: a caller that believes it squashed and a queue that merged disagree about what the merge commit looks like. Either honest resolution closes it — detect the queue and reject or report the applied strategy, or document the override on the `safe-merge` surface.

  ⭐ **Note the sender’s own restraint, which is worth keeping:** it explicitly WITHHELD an adjacent observation (a monitor’s auto-enqueue never firing, traced to a command-substitution fallback returning empty under `zsh`) because that pattern *“appears nowhere in the marketplace skills tree”* — **attributing it upstream on that evidence would be a guess.**

- **`review-apparatus-025`** (carried-out finding `18f362`, `PLAN-PR-038`) — *the CI payload cannot establish WHICH commit was verified: run `head_sha` and run age contradict each other.* At PR #1388, `ci checks wait` returned `run_id 33790703017` with `head_sha 8148fed537da…` — **the current local HEAD, exactly** — while **the same run reported `elapsed_sec` growing 2347 → 2926 → 3495 → 3579**, i.e. a run created ~60 minutes earlier, **which predates that commit by a wide margin.** ⛔ **A run cannot have started an hour before the commit it verifies.** Either `head_sha` is the caller’s local `git rev-parse HEAD` echoed back rather than the RUN’s head (making it useless for attribution), or `elapsed_sec` measures something else — **and a consumer cannot tell which, so no consumer can establish which commit CI actually observed.**

  ⛔⛔ **Compounding observable, and it lands on the merge path:** in that same run `verify / verify` is **SKIPPED** while `verify / gate` passes in 12s and `verify / conclusion` passes in 3s. The push changed **Python source** (five modules plus six test modules), so a docs-only skip would be wrong and an already-covered-by-PR skip would point at the run for the **SUPERSEDED** commit. Waiting 511s produced no new run id. ⇒ **the required check reports green while it is unestablished that any heavy build observed this HEAD — exactly the condition the pre-merge barrier trusts.** ⭐ Counterweight recorded by the finding itself: local `verify` WAS green at that tree (23,760 tests), **so the code was verified even though the CI attribution was not** — the defect is the attribution, not the coverage. Remedy: publish the RUN’s head sha under a distinct key from the caller’s local HEAD, and publish `created_at` rather than a bare elapsed.

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§6.4 — a re-fired step REVERSING ITS OWN VERDICT on UNCHANGED code, and the evidence for the right answer was already in the run.** `finalize-step-simplify` ran at an early HEAD and **deliberately left wildcard imports alone with a stated reason**. Re-fired at a later HEAD it **reversed itself and "fixed" them**. The orchestrator committed the reversal with a confident message; **the next build rewrote it back and the commit was reverted.** ⭐⭐ *"The evidence for the correct answer was already in the run transcript."*

  ⭐⭐⭐ **The verdict-class distinction is the transferable content and it is exactly this spec's subject:** a repeated step re-firing at a later HEAD produces **two verdict classes with DIFFERENT TRUST** — about code the delta *changed* (**new information**), and about code it did *not* change and the step already ruled on (**a SELF-CONTRADICTION**: the inputs did not change, so **at most one verdict is right and the step offers no evidence which**).

  > **Treat the second as a FLAG, not a finding**: retrieve the earlier verdict and its reason, search the transcript, and **if the reversal cannot be justified from evidence, KEEP THE EARLIER VERDICT.**

  Possible mechanism the document offers: **pass the prior-firing verdict as a runtime input so the step can see it is contradicting itself.**

- **§8.1 — a zombie GitHub Actions run is unrecoverable in place, and the DETECTION half is where the value is.** 75+ minutes lost to two runs that could never reach a terminal state. ⛔ *"The await loop treats 'not yet green' as 'keep waiting', so the default is to burn the whole timeout on a run that was dead on arrival."* **Two cheap signatures**: run-level `status=completed` with `conclusion=failure` but **zero jobs having left `queued`** (a real failure has at least one job `completed` with a failing conclusion); and run-level `startup_failure` on any event. ⭐ **Inspect JOB-level states, not just the run conclusion** — which is the same *read the data already at the site* discipline this spec is named for.

  ⚠ **Recovery requires a NEW SHA** — an operator-approved `commit --amend --no-edit` + force-push producing a **byte-identical tree** — because that is what makes GitHub schedule fresh runs. **Two constraints, both load-bearing:** it rewrites published history so it needs explicit approval, and **verify the tree really is byte-identical afterwards so the recovery is provably a re-trigger and not a content change riding an infrastructure workaround.** ⛔ Note the trap the document flags: *"produce a new SHA"* is the recovery **here** and is **useless against a bot quota**, which is account-scoped.

## ⭐⭐ FOLDED 2026-09-05 — PLAN-TRUTH-093 drain (1 message)

- **`preference-admissibility-...-002`** — *a rationale that refutes a move nobody proposed preserves the
  defect it claims to justify.*

  **The spec's archetype with a twist worth naming: the refuting data is not merely at the same site — it
  is in the SAME PARAGRAPH.** A rationale answers a strawman alternative, concludes correctly *about that
  alternative*, and the conclusion is then read as justifying the status quo the real proposal targeted.
  ⛔ **The verdict is locally valid and globally wrong**, which is exactly why re-reading the rationale
  never surfaces it: nothing in the text is false.

  ⇒ **D0's detector must compare the rationale's REFUTED PROPOSITION against the proposition actually on
  the table**, not merely check the rationale for internal soundness. A soundness check passes this
  every time. ⚠ **Expected Surface unchanged: adds no file surface.**

## ⭐ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (0 contradicted, but D1 IS ALREADY SHIPPED)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts. Every claim that
could be checked CORROBORATED; this section records an **applicability** change, not a refutation.

⭐⭐ **D1 IS CLOSED IN THE TREE.** `manage-tasks/scripts/_freshness_crosscheck.py` and
`_cmd_pre_commit_verify_freshness.py` now implement the **two-dimensional notation-plus-coverage
cross-check** this spec's own objective describes. ⇒ **Do not re-derive it.** The positive account is the
files themselves, which is the A2 test this cleanup applies before retiring any deliverable.

⛔ **D3 IS STILL OPEN, and it is the reason this spec stays staged.**
`manage_build_server.py:560-565`: `_start_daemon` calls `_spawn_detached` and then returns
`running: True` **with no `_running_pid()` re-probe between them** — a success asserted over a state
nobody observed, which is this spec's exact archetype. ⇒ **Re-scope: this plan is now D3-led.**

⚠ **D4 is INDETERMINATE and must not be assumed.** No `isInMergeQueue`-style per-PR field was found, so
whether the fix is a new call or a field read **cannot be settled from the current source**. That is a
D0 question, not a premise. ⚠ Claim 2's lesson (`2026-08-24-14-001`) remains unreachable — `list` says
active, `get` says `not_found` — which is itself an instance of `PLAN-TRUTH-135`'s subject.

## ⭐⭐ FOLDED 2026-09-06 (c) — DAEMON-LOG SWEEP. A POSITIVE CONTROL FOR THIS SPEC, ON THE SAME COMPONENT AS ITS OPEN D3.

`manage_build_server status` on the live daemon returns:

```text
running_binary_path:  .../plan-marshall/0.1.1603/.../marshalld.py
resolved_binary_path: .../plan-marshall/0.1.1607/.../marshalld.py
binary_diverges: true
note: "running daemon is STALE: it is executing 0.1.1603, but a fresh start would resolve 0.1.1607"
```

⭐⭐⭐ **This is what this spec asks for, ALREADY WORKING, on the very component whose D3 is still
open.** The verb does not assert health it did not observe: it **detects** the divergence, **names both
paths**, and **states the remedy in its own note**. ⇒ **A stale daemon is VISIBLE.**

⛔ **Keep this as the positive control when D3 is implemented.** D3's defect is that `_start_daemon`
returns `running: True` after `_spawn_detached` **with no `_running_pid()` re-probe** — a success
asserted over an unobserved state. **The `status` verb on the same component demonstrates the correct
shape.** ⇒ **D3 should make `_start_daemon` report what `status` reports, not invent a new vocabulary.**

⚠ **The divergence is live right now (4 versions stale), so a D3 control can be exercised against a
real diverged daemon rather than a fixture.**

## ⭐ FOLDED 2026-09-11 — cross-repo lessons drain (1 API-Sheriff item): D4, a second repo, and the read-back named

`api-sheriff-deployment-configurability-007`: API-Sheriff PR #255 — `ci pr merge-queue` returned
`enqueued: true` / `enqueue_corroboration: merge_queue rule active on branch`; the PR sat `OPEN` for 30
minutes with an empty queue, `autoMergeRequest: null`, `mergeStateStatus: CLEAN`; `ci pr auto-merge`
immediately after put it in at `pos=1`. A finalize run trusting the return would have waited out its
whole `merge_queue_wait_budget_seconds` and reported a slow queue as the cause.

- OBSERVED at `356973d80`: the corroboration string is produced by the branch-rule probe
  (`workflow-integration-github/scripts/github_ops.py`:982), and no `mergeQueue` read exists anywhere in the
  marketplace's Python. ⇒ the corroboration attests *the branch has a queue rule*, not *this PR entered
  the queue* — which come apart exactly when the enqueue silently fails.
- ⭐ The concrete read-back, matching this epic's standing reference: after enqueuing, query the
  repo-level GraphQL `repository.mergeQueue(branch:).entries` and require an entry whose
  `pullRequest.number` matches before reporting `enqueued: true`; otherwise `status: error` naming the
  attempted route. (`isInMergeQueue` is not a `gh` field, and `mergeStateStatus` reads `CLEAN` while
  genuinely queued — neither is a membership signal.)
- ⚠ `pr auto-merge` emits the same `disposition_detail` string while actually enqueuing, so the string
  cannot discriminate the two routes either.

Expected surface updated in this same act: the probe lives in
`workflow-integration-github/scripts/github_ops.py`, outside the `tools-integration-ci/scripts/**` entry
already declared for D4, so it is declared below.
Corroborates local lesson `2026-09-06-16-001` (active), which a D4 landing retires.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-150-build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path.md` (PLAN-TRUTH-150)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
