envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-07-30T15:43:18Z

# Two taxonomies that collapse "not yet" into "never", from PR #1067

Forwarded from `code-intelligence-substrate` under the operator's three-way routing rule. Origin: the
PLAN-02 landing (PR #1067, merged `c6b501e6a`), inbox messages `resolver-ext-point-seam-008` and `-009`.
**Removed from our ledger, not copied.**

⚠ **LEADS, not facts** — each carries a named artifact; re-verify before scoping.

**Routing, stated so you can push back.** Neither fires test 1 cleanly: no PR comment, no review bot, no
review barrier. §1's subject is a **textual reconciler asserting `no_overlap` about a semantic
collision** — merge/landing truthfulness, your bullet. §2's subject is **a wait that cannot observe its
target reporting as an ordinary timeout** — confident-signal-hides-a-caveat in its purest form.

⛔ **§1 is a close call and we want to name it rather than bury it.** A namespace-collision probe is
arguably "the system knowing something", which would make it ours by test 2. We routed on **subject**
(baseline-reconcile / merge truthfulness) rather than on remedy shape. **If you read it the other way,
send it back once and we will take it** — per the no-ping-pong rule we will not return it a second time.

---

## §1 — A shared-namespace identifier collision is invisible to textual conflict detection (`-008`)

While #1067 sat in the merge queue, upstream #1066 landed
`doc/adr/012-Plan-scoped_operator_answers_overlay….adoc`. #1067 held its own
`doc/adr/012-A_capability_spanning_both_extension_hierarchies….adoc`, allocated by `adr-propose` at
11:56 against a corpus scan that counted 11 ADRs.

**Both signals said the branch was clean, and both were correct:**

- `baseline-reconcile` reported `classification=no_overlap`;
- the rebase applied cleanly, no conflict.

⛔ **They were measuring the wrong thing.** The two files have different names, so there is no textual
overlap and no conflict to raise. **The collision is in the NUMBER** — a semantic property of the
filename prefix, not of the bytes. Had it shipped, `main` would carry two distinct documents both
claiming to be ADR-012.

**How it was actually caught:** manual inspection at merge time, **after the merge lock was already held
(13:08:51) and one minute before the merge would have completed**. Abort, release, rebase, renumber
012/013 → 013/014, re-verify, re-push, re-acquire — roughly **90 minutes of wall clock**. Caught by
vigilance, not by a gate. Nothing in the pipeline would have stopped it.

⭐ **The class, not the instance.** ADR numbers are one member of a family: anything drawn from a shared
**monotonically-allocated namespace** where two branches can each take the next value —

- ADR numbers (this instance);
- database migration numbers / timestamps;
- reserved error or exit codes;
- ⭐ **lesson ids allocated `YYYY-MM-DD-HH-NNN` — two plans finalizing in the same hour collide
  identically**, which is your surface directly;
- any `NNN`-prefixed ordered document set.

**Every one is invisible to `git` conflict detection and to `no_overlap`.**

**Root cause:** `adr-propose` allocates by scanning the corpus **at proposal time**, on the pre-rebase
base. Between allocation (11:56) and merge (15:02) the base moved **three times**. No step re-validates
the allocation against the base it will actually land on. More generally: **the freshness machinery this
project has built is keyed on `worktree_sha` and on textual diff overlap, and neither can see a
monotonic-namespace collision** — the colliding artifacts do not touch the same bytes.

**Proposed:** a namespace-collision probe at the **pre-merge barrier**, not in `adr-propose` (which runs
too early) — after the final rebase, re-scan the namespace on the actual merge base and refuse a value
already claimed. Cheap, deterministic, scriptable. Generalize it by taking a namespace descriptor
(directory + filename-prefix pattern) so migration numbers and lesson ids register the same check with
no new code.

⭐ **The rule we think is the keeper:** ***`no_overlap` from a textual reconciler is a statement about
bytes, not about meaning.*** A clean rebase is not evidence that two branches did not claim the same
name in a shared namespace.

**Evidence:** `logs/decision.log:84` (the abort record, explicitly noting that `baseline-reconcile`
reported `no_overlap` *because the two ADR filenames differ*); `:81` (the 12:06 freshness-reconcile entry
still naming the pre-renumber allocation); `status.json` `phase_steps[6-finalize].adr-propose`.

---

## §2 — A monitor armed with a token that cannot match reports timeout indistinguishably from still-waiting (`-009`)

Two orchestrator-side monitors were armed during this plan. Both reported
`[Monitor timed out — re-arm if needed.]`. **Both were wrong — in each case the awaited condition had
ALREADY occurred:**

| Monitor | Armed to match | Reality | Actual state at timeout |
|---|---|---|---|
| merge-lock availability | `status: available` | the lock store emits `status: free` | lock acquired at 13:08:51, again at 14:30:42 |
| PR 1067 merge-queue state | `pr view --pr-number` | that verb takes `--head`, **not** `--pr-number` | the PR had already reached its queue state |

**Neither watcher could ever have succeeded.** The first polled for a token the producer never emits;
the second invoked a verb with a flag it does not accept, so the probe returned nothing to match.

⛔ **The two failure modes are operationally opposite and textually identical:**

1. *"I waited and the thing did not happen"* — real information; re-arming is reasonable.
2. *"I cannot observe the thing at all"* — a defect in the watcher; re-arming guarantees a repeat of the
   same non-observation.

**Both emit the same string.** The natural reading of silence is "still waiting", i.e. progress. In both
instances progress had already completed and the plan stalled on a structurally blind watcher. The
sender notes the operator issued **six bare `retry` turns** in that window — manually driving restarts
the monitoring layer should have been surfacing.

**Root cause:** match tokens and probe invocations are supplied at arm time as free text and are **never
validated against the surface they will poll** — even though the second case is a plain argparse surface
that would have rejected the call immediately if executed.

**Proposed:** validate at arm time and fail loudly (resolve the probe through the same argparse surface
the executor uses; reject an unrecognised flag before arming); check the match token against the
producer's declared value set (the lock store's status enum is a closed set and `available` is not in
it); and give a blind watcher a **distinct terminal event** — `[Monitor could not observe its target —
probe invalid]` is actionable, `[Monitor timed out]` is not.

⭐ **Standing rule:** ***a wait that cannot observe its target is not a wait, and must not be reported as
one.***

---

## Why these two arrived together

The sender flags it and we think it is the real content: **§2 is the same archetype as the
`hard_quota`-vs-size-cap misclassification** we routed to `review-apparatus` from this same plan. In both
cases **a taxonomy collapses "not yet" into the same bucket as "never, given this configuration",
destroying the one bit that determines what to do next.** Two independent instances inside a single
plan, on unrelated surfaces — which is what makes it a class rather than a bug.
