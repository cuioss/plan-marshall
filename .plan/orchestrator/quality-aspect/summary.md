# quality-aspect — plans

### PLAN-01 ledger-joins — shipped (#1545)
Execution-log and dispatch-boundary ledger rows pair on a shared step-id key
instead of being summed per ledger. Per-task changed_files are persisted so
artifact emission stays measurable. Retrospective aspects publish the population
each figure was computed over, and split-plan footprints union every shipped
merge commit.
- step-id join key for the barely-pairing ledgers
- per-task changed_files persistence
- OUTCOME line for every completed task
- analyze-logs build_count reconciled with recorded calls
- RE_ENTRY_COVERAGE decoupled from its policed signal
- batched fragment registration
- per-firing DISPATCH comparison in dispatch audit
- manifest-consistency caveat on post-merge base-ref
- split-plan footprint union over all merge commits
- fragment paths resolved against a single plan root

### PLAN-02 build-telemetry
build_queue releases resolve the main checkout from inside a worktree, and every
build writes a change-ledger row so build time never reads as unavailable. Lock
accounting distinguishes concurrent plans' writes. Daemon, generator, and
capture-footprint failure modes carry diagnosable
evidence instead of empty stderr.
- build_queue release from inside a worktree
- change-ledger row per build
- coverage-report exit-1-with-empty-stderr diagnosis
- pollution guard distinguishing concurrent merge.lock writes
- down-daemon failover for concurrent suites
- branch-cleanup removing worktree metadata with the worktree
- generator interpreter resolution instead of hard-coded runner
- named rejected flag in capture-footprint failures
- accepted evidence named in build_scope_narrow refusal
- daemon job-log path never surfaced as an agent read instruction

### PLAN-03 verify-first-a
Delete-to-one-home fixes are verified by re-searching the literal, and self-review
prescriptions are applied as stated rather than narrowed. A round is clean only on
the propositions it enumerated, and unmeasured channels render as unmeasured —
never as clean zeros. Session ids are captured at finalize entry so every signal
stays attributable.
- delete-to-one-home verified by literal re-search
- context-load columns populated, enrich at metrics close
- billing-cost measurement before bounding re-fire
- metacharacter false-zero note for content search
- convergent resolutions applied as stated
- unmeasured channels rendered unmeasured
- round-cleanliness bound to enumerated propositions
- independent verification across self-review rounds
- should_emit fragments declaring could-not-look
- mirrored-site admission with scope
- session-id capture at finalize entry

### PLAN-04 verify-first-b
No phase-5 path reads an absent verdict as passing, and the four dispatch
context-load flags are passed at every call site. Closure claims carry
checkable arithmetic, and loop-back overrides re-arm the machinery they bypass.
- fallback tool for unsweepable lint roots
- cross-round defect recurrence detection
- residual-text classification of review actionability
- population-published signal-gate counts
- symmetric-pair comparison within one edit
- loop-back re-arm on out-of-band override
- could-not-look reporting in test-identifier asserts
- checkable closure arithmetic or no closure claim
- absent-verdict admission closed in phase-5
- context-load flags passed at every call site
- context-load forwarding at record-dispatch-boundary

### PLAN-05 review-yield-a
Poll pacing becomes dispatch-executable instead of bare sleeps a leaf cannot run.
Head-SHA evidence is three-valued rather than a bare bool, per-source review yield
is recorded before any bot is treated as required, and size-cap refusals are
recognized at FIND time instead of after the operator reads them.
- dispatch-executable wait replacing standalone sleep
- three-valued head_sha evidence
- per-plan review yield by source
- declined-claim bucketing by rationale effect
- size-cap refusal recognition at FIND time
- review invocations surviving their runtime
- narrowing remedy with named limit
- invocation-scoped review-producer refusals

### PLAN-06 review-yield-b
Quota-wait deadlines persist across killed sleeps and rate-window claims seed from
bot-stated ETAs. Refusals scope per invocation so a spent limit stops re-asserting,
sustained zero contribution becomes visible, and the Sourcery/CodeRabbit phrasings
observed in the wild match registry patterns.
- quota-wait deadline persisted across kills
- zero-contribution quorum visibility and action
- rate-window claim seeded from bot-stated ETA
- participation-site expectations on new CI read sites
- verdict helpers wired into production emission
- inline signal kept as gate complement, hardening banked
- Sourcery budget refusal phrasing in registry
- CodeRabbit reset-notice phrasing without trailing phrase
- provider nitpicks routed when test-only scope excludes them

### PLAN-07 footprint-surface — shipped (#1559)
The realized footprint is diffed against the upstream base with a recorded
creation SHA. Twin
declaration comparisons share one containment rule and report the classified
unevaluated state. Self-review surfaces against origin/main and fails loudly when
the local ref lags upstream.
- footprint diffs against upstream base
- plan_creation_sha in references
- retired references keys unlinked from step inputs
- sweep sizing on realized single-run throughput
- shared containment rule for twin comparisons
- classified unevaluated state, never row default
- surfacing against origin/main with fail-loud staleness
- hoisted-binding shadowing check in surfacing scope

### PLAN-08 baseline-reconcile
Localized git merge-tree prose is never parsed as file paths or conflict counts,
and drift recovery routes past gates refine cannot clear. Lesson dedup keys on
canonical component spelling. The frontmatter corpus split is closed: headers
normalized and the write path rejects malformed files instead of accepting ones no
id-keyed verb can reach.
- informational merge-tree lines excluded from conflicts
- documented-set contract test for termination-cause block
- frontmatter lessons normalized, write path closed
- localized git prose never parsed as file paths
- orchestration context forwarded from source id
- localized merge-tree conflict parser fix
- drift recovery clearing git-ancestry gates
- dedup on canonical component spelling

### PLAN-09 outline-sweep — shipped (#1551)
Tree-wide sweeps declare a form execution can satisfy rather than an enumerated
snapshot it outruns. Assessment covers every declared path including read-intent
ones, scope additions re-run the component pass, and success criteria are
operationalizable from the outline alone. Decline-on-merits work carries its
mutation list as an explicit upper bound.
- sweep declaration form satisfiable by execution
- assessment re-run on outline scope addition
- per-file assessments for downstream consumers
- success criteria operationalizable from the outline
- de-citing review trigger for stale shielded claims
- Q-gate outline gaps vs refine tension recorded
- Affected-files synced with Change-per-file promises
- assessment coverage over read-intent paths
- deliverable module derived from architecture inventory
- member-by-member checks for uniform-shape instructions
- title/summary counts re-derived from the request
- decline-on-merits mutation list as explicit upper bound

### PLAN-10 plan-execute-mechanics
Task files stage by absolute path so no stale prior attempt is silently read, and
phase-5 entry absorbs upstream commits only when overlap is genuinely zero.
Freshness returns one verdict per unchanged tree, the chain-tail predicate tests
deliverable completion, and deliverable-less edits are recorded as declared scope
changes.
- absolute-path tasks-file staging
- orchestrator post-return validation reachability
- verification-only guard honoring mutation_scope
- single-verdict freshness per unchanged tree
- declared_set_closure rewarding declaration growth
- registered finding type for scope_creep over-threshold
- overlap-aware self-absorb at first phase-5 entry
- deliverable-scoped chain-tail predicate
- OUTCOME before voluntary checkpoint yield
- deliverable-less edits as declared scope changes
- scope_estimate over edit targets
- manifest step-params freshness for written knobs

### PLAN-11 gate-predicates
Suspicion heuristics that fire on clean runs are removed or made signal, and
exclusions address sites rather than silently taking sibling sites in the same
file. Handshake failures carry diagnostics,
bounds come from live config, and the B7 predicate carves out orchestrator
handoffs while triage routes refutations to rejected.
- fixed-cost suspicion heuristics removed or made signal
- site-grained exclusions
- orchestrator-tier-handoff carve-out in B7
- triage route to rejected
- handshake diagnostics on empty-stderr failure
- handshake tolerance for legitimately decreased counts
- live-config bounds, never documented defaults
- bot STATUS bodies kept out of the pending barrier

### PLAN-12 worktree-paths
Plan directories resolve by uniform CWD walk-up so worktree-resident outlines are
found, and prepare/list/consult behave identically inside the worktree. Localized
git output never parses as conflicts, workflow prose names verbs instead of
describing intent, and argparse rejections classify by notation with the offending
flag named.
- uniform CWD walk-up plan resolution in consult
- directory/glob claims rendered and checked
- invalid-invocation classification from stdout
- idempotent prepare inside the worktree
- worktree-resident plan listing without file_not_found
- localized merge-tree output never parsed as conflicts
- main-anchored consult finding worktree outlines
- list-deliverables verb named in prose
- invocation-quoting workflow steps
- argparse/notation rejections classified per notation

### PLAN-13 self-review-detectors
Detectors see module and async-def docstrings plus AsciiDoc user documentation,
and the hand-mirrored-table class is surfaced with a regression fixture. Prompt
fields validate before dispatch, plugin-doctor stays precise on underivable
surfaces, and advisory as well as refuted findings reach terminal states with an
owner and bulk-resolve support.
- module and async-def docstring detection
- AsciiDoc user-documentation detectors
- hand-mirrored-table surfacer class
- authored-claim verification for sweeps
- plugin-doctor precision on underivable surfaces
- flag-loop break on unknown analyzer scope
- discharge-owned advisory findings
- refuted review findings recorded rejected
- bulk resolve for triage passes

### PLAN-14 chat-signal-halt
Chat-signal extraction keeps operator turns so no downstream aspect starves, and
transcript counts describe the intact text across the round-trip. The read filter
covers decision and work logs, version stamps name the shipped skill change, and
halt states narrate what the run waits for instead of announcing continuation and
ending the turn.
- operator-turn retention in extract-chat-signal
- wait-state narration on finalize gate halts
- continuation-without-progress treated as halt
- transcript counts describing intact text
- read-phase covering decision and work logs
- stamped skill version in sync-cache steps

### PLAN-15 config-guards
Non-object marshal.json roots are rejected before field access, and displayed plus
tested mode lists derive from the authoritative tuple instead of being restated
by hand.
- non-object marshal.json roots rejected
- mode lists derived from authoritative tuple

### PLAN-17 finalize-self-review
VERIFY emission is restored
across the lane, and fixes trigger whole-passage re-review rather than single-line
re-checks. Simplify reconciles outline-prose decisions, archive-plan completion
carries a receipt, and CI infrastructure noise
classifies as noise rather than defect.
- VERIFY emission restored across the finalize lane
- whole-round zero as the only benign zero
- Simplify reconciling outline-prose decisions
- prompt-field validation before dispatch
- stacked-child rebase before refusal re-read
- emitting-notation bucketing in lessons-capture gate
- archive-plan completion receipt
- mutates_source reconciled with edit behavior
- whole-passage re-review after self-review fixes
- infrastructure-noise classification for CI timeouts
### PLAN-18 cost-mergequeue
Finalize re-fire, the lane's dominant cost, splits into productive vs
unproductive with a round budget, and quality-gate auto-fix churn is accounted in
the realized footprint. Merge-queue enqueue proves PR membership instead of only
the queue rule, and derivation comments are verified against the adjacent code.
- productive vs unproductive re-fire separation with budget
- auto-fix churn in realized-footprint accounting
- merge-queue enqueue proving PR membership
- derivation-source comments verified against code

### PLAN-19 executor-target-fidelity — prio 1
Opencode runs execute opencode-fresh code: the executor detects its runtime target
and resolves scripts, imports, and refreshes from that target's roots — never from
the Claude plugin cache. Version skew between executed code and repo fails closed
instead of running silently outdated.
- target detection (env vars, marshal.json, probe) selecting script roots
- per-target executor generation with the opencode root walk
- opencode-side refresh pipeline with freshness gate
- PYTHONPATH and bootstrap dirs from target roots, cross-target refused
- stale-cache refusal in executor preflight
- finalize syncs the running target, never target-blind
- detection, resolution, and refusal matrix tests

## Owned elsewhere

### test-quality PLAN-180 test-fidelity-rules
Hoisted argv restricted to CLI-accepted forms; temp-root pruning scoped off the
session; project-wide default changes invalidating stating documents; test mirrors
pinned to published seams; yield-honest fixture docstrings; splits carved by
behavior cluster; live module object in TestFindSkillsRoot; single registration
for split modules; pytest basetemp out of agent scratch.
- CLI-accepted hoisted argv
- scoped temp-root pruning
- tool-default changes invalidating stating documents
- seam-pinned test mirrors
- yield-honest fixture docstrings
- behavior-cluster splits
- live module object in TestFindSkillsRoot
- single registration for split modules
- pytest basetemp out of agent scratch

### process-compliance PLAN-08 process-contracts
decision.log visibility for bypasses; PR-body edits through the abstraction;
idempotent intent rendering; re-review timeouts within leaf budgets; plan-local
manifest snapshots; findings persisted to the store; counts re-derived; footprint
prune gated on non-empty footprint.
- decision.log visibility for self-reported bypasses
- PR-body edit flow without bypass
- idempotent intent rendering
- re-review timeouts within leaf budgets
- plan-local manifest snapshots
- findings persisted to the finding store
- outline counts re-derived
- footprint prune gated on non-empty footprint
