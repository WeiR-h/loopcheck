# Agents for Humans: preserving user intent across AI coding changes with LoopCheck

Draft for author review and publication. AI-assisted writing and implementation. No publication URL exists yet.

An AI coding assistant can implement a requested feature while accidentally breaking behavior that worked a few minutes earlier. For a solo builder, the cost is often another round of clicking through the app, taking screenshots and describing the same problem again.

LoopCheck explores a narrow way to reduce that repeated work. A Strands agent inspects a running local frontend and proposes executable acceptance requirements. The builder reviews them before they become an active contract. Later source changes trigger independent browser checks, and the failed step, expected value, observed value and screenshot return to the existing coding assistant through MCP.

The first live planning attempt showed why approval and execution matter. The model confused invalid input with a negative calculated result and chose an input-value assertion for an output element. We retained that attempt, added explicit element metadata and trial execution, and kept model prose separate from the browser verdict. A model summary cannot turn an incomplete or failed run green.

In an original budget-calculator fixture, a confirmed check expected 850.00 but observed 1550.00 after an injected arithmetic regression. The actual stdio bridge returned the evidence. The development agent corrected the original source; the same confirmed requirements then passed. LoopCheck did not repair its own tests or silently change user expectations.

We also froze twelve artificial modifications across three frontend structures: the calculator, a pinned public TodoMVC React app, and LoopCheck's own frontend. Six faults were detected and six ordinary feature or visual changes passed. This small controlled benchmark is not a claim of universal reliability, naturally occurring bug coverage or measured human time savings. The user chose to defer the human timing study.

AWS's implemented contribution is Strands Agents SDK for observation, tool orchestration and structured planning. The model endpoint is Alibaba Cloud Model Studio Beijing; repeated browser checks do not use the model. AgentCore was not deployed. This choice kept work focused on a functioning local workflow and the project's small budget.

Next work is explicit user-reviewed replacement of outdated requirements, broader accessibility coverage and independently observed user trials. Before publishing this article, replace draft release links with verified public repository, evidence and demo URLs.
