# Migration / Back-Compat Shim Marker Convention

A **migration or back-compat shim** is a code path that reads persisted state, config, or data and
accommodates a shape an **earlier version of this tooling once wrote and the current version no
longer writes**. Left unmarked, a shim carries no owner, no record of *what* it tolerates, and no
record of *since when* — so nobody can prove it is safe to delete, and shims accumulate. This
convention gives every shim an owner, a version floor, and a removal trigger **at its definition
site**, so a shim is a deletable, auditable thing rather than a permanent unexplained widening of a
reader's accepted input.

The convention is enforced at edit time by the `shim-marker-missing` plugin-doctor rule (see
`pm-plugin-development:plugin-doctor` → `references/rule-catalog.md`).

## What counts as a shim (and what does not)

A site is a shim when it reads persisted data and accommodates a shape **our own earlier writer
produced and the current writer no longer produces** — the tell is a reference to a superseded
shape: "written before X existed", "legacy key", "pre-migration", "older format", "retired key".
Two shapes:

- **Category A — one-shot migration that self-disarms.** Reads the old shape, writes the new one,
  and **deletes/pops the old key**. A second run is a no-op. These expire by construction; the
  marker records what they migrate so the migration code itself can eventually be removed.
- **Category B — permanent "tolerate the old shape" read path.** Accepts the old shape on the read
  path and **never disarms**. Each one silently widens the accepted input surface of every reader
  downstream. This is the half that actually accumulates, and the marker's removal trigger is what
  finally makes it deletable.

The following are **NOT shims** and MUST NOT carry a marker (marking them is as wrong as leaving a
real shim unmarked — it dilutes the signal):

- **Ordinary defensive handling of missing / malformed / absent data** that *any* version can
  produce — a missing file, unparseable JSON, a missing key, a non-string value coerced to a
  default. There is no version boundary. Example (a genuine non-shim): a helper documented as
  *"missing status.json, malformed JSON, missing 'created' key, non-string value all return None"*
  is defensive robustness, not a shim.
- **CLI-flag / env-var / API-signature call-site compatibility** — a flag kept but ignored, a
  parameter retained for existing callers, an environment variable honoured as an override. Not
  persisted-data shape.
- **Module re-export aliases** kept for import stability (`# noqa: F401 -- re-export for backward
  compat`). These are governed by the separate `SIMPLICITY_BACKWARD_COMPAT_REEXPORT` rule, which
  asks for their *deletion*; do not double-mark them here.
- **Tolerance of an external system's shape variance** — GitHub login casing, an LSP protocol's
  older field, a filesystem's case-sensitivity. The boundary is another system's, not a past
  version of ours.
- **A deliberate breaking refusal of the old shape** — code that *names* a version boundary only to
  reject the old shape ("no longer accepts …", "written before the rename … will NOT be counted").
  It refuses the old shape; it does not tolerate or migrate it.

The discriminator is a single question: **does this code accommodate a shape a past version of our
own writer produced?** If yes → shim (A or B). If it merely handles absent/malformed input, an
external system's variance, a call-site signature, or refuses the old shape outright → not a shim.

## The marker

Place the marker as a comment block **immediately above the shim's key line or branch** (the read of
the legacy key, the tolerate-branch, or the migrate-and-delete step). It has one anchor line naming
the category and three required field lines:

```python
# SHIM(B): status.metadata.phase_steps entries stored as bare strings before they became dicts.
# shim-owner: manage-status
# shim-floor: the mark-step-done change that switched step storage to {"outcome": ...} dicts
# shim-remove-when: no status.json for an in-flight plan can still carry a bare-string step entry
```

Field semantics:

- **`SHIM(A)` / `SHIM(B)`** — the category (A = self-disarming migration, B = permanent tolerate
  path), followed by `:` and a one-line description of the exact old shape.
- **`shim-owner:`** — the skill or component responsible for the shim (who deletes it when the
  trigger fires). Usually the owning skill directory name.
- **`shim-floor:`** — the version boundary: the change (a PR number, a commit, a release, or a named
  schema version) at or after which the current writer stopped producing the old shape. This is the
  "since when" — the anchor a later reader needs to reason about whether any old-shape data can
  still exist.
- **`shim-remove-when:`** — the concrete removal trigger: the condition under which no old-shape
  data can remain, so the shim is provably dead and can be deleted. An honest long-horizon trigger
  ("when no archived plan predating <floor> is retained") is correct and useful; a shim whose real
  trigger is "never, while old archives persist" states exactly that, which is still far better than
  the silent status quo.

All three fields are **required** and must be non-empty. `shim-floor` and `shim-remove-when` should
be concrete: name the change, name the extinction condition. "Legacy" as a bare rationale is not a
floor.

## Relationship to other conventions

- **The `shim-marker-missing` plugin-doctor rule** enforces this at edit time: it flags a marker
  missing a required field, and flags a high-precision set of unmarked shim indicators. It is
  precision-first (it favours a false negative over firing on defensive code), so it is a backstop,
  not a substitute for applying the marker deliberately when you write a shim.
- **`SIMPLICITY_BACKWARD_COMPAT_REEXPORT`** governs re-export aliases (import lines) and asks for
  their removal. This convention does not overlap it — a re-export is not marked here.
- **The phase-3 outline "clean break vs deprecation shim" decision table** (`plan-marshall:
  phase-3-outline` → `standards/outline-workflow-detail.md`) decides, at plan-authoring time,
  *whether* to introduce a shim at all. When that table's outcome is "deprecation shim with a
  documented removal window", this convention is the mechanized form of that window: the removal
  trigger it tells the author to document is the `shim-remove-when` field here.
