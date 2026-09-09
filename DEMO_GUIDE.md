# Engineering AI Workbench: demonstration guide

## Start on Windows 11

1. Complete the [Windows 11 setup in README.md](README.md#start-here--windows-11): Python 3.12, a C++17 compiler, Ollama, Docker Desktop in Linux-container mode, the demo model and a pinned worker image.
2. Open **Docker Desktop** and wait for its engine to start. Open **Ollama** if it is not already running.
3. Open **Developer PowerShell for Visual Studio** in the repository folder, set the model and worker environment variables from the README, and run **`./start.ps1`**. Leave that window open. If the Workbench is already running, use the existing instance.
4. Open [Engineering AI Workbench](http://127.0.0.1:8765/) in the Windows browser.
5. Run the README's validation command and rehearse the comparison and reviewed Docker extension on this Windows 11 machine before the presentation. Previous integration checks were performed on macOS, not Windows.

The example configuration uses **Qwen2.5-Coder 7B through local Ollama** and a pinned Python 3.12 Linux Docker image. Configure these on the demo machine; the repository does not include downloaded models, machine settings, saved agents or conversation history. No cloud account is needed. The first model response may be slower while weights load into memory.

## Present the conversational flow

Open **Agents** and create **Engineering Analysis Agent** (or use **Create starter agent**), select local mode, and assign its released skills and permitted tools. Then click **Start conversation**. On subsequent launches you can reuse that saved agent.

Send these messages one at a time:

> What can you help me do?

> Compare Run A against Run B and explain the differences.

Review the proposed method on the right and click **Approve plan**. The actual C++ application reads the binary fixtures and the released Python calculation computes the report. Inspect the chart, inputs and evidence. Numerical expectations are approximately **0.01327 a.u. RMSE**, **0.02265 a.u. maximum difference**, and **101 aligned samples**.

> What does the RMSE of this result mean?

The local model answers using this conversation and the computed metrics. Its explanation is a draft; acceptance is an explicit report decision. Click **Accept report** after inspecting the synthetic results.

> Now smooth the difference using a five-sample moving average.

Approve the new plan, then **read the generated script** before clicking **Approve script**. Confirm that it reads the exported JSON, computes B minus A, averages the available centered window, and writes the result. Every newly generated script needs fresh review. If a draft is incorrect, reject it and submit a new request; do not approve it simply because a model proposed it.

Docker runs the approved script in a fresh isolated container. The Workbench checks all output points against the independent reference. **Evidence** includes a Docker receipt with the image, script hash, exit status, timing and cleanup. Docker Desktop normally shows no completed container because it is removed after execution and container logging is disabled.

## Show reusable capabilities

- Accept a report and choose **Propose reusable skill**. Give it a name, then approve its release in **Skills library**. You can assign that released recipe to an agent or run it directly. Extension code still requires fresh review.
- **Reviewed knowledge** stores proposed, approved or retired notes. It does not train the model or automatically inject notes into conversations.
- **Plugins** shows the bundled Run Comparison package. Disabling it blocks tool execution; re-enable it after demonstrating the control.
- **Source discovery** exposes the dummy C++ reader and released comparison source as a curated, read-only catalog.
- **Job history** preserves prior work. Reload the page to show conversation persistence. If the server stops mid-job, restart it and choose **Resume checkpoint**.

## State the prototype boundaries

This is a conversational local prototype with real model calls and actual tool execution. It supports two synthetic runs, a released comparison and a reviewed five-sample moving-average extension. It does not yet ingest your engineering files or perform arbitrary analyses. Agent configuration changes invalidate pending execution; start a new task after editing permissions.

Local model responses can be wrong. The verified numerical tools, plan/code/result review gates, and evidence provide the foundation for qualification; these few demonstration cases are not a general model benchmark. Corporate SSO, independent reviewers, production plugin distribution, real Windows adapters and department operation remain implementation work. The frontier connector accepts curated public questions only and has no provider configured.

## If something stops

- **Model unavailable:** open Ollama, confirm the configured model is installed, then retry the message. No cloud fallback occurs.
- **Docker execution blocked:** open Docker Desktop and wait for the engine. Resume only if the exact approved inputs, script and image are unchanged. Otherwise create a fresh request.
- **Invalid draft or failed numerical check:** reject the proposal or start a new analysis. The prototype does not silently accept or repair failed results.
- **Session restarted:** refresh the browser and retry the action. Jobs and conversations remain in local SQLite databases.
- **Port already in use:** the Workbench may already be running. Open its existing page rather than starting a second server.

See [README.md](README.md) for installation and architecture, and [VALIDATION.md](VALIDATION.md) for the tested scope.
