envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:46Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# Findings triage: a zero reported over one type still ships in a clean-path log line, and no triage axis asks whether a finding's stated premise is true

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Two lessons filed in **API-Sheriff's**
store, whose repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11.

Origin ids: `2026-09-02-22-005` (created 2026-09-02), `2026-09-10-22-002` (created 2026-09-10).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| finalize reported "zero pending findings" after querying only `pr-comment` + `sonar-issue` while 37 `build-error`/`test-failure` were pending | GATE FIXED by #1199 (2026-08-13) | `branch-cleanup.md:713-719` runs `phase_handshake findings-check` over every actionable type incl. build-error / test-failure / qgate (`_invariants.py:1297,1488`); `6-finalize` completion refused while any pend (`_cmd_lifecycle.py`); `manage-findings list --include-qgate` is the unified read (`manage-findings/SKILL.md:177`) | shipped |
| residual: the clean-path message still states a zero over ONE type | STILL-VALID (minor) | `branch-cleanup.md:1052` logs "zero pending pr-comment findings" — the exact shape the lesson's directive 3 names ("say what you queried whenever you report a zero"), now harmless to the gate but still a reader-facing zero without its population | none found |
| a review finding can be right about the fix and wrong about the reason; triage should record both axes ("accepted — correct fix, incorrect premise") | STILL-VALID, **UNTRACKED** | no two-axis disposition in ext-triage, verification-feedback or finalize triage docs | nearest: queued `lessons-handling-26-09-04-01-030` (spec claim asserted from memory) — related, different |

**What this message adds:** the `branch-cleanup.md:1052` wording residue, and the two-axis triage rule
in full. Suggested remedy for the latter: a triage disposition that carries `fix_correct` and
`premise_verified` separately, so an adopted finding with a false premise is recorded as such and its
premise does not enter commit messages and replies as accepted fact.

---

## Original lesson `2026-09-02-22-005` (verbatim)

id=2026-09-02-22-005
component=findings-triage
category=anti-pattern
status=active
created=2026-09-02

# Zero pending findings is only true over every blocking type - enumerate them, do not sample

## Observation

Twice during this plan's finalize the orchestrator reported **"zero pending findings"** on the
strength of two queries: `--type pr-comment` and `--type sonar-issue`. At that moment **37 pending
findings existed** — `build-error` and `test-failure` records filed earlier in the run. The triage
agent caught it; nothing else would have.

The report was not a lie about the data returned. Both queries were accurate. The failure is that a
query over *some* blocking types was reported as a verdict over *all* of them, and the resulting
sentence — "zero pending findings" — is indistinguishable from a true one.

## Why it happens

The types queried were the types the *current dispatch* had produced. That is the trap: the natural
query set is "what did I just do", while the gate's question is "what is outstanding across the
whole plan". Those coincide on every run where nothing earlier went wrong, which is exactly the set
of runs where the check does not matter.

## Directive

1. **A zero-findings claim must be computed over the full blocking-type set, never over the types in
   front of you.** Enumerate the types explicitly, from the taxonomy rather than from memory:
   `bug`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment` — plus the
   pending Q-Gate slice.
2. **Prefer the query that cannot under-cover.** A single unfiltered `list --resolution pending
   --include-qgate` answers the gate's real question in one call; a per-type sweep re-introduces the
   omission risk on every edit to the type set.
3. **Say what you queried whenever you report a zero.** "Zero pending across
   {enumerated types}" is checkable by the reader; a bare "zero pending findings" is not, and the
   difference is what let this pass twice.
4. **Read the store-state discriminator too.** A zero from an unresolved or absent store is not a
   clean zero — `manage-findings` publishes `findings_store_state` precisely so a count is never
   read without the substrate it came from.

## Evidence

Two occurrences in one finalize run on plan `configurable-context-path`; 37 pending `build-error` /
`test-failure` findings outstanding at the time of both reports; detected downstream by the triage
pass, not by the reporting path itself.

---

## Original lesson `2026-09-10-22-002` (verbatim)

id=2026-09-10-22-002
component=findings-triage
category=anti-pattern
status=active
created=2026-09-10

# A review finding can be right about the fix and wrong about why - verify its premise before adopting it

## Observation

A Q-Gate finding (`99ac34`) asked for a discriminating assertion in place of an existing
absence-assertion. The requested change was the right change. The **reason** the finding gave for it
was false.

The finding argued that the existing assertion "holds under every trust posture" — i.e. that it
would pass whatever the code did, and so proved nothing. That is the classic vacuous-assertion
shape, and it is a shape worth acting on. But it was not this assertion's shape: the absence being
asserted **is** discriminating here, because the artifact is regenerated per posture, so a wrong
posture produces a present value where absence was asserted and the test goes red.

So the finding was adopted on its conclusion while its stated mechanism was wrong.

## Why this is worth a rule

Adopting a finding without checking its premise costs more than the wasted verification:

- **The wrong premise propagates.** The commit message, the PR reply and the review thread all
  restate the finding's reasoning. A future reader learns "absence-assertions here are vacuous",
  which is false, and may go on to delete or weaken other absence-assertions that are in fact
  load-bearing.
- **You cannot tell a right-for-the-wrong-reason finding from a wrong one without doing the same
  work.** If the premise had been the only thing supporting the conclusion, and the premise is
  false, the conclusion had no support — the fix would have been churn. Here the conclusion happened
  to be independently justified. Nothing in the finding said which case you were in.
- **Automated reviewers state mechanisms confidently.** A bot's finding reads as an analysis result
  when it is frequently a pattern match with a generated rationale. Confidence in the prose is not
  evidence about the code.

## Directive

1. **Triage a review finding on two axes, not one: is the requested change right, and is the stated
   reason true?** Record both. The disposition "accepted — correct fix, incorrect premise" is a
   first-class outcome and is more common than it looks.
2. **Open the mechanism the finding describes before restating it.** A premise of the shape "this
   assertion holds under every X" is falsified or confirmed by reading the code under one non-default
   X. That is minutes, and it is the whole verification.
3. **When you adopt a finding whose premise is wrong, say so in the reply and in the commit
   message.** The correction is the durable part — it stops the false mechanism entering the record
   as accepted fact, and it tells the reviewer's operator that the rule misfired here.
4. **Never generalise a finding's premise to sibling code.** A premise you did not verify is not a
   licence to change the neighbours.

Related: `2026-09-02-22-002` is the same discipline applied to prose that *asserts* a mechanism;
this lesson applies it to prose that *demands a change on the strength of* a mechanism. Both reduce
to: open the file the claim depends on.
