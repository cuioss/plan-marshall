envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:43:08Z

## Proposed lesson metadata

- `component`: `plan-marshall:manage-status`
- `category`: `improvement`
- `title`: `config_hash` drift fires at every phase boundary, so the drift warning has no discriminating power

## Observation

`summarize-invariants` reported 7 drift findings for this plan. **Four of the
seven are `config_hash`, and they are every boundary that exists:**

```
config_hash  1-init   -> 2-refine    93acf2ec06e7525e -> d99761ec7d492858
config_hash  2-refine -> 3-outline   d99761ec7d492858 -> 0906b13f3a40aa47
config_hash  3-outline-> 4-plan      0906b13f3a40aa47 -> e8e8b3ea69f878ad
config_hash  4-plan   -> 5-execute   e8e8b3ea69f878ad -> d4c6e3751c68f9f8
```

Two of those four boundaries (`1-init → 2-refine`, `2-refine → 3-outline`)
precede **any** file mutation by this plan — there was no worktree yet and no
source edit had been made. The plan never touched `marshal.json`. Whatever the
hash is covering, it is not "the operator's configuration changed".

The other three drift findings (`main_sha` once, `task_state_hash` twice) are all
expected and explicable: `main_sha` moved because a sibling PR landed and the
worktree self-absorbed the zero-overlap drift; `task_state_hash` moved because
`4-plan` created the tasks and `5-execute` completed them.

## Why this matters

An invariant that fires on **4 of 4** opportunities carries zero bits. A real
config change — the thing this invariant exists to catch, and exactly the class
of thing the epic cares about, since a mid-run config change can silently alter
compose-time step selection — is now indistinguishable from the baseline noise.
The retrospective dutifully renders four `warning` findings that a reader learns
to skip, which is worse than not emitting them: it trains the reader to discount
the invariant that would matter.

Note the shape relative to the epic theme: this is the *inverse* of a false
green. It is a signal that is always red, and therefore just as uninformative,
while looking like diligent monitoring.

## Owed work

1. Diagnose what `config_hash` actually hashes and why it moves on every phase
   transition (this retrospective observed the behaviour but did not diagnose the
   cause — that is the first task, not an assumption to skip).
2. Either narrow the hash to the operator-meaningful configuration surface so a
   drift means something, or demote unconditional drift out of the findings list.
3. Add the anti-vacuity check the corpus already demands elsewhere: a detector
   that fires on 100% of a population is not a detector. This is the fifth
   recorded instance of the vacuous-guard archetype in this project, and the first
   where the guard is vacuous by *always firing* rather than by never firing.
