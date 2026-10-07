envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T14:01:34Z

component=plan-marshall:persona-module-tester
category=anti-pattern

# Standards input: four generic falsifiability rules for tests and prose — jointly-blind test pairs, land the guard with the removals, a comment naming its guard is a claim, scope a verdict to its evidence

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Four lessons filed in **API-Sheriff's**
store. They are **generic methodology, not tool defects**: every concrete instance they name in
API-Sheriff is already fixed (verified at API-Sheriff `origin/main` `428bbec`, 2026-09-11). Routed here
by operator decision during the `deployment-configurability` epic's lessons intake, as **input for
plan-marshall's testing and documentation standards** — candidate homes: `persona-module-tester`
(test-set falsifiability), `ref-code-quality` (guard-with-removal), `pm-documents:ref-documentation`
(mechanism claims in prose), and the orchestration verify-first contract (verdict scoping). Written here
first and removed there second (integrate-then-remove). Original bodies verbatim below.

Origin ids: `2026-09-02-13-001`, `2026-09-10-22-001`, `2026-09-02-22-002`, `2026-09-02-13-002`.

## The shared rule

All four are one question asked of different artifacts: **"what would have to be deleted or changed
for this to go red — and did anything actually check that?"**

| Lesson | Artifact | The rule | Local instance status |
|---|---|---|---|
| `2026-09-02-13-001` | a pair of tests | Two tests splitting an input space can each be correct and jointly blind; review complementary pairs as a SET: "if the mechanism both protect were deleted, would either go red?" Per-item review passes (Q-Gate, outline, self-review, simplify) cannot see a set-level gap — CodeRabbit caught it | fixed (`AwaitsTest:177`) |
| `2026-09-10-22-001` | a defect class | Removing N instances without a mechanical guard leaves N+1 free to arrive (it arrived in a day, copy-pasted from a sibling service, caught only at the merge-queue boundary). Land the guard in the same change; "no instances left" is what makes the guard cheap, not redundant | guard landed and fired |
| `2026-09-02-22-002` | a comment / doc sentence | "Guarded by X", "enabling Y does Z", "safe because the shell does W" are claims; open the mechanism before writing them. Any sentence falsified by opening one file must be written only after opening that file | all four instances fixed |
| `2026-09-02-13-002` | an investigation verdict | Evidence covering one form of a hypothesis retires that form, not the hypothesis; N claims read off one observation are one observation and N−1 inferences. A MEASURED label does not check scope | doc corrected |

**Relation to existing plan-marshall surfaces (not verified exhaustively — a lead, not a finding):** the
orchestration standard's Verify-First Contract already covers asserted presence/absence in specs, and
`persona-module-tester` covers AAA and coverage; neither states the set-level or guard-with-removal
rules as far as this intake read. Suggested disposition: fold into standards, no tool change.

---

## Original lesson `2026-09-02-13-001` (verbatim)

id=2026-09-02-13-001
component=java-testing
category=anti-pattern
status=active
created=2026-09-02

# Two tests can each be correct and jointly blind - review complementary pairs as a set, not individually

"Is each test correct?" is a strictly weaker question than "what regression would this
SET fail to catch?" A pair of tests can be individually sound, individually meaningful,
and collectively blind to the behaviour they appear to cover.

## The shape

Two complementary probes split a behaviour's input space between them — non-empty and
empty, present and absent, success and failure. Each asserts something true about its own
half. But the assertion that would pin the *shared* mechanism sits in neither, because
each author reasonably assumed the other half covered it.

The result is a coverage hole with no symptom. Both tests pass. Both look purposeful.
Neither would go red if the mechanism they exist to protect were deleted.

## What happened

`AwaitsTest` (API-Sheriff, `api-sheriff/src/test/java/de/cuioss/sheriff/gateway/testsupport/`)
carried a matched pair on rejected-upgrade diagnostics:

- `reportsStatusAndHeadersOnARejectedUpgrade()` — a rejection with a **non-empty** body,
  asserting the failure message names the status and the header.
- `statesTheAbsenceOfAZeroLengthRejectionBody()` — a rejection with a **zero-length**
  body, asserting the message renders `body=<none>` rather than trailing off.

Every assertion in both was true and worth making. But between them, **nothing asserted
that a non-empty body is rendered at all.** Delete the body-rendering code path and the
first test still passes (it only checked status and header) and the second still passes
(its body is empty, so `body=<none>` is still correct). A regression that silently stopped
rendering rejection bodies would ship green.

The fix was one assertion in the non-empty probe:

```java
() -> assertTrue(message.contains(bodyContent),
        "the failure names the rejection's body content — without this the pair is "
                + "blind to a regression that stops rendering a non-empty body, since "
                + "the companion test only pins the empty case")
```

## Why nothing caught it

This is the part worth remembering. The gap survived, in order: the Q-Gate, the solution
outline, the pre-submission structural self-review, and the simplify pass. **CodeRabbit
caught it.** Every one of those passes asks a per-item question — is this test correct, is
this assertion justified, is this code simpler than it was — and the defect is invisible to
all of them because no individual item is wrong. Only a question asked about the *set*
surfaces it.

## Rule

When tests come in complementary pairs — and they routinely do, because splitting an input
space is good practice — review them **as a set**, with one explicit question:

> If the mechanism these two tests exist to protect were deleted, would either go red?

If the answer is no, the pair is decorative for that mechanism, however correct each member
is. Add the missing assertion to whichever member's fixture actually exercises it (here, the
non-empty case), and say in the assertion message *why the companion does not cover it*, so
the next reader does not delete it as redundant.

Generalisation: per-item review cannot find set-level gaps. Any review pass whose unit is
the individual item — a test, an assertion, a branch, a config key — needs a deliberate
second pass whose unit is the collection, asking what the collection as a whole fails to
constrain.

## Related

- `2026-09-01-14-003` — the same family (a test that cannot fail), reached from the other
  direction: there an assertion was *made* dead by a refactor; here an assertion was never
  written because each author assumed the other half covered it. Both produce a test that
  reports coverage it does not provide.
- `CLAUDE.md` § Testing — "if the key were deleted entirely, would any test go red?" is
  this same falsifiability question applied to configuration keys. The question generalises
  past config to any mechanism a test set claims to cover.

## Evidence

Plan `macos-loopback-hang-investigation` (2026-09-02, API-Sheriff), PR #243 (merged as
`5948962`); `AwaitsTest.reportsStatusAndHeadersOnARejectedUpgrade()` /
`statesTheAbsenceOfAZeroLengthRejectionBody()`. Found by an automated PR reviewer after
four separate local review passes missed it.

---

## Original lesson `2026-09-10-22-001` (verbatim)

id=2026-09-10-22-001
component=code-quality
category=anti-pattern
status=active
created=2026-09-10

# Removing every instance of a defect class does not stop the next one - land the mechanical guard in the same change

## Observation

This branch removed **ten** instances of one defect class by hand and, over the objection that a
guard was redundant once the instances were gone, also landed a **mechanical guard** for the same
class. The argument that carried it was narrow and did not depend on any of the ten: *removing ten
lines without adding one leaves the eleventh free to arrive.*

The eleventh arrived within a day — from a direction none of the ten predicted. A sibling PR (#288),
authored independently and copied wholesale from a neighbouring service, carried a fresh instance of
the same defect onto `main`. The guard caught it at the **merge-queue boundary**, i.e. after review,
after CI on the PR branch, and after every human who looked at the diff.

## Why the manual removal could not have caught it

The ten removals and the eleventh instance share a defect class but share no code path, no author
and no review. The removals are a statement about the tree at one instant; the guard is a statement
about every tree from then on. Only the second kind of statement survives:

- a **copy-paste import from another repository or service**, which by construction never saw this
  branch's cleanup;
- a **revert or a long-lived branch** that predates the cleanup and merges after it;
- a **new contributor** applying the neighbouring service's idiom because it is the local idiom
  there.

Each of those defeats "we removed them all" without anyone doing anything wrong. Note also *where*
it was caught: at the merge queue, not on the PR. Review and PR-branch CI had both already passed,
so the mechanical guard was the only remaining reader that could see it.

## Directive

1. **A change that removes N instances of a defect class is unfinished until it also makes instance
   N+1 impossible or loud.** Land the guard — a test, a lint rule, an arch-gate constraint, a
   compiler setting — **in the same change** as the removals. Deferring the guard to a follow-up
   loses exactly the window in which the class is best understood.
2. **"There are no instances left" is not an argument against the guard; it is the argument that
   makes the guard cheap.** At zero instances the guard is green on day one and costs nothing to
   land. It is at its most expensive later, when instance N+1 already exists and the guard's first
   act is to turn something red.
3. **Reject "redundant with the removals" as a reason to drop a guard.** The removals and the guard
   answer different questions — *is the tree clean now?* versus *will the tree stay clean?* A
   reviewer arguing the second is redundant with the first has substituted one for the other.
4. **Weigh the guard against ingress paths, not against instance count.** The question is not "how
   many were there" but "how can a new one get in" — copy-paste from a sibling service, a revert, a
   stale branch, a new contributor. If any of those exist, N is irrelevant.

## Evidence

Ten instances removed on this branch plus one guard landed in the same PR; guard fired on the
eleventh instance one day later, on `main`, at the merge-queue boundary, on unrelated PR #288 whose
content was copied from a neighbouring service. Nothing else in the pipeline flagged it.

---

## Original lesson `2026-09-02-22-002` (verbatim)

id=2026-09-02-22-002
component=documentation
category=anti-pattern
status=active
created=2026-09-02

# A comment naming its own guard is a claim, not a guard - open the guard and look

## Observation

Four times on one branch, prose asserted a property that the mechanism it named did not have. Every
one was caught by human/bot review; **not one was caught by a test**, because in each case the prose
was the only thing that was wrong and prose is not executed.

1. A comment asserting "every build stays green" sat on an edit whose own tests this branch turned
   red.
2. A script comment claimed its value was "machine-guarded by `ManagementRootPathLabelIT`". The IT
   never opens that file — the guard named a test that could not observe the thing it was said to
   guard.
3. A documented route for re-enabling CVE scanning was **inert**: the plugin it instructs the reader
   to activate is unbound in the parent POM chain, so following the documented steps produces no
   scan.
4. A comment justified a `case` construct as necessary for `set -e` safety, resting on a claim about
   bash `errexit` behaviour that is not true.

## Why it recurs

A claim about a guard is cheap to write and expensive to check, and the two drift in one direction
only: the guard changes, the sentence does not. Worse, the sentence is *load-bearing* — a later
reader who trusts "machine-guarded by X" stops looking, so a false guard-claim is strictly worse
than no claim, exactly as a green assertion that cannot fail is worse than no assertion.

## Directive

When writing or reviewing a sentence that asserts a mechanism exists, **open the mechanism**:

- **"Guarded by X"** — open X and find the line that reads the guarded thing. If X never references
  it, the claim is false. Naming a test file is not evidence; naming an assertion in it is.
- **"Enabling Y does Z"** — follow the wiring to the point Y is actually bound. A configuration
  block that no plugin execution reads is documentation of an intention, not of a route.
- **"This is safe because the shell/runtime does W"** — verify W against the actual semantics, not
  against the folk version. Claims about `set -e`, exit-code propagation inside pipelines and
  subshell scoping are the recurring offenders.
- **"Every build stays green"** — check the branch's own test results before asserting anything
  about build outcomes; the run in front of you is the cheapest possible evidence and is routinely
  skipped.

The cheap general form: **any sentence that would be falsified by opening exactly one file must be
written only after opening that file.** If opening it is not worth the time, delete the claim rather
than shipping an unverified one — the deletion loses nothing, the false claim costs a later reader
their scepticism.

Related: `2026-09-02-13-002` (a claim must be scoped to the evidence that retired it) is the same
family seen from the evidence side; this lesson is the mechanism side.

---

## Original lesson `2026-09-02-13-002` (verbatim)

id=2026-09-02-13-002
component=documentation
category=anti-pattern
status=active
created=2026-09-02

# A hypothesis retired on evidence covering one of its forms is not retired - scope the claim to the evidence

A hypothesis has forms. Evidence that covers one form retires that form — not the
hypothesis. Writing the broader conclusion is how an investigation document launders an
inference into a measurement, and it happens most easily in documents whose whole subject
is keeping the two apart.

## What happened

Plan `macos-loopback-hang-investigation` produced an investigation document whose explicit
structure separated MEASURED from INFERRED. Two claims in it overreached their evidence,
from two different authors:

**1. A hypothesis retired on one of its forms.** The document wrote that ephemeral port
reuse was **CONTRADICTED**. The evidence covered *held `listen(0)` listeners only* — not
accepted sockets, not client sockets. Those are distinct forms of the same hypothesis with
distinct exhaustion behaviour. The measurement was real and correctly performed; the verdict
generalised past it. "Contradicted for held listeners" was the finding; "contradicted" was
what got written.

**2. Three facts read off one command's output.** Three separate firewall properties —
global state, block-all mode, and stealth mode — were each stated as established, all
derived from a single command's output. One observation supporting three independent claims
means at most one of them was actually instrumented; the other two are readings of the same
datum.

The same shape, twice, in one document, from two authors. That is not a lapse of attention —
it is the default failure mode of writing up an investigation, and it needs a mechanical
check rather than more care.

## Why the MEASURED/INFERRED split does not prevent this

The split sorts claims into two buckets. It does **not** check that a claim placed in the
MEASURED bucket is scoped to what was measured. A correctly-labelled MEASURED claim can
still assert more than its evidence supports, and the label then actively increases the
reader's confidence in the overreach. The section heading is a promise the prose has to
keep on its own.

## Rule

Before writing any conclusive verdict — CONTRADICTED, CONFIRMED, RULED OUT, ESTABLISHED —
apply two checks:

1. **Enumerate the hypothesis's forms, then state which the evidence covered.** If the
   evidence covered a proper subset, the verdict names that subset: "contradicted for held
   listeners; untested for accepted and client sockets." A hypothesis with untested forms is
   *narrowed*, never retired. Narrowing is a real result and is worth writing as one — the
   dishonest move is rounding it up to closure.

2. **Count observations against claims.** If N independent claims trace back to one command,
   one log line or one run, you have one observation and N−1 inferences. Say so, or go
   measure the others. Independent claims require independent evidence; sharing a source
   makes them one claim with three facets.

Concretely, every conclusive verdict in an investigation write-up should be answerable to:
*what specific observation would have to change for this verdict to flip, and did I actually
make that observation in every form the claim covers?*

## Cost when violated

An over-broad retirement is worse than no verdict at all. A hypothesis marked CONTRADICTED
is removed from the search space permanently — the next investigator reads the document,
sees the question closed, and does not re-open it. The untested forms then have to be
rediscovered from scratch, usually after the same symptom recurs and the document is trusted
to have already excluded the cause.

## Related

- `2026-09-01-19-001` — carries an explicit `## INFERRED (not established)` section naming
  an un-instrumented mechanism as a story that fits the evidence. That is this rule applied
  correctly, and is the model to follow.
- `2026-08-29-16-003` — build-report digests are lossy; read the primary artifact. Same
  underlying discipline: a summary is not the observation, and reading a verdict off a
  derived surface is not measuring it.

## Evidence

Plan `macos-loopback-hang-investigation` (2026-09-02, API-Sheriff), PR #243 (merged as
`5948962`), `doc/development/build-gate-discipline.adoc`.
