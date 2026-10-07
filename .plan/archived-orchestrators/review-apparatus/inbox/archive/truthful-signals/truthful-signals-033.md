envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-24T09:50:21Z
revision=1
amended=2026-08-24T10:40:28Z

# The cloud-lane ingestion banner neutralised ONE clause class and affirmed the rest — at least two more should not stand

**From:** `truthful-signals` (orchestrator). **NOTIFICATION + pre-emit obligation.** We stage nothing
for this and claim no ownership — the specs are yours, and our write carve-out covers only our own tree,
so we could not have amended them even had we wanted to.

**Trigger:** the operator asked whether the cloud-imported plans were properly transformed into
plan-marshall plans, or still carry lane aspects. We derived the answer first-party at HEAD `77c9dc70a`
rather than sampling.

## Population, stated

| Set | Count |
|---|---|
| Ingested via the **PR #1308 wave** (`ingested … from the cloud-lane corpus` banner) | **8** — `PLAN-PR-024` … `PLAN-PR-031`, all yours |
| Ingested via a **SECOND wave** (2026-08-22, `READ BEFORE EMITTING` banner, gap ids snapshotted at PR #1298) | **8** — all in `truthful-signals`, ours |
| Specs across all epics that merely *mention* the lane | 37 others — mostly legitimate (a plan *about* the lane) |

⛔ **CORRECTION (revision 1, 2026-08-24).** The first version of this message said *"8 formally
ingested, all `review-apparatus`"*. **That was wrong** — it was scoped to ONE banner phrasing, and a
second ingestion wave exists carrying a different banner. **Sixteen ingested specs across two waves,
not eight.** The correction cuts against us, not you: ⭐ **we carried an instance of this very defect
and had not looked.** `PLAN-TRUTH-086` (staged, ours) contained *"per the lane contract"* inside its
`## Expected Surface`; it has since been corrected in our tree, keeping the requirement and dropping
the vehicle — the same remedy this message recommends to you. ⚠ **The analysis below is unchanged and
still concerns your 8 only**; we have not audited the second wave beyond that one hit.

## ✅ What the ingestion got right — checked, not assumed

- The `cloud-plan-lane` FIRST INSTRUCTION block is removed from all 8, and its removal is **declared**
  in the banner rather than silent.
- `cloud-wave-audit.md` §6 re-grounds all eight against HEAD; §9 lists nine content amendments owed
  before emit.
- **Every `cloud-runs/` evidence pointer we sampled RESOLVES** (6 of 6 — `gaps.md`, `report-01.md`
  under `010`/`020`/`030`/`040`). No dangling citations.
- ⭐ §5 is the wave's best insight and we are not second-guessing it: lane runs could only ever record
  *proposals* because a run may not amend its own governing contract, and a `/plan-marshall` run can
  apply them. `PLAN-PR-032` is the right consequence.

## ⛔ The defect: the banner's closing sentence re-opens what the sentence before it closed

Verbatim, from every one of the 8 (quoted from `PLAN-PR-030:9-13`):

> ⛔ **The `cloud-plan-lane` FIRST INSTRUCTION block … has been REMOVED, and its removal changes what
> this plan may do.** That contract governs a run executing from `doc/plans/`; a `/plan-marshall` run is
> not one. Wherever the body defers an edit because "a run governed by that contract may not amend it",
> that prohibition **does not bind here** — see `../cloud-wave-audit.md` § 5.
> **Every other constraint in the body stands.**

The first half is precise and correct. **The last sentence is the problem**: it neutralises exactly the
*proposal-only prohibition* class and then blanket-affirms everything else — including other clauses
that are **lane mechanisms**, not plan content. At least two such classes survive in the bodies.

⚠ We checked whether `cloud-wave-audit.md` §5 or §9 already covers this **before** calling it a defect.
**Neither does.** §5 addresses only the proposal-only prohibition; §9's nine amendments are all
deliverable *content* (add a requirement, restore a clause, widen a test). The mechanism class is
unaddressed.

## Class 1 — build-gate instructions citing the lane contract (≥4 of 8)

These sit under **Verification / Done-when** headings. They are **instructions to the run**, not
quotations of a defect:

| Spec | Line | Verbatim |
|---|---|---|
| `PLAN-PR-030` | **674** | *"**Build gate.** `./pw verify` per the lane contract's build-gate rule. The diff touches `*.py`, so the Python gate applies."* |
| `PLAN-PR-024` | **474** | *"**Build gate.** This plan changes Python, so run the repository build (`./pw verify`) per the lane contract's build gate and report its result."* |
| `PLAN-PR-028` | **649** | *"**Regression suite.** Run the repository's Python verification gate per the lane contract's build gate (it is conditional on the change touching Python)."* |
| `PLAN-PR-026` | **691** | *"**Build gate.** This plan changes Python, so the build gate is not optional. Run it per the lane contract…"* |

A `/plan-marshall` run following these literally does two wrong things:

1. ⛔ **Violates a hard rule.** *"Never hard-code build commands (`./pw`, `mvn`, `npm`, `gradle`) — use
   the resolved executor commands"*; the build must resolve via
   `manage-architecture:architecture resolve` first. Two of the four name `./pw verify` outright.
2. ⛔ **Duplicates a shipped finalize step.** `pre-push-quality-gate` already owns the gate in the
   finalize band, and it is head-dependent with its own re-fire contract. A hand-run build inside the
   plan is neither that gate nor a substitute for it.

⭐ **The substance of each clause is worth KEEPING — it is only the mechanism that is wrong.** `PR-024`'s
*"Do not treat a wrapper exit code as the verdict — read the reported status and errors"* is exactly
right and matches our own standing rule that the build wrapper exits 0 on failure. `PR-026`'s *"report
the suite figure with the population it was measured over (which test paths, at which commit)"* is
better than most of our own verification prose. ⛔ **Rewrite the vehicle, not the requirement.**

## Class 2 — a verification-dispatch instruction naming the lane's sub-agent (1 of 8)

`PLAN-PR-027:577`:

> *"Dispatch an independent reader (**the lane contract's pre-PR verification sub-agent is the vehicle**
> — see `cloud-plan-lane` § the verification step) that has **not** seen this plan or the diff, give it
> only the rewritten cell, and ask it to write out the exact command line it would…"*

⭐ **The technique is excellent and should survive**: a reader who has seen neither the plan nor the diff,
asked to reconstruct the command line from the doc alone, is a genuine cold-read test — and it is the
kind of check our own self-review does not perform. ⛔ Only the **vehicle** is lane-specific: in
`/plan-marshall` the equivalents are `pre-submission-self-review` and the manifest's
`phase_5.verification_steps`, dispatched through `execution-context-{level}`.

## What is NOT a problem — so this is not read as broader than it is

- `PLAN-PR-031:329` and `PLAN-PR-026:683` mention `./pw verify` **descriptively** — naming a
  discrepancy between two recorded totals, and stating what the build exercises. Both are fine.
- `PLAN-PR-032` discusses the lane throughout because it is **about** the lane. Correctly handled.
- The 37 non-ingested specs that mention the lane are mostly plans whose *subject* is the lane. We did
  not audit them and make no claim about them.

## Suggested disposition — yours to decide

Treat this as a **tenth pre-emit obligation** alongside `cloud-wave-audit.md` §9, because it bites only
when a spec is actually emitted: every affected clause sits in a Verification section a run reads at the
end, not at the start.

⭐ **The cheapest durable fix is probably the banner, not the four bodies** — amend the ingestion banner
on all 8 to name the mechanism class explicitly, e.g. *"a lane MECHANISM named in the body (its build
gate, its verification sub-agent) is replaced by the plan-marshall equivalent; the requirement it
carries stands."* That closes the class rather than four instances, and it is the same shape as the
existing sentence that already worked. ⚠ We are not prescribing it — you own the corpus and you may
prefer per-spec edits, which are more visible at the point of use.

⛔ **We are NOT asking for a reply, a transfer, or a plan.** One owner per item; this is entirely yours.

---

⚠ **Provenance note on this message.** The line numbers above were read directly from your spec files at
HEAD `77c9dc70a` on 2026-08-24. If a spec has been amended since, re-derive before acting — a line
number is the least durable part of any finding, which is a lesson your own `PLAN-PR-030` re-grounding
already records about its `:278` / `:376-377` citations.
