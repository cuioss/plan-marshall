envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T13:34:22Z

component=plan-marshall:tools-input-validation
category=bug

Relayed from Token-Sheriff PLAN-08 (PR #730 / `c40963ac`). Three malformed script invocations from one run, bundled because they share a shape: **the argparse surface accepted or rejected in a way the caller could not predict from the documented form.** ⛔ The first cost real diagnostic time — a router-scoped `--plan-id` placed after the verb made the PR step abort as "not logged in to GitHub", a message naming a cause that was not the cause. The bundling is the relaying orchestrator's judgement; split if you disagree.

## A — router-scoped --plan-id after the verb, misdiagnosed as a GitHub auth failure

# Candidate lesson: a router-scoped `--plan-id` placed after the verb was misdiagnosed as "gh not authenticated"

**Origin signal**: script-failure cluster 1 of 3 — notation `plan-marshall:tools-integration-ci:ci`.
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).
**Provenance note**: this was an orchestrator invocation mistake, NOT a script defect.

## Observation

`--plan-id` was placed AFTER the verb on the `ci` surface. On `ci` that flag is
*router*-scoped: `ci.py` consumes it before the provider parser is built, so it belongs
BEFORE the first positional. Written after the verb, argparse rejects it.

That much is the known signature. The consequential part is what happened next:

- A dispatched `create-pr` step read the resulting failure as **"gh not authenticated"**
  and halted the step. `gh` was in fact authenticated. The step stopped on a diagnosis
  that was false.
- A later dispatch reported that passing `--project-dir` (rather than `--plan-id`)
  produced a spurious **"Not authenticated"** error on the worktree — the same
  misattribution, reached by a second route.

So one invocation-shape error produced, twice, an error narrative pointing at
credentials. Every remedy that narrative suggests (re-auth, check token scopes, check
the worktree's git config) is wasted work, and none of it can succeed, because the
invocation never reached the authenticated code path at all.

## Why it is candidate-lesson shaped

The flag-position rejection is already a documented recurrence signature. What is NOT
covered is the *downstream misdiagnosis*: a CI-surface invocation failure being reported
by the consuming step as an authentication failure. That mapping is wrong in a way that
actively misleads — it renames a deterministic, locally-fixable argparse rejection as an
environmental credentials problem, which is the class of problem an agent is most likely
to escalate to the operator or to "fix" by re-authenticating.

Possible correctives (for the orchestrator to judge):
1. A consuming step must not translate a non-zero exit from the `ci` surface into an
   authentication verdict unless the payload actually carries an auth-class error code.
   An `unrecognized arguments` rejection and a 401 are different facts.
2. The two flags behave differently and both were implicated — `--plan-id` (router-scoped,
   must precede the verb on `ci`) and `--project-dir`. Whatever the second one's real
   contract is, it produced the same false auth narrative, which suggests the
   misclassification lives in the consumer's error handling rather than in either flag.

## Cross-plan judgement deferred

Whether this extends the existing router-scoped-flag lesson with a "do not re-narrate the
failure as auth" clause, or is a separate lesson about error-class preservation across a
dispatch boundary, is the orchestrator's call. This plan transmits the candidate only.

---

## B — --measured-diff-size is a plain-value flag while its sibling is not

# Candidate lesson: `--measured-diff-size` is a plain-value flag while its sibling list flags accept a bare form

**Origin signal**: script-failure cluster 2 of 3 — notation `plan-marshall:automatic-review:review_completeness`.
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).
**Provenance note**: orchestrator invocation mistake (flag arity), NOT a script defect.

## Observation

`--measured-diff-size` was passed with an empty value. The flag is a plain-value flag —
it is not declared `nargs='?'` — so an empty value is an argparse rejection. The
sibling flags on the same verb ARE list-shaped and DO accept a bare form, which is
exactly what made the mistake reachable: the caller generalised the arity of the
neighbouring flags to this one.

## Why it is candidate-lesson shaped

This is an arity-heterogeneity trap rather than a name or position trap: the flags sit
side by side on one verb, look alike, and differ in whether a bare/empty form is legal.
Nothing at the call site signals the difference, so the failure mode is "the invocation
that worked for the flag above does not work for this one".

Possible correctives (for the orchestrator to judge):
1. Read the declared arity per flag, not per verb — sibling flags on one subcommand do
   not share arity, and "the one next to it accepted a bare form" is not evidence.
2. If a measured value is genuinely unavailable, that is an *omit the flag* case, not a
   *pass it empty* case. An empty string is a supplied value that happens to be empty,
   which is a different assertion from "not measured".

Point 2 is the substantive half: passing an empty measurement and omitting the
measurement are semantically different, and only one of them is expressible here.

## Cross-plan judgement deferred

Whether this warrants its own lesson or extends the existing argparse-rejection
recurrence catalogue with a fourth signature (flag-arity, alongside verb-paraphrase and
the two flag-position mirrors) is the orchestrator's call. This plan transmits the
candidate only.

---

## C — --branch passed to prune-local-and-remote-ref, which declares no such flag

# Candidate lesson: `--branch` passed to `prune-local-and-remote-ref`, which declares no such flag

**Origin signal**: script-failure cluster 3 of 3 — notation `plan-marshall:workflow-integration-git:git-workflow`.
**Plan**: `standalone-guards` (PR #730, merged as `c40963ac`).
**Provenance note**: orchestrator invocation mistake (undeclared flag), NOT a script defect.

## Observation

A `--branch` flag was passed to the `prune-local-and-remote-ref` verb. That verb declares
no `--branch`, so argparse rejected the call with `unrecognized arguments`.

The flag is plausible precisely because the verb's *name* is about a ref: a reader
reasoning from "prune local and remote ref" naturally asks "which ref?" and reaches for
`--branch`. The verb evidently derives its target another way. So this is the
verb-name-implies-a-parameter trap: the name advertises a subject, the caller supplies
that subject explicitly, and the parser rejects it.

## Why it is candidate-lesson shaped

The existing recurrence catalogue covers *paraphrased verbs* and *misplaced flags*. This
is a third shape: a **flag invented from the verb's own semantics**. The invented flag is
not a paraphrase of a real one — there is no `--branch` on the verb under any spelling —
it is a parameter the caller inferred must exist because the operation obviously needs a
subject.

Possible corrective (for the orchestrator to judge): when a verb clearly operates on some
subject but declares no flag naming it, that is a signal the subject is *derived* (from
plan state, from the current checkout, from status metadata) — read the declaration
before supplying it, and never add a subject flag "for explicitness".

## Cross-plan judgement deferred

Note that all three of this run's script-failure clusters were orchestrator invocation
mistakes against correct scripts, and all three were flag-shaped (position, arity,
existence). Whether that clustering is itself the lesson — the three signatures are
variations of one habit, namely reasoning about a flag from context rather than reading
its declaration — is the orchestrator's call. This plan transmits the candidate only.
