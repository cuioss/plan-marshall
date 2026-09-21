# PLAN-TRUTH-117: Restated counts and underived completeness claims

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-27 from the `lessons-handling-26-08-26-01` drain, message `-007` (7 lessons). This
class already carries a **standing rule** in the operator's memory corpus (*derive completeness, never
assert it*) and recurs anyway — which is the argument for a mechanical control rather than another
restatement of the rule.

## Objective

**A claim about a set — a count, a range, an endpoint, a partition, an `only` / `nothing` / `anywhere`
universal — is written as a rhetorical summary of what the author had in view, rather than derived from
an independent enumeration of the population.**

⭐⭐ **Two findings from the corpus change what the remedy must be, and both are established rather than
argued.**

**(1) Correction is not a remedy for this class; DELETION is.** `2026-08-09-13-001` records six
self-review rounds on a 19-file diff at 1,528,196 tokens, where **rounds 2–5 each found defects the
previous round's fix introduced** — four independent correction attempts, each holding the prior
finding, all failed. `PLAN-TRUTH-087` refined it: deleting *interior* prose silently **re-points
pronoun antecedents**, so the surviving text makes a new false claim nobody wrote. ⇒ Delete the claim
or open the enumeration; do not correct the number.

**(2) The corpus's prospective arm is NOT where this gets caught.** `2026-08-08-21-003` was **read,
cited by id, and violated in the same document** — a plan consulted it at outline, cited it inside its
own deliverable, and reproduced the archetype inside that deliverable. ⇒ **A deterministic sweep is the
control; the lesson is only the explanation of what to do once the sweep fires.**

## Deliverables

1. **D0 — GATE: derive the population.** Sweep for set-claims that are not backed by an enumeration.
   ⛔ **Publish the swept population and its size** — a plan about underived counts that reports an
   underived count is this epic's recurring self-reproduction, observed at least twice.
2. **D1 — an outline-time content sweep for the prior enumeration string.** When a widening changes a
   taxonomy from N to N+k, every site restating N is a finding. ⭐ `2026-08-08-21-003` records PR #1118
   growing a taxonomy 5→7 with **seven other sites across six documents** still asserting a number —
   **and not all the same wrong one**; one (*"two of the seven blocking members"*) was **never true at
   any point**, with the correct enumeration three lines above. ⛔ **The widening hunk PLANTS its own
   stale counts** — stale on arrival — so a drift check comparing against the current tree
   structurally cannot catch it. The sweep must key on the *prior* string.
3. **D2 — the vacuous-comparison topologies, which are NOT the same defect.** Two members are about a
   check's **shape**, not its population, and a population-derivation fix leaves them live:
   `2026-08-08-21-002` — *a count comparison whose two sides share a pivot proves nothing*, because a
   drift that moves the pivot moves both sides together; and `2026-08-09-22-003` — *two witnesses that
   share a bias are one witness*, where a shared bias is invisible from inside the comparison and the
   check **actively produces a reassuring result**. ⇒ Name both topologies in the standard and give
   each a detector or an explicit non-detectable note.
4. **D3 — hard-coded set-guarding literals.** `2026-08-08-20-001` finds four independent places in
   `plan-retrospective` where a set-guarding population is a hard-coded literal; **three of the four
   silently disable a check while its test stays green.** ⭐ Its most instructive detail: the test's
   anti-tautology reasoning was **correct** and still failed to bind, because it substituted the
   *standards document* for the *emitter* as its source of truth — **doc→regex and doc→test-literal is
   still a closed loop, just a three-node one.** Every set-guarding detector must be
   population-derived from the emitter; copy `test/_shared/_dispatch_roster.py`.
5. **D4 — the two remaining members, each with its own shape.** `2026-08-25-09-002`: five instances
   across three consecutive rounds **inside a self-review dispatcher's own replacement prose**, one of
   which survived two rounds because **two mistakes cancelled** and the arithmetic still summed.
   `2026-08-25-09-003`: a universal negative from a content search (*"no module imports X — zero hits
   across 5210 files"*) where the pattern matched **static imports only** and the documented loader uses
   `spec_from_file_location` — ⛔ **refuted by the very build the same commit cited as green evidence**,
   with the refuting mechanism named four lines above.

## Claim Labels

- OBSERVED: all seven instances, each quoted from a lesson recording a live run with its sites, counts and refutations
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Source lesson content is per-run and not independently reachable from this checkout
- OBSERVED: correction failed four consecutive times on one plan — `2026-08-09-13-001` enumerates the four attempts individually
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Source lesson 2026-08-09-13-001 is TOMBSTONED (removed 2026-08-27, superseded); survives only as quoted prose in the spec
- OBSERVED: `2026-08-08-21-003` was read, cited by id, and violated inside the citing deliverable
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Source lesson 2026-08-08-21-003 is TOMBSTONED (removed 2026-08-27, superseded); survives only as quoted prose in the spec
- HYPOTHESIS: an outline-time content sweep for the prior enumeration string is an effective control. ⛔ **It is the lessons' own proposal and has been neither built nor measured.** Confirm/refute by implementing it and measuring recurrence at the next widening (verify-at-outline)
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Spec own text: neither built nor measured -- the control is not implemented yet
- ⛔ **Counts in the source message are the filing plans' own and were NOT re-derived by the router** — treat them as a sample of the corpus, never an enumeration of it. D0 exists because of this.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-flagging methodology caveat about the router own sourcing, not a standalone checkable factual claim
- Verify-first clause: before scoping D2, settle whether the two topologies (shared-pivot, shared-bias) are mechanically detectable at all. If either is not, the deliverable is an explicit *"not detectable, review manually at these sites"* note — ⛔ **never a detector that cannot fail**, which would reproduce this epic's archetype inside its own remedy.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on D2 topology detectability; deferred to outline

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — the four hard-coded set-guarding literals (D3) (verify-at-outline)
- HYPOTHESIS: `test/_shared/_dispatch_roster.py` — the population-derived pattern to copy (expected READ-ONLY) (verify-at-outline)
- HYPOTHESIS: the outline-phase Q-Gate surface that would host D1's sweep — `marketplace/bundles/plan-marshall/skills/phase-3-outline/**` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/ref-documentation/**` or the governing standards home for the D2 topologies (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` — the enumeration-closure rule extended to defect-class closure and to dispatch-time deltas, added 2026-09-11 by the fold of `lessons-handling-26-09-04-01-053` and `api-sheriff-deployment-configurability-004` (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — the outline’s obligation to DERIVE a string-replacement affected-file list rather than assemble one, added 2026-09-04 by the drain fold of `documented-invocations-...-015` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-104` (empty-population verdicts) and `PLAN-TRUTH-116` (tests that cannot fail) — three sibling classes of the same theme, deliberately kept apart because their remedies differ. ⛔ Do not merge; DO cross-reference in the shipped docs.
- Adjacent to: `PLAN-TRUTH-112` (plugin-doctor rules that emit nothing) — D3's population-derivation rule is the same discipline applied to a different roster.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-117-restated-counts-and-underived-completeness-claims.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐⭐ FOLDED 2026-08-27 (landing #1359) — the through-line, filed by the run that produced it

From the `PLAN-TRUTH-098` landing drain (message `-009`), and it is this plan's central claim arriving
as first-party evidence rather than as corpus history.

**A doc-contract fix that RESTATES its authority reproduces the drift — delete and point.**

⭐⭐ **Four separate fixes in that ONE run each introduced a defect of the class they were fixing, all
doc-contract, and the convergent remedy in every case was DELETION PLUS A POINTER to the authoritative
source — never a corrected restatement.** That is a four-instance, single-run reproduction of the
finding this plan already carries from `2026-08-09-13-001` (four failed consecutive corrections) and
`PLAN-TRUTH-087` (deletion of interior prose re-points pronouns).

⇒ **The rule is now supported by two independent multi-instance runs**, and the remedy statement can be
sharpened from *"delete rather than correct"* to **"delete AND point at the authority"** — the pointer
is what stops the next author restating it again. ⚠ That is a stronger claim than the one this plan was
staged with; **D0 should verify the pointer half rather than inherit it**, since the corpus evidence
before this landing supported deletion without establishing that a pointer prevents recurrence.

## ⭐ FOLDED 2026-08-27 (landing #1361) — escalating literal matching to AST is still name matching

From the `PLAN-TRUTH-114` landing drain (candidate-lesson `-007`), and it is a rare thing: **an external
reviewer diagnosed a real methodological defect and reproduced its own class one rung up the ladder.**

CodeRabbit **correctly caught** a population derived by literal text matching (it had counted a comment
as a call) — then **proposed an AST count that misses an aliased import**. ⇒ ⭐⭐ **Name matching at a
higher rung is still name matching.** A derivation is only population-derived when it resolves what the
name BINDS TO, not when it parses the name more rigorously.

⇒ Sharpens this plan's D0/D3: *"derive the population"* must be stated as **derive it from the
resolver, not from a better parser of the identifier.** ⚠ **The remedy that looks strictly stronger can
carry the same defect**, which is why D0 must name the binding mechanism its derivation resolves
through rather than the syntax layer it parses at.

⚠ Adjacent from the same run: `2026-08-27-09-001` — a display-timezone helper-only guard **matches raw
file TEXT**, so a comment citing a helper name counts as reaching a timestamp. ⛔ **It carries a perverse
incentive worth quoting into the shipped doc: the cheapest way to make that guard pass is to DELETE THE
TRUE COMMENT.** A detector whose cheapest satisfaction is deleting accurate documentation is
mis-specified, not merely imprecise.

## ⭐ FOLDED 2026-08-31 — inbox drain (3 message(s))

- **`disjointness-gate-reads-declared-surface-wrong-001.md`** — A completeness claim about a semantic class cannot be discharged by enumeration or by string matching
- **`disjointness-gate-reads-declared-surface-wrong-002.md`** — A cardinality check cannot discharge a membership requirement
- **`findings-read-absent-plan-dir-returns-clean-zero-013.md`** — Five assert-completeness defects in one run, every one of them in prose written to correct earlier prose — and the converging fix was DELETE the cardinal, 5 out of 5 times

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-015`** — *the outline’s test-pin list was a SAMPLE presented as an enumeration: 1 named, 12 real.* Q-Gate `563f71`: **11 tests pin the OLD defective `generate.py --target claude` prescription**, across `test_content_drift.py` (2 sites) and `test_equality_check.py` (10 sites). ⛔ The finding names the archetype itself: *“the outline enumerated only ONE such pin and MISSED these eleven … it is the ‘a reviewer’s list of call sites is a SAMPLE, not an enumeration’ archetype, and the D0 test-pin sweep that produced the single-pin figure was itself incomplete.”* Prescribed remedy, verbatim: **“re-derive the test-pin population from source rather than from the outline’s list.”**

  ⭐⭐ **The same run demonstrates the CORRECT shape three times, and it is the shape this spec argues for: DELETE the count rather than re-count it.** `d00d72` — the “exactly one file / one path exemption” clauses were deleted and the comment now defers to the sibling sweep’s own `_EXCLUDED_PATHS` tuple as the authority. `8cc109` — an eleven-site enumeration was deleted from a module docstring: *“the guard derives its scope by walking `_SCAN_ROOTS`; a list copied into prose is a second unmaintained count, and what the guard covers is what it publishes at runtime.”* `6ff43a` — declined to add six duplicate path assertions precisely because *“duplicating six path checks there would be a second, unmaintained enumeration of a set the deliverable-4 guard already derives.”*

  ⭐ **The generalisable rule, and it is cheap:** an outline’s affected-file list for a **string-replacement** deliverable must be **derived by a content sweep at outline time** — one `architecture search --content` call whose clean-coverage fields (`files_scanned`, `unreadable`, `truncated`, `elided`) establish whether the count is a population or a lower bound. **Where the sweep cannot be run, the list must be LABELLED a sample in the outline, so execute knows to re-derive rather than to trust.**

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

**Theme 7's overclaim findings fold here, plus §3.2 and §8.5.**

⛔⛔ **§7.1 — the artifact written to codify overclaim-removal ITSELF overclaimed. 2 recurrences.** A plan existed to remove documentation overclaims; during finalize it authored two ADRs to **codify** that removal, and **each asserted a validation capability that did not exist** — no AsciiDoc processing in `pom.xml`, and the CI workflow skips documentation-only changes.

  ⭐⭐ **The defect is RECURSIVE and the diagnosis is the transferable part:** *"a normative document is written in the voice of the rule it WANTS, and the gap between the rule I want and the rule my mechanism applies is invisible from inside the document."* **The plan's gates were tuned to catch overclaims in the documents UNDER REMEDIATION; they did not look at the documents the remediation PRODUCED.**

  > **When a plan's purpose is to remove defect class D from document set S, every NEW document the plan authors is part of S for gating purposes** — ADRs, follow-up records, PR bodies included.

  ⛔⛔ **The recurrence extends the rule, and this half is the sharper one: NAMING A MECHANISM IS NECESSARY AND NOT SUFFICIENT.** A later ADR **named its enforcement registry and still overclaimed**, because naming a mechanism says nothing about its **scope**. ⭐ *"An explicit-list registry is the specific trap: it reads as complete because every entry in it genuinely IS enforced; what it cannot tell you is what is NOT in the list."* ⇒ **state the Decision with the mechanism's ACTUAL QUANTIFIER** — the rule holds *for registered entries*, with the unregistered residual stated. **Review trigger: any Decision sentence with an unqualified universal whose backing mechanism is ENUMERABLE.**

⭐⭐⭐ **§7.2 — a universal-quantifier claim is a CHECKABLE ASSERTION, and it is the best surfacer candidate in the document.** Javadoc claimed an allow-list applies *"in every pipeline"*. **False** — the header pipeline composes the stages differently. **Caught by a review bot; missed by pre-submission self-review, on a plan whose stated success criterion WAS documentation accuracy.**

  ⭐ *"A universal quantifier over a configurable composition is not prose: it names an ENUMERABLE POPULATION and asserts a property over it, and the pipelines are declared in code. It is mechanically falsifiable and needs no review judgement."* **Meets the existing surfacer criteria exactly**: deterministic (a regex over quantifier vocabulary — `every`, `all`, `always`, `never`, `any`, `no …`), **scoped** (text *this plan added*, bounded by the step's existing `--since-ref` anchor), and producing **a candidate, not a verdict** (*"name the population and confirm the property holds for every member"*).

  ⛔ **The failure mode is a specific authoring habit and it is INVISIBLE TO TESTS BY CONSTRUCTION:** the change is verified against **one** configuration and the documentation is then written from the author's mental model of it, **generalized** — *"the tests exercise the configuration the author was thinking about."*

- **§3.2 — the source report's named sites are the SEED, never the population.** A plan scoped to the sites a quality report named and **shipped a second live copy of the exact defect class it was fixing** — ⛔ *"the plan knew the wrong-RFC pattern and the right answer, and still left another instance in the corpus."* ⇒ **a report that under-enumerates propagates its blind spot straight through.** ⭐ *"When remediating a defect class that is characterisable as a pattern — a wrong citation, a stale count, a contradictory capability claim — the deliverable must include a CORPUS-WIDE CONTENT SWEEP. A defect class worth a deliverable is worth a `search --content` pass."*

- **§8.5 — scoping a fix around a named mechanism requires EXISTENCE **and** THREAT FIT.** A remediation was scoped as *"validate the redirect target through the currently configured `de.cuioss.http.security` pipeline"* — ⛔ **wrong on two INDEPENDENT axes, either of which alone would have wasted the fix task**: (1) **the mechanism does not exist** — no such pipeline is configured on that component, and the security pipelines are an *inbound* surface while the client is an *outbound* one; (2) **even if it existed it would not stop the attack** — those pipelines detect traversal and CVE patterns *within a path*, and the threat is an **egress host policy** question no path-matcher answers. ⇒ two separate pre-dispatch checks: **existence** (*"read the wiring, not the package name — a component in the same artifact is not evidence of configuration"*) and **threat fit** (*"name both explicitly: the mechanism detects X; the threat is Y"*). ⚠⚠ **Detection provenance is the worrying part: no script failure and no bot comment caught this. It was caught by the OPERATOR at dispatch review — the weakest possible surface for an error whose entire hazard is that it LOOKS RIGHT.**

## ⭐⭐⭐ FOLDED 2026-09-05 — PLAN-TRUTH-093 drain (3 messages). THE SPEC'S SUBJECT, THREE TIMES, INCLUDING ONCE BY A GOVERNING DOCUMENT.

### `preference-admissibility-...-001` — an anchor-driven sweep under-covers WITHIN its anchor, and its own coverage block cannot see the gap

⛔ **This is the worst shape in the family and the reason the spec exists.** A coverage block that
reports on the anchor rather than on the sweep INSIDE the anchor publishes a true statement that
answers a question nobody asked, and a reader has no way to tell it apart from real coverage. ⇒ **D0
must require a coverage claim to name the population it swept, not the population it selected FROM.**

### `preference-admissibility-...-004` — a corpus-health claim was propagated across SIX firings and ONE `get` refuted it

⭐⭐⭐ **The cheapest possible instance of this spec's archetype, and the most damning.** A finalize step
recorded that lesson `2026-09-04-13-001` had a title and an **empty body**. **False** — the lesson
carries a full ~1.5 KB body with four sections. ⛔⛔ **The claim was carried across SIX firings of the
housekeeping step and re-stated to the next step as established fact, and not one firing read the
lesson.** Refuting it cost a single `manage-lessons get`.

⭐ **The message's own guardable shape is the deliverable, and it is quotable verbatim:**

> *A corpus-health assertion naming a specific artifact id MUST be accompanied by the read that produced
> it. An assertion re-stated across firings without a fresh read is a rumour, not a finding.*

⭐⭐ **The sender then declined to assert that the corpus does not already cover this** — *"I did not
survey the 73-lesson corpus for it, and this message deliberately does not assert a clean negative."*
**That is this spec's own rule being obeyed by the message reporting a violation of it.** Keep the
sentence; it is a positive control.

⚠ **No remediation is owed on the lesson itself** — nothing is wrong with `2026-09-04-13-001`. Do not
re-open it.

### `code-intelligence-substrate-027` — a plan spec's own GATING DERIVATION made a confident absence claim that one read refutes

Forwarded to us by the sibling epic; **their finding, their corroboration, and they were right to send
it here.** `PLAN-CIS-054` § D6 states as settled fact, and as the premise for disarming a vacuous-pass
trap: *"That directory IS absent entirely."* ⛔ **At HEAD `28b578f1e` the directory is present and
populated** — three of its per-source-plan `gaps.md` files were `Read` directly and all three carry real
content. Independently corroborated by their own persisted ledger verdict at the same sha.

⛔⛔ **Blast radius, and it is why this is not a typo:** had D6 been executed as written (list the
directory; treat absence as `discharged-by-collection`), **roughly forty unexamined defects would have
been discharged as a clean pass over a directory that was never empty.**

⭐⭐ **This is the [Verify-First Contract's symmetric-obligation clause](../../persona-plan-orchestrator/standards/orchestration-model.md#verify-first-contract-for-inferred-claims)
earning its keep**: *an asserted ABSENCE is verified exactly as an asserted presence, and absence claims
are the higher-risk half, because nothing downstream trips over them.* ⇒ **D0's population must include
absence claims in governing documents, not only counts.** ⚠ Their stated root-cause hypothesis is
plausible and unverified: `.plan/local/` is git-ignored, so a fresh clone would not carry the directory —
**but the sentence was written as an unconditional fact about the tree rather than as a claim conditioned
on the checkout.** That conditioning failure, not the absence itself, is the defect shape.

⚠ **Expected Surface unchanged by this fold: it adds no file surface** — all three members are claims
about how evidence is asserted, and D0's sweep already owns the surfaces they sit on.

## ⭐⭐⭐ FOLDED 2026-09-06 — `review-apparatus-033` drain (1 item). THE PROMOTED RULE, INDEPENDENTLY REDISCOVERED.

### Item 7 (`-007`) — a correcting clause re-seeds the defect it corrects: DELETE instead

⭐⭐⭐ **A different plan, a different epic, a different run — and it arrived at the same terminating
move this epic promoted to the global corpus one day earlier** (`2026-09-05-16-001`, *replace a drifted
restatement with a POINTER at its declaring source; correcting it authors a new claim to audit*).

⇒ **Independent rediscovery is the strongest evidence a rule is real rather than one run's
rationalisation.** ⭐ Its framing adds a sharper third option this epic's version under-weighted:
**DELETE.** Our promoted rule offers *pointer* over *corrected restatement*; this one observes that where
no declaring source exists to point AT, **deletion beats correction** — because a correcting clause is
itself new prose with the same drift exposure as the clause it replaced.

⛔ **Do NOT re-promote it as a second lesson.** Fold it here as corroboration and, if the shipped doc
restates the rule, carry the delete arm alongside the pointer arm — **two arms of one rule, not two
rules.** A second corpus entry for the same rule would be the duplication this epic's own cleanup pass
exists to catch.

## ⭐⭐⭐ FOLDED 2026-09-06 (b) — THE ARCHETYPE RECURRED INSIDE ITS OWN FIX AGAIN, IN A FOREIGN JAVA REPO

From the same Java data-point. The reviewer *"found two genuine bypasses the plan's own tests missed, and
then caught that **my fix for one of them reintroduced the very asymmetry the plan existed to remove** —
`lenient()` reaching a different verdict than the defaults for the same input."*

⛔⛔ **This is the vacuous-guard / self-seeding archetype, and it is now confirmed OUTSIDE this
repository, in a different language, on a different subject.** Prior instances were all plan-marshall's
own: `-055`, `-075` (four times inside one guard across five rounds), `-089` (27% of 51 findings
self-seeded across five chains, one oscillating). **This one is Java, and the shape is identical.**

⭐⭐⭐ **The instance is unusually clean because the plan's PURPOSE names the defect its own fix
reintroduced.** A plan existing to remove an asymmetry, whose fix re-created that asymmetry at a
different entry point (`lenient()` vs the defaults, same input, different verdict). ⇒ **The archetype is
not a property of complex code or of this codebase — it is a property of fixing a class by patching an
instance.**

⛔ **And the plan's OWN TESTS missed both bypasses.** The catch came from the external reviewer. ⇒ **A
test suite authored alongside a fix inherits the author's model of the defect**, which is precisely the
model the defect escaped. **That is the argument for adversarial review independence** that
`PLAN-TRUTH-108` carries — arriving here as evidence rather than as reasoning.

⚠ **NOT staged as new work and NOT re-promoted.** The rule is already in the global corpus
(`2026-09-05-16-001`) and the archetype is already this epic's most-tracked. **Folded as the first
CROSS-LANGUAGE confirmation**, which is what it adds.

## ⭐⭐ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain (1 item). ONE MARKER, TWO POPULATIONS.

### `freshness-gate-...-003` — Worked and Wall totals print the same `(n=5/6)` marker over DIFFERENT phase sets

⛔⛔ **This is this spec's subject in its most compact form: a single coverage marker rendered beside
two figures whose populations are not the same set.** A reader takes `(n=5/6)` as one denominator
covering both; it covers each separately, over different fives.

⇒ **A coverage marker must name the population it qualifies, not merely its cardinality.** `5/6` and
`5/6` are indistinguishable when the two fives are different phases — **the cardinality matches and the
membership does not.** That is the same failure mode as this spec's `claimed_count` verification note:
**verify by MEMBERSHIP, never by cardinality.**

⚠ **The cheap fix is the wrong one**: printing two markers still leaves both unnamed. **The population
must be enumerable from the surface**, or the marker asserts a coverage a reader cannot check.

## ⭐⭐ FOLDED 2026-09-07 (b) — PLAN-TRUTH-099 drain (3 items). ONE IS A ONE-DAY-LATER CONFIRMATION OF YESTERDAY'S FOLD.

### `-011` — state WHICH phases an `(n=k/N)` total covers, not only how many

⭐⭐⭐ **This is the SAME defect folded here yesterday** from the `-128` drain (`Worked` and `Wall`
printing one `(n=5/6)` marker over two different phase sets) — **reported independently, one day later,
by a different plan.** ⇒ **Independent rediscovery within 24 hours**, which settles it as a property of
the marker rather than one run's rendering.

⛔ **And the two reports converge on the same remedy**: **name the population, do not merely count it.**
`5/6` and `5/6` are indistinguishable when the fives are different phases — **cardinality matches,
membership does not**, which is this spec's own verification rule turned on its own instrument.

### `-013` — re-check the NEIGHBOURS of a corrected guard for the same archetype

⭐⭐ **Corroborates the rule promoted to the global corpus on 09-05** (`2026-09-05-16-001`) from a third
direction: not *"the fix re-seeds the defect"* but *"the fix's NEIGHBOURS carry it untouched."* ⇒ **The
class-closure obligation is about the SIBLING SET, not only the edited site.** ⛔ Do not re-promote —
fold as a second arm of one rule.

### `-015` — check a doc-contract claim against the ON-DISK FILE, not the loaded skill body

⛔⛔ **A completeness claim verified against a CACHED artifact is not verified.** This is this spec's
subject at the reader's own instrument: the loaded skill body may lag the repository, so a claim
"confirmed" against it is confirmed against a snapshot of unknown age. ⭐ **This epic has a matching
first-party instance** — a seating claim derived from a session's own skill base directory that was
refuted by a dispatched envelope observing a different version. ⇒ **`D0` must state which artifact each
claim was checked against**; "verified" without a named substrate is the assertion this spec exists to
stop.

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (3 items, two repos, three new topologies)

### `-053` (Token-Sheriff) — fixing the CITED sites of a defect class is not closing the class

A review cited N sites of one defect class (DPoP / client-auth conflation). **Round 3 fixed the citations
and declared closure; round 4 fixed the newly-cited sites and declared closure again**; two further sites
survived outside the footprint. What established closure was an exhaustive
`architecture search --content` sweep over the class's signature, read under the complete-coverage
conjunction. ⇒ **A reviewer's citation list is a SAMPLE, never the population** — this epic's recurring
archetype, now stated for review-driven closure. The sender asks that it EXTEND the existing
enumeration-closure rule in `agent-behavior-rules.md` rather than sit beside it: that rule governs a
written enumeration; this one governs an implicit one (the set of sites exhibiting a defect). Remedy:
derive a signature, sweep the population, read the coverage fields, **report the swept population
alongside the fix count** so the closure claim carries its denominator.

### `-043` (Token-Sheriff) — an acceptance criterion whose total contradicts its own addends

The orchestrator's spec stated "ten glyph occurrences" while the per-file breakdown beneath it summed to
twelve; Q-Gate recounted (12 real + 23 harmless = 35, matching the occurrence count). A total and its
addends are one fact written twice, and nothing in authoring re-adds them. ⇒ **A new topology for D2:**
when a criterion states a count AND the deliverable enumerates the addends, the count must be DERIVED from
the enumeration, and re-derived when either side is edited — and a criterion is a gate, so a wrong total
makes the gate assert the wrong thing.

### `api-sheriff-deployment-configurability-004` (range half) — a delta handed to an agent is recollected, not computed

Twice in one run a reviewer was handed a hand-written "commits since your last verdict" list; both lists
contained **ancestors of the review anchor**. The reviewer caught it both times by re-deriving — which
means the briefing was wrong twice. Rule: a commit range is computed — `git -C {tree} log --oneline
{anchor}..{head}` — and the same applies to every **delta handed to another agent as context** (files
changed since review, findings outstanding since a triage pass, tasks remaining): compute it from the
authoritative store at dispatch and paste the computed output; never summarise it from session memory or
carry it forward from an earlier message, whose anchor has since moved. OBSERVED UNTRACKED: no such rule
exists; `persona-plan-marshall-agent`'s `agent-behavior-rules.md` uses `git log` only to decide whether a
branch touched a failing test. (The message's footprint half is forwarded to `code-intelligence-substrate`
for `PLAN-CIS-050` D7, not folded here.)

⇒ **Three topologies, one rule**: a review closure, a criterion total, and a dispatch-time delta are each
a set claim written from what the author had in view. Expected surface gains the persona home for the
delta rule.

### Claim labels for this fold

- HYPOTHESIS: `agent-behavior-rules.md` carries no dispatch-time delta-derivation rule — confirm/refute at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` § the enumeration-closure rule (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-153-tests-fixtures-and-detectors-that-cannot-fail-and-underived-completeness-claims.md` (PLAN-TRUTH-153)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
