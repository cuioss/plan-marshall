envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:11Z

# A deliverable's verification command checked other files, and nothing checks Markdown links

## What happened

In plan 39's outline, deliverable 9 changed only `README.md`, but its verification command was `asciidoc verify-links --directory pm-providers --recursive`. That command checks the pm-providers READMEs from deliverable 8, never `README.md`, so it would have reported a pass for a file it did not read. The 3-outline Q-Gate caught this (finding d94a64). Fixing it uncovered a second gap: `asciidoc verify-links --file README.md` reports `total_links: 0` even though `README.md` links to `LICENSE.md` and other files. The AsciiDoc link checker does not parse Markdown links, and no project script checks them. The verification had to become a manual read of all eleven link targets.

## Rule / fix

- A deliverable's verification command must actually read the files that deliverable changes. When writing the outline, compare the command's scope (directory, file arguments) with the deliverable's list of affected files.
- A link checker that finds zero links in a file that clearly has links should say the file was not parsed (for example, unsupported format), not report a clean pass. `asciidoc verify-links` should refuse or flag non-AsciiDoc input such as `.md` instead of returning `total_links: 0`.
- Consider adding a Markdown link check, or extending the existing checker to handle Markdown, so `README.md` links can be verified automatically.

## Evidence

3-outline Q-Gate finding d94a64 in plan-39-module-readmes-and-adrs, resolved taken_into_account. `verify-links --file README.md` returned total_links 0 even though the file has relative links.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-006.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
