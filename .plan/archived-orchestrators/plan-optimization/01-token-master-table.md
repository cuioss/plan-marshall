# Token-Usage Master Table — plan-marshall corpus (archived + dormated) + TokenSheriff source

All token figures are `input+output` generation volume (the `total_tokens` measure the audit script reports); they **exclude** `cache_read`/`cache_creation`, which run 10-100x larger and are the dominant *billed* cost (see the synthesis doc). LOC = real git insertions+deletions of the merged squash commit. `tok/LOC` = total_tokens ÷ LOC.

Per-phase column is **token usage** in `init/refine/outline/plan/exec/final` order. `—` = that phase's tokens were not recorded.

⚠ = partial metrics (≥1 phase's tokens unrecorded → the Total is a **floor, not truth**, an under-count). Plans: ci-pr-safe-merge, dead-extension-points-audit-fix, dynamic-finalize-step-discovery, phase-6-finalize-strict-sync-ordering, reactivate-architecture-refresh-step, security-audit-finalize-step, terminal-title-build-busy.

**Corpus-confidence caveat** — the ⚠ floor above covers ONLY `unrecorded_phases`. Two further leaks widen the error bar and are NOT reflected in any per-plan figure: (a) pre-#912 harness background-kills (~90 over a 23-day window) were absorbed as idle/wall time with zero trace, so Wall/idle figures here are floors with unquantified error (made legible going forward by #912, not back-filled); and (b) dispatched-phase token totals historically under-counted because `cmd_generate` never reconciled the phase total against the dispatch-boundaries sum (fixed by the dispatch-boundary reconciliation, PR #922 — pre-fix rows read low). Treat every Wall/idle and dispatched-phase Total below as a **floor with error above the floor**, not a point estimate.

| Plan | Corpus | Change-type | Scope | Lane | Wall | LOC | Total tok | tok/LOC | init/refine/outline/plan/exec/final |
|------|--------|-------------|-------|------|------|-----|-----------|---------|--------------------------------------|
| restore-coverage-gate-80 | dorm | tech_debt | single_module | deep | 5h37m | 10028 | 4,193,249 | 418 | 54k/82k/342k/216k/2.51M/991k |
| routing-v2-recipe-match | dorm | feature | multi_module | deep | 17h16m | 2409 | 3,964,160 | 1,646 | 58k/117k/532k/242k/2.01M/1.00M |
| integrate-sonar-finalize | arch | feature | multi_module | deep | 8h28m | 1129 | 3,779,867 | 3,348 | 55k/139k/353k/264k/1.63M/1.34M |
| dynamic-finalize-step-discovery ⚠ | dorm | tech_debt | multi_module | deep | 6h26m (n=4/6) | 2666 | 3,683,927 | 1,382 | 52k/76k/—/450k/1.12M/1.98M |
| persona-ref-profile-identity-model | dorm | feature | multi_module | deep | 11h12m | 3345 | 3,641,005 | 1,088 | 67k/167k/651k/354k/1.26M/1.14M |
| finish-portability-gaps-implementation | dorm | tech_debt | multi_module | deep | 20h31m | 6221 | 3,491,233 | 561 | 54k/67k/405k/249k/1.82M/895k |
| ext-point-verify-findings-pipeline | dorm | feature | multi_module | deep | 9h8m | 1477 | 3,480,871 | 2,357 | 74k/179k/418k/320k/938k/1.55M |
| remove-the-require-wrapper-knob-entirely-auto-dete | arch | tech_debt | multi_module | deep | 4h57m | 523 | 3,246,992 | 6,208 | 78k/204k/438k/416k/1.07M/1.04M |
| fix-config-step-list-serial-form | dorm | tech_debt | single_module | deep | 3h39m | 2411 | 3,164,466 | 1,313 | 52k/68k/284k/223k/1.62M/920k |
| arch-gate-build-command | arch | feature | multi_module | deep | 7h12m | 1530 | 3,023,302 | 1,976 | 56k/80k/229k/295k/1.04M/1.32M |
| phase-6-finalize-post-merge-re-review | dorm | feature | single_module | deep | 7h11m | 1703 | 2,755,733 | 1,618 | 52k/180k/340k/212k/1.13M/837k |
| merge-lock-queue-wait | dorm | feature | single_module | deep | 8h11m | 1655 | 2,749,924 | 1,662 | 50k/196k/326k/205k/820k/1.15M |
| phase-6-finalize-strict-sync-ordering ⚠ | dorm | bug_fix | multi_module | deep | 4h19m (n=5/6) | — | 2,741,490 | — | 69k/94k/1.12M/457k/999k/— |
| read-only-boundary-gate-verbs-must-fail-closed-wra | dorm | bug_fix | multi_module | deep | 12h45m | 1277 | 2,684,654 | 2,102 | 81k/299k/477k/201k/441k/1.19M |
| eliminate-or-statically-guard-manually-maintained | dorm | feature | single_module | deep | 3h57m | 2107 | 2,678,222 | 1,271 | 82k/206k/323k/271k/710k/1.09M |
| terminal-title-build-busy ⚠ | dorm | feature | single_module | deep | 4h24m | 804 | 2,598,546 | 3,232 | 56k/176k/904k/252k/1.21M/— |
| track-selection-accuracy-audit | dorm | feature | multi_module | deep | 7h1m | 845 | 2,463,961 | 2,916 | 57k/195k/303k/194k/177k/1.54M |
| agentfile-hygiene-audit-recipe | arch | feature | multi_module | deep | 6h4m | 1202 | 2,414,301 | 2,009 | 58k/144k/353k/214k/719k/928k |
| audit-capabilities-as-recipes | dorm | feature | multi_module | deep | 3h37m | 554 | 2,366,029 | 4,271 | 58k/154k/403k/290k/349k/1.11M |
| doc-validation-capability-split | TS-src | tech_debt | multi_module | deep | 4h2m | 457 | 2,260,310 | 4,946 | 65k/103k/409k/285k/725k/674k |
| remove-execute-task-skills | dorm | tech_debt | multi_module | deep | 10h8m | 547 | 2,237,568 | 4,091 | 53k/83k/439k/224k/554k/884k |
| verify-step-ext-point-discovery | dorm | tech_debt | single_module | deep | 11h20m | 806 | 2,187,828 | 2,714 | 95k/164k/285k/218k/617k/810k |
| auditor-preference-learning | dorm | feature | single_module | deep | 5h11m | 1119 | 2,171,802 | 1,941 | 62k/79k/414k/221k/347k/1.05M |
| pre-1-0-no-legacy-rule-a-format-contract-migration-2 | dorm | tech_debt | single_module | deep | 4h50m | 2062 | 2,169,602 | 1,052 | 60k/168k/564k/208k/429k/740k |
| retrospective-audit-follow-ups | arch | bug_fix | multi_module | deep | 4h49m | 1537 | 2,114,169 | 1,376 | 64k/81k/414k/237k/553k/765k |
| fix-pretooluse-enforcement-hook | dorm | bug_fix | multi_module | deep | 6h0m | 217 | 2,096,005 | 9,659 | 52k/83k/573k/224k/354k/809k |
| security-audit-finalize-step ⚠ | dorm | feature | multi_module | deep | 13h7m | 1484 | 2,022,301 | 1,363 | 54k/47k/915k/225k/781k/— |
| extend-security-skillset-coverage-gaps | dorm | feature | multi_module | deep | 77h40m | 574 | 2,011,553 | 3,504 | 55k/67k/269k/217k/251k/1.15M |
| dead-extension-points-audit-fix ⚠ | dorm | enhancement | multi_module | deep | 4h24m | 863 | 1,991,568 | 2,308 | 59k/100k/—/238k/372k/1.22M |
| finalize-early-baseline-rebase | dorm | feature | single_module | deep | 3h59m | 449 | 1,909,490 | 4,253 | 62k/81k/381k/272k/232k/882k |
| fix-re-review-timeout-proceed | dorm | bug_fix | single_module | deep | 9h46m | 337 | 1,908,547 | 5,663 | 69k/172k/305k/216k/386k/762k |
| task-derivation-must-honor-a-deliverable-s-write-n | dorm | bug_fix | single_module | deep | 12h26m | 96 | 1,899,634 | 19,788 | 79k/184k/259k/203k/295k/881k |
| lessons-knowledge-to-architecture-hints | dorm | feature | single_module | deep | 10h58m | 167 | 1,845,264 | 11,049 | 50k/95k/378k/265k/256k/801k |
| fix-plugin-doctor-pr774-findings | dorm | bug_fix | multi_module | deep | 2h3m | 28 | 1,836,439 | 65,587 | 70k/92k/300k/181k/170k/1.02M |
| harden-claude-runtime-fail-safes | dorm | bug_fix | single_module | deep | 4h22m | 612 | 1,799,911 | 2,941 | 50k/113k/304k/262k/202k/868k |
| pretooluse-enforcement-hook | dorm | feature | single_module | deep | 18h25m | 2162 | 1,785,671 | 826 | 52k/59k/318k/217k/519k/621k |
| ws05-security-skill-resolver | dorm | feature | surgical | deep | 3h31m | 573 | 1,771,048 | 3,091 | 55k/175k/267k/243k/552k/478k |
| plugin-dev-security-profile | dorm | feature | single_module | deep | 3h49m | 273 | 1,749,283 | 6,408 | 54k/186k/362k/232k/275k/640k |
| harden-untrusted-ingestion-reader-rule-of-two | dorm | feature | single_module | deep | 5h41m | 31 | 1,724,010 | 55,613 | 55k/61k/245k/244k/277k/842k |
| reactivate-architecture-refresh-step ⚠ | arch | enhancement | multi_module | deep | 9h3m | 812 | 1,698,214 | 2,091 | 56k/89k/—/268k/558k/727k |
| security-skills-reorganization | dorm | enhancement | multi_module | deep | 3h58m | 951 | 1,689,622 | 1,777 | 51k/80k/289k/198k/214k/858k |
| harmonize-owasp-top-ten-taxonomy | dorm | tech_debt | single_module | deep | 2h25m | 206 | 1,687,578 | 8,192 | 54k/193k/310k/274k/339k/519k |
| seed-re-review-timeout-config-knobs | dorm | feature | single_module | deep | 3h22m | 28 | 1,671,248 | 59,687 | 51k/61k/256k/194k/278k/831k |
| surface-encoded-verification | dorm | feature | single_module | deep | 2h58m | 95 | 1,662,329 | 17,498 | 54k/131k/357k/203k/179k/738k |
| activate-mirror-rules-gating | dorm | enhancement | single_module | deep | 3h29m | 2709 | 1,641,463 | 606 | 55k/71k/325k/246k/508k/436k |
| fix-broken-relative-link-findings | dorm | bug_fix | multi_module | deep | 2h18m | 41 | 1,625,898 | 39,656 | 61k/58k/347k/220k/277k/663k |
| measure-uncompressed-output | dorm | analysis | surgical | deep | 3h52m | 245 | 1,590,319 | 6,491 | 63k/86k/251k/250k/158k/783k |
| whole-tree-gate-deleted-symbol-detection-must-be | dorm | tech_debt | single_module | deep | 17h28m | 3024 | 1,572,513 | 520 | 75k/171k/290k/231k/284k/521k |
| fix-coderabbit-re-review-timeout | dorm | bug_fix | single_module | deep | 4h29m | 149 | 1,459,995 | 9,799 | 52k/74k/328k/194k/178k/635k |
| new-branch-added-to-a-manage-command-skipped-the-i | arch | feature | surgical | deep | 2h55m | 155 | 1,444,672 | 9,320 | 85k/298k/331k/102k/142k/486k |
| add-resolve-benign-probe | arch | bug_fix | surgical | deep | 3h13m | 194 | 1,425,100 | 7,346 | 56k/118k/157k/233k/412k/450k |
| simplify-self-review-must-remove-exception-swallow | dorm | enhancement | surgical | deep | 11h8m | 94 | 1,387,939 | 14,765 | 83k/221k/256k/97k/122k/609k |
| revert-license-to-fsl | dorm | feature | multi_module | deep | 9h0m | 1936 | 1,330,018 | 687 | 60k/134k/325k/214k/315k/283k |
| fix-broken-relative-link-fp | dorm | bug_fix | surgical | deep | 75h23m | 119 | 1,095,414 | 9,205 | 52k/67k/260k/171k/156k/389k |
| ci-complete-precondition-resolver-crashes-with-un | dorm | bug_fix | surgical | deep | 9h3m | 125 | 1,090,397 | 8,723 | 73k/193k/128k/88k/170k/438k |
| fix-automated-review-merge-anyway-record | dorm | bug_fix | surgical | deep | 1h52m | 11 | 1,041,870 | 94,715 | 98k/119k/93k/80k/143k/508k |
| fix-escalate-ask-guard-ordering | dorm | bug_fix | surgical | deep | 1h47m | 20 | 1,034,469 | 51,723 | 99k/97k/138k/92k/144k/465k |
| ci-pr-safe-merge ⚠ | dorm | feature | single_module | deep | 3h54m | 1332 | 938,092 | 704 | 52k/85k/423k/224k/155k/— |
