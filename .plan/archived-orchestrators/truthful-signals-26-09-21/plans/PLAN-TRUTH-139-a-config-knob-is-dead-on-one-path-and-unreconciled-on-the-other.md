# PLAN-TRUTH-139: `build.queue.max_slots` is dead on one path and unreconciled on the other

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-06 from a foreign-repo data-point, **corroborated first-party in full** — including a
live observation of this machine's running daemon. ⭐ **The reporting session's headline was a
CORRECTION of its own prior answer**: it had said the daemon's config source depends on its resolution
context at launch, then established that the resolution is *dead by construction*. It also noted its
earlier "it's moot, the value is 5 either way" had **landed on the right number for the wrong reason** —
and that the reason matters, which is why this spec exists.

## Objective

**`build.queue.max_slots` is a documented, resolvable configuration knob that CANNOT affect the daemon
path at all, and on the fallback path is applied per-caller against machine-global shared state with no
reconciliation. Neither failure reports itself.**

### The daemon path — dead by construction

Verified at HEAD `66320e70d`, and the ordering is the whole defect:

| Site | Fact |
|---|---|
| `marshalld.py:686-687` | `main()` calls `double_fork()` **then** `build_daemon()` |
| `marshalld.py:238` | `double_fork()` does `os.chdir('/')` |
| `marshalld.py:662` | `build_daemon()` calls `read_json(get_marshal_path(), default={})` |
| `file_ops.py:1274-1303` | `get_tracked_config_dir()` resolves cwd-relative (step 4 walk-up for `.plan/local`, step 5 `./.plan`) |
| `_marshalld_scheduler.py:212-222` | `resolve_max_slots({})` returns `DEFAULT_MAX_SLOTS` |
| `_marshalld_scheduler.py:43` | `DEFAULT_MAX_SLOTS = 5` |

⇒ From cwd `/` both resolution steps yield `/.plan/marshal.json`, which does not exist; `read_json`
degrades deterministically to `{}`; the cap is unconditionally **5**.

⭐ **Confirmed on the live daemon, not only by reading**: pid `79473`, `cwd = /`, `/.plan` absent, and no
`PLAN_TRACKED_CONFIG_DIR` / `PLAN_BASE_DIR` in its environment.

⛔⛔ **So setting `max_slots: 8` in any project changes NOTHING on the daemon path.** The knob is
documented, resolvable, validated — and unreachable. **An operator who sets it has no way to learn it
did not take.**

### The fallback path — per-caller cap over machine-global state

`build_queue.py:190` `_resolve_max_slots()` reads `build.queue.max_slots` from the **calling project's**
marshal.json, and `:400` / `:532` apply it to the shared queue at `~/.plan-marshall/build-queue.json`.

⛔ **Project A with `max_slots: 8` admits up to 8 entries into the same slot file that project B,
reading `max_slots: 2`, believes holds at most 2.** Each admitting caller applies its own cap to shared
state; **effective concurrency is whatever the most permissive currently-admitting project says**, and
**nothing detects or reports the disagreement.**

### ⭐⭐ The category error underneath both

`_marshalld_scheduler.py:9` calls it **"the machine-CPU cap"** in its own docstring. ⇒ **It describes a
property of the MACHINE, and it lives in a git-tracked per-repo file that gets cloned to machines with
different core counts.** There is no machine-global knob for it today — **which is why the daemon ended
up hardcoded.** The hardcoding is a symptom of the misplacement, not an independent bug.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the population of knobs with this shape before fixing this one.** Enumerate every
config key read by a process that `chdir`s away from its resolution root, and every key applied
per-caller against machine-global shared state. ⛔ **`max_slots` was found by an operator asking a
question, not by a sweep — so it is one member found by one accident, never the population.** Publish
both counts and the overlap. D0 may legitimately find it is the only member; **that is a result, and it
must be published as one.**

**D1 — the daemon must not silently accept an unreachable resolution.** Whatever the eventual home, a
config read that resolves to a path outside any project must **report that it could not look**, not
degrade to a default that is indistinguishable from a configured value. ⛔ **Do NOT fix this by
resolving the config before `double_fork()` and calling it done** — that repairs one call site and
leaves the class. The reachability of the resolution is the reportable fact.

**D2 — give the cap a machine-global home.** It is a machine property; site it next to `registry.json`.
⚠ **The per-repo key cannot simply be deleted**: the fallback path reads it today and consumers set it.
D0 decides the migration shape — precedence, deprecation, or both — and **whichever is chosen, a repo
key that no longer takes effect must SAY SO** rather than resolving silently.

**D3 — the fallback path reports cap disagreement.** When an admitting caller's cap differs from the cap
under which existing entries were admitted, that divergence is **reported**, not reconciled silently.
⛔ **Reconciling by picking one cap is out of scope and probably wrong** — the two projects genuinely
disagree, and the queue cannot know which is right. **Naming the disagreement is the deliverable.**

## Claim Labels

- OBSERVED: `main()` calls `double_fork()` before `build_daemon()` (`marshalld.py:686-687`), and `double_fork()` does `os.chdir('/')` (`marshalld.py:238`). First-party at HEAD `66320e70d`.
- OBSERVED: `build_daemon()` reads `read_json(get_marshal_path(), default={})` at `marshalld.py:662`, and `get_tracked_config_dir()` (`file_ops.py:1274-1303`) resolves cwd-relative with a `./.plan` fallback.
- OBSERVED: `resolve_max_slots({})` returns `DEFAULT_MAX_SLOTS = 5` (`_marshalld_scheduler.py:43, 212-222`).
- OBSERVED: the running daemon on this machine is pid `79473` with `cwd = /`, and `/.plan` does not exist. Live observation, not inferred.
- OBSERVED: `_marshalld_scheduler.py:9` describes the value as "the machine-CPU cap" in its own docstring.
- OBSERVED: `build_queue.py:190` resolves the cap per caller from the calling project's marshal.json and applies it at `:400` / `:532` to shared state.
- ⚠ HYPOTHESIS: the fallback queue state is machine-global at `~/.plan-marshall/build-queue.json`. ⛔ Reported by the sender and NOT independently confirmed by this orchestrator. Confirm/refute at `build_queue.py`'s state-path resolver (verify-at-outline).
- ⚠ HYPOTHESIS: no machine-global knob for this value exists anywhere today. ⛔ An asserted ABSENCE, which is the higher-risk half — **verify it directly, do not assume.** Confirm/refute against the machine-global config surface next to `registry.json` (verify-at-outline).
- ⚠ HYPOTHESIS: `max_slots` is the only key with this shape. ⛔ NOT corroborated — it was found by one accident. D0 owns it and may return `indeterminate` (verify-at-outline).
- ⚠ HYPOTHESIS: two projects with different caps admitting concurrently produces over-admission in practice. ⛔ Reasoned from the code, NOT observed. Confirm/refute by a two-caller control at outline (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — the `double_fork` / `build_daemon` ordering (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` — `DEFAULT_MAX_SLOTS` and `resolve_max_slots` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/build_queue.py` — `_resolve_max_slots` and the admitting call sites (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` — `get_tracked_config_dir`, only if D1 sites the reachability report there (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md` — the documented knob and its new precedence (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-build-server/**`, `test/plan-marshall/manage-locks/**` — the D1/D3 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Adjacent to `PLAN-TRUTH-104`** (a clear verdict over an empty population reported as a checked negative). ⛔ **Keep separate**: `-104`'s subject is a verdict published over nothing; this one's is a *configuration read* that cannot reach its source. **Same family, different layer** — name the archetype in both shipped docs, share no code.
- ⚠ **`_DEFAULT_MAX_SLOTS = 5` is duplicated** — `_marshalld_scheduler.py:43` and `build_queue.py:166` define it separately. **Two constants for one machine property**, which D2 should collapse rather than preserve.
- ⛔ **Re-derive `corpus cross-check` before emitting** — this spec's surface has never been machine-checked against the corpus.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-139-a-config-knob-is-dead-on-one-path-and-unreconciled-on-the-other.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐⭐⭐ RE-SCOPED 2026-09-06 (OPERATOR DIRECTION) — THE DELIVERABLE IS A CROSS-REPO CENTRAL CONFIG, NOT A BUG FIX. THIS IS THE NEXT PRIORITY.

⛔ **Operator direction supersedes this spec's original framing.** It was staged as *"a knob is dead on
one path and unreconciled on the other"* — a defect report. **The requirement is the positive one:**

> **A way to centrally configure parallel runs across repositories.**

⇒ **D2 is now the LEAD deliverable, not the third.** The dead daemon read and the per-caller cap are
**evidence that no central surface exists**, not the subject. A fix that repairs the resolution order
and leaves the value in a git-tracked per-repo file **satisfies none of the requirement.**

### The requirement, stated so outline cannot narrow it back to a bug fix

1. **One value, machine-scoped**, sited with the machine-global state (next to `registry.json`), because
   it describes the machine's CPU capacity — `_marshalld_scheduler.py:9` says so in its own docstring.
2. **Every consumer reads that one value** — the daemon's scheduler AND `build_queue.py`'s fallback
   admission — so the two paths cannot disagree.
3. **A per-repo override, if it survives at all, must SAY when it does not take effect.** ⛔ The current
   silence is the whole defect; a precedence rule that is also silent reproduces it one layer up.
4. **The cross-repo case is the primary case, not an edge.** Projects A and B on one machine share one
   queue; the configuration must be shared too, or the sharing is unmanaged.

⚠ **Operator's interim guidance stands until this lands: treat the key as MUST-BE-IDENTICAL-EVERYWHERE
and leave it at 5.** That is the only value where both paths agree with each other and with the daemon,
so nothing surprising happens when the daemon goes down and builds fall back.

## ⛔⛔ DAEMON-LOG SWEEP 2026-09-06 — FOUR ODDITIES, ALL FIRST-PARTY, AND ONE IS A LIVE BLIND SPOT

Operator asked for a look at the daemon log. Findings, in severity order:

### 1 — ⛔⛔⛔ BOTH build-recording surfaces have been BLIND for two days, and report success

| Surface | Last record |
|---|---|
| daemon interaction-audit (`manage_build_server logs`) | **2026-09-04T09:55:38Z** |
| build change-ledger (`.plan/work/change-ledger.jsonl`) | **2026-09-04T09:55:39Z** |

⛔ **`-126`, `-093` and `-089` ALL ran `verify` during their 2026-09-05 finalizes.** Not one of those
builds appears in either surface. ⇒ **The build-time oracle has recorded nothing for two days while
builds ran, and nothing reports the gap.**

⚠ **HYPOTHESIS for the cause, NOT corroborated**: callers stopped routing to the daemon (see oddity 2)
and the direct path does not write the ledger. **D0 must establish which of {daemon bypassed, ledger
writer broken, both} is true — the two have different fixes and the evidence so far cannot separate
them.**

### 2 — ⛔⛔ The running daemon is STALE BY FOUR VERSIONS, and the surface says so honestly

```text
running_binary_path:  .../plan-marshall/0.1.1603/skills/manage-build-server/scripts/marshalld.py
resolved_binary_path: .../plan-marshall/0.1.1607/skills/manage-build-server/scripts/marshalld.py
binary_diverges: true
```

⭐⭐ **This is a POSITIVE CONTROL and must not be "fixed" away**: the status verb detects the
divergence, names **both** paths, and states the remedy in its own `note`. **A stale daemon is visible.**
⚠ It connects to `PLAN-TRUTH-129`'s `executor_mismatch` fold: a caller at `0.1.1607` submitting to a
`0.1.1603` daemon is exactly the shape that rejection describes — **and that rejection's wording sends
the reader to a version diagnosis, which here would be RIGHT for once.**

### 3 — ⛔⛔ Attribution is 97.97% absent, and it has THREE SPELLINGS

Re-derived from the raw JSONL (**484 lines parsed, 0 unparseable** — an earlier TOON reading showed a
field shift that was a *parse artifact of the reader*, not a data defect; stated so nobody chases it):

| `plan_id` | rows |
|---|---:|
| `None` (JSON null) | **371** |
| `'NO_PLAN'` | **64** |
| `'none'` (literal string) | **1** |
| a real plan id | **8** |

**435 of 444 build rows (97.97%) carry no usable attribution.** ⛔⛔ **And three distinct spellings of
the same absence** — `null`, `NO_PLAN`, `none` — which is `PLAN-TRUTH-124`'s subject (one ledger
vocabulary) reproduced inside the build ledger. ⇒ **A consumer that filters on any ONE of them
under-counts, silently.**

### 4 — ⚠ The daemon's own audit log carries a 75% failure rate over its tiny population

4 submits / 4 fates across three days: **3 failures, 1 success.** ⛔ **n=4 is far too small to price**,
and it is stated here **only** so D0 does not read the log's brevity as quiet health. **The population
is the finding, not the ratio.**

## ⭐⭐ THE CLUSTER — corpus review for corresponding aspects (operator direction)

A sweep of every live spec for parallel/concurrency config, machine-vs-repo scoping, unreachable config
knobs, `NO_PLAN` attribution and daemon subjects returns **one coherent cluster of four**:

| Spec | Its half of the daemon/build subject |
|---|---|
| **`-139`** (this) | the cap has no central home; the daemon read is dead; the fallback cap is per-caller |
| **`-105`** | build execution verdicts mislead on the healthy path — **and it already owns the `NO_PLAN` attribution fold (20 references, the most of any spec)** |
| **`-118`** | `_start_daemon` returns `running: True` with **no `_running_pid()` re-probe** — now this spec's D3-led remainder |
| **`-129`** | `marshalld submit` rejects a relative executor path as `executor_mismatch`, sending the reader to a version diagnosis |

⛔⛔ **These four are ONE subsystem seen from four seams, and shipping any one alone leaves a daemon
that is stale, unattributed, unconfigurable and mis-diagnosing.** ⇒ **Whichever lands first must not
coin a private vocabulary for daemon state**; `-124` exists to end exactly that. ⚠ **They are NOT
merged**: their remedies are genuinely different (config siting, verdict honesty, a start-probe, a
rejection message), and merging four into one would breach the split guard on the first fold.

⚠ **`-132` is adjacent, not in the cluster**: a frozen manifest param with no staleness detector is
*a configured value that goes stale*; this spec is *a configured value that never arrives*. **Same
family, different failure — name it in both shipped docs, share no code.**
