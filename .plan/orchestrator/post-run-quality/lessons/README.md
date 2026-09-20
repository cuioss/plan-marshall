# Lessons archived into this epic

25 lessons whose SUBJECT is post-run quality analysis, moved here from `.plan/local/lessons-learned/` on
2026-09-17. Each file is the lesson's text **verbatim**; nothing was condensed, and every one names the
plan that filed it.

## ⛔ Two sessions swept concurrently — read this before trusting the Corpus column

Two orchestrator sessions ran this sweep at the same time on 2026-09-17, each unaware of the other until a
`duplicate_plan_id` refusal exposed it. **No lesson was lost** — both sessions archived before removing —
but three consequences are recorded here rather than smoothed over:

1. **This directory is the consolidated archive.** The other session's `archive/lessons/` (8 files) is
   superseded and carries a redirect; all 8 are present here.
2. **The other session's ten removals landed first**, so three of this session's `remove` calls returned
   `not_found`. ⛔ That `not_found` was GENUINE (already retired), **not** the documented
   destroy-while-returning-`not_found` failure — verified by inspecting each tombstone's `removed_at` and
   `reason`. A retry would have been the dangerous move and none was issued.
3. ⚠ **The tombstone verdicts are inconsistent across the two sessions, and the difference is material.**
   The other session retired its ten as `completely_covered`, which asserts the lesson's rule now lives in
   a named clause. For these lessons that is not yet true — the rule lives in a STAGED plan spec, and no
   spec is a codified clause. This session used `superseded` for the same class of retirement, which
   asserts only that ownership moved. **The `completely_covered` tombstones overstate their evidence**;
   they are left as written because a tombstone is an audit record and there is no sanctioned edit path,
   but a reader checking whether a retirement was sound should read this note first.

⛔ **This directory is the durable carrier, not a copy.** Where a lesson was retired from the corpus, its
text exists here and its tombstone at `.plan/local/lessons-learned/.tombstones/{id}.json` records the
verdict. Where a lesson could NOT be retired (see the headerless set below), the corpus file is still in
place and this is a second copy — stated so a reader never mistakes one case for the other.

## Why they were moved

A lesson describing a defect in post-run quality machinery is a work item for this epic, and the corpus
had accumulated 23 of them — the oldest filed 2026-08-27 — with **not one having reached a plan**. That
figure is the floor for `PLAN-PRQ-05` D4's contract-reach metric, measured on this epic's own subject.

## Disposition

| Lesson | Subject | Owner | Corpus |
|---|---|---|---|
| `2026-09-04-08-003` | extract-chat-signal truncates the reduced transcript across its hop | PRQ-02 D3 | retired (superseded) |
| `2026-09-04-08-004` | every footprint-resolving tier is worktree-bound; 3 aspects inconclusive post-merge | PRQ-02 D1 | retired (superseded) |
| `2026-09-04-08-008` | build rows never reach the change-ledger, so `build_time` publishes a clean zero | PRQ-02 D2 + PRQ-08 D0 | retired (superseded) |
| `2026-09-13-20-004` | the could-not-look discriminator belongs in the payload, not a docstring | PRQ-02 D0 | retired (superseded) |
| `2026-09-13-06-001` | `step_params` persists a lane override that resolution refused | PRQ-06 D2a | ⛔ kept — headerless, unretirable |
| `2026-09-03-23-006` | lesson-creation Gate 2 cannot read a worktree-resident plan's scope | PRQ-05 | retired (superseded) |
| `2026-08-31-09-001` | a producerless `SECTION_SPEC` row renders clean as `sections_omitted` | PRQ-09 D3 | retired (superseded) |
| `2026-09-03-23-004` | recall denominator counts delete-intent and foreign-checkout paths | PRQ-09 D4 | retired (superseded) |
| `2026-09-05-07-006` | plan-level recall averages away a deliverable at 67% | PRQ-09 D4 | retired (superseded) |
| `2026-09-08-22-007` | a precondition keyed on the marker whose absence is the defect | PRQ-09 D1 | ⛔ kept — headerless, unretirable |
| `2026-09-15-08-005` | `ARTIFACT_EMISSION` inert: tasks never persist `changed_files` | PRQ-09 D2 | retired (superseded) |
| `2026-08-27-16-003` | verify a defect claim handed to the retrospective before filing it | PRQ-09 D5 | ✅ **RESTORED to the corpus as `2026-09-18-06-001`** — retired by the other session as `completely_covered`; this session judged it a STANDING RULE, not a work item, and the operator agreed. New id because the corpus never reuses a retired one; the restoration carries its own provenance section naming the original id and tombstone |
| `2026-09-04-08-001` | manifest order inverted: retrospective (995) ran before lessons-capture (991) | ⚠ unowned — other session's classification | retired by the other session |
| `2026-09-15-08-007` | (other session's classification; outside this session's Class A set) | ⚠ unowned | retired by the other session |
| `2026-09-03-23-001` | `refire-report` reads only `execution_log` | PRQ-08 D2 | retired (superseded) ✅ |
| `2026-09-08-22-006` | `reconcile-ledgers` has no consuming aspect; 24 findings never reach the report | PRQ-08 D1 | ⛔ kept — headerless, unretirable |
| `2026-08-27-16-002` | error/retryable token classes misattribute terminal dispatch spend | PRQ-08 D3 | retired (superseded) |
| `2026-09-04-08-010` | the cost of an error-terminated dispatch is visible only post-hoc | PRQ-08 D3 | retired (redundant of `16-002`) |
| `2026-09-05-07-002` | findings-producing firings stamped `error`, inflating waste by 2.32M tokens | PRQ-08 D3 | retired (redundant of `16-002`) |
| `2026-09-04-08-009` | finalize re-fire spend unbounded; anchors compared only post-merge | PRQ-08 D4 | retired (superseded) |
| `2026-09-05-07-005` | `record-dispatch-boundary` never gets its four context-load flags | ⚠ `truthful-signals` PLAN-TRUTH-160 | **kept — another epic owns it** |
| `2026-09-05-07-001` | `false_positives_count` conflates administrative rejections with wrong claims | ⚠ forwarded to `review-apparatus` | **kept — another epic owns it** |
| `2026-08-27-18-001` | a refuted finding filed `accepted` makes the false-positive rate read zero | ⚠ forwarded to `review-apparatus` | **kept — another epic owns it** |
| `2026-09-03-08-001` | claimless bot bodies counted actionable, so `pct_resolved_as_fixed` reads 0.0% | ⚠ forwarded to `review-apparatus` | **kept — another epic owns it** |
| `2026-09-15-08-039` | "3 reviewers compared" rests on 1 measured participant | ⚠ forwarded to `review-apparatus` | **kept — another epic owns it** |

## The four kept-because-unretirable files

`2026-09-08-22-004`, `-005`, `-006`, `-007` and `2026-09-13-06-001`/`-002` carry **no metadata header**, so
`get --lesson-id` returns `not_found` while `list` shows them. ⛔ That is the recorded
destroy-while-returning-`not_found` path, so `remove` was never called on any of them. Three of that set
are archived here (`22-006`, `22-007`, `13-06-001`); the corpus copies remain in place and are `PLAN-PRQ-05`'s
subject.

## The four kept-because-another-epic-owns-them

Reviewer-quality measurement belongs to `review-apparatus` under the standing three-way routing rule (the
PR test wins outright), and the context-load flags belong to `truthful-signals` PLAN-TRUTH-160. Their text
is archived here as the evidence that travelled with the forward; the corpus entries stay live because this
epic is not their owner and must not retire another epic's evidence.

✅ **Forwarded 2026-09-18** as `review-apparatus` inbox message `post-run-quality-001.md`: the four
reviewer-quality lessons (`2026-09-05-07-001`, `2026-08-27-18-001`, `2026-09-03-08-001`,
`2026-09-15-08-039`) with their shared shape named — a reviewer-quality ratio published over a denominator
whose members were never established. Forwarded, not copied: this epic stages nothing for them.

## Final state of the sweep (2026-09-18)

- **25 lessons archived here**, every one verbatim.
- **17 retired from the live corpus**: 10 by the peer session (`completely_covered`), 7 by this session
  (5 `superseded`, 2 `redundant`). Corpus **194 → 178**: 194 − 17 retired = 177, **+1 restored** = 178,
  verified by `ls` and by `manage-lessons list` (both 178).
- **1 restored**: `2026-08-27-16-003` → `2026-09-18-06-001`, a standing rule rather than a work item.
- **4 left live and forwarded** to `review-apparatus`; **1 left live** because `truthful-signals`
  PLAN-TRUTH-160 owns it (`2026-09-05-07-005`).
- **6 invalid (headerless) entries REMOVED 2026-09-18** by operator instruction — `2026-09-08-22-004`,
  `-22-005`, `-22-006`, `-22-007`, `2026-09-13-06-001`, `-06-002`. Corpus **178 → 172**, and a re-derived
  header scan returns **0** headerless files, so the class is empty. ⛔ No sanctioned path existed
  (`manage-lessons` has no repair verb and both `update` and `remove` resolve by the id that fails), so
  this was a direct file delete and **no tombstone was written**. All six are preserved verbatim at
  `lessons/invalid-headerless/`, which is their only surviving copy and their only audit trail besides the
  decision log. See that directory's README for what each said and where four of them were already carried.
