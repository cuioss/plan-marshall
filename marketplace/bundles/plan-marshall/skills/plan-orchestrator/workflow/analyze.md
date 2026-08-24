# Analyze Verb Workflow

Workflow doc for the `analyze` verb: analyze a landed plan or a mid-flight observation and reconcile the ledger, or drain the epic's `inbox/` queue message by message when invoked with no paste. The untrusted-ingestion boundary, the log-everything posture, and the reconciliation direction (status.json → epic.md) are owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |
| analysis input | Yes | One of the four first-class input modes below. Pasted content is the DEFAULT mode. |

### The four input modes

| Mode | Source | Access |
|------|--------|--------|
| **Pasted content** (default) | The operator pastes the landing narrative, PR review threads, CI output, or an observation directly into the invocation | The operator's own narrative is trusted; **third-party text embedded in the paste** (PR comments, bot output, issue bodies, web excerpts) routes through the [`plan-marshall:untrusted-ingestion`](../../untrusted-ingestion/SKILL.md) posture before influencing any ledger write |
| **On-disk plan artifacts** | A finished plan's artifacts named by the operator (archived plan dir, metrics, execution manifest, PR state) | Read-only analysis within the small-ops carve-out; PR/CI state via read-side `plan-marshall:tools-integration-ci:ci` calls, never `gh`/`glab` directly |
| **Cross-repo** | A landing in ANOTHER repo the epic tracks | Read-side `git -C {other_repo}` and file reads; the other repo's content is externally-sourced and routes through the untrusted-ingestion posture |
| **Inbox scan** | The epic's own `inbox/` queue — the messages executing plans appended through their OUTBOX. Triggered by the operator invoking `analyze` with **no paste** | The message's own narrative is trusted exactly as an operator paste is; **third-party text embedded in a payload** routes through the [`plan-marshall:untrusted-ingestion`](../../untrusted-ingestion/SKILL.md) posture before influencing any ledger write |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Verify against ground truth

A pasted or read claim is a **lead, never a fact**. Before recording anything, corroborate each material claim against actual ground truth — the real diff, the real PR state (via the CI abstraction), the real artifacts, the real code. Claims that cannot be corroborated are recorded as unverified leads (a watch), not as findings.

Corroboration is this verb's one dispatchable sub-step, gated by the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule).

- **Dispatchable** — corroborating a full-ship landing against **first-party** ground truth (the real diff, the real code, the plan's on-disk artifacts, CI check state) when the read burden is large. The vehicle is `execution-context-{level}`, because the corroboration needs Bash for `git` and for the read-side `plan-marshall:tools-integration-ci:ci` calls; the prompt body carries the S1 read-only instruction. The dispatch level is config-resolved via `manage-config effort resolve-target --role orchestrator.analyze --plan-id none --caller plan-marshall:persona-plan-orchestrator --workflow {the doc the leaf loads}` (the four facts are NOT optional decoration: `--workflow` is what makes the resolve seam emit the `[DISPATCH]` line and its paired decision-log record, so a bare `--role` resolve leaves this dispatch with no trail at all — see [the canonical form](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule)) — the `orchestrator.analyze` surface, resolved through `orchestrator.effort.analyze` → `orchestrator.effort.default` → `plan.effort` → `inherit` and clamped by `orchestrator.effort.max` (see [`effort-roles.md` § Orchestrator role group](../../plan-marshall/standards/effort-roles.md)); its `target` field is the `execution-context-{level}` variant to dispatch. Return shape: `corroborations[N]{claim,verdict,evidence}`, with `verdict` one of `corroborated` / `contradicted` / `unverifiable`. The orchestrator consumes the return as data and performs every resulting ledger write itself.
- **Two-stage for untrusted third-party text** — when a claim's corroboration requires ingesting third-party text not already in the operator's paste (PR review-comment bodies, bot output, a remote issue body), the orchestrator runs the `ci` fetch **inline** (Bash never leaves the orchestrator), dispatches `execution-context-reader-{level}` with the fetched text to extract a candidate struct, and gates that struct through `validate_struct` with the schema selected from the source type — `--schema issue-body` for a remote issue or PR-comment body, `--schema ci-finding` for a CI/Sonar finding — carried from the source through the dispatch into the `validate_struct` call (see [`untrusted-ingestion` § Canonical invocations](../../untrusted-ingestion/SKILL.md#canonical-invocations)), and consumes only the `status: success` clamped struct. The reader level is config-resolved via `manage-config effort read --role orchestrator.reader` — the `orchestrator.reader` surface, resolved through `orchestrator.effort.reader` → `orchestrator.effort.default` → `plan.effort` → `inherit` and clamped by `orchestrator.effort.max`; the dispatch site composes the `execution-context-reader-{level}` variant name from that resolved level (the reader surface reads the level rather than calling `resolve-target`, because the reader variant name is composed, not the write-capable `execution-context-{level}`; see [`effort-roles.md` § Orchestrator role group](../../plan-marshall/standards/effort-roles.md)). The apparent vehicle mismatch dissolves because the reader never needs Bash: the only Bash-requiring part — the fetch — is deterministic and stays inline. No third write-capable verification stage is required; a validated claim that still needs corroboration against first-party ground truth is an ordinary instance of the dispatchable case above.
- **Inline-only** — parsing the operator's own paste (the rule's already-in-context clause); the verdict persistence below (it writes a spec); Step 3 granularity classification and the inbox-scan drain loop (its enumeration and archival are deterministic script calls, and each per-message branch feeds a ledger write); Step 4 landing-report authoring and every queue transition; Step 5 mid-flight observation (small, fork-adjacent, and it feeds a ledger write); Step 5b per-item disposition (it writes the corpus, a spec, or the queue); Step 6 logging and the resume-anchor write.

#### Step 2b: Persist each corroboration onto its spec

`analyze` is the **second producer** of the re-grounding verdict field; [`cleanup.md`](cleanup.md) Step 3 is the first. After the corroboration returns `corroborations[N]{claim,verdict,evidence}`, persist each verdict whose corroborated claim belongs to a staged spec in this epic's corpus — one `corpus set-verdict` call per claim, with the producer recorded as `{slug}/analyze`. See [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `corpus set-verdict` for the argument surface.

The field's grammar is defined once at [orchestration-model.md § Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is restated nowhere here; `corpus set-verdict` is its only sanctioned emitter, so this step never hand-writes the line. Without this persistence, `analyze`'s contradictions stay prose-only and the consumer — [`orchestrate.md`](orchestrate.md) Step 4's prep-ready admission test — parses a half-populated field, which is the partial-coverage failure both producers exist to close. A corroboration whose claim belongs to no staged spec in this epic (a landing narrative's own assertion, a cross-repo claim) is recorded in the landing report as before and persists no verdict.

### Step 3: Classify the granularity

Decide which output contract applies:

- **Full ship** — a tracked plan landed (merged PR, closed lifecycle). Follow Step 4.
- **Mid-flight observation** — a signal about in-flight or adjacent work with NO ship semantics. Follow Step 5.

For the three single-item modes (paste / on-disk / cross-repo) the classification is made once, over the one item the operator supplied, and the verb follows the single branch it selects. Under **inbox scan** the classification is made **per message** by the drain loop below.

#### Step 3 (inbox scan): drain the queue message by message

The drain semantics — enumeration order, the report-never-skip rule for a malformed message, archival as the consume marker, and the unbroken append-only invariant — are owned by [`standards/inbox-envelope.md`](../standards/inbox-envelope.md) § Drain semantics. Do NOT inline-copy them here.

1. **Enumerate once**, at the top of the drain:

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox list \
     --slug {slug}
   ```

   The returned `messages[]` table is the drain's work list. An empty queue is a legitimate outcome: record the empty scan as a Step 6 decision — reading `live_count`, `closed_senders` and `invalid_count` to say WHICH kind of zero it was, per the table there — and return with `messages_scanned: 0`.

2. **For each message the enumeration reported `valid`, read its `lifecycle` BEFORE its `kind`.** (A row whose `valid` is false is item 3's, and neither table here applies to it — its header was not validated, so its `lifecycle` is not a fact the drain may act on.) The row's `lifecycle` says whether the message is still a live claim at all, and `kind` says only what a live claim would be routed as — so a row whose lifecycle is terminal is dispositioned here and its `kind` branch is **not** run. Two rules, applied in this order, before the routing table below:

   | `lifecycle` | Disposition | Why the `kind` branch must not run |
   |---|---|---|
   | `superseded` | Record as **retired by successor** (naming the row's `superseded_by`), archive, and stop. Disposition token: `retired_by_successor` | The envelope records this message as retired in favour of a named successor. Routing it on `kind` would drive a full ship reconciliation for a landing its own envelope retired — a `landings/` write and a `queue --transition … --status shipped` for a claim that has been withdrawn. The successor carries the live claim and is enumerated in its own right. |
   | `stream-end` | Record as **the sender's stream closure** (naming the `sender_id`), archive, and stop. Disposition token: `stream_end_noted` | A `stream-end` marker carries `kind: finding` **by design** — the envelope schema has no control-record kind — so the table below would absorb a control record as a substantive observation, manufacturing a Watch or Open Defect out of "this sender is done". |

   A `live` lifecycle falls through to the routing table. Both rules above still **archive**, so both dispositions count inside `messages_archived` and the closure equation in § Output holds unchanged.

   Then, for each remaining (`lifecycle: live`) message **in the returned order**, map its `kind` to a branch. The three `kind` values are exhaustively routed — no kind is left unhandled:

   | `kind` | Branch |
   |--------|--------|
   | `landing` | Step 4 (full ship — landing report + full reconciliation) |
   | `finding` | Step 5 (mid-flight observation — minimal reconciliation) |
   | `candidate-lesson` | Step 5b (per-item disposition) |

3. **A message the enumeration reported as invalid is NOT processed.** Record it as an Open Defect in `epic.md` naming the validator error code the row carried, and **leave it in `inbox/` un-archived** so it stays visible to the next drain. An invalid message never routes to a branch and never counts as consumed. **Apply the same dedup discipline Step 5b carries**: because the message deliberately survives the drain, every subsequent scan re-enumerates it — a message already tracked by an existing Open Defect FOLDS into that entry (record the recurrence on it) and never becomes a second one.

4. **Archive on consume.** Archive every message immediately after its disposition is **persisted** — a Step 4 landing reconciliation, a Step 5b disposition, or a Step 5 absorption into a Watch or Open Defect (the `observed` disposition). This covers every consuming disposition `drained[]` enumerates (`reconciled`, `observed`, the four Step 5b outcomes, and the two Step 3 item 2 lifecycle dispositions `retired_by_successor` and `stream_end_noted` — both archive on consume exactly as the others do, which is why the closure equation in § Output needs no fourth term). TWO dispositions are excluded, for distinct reasons: `invalid` — item 3 leaves it un-archived by design and never routes it to a branch — and `archive_failed` — its disposition WAS persisted, but the archival that would have consumed it was refused, so sub-item 4a records it as an Open Defect and sub-item 4b forbids re-applying the disposition. Retire the message:

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox archive \
     --slug {slug} --message {name}
   ```

   The order is **persist-then-archive, never the reverse**. An interrupted drain therefore re-processes at most the one in-flight message, and a completed drain is a no-op on re-scan.

   4a. **Read the returned TOON `status`. On `status: error` the message is NOT counted as archived.** Record it as an Open Defect in `epic.md` naming the message filename and the returned `error` code (one of `archive_conflict`, `archive_dir_unavailable`, `file_not_found`, `invalid_message_name`), and log the disposition through the same `manage-logging decision --store orchestrator` line Step 5b uses, naming the filename and the `archive_failed` disposition. **Apply the same dedup discipline items 3 and 5b carry**: a message already tracked by an existing Open Defect FOLDS into that entry as a recurrence rather than becoming a second one.

   4b. **A message whose archival failed retains its already-persisted disposition, and that disposition MUST NOT be re-applied on a later drain.** The Open Defect is the record that the message is awaiting operator recovery — `inbox archive --as-name` retires it under a non-colliding, sender-preserving archived name — not a signal to re-consume it. Without this rule the message stays schema-valid in `inbox/`, item 3's leave-un-archived path does not catch it, and every subsequent drain re-runs its full branch.

### Step 4: Full ship — landing report + full reconciliation

**Under inbox scan the landing narrative comes from the message payload rather than from an operator paste — and that changes the SOURCE, never the obligation.** The Step 2 verify-against-ground-truth contract applies unchanged and undiluted: the message is a **lead, not a fact**. The PR number, the merge state, and the deliverable set are corroborated against git and the read-side `plan-marshall:tools-integration-ci:ci` abstraction BEFORE `landings/PLAN-NN.md` is written, BEFORE the `queue --transition ... --status shipped` call at item 2, and BEFORE the three `queue --set-row` stamps at item 3. A claim the corroboration contradicts or cannot settle is recorded as an unverified lead (a watch), exactly as for a paste.

**Under inbox scan, run the drain-completeness check on the landing message FIRST** — this is the check that lets the orchestrator establish, after a zero-drain, that every REQUIRED fact drained (narrower than "nothing is outstanding" — see the `complete: true` bullet below):

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox landing-check \
  --slug {slug} --message {name}
```

Read `complete` and `missing_keys` from the TOON. A `landing` message carries a machine-readable `landing-facts` block specified by [`../standards/landing-payload-spec.md`](../standards/landing-payload-spec.md); the check reports whether that block is present and carries every required fact key.

- **`complete: true`** — the landing supplied every REQUIRED fact key, each with a real value rather than a degraded one. Two degraded classes are rejected on different terms: `n/a` asserts a real end state, so it reads as missing only at the keys that must exist (`plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`) and stays a legal answer at `pr` and `merge_state`; `unknown` asserts only that nothing was observed, so it reads as missing at EVERY key, `pr` and `merge_state` included. A `merge_state=unknown` landing is therefore INCOMPLETE — the drain records the failed read rather than reconciling against it as a settled merge fact. Reconcile normally (items 1–7). This is the whole of what the check establishes, and it is narrower than "the whole mechanisable delta drained": several mechanisable facts — the per-step typed facts, the wall-clock, the repository end-state — ride OPTIONAL keys the check does not require, so a complete landing may still be carrying none of them. So what a subsequent operator paste from that plan cannot surface is a **required** fact; it may still surface an optional one the producer never emitted. See [`../standards/landing-payload-spec.md`](../standards/landing-payload-spec.md) § "The report↔inbox delta" for which rows ride optional keys.
- **`complete: false`** — the landing carried only narrative, or a stale/partial facts block (a PRE-FIX landing has no block at all, so `missing_keys` names the whole required set). Record it as an Open Defect in `epic.md` naming `{name}` and the `missing_keys`, and log the disposition through the same `manage-logging decision --store orchestrator` line Step 5b uses, so the incompleteness is VISIBLE rather than reconciled-as-if-complete. The landing is STILL reconciled below — an incomplete landing is drained and its facts used as far as they go; the defect records that a manual paste from that plan may still surface something the inbox did not.

`complete: false` is a VERDICT, never a fault: the verb stays `status: success` and never aborts the drain. This check is what turns "the queue is empty" into "every required fact drained" — the two are the same only when every drained landing was complete. It does not reach the optional keys, so it never establishes that nothing whatsoever is outstanding.

**Parse the `steps` fact before reading any per-step outcome from it — split each element on its LAST colon.** The `landing-facts` block supplies `steps` as a comma-joined list of `{step}:{outcome}` elements, and a step id may itself be namespaced, so the pair is recovered by a last-colon split (`rsplit(':', 1)`) and NEVER by a first-colon one. This step is where the rule [`../standards/landing-payload-spec.md`](../standards/landing-payload-spec.md) § "Required machine-readable fact keys" states is APPLIED — there is no earlier parse, so a drain that reads the raw element list has silently skipped it:

| Element | LAST-colon split (correct) | first-colon split (wrong) |
|---|---|---|
| `push:done` | `push` / `done` | `push` / `done` |
| `project:finalize-step-plugin-doctor:done` | `project:finalize-step-plugin-doctor` / `done` | `project` / `finalize-step-plugin-doctor:done` |
| `plan-marshall:plan-retrospective:loop_back` | `plan-marshall:plan-retrospective` / `loop_back` | `plan-marshall` / `plan-retrospective:loop_back` |

⛔ A bare `push:done` element splits identically under BOTH directions, so getting it right is no evidence the rule was followed — the namespaced rows are the ones that discriminate, and `project:` and `plan-marshall:` step ids are ordinary entries in a composed finalize order. Apply the split to every element before item 1 authors the landing report and before item 3 stamps the queue; a first-colon split reports the bare namespace as the step name, which reconciles a real step's outcome onto a step that does not exist.

1. Write the landing report to `landings/PLAN-NN.md`, instantiated from [`templates/landing-analysis.md`](../templates/landing-analysis.md) via the Write tool: deliverable fidelity vs spec, metrics/anomalies, routing/merge behavior, reconciliation actions.
2. Mark the plan shipped in the machine authority:

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
     --slug {slug} --transition PLAN-NN --status shipped
   ```

3. Stamp the plan's three result fields, one `--set-row` call per field, so the landing is reconciled COMPLETELY by sanctioned calls. A `shipped`/`landed` row missing `pr` or `landing` renders the `(!) missing: ...` gap marker in the START-HERE block regenerated at item 6, so an unstamped row is visible rather than silent:

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
     --slug {slug} --set-row PLAN-NN --field pr --value "{pr_number}"
   ```

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
     --slug {slug} --set-row PLAN-NN --field landing --value "landings/PLAN-NN.md"
   ```

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
     --slug {slug} --set-row PLAN-NN --field plan_marshall_plan_id --value "{plan_marshall_plan_id}"
   ```

   `queue --set-row` is THE stamping mechanism. The whole-array `manage-status update-field --field plans` rewrite is reserved for `decompose`'s bulk queue seed (see [`decompose.md`](decompose.md)) and MUST NOT be used to stamp a landing — re-serializing every row to change one cell is the lost-update path `--set-row` exists to remove. Editing `status.json` by direct file access is prohibited outright (see the skill's Enforcement block).

4. Reconcile `epic.md` from status.json: the Ordered Queue table is a GENERATED block regenerated in Step 6 (⛔ **never hand-edit the rows between its markers**), so here you move the *narrative* sections the generator does not own — retire queue items the landing folded in (with a decision naming what absorbed them), move resolved Open Defects out, retire satisfied Watches, add new defects/watches the landing surfaced, and record any per-row sequencing caveat in the `### Queue annotations` zone.
5. Check parallelization consequences: when the landing revealed that two supposedly disjoint plans collided (rebase conflicts, re-verify signals), record the overlap so the next `next`-verb pairing decision uses it.
6. Regenerate both derivable blocks — the START-HERE block AND the Ordered Queue table — and paste each verbatim between its own markers (`resume-summary` and `ordered-queue`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
     --slug {slug}
   ```

7. **Conclude with the proactive emit.** Run the [`orchestrate.md` `next` selection](orchestrate.md) — its `parallelization_scope` read, `N − R` slot count, and disjoint-plus-prep-ready admission tests govern; do not restate them — and emit the resulting queue-filling copy-paste block. When nothing qualifies, state "nothing emittable, blocked on {X}" instead, enumerating each unemittable candidate and its blocking reason. The emit-only rule holds: the block is handed to the operator, never launched. The [`orchestrate.md` Step 5 `auto_emit` gate](orchestrate.md) applies unchanged: under `orchestrator.auto_emit == true` the emitted block's `launched` transitions are auto-recorded; under `false` (default) they stay operator-confirmed — and under **both** values the started/`running` transition remains operator-owned (emit≠running).

### Step 5: Mid-flight observation — minimal reconciliation

1. **Classify before writing anything.** Decide whether the observation is answered in full by a ledger entry (**absorb**) or warrants new work (**escalate**) — the branch is chosen before any write.
2. **Act on exactly one arm.** **Absorb** → record the observation as a Watch or Open Defect entry in `epic.md` — NO ship semantics, no landing report, no queue-status transition for the observed plan — and stop there: its `drained[]` disposition is `observed`, and it does NOT reach Step 5b. The absorb arm owes the SAME two-sided auditable record Step 5b requires (see § Step 5b): the `epic.md` entry plus a `manage-logging decision --store orchestrator` line naming the message filename and the `observed` disposition. An absorbed message is archived on consume like any other, so without that line it would leave the drain with no disposition record. **Escalate** → record nothing here; the observation goes to Step 5b and takes exactly one of the four dispositions there (a **fold** into an existing staged `plans/PLAN-NN-{plan_slug}.md` spec is `folded`, a **spawn** of a new spec plus its queue entry via the `decompose.md` Step 5 queue-write shape is `staged`). Anything larger than the small-ops carve-out becomes a plan, never inline work.
3. Regenerate both derivable blocks (START-HERE and the Ordered Queue table) when the queue was touched — the Step 4 item 6 invocation emits both.
4. **Conclude with the proactive emit** — the same standing output as Step 4 item 7, under the same `orchestrate.md` selection rules AND the same [`auto_emit` gate](orchestrate.md): emit the queue-filling block, or the explicit "nothing emittable, blocked on {X}" statement with a reason per unemittable candidate. `auto_emit == true` auto-records the emitted block's `launched` transitions; `auto_emit == false` (default) leaves them operator-confirmed; neither records started/`running` (emit≠running).

### Step 5b: Candidate-lesson message — per-item disposition

Applies to each `lifecycle: live` `kind: candidate-lesson` message, and to each `lifecycle: live` `kind: finding` message Step 5 did not absorb into a Watch or Open Defect. A `stream-end` marker is NOT in scope however this reads: it carries `kind: finding` by design but is dispositioned at Step 3 item 2 and never reaches Step 5, so it is not a `finding` "Step 5 did not absorb" — it is a control record Step 5 was never offered. Exactly one of the four dispositions below is applied per message — **`Promote` is restricted to `kind: candidate-lesson`**; a `kind: finding` message carries no corpus body shape and may take only Fold, Stage, or Discard.

| Disposition | Action |
|-------------|--------|
| **Promote** (`candidate-lesson` only) | Lift the payload into the global lessons corpus via the path-allocate flow — `manage-lessons add` to allocate, then `manage-lessons set-body` with the body staged to a file by the Write tool (see `manage-lessons` Canonical invocations → `add` and → `set-body`). The `candidate-lesson` payload already carries the corpus body shape, so no transcoding is needed. A `kind: finding` payload does NOT carry that shape, so `Promote` is never a valid disposition for it. |
| **Fold** | Fold the signal into an existing staged `plans/PLAN-NN-{plan_slug}.md` spec. |
| **Stage** | Stage a NEW spec plus its queue entry, via the [`decompose.md`](decompose.md) Step 5 queue-write shape. |
| **Discard** | The signal is already shipped, refuted, or out of the epic's scope — no corpus entry, no spec, no queue item. |

**Every message receives exactly one recorded, auditable disposition.** The record is two-sided and both sides are required: an entry in `epic.md`, and a decision-log line naming the message filename and the chosen disposition:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "inbox {message_name}: {disposition} — {rationale}" --store orchestrator
```

This mirrors the per-lesson disposition obligation [`lessons-handling.md`](lessons-handling.md) Step 3 already carries — no message leaves the drain without one.

**Apply the same dedup discipline.** A recurrence of an already-tracked signal FOLDS into the existing item (spec, queue entry, defect, watch, or corpus lesson) and never creates a duplicate. Recurrence is itself information: record it on the existing item rather than as a second one.

### Step 6: Log and set the resume anchor

**Under inbox scan, state WHICH KIND OF ZERO a drained queue was, from `live_count`, `closed_senders` AND `invalid_count` together — never from `count`, and never from `live_count` alone.** `count` is the enumerated total, so it says only how many files were there; it cannot distinguish a queue that has nothing left from one whose senders have all declared they will send no more. The `inbox list` payload carries the discriminator directly:

| `live_count` | `closed_senders` | `invalid_count` | The conclusion to record |
|---|---|---|---|
| `0` | empty | `0` | **Empty** — nothing is queued and no sender has declared closure, so a later message is still possible. |
| `0` | non-empty | `0` | **Finished** — every named sender filed a `stream-end` marker, so no further message is coming from them. Name the senders. |
| `0` | any | `> 0` | **Blocked** — nothing drainable, but messages remain that the drain refuses to consume. This is neither finished nor empty; name the `invalid_count` and the Open Defects recording them. |

⛔ These are three distinct states and the log must not collapse them: recording a blocked queue as "empty" claims a completed drain over messages nobody read, and recording an empty queue as "finished" claims a closure no sender declared. A non-zero `live_count` at the end of a drain is itself a discrepancy — the drain did not consume what it enumerated — and is recorded as an Open Defect.

Log the analysis decisions and reconciliations:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{analysis decision / reconciliation statement}" --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

## Output

```toon
status: success | error
display_detail: "analyze {slug}: {full-ship PLAN-NN | observation | N drained} reconciled"
slug: {slug}
mode: paste | on_disk | cross_repo | inbox_scan
granularity: full_ship | observation | -
plan: PLAN-NN | -
landing_report: landings/PLAN-NN.md | -
messages_scanned: {N}
messages_archived: {N}
messages_invalid: {N}
messages_archive_failed: {N}
landings_incomplete: {N}
drained[D]{message,kind,disposition}:
  orchestration-inbox-channel-001.md,landing,reconciled
  orchestration-inbox-channel-002.md,candidate-lesson,promoted
queue_items_retired: {N}
defects_added: {N}
watches_added: {N}
emitted[E]{plan,command}:
  PLAN-NN,/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
shortfall[S]{plan,reason}:
  PLAN-MM,"overlaps {surface} with PLAN-KK"
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

The block carries a singular half and a plural half, and `mode` says which half is live:

- **Single-item modes** (`paste` / `on_disk` / `cross_repo`) — `granularity`, `plan`, and `landing_report` carry the analysis result exactly as before (`plan` and `landing_report` carry `-` for the observation granularity). The drain fields carry `0` and `drained[]` is empty.
- **Inbox scan** (`inbox_scan`) — the singular fields `granularity`, `plan`, and `landing_report` carry `-`, and the per-message outcomes ride `drained[]`. `messages_scanned` counts every enumerated message, `messages_archived` counts those consumed and retired, `messages_invalid` counts those reported invalid and deliberately left un-archived, and `messages_archive_failed` counts those whose disposition was persisted but whose archival was refused (item 4a). `landings_incomplete` counts the `kind: landing` messages the drain-completeness check (Step 4) reported `complete: false` — the landings that carried only narrative or a partial facts block, each recorded as an Open Defect. A zero-drain with `landings_incomplete: 0` is what establishes that every REQUIRED fact drained — not that nothing whatsoever is outstanding, since the optional keys lie outside the check; a non-zero value names exactly the plans whose manual paste may still surface a required fact the inbox did not get. `messages_archived + messages_invalid + messages_archive_failed == messages_scanned` at a clean exit; a gap means a message was neither consumed nor recorded as a defect, and the epic ledger carries the discrepancy as an open defect. **The two lifecycle dispositions (item 2) are counted inside `messages_archived`**, because both archive — so the closure equation is unchanged by them and needs no fourth term. Each `drained[]` row's `disposition` is one of: the recorded Step 5b disposition (`promoted` / `folded` / `staged` / `discarded`); `reconciled` for a landing; `observed` for a finding absorbed by Step 5; `retired_by_successor` for a `lifecycle: superseded` row recorded as retired without running its `kind` branch (item 2); `stream_end_noted` for a `lifecycle: stream-end` control record noted as the sender's closure without being absorbed as an observation (item 2); `invalid` for an unprocessed message; or `archive_failed` for a processed message whose archival was refused.

This is a clean break, not a shim: there is one Output block, and a consumer reads `mode` to know which half to trust.

`emitted[]`/`shortfall[]` mirror the `orchestrate.md` `next` verb output shape (see there) for every mode, with one blocking reason per unemittable candidate.
