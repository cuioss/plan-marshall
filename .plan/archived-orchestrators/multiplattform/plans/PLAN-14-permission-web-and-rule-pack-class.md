# PLAN-14: The last permission surfaces — the web skill, and the rules as declared material

epic: multiplattform
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to close two inventory rows PLAN-08 explicitly and deliberately excluded.
> Source evidence: `../reference/coupling-inventory.md` §B rows 5 and 8;
> `plans/PLAN-08-permission-skills-through-the-registry.md` § Out of Scope.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

PLAN-08 closes the permission-skill coupling for `tools-permission-doctor` and `tools-permission-fix`,
and excludes two neighbours **on stated reasons, not by oversight**. `workflow-permission-web`'s
`permission_web.py` renders `WebFetch(domain)` grammar and performs Claude settings I/O itself — the
same class of defect, excluded because folding it in roughly doubles PLAN-08's surface and review
burden. Separately, `permission_doctor.py`'s analysis rules and the three permission standards
documents carry the Claude permission model as *analyzed subject matter* — a different class from
render/import residue, and one PLAN-08's surface does not reach. Close both, consuming the semantic
vocabulary PLAN-08 built rather than inventing a second one.

## Deliverables

1. **D1 — `permission_web.py` routes and states intent.** It renders `WebFetch(domain)` strings and reads/writes the settings JSON directly. Route both through the registry, consuming PLAN-08's semantic vocabulary. ⛔ The in-tree precedent is already exactly right here: `permission_web_apply` **takes domain names** — the argument is already semantic, so this is a routing fix, not a vocabulary invention.
   *Done when:* `permission_web.py` performs no settings I/O of its own and renders no permission-DSL string; an OpenCode-target project driving it gets a real result or an honest `no-op`, never a written `.claude/settings*.json`, pinned by a test that sets `runtime.target` to a non-Claude value.
2. **D2 — The permission rule-pack class is declared.** `permission_doctor.py`'s analysis rules and `standards/permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md` state the Claude permission model as the model. Declare them as Claude rule-pack material — the same treatment `plugin-doctor`'s documented, swappable Claude rule-pack already receives — or route the target-neutral half and declare the remainder.
   *Done when:* a reader of each document can tell which statements bind them on a non-Claude target; the doctor's analysis rules name their rule-pack; no document states a Claude permission rule as universal.
3. **D3 — Report both inventory rows for retirement.** Re-run each row's own detection against the tree and report the result. ⛔ The plan does **not** edit `../reference/coupling-inventory.md` — it is ledger-resident and off-limits. A row whose detection still finds something **stays, narrowed to the residue**.
   *Done when:* the PR body and the inbox message carry each row's re-run detection and its verdict.

## Out of Scope

- **`permission_common.py`, `permission_doctor.py`'s runtime binding, and `permission_fix.py`** — PLAN-08's surface. ⛔ D2 touches `permission_doctor.py`'s **analysis rules** only, not its imports. If PLAN-08 has not landed, that file is contested: **halt and report** rather than editing it.
- **Inventing a permission vocabulary.** D1 consumes PLAN-08's D2 output. ⛔ If PLAN-08 has not landed, this plan is not buildable as specified — see Dependencies.
- **Deciding what the permission model *means* on OpenCode** — WS-05's territory, needing a live install.
- **The `Grep`-tool deny-set question** — an operator policy call recorded as an epic Open Defect, not a plan deliverable.

## Claim Labels

- OBSERVED: `permission_web.py` renders `WebFetch(domain)` strings — read at `permission_web.py:469-471` (`f'WebFetch({d})'`) — and performs raw settings I/O — read at lines 461 and 497–502. Re-derived at HEAD `2cd1a19c`.
- OBSERVED: PLAN-08 excludes this file on a stated reason and records that the row stays open and un-drawn — read at `plans/PLAN-08-permission-skills-through-the-registry.md` § Out of Scope. This plan is the draw.
- OBSERVED: the three permission standards documents exist — `permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md`.
- OBSERVED: `permission_doctor.py` carries analysis rules encoding the Claude permission model, distinct from its `from claude_runtime import` binding at line 27 (which is PLAN-08's D3).
- OBSERVED: `plugin-doctor` is a target-agnostic engine with a documented, swappable Claude rule-pack — the precedent D2 mirrors; read at `plugin-doctor/references/rule-provenance.md`.
- OBSERVED: `permission_web_apply` takes **domain names** — read at `runtime_base.py::permission_web_apply`. D1's argument surface is therefore already semantic; only the routing and the settings I/O move.
- HYPOTHESIS: PLAN-08's semantic vocabulary covers every crossing `permission_web.py` needs — confirm/refute against PLAN-08's landed D2 output (verify-at-outline). ⛔ If it does **not**, extend that vocabulary in place rather than adding a parallel one, and report the extension.
- HYPOTHESIS: the target-neutral half of the permission standards is separable from the Claude-specific half — confirm/refute by reading the three documents (verify-at-outline). A document that turns out wholly Claude-specific is **declared**, not split; that is a legitimate outcome.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-permission-web/scripts/permission_web.py` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-permission-web/SKILL.md` — D1's command table
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py` — D2, **analysis rules only**
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md` — D2
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/**` and `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — only if D1's routing needs a signature change PLAN-08 did not make; recorded and made minimally (verify-at-outline)
- OBSERVED: `test/plan-marshall/workflow-permission-web/**`, `test/plan-marshall/tools-permission-doctor/**`

## Dependencies and Sequencing

- Depends on: **PLAN-08**. ⛔ **Hard dependency, not a preference.** D1 consumes the semantic vocabulary PLAN-08's D2 produces, and D2 edits a file whose imports PLAN-08 is rewriting. Building this first would either invent a second vocabulary — the exact coupling-inverted outcome PLAN-08 exists to prevent — or collide mid-file.
- Depends on: **PLAN-09** by preference, not requirement. If PLAN-09 lands first, the ABC's operation count and decline vocabulary are settled and D1's conditional surface shrinks.
- Overlaps with: **PLAN-08**, **PLAN-09** on `platform-runtime/scripts/**` and `permission_doctor.py`; **PLAN-06** and **PLAN-07** conditionally on `contract.md`. ⛔ Not concurrent with any of them.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint, subject to its own platform-runtime caveat).

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- **The no-Claude-write pin (D1)**, mirroring PLAN-08's: drive the web-permission subcommands with `runtime.target` set to a non-Claude value and assert no `.claude/settings*.json` is created.
- **A cold read of the declared standards (D2):** a reviewer reads each of the three documents without the plan in context and answers "which of these rules bind me on a non-Claude target?" An answer of "all of them" or "I cannot tell" means D2's declaration failed.
- The two inventory rows' own detections re-run and reported, with the residue-narrowing rule applied.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-14-permission-web-and-rule-pack-class.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. D3 **reports** its row re-derivations through that
message; the orchestrator retires the rows from the landing.
