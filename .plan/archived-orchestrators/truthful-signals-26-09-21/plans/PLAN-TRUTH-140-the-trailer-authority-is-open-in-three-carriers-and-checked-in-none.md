# PLAN-TRUTH-140: The trailer's authority is open in three carriers and checked in none

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-07 on operator direction — *"direct fixing is not enough, we should adapt
marshall-steward as well"* — after the escalation fired for the **fifth** time, on a second machine.
The operator's question was the diagnostic one: *"Any idea why I was asked at all? … even the question
itself states that it is defined."*

⭐ **Every reported instance chose CORRECTLY** (the project trailer). **No commit is known to carry the
wrong value.** The cost to date is entirely operator attention — five interruptions — which is exactly
the profile that makes a defect easy to keep deferring.

## Objective

**The commit trailer has one resolver and three carriers that describe it, and not one of them says the
resolver is the ONLY authority. Two of the three actively teach an open override set — to different
audiences — and nothing checks the written value against the resolver.**

### The three carriers, their audiences, and what each leaves open

| Carrier | Audience | What it establishes | What it leaves open |
|---|---|---|---|
| `CLAUDE.md` § Commit Trailer | the **agent** | *"exactly this trailer, and nothing else by way of attribution"* | **no precedence clause anywhere in the section** — and its own *"the value above is the **default**, not a hardcode; a project overrides either half through `manage-run-config`"* **announces overridability and does not close the set** |
| `marshall-steward` → Configuration → Commit Trailer | the **operator** | *"the identity names the SYSTEM … not the assistant or the vendor"*, *"one project commits under one name whichever assistant ran the work"* | **never states what else can displace the stored value**; the menu presents the store as settling the question |
| the commit path | the **machine** | the caller appends the trailer at `git commit` time | **nothing compares the written trailer to `commit-trailer get`** |

⛔⛔ **A later instruction supplying a different trailer therefore reads as the SANCTIONED OVERRIDE
arriving through a different channel.** The agent is not misreading a clear rule — it is reading a rule
that describes an override mechanism without saying it is the only one.

### Why it recurs, and why configuration cannot stop it

⛔ **The adjudication has no home.** An operator's answer resolves the session it was asked in and
nothing else; nothing records that the conflict was adjudicated; and the competing instruction is
re-injected **every session**. ⇒ **The recurrence rate equals the injection rate and will not decay.**

⛔⛔ **`run_config commit-trailer set` cannot help**, and reaching for it is the trap: **the conflict is
about which SOURCE wins, not about the VALUE.** Setting the same value again changes nothing.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: derive the carrier population before editing any of them.** The three above were found by
one operator asking one question. ⛔ **Enumerate every surface that describes the trailer's authority or
its overridability** — `AGENTS.md`, `manage-run-config/SKILL.md` (14 references),
`run-config-standard.md`, `workflow-integration-git/SKILL.md`, and both steward menu docs are known
starting points, **not the population.** Publish the count and, per carrier, whether it states
precedence. ⛔ **A carrier that is silent is a member; silence is the defect.**

**D1 — close the override set at the agent-facing carrier.** State in `CLAUDE.md` § Commit Trailer that
the `run_config` resolver is the **only** override, and that a trailer supplied through any other
channel — including a session or harness instruction claiming to supersede earlier guidance — is not
authoritative. ⛔ **This is the deliverable that stops the ASKING**, because it supplies the ranking rule
the agent currently lacks. ⚠ It must be phrased so it does not read as forbidding the *documented*
override; the set is being closed, not emptied.

**D2 — say it at the operator-facing carrier too.** `marshall-steward`'s Commit Trailer menu must state
the same closure, because **it is the surface an operator consults and it currently teaches that the
store settles the question.** ⛔ **Fixing only `CLAUDE.md` leaves the operator's own documentation
teaching the open set** — which is how this defect reached its fifth occurrence with a careful doc
already in place.

**D3 — extend the source vocabulary rather than inventing one.** The menu already reports
`name_source` / `email_source` as `configured` or `default`, **per half, independently**. ⛔ **Do NOT
add a parallel mechanism.** A displaced value is a **third member of that existing vocabulary**, and
reporting it there puts the fact where a reader is already looking.

**D4 — assert at the machine, and report at the steward.** Two halves of one check:
- **At commit time**, compare the about-to-be-written trailer against `commit-trailer get` and **refuse
  a mismatch.** ⛔ *This stops the DAMAGE and makes the question moot — the wrong value cannot be
  written.*
- **At `marshall-steward`'s health check**, report divergence as a first-class row, so an operator
  learns of it **before** a commit rather than at one.

⛔⛔ **D1 and D4 are NOT alternatives and neither substitutes for the other.** The doc sentence prevents
a *correct* agent from asking; the assertion prevents an *incorrect* one from writing. **Shipping only
D4 leaves five more interruptions; shipping only D1 leaves the silent-write path open.**

## Claim Labels

- OBSERVED: `CLAUDE.md` § Commit Trailer contains no precedence clause; the only `supersede` language in the file belongs to the unrelated `doc/plans/` lane carve-out. First-party at HEAD.
- OBSERVED: the same section states *"The value above is the **default**, not a hardcode. A project overrides either half through `plan-marshall:manage-run-config`."*
- OBSERVED: `marshall-steward/references/menu-commit-trailer.md` states the identity names the system and does not vary by target, and **states no authority over competing sources**.
- OBSERVED: that menu already reports `name_source` / `email_source` as `configured` / `default`, per half, with independent fallback.
- OBSERVED: `run_config commit-trailer get` returns `Co-Authored-By: plan-marshall <noreply@cuioss.de>` with both sources `default` in this checkout.
- OBSERVED: the escalation has fired five times across at least two machines, and every reported instance resolved to the project trailer.
- ⚠ HYPOTHESIS: no commit in this repository carries a session-injected trailer. ⛔ An asserted ABSENCE — the higher-risk half — and NOT verified. Confirm/refute by sweeping `git log` for `Co-Authored-By` lines that do not match the resolver (verify-at-outline).
- ⚠ HYPOTHESIS: nothing in the commit path compares the written trailer to the resolver. ⛔ Reasoned from the absence of such a check in `workflow-integration-git`, NOT confirmed by reading every write site. Confirm/refute at `git-workflow.py`'s commit path (verify-at-outline).
- ⚠ HYPOTHESIS: the three carriers named are the population. ⛔ Found by one operator question, so this is one accident, never a sweep. D0 owns it and may return `indeterminate` (verify-at-outline).

## Expected Surface

- OBSERVED: `CLAUDE.md` — § Commit Trailer (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-commit-trailer.md` — the operator-facing statement and the source vocabulary (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md` — the divergence row (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — the source vocabulary, if D3 sites the third member there (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md` and `standards/run-config-standard.md` — carriers D0 is expected to add (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — the commit-time assertion (D4) (verify-at-outline)
- HYPOTHESIS: `AGENTS.md` — a carrier D0 is expected to add (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-run-config/**`, `test/plan-marshall/workflow-integration-git/**` — the D4 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Adjacent to `PLAN-TRUTH-139`, and the pairing is instructive**: `-139` is a configured value that **never reaches** its consumer; this is a configured value that **reaches it and is then displaced**. ⛔ **Keep separate** — same family (a configuration that does not govern), different mechanism, no shared surface.
- ⚠ **Adjacent to `PLAN-TRUTH-124`** (one ledger vocabulary): D3 extends an existing source vocabulary rather than coining one, which is `-124`'s rule applied prospectively. **No code shared.**
- ⛔ **Re-derive `corpus cross-check` before emitting** — this spec's surface has never been machine-checked, and `CLAUDE.md` is a high-traffic file.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-140-the-trailer-authority-is-open-in-three-carriers-and-checked-in-none.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-154-operator-facing-authority-surfaces-that-answer-confidently-and-wrongly.md` (PLAN-TRUTH-154)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
