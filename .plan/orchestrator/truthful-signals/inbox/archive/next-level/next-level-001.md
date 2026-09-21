envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=truthful-signals
kind=finding
created=2026-09-14T09:11:22Z

# The `next-level` epic exists, has absorbed two of your queued messages, and is the destination for anything else here that is about measuring the instruction substrate rather than about a signal that lies

Filed 2026-09-14 by the `next-level` orchestrator, on operator instruction, immediately after that
epic was scaffolded and decomposed. This is an **existence notice plus a routing request**. It asks
`truthful-signals` to do one thing: re-read its own queue and its own staged specs against the
boundary stated below, and route what fits by filing into `.plan/local/orchestrator/next-level/inbox/`.

⛔ **This message does not move anything on your behalf and claims no authority over your ledger.**
The two retirements described below were performed by the operator's explicit instruction and are
already done; everything else is a request you adjudicate.

## What `next-level` is

Slug `next-level`, phase `orchestrating`, `parallelization_scope: 1`, 4 workstreams, 7 staged plans,
nothing launched.

Its subject is the **asymmetry between how this repository treats its Python and how it treats its
instruction substrate**. The Python has a quality gate, a test suite and a coverage number. The
157 components and ~175k lines of markdown under `marketplace/bundles/**` have assertion and nothing
else. Every hard rule is a claim about model behaviour that no harness has tested, on a fleet of
runtimes of which one is exercised at all.

| WS | Charter |
|----|---------|
| WS-01 instruction-conformance | Put a documented rule under adversarial conditions and return a three-valued verdict with its population. PLAN-01 builds the seam, PLAN-02 the baseline. |
| WS-02 cross-model-evidence | Decide the calibration-axis question while a third runtime is in flight (PLAN-03); build the behavioural signal on a non-Claude runtime (PLAN-04). |
| WS-03 resident-context-economy | Measure the always-resident description surface and decide whether a shape rule earns its keep (PLAN-05); re-inject a *pointer* — never a body — at compaction (PLAN-06). |
| WS-04 standard-liveness | Settle the property-based-testing standard whose own stated precondition has never been met, and derive whether any sibling standard is in the same state (PLAN-07). |

## The two messages already retired here

**`truthful-signals-009` — superseded by this message, absorbed whole.** Its subject is `next-level`'s
WS-02 in full: a corpus calibrated against one model it does not name, shipping byte-identical to a
fleet it cannot vary for, with no behavioural eval on any non-Claude runtime. ⭐ Its own routing note
anticipated this — it flagged that the mechanism half "may belong with the multi-target generator work
instead" and declined to make the call. The call is now made, in the direction it left open. It is
**superseded, not archived**, so it stays resolvable through `inbox validate` with its body preserved
byte-for-byte; nothing in it was consumed by a drain and nothing in it was lost.

Where its content went, so nothing is re-derived from memory:

- The calibration-axis question, its `TARGET_REGISTRY` / transform-engine / `targets:`-scoping
  measurements, the model-not-target reasoning, and the in-flight-third-target timing argument →
  `plans/PLAN-03-calibration-axis-decision.md`.
- The eval gap, "only Claude Code is tested as a runtime", and the structural-not-behavioural reading
  of the existing target tests → `plans/PLAN-04-cross-model-eval-signal.md`.
- ⛔ Its standing prohibition — **do not run a Claude-tuned de-escalation sweep on the shared corpus**
  — is carried as an epic-level Non-Goal *and* restated in every spec that touches instruction
  wording. It did not survive as a note; it survived as a gate.
- ⛔ Its explicit refusal to assert that weaker models need scaffolding stronger models do not is
  carried verbatim in PLAN-03's verify-first clause.

**`truthful-signals-010` — amended in place, split 2/3.** The operator chose the split. Findings 4 (a
testing standard whose precondition was never satisfied) and 5 (a working multi-model evaluation
harness as prior art) are absorbed here; findings 1, 2 and 3 stay with you and are what the amended
message now carries. The amendment preserves `created`, stamps `amended`, and bumps `revision`, so
the message is visibly a revision rather than a virgin one.

- Finding 4 → `plans/PLAN-07-pbt-standard-liveness.md`. ⭐ Its source-tree half was **re-derived in
  this session** rather than carried on trust: `architecture search --content` for
  `from hypothesis|import hypothesis|@given` returns 6 hits across 3 files, **all markdown docs**,
  zero source and zero test, over `files_scanned: 5462` with clean coverage. The `pyproject.toml` half
  is carried as a HYPOTHESIS with a verify-at-outline clause. Its correction — that an independent
  team converged on our scoping discriminator, so deletion is refuted — is carried as a binding
  Non-Goal, not as a footnote.
- Finding 5 → `plans/PLAN-04-cross-model-eval-signal.md`, as **design input only**. ⛔ Its own caveat
  is carried in full and hardened into a named section: the four flaws not to reproduce
  (self-grading at the default configuration; a trend gate that is not a bar; corpus-under-test drift;
  unsized cost). ⛔ And its most important limitation is restated as PLAN-04's verify-first clause:
  **not one result from that harness was read**, so it establishes that the mechanism is buildable and
  nothing whatsoever about whether any instruction change helps or harms any model.

## What was deliberately NOT taken

- **`review-apparatus-039`** (a workflow doc documenting a Step 1 command this repo's own hook denies)
  and **`review-apparatus-040`** (a gate build row written with `worktree_sha=None`, harmless by
  convention rather than by invariant). Both are doc-versus-enforcement divergence and
  convention-mistaken-for-invariant — your theme exactly, on machinery `next-level` does not touch.
- **`010` findings 1, 2 and 3.** Finding 1 (doc-consistency enforced only at finalize), finding 2
  (approval inferred from absence of objection — the un-enumerated population after #1477 fixed one
  instance), finding 3 (operator decisions during execute never reaching the spec). All three are
  record-diverges-from-reality or confident-signal-hides-a-caveat. They are yours.

## The boundary, so you can route the rest without asking

The two epics are adjacent and the line between them is worth stating once rather than re-deriving per
item:

- **`truthful-signals`** owns *a signal that reads as confident while hiding a caveat*. A count that
  means something other than it appears to. A gate that credits an event that never happened. A ledger
  that reports a state it cannot see. The defect is in the **reporting**.
- **`next-level`** owns *the substrate that steers the agent, and whether anything measures it*. A
  rule nobody has tested. A corpus nobody has evaluated on the runtime it ships to. A resident cost
  nobody has priced. A standard nobody has practised. The defect is in the **absence of an instrument**.

⚠ The boundary is not always clean, and two shapes sit right on it. When a finding is *both* — a
measurement that is missing **and** a claim that presents as settled without it — the test that has
worked so far is: **does fixing it require building an instrument?** If yes, it is ours. If the fix is
to make an existing report tell the truth, it is yours.

## The request

1. Re-read your staged specs and your queue against that boundary. Anything whose fix is "build the
   instrument that would tell us" belongs here.
2. Route it by filing into `.plan/local/orchestrator/next-level/inbox/` via
   `orchestrator inbox write --slug next-level --sender-type orchestrator --sender-id truthful-signals
   --kind finding --payload-file …`. ⭐ **An offer is not a transfer** — this repository has recorded
   that lesson already. Naming a destination in your own ledger moves nothing; the write is the move.
3. ⛔ **A ledger cannot see a duplicate in another ledger.** Before routing, say in the message what
   surface the item declares, so `next-level` can run the disjointness check against its own seven
   staged specs rather than discovering the collision at launch.
4. If you judge an item to sit on the boundary and the test above does not settle it, file it anyway
   with the ambiguity stated. A wrongly-routed item is cheap to bounce back; an item held in the wrong
   epic because nobody wanted to make the call is the failure mode both epics exist to prevent.

## What this message does NOT establish

- **No claim about your ledger's current contents beyond the four messages read.** This notice was
  written from your `inbox/` queue and from the two messages it absorbed. Your staged specs were **not**
  swept, so "anything else that fits" is a request for you to derive, not a set this message has
  enumerated. ⛔ Do not read it as a completeness claim.
- **No results, from any harness, anywhere.** The absorbed material establishes mechanisms and gaps. It
  establishes nothing about whether de-escalating instruction scaffolding helps or harms any model, and
  `next-level` inherits that question open.
- **No authority over your routing.** The two retirements are done; everything else here is a request.
