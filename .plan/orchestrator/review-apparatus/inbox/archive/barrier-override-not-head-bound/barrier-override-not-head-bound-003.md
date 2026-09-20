envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:41:55Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=A fail-closed guard leaks through its own indeterminate paths - UNKNOWN must never mint a durable credential and a no-match must never admit

# A fail-closed guard leaks through its own indeterminate paths

## What happened

Plan `barrier-override-not-head-bound` hardened the pre-merge review barrier so that an
operator authorization is a persisted, HEAD-bound record rather than free text. Its own
pre-submission self-review found **two independent fail-open leaks in the new fail-closed
guard**, in the same round:

- **`37dad6` — the UNKNOWN branches could still mint a durable authorization.** The barrier's
  two UNKNOWN verdicts (the re-fetch itself failed; the predicate itself failed) carry an
  absolute refusal — *"The merge NEVER proceeds on an UNKNOWN verdict"* — and the spec
  explicitly carved them out of scope. Yet the granting path reachable from those branches
  could still write a `merge-authorization grant` record. A grant is **durable**: once
  written it satisfies the check at that HEAD forever. So an indeterminate verdict, which is
  never allowed to merge, could nonetheless mint the credential that authorizes a later
  merge. The refusal was enforced on the *routing* and not on the *credential issuance*.
- **`454e1b` — a fail-open `--kind` matcher inside a guard built to fail closed.** The kind
  matcher admitted on no-match instead of denying, so an unrecognised or absent kind resolved
  to "authorized" rather than "refused".

## Why it recurs

Both leaks sit on the paths a reader does not picture when reasoning about the guard. The
happy path (valid credential → admit) and the obvious sad path (lapsed credential → refuse)
are the ones the design, the prose, and the tests all cover. The paths that leak are:

- **indeterminate** — "we could not compute a verdict";
- **no-match** — "nothing in the store corresponds to this key".

Both are *absences*, and an absence is easy to write as a fallthrough. A fallthrough in a
matcher inherits whatever the last branch was; a fallthrough in an authorization store
inherits "nothing said no". The plan's own spec anticipated one half of this and got it
right in the `check` verb — *"an empty store returns `any_authorized: false` … `absent` is
never collapsed into `valid`"* — and then leaked at two sites the same sentence did not
happen to name.

Note the asymmetry that makes the UNKNOWN case worse than a normal fail-open: refusing to
MERGE on UNKNOWN is a transient decision, but issuing a GRANT on UNKNOWN is permanent. A
guard can be simultaneously correct about the action and wrong about the credential.

## Rule

For any guard whose contract is "fail closed":

1. **Enumerate the guard's indeterminate outcomes explicitly** — `unknown`, `error`,
   `not-found`, `no-match`, `empty`, `timeout` — and assert a DENY verdict for each one by
   name. A guard with a single `else: allow` has not been made fail-closed by documentation.
2. **Separate "may this action proceed?" from "may a credential be issued?"** Enforcing the
   refusal only on the action leaves the durable artifact unguarded. If a verdict is not
   good enough to act on, it is not good enough to mint a credential from.
3. **Never let a matcher admit on no-match.** Order verdict branches specific-first and
   forbid a catch-all that resolves into the passing set.
4. **Test the absences, not just the negatives.** "Lapsed credential is refused" is a
   negative test. "Unknown verdict issues no grant" and "unrecognised kind is refused" are
   absence tests, and they are the ones that were missing here.
5. When a spec states a fail-closed rule in one place (e.g. for one verb), **sweep every
   other site that decides the same question in one pass** — a rule stated once and applied
   at one of three sites is indistinguishable from a rule not stated at all.

## Scope note for the orchestrator

Two distinct sites, one archetype, found in one self-review round. Domain-invariant rule;
the concrete sites are `phase-6-finalize/standards/branch-cleanup.md` and the
`merge-authorization check` verb. Classification deferred to the orchestrator.
