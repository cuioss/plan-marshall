envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:19Z

component=plan-marshall:marshall-orchestrator
category=bug
created=2026-07-29

# `inbox validate` reports an archived message as `file_not_found`, and the resume anchor's queue count contradicts the derived reader

## How this was found — including the wrong turn, because it is the point

Running the retrospective from the main checkout after `branch-cleanup`, three reads looked like data loss:

```
$ orchestrator inbox list --slug truthful-signals
status: success
count: 0

$ orchestrator inbox validate --slug truthful-signals --message manage-lessons-mixes-local-time-and-utc-001.md
status: error
error: file_not_found

$ orchestrator inbox validate --slug truthful-signals --message code-intelligence-substrate-004.md
status: error
error: file_not_found
```

`lessons-capture` had reported `5 inbox message(s) -> epic truthful-signals`, and the epic's own resume anchor asserts **"INBOX: 18 queued (all candidate-lessons, 0 invalid)"** and names `code-intelligence-substrate-004` as **"still queued in the inbox UNARCHIVED and undispositioned"**. The obvious hypothesis — messages written into a worktree-scoped store and destroyed with the worktree — fit every symptom.

**It was wrong.** Writing this plan's next message returned:

```
message: manage-lessons-mixes-local-time-and-utc-006.md
```

The allocator issued **006**, so it can see 001–005. They exist, in `inbox/archive/`. Nothing was lost, the store path is correct, and `inbox list`'s `count: 0` was truthful.

## The two real defects

**(a) `inbox validate` cannot distinguish archived from never-written.** Both return `error: file_not_found`. An archived message is a *consumed* message with a known location; a never-written one is missing data. Collapsing them into one error is what made a healthy epic look like a data-loss incident, and it cost a full investigation to disprove. `validate` should look in `inbox/archive/` on miss and return `status: archived` with the archive path.

**(b) The resume anchor's inbox count is hand-written prose that has drifted from derived state.** The anchor claims 18 queued and names a specific message as unarchived; the derived reader says 0 queued and that message is archived. The anchor is the surface an operator resumes from, and on this dimension it is stale in the confident direction — it asserts pending work that has already been drained.

Note the direction of the epic's own standing rule ("re-derive counts from status.json, never from the rendered block") — this is the same rule one level up: the anchor's *own* narrative counts must be re-derived from `inbox list`, not carried forward as prose.

## Solution

1. `inbox validate` — on a miss in `inbox/`, check `inbox/archive/` and return `status: archived` with `archive_path`, never `file_not_found`.
2. `inbox list` — report the resolved inbox directory, and distinguish `inbox_missing` / `epic_not_found` from a genuinely empty queue, so a `count: 0` states which of the three it means.
3. `resume-summary` — derive the queued/archived counts from the inbox at read time and render them separately from the operator's narrative anchor, so a stale sentence cannot outrank a live count.

## Impact

Any consumer that treats `file_not_found` as "the message was never delivered" will conclude data loss from a correctly-consumed message. This retrospective did exactly that, and only the sequence allocator's behaviour disproved it — an accidental oracle, not a designed one.
