# Handle-Open Verb Workflow

Workflow doc for the `handle-open` verb: walk every open defect, watch and question the epic carries, decide the items the orchestrator is confident about, and put the rest to the operator one item per turn in plain text. The binding contract — the closed subject set, the confidence cap, the threshold semantics, the bounded decision acts and their prohibitions, the plain-text presentation and the reporting rule — is owned by [`persona-plan-orchestrator/standards/orchestration-model.md` § Handle-Open Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#handle-open-contract); this doc implements it and xrefs those statements rather than restating them. When this doc and the standard disagree, the standard wins.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |
| `threshold` | No | Integer `0` to `100`, overriding `orchestrator.decision_confidence_threshold` for THIS run. |

## Dispatch

Per the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule), this verb names which sub-steps are dispatchable and which are not; it does not restate the three tests, the safety constraints, or the fall-back clause.

- **Dispatchable** — the per-item analysis of Step 4, and it is ONE envelope that iterates internally over the whole inventory, never one envelope per item. The vehicle is `execution-context-{level}` under the S1 read-only instruction, and the dispatch level is config-resolved via `manage-config effort resolve-target --role orchestrator.analyze --plan-id none --caller plan-marshall:persona-plan-orchestrator --workflow plan-marshall:plan-orchestrator/workflow/handle-open.md` (the four facts are not optional decoration: `--workflow` is what makes the resolve seam emit the `[DISPATCH]` line and its paired decision-log record). The leaf loads this document. Return shape: `proposals[N]{number,kind,source,recommendation,alternatives,evidence,unchecked}` — one row per inventoried item, where `alternatives` is the numbered proposal list, `evidence` is the `file:line` material the leaf actually read, and `unchecked` names every claim the leaf did NOT verify. The orchestrator consumes the return as data: the confidence, the decision, every ledger write and every operator turn stay inline.
- **Inline-only** — Steps 1-3, Step 5's confidence assignment, Step 6's decisions and every write they make, Step 7's operator turns, and Step 8's log, anchor write, view regeneration and ledger commit at `{store_checkout}`.

## Workflow

### Step 1: Push the terminal title and resolve the epic tree

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

**Resolve the epic tree.** Ask the store seam where this epic lives and which checkout holds the store, and keep `epic_dir` and `store_checkout` from the payload for every later step — every direct file-tool call on a ledger document addresses `{epic_dir}/…` and every ledger `git add` / `git commit` runs as `git -C {store_checkout}` (see the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#direct-file-write-carve-out)):

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resolve-path \
  --slug {slug}
```

An epic whose tree does not resolve is an error, not an empty inventory: report it and stop.

### Step 2: Resolve the effective threshold

Take the per-run `threshold` argument when it was supplied, else read the knob:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config orchestrator get \
  --field decision_confidence_threshold
```

Carry the source of the resolved value — `argument`, `knob`, or `unset default` — into the report, so a reader sees where the number came from. Apply the contract's fail-closed reading: a threshold that cannot be read, or an argument that is not an integer `0` to `100`, resolves to `100` for the run and the report says so. This doc states no threshold value of its own and no default for the knob — the seeded default lives in `DEFAULT_ORCHESTRATOR` and is not restated here.

### Step 3: Inventory the four sources and number the items

Read the ledger documents directly — the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#carve-outs) permits the reads — and enumerate the closed subject set the contract defines: the `## Open Defects` entries, the `## Watches` entries, the open operator questions, and the unowned residue carried by those entries. Number every item in one run sequence and record, per item, its kind, its source and the pointer the rest of the run re-finds it by.

Publish each source's population before analysing anything. A source that holds nothing reports as zero with its population; a source that could not be read is NAMED and is never counted as zero — the two are different lines, and a report that collapses them is the failure the contract's Reporting rule exists for.

### Step 4: Analyse every item

Dispatch the single analysis envelope named under [Dispatch](#dispatch), or, for a small inventory, analyse inline. Per item, the analysis returns a recommendation, the numbered alternatives, the evidence it read, and the claims it did NOT check.

The envelope iterates over the whole inventory. A second envelope for the same run is not this verb's shape; when the return is empty, incomplete, or missing an item, analyse that item inline rather than re-dispatching.

### Step 5: Verify inline and assign the confidence

Re-read every load-bearing point of the analysis at `file:line` in this run, and run the existing check before saying a fix is possible. Then assign the item's confidence under the contract's confidence cap: an item resting on a claim the leaf reported, on the ledger's own prose, or on an unsettled `HYPOTHESIS` is held at the threshold, so it cannot be decided without the operator. A leaf's number is never copied as the confidence.

### Step 6: Decide every item above the threshold

For each item whose confidence is strictly greater than the threshold, apply one of the contract's bounded decision acts and record it: log the decision through `manage-logging --store orchestrator`, write the `## Decisions` entry, and mark the item in place with a pointer to that record. An item whose decision changes another item's analysis makes that item re-analysed before it is decided.

The eight prohibitions hold here and need no restatement to bind, but this step names them so the checklist is complete: this verb NEVER **stages a plan**, NEVER **emits a command**, NEVER **transitions a queue row**, NEVER **edits the spec of a running row**, NEVER **relocates settled narrative**, NEVER **lands**, NEVER **retires an item without a positive account** of what closed it, and NEVER **records a plan-consequence decision without naming the follow-up**. A decision whose consequence is a plan is recorded as decided with that follow-up named, and the staging stays an act the operator words.

### Step 7: Present the remaining items one per turn

Present every item at or below the threshold in plain text, one item per turn, most consequential first: the analysis, the numbered proposals, the one marked recommended with its confidence and the reason, and a final "leave it open" proposal. Wait for the operator's answer before the next item. This verb never surfaces an item through the question tool — the plain-text, one-per-turn shape is the contract's, and a tool card cannot carry the analysis.

Record each answer the same way Step 6 records a decision, before the next item: the chosen proposal, the `## Decisions` entry and the in-place marker. An answer of "stop" or "skip" leaves the item open and the report says so; it is a recorded outcome, never a silent skip.

### Step 8: Log, rewrite the anchor, regenerate the view, commit the ledger

Log the run's summary and write the resume anchor:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{handle-open: {D} decided, {P} presented, {U} unreadable sources}" --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

The anchor write REPLACES the whole value, so read the current anchor first, and after writing it check the written value with a word-diff against the committed one before the view is regenerated — a lost clause is visible in that diff and nowhere else. Then regenerate the view:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

Commit the ledger paths as `git -C {store_checkout}`. This is never a land: the verb opens no pull request and pushes no ledger branch.

### Step 9: Report

Emit the report described under [Output](#output). Every count it carries rides with the population it was computed over, every decided item names who decided it, its confidence and the threshold it was decided against, and every declined or unanswered item is named rather than dropped.

## Idempotence

**Each decision is keyed by the item and its in-place marker.** An item already marked decided, with its `## Decisions` entry on record, is not decided again and is not presented again: a second run over an unchanged ledger decides nothing new, presents nothing, and reports the same item as `already_decided`. An item whose marker is missing is treated as open — the marker, not the memory of a previous run, is the record.

## Output

```toon
status: success | error
display_detail: "handle-open {slug}: {D} decided, {P} presented, {U} unreadable"
slug: {slug}
threshold: {N}
threshold_source: argument | knob | unset default | fail_closed_default
sources[S]{source,state,population,items}:
  Open Defects,read,3,3
  Watches,read,2,2
  operator_questions,read,1,1
  landing_residue,unreadable,0,0
decided[D]{number,kind,source,confidence,threshold,decision,evidence}:
  2,defect,Open Defects,96,{threshold},"retired on positive account: {commit}","{file}:{line}"
presented[P]{number,kind,source,confidence,proposal_count,recommended,answer}:
  5,watch,Watches,72,3,"proposal 2","leave it open"
already_decided[A]{number,kind,source,marker}:
  1,question,operator_questions,"## Decisions entry of 2026-11-10"
unreadable[U]{source,reason}:
  landing_residue,"{epic_dir}/landings/ not readable"
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

`sources[]` is the population every later count is computed over: its `state` distinguishes a source that holds nothing (`read`, population `0`) from one that could not be read (`unreadable`), and each row carries its own `items` count. `decided[]` names, per item, the confidence it earned, the threshold it was decided against, the act performed and the evidence the verification read. `presented[]` names the operator's answer per item, including `leave it open` and `stop`/`skip`. `already_decided[]` and `unreadable[]` are **required fields, never omitted**: a run that decided nothing new and read every source emits them empty rather than dropping them, because an absent key is indistinguishable from a check that never ran.
