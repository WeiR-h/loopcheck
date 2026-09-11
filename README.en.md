# LoopCheck 0.5.0

**Keep every change honest.** [中文](README.md)

An acceptance companion for solo builders working with AI on small web apps. Save the business behavior you want before a feature exists. Review browser checks when it is implemented, replay preserved requirements after every edit, and give your coding AI complete regression evidence.

## Start locally

Use Python 3.12+. On Windows run `install.ps1`, keep your existing `.env`, then run `启动应用.cmd`. Open http://127.0.0.1:8791/ (`/judge` opens English). Configure `DASHSCOPE_API_KEY`, provider `dashscope`, model `qwen3.7-flash` and `MODEL_BUDGET_CNY=20` in `.env`. Never put the key in frontend files. Total authorized project budget remains CNY 100.

Connect a trusted project folder and its already running loopback HTTP preview with an explicit port. LoopCheck hashes supported frontend files locally; it does not install dependencies, run arbitrary project commands, upload source or edit the original project. Docker/public mode only exposes bundled examples.

## Daily workflow

1. Select Pocket Budget or Everyday Cart, or connect your own running preview.
2. Describe the change and behaviors to preserve. **Prepare requirements** uses Strands to propose business intentions. Review the original goal, edit or add items, then confirm.
3. Missing checks remain **uncovered**. Future controls do not need to exist to save their requirement. Use **Generate missing checks** to observe the current page and propose executable steps; review and confirm again.
4. Have your coding AI implement the change. **Check this change** runs confirmed flows without a model call. Uncovered requirements keep the result incomplete even when all old checks pass.
5. Copy failure evidence or read it through MCP. Fix source and recheck. Edit, retire with a reason, restore or rebuild checks through reviewed drafts. Retired requirements never count as passing.

A changed requirement creates a new revision and cannot inherit its previous passing result. Unchanged flows remain available. Historical results are labeled with time and versions. Only a nonempty, fully covered, passing current scope has `can_accept=true`.

## Coding AI integration

Use **Connect my coding AI** to obtain local stdio configuration. Keep credential files private. Three tools remain: `prepare_change(goal, language, stage='intent', requirement_ids=[])`, `check_change()` and `get_result(run_id, wait_seconds=0)`. Use `stage='bind'` after implementing approved uncovered requirements. MCP cannot approve or weaken expectations. It returns coverage, currentness, complete prerequisites/actions, failed step, expected/actual values, screenshot paths and related changed files (not asserted root causes). It cannot wake a closed client. [Details](docs/MCP.md).

## Evidence and limits

[0.5 verification](docs/验证记录-v05.md) records all failed attempts. Twelve frozen artificial mutations met expected outcomes: six faults detected, six normal changes passed. A real shopping-cart development gate demonstrated passed → incomplete → regression → passed. These developer-defined tests are separate from agent planning.

Live Strands/Qwen planning was tested on four frozen goals in two pinned MDN CC0 examples. All five rounds are retained: 0/4, 1/4, 2/4, 0/4, then 4/4 passing goals. The latest round covers item addition and deletion plus dialog cancellation and selection/confirmation. The full 35-test suite also passes. Short requirement references, compact step submissions and evidence-based locator correction reduce avoidable planning failures; retries preserve assertion types and expected values. This is a small debugging evaluation, not a production success rate. Human review remains essential. No human time-saving percentage or external user study is claimed.

Limits: 10 active requirements and 10 flows per project, 20 steps per flow; retired records do not consume active quota. Exploration permits three observations and six replayed actions per path. Each observation/flow starts fresh; network stays on the selected origin. Missing/ambiguous elements, blocked dependencies, interruption, empty scopes and stale results cannot approve a change. Frontend tracking excludes secrets, hidden folders, dependencies and build outputs; maximum 2000 files/20 MB, 1 MB each. This is not a hostile repository sandbox, login/payment tester or backend verification platform.

## Upgrade and verify

Read [upgrade and rollback](docs/UPGRADE-0.5.md). Startup backs up legacy SQLite before converting flow-only contracts. Old evidence and budget records remain; fresh checks establish current evidence.

```sh
python -m unittest discover -s tests -v
python scripts/cart_gate_v05.py
# Start run.py on port 8791 first:
python scripts/evaluate_projects.py
```

Tests use isolated storage. The live-model evaluation script freezes artifacts before calling the configured provider and refuses to overwrite an existing evaluation. Model evaluation costs money; ordinary rechecks do not.

## Publication

[Public repository](https://github.com/WeiR-h/loopcheck). Previous 0.4 release and Linux CI are historical evidence, not confirmation of 0.5 cloud deployment. AWS hosting, publicly hosted video and final Devpost submission remain independent pending steps. AgentCore is not deployed. [Architecture](docs/architecture.md) · [Submission draft](docs/SUBMISSION.en.md) · [Delivery status](docs/验证记录-v05.md).

MIT for LoopCheck and original examples, created with AI coding assistance. MDN fixtures are pinned and distributed unchanged with CC0 licenses and source notices under `examples/public`. TodoMVC React benchmark fixture retains its upstream MIT license and pinned provenance.
