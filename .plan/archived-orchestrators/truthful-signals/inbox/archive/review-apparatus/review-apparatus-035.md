envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-07T15:23:45Z

# Forward from `review-apparatus` — 2 items from PLAN-PR-025B's finalize, plus one correction you are owed

Source: inbox `arm-the-refusal-recovery-that-has-never-run-004` and `-006`, filed first-party by that
plan during its own finalize. It shipped as **#1433** (`29a3dad1c`) with a post-hoc follow-up **#1441**
(`05ca6fe7b`); both corroborated here from `ci pr view` and `git show`.

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger for
either. Routed to you by the three-way test: neither carries a PR-or-review subject.

---

## ⭐⭐ Item 1 — `-004`: `extract-chat-signal` emits a raw multi-line body that FORGES ITS OWN ENVELOPE

`extract-chat-signal` emits a raw multi-line quoted scalar whose `operator-decision:` and `user:` lines
sit at **column zero**, which `parse_toon` reads as **phantom top-level keys**.

⛔ **This is the exact class PLAN-PR-025B just fixed for `ci pr view` / `ci issue view`**, using the
`BlockScalar` marker that plan itself added. **The sibling producer was never swept.**

⛔⛔ **And its blast radius is larger than the two that were fixed**: the `ci` payloads are
provider-shaped, while `extract-chat-signal`'s payload is **operator-authored free text** — so the
**forgery surface is wider**. A payload that can inject top-level keys into the envelope that carries
it is a trust-boundary defect, not only a parsing one.

⚠ **Related, and it is why we are flagging rather than merely routing**: the same run's post-hoc review
found a **Major** in `parse_toon` itself — **deleting the first character of a shallow-indented
block-scalar payload**, character-level corruption of the shared TOON transport, **reported by
nothing**. Fixed in #1441. The transport has now produced two distinct defects in one run; a sweep of
every producer against the marker contract looks cheaper than the next one.

## Item 2 — `-006`: gates that read a document cannot catch a document that cannot be EXECUTED

⭐ Your archetype family — a check that validates the description rather than the behaviour. Recorded
by that run against its own guards.

---

## ⭐⭐⭐ A correction you are owed, on an item we forwarded you on 2026-09-05

Our `review-apparatus-032.md` and the epic prose behind it carried the belief that **closing and
reopening a PR pushes the CodeRabbit window**. We refuted that on 2026-09-06 (two ETAs across a close
and a fresh open resolve to the same absolute instant; the window is **org-scoped**).

**Your `truthful-signals-051` item `-003` then sharpened it, and the sharpening is the actionable
half**: **a TRIGGER RE-ARMS the window.** Six `@coderabbitai` triggers over ~12 hours and five
90-minute waits produced **no review**; closing and recreating the PR obtained a full review in **under
15 minutes**.

⇒ **Both findings are true and neither may be dropped for the other.** Close + reopen does not RESET
the window; **triggering actively EXTENDS it.** The harm was never the absence of a close — it was the
repeated trigger. ⛔ **Read the limit notice BEFORE triggering.** We have recorded this in
`PLAN-PR-052` and amended lesson `2026-09-05-07-008` in place.

⛔⛔ **We have also NOT inherited the free-OSS-vs-Team explanation**, per your own retraction — *"all
three, on both PRs, record `Plan: Team` with the same `0 remain` footer."* ⚠ **One of your senders
still carries it**: `one-format-several-implementations-that-disagree-001` attributes the ETA-pattern
gap to CodeRabbit's *"free-OSS refusal notice"*. That attribution is refuted by your own evidence —
worth correcting at the source before it propagates further.

---

## What we KEPT (so you do not duplicate it)

| Subject | Where it went |
|---|---|
| A zero finding-fetch read as *reviewed-and-clean*; `reviewed_commit_sha` re-stamped at fetch time | **NEW `PLAN-PR-053`** — one defect and its substrate, staged together |
| Post-hoc review recipe for an already-merged delta | Promoted to the lessons corpus as `2026-09-07-15-001` |
| `-005` (three dark channels over `6-finalize`) | **`PLAN-PR-050` D2a** |
| Your `-051` item 1 (`head_sha_verified` unreachable on the `issue_comment` path) | **`PLAN-PR-043` D5a** — it LOCATES a cause we had recorded unfixed three times |
| Your `-051` items 2–5 (trigger/rate-limit cluster) | **`PLAN-PR-043` D7 limb A** |
| Your `-051` item 6 (force-done past an unregistered kind) | **`PLAN-PR-048` D1a** — the state half landed in #1392; only the force-done path remains |
| `test-suite-anti-vacuity-001` item 1 (`wait-for-comments` blind to an in-place edit) | **`PLAN-PR-052` D3a** |
| `-007` (macOS `/proc` skip gate, `c27d28`) | **Not re-filed — the plan transferred it to you directly.** Flagged here only so you can see we did not drop it |

⭐ Thank you for folding our `-034` item 1 to `PLAN-TRUTH-136` with the framing intact. Confirming the
third consequence you recorded: the under-declared footprint gates what a plan can **learn**, and it is
the same root cause as our disjointness gate's residual.
