# Aggregate Analysis: Group Lessons That Would Land in One Plan

Shared procedure used by two callers:

- `plan-marshall:manage-lessons:manage-lessons` `aggregate` verb (read-only classifier — returns groups as TOON).
- `plan-marshall:plan-marshall` Action: lessons-aggregate (orchestrator that composes merged bodies, runs `set-body` + `set-title` + `supersede`, and optionally prunes).

Sibling document: [`dedup-analysis.md`](dedup-analysis.md). Dedup classifies a single candidate against the existing corpus (new / merge_into / already_closed). Aggregate classifies the entire active corpus into multi-lesson groups whose work would land in a single plan.

## Inputs

- The full active lessons corpus, loaded with bodies via:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
  ```

- A `top_n` integer (default `5`) that controls only the headline command list returned to the caller. Group composition itself is unaffected by `top_n`.

## Per-lesson signals

Extracted once per active lesson before grouping:

- **cross_refs**: the set of lesson ids that appear verbatim in the lesson body, matched by the regex `\b\d{4}-\d{2}-\d{2}-\d{2}-\d{3}\b`. The lesson's own id is excluded from its cross_refs set.
- **component**: the `component` value from frontmatter (e.g., `plan-marshall:phase-5-execute`).
- **standards_dir**: the directory holding the component's `standards/`. Derived from `component` by resolving the bundles root through the cache-aware bundle resolver in `script-shared` (`marketplace_paths.find_marketplace_path`) and appending `{bundle}/skills/{skill}/standards/`. The resolver tracks the actually-resolved bundles location (explicit `PM_MARKETPLACE_ROOT` anchor, plugin-cache install, or cwd walk-up); when no bundles tree resolves it falls back to the relative `marketplace/bundles` segment so the value still serves as a deterministic per-component grouping key.
- **workflow_boundary**: a coarse grouping label inferred from the component prefix. Use the `{bundle}:{skill}` pair stripped of any task-number suffix; lessons whose components share this label are workflow-adjacent even when their components differ in detail.

## Signal priority (strongest wins)

When two signals would place a lesson in different groups, the strongest signal wins. Priority order (highest first):

1. **cross-ref** — lesson A's body cites lesson B's id (or vice versa).
2. **shared-component** — both lessons declare the exact same `component` value.
3. **shared-standards-dir** — both lessons map to the same `standards_dir`.
4. **shared-workflow-boundary** — both lessons share the same `workflow_boundary` label.

A lesson belongs to exactly one group. When multiple signals fire for a candidate pair, place the lesson in the group identified by the strongest matching signal and ignore the weaker ones for that pair. Singletons (lessons matching no other lesson at any level) form their own one-member groups but MUST NOT be returned in the result — only multi-member groups are emitted.

## Tie-break: deterministic group ordering

Group keys are built from the strongest signal that produced the group:

- cross-ref groups: key = the alphabetically-smallest member id.
- shared-component groups: key = the shared `component` value.
- shared-standards-dir groups: key = the shared `standards_dir` path.
- shared-workflow-boundary groups: key = the shared `workflow_boundary` label.

Groups are returned sorted by key ascending (alphabetical). Within a group, members are sorted by lesson id ascending. This makes repeated runs over the same corpus produce identical TOON output.

## Primary-pick rule

For each multi-member group, pick exactly one lesson as the **primary** (the one whose body is preserved and whose id survives). The other group members are **absorbed** (their bodies become H2 sub-sections under the primary, and they are superseded by the primary).

Pick order:

1. Highest **cross-ref-fan-in** — the lesson cited by the largest number of other group members in their bodies. The primary is preferentially the one others already point at.
2. Tie-break: highest **recurrence-count** — the count of `## Recurrence — ...` H2 sections in the lesson body (these are appended by the dedup `merge_into` flow).
3. Tie-break: lowest **lesson-id** ascending (lexicographic on the `YYYY-MM-DD-HH-NNN` pattern). Earlier lessons win.

Absorbed members keep their relative order from the group's deterministic-sort (id ascending) — this is the order in which their bodies appear under the primary.

## Merged-body composition template

For each group, the would-be merged body is composed verbatim from existing content:

```text
{primary's existing body, exactly as on disk, with no edits}

## Sub-task: {first absorbed title} ({first absorbed id})

{first absorbed body, exactly as on disk, with no edits}

## Sub-task: {second absorbed title} ({second absorbed id})

{second absorbed body, exactly as on disk, with no edits}

...
```

Rules:

- The primary's body is placed first, unedited. Frontmatter is NOT included — the orchestrator writes only the body section to `.plan/temp/aggregate-merged-bodies/{primary_id}.md`.
- Each absorbed lesson appears under an H2 heading `## Sub-task: {title} ({lesson_id})`. The parenthetical lesson id matches the absorbed lesson exactly.
- Absorbed bodies are inserted verbatim, including any pre-existing headings inside them (those headings keep their original level; H1 lines inside absorbed bodies remain H1 but are nested under the new H2 heading semantically).
- A single blank line separates the primary's body from the first H2, and one blank line separates each H2 sub-section from the next.
- The order of H2 sub-sections matches the deterministic absorbed-member order (id ascending) defined above.

## Consumer contract — TOON shape returned by the `aggregate` verb

The `aggregate` verb is read-only. It returns the proposed grouping; it MUST NOT call `set-body`, `set-title`, `supersede`, or `cleanup-superseded`. Callers (the orchestrator action) consume this TOON and decide whether to enact the changes.

```toon
status: success
top_n: N
groups[K]{primary_id,primary_title,absorb_count,tier,enacted,absorbed[M]{lesson_id,title,reason},merged_body_preview}:
  YYYY-MM-DD-HH-NNN,"Primary title",2,cross-ref,true,absorbed-rows-flattened-per-toon-conventions,"first ~400 chars of merged body ..."
  ...
top_n_commands[N]:
  - "/plan-marshall:plan-marshall lesson=YYYY-MM-DD-HH-NNN"
  - ...
```

Field semantics:

- **status** — `success` on a clean classifier run. Errors during corpus load surface as `status: error` with a `message` field; no `groups` are emitted in the error case.
- **top_n** — echoed back from the input flag so the caller can confirm the requested truncation.
- **groups[]** — every multi-member group from the classifier, in deterministic key-ascending order. Singletons are omitted. The number of groups is independent of `top_n`.
- **groups[].primary_id** — the picked primary's lesson id.
- **groups[].primary_title** — the picked primary's H1 title (the first `# ` line in its body), with the leading `# ` stripped.
- **groups[].absorb_count** — the number of absorbed members (excluding the primary). Always `>= 1` because singletons are dropped.
- **groups[].tier** — the producing signal that grouped the lesson: `cross-ref` | `shared-component` | `shared-standards-dir` | `shared-workflow-boundary`. Matches the strongest matching signal per the signal-priority order above.
- **groups[].enacted** — `true` only for `cross-ref` tier groups; `false` for every weaker tier. `enacted: false` signals that the group is a co-location suggestion, not an auto-applied merge — the orchestrator MUST treat weaker-tier groups as opt-in.
- **groups[].absorbed[]** — one row per absorbed member in deterministic order (id ascending). Each row carries:
  - `lesson_id` — the absorbed lesson's id.
  - `title` — the absorbed lesson's H1 title (leading `# ` stripped).
  - `reason` — short human-readable phrase naming the strongest signal that placed this lesson in the group (e.g., `cross-ref to {primary_id}`, `shared component {component}`, `shared standards-dir {dir}`, `shared workflow-boundary {label}`).
- **groups[].merged_body_preview** — the first 400 characters of the would-be merged body composed per the template above, truncated on a code-point boundary. The preview is intended for `AskUserQuestion` display only; the orchestrator MUST recompose the full body when calling `set-body`.
- **top_n_commands[]** — at most `top_n` strings of shape `/plan-marshall:plan-marshall lesson={primary_id}`, taken from the highest-priority groups (cross-ref groups first, then shared-component, then shared-standards-dir, then shared-workflow-boundary; within a tier, by descending `absorb_count` then by group key ascending). The list is purely a UX shortcut; orchestrators MAY ignore it.

## Caller contract

- **Read-only caller** (`manage-lessons aggregate`) returns the TOON shape above and exits without side effects.
- **Orchestrator caller** (`plan-marshall` Action: lessons-aggregate) consumes the TOON and MUST present the groups for per-group selection rather than a single accept-all batch confirmation. `enacted: false` groups MUST default to opt-in (not pre-selected). Only user-selected groups are enacted — for each selected group the orchestrator drives `set-body` + `set-title` + `supersede`, optionally followed by `cleanup-superseded`. Tombstones at `.tombstones/{id}.json` are preserved regardless of the prune choice.

The orchestrator MUST recompose the merged body from disk before calling `set-body` — the `merged_body_preview` field is a UX truncation, not a reproducible payload.
