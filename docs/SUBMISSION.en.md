# LoopCheck — Keep your changes honest

## Elevator pitch
An acceptance companion for solo AI builders: approve browser requirements once, replay them after code changes, and send reproducible regression evidence back to your coding AI.

## Inspiration
AI makes it easier to change a small web app, but checking whether an earlier feature still works remains repetitive. We built LoopCheck around the requirements the builder wants to preserve across edits.

## What it does
Connect a local project folder and its running preview. Describe the next change and behaviors that must remain. A Strands agent inspects the actual page and proposes executable flows with explicit outcomes. The builder reviews and confirms them before the first baseline run.

After a source change, Chromium replays the approved flows. Results distinguish passed checks, regressions, unmet requirements and cases that could not be reliably checked. Each result is tied to a source hash and a confirmed requirements version. A source edit during a run makes the result stale.

A local MCP bridge exposes prepare_change, check_change and get_result. Your existing coding AI receives failed steps, expected and observed behavior, source filenames and screenshot evidence. It fixes the original project; LoopCheck verifies the same requirements again. MCP cannot approve or rewrite those requirements.

## How we built it
Python, FastAPI, Strands Agents SDK, Qwen3.7 Flash via Alibaba Cloud Model Studio Beijing, Playwright/Chromium, SQLite and MCP. Strands performs real page observation, proposes structured browser actions and trial-runs its proposal. Deterministic browser assertions decide subsequent outcomes without model calls.

The local edition supports small HTML/JavaScript and React/Vite previews. Each project can keep 10 flows with at most 20 steps each. A shared browser slot, persistent model budget and debounced source watcher bound work. Public mode accepts only bundled examples and disables local directory and MCP access. AgentCore is not deployed.

## Challenges and learning
The first live planning attempt confused a negative input with a negative calculated balance and proposed a value assertion against a non-editable output element. That proposal was not approved. We added element metadata, clearer instructions and trial execution before review. The second live preparation produced three executable flows that passed a real browser baseline. Human review is still necessary: successful execution alone does not prove a proposal captures the user's intent.

We also found a completion-state race in the original guard: the result could become final just before its worker slot was released. We changed publication order and reran the suite. Failures are documented alongside final results.

## Verified results
The frozen automated evaluation contains 12 deliberately constructed changes across an original budget calculator, a pinned public TodoMVC React example, and LoopCheck's own frontend. All six injected faults were detected; all six non-fault changes passed. This is a small, disclosed regression exercise using frozen developer-authored requirements, not a model success rate on unknown applications.

The real MCP client completed pass → injected arithmetic regression → repair → pass. The failed calculation expected 850.00 and observed 1550.00. Rechecks used no model calls. See docs/evidence/v04-live.json, v04-benchmark.json and v04-release-checks.json for the actual records.

## Limits and next steps
No measured human-efficiency benefit, external user study, production reliability or guaranteed prize outcome is claimed. Login, payments, complex backends and arbitrary repository repair are outside this release. Requirement replacement/removal is not yet exposed; new checks append to the confirmed contract. Source versioning covers included frontend files, not changes to databases or runtime configuration.

Next: test unseen projects, improve requirement review, and measure human verification time only with an actual paired human experiment.

## Attribution and publication fields
Built with AI coding assistance. Pocket Budget is an original example. TodoMVC React is pinned with its upstream license and provenance in the frozen manifest. Runtime planning used the real connected model; unit tests that simulate provider responses are labeled.

This is an AI-assisted submission draft for author review. Public repository, free judge URL, public video URL and Builder profile fields remain to be filled only after publication. Local readiness is not a completed submission.
