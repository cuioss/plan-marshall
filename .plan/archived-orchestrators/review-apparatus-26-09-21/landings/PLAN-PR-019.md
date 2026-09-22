# Landing: PLAN-PR-019 — post_responses retransmits already-sent replies

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-12
cloud run: `cloud-runs/070-post-responses-retransmits-already-sent-replies/`
PR #1187 (`c89bfc530`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

The idempotency marker genuinely landed — imported, honoured and stamped on both transmit branches,
with `resolve_finding` clearing it on a changed disposition so it is a `(finding, disposition)` key
rather than a suppression. `count_responded` now counts only this round's transmits.

**Deliverables: 4 — 1 done, 3 partial.**

## ⛔ The failure branch did not land

A thread reply that is **delivered** and whose `RESOLVE_THREAD_MUTATION` then fails `continue`s past
the stamp, so the identical reply goes out again next round — and that same round reports the
delivered disposition under `count_untransmitted`.

**Standing rule this produces: when a plan is about a count that lies in one direction, check the
sibling count in the other.** This run fixed `count_responded` over-counting on the happy path; the
same fix left `count_untransmitted` **under**-counting on the failure path — a confident negative over
a reply that reached the reviewer.

## Report claims the verification found false

- "`verification-feedback.md` Step 8 (**sole** production invoker)" — refuted; the derived invocation
  set is exactly **two** (`automated-review-lifecycle.md` is the second).
- Finding 6, "cold read of the corrected prose answers correctly" — overstated; the cold read was
  pointed at the corrected paragraph (`:265`) while `:243` in the same file still asserts *"Only a
  finding with no `resolution_detail` is skipped"*. Re-verified live at HEAD.
- "D3(c) adapts `_dispatch_roster.py`'s derive → assert non-empty" — overstated; the test hard-codes
  two keys, so the non-empty assert cannot fail.
- "gives Sonar the same changed-disposition correctness for free" — accurate but **untested**.

## Gaps: 13 — 12 full, 1 partial, 0 uncovered

## ⭐⭐ `070 G1` is the wave's one substantive coverage hole — and the gap itself predicted it

PLAN-PR-029 (ex-`550`) D2 covers two of G1's three requirements. It does **not** carry the third, which
G1 states as an explicit ⛔: moving the marker earlier closes the duplicate-reply hole but opens a
second one — with the finding marked responded, the `already responded` guard skips it on every later
round, so a thread whose `RESOLVE_THREAD_MUTATION` failed **stays unresolved forever**. G1 requires the
resolve state persisted separately (a `resolve_pending` field or equivalent) plus a resolve-only branch
that re-attempts the mutation *without* re-sending the reply.

**550 D2 does exactly the half G1 warns against, and its Done-when pins the resulting behaviour rather
than the fix** — it requires "an already-responded skip on the second pass", which is the finding being
skipped entirely.

Verified directly: `grep -rn "resolve_pending\|resolve-only retry\|transmitted-but-unresolved"` over
the whole 5NN series → **no output**. The requirement is absent from every staged plan.

**Disposition: amend PLAN-PR-029 D2 before it is emitted** — do not stage a second plan on
`github_pr.py`, which the README forbids pairing on. Recorded as a pre-emit obligation.

## Standing facts

- ⭐ **A "derived population" that is a hard-coded literal is a vacuous guard, and this epic has now
  produced it twice** — D3(c)'s two-key dict comprehension here, and plan 090's noun set selected from
  the plan's own docstring rather than the 510-file distribution it scanned.
  `test/_shared/_dispatch_roster.py` is the in-tree precedent: parse the population from a substrate
  and raise when the substrate is absent.
