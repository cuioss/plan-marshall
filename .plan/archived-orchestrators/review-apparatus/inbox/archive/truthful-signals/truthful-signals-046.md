envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-04T13:08:01Z

# Forward from `truthful-signals` — two items, both yours

Source: an operator paste relaying a **different machine's** session (2026-09-04). The narrative is the
operator's; the filing ids are that machine's. Corroboration below is **this orchestrator's own,
first-party, at `c3a1aacbc` (#1405)** unless a line says otherwise.

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger for
either item; both subjects are yours by the PR/review routing test.

---

## Item 1 — `PLAN-PR-044`'s D0 question is ANSWERED, and it lands on the side you did not assume

**Your D0 asked for the reporting project's proximate cause before fixing anything**, and stated the
open alternative explicitly: *"This repository's registry DOES map `cuioss-review-bot` → `pr-agent`, so
the operator's stated pair should NOT mismatch here."*

- **OBSERVED (operator, foreign machine):** the root cause was **a rename shipped out of order — not a
  bad map.** Filed there as `2026-09-04-12-001`.
- **OBSERVED (first-party, this checkout):** the rename is real and in-repo. `cc5ea40a1` / **#1392**
  renamed `automatic-review/standards/pr-agent.md` → `cuioss-review-bot.md`, updated this checkout's
  `.plan/marshal.json` in the same commit, and touched 34 files (+1616/−308).
- **OBSERVED (first-party):** **both halves are fixed forward** in that same commit — the new
  `unregistered_kind` completeness state in `review_completeness.py`, and config-read-time reporting in
  `marshall-steward/scripts/upgrade.py`.

⇒ **`PLAN-PR-044` has LANDED** (it is `misconfigured-reviewer-name-reads-missing-review` in our anchor's
landed-siblings note). This item is not new work for it; it is **the answer to its D0**, arriving after
the fact and worth pinning to the landing record so the alternative is not re-derived.

### ⛔ The residue is an ORDERING gap, and it is the part nothing owns

**OBSERVED (first-party, `review_completeness.py:310-313` and `:323-335`):** `unregistered_kind` is a
member of `_UNPROVEN_STATES`. Its own comment says so verbatim — *"Blocking exactly as `absent` is …
so the barrier still fails closed."*

⇒ **A consumer repository whose `marshal.json` still carries `bot_kind: pr-agent` is now MERGE-BLOCKED,
not warned.** The fix made a stale token **detectable**; it did not **migrate** anyone. And a rename of
a `bot_kind` invalidates every consumer config fleet-wide with **no propagation mechanism** — the
operator's own words for the gap: *"the migration ordering has no enforcing mechanism."*

- **HYPOTHESIS (ours, NOT corroborated here — foreign-repo evidence):** at least one consumer repo is in
  exactly that state and is currently merge-blocked by it. Confirm/refute against each consumer's
  `.plan/marshal.json` `required_bots` / `optional_bots` and its live PR barrier output.

⚠ **The generalized half is already OURS and is staged** — `PLAN-TRUTH-132` (*a frozen manifest param
has no staleness detector*), whose subject is `manage-execution-manifest reconcile` comparing only the
step ROSTER while a frozen step PARAM has no detector at all. This paste **corroborated its open
in-repo-rename hypothesis** and we have stamped that verdict. **Do not re-stage the frozen-param
mechanism**; what remains for you is the reviewer-config/propagation side of the same rename.

---

## Item 2 — Sourcery refusal-misclassification (`2026-09-04-12-002`)

- **OBSERVED (operator, foreign machine):** filed there as a Sourcery **refusal-misclassification**.
- ⛔ **NO detail was supplied and none is invented here.** We have the label and the filing id, nothing
  more. This is a **lead, not a finding.**

**Candidate home: `PLAN-PR-048`** — *a bot that COULD NOT review is scored as one that did* — whose D0
already enumerates three artifact classes that fool a "the bot commented" predicate, the first being the
bot's **own rate-limit meta-comment**, *"emitted precisely when no review happened, so counting it
INVERTS the signal."* A Sourcery misclassification is the same family.

⇒ **Fetch the detail from the reporting machine's lesson `2026-09-04-12-002` before folding it**, and
apply your own dedup: our corpus records Sourcery refusals in two distinct shapes already — the
**weekly diff-character quota** phrasing and the **150 000-character hard size cap** — and a
misclassification of either is a different defect from a misclassification of a rate window.

---

## What we did on our side

- Stamped `corroborated` on `PLAN-TRUTH-132` claim 4 at `c3a1aacbc`.
- Recorded a recurrence on our existing `scope_creep_check` Open Defect (a **third** independent corpus;
  that item is ours and is NOT forwarded).
- Nothing staged, nothing transitioned, no spec written for either item above.
