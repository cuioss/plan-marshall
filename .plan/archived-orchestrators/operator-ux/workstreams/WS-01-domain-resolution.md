# WS-01: Automatic domain resolution

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-domain-resolution.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Make skill-domain selection automatic in the ordinary case and self-correcting over the plan
lifecycle, so the ambiguous-domain `AskUserQuestion` stops firing. Three moves, in dependency
order: **over-provision** on a zero narrative match instead of prompting; **seed `file_globs`**
at wizard time so the match is accurate rather than merely silent; and **narrow after
planning**, when the plan's real deliverables and affected files are known and the system
genuinely does know which domains it needed. The workstream closes when a plan whose request
names no domain by name resolves its domain set end-to-end without an operator prompt, and the
set it lands on is no wider than the work required.

## Scope

- In scope: the domain detector (`_cmd_domain_detect.py`) and its `always_on` / `file_globs`
  inclusion legs; the wizard's domain-configuration step (`_cmd_skill_domains.py`,
  `skill-domains-setup.md`); the post-planning re-resolution point in `phase-2-refine` and its
  successor phases; `standards/skill-domains.md` and the `manage-config` surface docs for all
  three; the `references.domains` write path.
- Out of scope: the *wording* of any prompt that survives (WS-03 owns prompt-context quality,
  WS-05 owns remediating the sites); the autonomy gate defaults (WS-02); whether an
  `interaction_mode` may re-enable the prompt for a deliberate expert (WS-06 may add that knob
  on top, but this workstream's default stands alone and does not depend on it).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-domain-over-provision | staged | Zero narrative match unions the ranked candidates instead of prompting |
| PLAN-02-domain-glob-seeding | staged | `skill-domains configure` seeds `file_globs` per domain from extension knowledge |
| PLAN-03-domain-post-plan-narrow | staged | Re-resolve and NARROW the domain set once real deliverables are known |

## Sequencing and Surface Notes

- **PLAN-01 → PLAN-03 is a hard sequence.** Both edit `_cmd_domain_detect.py`. PLAN-03 also
  needs PLAN-01's over-provision branch to exist before narrowing has anything to narrow.
- **PLAN-02 is surface-disjoint from PLAN-01** in its primary file (`_cmd_skill_domains.py`
  vs `_cmd_domain_detect.py`) but both touch `standards/skill-domains.md` and
  `manage-config/SKILL.md`. Treated as overlapping and sequenced; the doc collision is not
  worth the rebase.
- This workstream collides with WS-02 (PLAN-04) on `manage-config/SKILL.md` and
  `extension-api/standards/marshal-json-reference.md`. Sequence, do not pair.
- Safe parallel partner for anything here is WS-04 (persona/standards surface) — no shared
  files.
- **Narrowing is a safety-bearing change, not a cleanup.** Dropping a domain that a task's
  skill resolution already consumed would silently change how that task is executed. PLAN-03
  carries the constraint that narrowing may only remove a domain no resolved task depends on.
