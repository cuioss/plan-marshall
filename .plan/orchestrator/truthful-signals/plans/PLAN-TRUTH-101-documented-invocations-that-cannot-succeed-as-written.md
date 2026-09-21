# PLAN-TRUTH-101: Documented invocations that cannot succeed as written

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-101-documented-invocations-that-cannot-succeed-as-written.md` and is
> queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

Three documented invocations in this repository cannot succeed as written, and each one's failure names
the wrong cause — so a caller who trusts the doc is sent to fix something that is already correct. Close
all three, and add the contract test that stops a documented example from drifting away from the validator
that governs it.

⭐ **The unifying defect is not "a stale doc". It is that the failure MISDIRECTS.** A rejection that named
its real cause would cost a caller seconds; each of these costs a diagnosis. That is why they are one plan:
the remedy shape is shared, and it is the contract test, not the individual edits.

## Deliverables

Six deliverables, under the epic's split guard of 12. D0 is a gate.

**D0 — GATE: derive the POPULATION before fixing any member.** Enumerate every documented example and
prescribed invocation in the touched skills and check each against the validator or runtime that actually
governs it. ⛔ **Publish the enumerated count and the checked count as two numbers.** The three known
members below were each found by a different accident — one by an operator hitting it, one by three failed
attempts, one by an exit 127 — which is evidence that the population was never swept. **A fix that closes
only the three known members and reports "done" repeats the defect this epic exists to remove.**

**D1 — `parse_stdin_task` MUST NOT discard input silently.** *(D-1332-c, from PR #1332 / L11)*
`manage-tasks/scripts/_tasks_core.py` `parse_stdin_task` recognises a narrow set of line shapes and its
outer dispatch chain ends in a bare `else: i += 1` — **no unrecognized-line diagnostic anywhere in the
function.** An empty `steps` list produced by silent discard is then indistinguishable from a genuinely
absent field, and the raise says `Missing required field: steps (at least one step required)` — so the
caller edits the field that is plainly there. Observed: three rejections with differing shapes, identical
message; `batch-add` with equivalent JSON succeeded first try.
**Remedy:** collect unrecognized non-blank lines and, on a validation failure, report them —
*"the following lines were not recognized: …"*. ⭐ That single change turns all three failed attempts into
a diagnosis.

**D2 — accept the canonical TOON tabular header, or name the accepted spellings in the error.**
`_matches_steps_header` accepts `steps:` and `steps[3]:` and **rejects `steps[3]{target,intent}:` — the
length-declared tabular form this project's own TOON output uses everywhere.** The list-body walker
additionally requires the exact prefix `'  - '`, so four-space indent, a tab, or a zero-indent `- ` each
terminate the walk on the first item. Widen the matcher (and the same for `skills` / `commands`), or state
the accepted spellings in the rejection. ⚠ Whichever is chosen, D1 still applies — a widened matcher with
a silent discard behind it fails the next unanticipated shape exactly as this one did.

**D3 — repair the two `manage-tasks/SKILL.md` examples so they pass their own validators.**
`SKILL.md:518-521`'s canonical TOON block uses prose steps, which `validate_steps_are_file_paths` rejects
and which carry none of the `(intent)` suffix `_STEP_INTENT_SUFFIX_RE` requires. `SKILL.md:638` and `:654`
give batch payloads with bare-string steps, which `_validate_batch_entry` explicitly rejects
(*"bare-string steps are rejected"*). ⇒ **The two worked examples a caller reaches for first are both
stale relative to validators in the same skill.**

**D4 — drop the `uv run` prefix from `finalize-step-deploy-target`.** *(D-1332-e, from PR #1332 / L8)*
The step doc prescribes `uv run python marketplace/targets/generate.py`; `uv` is not on PATH in the shell
the finalize step executes in, so the documented invocation exits **127**. The generator has no
`uv`-specific dependency — under system `python3` it produced the full 1167-entry output and the correct
version stamp. ⚠ **`exit 127 / command not found` gives no indication that the PRESCRIPTION is wrong rather
than the machine being broken**, so a caller reasonably goes looking for a missing prerequisite. Drop the
prefix (matching how every other marketplace script is invoked here); if `uv` is genuinely required for
some target, probe for it and fail with a message naming it as a missing prerequisite instead of a bare 127.

**D5 — the contract test, and it is the deliverable that outlives the other four.** Feed **each documented
example through its own validator**, so a doc and the code that governs it cannot drift again. ⛔ The test
MUST be **population-derived**, per this epic's standing rule: enumerate the documented examples from the
source rather than restating them as literals, and **publish the population size**, so a suite that
degenerates to zero examples cannot report green. ⚠ **`test_inject_project_dir.py` is the cautionary
precedent inside this very family** — it re-declared a whitelist as a literal list and asserted against a
command shape no production caller writes, which is how it locked a defect in rather than catching it.

## Claim Labels

Checked first-party at HEAD `f6d058b4b` on 2026-08-23 unless marked otherwise; re-ground at the plan's own
HEAD before relying on any one of them.

- **OBSERVED** — the `triage.md` `deliverable: 0` defect is **NOT in this plan's scope** and is already
  tracked with a sharper diagnosis: `_tasks_core.py:278` already tests presence, `:279` defaults an absent
  deliverable to `0` (erasing ABSENT vs EXPLICIT-0), `:536-537` raises when
  `deliverable == 0 and origin != 'holistic'`, and **the real fix is that the template omits
  `origin: holistic`.** See the epic's API-Sheriff round-6 entry. ⛔ Do not re-derive or re-fix it here.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _tasks_core.py confirms the sharper diagnosis: 'if deliverable not in task: task[deliverable] = 0' defaults an ABSENT deliverable to 0, erasing the distinction between absent and explicit-zero
- **HYPOTHESIS** — that D1 and D2 are separable. If the widened matcher (D2) turns out to require the
  unrecognized-line collection (D1) to be implemented first, say so and sequence them rather than merging
  the deliverables.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: A design-separability bet about D1 and D2, resolved during outline rather than against any implementing source. It carries no confirm/refute artifact because none exists at this tier
- **HYPOTHESIS** — that the population D0 derives contains more than these three members. It was never
  swept, so the honest expectation is "unknown", not "three".
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: States its own expectation as unknown and is settled only by D0's sweep. Unverifiable BY CONSTRUCTION until that sweep runs - which is the correct state, not a defect
- **OBSERVED (foreign machine, NOT reproduced here)** — the three-attempt rejection sequence and the
  exit-127 observation come from PR #1332's run report. The CODE claims above (the `else: i += 1`, the
  header matcher's accepted shapes, the two SKILL.md examples, the validator messages) were verified
  first-party; the *observations of hitting them* were not.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-labelled OBSERVED (foreign machine, NOT reproduced here). The three-attempt rejection sequence and exit-127 came from PR #1332's run report on another machine. This drain reproduced two SIBLING members of the same class first-party (scan-planning-inventory scan exits 2; manage_status underscore notation is rejected) but did NOT reproduce these two, so the claim stands unreproduced rather than corroborated
- OBSERVED *(2026-08-27 cleanup, first-party at `5f972ac15`)*: `scope_creep_check` is structurally inert on every plan — a repo-wide sweep of `marketplace/` and `test/` for `plan_creation_sha` returns exactly four sites and **no writer**: one reader (`phase-5-execute/scripts/scope_creep_check.py`:205), one doc (`phase-5-execute/SKILL.md`:576), and two tests that **hand-construct the field** (`test_qgate_persist_contract.py`:73, `test_scope_creep_could_not_look.py`:46). This is sub-shape C's third and strongest member: consumer implemented, documented AND unit-tested, producer never written.
  - verdict: corroborated | checked_at: 5f972ac15 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Re-derived first-party at HEAD 5f972ac15 during the 2026-08-27 cleanup, not taken from the PLAN-TRUTH-114 landing report. Sweep of marketplace/ and test/ for plan_creation_sha returns four sites: reader scope_creep_check.py:205, doc phase-5-execute/SKILL.md:576, and two tests hand-constructing the field. No writer exists, so every plan takes the no-plan_creation_sha branch and no plan has ever had scope-creep coverage
- OBSERVED: the eleven full-body instances, each with the quoted rejection or the quoted contradicting text
- OBSERVED: `24-09-001`/`26-13-001` and `24-08-002`/`25-06-001` are each ONE defect observed twice — the pairs' titles and bodies name the same site and mechanism
- HYPOTHESIS: the four title/second-hand-derived rows belong here. **Title-only stubs:** `2026-08-25-06-001`, `2026-08-26-13-001`. **Unresolvable** (`list` says `active`, `get` says `not_found`): `2026-08-23-13-002`, `2026-08-08-19-001`. ⛔ **`19-001` is the weakest row in this cluster — nothing in that run read either its title or its body**; its subject is second-hand from `2026-08-08-20-002`. Confirm/refute at the lesson files once the corpus-integrity defect is fixed (verify-at-outline)
- HYPOTHESIS: sub-shapes A/B/C are the right split — ⛔ **the router's cut, not a property of the corpus.** Adopt or re-cut freely at D0.
- ⚠ **Scope-bloat:** 15 candidate members is far past the guard. ⛔ **D0 must decide split-or-proceed and RECORD the rationale** before any implementation.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py`
- `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`
- `.claude/skills/finalize-step-deploy-target/SKILL.md`
- `test/plan-marshall/manage-tasks/test_tasks_core.py`

## Dependencies and Sequencing

⛔ **Re-derive this section with `corpus cross-check` at emit time — do not trust it as written.** It was
authored at staging, and this epic has recorded that a hand-derived collision map is wrong in both
directions.

- **Depends on:** nothing.
- **Overlaps with:** no staged or running plan holds `manage-tasks` or `finalize-step-deploy-target` at
  staging time. Verify against the six running plans' LANDED diffs, not their specs — `affected_files`
  under-recording is a live defect in this epic, so a running plan's real surface can be wider than either
  its spec or its `references.json` shows.
- **Adjacent to:** `plan-marshall/workflow/triage.md` — the `deliverable: 0` template lives there and is
  the sibling defect this plan deliberately does NOT touch (see Claim Labels).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-101-documented-invocations-that-cannot-succeed-as-written.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator
owns every other ledger write — and reports its outcome through its PR and its inbox message. The inbox
exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

---

## ⭐ A FOURTH MEMBER, FOUND BY A FOURTH ACCIDENT — and it is NOT ours to fix (2026-08-24)

Drained from PLAN-TRUTH-075's inbox (`-008`, finding `48dd4c`). **`automatic-review/SKILL.md:681`**
interpolates `--measured-diff-size "{measured_diff_size}"` **unconditionally**, while the Canonical
invocations block at `:976-978` states the opposite — it is not a list flag and must be omitted when
unmeasured. On the common path (no diff-size refusal) `fetch_findings` correctly returns an empty
value, the executor's empty-arg strip reduces it to a bare trailing flag, and **argparse rejects at
exit 2** — which under the guard's own UNKNOWN rule forces a `loop_back` rather than a verdict. ⭐ The
eight genuine LIST flags on the same call are safe because they declare `nargs='?'`; **this scalar flag
is the sole exception and the worked example treats it identically.** PLAN-TRUTH-075's dispatch **hit
it and had to work around it.**

### Why this strengthens D0 rather than adding a deliverable

D0's premise is that the three known members *"were each found by a different accident, which is
evidence it was never swept."* **This is a fourth member, found by a fourth accident — a live dispatch
tripping over it during an unrelated plan's finalize.** Four independent accidents and zero systematic
discoveries is now the strongest form of that argument. ⛔ **D0's population sweep must therefore
include `automatic-review/SKILL.md`**, and the sweep must cover the *scalar-flag-treated-as-list* shape
specifically — the failure here is not a malformed example but a **correct-looking example applied to
the one flag whose argparse declaration differs from its eight neighbours.**

### ⛔ OWNERSHIP: the member is REPORTED here, OWNED by `review-apparatus`

`automatic-review` is a PR-review surface, and this epic's standing routing rule makes it a
**dispatcher, not an owner**, for that theme — the PR test runs first and wins outright. The finding
was forwarded to `review-apparatus` on 2026-08-24.

⇒ **D0 must ENUMERATE this member and then DEFER on it**, recording that the file has another owner
rather than fixing it here. ⛔ Do **not** edit `automatic-review/SKILL.md` under this plan. ⭐ The
contract test this plan's deliverable builds — *feeding each documented example through its own
validator* — **should still cover that file**, because the test is ours and the sweep is ours even
where the individual repair is not. A population that excludes a member because someone else owns its
fix is not a population.

## ⭐ A FIFTH MEMBER, FOUND BY A FIFTH ACCIDENT — and it carries a `lessons-routing` cross-reference (2026-08-24)

From PLAN-TRUTH-095's inbox `-010`. **`.claude/skills/finalize-step-deploy-target/SKILL.md` § "2. Parse
the result" instructs the executor to read the generator's stdout as TOON — a contract the generator
never emits.**

⛔ **D0's population argument is now at FIVE members, each found by a different accident, and still
zero systematic sweeps.** That is no longer suggestive; it is the strongest form the argument can take
short of doing the sweep. ⚠ **This member is `project:`-scoped** (a project-local step under
`.claude/skills/`, not a marketplace bundle) — **D0's sweep must cover `.claude/skills/**` and not only
`marketplace/bundles/**`**, or it will reproduce the very narrowing it exists to prevent.

⭐ **The message also surfaces a cross-epic dependency worth naming here**: its own pickup note observes
that filing a lesson against a `project:` component *"will need `--allow-foreign-store` or a re-homed
component value"* — which is **`lessons-routing`'s `PLAN-LR-02`** (the ownership predicate) in
miniature, met by a real filer. ⛔ Do not fix that here; it is that epic's. Recorded so the two are not
independently re-derived.

## ⭐⭐ A SIXTH MEMBER — and this one was found by an INSTRUMENT, not by an accident (2026-08-25)

Drained from PLAN-TRUTH-094's inbox (`-001`, finding `e2b602`; landing `-008`). PR #1343,
`1169fb5bf`.

**`pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory scan` is documented at
FOUR sites and cannot succeed.** `tools-marketplace-inventory/SKILL.md` lines **335, 349, 352, 355**
each prescribe a `scan` positional the script does not declare; its argparse surface is
`[-h] [--format {full,summary}] [--include-descriptions]`.

⛔ **CORROBORATED FIRST-PARTY AT HEAD `1169fb5bf`, and STILL LIVE** — the drain reproduced it:

```text
scan-planning-inventory.py: error: unrecognized arguments: scan
```

⚠ **Do NOT read #1343 as having fixed this.** #1343 fixed the **detector** (`0abdc8713`) that had been
counting this site as DECIDED; the four documented sites are untouched. The plan's own landing says
the detector defect *"was hiding a live corpus defect"* — the hiding stopped, the defect did not.

⭐⭐ **This member changes D0's argument in kind, not just in count.** The first five were each found by
a different accident, which is why D0 argues the population was never swept. This one was found
because #1343 **shipped the sweep instrument**: `analyze_argument_naming` now publishes
`population_size` (2792) **and** `blind_spots` (304) over the real corpus. ⇒ **D0's population
derivation is now mechanically performable rather than aspirational**, and D0 should be re-read as
"run the instrument that now exists", not "invent a sweep". This is a capability `-101` did not have
when it was staged.

### Recurrence, not a new member — the FIFTH member re-observed

The same finding `e2b602` also reports the `finalize-step-deploy-target` TOON stdout contract. **That
is the FIFTH member above, re-observed by a second, independent plan.** Recorded here as a recurrence
per the drain's dedup discipline; it is NOT a sixth entry and must not be counted as one. Its
independent re-discovery is itself the evidence D0 wants: two plans hit the same undocumented-contract
site without either knowing of the other.

### One genuinely new sub-item folded into D3's class

`e2b602` additionally reports **`.claude/skills/finalize-step-deploy-target/SKILL.md:99`** prescribing
the unregistered notation `plan-marshall:manage-status:manage_status` (underscore). Corroborated
first-party — the executor rejects it with `Unknown notation`, naming the hyphenated form. ⚠ Same
`project:`-scoped `.claude/skills/**` surface the fifth member flagged, so D0's sweep scope is
unchanged by it. The `uv run` half of `e2b602` is already **D4** and is not re-staged.

## A SEVENTH MEMBER — the rejection hint itself misdirects (2026-08-26, PLAN-TRUTH-086 drain)

From inbox `-007` (PR #1351). **The argparse-rejection hint names the wrong verb's flags and suggests
a write verb for a read verb.**

⛔ **This member is different in kind from the other six and raises D5's stakes.** The first six are
*documented* invocations that fail. This one is the **error message the executor prints when an
invocation fails** — the surface a caller reads to recover. A wrong hint does not merely fail; it
**routes the reader to a write verb when they asked to read**, so following the guidance is worse
than ignoring it.

⭐ **D5's contract test gains a second obligation:** feeding each documented example through its own
validator establishes the examples are runnable. It does NOT establish that the **rejection path**
names a recoverable next step. ⇒ Assert on the hint text too — the accept-set it prints must be the
addressed verb's own, and it must not propose a verb from a different read/write class.

⚠ Corroborated in kind, first-party, this session: `manage-lessons set-body` rejected `--id` and
`marshall-steward preflight` rejected the whole notation, both with accept-lists that were correct.
So the hint machinery is **not uniformly wrong** — D0's population sweep must find which sites are,
rather than treating this as universal.

## ⭐⭐ FOLDED 2026-08-27 — 15 lessons of doc-contract divergence, and this plan's D0 is exactly the gate they need

From the `lessons-handling-26-08-26-01` drain, message `-006` (15 lessons). ⚠ **The router flagged it
past the scope-bloat guard and suggested splitting by sub-shape**; its suggested target
(`PLAN-TRUTH-012`) is **SHIPPED**, so this plan inherits the cluster. ⛔ **This plan's D0 already
requires the population be derived first — that gate now governs 15 candidate members, not 3.**

**The failure mode:** a document states a contract the live surface does not implement. The document
reads as authoritative, nothing binds the two, and the divergence is found the expensive way — an agent
hitting the rejection at runtime, mid-phase, one at a time.

### Sub-shape A — a documented invocation the parser rejects (this plan's existing subject)

- `2026-08-23-16-001` — `triage.md` § Step 3c prescribes `deliverable: 0`; the validator's **falsy check** rejects it as *"Missing required field"*. ⛔ **Every fix task allocated through the documented FIX path hits this**, and the workaround **fabricates provenance** — the task claims a deliverable it has nothing to do with.
- `2026-08-24-12-002` — `branch-cleanup.md`'s merge-barrier example passes `--measured-diff-size` unconditionally; with no refusals the value is empty, **the executor strips empty-string args**, and argparse rejects the bare flag. ⛔⛔ **Inside a fail-closed merge gate — the honest outcome is a merge blocked by the documentation of the block.** ⭐ The doc's own prose already explains the `nargs='?'` defence for the eight list flags beside it **and interpolates all nine identically**.
- `2026-08-25-09-008` — `plan-retrospective` Step 5b names `plan-marshall:marshall-orchestrator:orchestrator`; the live notation is `plan-orchestrator`. ⛔ **Every ORCHESTRATED plan's retrospective fails at its recording step**; non-orchestrated ones take the other branch, which is why it survived.
- `2026-08-08-20-003` — ⭐ **the INVERSE of argparse-rejection drift**: `manage-logging read --phase` is declared with a constrained `choices` list, **validates its input, and applies no filter**. The advertised surface is *wider* than the implementation and the call **succeeds wrongly**. `total_entries` reports the unfiltered population either way, **so the count that would expose the no-op corroborates the wrong answer.**
- `2026-08-08-19-001` — the archived-plan audit's argparse-rejection corpus, 463 signatures across 48 of 58 plans. (⛔ Unresolvable — see Claim Labels.)

### Sub-shape B — a stated constraint the mechanism cannot satisfy

- `2026-08-24-09-001` + `2026-08-26-13-001` — **one defect, observed twice.** `automatic-review`'s Branch A `display_detail` renders **86 chars with a non-ASCII em dash** against the same document's stated `<=80 chars, ASCII` cap. ⭐ **Structural, not a typo:** `review_state_summary` is unbounded and grows with the bot roster, so **no fixed template ending in `(unified triage pending)` can honour the cap.** Fires on the three-bot roster this repo actually ships.
- `2026-08-24-08-002` + `2026-08-25-06-001` — **one defect, observed twice.** `pr_intent_section render` **APPENDS** the Intent block while `pr-template.md` declares a **mid-body slot**, so Intent lands below the footer on **every** finalize-generated PR. The second observation adds that the render is **non-idempotent** and truncates at the char budget, losing non-goals.
- `2026-08-26-05-007` — a docstring enumerated **three** conditions returning `False`; the body implemented **two**. The missing one was *"timestamps that do not compare"* — and `<` on strings is **total**, so it always yields a verdict. Mixed ISO-8601 offsets then sort by **wall-clock digits rather than by instant**, silently **INVERTING** the ordering, in the arm that errs toward **crediting participation**. ⭐⭐ **Its fix is the model for this whole plan:** a pinned comparable-shape constant, plus 8 tests including a **matched positive AND negative control**, with the pre-fix run recorded verbatim.

### Sub-shape C — a declared key space or producer that does not exist

- `2026-08-26-08-001` — `data-model.md` says the lane value is *"validated by `validate_lane_override`"*. **Only `finalize-steps set-lane` validates**; the generic `plan <phase> step set --param lane` path writes the same field with **no enum check** and **accepted and persisted `auto`**. ⛔ Both verbs write the same field, so **a reader cannot tell which path they are on.**
- `2026-08-25-09-011` — the plan-efficiency anchor table enumerates `bug_fix`/`feature`/`refactor`; `manage-status change-type-heuristic` emits **`enhancement`**. A plan carrying an unlisted `change_type` is **structurally incapable** of tripping an absolute token anchor.
- `2026-08-25-09-013` — **two of fifteen declared report sections have NO producer.** `executive-summary` is not in the aspect registry at all; `dispatch_boundaries` is in the registry but in **no documented step**, while `analyze-logs` emits that data **nested where the compiler does not look**. ⛔⛔ Both land in `sections_omitted`, which the spec defines as *"benign: nothing was lost"* — **a DROP reported as an OMISSION.**
- `2026-08-25-09-009` — `plan-retrospective`'s Input Contract declares `orchestrated`/`epic` as forwarded and states the body **MUST NOT recompute** them. **The dispatcher sends neither.** A body obeying the prohibition falls through to the default `false` — **the branch that writes to the GLOBAL lessons store instead of the epic inbox.** Silent in both directions.
- `2026-08-23-13-002` — `scope_creep_threshold` is documented as a `marshal.json` override **in two places**, and `scope_creep_check` **never reads config at all**. (⛔ Unresolvable — see Claim Labels.)

### The one lesson that generalises the class

⭐⭐ `2026-08-24-12-002`: **a documented invocation that interpolates a placeholder MUST state what
happens when that placeholder is empty**, because the executor's empty-strip makes *"empty"* and
*"absent"* indistinguishable at the parser. ⛔ **Quoting does not save it — the quotes never reach
argparse.**

⚠⚠ **The analyzer that owns this class cannot see it.** `2026-08-24-09-002` records
`scan_manage_invocation` reporting `findings: 0` while **four divergences of exactly this class sat live
in the tree it had just scanned**, and names those four as its regression corpus. That lesson is folded
into `PLAN-TRUTH-104` (empty-population), **but the two meet here** — and this plan should treat those
four as its own regression corpus too.

## Claim Labels — folded 2026-08-27

> ↪ The bullets filed here on 2026-08-27 were merged into `## Claim Labels` above.
> `_parse_claims` reads ONE `## Claim Labels` section, so claims under a decorated
> second heading were structurally unstampable — the R97/R102 class, self-inflicted.

## ⭐ FOLDED 2026-08-27 (landing #1359) — three more members, two of them LIVE IN MAIN

From the `PLAN-TRUTH-098` landing drain (messages `-001`, `-006`, `-010`).

**Sub-shape A — `work/footprint.txt` is named by two documented capture commands and created by no
step.** `plan-retrospective` `references/routing-decision-verification.md` (aspect 13) and the
**newly-shipped** `references/outline-vs-shipped.md` (aspect 15) both instruct capture into that path.
⛔ **Run verbatim, both aspects exit 1.** They produced fragments in that run only because the agent
**deviated from the documented command**. ⭐⭐ **The new file copied its broken sibling's reference — a
defect propagated by IMITATION into the very deliverable meant to close the gap.** This is D-098-a and
it is LIVE in merged main.

**Sub-shape A — `get-deliverable` was argparse-rejected ELEVEN TIMES IN A SINGLE RUN.** One invocation
shape, repeated; each rejection cost a round-trip. A documented-vs-actual surface divergence with an
unusually high firing rate, which makes it good regression-corpus material for this plan's D0 sweep.

**Sub-shape C — "Phase Dispatch Boundaries" renders on no plan: the consumer key has no producer.**
`compile-report.py` reads a **top-level** `dispatch_boundaries` key; `analyze-logs.py` **nests** it
inside its log-analysis fragment; **no aspect registers it.** ⛔ The omission classifies as **benign**
(`sections_omitted`), so the loud half never fires — a **drop reported as an omission**, the same shape
as `2026-08-25-09-013` already in this plan. ⚠ **Test fixtures hand-construct the key**, so the suite is
**green over a shape production never emits** — a green suite proving a contract production does not
satisfy. This is D-098-b and it is LIVE in merged main.

⇒ **D0's population grows again. Two of these three are shipped defects, not candidates.**

## ⛔⛔ FOLDED 2026-08-27 (landing #1361) — sub-shape C's third member, and it is INERT ON EVERY PLAN

From the `PLAN-TRUTH-114` landing drain (global lesson `2026-08-27-07-001`), **re-corroborated
first-party at `5f972ac15` rather than taken from the report.**

**`scope_creep_check` is structurally inert on EVERY plan: `plan_creation_sha` has readers and tests
and NO WRITER.** A repo-wide sweep of `marketplace/` and `test/` returns exactly four sites:

| Site | Kind |
|---|---|
| `phase-5-execute/scripts/scope_creep_check.py`:205 | **reader** |
| `phase-5-execute/SKILL.md`:576 | doc |
| `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py`:73 | test — **hand-constructs the field** |
| `test/plan-marshall/phase-5-execute/test_scope_creep_could_not_look.py`:46 | test — **hand-constructs the field** |

⇒ **Every plan takes the `no plan_creation_sha` branch. No plan has ever had scope-creep coverage.**
`PLAN-TRUTH-114` proved it by execution: an undeclared file escaped into its footprint and was caught
only **incidentally** by `baseline-reconcile`.

⭐⭐ **This is a STRONGER member than the two already in sub-shape C.** `2026-08-25-09-013`'s sections
have no producer and land in `sections_omitted`; `2026-08-23-13-002`'s config key is never read. Here
the consumer is fully implemented, documented, and **unit-tested** — and the producer was never
written, so the check has run its could-not-look branch and nothing else since it shipped.

⛔⛔ **And the tests hand-construct the key — the SAME archetype as D-098-b, in TWO CONSECUTIVE
LANDINGS.** A green suite over a shape production never emits. ⭐ There is even a test named
`test_scope_creep_could_not_look.py` asserting the could-not-look branch: **the only branch that ever
executes in production is the one the suite treats as the degraded case.**

⚠ **The operator named this as the first of the seven hand-offs to act on.** ⛔ Note the remedy is NOT
merely "write the field": D0 must establish WHO writes it and at which phase boundary, because a sha
written at the wrong moment produces a scope-creep verdict over the wrong baseline — which would
convert an inert check into a confidently wrong one.
