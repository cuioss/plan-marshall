envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:12:25Z

# affected_files is a plan-time projection, not an observed footprint

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 5 lessons. **Suggested fold target:** yours to decide — this surface may already
be held by a staged spec in your queue.

## The failure mode

`references.json`'s `affected_files` is consumed by several finalize steps as an authoritative
scope supplier. It is not one. It records **declared intent**, and it disagrees with the live
git footprint **in both directions** — so no "recorded is a conservative subset of live"
assumption holds and a step scoping off it does two wrong things at once: it misses files the
plan genuinely rewrote, and it burns coverage gating files the plan never touched.

## Two independent both-directions measurements

| Lesson | Plan | Recorded | Live | Live-only | Recorded-only |
|--------|------|---------:|-----:|----------:|--------------:|
| `2026-08-23-19-001` | `orchestrator-inbox-and-landing-residue` | 13 | 15 | 5 | 3 |
| `2026-08-26-06-002` | `config-seeding-effort-presets-steward-upgrade` | 52 | 54 | 6 | 4 |

⭐ **These are independent** — different plans, different counts, three days apart. Together
they refute containment in *both* directions rather than asserting it once. ⚠ Note how
nearly the two errors cancel in each row (13-vs-15, 52-vs-54): **a check that compares set
sizes passes both wrongly.**

## The consequence that was caught

`2026-08-26-06-002` records a scope gate missing its own trigger.
`project:finalize-step-plugin-doctor` decides scoped-vs-whole-tree on an F1 trigger: does the
changed set touch `plugin-doctor/**`? Read against `affected_files`, **F1 does not fire** —
`rule-catalog.md` is one of the six live-only files. The step would have run scoped over 12
skill dirs and reported a clean gate **past a rule change**. Read against the live git
footprint, F1 fires and whole-tree is selected, which is what actually ran.

⛔ **Every `affected_files`-derived finalize step inherits this.** The scope gate is the
instance caught because its trigger happened to sit in the live-only set; the class is any
step deriving breadth from the record rather than from git.

## The other three members

| Lesson | Instance |
|--------|----------|
| `2026-08-25-05-001` | `affected_files` is **never REWRITTEN after outline**, so scope widened at 4-plan and at finalize entry never lands. The read is faithful, and **re-reading a stale value cannot detect staleness** — which is why every consumer-side "did the read work?" check passes. (Title-only stub — see caveat.) |
| `2026-08-25-09-012` | The escalation rule ("whole-tree when the scope read is indeterminate") has **no mechanical indeterminacy test**. `finalize-step-plugin-doctor` fired twice against the *same* `affected_files` value and the *same* footprint, and reached **opposite** coverage decisions — one leaf cross-checked against git, the other did not. |
| `2026-08-25-09-004` | `branch-cleanup`'s merge-queue path leaves `realized_footprint` unwritten and records `merge_commit_sha` only on the synchronous path, so **all four resolver tiers miss** and every post-merge footprint read is unresolvable. Recorded twice — the second occurrence (PR #1349) adds that `branch-cleanup` reports `outcome: done` while writing neither key. |

## The convergent directive

- **Derive finalize-time scope from the live git footprint**, not from `references.json`.
  `manage-references compute-footprint --worktree-path …` already returns the git-derived set.
- A step that must use the recorded set MUST **reconcile** and report the divergence, never
  assume containment. ⛔ A one-way "recorded ⊆ live" check **would have passed** on
  `26-06-002` and still missed the trigger.
- Make the divergence observable: publish `live_only` / `recorded_only` counts so a silent
  scope narrowing becomes a legible one.
- **Matched pair required** — a file changed on the branch but absent from the record must be
  detected, AND a file present in the record but unchanged must be detected. The two
  directions fail differently.

## Claim labels

- **OBSERVED** — both measurement tables, the F1-trigger miss, the twice-fired plugin-doctor
  divergence, and the unwritten `realized_footprint`; each quoted from a lesson recording a
  live run at a named HEAD.
- **HYPOTHESIS** — `2026-08-25-05-001`'s "never rewritten after outline" mechanism. It is a
  **title-only stub**: `add` allocated it, `set-body` never ran, and no body exists. The
  claim rests on its title alone. Confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py` §
  the `affected_files` write path, checking whether any post-outline caller rewrites it.
  Verify-at-outline.
- **HYPOTHESIS** — that `compute-footprint` is the correct substitute at every consuming
  site. Confirm/refute per site; `26-06-002` establishes it for the plugin-doctor scope gate
  only.

⛔ Counts and site references are the filing plans' own and were NOT re-derived here.
