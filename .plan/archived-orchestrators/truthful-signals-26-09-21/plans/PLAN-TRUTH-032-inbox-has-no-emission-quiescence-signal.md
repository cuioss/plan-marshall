> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-038`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-032: an agent-to-agent message protocol — termination signal, autonomous drain, and a plan-side inbox

epic: truthful-signals
workstream: WS-01

## Objective

The `inbox/` channel works for one direction (a plan writes, an orchestrator hand-drains) and has no
protocol for anything else. Give it: a **termination signal** so a receiver knows a sender is done, an
**autonomous drain** for standalone signals that is safe against orchestrator↔orchestrator ping-pong, and
a **plan-side inbox** sharing ONE structure with the orchestrator side.

## The measured defect that started this (PLAN-TRUTH-001 / #1073)

Read from `inbox/archive` envelope headers, 2026-08-02:

| Time | Emission |
|---|---|
| **19:09:47Z** | `kind=landing` — message **001**, written **before every one of its children** |
| 19:10:01 → 19:11:13Z | 12 `candidate-lesson` (002–013) — the first burst |
| **19:48:12 → 19:50:57Z** | **6 MORE** (014–019) — **37 minutes later**, a second burst |

⛔ The landing states *"12 candidate-lesson messages accompany this landing."* **True at 19:09:47Z, wrong
by 19:48:12Z.** The real total is **18**. The landing cannot be authoritative about its own siblings
because six of them do not exist when it is written.

⇒ **There is no signal that a sender is finished**, and the current standing rule (*"never drain while a
finalize is running"*) is a **human-memory workaround for a missing protocol field**. It fails both ways:
draining between bursts consumes 13 of 19 and reports the sender drained with nothing detecting the
shortfall; waiting for archive is how a **38-message backlog** accumulated. Corroborating instance: the
epic inbox grew **36 → 38 mid-drain** on 2026-08-01.

## Prior art — external and in-tree

**External** (survey + practitioner sources; see § Sources):

- **A2A / ACP model a lifecycle with an explicit `Termination` phase** — creation, operation, update,
  termination. ⇒ Our missing terminal signal is a **known, named element of the standard shape**, not an
  exotic requirement. A2A's envelope is a message of typed parts with a completed task delivered as a
  distinct **Artifact** — i.e. the *result* is a different object from the *messages*, which is close to
  our `landing` vs `candidate-lesson` split.
- **Loop prevention is a solved-shape problem** with four recurring mechanisms: **task-ID idempotency +
  dedup** (check before processing), **anti-recursion rules** (bound how often A may hand back to B in
  one conversation), **circuit breakers** (trip on repeated failing handoffs), and **tracking ID +
  expiry** on every message so a conversation is traceable across agents.
- Loop **detection** signals: repeated identical messages, rising output similarity across turns, and
  token-budget overrun.

**In-tree, and this is the stronger input — we already shipped a fix for this exact loop class.**
`PLAN-111` (#1047) `self-ingested-reply-is-a-non-terminating-barrier-loop`, now live in
`workflow-integration-github`:

> *`post_responses` transmits thread-less dispositions as a NEW PR-level comment … on the next fetch that
> comment is unresolved, is not a refusal, matches no `ignore` regex, and carries a NEW `comment_id` the
> dedup cannot know — so … it is filed as a fresh pending finding, the barrier blocks on it, triage
> responds again, **and the cycle never terminates**.*

Its fix is the template for our ping-pong caveat:

1. **Start-anchored self-authored exclusion** — drop a message whose stripped body *starts with* the
   known self-emitted heading. ⛔ **Never a substring test**: a peer *quoting* our text is real content
   and must still be filed.
2. **A separate counter per class** — `count_skipped_self_response` is deliberately NOT
   `count_skipped_noise`, on the stated grounds that *"our own output is not acknowledgment noise."*
3. **Each recognizer is its own stage.** The noise pre-filter, the refusal recognizer, and the
   self-authored recognizer are three stages with three counters — collapsing them destroys the ability
   to distinguish *nothing to say* from *declined* from *my own echo*.

⇒ **D2 adopts this three-class discipline verbatim rather than inventing a loop guard.**

## ⛔ Binding design constraint — ONE batched read, for orchestrators AND plans

**Operator, 2026-08-02: all messages are ALWAYS read together — a single `untrusted-ingestion` instance
per drain, on both the orchestrator side and the plan side.** Never one ingestion pass per message.

Three things follow, and the third changes this plan's internal ordering:

1. **Security**: the containment boundary is crossed **once per drain**, not N times. One reader
   invocation, one `validate_struct` gate, one clamped struct the write-capable context consumes.
2. **Coherence — this is the operator's earlier "digest the intermediate reports together with the final
   report", arriving as a hard requirement.** Read together, the `landing` is the *frame* and the
   `candidate-lesson`s are read *inside* it. Read apart, the children lose the frame that makes them
   interpretable — which is exactly what happened in the 2026-08-01 drain, where the landing was
   dispositioned in batch 1 and its children across batches 2–5.
3. ⛔ **THE TERMINATION SIGNAL BECOMES A HARD PREREQUISITE, NOT A PARALLEL NICETY.** *You cannot read
   "all messages together" without knowing what "all" is.* A batched read over an incomplete set is a
   batched read of the wrong batch — and the measured failure is precisely this: a drain between the two
   bursts would have "read all together" over **13 of 19**. ⇒ **D1 gates D3/D4; it is not a sibling of
   them.** Sequence accordingly, and do not let a split separate them.

⚠ **One batch must NOT mean one verdict.** A single malformed or hostile message must not poison the
batch. The precedent already exists and is adopted: `inbox list` today enumerates every message,
**reports per-message validity with its own error code, and never aborts the enumeration** on one bad
message. The batched read preserves **per-message error isolation inside a single ingestion pass** —
one boundary crossing, N independent validity verdicts.

## ⛔ Binding design constraint — every inbox verb returns structured TOON

**Operator, 2026-08-02.** ✅ **Already satisfied by the five existing verbs** — verified from live output
this session: `write` returns `status/operation/slug/store/sender_type/sender_id/kind/message/path`;
`list` returns `count/invalid_count` plus `messages[N]{name,sender_id,kind,created,valid,error}`;
`validate` returns the parsed header plus `location`/`archive_path`; `archive` returns
`message`/`already_archived`; `detect` returns `orchestrated`/`epic`/`plan_spec`.

⇒ **The constraint therefore binds the NEW surfaces this plan adds**: `anyMessageForMe`, the D1 terminal
marker, and the D3/D4 batched read. Each returns a TOON envelope with an explicit `status`, a stable
field set, and — for the enumerating verbs — a counted table, so a caller never parses prose.

⚠ **A premise correction, made before it could shape the design.** The orchestrator's first instinct was
that TOON truncates multi-line values, which would have forced the batched read to return *paths only*.
**That is false**: `ref-toon-format/scripts/toon_parser.py` implements `_parse_multiline_value` with the
`|` block indicator and explicitly preserves empty lines inside the block. **TOON carries multi-line
bodies fine**, so "return TOON" and "carry the message bodies" are **not** in conflict, and no deliverable
should be scoped as if they were.

⭐ **The path-vs-body question is therefore a real DESIGN CHOICE, not a forced one — D3 decides and
records why.** The argument for returning **paths + metadata** rather than inline bodies is symmetry with
the write side: `inbox write` takes `--payload-file` precisely so that **no message body ever passes
through a shell argument**, and that is what makes its write-boundary enforceable by construction. A read
side that returns paths mirrors it, keeps the payload-blind metadata layer cleanly separable, and keeps
large bodies out of the transport. ⚠ **Neither option is precluded by TOON** — decide on the boundary
argument, not on a format limitation that does not exist.

## Deliverables

1. **D0 — GATE (mutates nothing): derive the emitter population, the peer graph, and the drain seams.**
   (a) Every producer that writes to an inbox and **when in the lifecycle it fires** — the two observed
   are `lessons-capture` (19:10) and `plan-retrospective` (19:48), ⛔ **a SAMPLE from one plan**.
   (b) Whether any emitter can fire **after `archive-plan`** — this decides whether a terminal marker has
   a well-defined author at all. (c) The existing drain seams: ⭐ **the Phase Entry Protocol already runs
   `phase_handshake verify --phase {prev} --strict` at the entry of phases 2–6** — **the phase-transition
   drain check needs no new trigger mechanism**, it hangs there.
2. **D1 — the termination signal.** Choose ONE and record the rejected options: **(a)** a terminal
   `kind=final` marker written by the last emitter; **(b)** the landing moves LAST so its manifest is
   authoritative — ⚠ costs the read-the-frame-first property the current order gives; **(c)** landing
   stays at 001 carrying **no count**, with the count supplied by a terminal marker; **(d)** `inbox list`
   derives per-sender completeness from plan status (complete iff archived). ⛔ **A mechanism that
   requires the orchestrator to REMEMBER A RULE is not a fix** — that is exactly what exists and what
   failed.
3. **D2 — autonomous drain for standalone signals, with ping-pong containment.** A `kind=finding` /
   `kind=signal` message not bound to a plan result is drained without operator involvement. Containment
   adopts PLAN-111's three-stage discipline (self-authored / refusal-or-ack / real content, **separate
   counters**) plus a bounded **anti-recursion rule** on orchestrator↔orchestrator exchange.
   ⛔ **A reply is NOT noise and MUST NOT be silently dropped** — `review-apparatus-011` was a reply that
   **refuted one of our findings** and `-007` was a reply that **corrected our ledger**. Suppressing
   replies to stop a loop would have discarded both. **Bound the exchange, never mute the channel.**
   ⚠ D0 must count the real peer graph: today 3 epics, and the reply depth observed is 2 (we send, they
   reply) — **no actual loop has occurred yet**, so this is prevention, not incident response. Say so.
4. **D3 — one structure for plans and orchestrators.** The envelope already carries
   `sender_type: plan|orchestrator`, so the *sender* half generalizes today. What is missing is an
   addressable **recipient** (the path currently encodes the epic) and a **plan-scoped inbox location**.
   ⛔ **Preserve the write-boundary carve-out by construction**: the reason `inbox write` is safe is that
   it derives the path from validated slug + sender id with **no caller-supplied output path**. Any
   recipient field must keep that property.
5. **D4 — plan-side check, and its containment boundary.** Check at (a) each phase transition via the
   existing Phase Entry Protocol and (b) after each execution-context return.

   ⛔ **BINDING IMPLEMENTATION CONSTRAINT (operator, 2026-08-02): the check is COMPLETELY SCRIPT-BASED.**
   An `anyMessageForMe()`-shaped deterministic verb taking `--plan-id`, which also writes the work-log
   entry itself. **No LLM envelope, no dispatched leaf, no model judgement in the check.** This is
   `dispatch-granularity`'s Heuristic 1 applied exactly — deterministic work becomes a script — and it is
   what makes the high call frequency a non-issue.

   ⛔ **The check PARSES THE ENVELOPE METADATA too** (operator, 2026-08-02) — not merely a boolean — so
   the caller can decide **whether to act NOW or defer to the next drain**. It returns the enumerated
   header fields (`sender_type`, `sender_id`, `kind`, `created`, validity, and D1's terminal marker),
   **never the payload body.**

   ⭐ **This SHARPENS the security property rather than weakening it — the correct formulation is
   PAYLOAD-BLIND, NOT FILE-BLIND.** The trust boundary is about the **body**, not about opening the file.
   The envelope header is a **constrained, enumerated, first-party surface written by our own
   `inbox write`** — `sender_type` and `kind` are closed enums, `sender_id` is path-safe-validated, and
   `epic` must match — which is precisely why `validate_envelope` can return distinct error codes for
   each. Parsing that is not ingesting untrusted prose.

   ⭐ **The existing `inbox list` ALREADY DEMONSTRATES THIS SHAPE**: it validates every message through
   the same seam and returns `name`, `sender_id`, `kind`, `created`, `valid`, `error` per row — **and no
   body.** ⇒ `anyMessageForMe()` is plausibly a thin `--plan-id`-scoped extension of `inbox list` rather
   than a new accessor. **D4 confirms; do not build a parallel enumerator** (this epic's *where a copy
   exists, delete the copy* rule).

   | Operation | Frequency | Sees metadata? | Sees payload? | Trust boundary |
   |---|---|---|---|---|
   | `anyMessageForMe --plan-id` | high | ✅ yes (enumerated) | ⛔ **no** | not crossed |
   | reading a message | rare (on a hit) | yes | yes | ⛔ **untrusted-ingestion applies** |

   ⛔⛔ **GUARD — URGENCY MUST BE RECEIVER-DECIDED, NEVER SENDER-DECLARED.** Once `kind` drives an
   act-now decision, it becomes a surface a sender can inflate: a peer that marks everything `finding`
   commands attention it did not earn. ⇒ **Do NOT add a `priority:` / `urgent:` field to the envelope.**
   The receiver applies **its own policy** over the enumerated metadata (its phase, its cap, its queue
   state) to decide act-now-vs-defer. The sender states *what kind of thing this is*; only the receiver
   decides *what that is worth right now*. ⚠ This is the operator's own standing instruction applied —
   a sibling orchestrator is not trusted merely because it is in-tree.

   ⛔ **The containment requirement is unchanged and still binds the READ half.** Today plans only
   **write** to inboxes. The moment a plan **reads** one, the inbox becomes an **input to a running
   plan's control flow** — a message can change what the plan does. Any message not authored by the
   operator or by first-party machinery MUST route through `plan-marshall:untrusted-ingestion` before it
   can influence execution. ⚠ **A sibling orchestrator is NOT trusted merely because it is in-tree.**

   ⚠ **REFINEMENT OWED ON THE WORK-LOG WRITE — log on HIT, not on CHECK.** The operator's "a work log for
   the result" must not become a line per call. **Evidence already in this ledger**: `PLAN-TRUTH-017`
   records an observed `work.log` at **111,433 entries / 19.9 MB** on a single run. A check firing at
   every phase transition *and* every execution-context return, each writing a line, inflates the very
   artifact that is already the largest in a plan directory — and `work.log` is what the dispatch audit
   and the retrospective read. ⇒ **An empty check writes nothing.** D0 sizes the call volume to confirm
   the ratio; the constraint stands regardless.

   ⭐ **`anyMessageForMe()` presupposes an addressable recipient** — "me" must be resolvable from
   `--plan-id`. That is the same recipient concept D3 owns, arriving from the plan side. **D3 and D4 must
   agree on one addressing scheme, not two.**
6. **D5 — tests, each verified to FAIL pre-fix.** (a) A drain between two emission bursts reports the
   sender INCOMPLETE, not drained. (b) A self-authored message is excluded **start-anchored**, while one
   that merely *quotes* the heading is still filed (the false-positive boundary, both directions).
   (c) The three skip classes keep **distinct counters**. (d) The append-only and own-file-only
   invariants hold — a terminal marker is a NEW message, never a mutation. (e) D0's emitter population is
   asserted non-empty and contains both observed emitters.

Six deliverables — at the split threshold. **Split evaluated and NARROWED by the batched-read
constraint.** D1 (termination) now **gates** D3/D4 rather than sitting beside them — a batched read
requires knowing the batch is complete — so any split that puts D1 in a different plan from D3/D4 would
ship a batched read over a set nobody can bound. ⇒ **The only admissible split boundary is D0–D4 vs D5**,
and even that is unattractive. **Proceeding unsplit; D0 may still re-evaluate if the emitter population
turns out far larger than the two observed.**

## Claim Labels

- **OBSERVED**: every timestamp/count in the defect table, read from the archived envelope headers.
- **OBSERVED**: the landing's "12 accompany" sentence vs the true total of 18.
- **OBSERVED**: the inbox grew 36 → 38 mid-drain on 2026-08-01.
- **OBSERVED**: the envelope already carries `sender_type: plan|orchestrator`.
- **OBSERVED**: `inbox write` derives its path from validated slug + sender id with **no caller-supplied
  output path** — the property that makes the write-boundary enforced by construction.
- **OBSERVED**: the Phase Entry Protocol calls `phase_handshake verify --phase {prev} --strict` at the
  entry of phases 2–6 — read in `phase-2-refine`, `phase-3-outline`, `phase-4-plan` SKILL.md.
- **OBSERVED**: PLAN-111's self-authored exclusion is start-anchored with its own counter, documented in
  `workflow-integration-github/SKILL.md`, with the explicit rationale that our own output is not noise.
- **OBSERVED**: two sibling replies this week carried substantive corrections (`review-apparatus-011`
  refuted a finding of ours; `-007` corrected our ledger) — the evidence that muting replies is wrong.
- **HYPOTHESIS**: the two bursts are `lessons-capture` and `plan-retrospective`. The gap and step order
  make it the obvious reading, but **the messages do not name their emitter** — confirm at D0.
- **HYPOTHESIS**: no emitter fires after `archive-plan`. **Confirm at D0** — if one can, option (a) has no
  well-defined author and D1 must take (d).
- **REPORTED (external, not verified in-tree)**: the A2A/ACP lifecycle-with-Termination shape and the
  four loop-prevention mechanisms. Used as **design orientation only** — no external claim is load-bearing
  for any deliverable, and the in-tree PLAN-111 precedent governs where they differ.
- **OBSERVED**: `work.log` reached **111,433 entries / 19.9 MB** on a single observed run — recorded in
  `PLAN-TRUTH-017`. This is the evidence behind D4's log-on-hit refinement, and it is first-party to this
  epic, not a projection.
- **OBSERVED**: `inbox list` returns `name`, `sender_id`, `kind`, `created`, `valid`, `error` per row and
  **no message body** — so a metadata-parsing, payload-blind enumerator **already exists in-tree**. This
  RESOLVES the concern filed one revision earlier (that reusing `validate_envelope` would break the
  content-blind property): the property is **payload-blind, not file-blind**, and the existing verb
  already meets it. ⇒ D4 extends this verb rather than adding a parallel one.
- **OBSERVED**: the envelope header is a constrained enumerated surface — `sender_type` and `kind` are
  closed enums, `sender_id` is path-safe-validated, `epic` must match — evidenced by `validate_envelope`
  returning a distinct error code per class.
- **Verify-first clause**: D3 assumes a recipient field can be added without weakening the
  path-derivation property. Confirm against `inbox write`'s argument surface before scoping; if a
  recipient must be caller-supplied, the write-boundary carve-out changes character and D3 re-scopes.

## Expected Surface

- **OBSERVED**: `marshall-orchestrator/standards/inbox-envelope.md`, `marshall-orchestrator/workflow/analyze.md`
- **HYPOTHESIS**: `marshall-orchestrator/scripts/orchestrator.py` — the `inbox` verb family
- **HYPOTHESIS**: `ref-workflow-architecture/standards/phase-lifecycle.md` + the phase SKILLs for D4(a)
- **HYPOTHESIS**: `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary
- **HYPOTHESIS**: `untrusted-ingestion` for D4's containment boundary
- **HYPOTHESIS**: `test/plan-marshall/marshall-orchestrator/**`

## Dependencies and Sequencing

- **Depends on**: none. ✅ Disjoint from both running plans (TRUTH-026 build seam, TRUTH-031
  `phase-6-finalize` + `workflow-integration-git`).
- ⚠ **Adjacent to PLAN-TRUTH-022** (`orchestrator-cleanup-verb`) — same skill, different concern.
  Sequence, do not pair.
- ⚠ **PLAN-TRUTH-015** renames this skill — re-ground every path if it lands first.
- ⛔ **Cannot emit: `parallelization_scope` = 2, R = 2.** CAPACITY block, not a collision.

## Sources

- [A Survey of Agent Interoperability Protocols (MCP, ACP, A2A, ANP)](https://arxiv.org/html/2505.02279v1)
- [How To Prevent Infinite Loops in Multi-Agent Systems — NeuralTrust](https://neuraltrust.ai/blog/a2a-loop)
- [Inter-Agent Communication: A2A, MCP & Buses](https://www.taskade.com/blog/inter-agent-communication-patterns)
- [Unlocking agent communication: the A2A protocol explained](https://medium.com/wpp-ai-research-labs/unlocking-agent-communication-the-a2a-protocol-explained-4a63ceea1de3)

## ⚠ ADJACENCY 2026-08-02 — `PLAN-TRUTH-038` extends the same verb group and the same `list` row schema

`PLAN-TRUTH-038` (staged) adds an `amend`/`supersede` verb because a filed inbox message cannot be
corrected, and its envelope carries no marker making a post-filing mutation visible. ⛔ **This
orchestrator consumed an amended message on 2026-08-02 and could not tell.**

**Both plans touch `orchestrator.py`'s inbox verb group and both extend the `inbox list` row schema.**
⛔ **SERIALIZATION PAIR — and 038's spec already names this plan as the one that should run first**,
because this plan sets the row shape.

⭐ **Evaluate ABSORBING 038 as a deliverable here at outline.** Argument for: two passes over the same
row schema is the more expensive path, and the envelope is already being revisited for the termination
signal. Argument against: this plan is already large, and 038's load-bearing half (an envelope field
that makes mutation visible) is independent of quiescence. **Decide and record the rejected option.**

## ⛔ FOLDED 2026-08-03 (#1085) — the GRANULARITY invariant is violated, and two counts use different UNITS

`plan-retrospective`'s `mark-step-done` display_detail read
**"10 candidate-lesson(s) -> epic truthful-signals, 1 -> review-apparatus"**, while
`orchestrator inbox list --slug truthful-signals` reported **`count: 1`**.

✅ **Nothing was lost** — all ten candidates (CL-1..CL-10) were **bundled into ONE message**. But:

1. ⛔ **The granularity invariant is violated.** `inbox-envelope.md` specifies *"one message per emitted
   item — that is what the sequence exists to allocate"*, and `lessons-capture.md` § Orchestrated
   emission contract repeats it as *"One `kind: candidate-lesson` message per candidate."*
   ⇒ **Ten candidates consumed ONE sequence number, and the drain cannot archive them independently** —
   which defeats the per-message consume marker this plan's protocol is built on.
2. ⭐⭐ **The two numbers count different UNITS and nothing reconciles them.** `display_detail` counts
   **candidates**; the enumeration seam counts **messages**. ⇒ **A drain trusting either alone concludes
   wrongly**: 10 says nine messages are missing; 1 says nine candidates were dropped. **The 10-vs-1 gap
   reads as data loss until a human opens the body.**

⇒ **This is this plan's own subject arriving from a third direction**: not *"has the sender finished?"*
and not *"is the sender sending everything?"* but **"do the sender and the receiver agree on what a
message IS?"** ⛔ **A termination signal over a channel whose unit is ambiguous does not settle a drain.**

⚠ **Do not fix this by making the drain tolerant of bundles.** The sequence allocation, the archive
claim and the idempotent re-drain all key on one-item-per-message. **Either enforce the invariant at the
write seam, or change the contract and every consumer with it — never leave the two in disagreement.**

## ⛔ ENVELOPE OWNERSHIP SPLIT 2026-08-08 — `PLAN-TRUTH-038` lands FIRST; this plan CONSUMES its vocabulary

This plan and `PLAN-TRUTH-038` (inbox amend/supersede) both add `orchestrator inbox` verbs **and
both add envelope fields**. Shipped independently they would put **two overlapping message-state
vocabularies in one schema**.

**Decision: 038 first.** It owns the envelope's message-state vocabulary (amend/supersede, a
`revision` counter, the superseded marker). ⇒ **This plan's termination signal is expressed IN THAT
VOCABULARY — it does NOT add a parallel state field, and it does not invent a second enum.**

⛔ **SERIALIZE — do not pair these two.** They edit the same schema file and the same verb surface.
⚠ If 038's chosen model cannot express *"this sender will send no more"*, 038 is required to say so
at its D0 and notify this plan; only then does this plan add its own field, and it does so as a
documented extension of 038's vocabulary rather than beside it.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
