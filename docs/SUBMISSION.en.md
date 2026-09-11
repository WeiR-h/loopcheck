# LoopCheck — Keep your changes honest

## Elevator pitch
An acceptance companion for solo AI builders: approve browser requirements once, replay them after code changes, and send reproducible regression evidence back to your coding AI.

## Inspiration
AI makes it easier to change a small web app, but checking whether an earlier feature still works remains repetitive. We built LoopCheck around the requirements the builder wants to preserve across edits.

## What it does
Connect a local project folder and its running preview. Describe the next change and behaviors that must remain. A Strands agent proposes business requirements before the feature exists. The builder edits and confirms them. A separate planning stage observes the real page, including bounded dialog exploration, and proposes browser checks bound to specific requirement revisions. Missing checks stay uncovered.

After a source change, Chromium replays the approved flows. Results distinguish passed checks, regressions, unmet requirements and cases that could not be reliably checked. Each result is tied to a source hash and a confirmed requirements version. A source edit during a run makes the result stale.

A local MCP bridge exposes prepare_change, check_change and get_result. Your existing coding AI receives failed steps, expected and observed behavior, source filenames and screenshot evidence. It fixes the original project; LoopCheck verifies the same requirements again. MCP cannot approve or rewrite those requirements.

## How we built it
Python, FastAPI, Strands Agents SDK, Qwen3.7 Flash via Alibaba Cloud Model Studio Beijing, Playwright/Chromium, SQLite and MCP. Strands performs real page observation, proposes structured browser actions and trial-runs its proposal. Deterministic browser assertions decide subsequent outcomes without model calls.

The local edition supports small HTML/JavaScript and React/Vite previews. Each project can keep 10 active requirements and 10 flows with at most 20 steps each. Business requirements support reviewed edits, retirement, restoration and rebuilding. A shared browser slot, persistent model budget and debounced source watcher bound work. Public mode accepts only bundled examples and disables local directory and MCP access. AgentCore is not deployed.

## Challenges and learning
The first live planning attempt confused a negative input with a negative calculated balance and proposed a value assertion against a non-editable output element. That proposal was not approved. We added element metadata, clearer instructions and trial execution before review. The second live preparation produced three executable flows that passed a real browser baseline. Human review is still necessary: successful execution alone does not prove a proposal captures the user's intent.

We also found a completion-state race in the original guard: the result could become final just before its worker slot was released. We changed publication order and reran the suite. Failures are documented alongside final results.

## 0.5 daily requirement workflow

An active requirement may have no flow. A mixed scope of passing old checks and uncovered new expectations is `incomplete`, never `passed`. Each result snapshots source, requirement revisions and flows; the API computes `can_accept` against current versions and the latest check. A historical green result cannot authorize current development. Failure evidence includes the complete reproduction sequence, prerequisite state, failed location, expected/actual values, screenshots and related files.

The cart development gate recorded baseline pass → future coupon requirement incomplete → implemented coupon plus injected price regression fails → repaired source passes all four checks. Actual MCP stdio verification retrieved full failure evidence and rejected historical approval.

Four live Strands/Qwen planning goals on pinned MDN shopping-list and dialog samples produced 0/4, 1/4, 2/4, 0/4 and 4/4 passing goals across five retained rounds. The latest round passes all four goals after improving requirement references, compact step submissions and bounded locator correction. The full 35-test suite and all 12 frozen mutation cases pass. This debugging evaluation is not a production success-rate claim. All unsuccessful attempts remain in the evidence folder.

## Historical 0.4 results
The frozen automated evaluation contains 12 deliberately constructed changes across an original budget calculator, a pinned public TodoMVC React example, and LoopCheck's own frontend. All six injected faults were detected; all six non-fault changes passed. This is a small, disclosed regression exercise using frozen developer-authored requirements, not a model success rate on unknown applications.

The real MCP client completed pass → injected arithmetic regression → repair → pass. The failed calculation expected 850.00 and observed 1550.00. Rechecks used no model calls. See docs/evidence/v04-live.json, v04-benchmark.json and v04-release-checks.json for the actual records.

## Limits and next steps
No measured human-efficiency benefit, external user study, production reliability or guaranteed prize outcome is claimed. Login, payments, complex backends and arbitrary repository repair are outside this release. Retired requirements stay in history with a reason and do not count as passed. Modified requirements cannot inherit an old passing result. Source versioning covers included frontend files, not changes to databases or runtime configuration.

Next: improve agent planning reliability on unseen pages, then measure human verification time only with an actual paired human experiment.

## Attribution and publication fields
Built with AI coding assistance. Pocket Budget is an original example. TodoMVC React is pinned with its upstream license and provenance in the frozen manifest. Runtime planning used the real connected model; unit tests that simulate provider responses are labeled.

This is an AI-assisted submission draft for author review.

- Public repository: https://github.com/WeiR-h/loopcheck
- Automated verification: https://github.com/WeiR-h/loopcheck/actions/runs/34589055868
- Versioned source download: https://github.com/WeiR-h/loopcheck/releases/tag/v0.5.0
- Free judge URL: pending AWS deployment and external verification.
- YouTube/Vimeo URL: pending publication.
- Builder profile: author to supply.

Public source and local readiness are not a completed submission. No human time-saving result is claimed.
