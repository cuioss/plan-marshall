envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-24T12:42:44Z

# finding (high, recurrence of `lessons-routing-044`): documented script surfaces that the scripts do not declare, with live residue at HEAD

**Severity:** high, as filed in `lessons-routing-044` (script surface drift). **Bundle:** `plan-marshall`. Filed as recurrence evidence because `-044` is already consumed and cannot be amended.

**Ground truth (orchestrator re-read at `3da9e1f44`).** `phase-3-outline/SKILL.md:785` reads "Q-Gate findings (qgate add/query/resolve)". Drafting-leaf reading, not re-read by the orchestrator: the same wording stands in `phase-2-refine/SKILL.md` (`:366`) and `phase-4-plan/SKILL.md` (`:1243`); `manage-findings list` declares no `--limit` and no doc names it; `get-deliverable` is invoked with `--number` where the script takes `--deliverable-number`; bot flags are used bare where the script takes the pair form.

**Recurrence.** Eight sources across two repositories: `libraries-initial-implementation-003`, `-004`, `-011`, `-022`, `-023`, `-061`, `-066`; `client-framework-aspects-011` (records 1-2: `manage-findings list --full`, `inbox detect` without `--source-id`; record 3 is refuted, the flag exists since #2012). The matching earlier lesson is TokenSheriff `2026-11-11-12-003`, archived low in the 2026-11-16 sweep with this same residue named.

**Ask of `live-blockers`.** Quote the canonical form at every call site (`qgate list --plan-id P --phase PH`, `get-deliverable --deliverable-number`), decide whether a cross-phase `qgate list` (no `--phase`) exists or is documented as absent, have the executor diagnose underscore notation, and add a canonical-invocation guard test over these call sites. Check the owner of `-044` first and amend its plan rather than opening a new one.
