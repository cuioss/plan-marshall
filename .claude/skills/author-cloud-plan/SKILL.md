---
name: author-cloud-plan
description: Authoring judgement for a cloud plan under doc/plans/ — the rules an orchestrator applies when writing a plan that must survive a runtime with no operator, no ledger visibility, and no way to ask a question. Load when authoring a doc/plans/{epic}/ plan; the mechanics — naming, plan shape, the run contract — live elsewhere and are pointed to, never restated.
user-invocable: true
mode: workflow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, Skill, AskUserQuestion
---

# Author a cloud plan

The judgement an orchestrator applies when turning an epic's staged work into a **cloud plan** under
`doc/plans/{epic}/`. Two different actors touch a cloud plan at two different moments: the **cloud
session that executes** it loads [`cloud-plan-lane`](../cloud-plan-lane/SKILL.md), 750 lines of
execution contract, as its first action. The **orchestrator that authors** it — locally, where both
trees are visible — is the actor this skill is for.

A cloud plan is executed by a runtime with three properties an ordinary task does not have: it
**cannot see `.plan/`** (git-ignored, so the orchestrator ledger, the plan specs, and the landing
records are absent from its clone), it **has no operator** (it cannot ask a question or wait for an
approval mid-run), and its **working state dies with its VM** (git is the only durable channel). A
plan authored without those three in mind ships work that stalls, sends the run to a path it cannot
reach, or bakes in a fallback that defeats its own purpose. That judgement was paid for by the cloud
plans run so far; this skill is where it lives so the next author does not rediscover it.

## When to load

Load this while **authoring** a cloud plan — the [`cloud-bridge.md`](../../../doc/plans/cloud-bridge.md)
§ Path 1 create step, done locally. It is not loaded by the run: the run loads `cloud-plan-lane`, and
loading authoring guidance into every cloud run would spend context on guidance the run can never use.

## Boundary — what this skill owns, and what it does not

This skill carries **only** judgement that has no home elsewhere. The mechanics of a cloud plan —
what it is named, what shape it takes, how the run executes it — are already owned, and are pointed
to rather than copied. A restated rule is a second place to look and a second thing to drift; it is
the defect this boundary exists to prevent.

### OWNED-ELSEWHERE

Each entry names the file that owns it. **None of these is restated as a rule below** — where the
judgement touches one, it points here and adds only the cloud-specific increment.

- **Naming a cloud plan** `{NNN}-{orchestrator-slug}.md`, and the `{NNN}-` priority-prefix rules
  (numbered per epic from `010`, sparse in tens, fixed once handed to a session, prefix kept through
  the lifecycle; pre-scheme plans keep no prefix) — `doc/plans/cloud-bridge.md` § Path 1.
- **The derive-from-spec order** (pick a staged plan → read the orchestrator spec → author from the
  template → commit and push) — `doc/plans/cloud-bridge.md` § Path 1.
- **The carry-across set** from the orchestrator spec (problem and mechanism, deliverables,
  out-of-scope, expected surface, every claim label; a `HYPOTHESIS` stays a `HYPOTHESIS` with its
  artifact) — `doc/plans/cloud-bridge.md` § Path 1 step 3.
- **Do not delete the orchestrator spec**; it stays as the source record — `doc/plans/cloud-bridge.md`
  § Path 1 step 4.
- **The plan must reach `origin/main`** before a cloud session can see it —
  `doc/plans/cloud-bridge.md` § Path 1.
- **The plan's shape** — the sections a plan has (Problem, Goal, Deliverables with a *done when*,
  Out of scope, Expected surface, Claim labels, Verification, Notes) and the six-deliverables-is-a-
  split heuristic — `doc/plans/_template/plan.md`.
- **The mandatory first-instruction block** that loads `cloud-plan-lane` before anything else —
  `doc/plans/_template/plan.md` (and `doc/plans/README.md`).
- **The claim-label mechanics** — `OBSERVED`/`HYPOTHESIS` on every premise, a named confirm/refute
  artifact per claim (required for a `HYPOTHESIS`), and "an asserted absence is verified exactly as an
  asserted presence, and is the higher-risk half" — `doc/plans/_template/plan.md` § Claim labels.
- **The out-of-scope section and its generic reason** ("an explicit boundary here is what stops scope
  drift mid-run") — `doc/plans/_template/plan.md` § Out of scope.
- **The whole execution contract** — skill loading, the plan-directory lifecycle, the build gate, the
  pre-PR verification sub-agent's dispatch, the branch/PR/review cycle, the merge gate and its
  shortfall disclosure, the report, and the closing self-check — `.claude/skills/cloud-plan-lane/SKILL.md`.
- **The run-side re-derivation rule** ("a count derived by looking is a sample… re-derive it at the
  moment of the claim") and the **run-side self-approval prohibition** ("never self-approve a change
  to the contract that governs you") — `.claude/skills/cloud-plan-lane/SKILL.md`.
- **The tree layout** and the status-is-the-filesystem model — `doc/plans/README.md` and
  `doc/plans/cloud-bridge.md` § Status vocabulary.

### REMAINDER — what this skill owns

The authoring judgement, and nothing that is owned above:

- **Self-sufficiency of the plan text** — restate everything the run needs inside the plan, because
  `.plan/` is invisible to the clone; a machine-local path may be named only to tell the run *not* to
  look for it.
- **The no-operator constraint on deliverable design** — no deliverable may be authored to require a
  mid-run decision; anything needing a decision is authored to *record a proposal*, never to decide.
- **Stop-condition deliverables** — where scope rests on a premise being derivable, author the
  derivation as the gating deliverable and have it HALT, rather than author a fallback to a
  hand-maintained artifact.
- **Cold-read verification** — where a deliverable's value is what its text makes a later reader *do*,
  author the plan to verify it by an independent cold read that reports which reading it took.
- **Evidence lives in the clone** — the cloud increment on the claim-label mechanics: a claim's
  confirm/refute artifact must be git-reachable, and an asserted absence is the highest-risk claim in
  a cloud plan specifically.
- **A count is authored as a lead** — the authoring counterpart to the run-side re-derivation rule.
- **Out-of-scope's reason is load-bearing here** — the cloud increment on the out-of-scope section:
  with no operator watching, the written boundary is the *only* thing that stops mid-run drift.

The subtraction leaves a real remainder: the four rules that open § The judgement (self-sufficiency,
no-operator, stop-condition, cold-read) are owned by no other file, and each is drawn from something a
cloud plan actually had to do by hand. This is not a pointer-shaped skill — if a future subtraction
ever thins the remainder to pointers, the honest move is to delete this skill, not to pad it.

## The judgement

Each rule states its **grounding** — what happened that produced it — because a rule without its
evidence is indistinguishable from a preference, and the first thing a later author will want to know
is whether it was earned. The grounding is the two cloud plans run so far: plan `010`
("cloud lane merges on unverified review coverage", PR #1112) and the plan that created this skill.

### 1. Self-sufficiency: the plan is the whole brief

`.plan/` is git-ignored, so the orchestrator ledger, the plan specs, and the landing records are
**absent from the clone the run executes in**. A plan that cites any of them as required reading sends
the run somewhere it cannot go. So: **restate inside the plan everything the run needs.** A
machine-local path (`.plan/local/orchestrator/…`, a landing record) may appear **only** to tell the
run not to look for it — never as a source it is expected to open.

*Grounding.* Plan `010` needed its source incident's landing analysis
(`.plan/local/orchestrator/…/landings/PLAN-CIS-021.md`). It restated everything it needed in its own
Notes and wrote, in the plan: "machine-local and NOT visible from a cloud session … do not go looking
for it." That worked — but it was written by hand, from judgement no skill carried. This rule is that
judgement.

### 2. No operator: no deliverable may need a mid-run decision

A cloud run has no operator to ask. It cannot pause for an approval, cannot resolve an ambiguity by
checking, cannot be told "yes, ship it." So **no deliverable may be authored such that completing it
requires a decision the run cannot make.** Where a decision is genuinely needed, author the
deliverable to **record a proposal for the operator**, not to make the call. A change to a governing
contract is the sharp case: it is never authored as "the run amends the contract."

*Grounding.* Plan `010`'s run discovered mid-execution that the lane forbids self-approving a contract
change; it correctly **recorded three contract proposals instead of shipping them**. A plan whose
deliverable had *required* that decision would simply have stalled, with no operator to unblock it.
Author the recording, not the decision, from the start.

### 3. Stop-condition deliverables: derive-or-halt, never fall back to hand-maintenance

When a plan's scope rests on a premise that must be **derivable** — a population read from
configuration, a set computed from the tree — make that derivation the **first, gating deliverable**,
and author it to **HALT the plan** if the premise fails. Do **not** author a fallback that
hand-maintains the artifact the derivation was supposed to produce: a hand-maintained list is usually
the very defect class the plan is closing, so the fallback would reproduce it inside the fix.

*Grounding.* Plan `010`'s D0 was written as a stop-condition: derive the expected reviewer population
from the machine-readable registry, and "if the population cannot be derived from configuration, say
so and stop." It paid off — the population *was* derivable, so the run never wrote the hand-maintained
fallback that would have reproduced the defect. The stop-condition is the guard that makes the
premise safe to build on; a plan that merely *hopes* the premise holds has no such guard.

### 4. Cold-read verification: for text whose value is what a reader does with it

Some deliverables are **text whose whole value is the behaviour it produces in a later reader** — a
gate rule, a disclosure clause, a contract paragraph, a skill like this one. "Implemented as
specified" cannot verify such a deliverable: the text can be present, well-formed, and still read the
wrong way. Author the plan's Verification to **have an independent reader take the text cold and report
which reading it took.** If the reading is wrong, the wording failed, however complete it looks. The
lane's pre-PR verification sub-agent (`cloud-plan-lane` § Step 6) is the dispatch vehicle; this rule
is the authoring choice to *aim it at interpretation*, which the default "verify against requirements"
pass does not do.

*Grounding.* Plan `010`'s D2 changed the merge gate to **disclose** a review-coverage shortfall rather
than **block** on it — a distinction a later reader must not collapse. Its Verification had a sub-agent
read the new text cold and state which it was; the cold read returned **DISCLOSE**, which is the only
check that tests the thing that actually matters. Note the trap this skill's own author must avoid: a
skill *is* a text-that-drives-a-reader deliverable, so authoring it without a cold read is this rule
applied to everything except itself.

### 5. Evidence lives in the clone (self-sufficiency, applied to claim labels)

The claim-label mechanics are owned by the template (§ Boundary → OWNED-ELSEWHERE): the label, the
named artifact, and the rule that an asserted absence is verified as a presence. The **cloud increment**
is a single constraint the template does not carry: a claim's **confirm/refute artifact must be
reachable from the clone** — a git-tracked file, a directory listing, a commit — never a `.plan/` path
or a machine-local record the run cannot open. And the **asserted absence** ("X does not exist, build
it") is the highest-risk claim in a *cloud* plan in particular: the run cannot browse `.plan/` or ask
the operator to sanity-check a "does not exist", so an unverified absence sends it to build something
that may already exist, with nothing positioned to catch it.

*Grounding.* This plan's own scoping premise was the asserted absence "`.claude/skills/` holds N
skills and none covers cloud-plan authoring", with a **git-visible** artifact (a directory listing) and
an instruction to re-derive it. Had the artifact been a `.plan/` record, the run could not have settled
the premise at all.

### 6. A count is authored as a lead

`cloud-plan-lane` owns the run-side rule that a count is re-derived at the moment of the claim. The
**authoring counterpart**: never write a trusted number into the plan. Write the count with the
instruction to **re-derive it**, because the clone the run sees is not guaranteed to match the tree the
author saw — a skill added or removed between authoring and execution silently invalidates a baked-in
number.

*Grounding.* This plan labelled its one count with an explicit **re-derive it, do not trust this
count** instruction; plan `010` labelled the `1 of 3` coverage figure, the reviewer population, and
its section enumeration all as leads. Every count that mattered was authored to be recomputed.

### 7. Out-of-scope names why — the only drift-stopper when no one is watching

The template owns the out-of-scope section and its generic reason (§ Boundary → OWNED-ELSEWHERE). The
**cloud increment** is *why the reason is load-bearing here*: in a local run the operator is a
backstop against scope creep, but a cloud run has none. The **written** out-of-scope boundary, each
entry carrying the reason it is excluded, is therefore the *only* thing standing between the run and
mid-run drift. An out-of-scope list without reasons is an assertion; with reasons it is an argument the
run can hold the line against a tempting adjacent change with.

*Grounding.* Plan `010` excluded "blocking a merge on bot participation" and named why (rate limits
are routine; blocking would strand landings); this plan excluded merging authoring into
`cloud-plan-lane` and named why (every cloud run would then load guidance it can never use). In both,
the *reason* is what makes the boundary defensible mid-run, not just declared.

## Authoring order, and the self-check

Author in the order § Path 1 sets (derive from the orchestrator spec, carry the labels across), and as
you write, apply the seven rules above. Before the plan is handed over, read it back once against this
skill:

- Does any deliverable cite a `.plan/` path as a source to open, rather than as a thing not to look
  for? (Rule 1)
- Does any deliverable need a decision the run cannot make? (Rule 2)
- Does any premise the scope rests on lack a gating, halting derivation? (Rule 3)
- Is any deliverable a text-that-drives-a-reader with no cold read in its Verification? (Rule 4)
- Does any claim's artifact live somewhere the clone cannot reach, and is every asserted absence
  verified? (Rule 5)
- Is any count written as a trusted number rather than a lead? (Rule 6)
- Does any out-of-scope entry state *that* it is excluded without stating *why*? (Rule 7)

A "yes" to any is a defect to fix before hand-over — there is no operator downstream to catch it.
