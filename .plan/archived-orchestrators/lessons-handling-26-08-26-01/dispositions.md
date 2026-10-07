# Per-Lesson Dispositions

One row per scanned lesson. The scan population is `manage-lessons list` — **87 active**
of 92 total (5 are pre-existing `superseded` stubs on the `cleanup-superseded` retention
lifecycle, outside the active corpus and not scanned).

Every row carries a disposition and a cluster. `Read` records how much of the lesson this
run could actually read, because three distinct read outcomes occurred and they are not
interchangeable:

| `Read` | Meaning | Count |
|--------|---------|------:|
| `full` | `get` returned metadata and a body | 71 |
| `title-only` | `get` succeeded; the record carries **no body at all** — `add` allocated the stub and `set-body` never ran | 11 |
| `unresolvable` | `list` enumerates it `active`; `get` returns `not_found`, so no documented read path resolves it | 5 |

⛔ **A `title-only` or `unresolvable` row's cluster assignment is derived from its title and
from sibling lessons that cite it by id — not from its body.** For the five `unresolvable`
rows the body was never read by anything in this run; two of them are described second-hand
inside `2026-08-08-20-002`, and those descriptions are the only evidence for their subject.
Treat every such assignment as a HYPOTHESIS the receiving plan re-checks at outline.

## Disposition totals

| Disposition | Count |
|-------------|------:|
| `clustered-into` | 84 |
| `standalone` | 3 |
| `already-covered` | 0 |
| `stale` | 0 |
| **Total** | **87** |

`already-covered` is **deliberately zero**. That verdict requires naming a covering clause
AND resolving the concrete input on which that clause's own worked example resolves. No such
verification was performed in this run, and claiming coverage without it is the fail-open
`PLAN-TRUTH-044` exists to repair. Several lessons plausibly overlap shipped work — for
example `2026-08-23-17-001` states in its own body that its transport half is already closed
— but "plausibly covered" is not the verdict, and the residual half is what carries forward.

`stale` is zero for the same reason: no lesson's premise was re-checked against HEAD.

## C01 — A guard's verdict computed over an empty or unexamined population

Destination: `truthful-signals` · PLAN-LH2-01 · 7 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-09-22-004` | full | clustered-into | The standing rule: publish the empty population, report `indeterminate`, never a verdict. |
| `2026-08-23-20-001` | full | clustered-into | `review_commitments reconcile` → `clear` over `commitments_considered: 0`. |
| `2026-08-24-08-001` | full | clustered-into | Same seam, and the population is empty **by construction** at order 9 — no PR exists yet. |
| `2026-08-26-10-001` | full | clustered-into | Same seam again: population derives from `pr-comment` findings only, so a self-review-only run is empty. |
| `2026-08-24-16-003` | full | clustered-into | `scope_creep_check` → `residual_count: 0` with `reason: no_baseline_sha`. |
| `2026-08-24-09-002` | full | clustered-into | `scan_manage_invocation` → `findings: 0`, `population_size: ""`. |
| `2026-08-26-06-003` | full | clustered-into | 33 of 37 plugin-doctor rules report `findings: 0` with an empty `population_size`. |

⭐ The three `review_commitments` rows are one seam observed on three plans with three
different empty-population causes. They are not one observation counted three times.

## C02 — A test or fixture that cannot fail

Destination: `truthful-signals` · PLAN-LH2-02 · 4 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-09-22-001` | full | clustered-into | The matched-negative-control standard: "the guard did not fire" is not evidence it works. |
| `2026-08-26-05-001` | full | clustered-into | Reentrant-acquire FIFO test short-circuits before the enqueue its own name asserts. |
| `2026-08-24-17-001` | full | clustered-into | `parse_stdin_task` truncates `verification.criteria` to one line → a task that cannot fail its own verification. |
| `2026-08-08-19-004` | full | clustered-into | An anti-vacuity fixture asserting pass/fail only — the plan reproduced its own target defect. |

## C03 — A routed build loses `tests_run` and asserts "this run tested nothing"

Destination: `truthful-signals` · PLAN-LH2-03 · 4 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-23-17-001` | full | clustered-into | Inner 17916 vs outer 0. Body states the transport half is CLOSED; the unavailable-count case is the residual. |
| `2026-08-24-16-002` | full | clustered-into | Inner 18083 vs outer 0, at `_build_execute_factory.py`. |
| `2026-08-24-18-001` | title-only | clustered-into | Inner 18123 vs outer 0. Title carries the whole finding; no body exists. |
| `2026-08-23-13-001` | unresolvable | clustered-into | Inner 17888 vs outer 0, per its `list` title. Body never read. |

⭐ **Four independent observations of one defect across four plans.** That recurrence count is
the cluster's strongest argument and is derived from the enumeration above, not asserted.

## C04 — A confident verdict refuted by data already at the same site

Destination: `truthful-signals` · PLAN-LH2-04 · 5 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-26-06-001` | full | clustered-into | Freshness gate corroborates on notation alone; the `command` field naming `quality-gate` is in the same ledger row. |
| `2026-08-25-17-001` | full | clustered-into | `files_exist` calls a glob non-existent while its sibling check expands that identical glob to 431 files. |
| `2026-08-26-09-001` | full | clustered-into | `_start_daemon` returns `running: True` on both branches — a structural constant named like an observation. |
| `2026-08-26-15-001` | full | clustered-into | `ci pr merge-queue` corroborates `enqueued: true` against the branch RULE, not this PR's membership. Confirmed twice by a second observer. |
| `2026-08-24-14-001` | unresolvable | clustered-into | `baseline-reconcile` counts merge-tree informational lines as conflicts, per its `list` title. Body never read. |

## C05 — `affected_files` is a plan-time projection, not an observed footprint

Destination: `truthful-signals` · PLAN-LH2-05 · 5 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-23-19-001` | full | clustered-into | 15 real vs 13 recorded, from 5 missing and 3 phantom — disagrees in BOTH directions. |
| `2026-08-26-06-002` | full | clustered-into | 54 live vs 52 recorded, 6 live-only and 4 recorded-only; a scope gate missed its own F1 trigger. |
| `2026-08-25-05-001` | title-only | clustered-into | Never REWRITTEN after outline, so re-reading a stale value cannot detect staleness. |
| `2026-08-25-09-012` | full | clustered-into | Scope-source indeterminacy decided by LLM judgement — identical input, opposite coverage decisions. |
| `2026-08-25-09-004` | full | clustered-into | `branch-cleanup` leaves `realized_footprint` unwritten; all four resolver tiers miss on the merge-queue path. |

⚠ **The two both-directions measurements are independent** (different plans, different
counts). Neither is a restatement of the other, and together they refute the
"recorded ⊆ live" assumption in both directions rather than asserting it once.

## C06 — Doc-contract divergence: a documented surface the live one rejects or contradicts

Destination: `truthful-signals` · PLAN-LH2-06 · 15 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-23-16-001` | full | clustered-into | `triage.md` prescribes `deliverable: 0`; the validator's falsy check rejects it. |
| `2026-08-24-12-002` | full | clustered-into | `--measured-diff-size` passed unconditionally; argparse rejects the empty case — inside a fail-closed merge gate. |
| `2026-08-25-09-008` | full | clustered-into | Step 5b names `plan-marshall:marshall-orchestrator:orchestrator`; the live notation is `plan-orchestrator`. |
| `2026-08-08-20-003` | full | clustered-into | `manage-logging read --phase` validates its input and applies no filter. |
| `2026-08-24-08-002` | full | clustered-into | `pr_intent_section` appends Intent after the footer; the template declares a mid-body slot. |
| `2026-08-25-06-001` | title-only | clustered-into | Same defect, sharpened: the render is also non-idempotent and truncates, losing non-goals. |
| `2026-08-24-09-001` | full | clustered-into | Branch A `display_detail` template cannot satisfy the 80-char ASCII cap the same document states. |
| `2026-08-26-13-001` | title-only | clustered-into | Same defect, re-observed: renders over 80 chars with a non-ASCII dash. |
| `2026-08-26-08-001` | full | clustered-into | `data-model.md` says the lane value is validated; only `finalize-steps set-lane` validates it. |
| `2026-08-25-09-011` | full | clustered-into | Anchor table's `change_type` key space omits `enhancement`, which the emitter produces. |
| `2026-08-25-09-013` | full | clustered-into | Two declared report sections have no producer; their non-emission reports as benign. |
| `2026-08-25-09-009` | full | clustered-into | Consumer forbidden from recomputing `orchestrated`/`epic`; the dispatcher does not send them. |
| `2026-08-26-05-007` | full | clustered-into | Docstring promised three guards, the body implemented two; the missing one silently inverted a time comparison. |
| `2026-08-23-13-002` | unresolvable | clustered-into | `scope_creep_threshold` documented as a `marshal.json` override in two places; the check never reads config. |
| `2026-08-08-19-001` | unresolvable | clustered-into | The archived-plan audit's argparse-rejection corpus (463 signatures across 48 of 58 plans), per `2026-08-08-20-002`'s description of it. |

⚠ **Fifteen members — the receiving epic should expect to split this.** Two internal pairs
(`24-08-002`/`25-06-001` and `24-09-001`/`26-13-001`) are each one defect observed twice;
folding them is a merge, not a discard.

## C07 — Restated counts and underived completeness claims

Destination: `truthful-signals` · PLAN-LH2-07 · 7 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-08-21-003` | full | clustered-into | Deletion, not correction; plus the widening hunk PLANTS its own stale counts. |
| `2026-08-09-13-001` | full | clustered-into | Correction failed three rounds running; refined — interior deletion silently rebinds pronouns. |
| `2026-08-25-09-002` | full | clustered-into | Derive every set/count/partition claim; two cancelling errors read as consistent for two rounds. |
| `2026-08-25-09-003` | full | clustered-into | A zero from a content search proves absence only for the forms the pattern can express. |
| `2026-08-08-20-001` | full | clustered-into | Four retrospective cross-checks hard-code a population that drifted from its source. |
| `2026-08-08-21-002` | full | clustered-into | A count comparison whose two sides share a pivot proves nothing — a topology defect, not a population one. |
| `2026-08-09-22-003` | full | clustered-into | Two witnesses that share a bias are one witness; establish independent producers before recording corroboration. |

## C08 — The run's own measurement is unrecoverable

Destination: `code-intelligence-substrate` · PLAN-LH2-08 · 7 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-25-09-007` | full | clustered-into | Six ledgers, no two agreeing, none reaching the true firing count of 7; none publishes a denominator. |
| `2026-08-25-09-006` | full | clustered-into | `record-dispatch-boundary` stamps `now()`, so an honest backfill fabricates the timeline every correlator keys on. |
| `2026-08-26-05-002` | full | clustered-into | 3.5M dispatched tokens and **no cost figure at all** — both measurement paths empty. |
| `2026-08-25-09-010` | full | clustered-into | `--iteration` exists and is not passed, making the per-round yield curve unrecoverable. |
| `2026-08-25-09-005` | full | clustered-into | The retry path skips the resolve seam the `[DISPATCH]` emission rides — 5 of 7 firings invisible. |
| `2026-08-08-20-004` | full | clustered-into | `record-metrics` ordered after `plan-retrospective`, so the efficiency aspect never sees `6-finalize` (~40% understatement). |
| `2026-08-25-09-014` | full | clustered-into | `compile-report` auto-deletes the fragment bundle on success, so acting on its own warning costs 19 tool calls. |

⭐ Routed to `code-intelligence-substrate` under the token-reduction arm: every member is a
reason the cost of a run cannot be measured, and measurement is that epic's blocking
dependency.

## C09 — Self-review loop mechanics

Destination: `review-apparatus` · PLAN-LH2-09 · 6 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-25-15-001` | full | clustered-into | Terminate on self-seeding, not on an empty round — an empty round cannot tell convergence from oscillation. |
| `2026-08-08-19-006` | full | clustered-into | Re-run detectors over the FIX diff; the delta round shipped, the intra-round re-scan did not. |
| `2026-08-08-19-005` | full | clustered-into | A finding raised at the iteration ceiling can be reported but never remediated. |
| `2026-08-23-22-001` | full | clustered-into | Surfacer emits docstring prose only; assertion messages and comments are invisible to every round. |
| `2026-08-24-20-001` | title-only | clustered-into | Findings returned but not persisted to `qgate-6-finalize.jsonl`; the store under-reports the step. |
| `2026-08-26-05-006` | full | clustered-into | Seed the candidate surface from the plan's own target defect class — targeting, not a new check. |

## C10 — Review-bot participation and reliability

Destination: `review-apparatus` · PLAN-LH2-10 · 8 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-26-16-001` | title-only | clustered-into | Sourcery rate-limit refusal credited as participation: a third budget phrasing matches no pattern and no fallback. |
| `2026-08-26-17-001` | title-only | clustered-into | pr-agent reports absent — its response outruns `review_bot_buffer_seconds` and it publishes no check-run to wait on. |
| `2026-08-25-07-001` | title-only | clustered-into | `_grade_comparison` returns clean on a non-empty intersection; comparison carries no coverage dimension. |
| `2026-08-26-05-004` | full | clustered-into | In-house gate 5, external bot set 0, on the same diff — with 0 of 3 reviewers measurable and the merge proceeding. |
| `2026-08-08-21-001` | full | clustered-into | A boolean from a fallible read has three inputs and two branches; the fold asserts a state nobody gathered. |
| `2026-08-08-21-005` | full | clustered-into | A correctness fix has a direction, and the direction has an error budget. |
| `2026-08-08-21-004` | full | clustered-into | Splitting one state into N obliges N reachable remedies, not N names. |
| `2026-08-25-09-015` | full | clustered-into | A consumer gated on one of two disjointly-reported sets is unreachable, and its test pins the gap. |

⚠ Eight members; the receiving epic decides fold-vs-split. `26-05-004` explicitly warns
**against** spending another round on bot-charter exhortation — the failure it records is
empty/refused/refused-structural, which no charter change addresses.

## C11 — Review triage discipline

Destination: `review-apparatus` · PLAN-LH2-11 · 3 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-25-09-016` | full | clustered-into | A reverted partial fix reads as a refuted finding; a rejection re-checked against the prior verdict is vacuous authority. |
| `2026-08-25-09-017` | full | clustered-into | Verify before ACTING, not only before rejecting — `fixed` is the highest-scoring and least-verified disposition. |
| `2026-08-09-22-002` | full | clustered-into | A review may RAISE a severity by reasoning; it may not LOWER one without executing the call site. |

⭐ These three close one rule from three sides: the rejection half, the acceptance half, and
the softening half. They were filed by different plans and are complementary, not redundant.

## C12 — Plugin-cache and registry-pin staleness

Destination: `truthful-signals` · PLAN-LH2-12 · 3 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-25-06-002` | title-only | clustered-into | Agents served 0.1.1240 while scripts resolve 0.1.1541; the served body prescribes a flag no script declares. |
| `2026-08-25-09-001` | title-only | clustered-into | The pin gap is a CORRECTNESS hazard producing duplicate landings, not merely a version delta. |
| `2026-08-25-15-002` | full | clustered-into | Stale per-worktree derived state reads as a source defect after a rebase; regenerate before triaging. |

## C13 — Build and test infrastructure

Destination: `truthful-signals` · PLAN-LH2-13 · 3 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-23-18-001` | full | clustered-into | Coverage instrumentation pushes subprocess tests past the 30s conftest budget; a timeout reads as an assertion failure. |
| `2026-08-08-22-001` | full | clustered-into | The routed build's `log_file` is the job log, not the pytest log; calibrate with a control before believing a zero. |
| `2026-08-08-19-003` | unresolvable | clustered-into | The archived-plan audit's in-task-build churn finding, per `2026-08-08-20-002`'s description of it. |

## C14 — The orchestrator stops short

Destination: `truthful-signals` · PLAN-LH2-14 · 2 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-26-15-002` | full | clustered-into | Six operator interventions in one run with all three `*_without_asking` knobs true; the sixth was a MANUFACTURED blocker. |
| `2026-08-26-05-003` | full | clustered-into | Five yields with no operator question pending; 404,605 tokens (11.4%) spent on non-completing dispatches. |

## C15 — Early-phase gate quality

Destination: `truthful-signals` · PLAN-LH2-15 · 3 lessons

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-26-05-005` | full | clustered-into | Domain detector scored zero narrative matches on a plan whose footprint is 7 of 10 `.py` files. |
| `2026-08-08-19-007` | full | clustered-into | A 100%-across-all-dimensions confidence score has no mechanical discriminator from a self-graded one. |
| `2026-08-08-19-008` | full | clustered-into | Ordering asserted in Approach prose is inert — `phase-4-plan` reads only `depends` metadata. |

## C16 — Git and worktree integrity

Destination: `truthful-signals` · PLAN-LH2-16 · 1 lesson

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-24-16-001` | full | **standalone** | Four tracked files vanished with no identified cause; the only instance was force-removed, so nothing survives to diagnose. |

⛔ The lesson itself states **the cause is unknown and it records an observation, not a
diagnosis**. The routable part is the `worktree-remove` payload change (distinguish
"dirty with work" from "dirty with recoverable deletions"), which does not depend on the
cause being found.

## C17 — The cost-reducing lane levers are unadopted

Destination: `code-intelligence-substrate` · PLAN-LH2-17 · 1 lesson

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-08-19-002` | full | **standalone** | 49 of 53 plans over their armed target, `recipe_routed: 0`, `minimal_posture_chosen: 0`, 3 light-lane fires. |

⭐ Its own body records that the checkpoint metric is `input + output` and therefore scores
**the small end of the bill** — `cache_read` is 76.2% and `output` 1.1% over the same 53
plans. That reframing, not the miss count, is why this routes to
`code-intelligence-substrate`.

⚠ This lesson is one of the three YAML-frontmatter files: it enumerates with empty
`component`/`title` but its body IS readable via `get`, unlike its two siblings.

## C18 — `manage-lessons` corpus integrity

Destination: **this epic (self)** · PLAN-LH2-18 · 2 lessons + this run's own first-party observations

| Lesson | Read | Disposition | Note |
|--------|------|-------------|------|
| `2026-08-08-20-002` | full | clustered-into | YAML frontmatter parses to empty metadata; `list` and `get` disagree; the dedup gate cannot see the affected lessons. |
| `2026-08-25-05-002` | title-only | clustered-into | Reports the membership disagreement at **n=2**. This run measured **n=5**. |

### First-party observations from this drain

Three corpus defects were observed directly while executing this scan. They are OBSERVED,
not inferred, and each is reproducible by re-running the enumeration:

1. ⛔ **Five lessons enumerate as `active` and `get` returns `not_found`** —
   `2026-08-08-19-001`, `2026-08-08-19-003`, `2026-08-23-13-001`, `2026-08-23-13-002`,
   `2026-08-24-14-001`. Lesson `2026-08-25-05-002` records this class at n=2; the population
   has since grown to 5.

2. ⛔⛔ **The empty-metadata explanation in `2026-08-08-20-002` is REFUTED as a general
   rule.** That lesson names `19-001`, `19-002` and `19-003` as the three YAML-frontmatter
   files and attributes the `not_found` to that encoding. But `2026-08-08-19-002` — a
   YAML-frontmatter file by that lesson's own account, enumerating with empty
   `component`/`category`/`title` exactly like its siblings — **resolves through `get` and
   returns its full body**. So YAML frontmatter is not sufficient to cause `not_found`, and
   the mechanism is unestablished. Whatever discriminates `19-002` from `19-001`/`19-003` has
   not been identified.

3. ⛔ **Eleven lessons carry a title and NO body at all** — `2026-08-24-18-001`,
   `2026-08-24-20-001`, `2026-08-25-05-001`, `2026-08-25-05-002`, `2026-08-25-06-001`,
   `2026-08-25-06-002`, `2026-08-25-07-001`, `2026-08-25-09-001`, `2026-08-26-13-001`,
   `2026-08-26-16-001`, `2026-08-26-17-001`. `add` allocated the stub, `set-body` never ran,
   and the write path reported success. The titles are long enough to carry the finding —
   which is why the loss is survivable here and why it is invisible to anyone reading `list`.
   ⚠ All eleven fall in a contiguous date band (08-24 → 08-26), which points at a producer
   change rather than at eleven independent authoring slips. **Unestablished:** which producer,
   and whether the bodies were ever written.

⛔ **This epic performs NO retirement.** The prior lessons epic
(`lessons-handling-26-08-08-01`) drained its corpus under explicit operator direction and hit
exactly one blocked file that required a filesystem `rm` outside any sanctioned verb. That
direction was given for that run; it is not standing authority, and the `remove` defect it
surfaced is still unfixed. Retirement here is deferred to an operator decision.

## Clustering signals used

In the priority order the mode contract sets:

1. **Explicit cross-reference between bodies** — used heavily; many lessons name siblings by
   id in a `See also` / `Related` section.
2. **Shared failure mode described in different words** — the primary signal for C01, C04,
   C06 and C07, and the reason the `manage-lessons aggregate` grouping was NOT adopted
   verbatim.
3. **Shared subject surface** — used for C03, C05, C08, C12.
4. **Shared `component`** — used last, and never on its own.

⚠ **`manage-lessons aggregate` was run and its output was NOT taken as the clustering.** It
returned 15 groups over 64 of the 87 lessons using cross-ref and shared-component signals
only. Both signals proved noisy here: its largest cross-ref group folded six topically
unrelated lessons that merely cite one co-captured sibling, and its largest shared-component
group folded 16 lessons under `phase-6-finalize`, which is a component bucket rather than a
failure mode. It was used as a corroborating input to the manual clustering, not as its
substitute.
