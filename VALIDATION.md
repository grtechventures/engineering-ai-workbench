# Prototype validation — version 0.2

Verified on macOS, 7 September 2026, with the pinned Python 3.12 dependencies and LangGraph 1.2.11.

## Automated checks

**38 tests passed.** One upstream Starlette/AnyIO deprecation warning remains. The tests cover:

- Real C++ binary export and independently calculated comparison values; corrupt files and mismatched units are rejected.
- Persisted LangGraph checkpoints, restored plan/result reviews, cancellation, duplicate decisions, and stale script/result/plan approval rejection.
- Agent creation and optimistic revisions; tool scope, disabled agents, revoked skill release, and changed configurations block execution.
- Conversation persistence, local-only model routing, unsupported model actions, and explicit failure when the local endpoint is not configured.
- Model drafts pause for exact-code review; malformed Python never executes, incorrect numerical outputs cannot become accepted reports, and changed worker images invalidate approval.
- API request-origin/token checks, evidence export, curated read-only source, knowledge/skill lifecycle, and rejection of engineering context or additional fields on the public frontier route.

## Live local model and execution

Ollama was already installed with Llama 3 and Mistral. Llama 3 was tried first and did not qualify for reliable script drafting in these cases. With the user's authorization, Qwen2.5-Coder 7B was installed through Ollama and configured as the local model.

The actual model was exercised for greetings, conversational comparison requests, structured plans, result follow-ups, extension requests and structured Python drafting. Review caught a wrong edge-window divisor in an early draft. The drafting contract now supplies the precise reviewed window algorithm. A subsequent inspected model-generated script ran in the pinned Python 3.12 Docker image, and all **101 output points** matched the independent reference to **1e-10**.

The browser also completed a separate real model-driven comparison and extension, including plan review, actual C++ export, script review, Docker execution, numerical validation and result acceptance. The extension's retained receipt records a successful exit, image and script identity, timing and container cleanup. Docker Desktop 4.90.0 is installed; the model and Docker configuration are restored by the launcher.

Expected base metrics: RMSE approximately **0.01327444 a.u.**, maximum absolute difference approximately **0.02265 a.u.**, **101 aligned sample pairs**. There is no engineering acceptance tolerance in the synthetic fixture.

## Browser verification

The in-app browser was used to create and rename an agent, save a new revision, disable/re-enable it, run conversational analyses, ask a result follow-up, inspect plan/code/result approvals and the Docker receipt, and reload the persisted conversation. Plugin enable/disable, reviewed project notes, and the read-only source view were also exercised. Browser testing found that the original JavaScript skill-naming prompt did not appear in the embedded browser; it was replaced by an inline form. A baseline comparison was proposed, released and rerun as a skill. Existing user jobs were backed up and preserved through the upgrade.

## Limits of this validation

These are focused prototype checks, not a broad benchmark or production qualification. Small-model drafts were observed making errors, including an unsupported similarity interpretation; model prose remains explicitly labelled as a draft and does not change numerical results. Python syntax checks are not a proof of safety or correctness. Human review and method-specific reference checks remain necessary.

Not validated live: a frontier provider, real engineering files, Windows compilation/runtime, SSO/RBAC, multiple users/workers, arbitrary plugins, network deployment, long-context reliability, and general autonomous engineering tasks. Retained notes do not automatically train or augment the model. Only the fixed comparison and five-sample moving-average extension are executable today.
