envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:38:32Z

component=project:finalize-step-deploy-target
category=bug

# `finalize-step-deploy-target` prescribes parsing a TOON contract its generator never emits

> Pickup note: the component segment is `project:` (a project-local step under
> `.claude/skills/`, not a marketplace bundle), so `manage-lessons add` will need
> `--allow-foreign-store` or a re-homed component value.

`.claude/skills/finalize-step-deploy-target/SKILL.md` § "2. Parse the result" instructs the
executor to read the generator's stdout as TOON:

| Field | Meaning |
|-------|---------|
| `status: success` | record `outcome=done` and use `emitted_count` for the display detail |
| `status: error` | record `outcome=failed` and surface the `error` field |

and § 3 then interpolates `{N}` from `emitted_count` into
`--display-detail "{N} files emitted to target/claude/"`.

The invoked entry point emits none of that.

## Measurement

The prescribed command (§ 1) is:

```bash
uv run python marketplace/targets/generate.py --target claude --output target/claude
```

`marketplace/targets/generate.py` `main()` writes only prose:

```python
# line 444 — the ONLY stdout line on the success path
print(f'{target_name}: produced {len(generated)} entries')
```

plus, conditionally, one of two more prose lines (lines 472 / 474-477) and `error: ...` /
`warning: ...` lines to **stderr**. There is no `status:` key, no `error:` key on stdout,
and no `emitted_count` key anywhere in the file. Its own module docstring states the real
contract:

> Exits 0 on success, 2 on any failure (unknown target, missing required flag,
> generator-reported error).

An `architecture search --content --pattern "emitted_count"` over the whole inventory
returns exactly two files — `marketplace/targets/claude/target.py` and
`test/finalize-step-deploy-target/test_deploy_target.py`. `target.py` is an *inner*
generator API that `generate.py` does not surface; nothing propagates the key to stdout.

## Consequence

Neither documented branch is reachable. An executor following the step literally finds no
`status` field, and must then either fail the step or improvise. In practice it improvises:
the `outcome` and the `{N}` in `display_detail` are hand-authored from the prose line (or
from nothing), so the step's recorded verdict is a narration rather than a parse. A step
whose success criterion cannot be evaluated reports `done` for the same reasons it would
report anything else — which is the epic's theme exactly.

## Second defect in the same file

§ 3's `mark-step-done` call uses the notation
`plan-marshall:manage-status:manage_status` — underscore in the script segment. The
canonical form throughout the corpus is `plan-marshall:manage-status:manage-status`. This
run's `signal_script_failure_clusters_count` was driven by 9 distinct argparse/notation
rejections, and this is the same class, sitting unexercised in a step body.

## Solution

Pick ONE and make the doc and the code agree:

- **Exit-code contract (smaller change).** Rewrite § 2 to read the exit code (0 → `done`,
  2 → `failed`) and drop `emitted_count` from § 3's `display_detail` template, or derive
  `{N}` from the `produced N entries` prose with the parse stated explicitly.
- **TOON contract (matches the rest of the corpus).** Give `generate.py` a real TOON
  emitter carrying `status` / `emitted_count` / `error`, so § 2 becomes true as written.
  This is the better end state — every other finalize step's executor parses TOON — but it
  changes a shared entry point with non-finalize callers (`pyproject.toml`, CI,
  `marketplace-build.adoc`, `/sync-plugin-cache`), so the prose lines must be preserved or
  those callers migrated in the same change.

Fix the `manage_status` notation in the same pass.

## Impact

Runs on every finalize of this repo (`order: 81`, between `branch-cleanup` at 70 and
`sync-plugin-cache` at 85). It is `default_on: false`, so the exposure is scoped to
plan-marshall's own finalize runs — but that is precisely the surface the meta-project
uses to certify its own releases.

The general rule this instance illustrates: **a step body that declares a parse of another
component's output is a two-sided contract, and nothing in the finalize machinery checks
the producing side.** It held here because the step is project-local and therefore outside
plugin-doctor's `marketplace/bundles/` scan AND outside the architecture inventory (see the
sibling `manage-architecture` candidate) — so no structural guard covers it at all.
