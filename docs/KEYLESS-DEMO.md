# 0.5.1: a complete walkthrough without a model key

Use **Try the full flow · no API key** in the left sidebar. The same button is available in local and public sample mode. Each browser session receives its own cart copy; repeated clicks reopen that copy instead of resetting history.

1. Review the three preset baseline requirements and confirm them. Quantity, validation and persistence are checked by a real browser.
2. Add the future SAVE10 coupon requirement and confirm its business expectation. There is no coupon control yet. Three passing old checks plus one uncovered requirement must produce **incomplete**.
3. Implement the sample coupon and deliberately inject a price fault. Review the coupon's proposed steps and confirm them. Old total and persistence checks fail; the new coupon check passes.
4. Expand the failure evidence or the **Full reproduction brief**. It includes prerequisite state, every action, expected and observed values, screenshots, source and requirement versions, and related files.
5. Restore the sample price and recheck. All four confirmed requirements now pass. Open an older record: it is labelled historical while the current coverage totals stay visible above.

The requirements and source edits in this walkthrough are developer-authored presets. No model calls, autonomous coding, or model-planning success are demonstrated here. Browser executions and evidence are real. AI planning for a connected real project remains a separate Strands/Qwen flow with a server-side key. This walkthrough does not fulfill the separate live-hosting, public-video or final-submission deliverables.

## Data and controls

- Only session-owned copies under the application's `guided-demos` data folder can receive scripted edits. Connected user projects and bundled source files remain unchanged.
- Requests must match the current source hash and confirmed contract. Drafts still require the existing user-confirmation step; scripted actions cannot approve or relax expectations.
- Another session cannot mutate the known project or read its private run evidence. Generated HTML/JavaScript assets are deliberately shareable and contain only the synthetic sample, never uploaded source or keys.
- Existing browser queue, cancellation and timeout controls apply. Normal rechecks and this preset walkthrough consume zero model calls. Restart preserves requirements and history.
- Back up the existing data directory before upgrading. This patch adds no new database migration beyond 0.5.0.

## Local verification, 2026-09-11

The full suite passed **37 tests in 275.716 seconds**. After a subsequent UI correction, both focused guided-demo tests passed again in **74.196 seconds**, including an actual rendered-browser assertion that browsing historical failure evidence preserves the latest four-passed coverage and exposes the complete reproduction text without JavaScript errors.

All **12 frozen cases** met expected outcomes: six injected faults were not reported as passing, and six normal changes passed. Frozen case definitions and results are retained separately as `docs/evidence/v051-frozen-cases.json` and `docs/evidence/v051-benchmark.json`. These are developer-authored automatic checks; no human time-saving percentage is claimed.

Agent-operated UI verification in the user's browser confirmed baseline passed → future requirement incomplete → two price regressions detected → four checks passed after repair. The example expected 200.00 and observed 300.00 during the injected fault; after reload it expected 300.00 and observed 450.00. Historical evidence stayed marked historical. The inline brief was inspected. The copy button displayed success, but independent clipboard readback was empty; clipboard transport is **not independently verified**, and the visible brief plus download remain available.

## Retained unsuccessful attempts

| Attempt | Result | What changed |
|---|---|---|
| Guided test run 1 | 2 tests, cleanup error; Windows `WinError 32` kept `server.log` open | The virtual-environment launcher did not own the actual server process. Functional flow success did not count as a passing test run. |
| Guided test run 2 | Cleanup still failed after attempted process-tree termination | Removed dependence on denied process-tree termination. |
| Guided test run 3 | 2 tests passed, 125.253 seconds | Tests start the Windows base interpreter directly with the virtual environment's packages and retain the actual server process handle. |
| Full suite | 37 tests passed, 275.716 seconds | Isolated application data; no provider requests. |
| UI review | Found historical selection incorrectly reset current coverage | Coverage now comes from the latest check, independently of the selected historical detail. |
| Focused UI retest | 2 tests passed, 74.196 seconds | Includes browser rendering, historical coverage and visible reproduction evidence. |

Local raw logs remain under `.test-data/guided-tests-attempt1.log`, `guided-tests-attempt2.log`, `guided-tests.log`, `guided-full-suite.log` and `guided-ui-suite.log`. Public CI retains its own complete test output as an artifact. This report preserves unsuccessful outcomes rather than presenting only the final run.

## Delivery status

0.5.0 remains an immutable published release. The 0.5.1 workflow publishes a separate source archive only after its own Linux tests and container verification succeed. AWS deployment, a public submission video and Devpost submission remain separate, incomplete steps. No paid resources were created for this patch.
