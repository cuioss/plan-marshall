# Lessons archived into this epic — the 2026-09-18 corpus sweep

**124 lessons**, archived verbatim from `.plan/local/lessons-learned/` on 2026-09-18. Every file here is
the lesson's own text; nothing was condensed.

## What the sweep did

The global corpus held 131 active lessons. Classified by SUBJECT against this epic's theme — *a signal
about behaviour or a contract that reads as CONFIDENT while hiding a caveat* — **124 were ours**. Seven
were not, and were left live for the epics that own them (see the last section).

Of the 124: **42 duplicate cluster members**, **68 already owned by a staged spec**, and **14 owned by
nothing**, which is what this sweep turned into work.

| Outcome | Count | Verdict written | Where the text lives now |
|---|---|---|---|
| Duplicate of a fuller sibling | 42 | `redundant`, naming the keeper | here + tombstone |
| Owned by an already-staged spec | 68 | `superseded`, naming the spec | here + tombstone |
| Owned by nothing → **3 new specs** | 14 | `superseded`, naming the new spec | here + tombstone |
| Belongs to another epic | 7 | *not retired* | still live in the corpus |

**Corpus 131 → 7.** Every retirement wrote a tombstone at
`.plan/local/lessons-learned/.tombstones/{id}.json` carrying its verdict, its reason and the archived
path above.

⛔ **Why no retirement says `completely_covered`.** That verdict asserts the lesson's rule now lives in a
named clause. For all 124 it lives in a STAGED spec, and a spec is not a clause — the fix has not shipped.
`superseded` says what is true: ownership moved. When a spec lands, its own
`finalize-step-lessons-housekeeping` closes the loop against real code.

## The three specs this sweep created

The 14 lessons nothing owned collapsed into three mechanisms rather than fourteen tickets:

- **`PLAN-TRUTH-169`** — a timeout verdict describes the WAIT, not the work, and the time budgets it is
  measured against are undeclared. *(5 lessons; corroborated first-party in a consuming repo the same week
  by `api-sheriff-deployment-configurability-020`.)*
- **`PLAN-TRUTH-170`** — the finalize seam records less than it does and enforces less than it documents:
  a re-fire discarded by a missing `--force`, `[OUTCOME]`/`[DISPATCH]` lost on re-dispatch, a documented
  `display_detail` ceiling nothing enforces, and a commit staging rule that is prose over a whole-tree
  porcelain read. *(4 lessons.)*
- **`PLAN-TRUTH-171`** — state writers that fabricate, collide or fail silently: a reconstructed commit
  SHA accepted into an append-only ledger, a non-plan-namespaced temp path two dispatches race for,
  merge-tree prose parsed into synthetic file paths, `.get(k, {})` against an explicit `null`, and an
  exit 1 with no stderr. *(5 lessons.)*

## Duplicate clusters — the keeper and why it won

16 clusters, each retired down to the fullest member. The largest:

- **Argparse / invocation vocabulary** → keeper `2026-09-04-08-014` (a flag spelling transferred from a
  sibling verb; two-plan recurrence). 6 members retired.
- **`--plan-id` placement trichotomy** → keeper `2026-09-15-08-060` (router vs subcommand vs undeclared).
  4 members.
- **Duplicate-key population loss in the qgate mechanical checks** → keeper `2026-09-15-08-045` (the DAG
  check lost identities while its verdict stayed authoritative). 5 members.
- **A hardcoded mirror of a set defined elsewhere** → keeper `2026-09-15-06-003`. 5 members.
- **`manage-architecture` contract drift across doc sites** → keeper `2026-09-15-08-036` (*"every writer"*
  listed two of three). 5 members.

⚠ A keeper was itself retired when a staged spec already owned its defect — a cluster's keeper won
against its siblings, not against the ledger.

## ⛔ FINAL STATE: the global lessons corpus is EMPTY (0 active lessons)

The seven below were **transformed into inbox items for their owning epics and then removed**
(operator-directed, 2026-09-18), which took the corpus from 7 to **0**. `.tombstones/` is intact — **860
tombstones**, one per retirement ever made, and the directory was never touched.

| Forwarded to | Message | Lessons |
|---|---|---|
| `post-run-quality` | `truthful-signals-001.md` | `2026-09-15-08-003`, `2026-09-18-06-001` |
| `code-intelligence-substrate` | `truthful-signals-060.md` | `2026-09-15-08-041`, `-08-052`, `-08-053` |
| `next-level` | `truthful-signals-001.md` | `2026-09-03-16-004`, `2026-09-05-08-001` |

Each message carries the lesson body IN FULL, names the archived path, and states that the corpus copy is
gone and will be restored on request. Their text is at `lessons/forwarded-to-other-epics/{id}.md`.

⚠ **Two consequences a later reader should not have to rediscover.**

1. **`manage-lessons consult` / `auto-suggest` now return nothing**, because there is nothing to return.
   Every rule the corpus used to steer sessions with now lives in a staged spec, an epic ledger, or another
   epic's inbox — none of which a session reads at recall time. Whether that is acceptable is a standing
   question for `post-run-quality` PLAN-PRQ-05, whose whole subject is the corpus's value.
2. **`2026-09-18-06-001` was restored to the corpus one day before it was removed from it.** It was
   re-filed deliberately on 2026-09-17 as a standing agent-facing rule after a peer session retired it;
   the 2026-09-18 directive then swept it out with the rest. The contradiction is recorded rather than
   resolved: the forwarding message to `post-run-quality` states it plainly and leaves the call to that
   epic.

## The seven forwarded — original ownership notes

| Lesson | Owner |
|---|---|
| `2026-09-15-08-003` · split an oversized plan before executing it | `post-run-quality` |
| `2026-09-18-06-001` · verify a defect claim handed to the retrospective | `post-run-quality` |
| `2026-09-15-08-041` · a writer bypassed the index write-through | `code-intelligence-substrate` |
| `2026-09-15-08-052` · the JSON writer truncated before the dump completed | `code-intelligence-substrate` |
| `2026-09-15-08-053` · index sync not in a `finally`, stranding documents | `code-intelligence-substrate` |
| `2026-09-03-16-004` · a security remedy right about the symptom, wrong about direction | out of theme |
| `2026-09-05-08-001` · narrowing a catch drops the cleanup that followed | out of theme |

⛔ This epic did not retire any of them. Retiring another epic's evidence, or a general methodology rule
with no truthful-signals surface, is not this sweep's to do.

## What a reader should take from the numbers

⭐ **124 lessons describing this epic's own subject had accumulated in a corpus, and 14 of them were owned
by nothing at all** — the oldest filed 2026-08-27. The 68 that *were* covered had never been reconciled
against the specs covering them, so the corpus and the ledger had been telling the same story twice
without either knowing. That is the contract-reach problem this project already tracks, measured here on
the epic whose theme is exactly that.
