# API-Sheriff PR #138 — post-merge revisit (merged `ffa8cef`)

epic: review-apparatus · analysed 2026-08-01 · **cross-repo** (`cuioss/API-Sheriff`), **MERGED** — a
genuine post-merge revisit · source: operator paste of the finalize summary, then verified against code
· evidence: `.plan/execute-script.py:983-992`; `tools-script-executor/templates/execute-script.py.template:768`;
`automatic-review/SKILL.md:604,610-614`; `gh api graphql` PR #138

> ⭐ **The most operationally valuable data point this epic has received.** It does not merely corroborate
> a staged plan — it **refutes that plan's remedy while the plan is RUNNING.**

## 1. The executor strips falsy args — real mechanism, ALREADY HANDLED by PLAN-PR-014

> ⛔⛔ **CORRECTION, same day.** This section originally read *"PLAN-PR-014's REMEDY IS WRONG … and PR-014
> is in flight NOW"*, and drove an urgent operator relay. **That was WRONG.** It was written from the
> spec's wording without reading the shipped branch.
>
> ✅ `feature/crashed-participation-gate-records-a-pass` ships **`nargs='?', const=''` on all five flags**
> of `review_completeness.py` — so a bare `--in-progress-bots`, which is *exactly* what the executor's
> strip produces, is now VALID and reads as the empty list — plus an **UNKNOWN-verdict branch recording
> `loop_back` on any non-zero exit**. The quoting was added alongside and is not the load-bearing change.
> **No correction is owed to that plan.**
>
> ⚠ Kept rather than deleted because the failure is instructive: the orchestrator recorded a claim before
> verifying it against the implementing source — the exact discipline its own verify-first contract
> demands, broken hours after writing that contract into a sweep document. The mechanism below is still
> true; only the verdict about PR-014 was false.

The operator's root cause, quoted: *"passing `--in-progress-bots ""` makes the executor drop the empty
value, so argparse sees a flag with no argument. Omitting the optional flag works."*

**Confirmed verbatim at `.plan/execute-script.py:988-989`:**

```python
# Strip empty string args (defensive: agents may pass empty args from shell variable expansion)
script_args = [a for a in script_args if a]
```

⇒ The executor **unconditionally strips every falsy argument** before argparse sees it. `--flag ""`
becomes a bare `--flag`, and argparse exits 2 with *"expected one argument"*.

⛔⛔ **This means QUOTING IS NOT THE FIX, and PLAN-PR-014's spec implies that it is.** That spec frames
the defect as *"Unquoted `{...}` at ≥2 sites × 5 flags"* — the natural reading of which is *add quotes*.
**Quoting changes nothing**: `""` is falsy and is stripped at line 989 exactly as a bare empty
substitution is. A quoting fix would leave the crash fully intact.

⭐ **This is the epic's own recurring archetype about to recur inside its own remediation** — a *vacuous
fix*, the family already logged at n=4 with one instance introduced BY a fix for it. PLAN-PR-014 exists
to stop a crashed gate recording a pass; shipping a fix that does not stop the crash would reproduce its
own target defect, exactly as PLAN-86 did.

**The working remedy is the one the operator found empirically: OMIT the optional flag when its set is
empty** — not quote it.

⚠ **And the guard is itself the deeper defect.** The comment calls the strip *defensive*. It defends
against one failure mode (a stray empty arg from shell expansion) and **manufactures another** (a
malformed flag from a legitimately-empty optional value), converting a recoverable no-op into an exit-2
crash. ⛔ The fix site is the GENERATOR —
`tools-script-executor/templates/execute-script.py.template:768` — **never the generated
`.plan/execute-script.py`**.

**Population — larger than PR-014's scope.** The two sites passing possibly-empty placeholders to this
predicate are `automatic-review/SKILL.md` and `phase-6-finalize/standards/branch-cleanup.md` (grep-verified,
not assumed). But the *executor-level* strip governs **every marketplace script invocation that can pass an
empty value**, which is a strictly larger population than PR-014's 5 flags × 2 sites. ⛔ Deriving that
population is the plan's job, not this document's — but it must not be assumed to be 5×2.

## 2. ⭐⭐ "A green bot check can mean *never looked*" — the sharpest instance yet, with a 1-second gap

CodeRabbit set a **success commit status** on `be0271a` **one second after** posting *"we couldn't start
this review"*. It read green everywhere at once: checks list, commit status, and zero comments filed.

**The counterfactual is measured, not hypothesised.** Waiting out the rate limit produced **4 real
findings**, including a factually wrong precedence claim in ADR-0025 and `curl` probes with no timeout
whose *"within 30 seconds"* abort was unreachable. Had the green been trusted, all four would have
shipped.

⇒ This is the epic's standing rule (*only `ci pr comments` is evidence of participation*) with the
tightest timestamp evidence yet, and it is **direct, measured support for enabling
`review_rate_window_await`**: waiting was not merely safe, it was worth 4 findings.

## 3. Corroboration — `post_responses` non-idempotency, second independent sighting

The operator reports `github_pr post_responses` has no per-finding scope and *"re-posts every prior
terminal disposition on each run"*, with the last round routed through scoped primitives specifically to
avoid spamming **11 threads a third time**.

⇒ Independently corroborates the epic's existing Open Defect (first sighting: 9 duplicated thread
replies). **Two independent sightings, in two repositories.** ⚠ Per this epic's own rule, note what this
is NOT: the two counts (9, 11) are two observations, not a trend — do not derive a rate from them.

## 4. ✅ The local security audit RAN, and cleanly

`[OK] finalize-step-security-audit — 0 edits, 0 findings (delta re-audit)`.

⇒ One **confirmed activation** on API-Sheriff, consistent with `review-practice.md` § 3's note that the
step is active there in most cases. ⛔ It does **NOT** answer the plan-marshall activation rate left OWED
in [`2026-08-01-sweep-4day.md`](2026-08-01-sweep-4day.md) § 6 — different repo, different lane routing.
It does establish that the step works when active, which narrows that owed question to purely a routing
one.

## 5. What the review rounds actually caught

3 triage rounds → 21 findings → 10 fix tasks across 2 loop-backs, including a security-relevant one: a
cipher guard that could not fire for a protocol/suite intersection miss. ⭐ The executor found the task's
**prescribed mechanism did not work** (JDK 25 `setEnabledProtocols` does not filter
`getEnabledCipherSuites` — both protocols returned the same 31 suites) and derived a working per-protocol
set **rather than shipping a vacuous guard**. Worth recording as the *positive* case of the same archetype
§ 1 warns about: a prescribed fix was tested against reality and replaced when it proved vacuous.

## 6. ⚠ Operator's self-declared caveat — assessed, not waved through

`pre-push-quality-gate` was marked done once from ledger evidence rather than re-run, logged as a
decision. **Sound as described**, on one condition that was met: the ledger showed whole-tree
`verify -Ppre-commit` and `verify -Pcoverage` green **at that exact tree sha**. A sha-matched ledger read
is evidence about *this* tree, not a stale-cache substitution.

⚠ Recorded because the epic's theme is confident-signal-hides-a-caveat and the *shape* is adjacent to the
[stale-cache-as-evidence] archetype. The discriminator is the sha match, and it held. **Not a defect.**

## 7. Could we have found it ourselves?

**OWED for the 4 CodeRabbit findings** — this document is written from the operator's finalize summary,
and the back-feed question keys off the **answers posted on the PR**, which are not in that summary.
⛔ Answering from the summary alone would be the "keyed off internal state" error
`review-practice.md` already records as discarded. Re-run against `ci pr comments --pr-number 138`.

⭐ One is *provisionally* a "Yes" worth checking: **`curl` probes with no timeout whose "within 30
seconds" abort was unreachable** is an unreachable-guard shape, and `pre-submission-self-review` already
advertises an unreachable-guard detector (shipped in plan-marshall #1042). If that detector exists and
ran here, this is the **fourth answer shape (WIDEN)**, not a new detector.

## Feeds

- **PLAN-PR-014** — ✅ **NO ACTION OWED.** The urgent-relay claim in the first version of § 1 is
  withdrawn: the plan already ships `nargs='?', const=''` plus an UNKNOWN-verdict `loop_back` branch,
  which covers the executor-strip mechanism directly. ⭐ The only genuine hand-off is the **population
  question** — every *other* marketplace script with an optional flag lacking `nargs='?'` remains
  exposed if it can be reached with an empty value. **UNMEASURED; a question, not a defect.**
- **PLAN-PR-008 / the `review_rate_window_await` question** — § 2 supplies measured evidence that waiting
  out a rate limit is worth 4 real findings. This is the strongest argument yet for enabling it.
- **Open Defect `post_responses` non-idempotency** — § 3 is a second independent sighting, cross-repo.
  Still unowned; the case for staging it is stronger.
- **`2026-08-01-sweep-4day.md` § 6** — § 4 narrows the owed security-audit question to lane routing alone.
- **PLAN-PR-012** — § 7's unreachable-`curl`-timeout finding is a candidate for the WIDEN batch, pending
  the posted-answer check.
