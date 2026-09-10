# Judge walkthrough — LoopCheck 0.4

Audience: solo builders using AI to develop small web apps. Problem: a requested change can break previously working behavior, leading to repeated clicking, screenshots and bug explanations.

1. Open `/judge` and choose **Try it first: Pocket Budget**. This is an original, explicitly disclosed fixture.
2. Select **Prepare acceptance checks**. Strands observes the actual page, proposes three workflows and trial-runs them. Review the goals and executable steps, then approve.
3. **Check this change** records the passing baseline. Replaying confirmed flows uses no model request.
4. In the local edition, connect your coding AI through MCP and enable source watching. Change the original project with your coding tool. The supplied evidence demonstrates an injected arithmetic regression.
5. Inspect the expected 850.00 and observed 1550.00, the failed step and screenshot. Return the repair brief to the coding AI. Correct the source and run the same unchanged requirements again.
6. Read the frozen three-project benchmark and live MCP evidence. The twelve mutation outcomes are a small controlled evaluation, not a general reliability claim. Human time savings were not measured.

Public sample mode demonstrates planning and acceptance. Full original-directory watching and MCP are local-edition features. The repository must include this distinction. Public deployment must supply model access to judges without requiring a paid API key.

The previous task-list repair app remains at `/legacy` for historical comparison. AgentCore is not deployed. Public source: [https://github.com/WeiR-h/loopcheck](https://github.com/WeiR-h/loopcheck). [Linux CI](https://github.com/WeiR-h/loopcheck/actions/runs/34462275115) passed 25 tests, all 12 frozen mutation cases and a fresh Docker browser gate. At a 768 MiB container memory limit, peak usage was 324.27 MiB with no OOM. This CI gate used no model calls and is not an AWS instance capacity test. Hosted judging access, YouTube/Vimeo publication and Devpost submission remain pending. AgentCore is not deployed. [Publication evidence](evidence/v04-publication.json).
