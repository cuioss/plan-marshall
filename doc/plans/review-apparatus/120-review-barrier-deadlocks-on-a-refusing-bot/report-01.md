# Run report — 120-review-barrier-deadlocks-on-a-refusing-bot (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/review-barrier-deadlocks-6b5sao`    **PR:** _pending_    **Outcome:** _in progress_

⚠ **The slug does not describe the work.** The file name is kept because a cloud session is bound to
its path, but the real subject is: **the refusal taxonomy had no STRUCTURAL member, so a size-capped
reviewer was offered a non-option.** The plan's original deadlock premise is REFUTED and two of its
three original deliverables were already shipped; neither was re-implemented.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) — loaded first, before reading the plan |
| `plan-marshall:ref-code-quality` | bundle path (`marketplace/bundles/.../SKILL.md`) |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `pm-dev-python:python-core` | bundle path — Python production code on the surface |
| `pm-dev-python:pytest-testing` | bundle path — Python tests on the surface |

The `plan-marshall` plugin was not consulted via `Skill:` notation for the bundle skills; the bundle
path route was used directly, which is the route the contract says always works in a fresh clone. No
skill was unobtainable.

## D0 — the barrier's terminal-state population (GATE, mutates nothing)

**The gate did not halt.** The plan halts D0 if the taxonomy members cannot be enumerated from the
contract and the classifier. They can, from both, and the two agree — the pre-existing derivation
guard in `test_bot_participation_contract.py` already asserts that agreement in both directions.

**Derivation method** (published here as the plan's Verification section requires):

- **Source 1 — the classifier.** A `vars()` sweep of `review_completeness.py` for `STATE_`-prefixed
  string constants. Not a hand-list: a literal is complete only until the next member is added.
- **Source 2 — the contract.** The `## Failure taxonomy` table in `bot-participation-contract.md`,
  parsed by row. Normative, and the owner of the closure claim.

**Population size: 11 terminal states** — 10 closed non-participation members plus `participated`,
their complement. (It was 10 before this change; `refused_structural` is the eleventh.)

Each member classified on two axes. `passable` = can a plan exit by an action of its OWN, read
against the SHIPPED branches rather than what is imaginable. `await can succeed` = could waiting, in
principle, ever produce the review — this is the axis on which a remedy is a *non-option* rather than
merely a slow option.

| Member | Blocks? | Passable by plan action | Await can ever succeed | Remedy the shipped contract names |
|---|---|---|---|---|
| `participated` | no | — | — | none needed |
| `participated_but_empty` | no | — | — | none needed (accounted-for) |
| `in_progress` | yes | ✅ | ✅ | let the run finish |
| `not_triggered` | yes | ✅ | ❌ | generate the trigger event |
| `participated_stale` | yes | ✅ | ❌ | re-trigger a re-review |
| `absent` | yes | ✅ | ✅ | loop back / escalate the silent bot |
| `refused_awaitable` | yes | ✅ | ✅ | claim the window and await the reset |
| `refused_unknown` | yes | ❌ (recovery escalates) | ✅ (declared ignorance — not refuted) | operator ruling |
| `refused_hard` | yes | ❌ | ❌ | accept the gap / required-vs-optional |
| `declined` | yes | ❌ | ❌ | accept the decline |
| `refused_structural` ⭐ | yes | ❌ | ❌ | **split / accept / disable-for-this-PR** |

### Deadlocks: none. The finding is the NON-OPTION, exactly as the plan predicted

No member is a deadlock in the plan's sense (*"a state a plan cannot exit by acting"* being
unexitable). The four `passable: ❌` members all exit through the shipped, HEAD-bound,
gap-class-bound, fail-closed merge-authorization surface — the override **is** the exit, so the
plan's instruction not to re-litigate the deadlock framing is confirmed against merged `main`.

The barrier's own dispositions were classified alongside the per-bot members: `clean` (merges),
`blocked/participation-incomplete` and `blocked/pending-findings` (both authorizable), and the two
`UNKNOWN` branches (never authorizable — but not deadlocks either: their exit is to make the failed
read succeed, which is an action).

### The non-option pairings — a remedy offered that cannot work

⭐ **1. SHIPPED AND LIVE. `refused_hard` + cause `size` → `escalate_ask{reason:
rate_window_not_awaitable}`, whose `prompt_options[0]` was `"Wait another
{review_rate_window_timeout_seconds}s"`.** Sourcery's registry doc states in as many words that "the
same PR is over the limit a minute later and an hour later alike, so nothing reopens by waiting" — and
the operator's *first* offered option was to wait. **This is the defect D1 fixes.**

⭐ **2. LATENT AND UNGUARDED. `refused_awaitable` + cause `size` → Branch 2 `claim_and_await`.** The
recovery arming read `rate_limit_class` ALONE
(`_RECOVERY_BY_CLASS[bot_registry.rate_limit_class(bot_kind)]`, pinned by
`test_refusal_recovery_arming.py`) and was blind to the cause. Any `awaitable_window` bot that refuses
on size would get the full claim-await-generate recovery, burning the whole
`review_rate_window_timeout_seconds` budget on a ceiling that waiting does not move, then re-triggering
a bot whose answer cannot change. No live instance today (no `awaitable_window` bot declared a size
pattern), but nothing prevented one.

**3. `refused_hard`'s own interpretation text conflated the two causes** — "a per-PR size/diff ceiling
**or** a plan-level quota" — one member, two disjoint remedy sets, so a consumer rendering the member
alone named neither remedy correctly.

**4. `review_state_summary` bucketed every refusal under one `refused` label,** so `display_detail`
could not distinguish a size refusal from a quota one — the same collapse the summary was introduced
to undo for reviewed-vs-nobody-reviewed.

## Deliverables

_(completed below)_

## Build gate

_(completed below)_

## Findings

_(completed below)_

## Reviewer participation

_(completed below)_

## Cost

_(completed below)_

## Contract check (Step 9)

_(completed below)_

## What have we learned (Step 9)

_(completed below)_

## Residue

_(completed below)_
