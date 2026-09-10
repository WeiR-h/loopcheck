# LoopCheck 0.4

**Keep every change honest.** [中文](README.md)

[![Verify LoopCheck](https://github.com/WeiR-h/loopcheck/actions/workflows/verify.yml/badge.svg)](https://github.com/WeiR-h/loopcheck/actions/workflows/verify.yml)

LoopCheck is an acceptance companion for solo builders using AI to develop small web apps. Connect a running local project, describe the change and behaviors to preserve, review the Strands agent's proposed requirements, and replay them after source changes. Failed checks return reproducible evidence to your existing coding AI through MCP. LoopCheck does not edit source in this workflow.

## Try it

Use Python 3.12 or newer. Windows: run `install.ps1`, preserve your existing `.env`, then run `启动应用.cmd`. Open http://127.0.0.1:8791/ or `/judge` for English. Model configuration stays in `.env`: `DASHSCOPE_API_KEY`, provider `dashscope`, model `qwen3.7-flash`, budget `MODEL_BUDGET_CNY=20`. No key is sent to the frontend or browser worker.

For your own frontend, start its preview in your usual coding tool, then enter its project folder and a loopback HTTP URL with a port, such as `http://localhost:5173/`. LoopCheck does not install dependencies or launch arbitrary project commands. Native startup is the supported local-project path; Docker is the sample-only review deployment.

For a first session, select **Try it first: Pocket Budget**, then **Prepare acceptance checks**. Review every proposed step and expected result. Select **Approve & check current version**. The model can make mistakes: the initial planning failure is retained in our evidence. Approval is a human decision, never an MCP tool.

After approval, **Check this change** replays requirements without a model request. **Enable auto-check** watches the original frontend files while the server is running. A stop request also pauses watching. A changed source revision invalidates an in-flight result and triggers up to two bounded checks of the latest version.

## Use it with your coding AI

Select **Connect my coding AI** for a local configuration. Codex uses the generated TOML section in its MCP settings; other clients can use the displayed command and arguments. The credential file is stored under ignored `data/app/bridges/`; never publish it.

The stdio tools are `prepare_change(goal, language)`, `check_change()`, and `get_result(run_id, wait_seconds)`. The last tool returns expected/actual browser evidence and a repair brief. Tools never approve requirements, install dependencies, or edit source. They cannot wake a closed coding tool. See [MCP integration](docs/MCP.md).

## Verified evidence and limits

- 25 automated tests passed on Windows in 92.667 seconds; see [verification](docs/验证记录-v04.md) for the final check record.
- Three different frontends: original Pocket Budget, pinned public TodoMVC React, and LoopCheck's frontend using its real backend through a local test proxy.
- 12 frozen, disclosed mutation cases: six faults detected; six normal feature/cosmetic changes passed. Zero false-green faults and zero false alarms in this small controlled set. These are not naturally occurring defects or a general success-rate estimate.
- A live Strands/Qwen proposal was reviewed and browser-checked. An actual stdio MCP sequence produced **passed → failed → passed** after the development agent changed the original sample source using the returned evidence.
- **No human-efficiency percentage is claimed.** Automated durations are not human time saved. The user deferred the human timing study.

[Benchmark](docs/evidence/v04-benchmark.json) · [Frozen cases](docs/evidence/v04-frozen-cases.json) · [Live evidence](docs/evidence/v04-live.json) · [Architecture](docs/architecture.md)

## Scope and safeguards

Supports small loopback HTTP frontends with native form controls and accessible DOM. HTML/JavaScript and React can be checked through the browser; no framework-specific test IDs are required. Existing test IDs are supported when present. Hover is supported for controls revealed on pointer interaction.

Limits: 10 projects per session, 10 flows per project, 20 steps per flow, 2000 frontend source files / 20 MB per connected folder, 1 MB per source file, 120-second browser deadline plus at most 120 seconds waiting for the shared browser slot. `.env`, hidden folders, dependency/build directories, links out of the selected folder, and backend files are excluded from source-change tracking. Source content is hashed locally; the planner receives live page observations and the stated goal, not the repository.

Each flow starts in a fresh browser context. Service workers and cross-origin requests are blocked; same-origin preview WebSockets are allowed for development previews. Missing elements, blocked dependencies, unavailable previews, cancellation, and stale revisions cannot approve a change. The local project itself must be trusted; this is not a hostile repository sandbox or production-site testing service.

Confirmed flow specifications remain immutable. New drafts append to them within the limit; semantic editing/removal of existing contracts is not yet supported. A future release will add explicit user-reviewed contract replacement. The `/legacy` route retains the v0.3 demo and its historical data.

## Tests

```sh
python -m unittest discover -s tests -v
python scripts/project_gate.py
# Start LoopCheck on port 8791 before the cross-project benchmark:
python scripts/evaluate_projects.py
```

The benchmark downloads only the pinned TodoMVC test fixture if absent. It mutates temporary copies and preserves the original applications. `tests/project_fixtures.py` contains developer-defined (AI-assisted) test contracts, not hidden runtime repairs.

## Budget and submission

The existing Qwen3.7 Flash Beijing endpoint and persistent SQLite cost reservations remain in place. Model budget: CNY 20; total authorized project budget: CNY 100. No fallback to a different paid model. Public hosting must use persistent storage and provide model access without requiring judges to buy a key. No paid AWS resource has been provisioned by this release.

A 127-second captioned evidence walkthrough is included in the release artifacts. It combines real browser clips and UI stills with editing explicitly disclosed; it is not a continuous desktop recording. Fresh Linux Docker build and real browser checks passed; see [container evidence](docs/evidence/v04-container-check.json).

Public source: [https://github.com/WeiR-h/loopcheck](https://github.com/WeiR-h/loopcheck). [Linux CI](https://github.com/WeiR-h/loopcheck/actions/runs/34462275115) passed 25 tests, all 12 frozen mutation cases and a fresh Docker browser gate. At a 768 MiB container memory limit, peak usage was 324.27 MiB with no OOM. This CI gate used no model calls and is not an AWS instance capacity test. Hosted judging access, YouTube/Vimeo publication and Devpost submission remain pending. AgentCore is not deployed. [Publication evidence](docs/evidence/v04-publication.json).

MIT. Original app and Pocket Budget created with AI coding assistance. TodoMVC is an external evaluation fixture pinned to `ff43b02e59dfa604386bb382034b2cd07c2bcd8a`; its MIT license and bundled notices remain with the downloaded fixture. [Upstream](https://github.com/tastejs/todomvc). Libraries retain their licenses.
