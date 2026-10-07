# PLAN-02: Seed `file_globs` per domain at wizard time

epic: operator-ux
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-domain-glob-seeding.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`skill_domains.{domain}.file_globs` is the accuracy leg of domain detection: a plan whose
affected files match a domain's globs resolves that domain with no narrative mention at all.
The key exists, is validated, and is read by the detector — but it is absent by default and no
wizard path writes it, so it is inert in any project where nobody set it by hand. Have `skill-domains configure` seed it
from each domain extension's own file-type knowledge, so `src/test/**/*.java` resolves `java`
because of what the files ARE, not because the request happened to say the word. This makes
PLAN-01's over-provisioning narrower and more accurate; without it, domain sets stay wide
forever.

## Deliverables

1. A source of per-domain glob knowledge. The domain extension already knows its file types —
   it implements `discover_modules()` — so the seed reads from the extension rather than from
   a hand-maintained table in core. If no such accessor exists, add one to the extension
   contract; a hard-coded map in `manage-config` would put language knowledge in the core,
   which `doc/adr/004` forbids.
2. `_cmd_skill_domains.py`: `configure` seeds `file_globs` for each selected domain from that
   source, on first configuration only.
3. Preservation semantics: an operator-set `file_globs` (via `set-inclusion`) is never
   overwritten by a later `configure`, mirroring how `project_skills` / `active_profiles`
   already survive a reconfigure.
4. `skill-domains-setup.md` and `standards/skill-domains.md`: the seeding behaviour, its
   source, and the preservation rule are documented; the "absent by default, no seed"
   statement is corrected where it no longer holds.
5. Tests in `test/plan-marshall/manage-config/test_cmd_skill_domains.py` covering: fresh
   configure seeds globs; reconfigure preserves an operator-set value; a domain whose
   extension exposes no glob knowledge seeds nothing and stays valid.

## Claim Labels

- OBSERVED: `file_globs` is read by the detector's inclusion leg and validated by
  `validate_domain_inclusion` — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § `_glob_matched_domains` and
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
  § `validate_domain_inclusion`.
- OBSERVED: The only writer of `file_globs` anywhere is the manual
  `skill-domains set-inclusion` verb; no `marshall-steward` path writes it. Asserted as an
  ABSENCE and verified as such — a grep for `file_globs` and `always_on` across the whole
  `marketplace/bundles/plan-marshall/skills/marshall-steward/` tree returns zero hits.
  - verdict: corroborated | checked_at: 9fd0957 | by: operator-ux/cleanup | rescoped: n/a | evidence: grep for file_globs/always_on across marshall-steward/ returns 0 hits at this sha; the writer-absence claim holds
- ⛔ **PARTIAL REFUTATION of this spec's original framing, recorded 2026-09-02.** The
  "inert in every project" claim this spec was written on is too strong: THIS project already
  carries `file_globs: ['**/*.py']` on the `python` domain (read via
  `manage-config skill-domains get --domain python`), hand-set rather than seeded. The
  writer-absence claim above still holds; what is refuted is the inference that no project has
  globs. Two consequences for outline: the seed must not clobber a hand-set value (deliverable
  3 already requires this, and it is now load-bearing rather than defensive), and the
  before/after benefit measurement must not assume an empty starting state.
  - verdict: corroborated | checked_at: 9fd0957 | by: operator-ux/cleanup | rescoped: n/a | evidence: _cmd_skill_domains.py still preserves project_skills and active_profiles across reconfigure
- OBSERVED: Correct globs are necessary but NOT sufficient. A live instance was observed where
  `python` carried `**/*.py` and was still omitted, because at init the glob leg's file signal
  is path tokens scraped from the NARRATIVE, not a real file list — a prose request naming no
  `.py` path leaves the leg empty regardless of configuration. The class fix is PLAN-10; this
  spec's value is unchanged but its ceiling is lower than originally implied.
- OBSERVED: `configure` already preserves `project_skills` and `active_profiles` across a
  reconfigure — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py`
  § the reconfigure preservation block (~L836–L868). This plan extends that existing pattern
  rather than inventing one.
- HYPOTHESIS: A domain extension exposes, or can cheaply expose, the file-type knowledge the
  seed needs — confirm/refute at the domain-extension contract in
  `marketplace/bundles/plan-marshall/skills/extension-api/` § the extension interface that
  declares `discover_modules()` (verify-at-outline). ⛔ If no such accessor exists and adding
  one is out of proportion, re-scope: the fallback is a per-bundle declaration in the
  extension's own manifest, NOT a table in `manage-config`.
- HYPOTHESIS: Seeding globs cannot *narrow* an existing project's resolved domain set, because
  the glob leg is a union member and only ever adds — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § the `inclusion_union` composition (verify-at-outline).
- Verify-first clause: confirm at outline that `doc/adr/004` governs this boundary as stated —
  that file-to-domain knowledge is owned by the extension and not by the core — before
  choosing where the glob source lives.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/skill-domains-setup.md`
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_skill_domains.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/` — the domain-extension
  contract doc that would declare the glob accessor (verify-at-outline; the exact file is
  settled by the extension-contract claim above)

## Dependencies and Sequencing

- ⛔ **PLAN-01 changed the `manage-config` script surface without declaring it.** #1380
  (merged `bf012b2cd`) touched `_cmd_skill_resolution.py`, `manage-config.py` and
  `query-config.py`, none of which appeared in any spec's Expected Surface. Re-read
  `manage-config/SKILL.md`, `standards/skill-domains.md` and the detector at outline: both
  documents were rewritten by PLAN-01, so this spec's quoted contract text may be stale.
- Depends on: none strictly, but sequenced after PLAN-01 to avoid a doc collision on
  `skill-domains.md` / `manage-config/SKILL.md`.
- Overlaps with: PLAN-01 and PLAN-03 (`skill-domains.md`, `manage-config/SKILL.md`);
  PLAN-09 (`marshall-steward` references).
- Adjacent to: `_cmd_domain_detect.py` — this plan changes what the detector READS, never the
  detector itself. Keeping that boundary is what lets PLAN-01 and PLAN-02 be reviewed apart.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-02-domain-glob-seeding.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
