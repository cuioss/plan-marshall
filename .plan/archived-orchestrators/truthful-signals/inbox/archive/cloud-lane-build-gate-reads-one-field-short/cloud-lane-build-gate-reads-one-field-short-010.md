envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=landing
created=2026-08-23T22:16:26Z

# PLAN-TRUTH-075 landed — PR #1336, main `77c9dc70a`

**Plan**: `cloud-lane-build-gate-reads-one-field-short`
**Spec**: `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-075-cloud-lane-build-gate-reads-one-field-short.md`
**Merged**: PR #1336 via merge queue, squash. Verified from PR state (`state: merged`), not from a
landing message.

## What shipped

One deliverable. The run-report template's `## Build gate` block now quotes Step 5's normative skip
phrase `"no buildable footprint, build skipped"` instead of its own divergent
`"no Python changes, build skipped"`. Step 5's trigger table is the source of truth and was not edited.

A new pytest guard (`test/pm-plugin-development/cloud-plan-lane/test_build_gate_lockstep.py`,
**10 tests**) parses both surfaces out of the document and fails when they disagree.

Also shipped: a one-line macOS fix to `test_qgate_closure.py` (out of scope, fixed because it made a
green coverage run unobtainable on any Mac) and an architecture descriptor refresh.

## Three of four deliverables closed WITHOUT a code change

See sibling message `-009.md` for the full evidence. Summary:

- **D0** — settled by CODE READ: the build wrapper structurally cannot emit a green `status` with a
  non-empty `errors[]`. This is the claim the spec named as its discriminator gate. **Answered.**
- **D1** — both cited gate sites already require an empty `errors[]`. No edit owed.
- **D2** — already shipped by `2cbcb1f30` / #1299. ⛔ **The chronology in this plan's own outline and
  in both phase summaries is BACKWARDS**: #1299 landed 2026-08-18, **nine days AFTER** the 2026-08-09
  staging. Diagnosis is **queue latency**, not stale ingest.

⭐ **Epic implication**: a staged spec must be re-grounded against HEAD at execution start. Refine's
source-premise check did exactly that and is why three deliverables closed without touching a file
two other plans also claim.

## The defect cascade — five rounds, same archetype, each one level deeper

The guard built to prevent n−1-of-n **reproduced n−1-of-n four times inside itself**:

| Round | Found by | Defect | Resolution |
|---|---|---|---|
| 1 | self-review r1 | glob pinned at 2 of 4 sites; docstring said "twice" | `9b0558334` |
| 2 | self-review r2 | population check was non-emptiness → 2→1 shrinks silently | `e5cadb886` |
| 3 | simplify (outside its remit) | skip row bound POSITIONALLY while docstring claimed semantic | `cd5135b57` |
| 4 | sourcery on the PR | the REPORT surface still bound positionally — same defect, other surface | `f41d4cdaf` |
| 5 | sourcery on the PR | the cardinality floor cannot detect a marker SWAP | accepted, rationale recorded |

⭐ **Round 4 is the sharpest**: my first fix for it (block-wide uniqueness) was **wrong**, and the
tests caught it — the block legitimately quotes a second phrase in its stale-base paragraph, so
uniqueness fails on a *correct* document. The landed fix scopes the binding to the verdict sentence's
paragraph.

Guard grew 4 → 10 tests. Every fix carries a matched negative control; two of them are red against a
first-match binding.

## Review reality

- **sourcery — an OPTIONAL bot — produced BOTH actionable findings.**
- **pr-agent — the REQUIRED bot — produced one content-free comment** ("No code suggestions found").
  Quorum passed on it alone. Participation is not review quality.
- **coderabbit is `unmeasurable`** — its check completed but it published no comment in a crediting
  shape. ⚠ Do NOT read that as "reviewed nothing": it is equally consistent with rate-limited,
  refused, or published-in-a-dropped-shape. The producer did not credit it; that is all this PR
  establishes.
- Both escapes were `gate_addressable`, not `gate_structural` — in-house lenses could reach them. The
  gap is surfacing and disposition, not reach.

## Five infrastructure defects filed — see sibling message `-008.md`

`10298b` (green builds report `tests_run: 0`, reproduced 3×), `3e095e` (stale job re-attach returns a
foreign green), `4fee70` (coverage budget truncates ONLY green runs, proven causally), `48dd4c`
(`automatic-review` worked example crashes on the common path), `9134b6` (gate-delta unmeasurable
whenever a gate re-fires).

⭐ Three of the five are **anti-correlated with the interesting case** — they misreport specifically on
the healthy path.

## Cost — this is the uncomfortable number

**3.04M tokens dispatched · 71.4M billing-weighted · 13h2m wall · 2h30m worked · 10h32m idle** for a
3-file landing.

The plan-retrospective judged this **past the `error` anchor (1.6M) for `single_module+feature`**, and
called the verdict robust because the total is a floor. `6-finalize` alone was 45.3M billing (**63%**)
and 342 tool uses. 80% of wall time was idle.

⚠ The epic should weigh this against what the spend bought: five rounds of defect-finding on a
3-file diff, and five reproduced infrastructure defects that no cheaper pass would have surfaced.
That is a judgement for the orchestrator, not for this plan to settle in its own favour.

## Sequencing note for the orchestrator

**PLAN-TRUTH-092** (`cloud-plan-lane-contract-and-run-report-accuracy`, staged) declares the same file
in its Expected Surface — different defect (merge gate, not build gate). It must now be re-grounded
against this landing: `.claude/skills/cloud-plan-lane/SKILL.md` moved, and the guard added here will
fail if -092 edits the Step 5 trigger table or the report `## Build gate` block without keeping them
in lockstep. **That is the guard working as intended**, but -092's author should know before starting.
