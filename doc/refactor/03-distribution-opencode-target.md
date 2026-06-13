# 03 — Add the OpenCode distribution target

## Objective

Publish the OpenCode artifact tree the same way the Claude tree is already published —
through the existing target-parametrized CI matrix. This workstream is small **because
the distribution design already anticipated it.**

## Current state

`.github/workflows/claude-distribute.yml` publishes via a `strategy.matrix` where each
entry defines a target's branch (`dist-{name}`), dist-tag prefix (`{name}/`), publish
directory (`target/{name}`), and generator flag (`--target {name}`). The matrix has one
entry today (`claude`). `doc/developer/distribution.adoc` already documents that adding a
target is "a config-only change — one line appended to the matrix list" producing a
`dist-opencode` branch plus `opencode/v*` dist tags from the same source `v{x.y.z}` tag.

**The retired plan's distribution design (move `marketplace.json` to the repo root,
GitHub Pages hosting, release tarballs, `opencode-marketplace install` from a Pages URL)
is obsolete.** Do not implement it.

## Tasks

1. **Add the `opencode` matrix entry** to the distribute workflow: `target_name:
   opencode`, `generator_target_flag: opencode`, publish dir `target/opencode`, branch
   `dist-opencode`, tag prefix `opencode/`. Confirm the generated tree's root holds
   whatever manifest an OpenCode client's "add marketplace" path expects.

2. **Confirm the OpenCode consumption path** against the published `dist-opencode` ref.
   Determine, by testing on a live OpenCode client, which install path actually works
   (git-ref add, `opencode-marketplace install <ref>`, or a deploy into
   `~/.config/opencode/`), and pin that as the documented primary path. The original
   plan's assumptions about `opencode-marketplace` accepting static URLs are unverified —
   validate before documenting.

3. **Gate the publish on the OpenCode generation check** from
   [02](02-validate-opencode-runtime.md) so a broken emitter never publishes a
   `dist-opencode` snapshot.

4. **Versioning stays unified.** The single source `v{x.y.z}` tag drives every target;
   the OpenCode dist tag is `opencode/v{x.y.z}`. No per-bundle or per-target version
   channel.

## Acceptance

- A push to `main` updates a `dist-opencode` snapshot branch; a `v*` tag creates an
  immutable `opencode/v*` dist tag.
- The documented OpenCode install path is verified end-to-end on a live client.
- A broken OpenCode emit fails CI before publish.

## Dependencies

- [02 — Validate the OpenCode runtime](02-validate-opencode-runtime.md) — do not publish
  an installable artifact for a runtime that has not been proven.
- The Claude distribution pipeline and matrix already exist; this extends them.
