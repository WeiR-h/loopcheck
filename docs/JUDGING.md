# LoopCheck 0.5 judging guide

Start the local edition with the instructions in README.en.md. Choose Everyday Cart, save a future coupon requirement, and see that an uncovered requirement prevents acceptance. Review requirement changes before confirming. Existing Pocket Budget remains available for browser checks.

For reproducible automatic evidence, run `scripts/cart_gate_v05.py` then `scripts/verify_mcp_v05.py`. The gate copies the bundled cart, records its browser flows, adds an explicitly scripted feature and regression, then repairs source. It uses no model calls. Requirements are confirmed by the test harness, not a claimed human study.

Inspect `docs/验证记录-v05.md` and `docs/evidence/v05-planning-results*.json` for all live model planning outcomes, including unsuccessful rounds. The latest four-goal round passes both shopping-list and both dialog goals. All five debugging rounds (0/4, 1/4, 2/4, 0/4, 4/4) remain available; this is not held-out generalization evidence. Human review remains necessary.

Public Docker mode permits only bundled examples. Local project folders and MCP require the native local edition. Hosted judge access, public video publication and final submission are separate pending delivery steps. The existing 0.4 release/CI is historical; do not treat it as a 0.5 deployment test.
