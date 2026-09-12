# LoopCheck 0.5.2 judging guide

[Download the verified source](https://github.com/WeiR-h/loopcheck/releases/tag/v0.5.2), follow README.en.md and open `/judge`. The [English demonstration](https://www.youtube.com/watch?v=-Gp8uHgHy-s) is public and runs for 3 minutes 40 seconds.

The free keyless cart walkthrough uses preset requirements and deliberately scripted edits with real browser checks. Establish a baseline, approve a future coupon requirement, observe incomplete coverage, introduce the disclosed price regression, read full expected/actual reproduction evidence, repair and recheck four approved flows. This path needs no provider key. It is not live model planning.

Live Strands planning is a separate entry using a pinned, unchanged MDN shopping list. It needs a server-side provider key. Describe the goal, review proposed business requirements, generate and review checks, then replay without another model call. Two generated checks were reviewed and passed in the recorded UI flow. The fresh four-goal debugging rounds finished 2/4 and 1/4; all failures are retained. Earlier 0.5.0 results are historical, not current reliability claims.

[The exact release CI](https://github.com/WeiR-h/loopcheck/actions/runs/34670989974) passed 48 tests, the budget/cart/MCP gates and all 12 frozen artificial mutations. The public-mode container passed at a 768 MiB limit with a 328.53 MiB peak. These are CI measurements with zero provider calls, not an AWS or production load test.

Public mode accepts bundled samples only. Native local mode can connect a trusted folder and running preview; MCP exposes three tools and cannot approve requirements. Missing, stale, interrupted and uncovered checks cannot authorize a change.

Hosted live-provider access and final Devpost submission remain pending. See [current external delivery evidence](evidence/v052-publication.json) and [retained attempts](VERIFICATION-0.5.2.md). No human-efficiency percentage or prize outcome is claimed.
