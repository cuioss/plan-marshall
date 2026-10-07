# PLAN-101: The lane router reads the wrong body and counts the wrong things

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> **Split out of PLAN-57 on 2026-07-28.** PLAN-57 grew to seven defects across two independent seams;
> this plan owns the READ/COUNT seam, PLAN-57 keeps the CLASSIFY/ROUTE seam.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and hand-off
> contract.

## ⛔ Read this before scheduling: the split buys LANDABILITY, not throughput

**PLAN-101 and PLAN-57 both edit `manage-status/scripts/_cmd_planning_lane.py`. They are the SAME
serialization class and MUST NOT be paired.** Splitting was done because seven defects across two
seams is too large to land and verify as one unit — **not** to create a parallel slot. A future
session reading two plans must sequence them, never emit both.

**Recommended order: PLAN-101 FIRST.** It fixes what the router *reads*; PLAN-57 then re-baselines
its tests against inputs that are finally correct. ⚠ The reverse order also works (PLAN-99 proved the
route-side defect fires independently of the read-side one), but then PLAN-57's tests encode
assumptions about a body the router does not actually score, and must be re-verified after this lands.

## Objective

The lane router's scope signal is derived from the wrong text and counted with the wrong rule. Fix the
**read seam** — what body is scored — and the **counting precision** — which strings are scope. Both
are upstream of any banding or carve-out decision, which is PLAN-57's subject.

## ⭐ Defect A — the router scores a body that is not the request. CONFIRMED, mechanism settled

Settled first-party 2026-07-28 against the live `orchestrator-read-boundary-self-contradiction` plan,
using this router's own regexes:

- **The ingested spec** contains **11 distinct `_PATH_RE` matches AND a glob**. The router's own rule
  therefore says `single_module` on **two independent grounds**.
- **`references.json` persisted `scope_estimate: surgical`.** Irreconcilable with that body.
- **The `## Original Input` section is EMPTY — 0 bytes.** The ingested spec's own `# PLAN-NN: …`
  heading immediately follows the `## Original Input` heading, so a heading-splitting section parser
  terminates the section instantly. **Verified empty for every orchestrated plan checked** (PLAN-94,
  PLAN-90, PLAN-88, PLAN-99) — structural and universal, not incidental.
- **The `request.md` header region contains EXACTLY ONE path and no glob** — the `source_id:` pointer.
  One path, no glob ⇒ `surgical`. **The persisted value matched the header, not the body.**

⛔ **Consequence: PLAN-41 / #991's fix is INERT for every orchestrated plan.** Ingestion works — the
spec body *is* in `request.md` — but the section the router reads is empty **because the ingested body
carries its own markdown headings**, so the scorer falls back to material whose only path is the
pointer. **The router scores the very pointer PLAN-41 was built to stop it scoring.** Ingestion
succeeded and was made irrelevant by a section boundary.

⚠ **UNEXPLAINED, and D1 owes an answer.** PLAN-94 and PLAN-99 have structurally identical requests —
both an empty `## Original Input`, both a 1-path header — yet persisted **different** values
(`surgical` vs `single_module`). The pure function cannot produce both from the same structure, so
**either something other than `scope_estimate_from_request_pure` writes this field, or the scored input
differs in a way the file does not show.** Do not assume the pure function is the only writer.

## Defect B — the counter cannot tell a TARGET from a CITATION

OBSERVED first-party at HEAD:

- `_PATH_RE = re.compile(r'[\w./-]+/[\w.-]+\.[A-Za-z0-9]+')` (`:89`), consumed by `_distinct_paths`
  (`:97-105`), is a **purely lexical scan of the whole body** with no notion of whether a matched path
  is a *target of the work* or a *citation of a governing document*.
- It **requires a directory separator**, so a target named as a bare filename (`retro_sections.py`,
  `agents.md`) does not match at all. **It over-counts citations and under-counts targets in the same
  pass.**
- It counts distinct **path strings**, never distinct modules or bundles — "4 files across 3 bundles"
  is not a quantity this sensor can express.

**Systemic and self-inflicted:** the `marshall-orchestrator` plan-spec template cites
`orchestration-model.md` three times, so **every spec this epic emits carries a phantom path token
before a single target is named.**

⛔ **But the phantom is NOT what selects the lane** — `surgical` and `single_module` are both in
`_NARROW_SCOPE_ESTIMATES`, so removing it changes the **label**, not the **route**. That half belongs
to PLAN-57. **Do not fix the boilerplate and declare the lane problem solved.**

## Defect C — pointer collapse

`implement {spec}` → 1 path → `surgical` → narrow+concrete → `light`, **counting the pointer's own
path as the work.** This is Defect A's visible symptom in the non-orchestrated case and shares its
fix; kept here so the read seam is addressed as one.

## ⭐ Defect D — the Tier-1 classifiers can only be fed through a SHELL ARGUMENT, so the body is excerpted

**OBSERVED first-party 2026-07-28.** `manage-config recipe-match` and `manage-config aspect-classify`
accept **only `--request-text`** — a shell argument. **Neither offers a `--request-file` /
`--body-file` alternative** (`--help` on both shows `--request-text` and `--threshold`, nothing else).

A realistic spec body is markdown full of backticks and shell metacharacters, so it cannot be passed
verbatim through an argument. **The observed consequence, self-reported by a live plan:** *"Passing
the narrative to the Tier 1 classifiers as a plain-ASCII faithful excerpt (the full spec body carries
backticks that would be shell-interpreted)."* **The classifiers scored a hand-made excerpt, not the
request.**

⛔ **This makes PLAN-41's Step-4 "narrative rebind" UNSATISFIABLE BY CONSTRUCTION.**
`phase-1-init/SKILL.md:299` declares that rebind **load-bearing** precisely because these two
consumers do *not* re-read `request.md` from disk — they consume the in-context narrative. But the
only channel into them is a shell argument the real body cannot safely cross. **The contract requires
passing the ingested body; the surface makes it impossible.** Doc-contract-divergence, and the doc is
the one that calls itself load-bearing.

⚠ **Note the split:** `SKILL.md:301` states four consumers re-read the persisted `request.md`
(domain-detect, both Step 8a.5 heuristics, `planning-lane route`) while **these two** take the
in-context narrative. **So Defects A and D hit different consumers by different routes** — A corrupts
what the file-reading four score, D corrupts what the argument-fed two score. **Fixing one does not
fix the other**, and D1 must address both or say which it defers.

**The obvious remedy is small:** give both verbs a `--request-file` (the deterministic-file-read
pattern `manage-plan-documents request create --body-file` already uses), and have the caller pass a
path rather than prose. ⚠ D1 should confirm no other caller depends on the argument form.

## ⚠ CORRECTION TO THIS SPEC'S OWN REFUTATION — the backtick instinct was RIGHT, at a different site

Three sessions independently proposed "backticks hid the surface" and this spec refutes it below.
**The refutation is correct about `_PATH_RE`** — it has no backtick in its character class and matches
paths inside backticks normally. **But those sessions were pointing at something real:** backticks
*do* break the body, at the **shell boundary** in Defect D, not in the regex.

⭐ **Record this as correct-verdict-wrong-evidence in OUR OWN analysis.** Repeatedly refuting the
stated mechanism without noticing that the instinct pointed at a genuine adjacent defect is the same
failure this epic tracks everywhere else. **Keep both statements: the regex claim is refuted, and the
shell-boundary claim is confirmed.**

## ⛔ REFUTED — do not spend budget here

**"The spec writes its paths in backticks, so the heuristic saw almost none of the real surface."**
Proposed independently by two sessions and **refuted both times**: `_PATH_RE` contains no backtick in
its character class, and **16 paths matched in a spec where all of them are inside backticks.**
Backticks are a non-issue. Recorded because a plausible-and-wrong mechanism that keeps being
re-proposed will eventually be "fixed".

## ⭐ SEVENTH INSTANCE — folded from the PLAN-94 landing (#1040), inbox message 008

**OBSERVED, first-party in PLAN-94's own `decision.log`.** The same predicate mis-routed a plan
whose real footprint was **seven** files:

```text
(manage-status:scope-estimate-heuristic) Classified scope_estimate=surgical
  (distinct_paths=1, glob=False) — pre-route coarse guess
(manage-status:planning-lane) Routed planning_lane=light (predicate=signal_set, ...)
```

`distinct_paths=1` against an actual 7 — a **7× undercount** — and the operator's own escalation
note names the cause: *"scope heuristic undercounted paths buried in backticked prose"*. This is
Defect D at the shell boundary, not the refuted `_PATH_RE` claim; it corroborates the correction
recorded above rather than the refutation.

⛔ **The consequence is the load-bearing part, and it sharpens D1.** Only a MANUAL operator
escalation to `deep` prevented the light route. The deep lane is what ran the outline Q-Gate that
found `doc/concepts/orchestration.adoc:31` — the fourth live restatement, outside the request's
stated constraints, that the fix needed. **The light lane would have shipped an incomplete fix and
nothing automated would have said so.** A confidently-wrong `surgical` does not merely mis-size the
plan: it removes the check that would have caught the mis-sizing. **Self-sealing failure — the
wrong answer disables its own detector.** Human intervention was the only control.

**Second, independent instance in the same run — the aspect classifier:**

```text
(plan-marshall:phase-1-init) Request aspect classified: implementation
  (confidence=0.055, below 0.7 threshold - conservative fallback)
```

`0.055` against a `0.7` threshold is not weak evidence, it is *no* evidence — yet the run persists
`request_aspect: implementation` into `status.metadata`, where every downstream consumer reads it as
a fact with no confidence attached. The phrase *"conservative fallback"* makes the outcome sound
**safer** than an abstention, when a coin-flip was promoted to a stored attribute.

**What this adds to the deliverables** (fold, not a new deliverable — D1 and D3 already own the
seam):

- **Abstain below threshold.** A classifier landing below its own stated threshold persists
  `unknown` or omits the field — never the argmax label. A label stored without its confidence
  loses the only information that qualified it: the confidence lives in the decision log, the label
  lives in `status.metadata`, and **only the label is read downstream**.
- **Escalate on abstention, never default.** A one-way ratchet to the WIDER lane on `unknown` is the
  safe direction. Current behaviour defaults to the **narrower** lane on the weakest evidence.
- **Report the input basis.** `distinct_paths=1` is the falsifiable part of the claim and is already
  logged. A low path count derived from a request containing many backticked paths is a
  low-confidence estimate, not a `surgical` verdict — and a **backtick-token count is enough to flag
  the disagreement** without solving the general parsing problem.

## Deliverables

1. **D1 — GATE (mutates nothing): settle what the router SHOULD read, and explain the discrepancy.**
   Establish the real scored input for both PLAN-94 and PLAN-99 and account for the differing persisted
   values. Decide the correct source: the full `request.md`, a named section, or the ingested body
   located some other way. ⚠ **An empty read must become a declared outcome, never a silent
   classification** — a scorer that reads 0 bytes and still emits a band is this epic's flagship
   archetype, and it is the actual defect here.
2. **D2 — fix the read seam.** Implement D1's verdict at `_read_request_body` (`:125-144`). ⚠ The
   ingested body carries its own headings; whatever mechanism is chosen must be robust to that, since
   it is the normal case for every orchestrated plan.
3. **D3 — counting precision.** Address target-vs-citation discrimination and the directory-separator
   requirement. ⚠ If reliable discrimination is not achievable at this layer, **say so and make the
   sensor declare its own inapplicability** rather than emitting a confident band — that is a
   legitimate and preferable outcome.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) An orchestrated spec with N>3 paths and a glob
   scores `single_module`, not `surgical`. (b) An empty scored body yields a declared-unknown, not a
   band. (c) A bare-filename target is counted, or its exclusion is asserted as intentional.

Four deliverables, under the split guard.

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-28): the empty `## Original Input` section across four live
  plans; the 1-path header; the 11-path-plus-glob spec body; the persisted `surgical`.
- OBSERVED: `_PATH_RE` at `:89`, `_distinct_paths` at `:97-105`, `_read_request_body` at `:125-144`,
  `_NARROW_SCOPE_ESTIMATES` at `:76`, `_GLOB_RE` at `:122`.
- OBSERVED: the plan-spec template's three citations of `orchestration-model.md`.
- HYPOTHESIS: that a writer other than `scope_estimate_from_request_pure` sets `scope_estimate` —
  confirm/refute by tracing every writer of `references.json` `scope_estimate` (verify-at-outline).
  **This is D1's core question.**
- Verify-first clause: re-read `_read_request_body` and `_PATH_RE` at HEAD before scoping. If PLAN-57
  landed first and altered either, re-baseline rather than proceeding against this spec.

## Expected Surface

- OBSERVED: `manage-status/scripts/_cmd_planning_lane.py` — `_read_request_body` `:125-144`,
  `_PATH_RE` `:89`, `_distinct_paths` `:97-105`, `scope_estimate_from_request_pure`,
  `cmd_scope_estimate_heuristic`.
- HYPOTHESIS: the `references.json` write path for `scope_estimate` (verify-at-outline).
- HYPOTHESIS: `marshall-orchestrator/templates/plan-spec.md` — only if D3 decides the boilerplate
  citations should change (verify-at-outline). ⚠ Cosmetic on its own; not a lane fix.
- OBSERVED: tests under `test/plan-marshall/manage-status/**`.

**Disjointness:** `manage-status/scripts/_cmd_planning_lane.py`.
⛔ **SAME FILE AS PLAN-57 — sequence, NEVER pair.** ⚠ Also shares the `manage-status` test tree with
PLAN-57.

## Dependencies and Sequencing

- Depends on: none. **Recommended to run BEFORE PLAN-57.**
- Overlaps with: **PLAN-57 (same file — never pair)**.
- Adjacent to: PLAN-61 (outline scope derivation) — different phase, but both concern how scope is
  derived; read its findings before D1.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-101-lane-router-reads-the-wrong-body.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
