## Inspiration

AI makes changing a small web app easier. It does not remove the work of checking whether earlier behavior still works. As a solo builder using AI, I wanted to preserve my expectations across edits instead of repeatedly clicking the same pages and describing the same regressions.

LoopCheck focuses on approved business requirements, independent browser evidence, and a clear answer about the current change.

## What it does

Connect a trusted local project folder and its running frontend preview. Describe what is changing and what must keep working. A Strands agent proposes business requirements, including future features whose controls do not yet exist. The builder reviews and confirms them.

Once a feature exists, a separate planning stage observes the live page, explores bounded paths such as opening a dialog, and proposes executable browser checks. Each flow is tied to a requirement revision and reviewed before use. Missing checks remain uncovered; they cannot disappear behind passing old checks.

After the coding AI changes the original project, LoopCheck replays the same approved flows without another model request. Results include expected and observed behavior, screenshots, complete reproduction steps, related files and source/requirement versions. Concurrent edits make an old result stale. Only a current, nonempty, fully covered and passing scope can approve the change.

Requirements can be revised, retired with a reason, restored or given a rebuilt check. These changes require reviewed drafts. The model cannot silently weaken assertions, retire a failing requirement or approve its own work.

## Working demonstration

The live planning path uses a pinned, unchanged public MDN shopping-list example. Strands and Qwen generated requirements and two flows covering item text, cleared input and deletion. After operator review, both flows passed. An ordinary replay also passed with zero model calls. The recorded tool trace and unsuccessful planning attempts remain available.

A separate, explicitly disclosed keyless cart walkthrough demonstrates the complete regression cycle with real Chromium checks. It establishes a baseline, saves an uncovered coupon requirement, introduces a scripted feature plus a deliberate price regression, returns failure evidence, and restores the price before rechecking the same requirements. The old total check expects 200.00 and observes 300.00. After repair, all four flows pass. Its requirements and code edits are presets; this is not a claim of autonomous coding.

The video combines actual interface recordings within these stages and recorded live-planning evidence. Cuts between stages, synthetic narration and deliberately injected faults are disclosed.

## How I built it

Python, FastAPI, Strands Agents SDK, Qwen3.7 Flash through Alibaba Cloud Model Studio Beijing, Playwright/Chromium, SQLite and MCP. Strands selects page observations, proposes requirements and steps, and invokes trial verification. Browser assertions determine acceptance independently of the model's summary.

The local MCP interface exposes prepare_change, check_change and get_result. It returns evidence to an existing coding tool and cannot approve drafts. Original source remains in the user's project. Source tracking excludes keys, hidden directories, dependencies and build outputs.

Public mode accepts bundled samples only and keeps sessions separate. The provider key stays on the server. Model requests reserve costs persistently, including unknown costs after an interrupted request. Ordinary rechecks do not use a model. AgentCore is not deployed.

## Challenges and learning

Executable checks are not automatically correct business requirements. Early attempts confused element text and editable values, guessed selectors or consumed request limits. I separated intent from execution, added trial runs, preserved exact assertions on locator retries, simplified initial observation, and stopped the agent after saving a review draft.

Browser verification exposed a deployment-specific problem: inline scripts in the newly mounted MDN samples were blocked by the application security policy. Exact hashes now permit only those pinned assets. A real browser test exercises their behavior through the production middleware.

Provider connections remain a limitation. Two new four-goal evaluation rounds completed 2/4 and 1/4 goals respectively, with connection failures retained. A bounded retry does not guarantee availability. These small debugging rounds are not a production success rate.

## Verification and limits

The final local suite passed 48 tests. Twelve frozen artificial changes across a budget calculator, TodoMVC React and LoopCheck's own frontend met all expected outcomes: six injected faults were detected and six non-fault changes passed. The frozen flows are developer-defined tests, separate from model-planning evaluation. Records, fixture versions and licenses are included in the repository.

LoopCheck targets small HTML/JavaScript and React/Vite frontends: up to ten active requirements, ten flows and twenty steps per flow. Exploration is bounded to three fresh observations and six actions per path. Login, payments, complex backends and hostile repository execution are outside this release. No measured human-efficiency percentage, external user study, production-reliability guarantee or prize outcome is claimed.

## What's next

Improve planning reliability on unseen pages and collect paired human verification measurements. The immediate value to test is fewer repeated manual checks and less effort transferring regression evidence to the coding AI.

## Attribution

Built by one person with AI coding assistance. LoopCheck and its original samples are MIT licensed. MDN examples retain pinned provenance and CC0 licenses; TodoMVC React retains its upstream MIT license and fixed revision. See the README, architecture and retained verification records for installation and evidence boundaries.
