# LoopCheck 0.5.2 verification

This document distinguishes completed local evidence from external delivery.

## Retained attempts

- Initial entry: local service was stopped. The UI showed recovery instructions and disabled service-dependent operations. The shutdown cause was not established.
- First live business-planning attempt: inconclusive after one unsettled provider call; no draft or passing result. A minimal Strands call later returned OK, and the explicit planning retry produced two requirements. This does not identify the first network/provider failure's root cause.
- The first browser-binding attempt encountered a context-size limit. The newly mounted MDN sample's inline script had been blocked by the application CSP, so observations correctly saw no added item. Fixed using exact inline-asset hashes for the pinned samples; their source remains unchanged.
- Subsequent binding attempts exhausted the eight-call limit on invalid tool parameters. These records are retained. The planner now receives a simpler initial observation interface and stage-specific instructions. Observations still execute through the real browser and cannot approve requirements.
- A context compaction edit initially raised a missing-key error for an empty exploration path. The concurrent full test run recorded 45 passes and 1 failure. The focused 10-test requirement suite passed after the correction; the final complete suite subsequently passed as recorded below.
- The final live browser path generated two flows, both reviewed in the UI: add Milk and assert item text plus empty input; add Milk, delete it and assert zero list items. Confirmation passed both flows in 7.13 seconds. A separate ordinary recheck is recorded independently.

## Completed automatic evidence

The 12 frozen mutation cases met all expected outcomes: six injected faults were detected and six non-fault changes passed, with no false green fault and no false alarm. The flows are frozen, developer-defined tests and use zero model calls; these counts do not measure agent planning quality. See `evidence/v052-benchmark.json` and its frozen manifest.

Three focused public-demo tests passed, including actual MDN interactions under the production content security policy, session boundaries and the future-requirement/regression/repair/restart workflow. Four focused error-classification tests passed. Final complete-test and live-planning results are recorded below.

## Review boundaries

Screenshots under `audit-v052` cover the entry, original goal, requirement review, uncovered state, bound-check review and current result. This is a bounded workflow review, not a full accessibility audit. Agent planning was tested on simple public frontend samples, not arbitrary production applications. No paired human study or time-saving percentage is claimed.

## Independent external gates

| Gate | Status |
|---|---|
| Public source | 0.5.2 published; anonymous archive and all 209 manifest entries verified |
| Version-specific Linux/container checks | 0.5.2 Linux and container checks passed (48 tests, 12 cases, 328.53 MiB container peak) |
| Architecture PDF | Created and visually reviewed locally |
| Free live judge access | Pending AWS account login, deployment and public verification |
| Public YouTube/Vimeo video | Public on YouTube; Studio publication and 3:40 watch page verified |
| AWS Builder ID | Required identity not yet supplied |
| Devpost draft | LoopCheck details, six images, video, architecture and additional fields saved; Builder ID missing; not submitted |
| Final submission | Not submitted; no organizer acceptance or award claimed |

The official rules were checked on 2026-09-11: https://agentsforhumans.devpost.com/rules. Submission closes 2026-09-15 08:00 Asia/Shanghai; test access must remain available through judging. Live hosting is optional, but functional free test access is required. Strands, public MIT/Apache source, English material, README, architecture, Builder ID and a public video of at most five minutes are required.

## Final local code gate

The final complete suite passed **48 tests in 299.044 seconds**, including real Strands stop-after-draft dispatch, independently reserved bounded transport retries, current planning/history classification and actual public-sample browser behavior. The earlier failed test run remains in local logs and is described above. Node syntax validation passed. No failure was converted into a pass.

Fresh live four-goal evaluations are retained separately: `v052-planning-results.json` finished 2/4 and `v052-planning-results-retry1.json` finished 1/4. Provider connection failures prevented the remaining goals from finishing. A saved binding draft in the first round remained reviewable after an extra summary call hit the limit; the final implementation now stops the agent immediately at the saved draft. Neither round establishes a broad planning success rate.

The actual UI shopping-list flow and its unsuccessful attempts are retained in `evidence/v052-live-ui.json`: two reviewed checks passed, and the next ordinary recheck passed in 6.95 seconds with zero model calls. Three subsequent small connection diagnostics returned successfully; one needed its bounded retry. This does not establish sustained provider availability.

Recorded UI demonstration: baseline 3/3 (5.24s), future requirement incomplete (5.95s), two price regressions detected among four flows (10.14s), repaired source 4/4 (6.26s). A separate live-generated two-flow recheck passed in 7.54s. Cart code changes and preset approvals were explicitly disclosed. The inline full reproduction brief was verified; the browser clipboard reader returned empty despite the UI copy-success notice, so cross-tool clipboard delivery is not independently verified. Inline/download/MCP evidence remains available.

Full-page screenshots produced stitching artifacts while the interface updated. Original captures remain in the private test directory; published audit images are unaltered single-viewport captures. They are not a claim of a complete accessibility audit.

## Published artifacts (2026-09-12)

[Source release](https://github.com/WeiR-h/loopcheck/releases/tag/v0.5.2) pins `1a4b659491c18af66195d9cee218f75adf708535`. [CI](https://github.com/WeiR-h/loopcheck/actions/runs/34670989974) passed both jobs. Anonymous archive download and every manifest entry were checked; see `evidence/v052-publication.json`. The [English video](https://www.youtube.com/watch?v=-Gp8uHgHy-s) is public. Devpost remains an incomplete draft. No cloud resources were created; Builder ID and hosted live-provider access remain pending.
