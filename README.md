# Engineering AI Workbench — functional prototype

**Version 0.2 adds saved agents and persistent conversations.** Start with a natural-language message, review the proposed plan, then discuss the results in the same conversation. Local model and Docker settings are saved on this Mac; the portable archive excludes those machine settings and runtime data. See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the demonstration walkthrough.

A local browser workspace backed by **real LangGraph workflows, SQLite checkpoints, a compiled C++ application, and numerical Python analysis**. This demonstrates the architecture using synthetic engineering data. It is a single-user development prototype, not a production department deployment.

## Start here

On this Mac, open `start.command` (or run `bash start.command` from this directory), then open **http://127.0.0.1:8765**. If the existing server is already running, simply open that address. Do not start a second server on the same port. Stop a terminal-launched server with **Ctrl+C**.

The launcher reuses the tested environment from this task when available. On another Mac/Linux machine it creates `.venv` and installs the pinned dependencies. Python 3.11+ and a C++17 compiler are required. On Windows, use Python 3.12 and a Visual Studio Developer PowerShell, then run `./start.ps1`. Windows support is provided in source and launcher form; this prototype was tested on macOS only.

Manual setup from this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup.py
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

The C++ build script seeds `data/run-a.ewb` and `data/run-b.ewb` only if either file is missing. The `.ewb` format is a deliberately simple, native-endian binary fixture owned by the C++ application. It is neither an existing proprietary format nor a cross-platform archival standard. Regenerate fixture files on a different architecture.

## Conversational demonstration

1. Open **Agents** to create or edit an assistant. Set its name, purpose, local-model/demo mode, permitted tools and assigned released skills. Data scope and all three review gates are fixed for this prototype.
2. Choose **Start conversation**. Ask what it can do, then request “Compare Run A against Run B and explain the differences.” The local model proposes a supported method. The server checks permissions and pauses at **Plan review** before reading the binary inputs.
3. Approve the plan. The C++ executable exports the two synthetic runs; the released Python calculation produces a chart and numerical metrics. Ask follow-up questions in the conversation, inspect evidence, then accept or request changes to the report.
4. Ask “Now smooth the difference using a five-sample moving average.” Review the new plan, then inspect the exact model-drafted Python. Code approval covers its input snapshots and pinned worker image. Docker executes it; an independent reference checks all 101 output samples.
5. Open **Evidence** to see the Docker execution receipt. Completed containers are removed automatically and Docker logs are disabled; the Workbench retains results and provenance.
6. Propose an accepted workflow as a reusable skill and separately approve its release. Add reviewed notes, inspect the curated source catalog, and inspect or disable the bundled plugin.

**Guided workflows** preserves the original explicit workflow picker. **Demo-mode agents** use deterministic routing and canned explanations; the interface labels them as having no model. **Local-mode agents** actually call the configured Ollama/OpenAI-compatible model for conversation, bounded planning and script proposals. There is no silent fallback to demo mode or cloud inference.

The conversation can discuss and refine requests, but execution currently supports two methods only: comparing the fixed synthetic Run A/Run B and their centered five-sample moving-average difference. It cannot run arbitrary engineering analyses, accept new project files, install arbitrary tools or create unrestricted autonomous agents. Unsupported plans ask for clarification without executing tools.

## Implemented versus integration work

| Area | Working now | Remaining integration |
|---|---|---|
| Interface | Persistent conversations, agent editor, chart, metrics, history, evidence downloads | Desktop packaging, broader accessibility and user research |
| Orchestration | Actual LangGraph StateGraph, saved agent revisions, SQLite persistence, plan/code/result interrupts, retry/resume | Department queue, HA, richer cancellation and reconciliation |
| C++ gateway | Compiled dummy app, binary input validation, CLI export, source viewer | Real Windows apps, DLL/COM/IPC adapters and app ownership |
| Analysis | Real deterministic comparison and independent fixture tests | Your specific engineering methods and acceptance criteria |
| Generated Python | Structured script proposals, syntax checks, exact-artifact approval, Docker-only runner, reference validation and receipts | Production sandbox hardening, new-method qualification |
| Local models | Configured local adapter for conversation, structured planning, drafting and explanations | Broader task benchmarks and model-profile selection per agent |
| Frontier models | Separate OpenAI-compatible route with curated public questions only | Approved provider, credentials, and organizational approval |
| Skills | Candidate, release, reuse, retirement of bundled workflow recipes | General packaging, automated qualification, release signatures |
| Plugins | Bundled manifest and enable/disable enforcement | Signed distribution, compatibility upgrades/rollback, third-party extension isolation |
| Knowledge | Explicit note proposal, scope label, approval, retirement | Identity-backed access controls and evaluated retrieval |
| Governance | Same-origin request checks, per-process request token, local bind, no remote tracing | Corporate SSO/RBAC, independent reviewers, immutable audit, retention enforcement |
| MCP | Stable tool boundary demonstrated directly | No MCP server is implemented; add a wrapper after the real adapter is stable |
| Scheduling | Persistent individual jobs | Recurring schedules and a managed departmental runner |
| Data sources | Synthetic C++ binary application | SQLite/SQL Server enterprise adapters and file authorization |

The application never automatically installs model weights or Docker. They are configured separately. This session includes local model qualification and real Docker integration checks; see VALIDATION.md for results. A frontier provider is not configured or tested live.

## Connect a local or approved on-premises model

Set environment variables **before starting the server**. `.env.example` is a reference, not an automatically loaded secrets file. The base URL must expose OpenAI-compatible `POST /chat/completions` and normally ends in `/v1`.

```sh
export EWB_LOCAL_MODEL_URL=http://127.0.0.1:11434/v1
export EWB_LOCAL_MODEL=qwen2.5-coder:7b
# Optional when your approved server requires authentication:
# export EWB_LOCAL_API_KEY=...
bash start.command
```

A non-loopback engineering endpoint also requires `EWB_APPROVED_ONPREM=1`. That is an administrator assertion, not an automatic proof of corporate approval; configure only a host within your permitted data boundary. The prototype does not implement network-based verification of an approved on-premises server.

The local model must support JSON-schema structured chat responses for conversation, plans and script proposals. The launchers can also read non-secret settings from `data/local-model.json` with `url` and `model` keys; explicit environment variables take priority. Model credentials belong only in environment variables.

With a local-mode agent, each conversation request includes up to eight recent messages (each capped at 1,200 characters), the current job status and metrics, and the agent purpose/tool list. Complete conversation history is retained locally for the UI; older turns are not all supplied to the model. This is context retention, not fine-tuning. Reviewed notes are currently a human reference library rather than automatic model memory.

With a local model configured, the moving-average workflow obtains a draft script from it, validates its JSON envelope and Python syntax, then pauses for human approval. Syntax validation does not prove correctness or safety. The exact code is displayed, fingerprinted with the input snapshots and worker image, and independently checked against the supported moving-average method after execution. For a completed comparison, **Draft local-model explanation** calls the local endpoint with computed metrics only. The returned prose does not alter the numerical result or acceptance record.

A configured but unreachable model results in a visible error; it never silently switches an engineering request to a cloud model. Generation is currently restricted to the supported extension, not arbitrary new engineering methods.

## Connect a frontier or enterprise cloud model

```sh
export EWB_FRONTIER_URL=https://your-approved-provider.example/v1
export EWB_FRONTIER_MODEL=your-approved-model
export EWB_FRONTIER_API_KEY=...
```

Use **Model connections → Public topic**. Only a server-owned topic enum is accepted. The server creates a curated public prompt, with no free-form text, conversation, source, files, job ID, or measurements. The engineering graph never uses this route. Unknown request fields are rejected. OpenAI-compatible endpoints are supported; provider-specific APIs such as native Anthropic Messages or Azure-specific authentication need an additional adapter.

Credentials remain in the server environment. Requests disable proxy-environment inheritance, redirects are not followed, and frontier URLs require HTTPS. Do not mistake these development controls for a complete enterprise gateway.

## Enable reviewed Python execution

Install an approved Docker distribution separately. Obtain a reviewed Python runtime image through your normal process. It needs Python 3 and only the standard library for this demo. Record its **local image ID**:

```sh
docker image inspect --format '{{.Id}}' YOUR_REVIEWED_IMAGE
export EWB_WORKER_IMAGE=sha256:YOUR_LOCAL_IMAGE_ID
```

Restart the server, then create a **new** extension job so approval includes that image. A job approved against another image must not be reused; create a fresh request. The runner does not pull images during execution.

Each job runs in a fresh container with no network, a read-only root and inputs, a dedicated output folder, a non-root user, dropped capabilities, no new privileges, PID/CPU/memory/file limits, and a 30-second timeout. Neither model nor generated code can access the Docker socket. The trusted server launches Docker and validates the bounded result artifact. It refuses symlinked output and non-finite or misaligned values, and compares the supported extension against an independent reference calculation.

Production needs an approved security profile, aggregate output/disk quotas, stronger worker isolation where policy requires it, dependency governance, malware review, job identity enforcement, and robust crash cleanup. Do not use the prototype runner for untrusted external workloads or real sensitive engineering data.

## Layout

```text
backend/app.py       Local API, request boundary, capability lifecycle
backend/engine.py    LangGraph state machine and SQLite-backed jobs
backend/agents.py    Saved revisions, plan selection and capability checks
backend/conversations.py Persistent messages and bounded local-model actions
backend/analysis.py  Released calculation and no-model draft fixture
backend/models.py    Separate local and public model routes
backend/worker.py    Docker-only approved-script execution
legacy/              Dummy C++ application's source and build output
plugins/             Bundled capability manifest
frontend/            Dependency-free HTML/CSS/JavaScript interface
scripts/setup.py     Compile application and seed binary fixtures
tests/               Numerical, recovery, review, and policy checks
data/                Local runtime databases, synthetic inputs, job artifacts
```

The agent graph is **plan → plan review → export → prepare → optional code review → execute → result review**. Unsupported plans end in clarification before export. Guided workflows start at export. Changes to an agent revision or permission invalidate pending execution; start a fresh task after edits. Skills are selected only from assigned, compatible released recipes, and release status is checked again before use. Each review is a real LangGraph interrupt. The service resumes that same thread using a stored checkpoint. Running/queued jobs detected on restart become interrupted; use **Resume checkpoint**. Completed export snapshots are persisted. Side effects in this prototype are read-only extraction and job-scoped analysis; this does not provide exactly-once execution for future legacy write operations.

One process and one worker are supported. Do not run multiple web workers or expose the server on a network interface. The displayed reviewer and personal/project scopes are demonstration labels, not authenticated identities. Anyone with access to this local session can approve its artifacts. The local database is editable by the machine owner and is not an immutable audit system.

## Validation

```sh
.venv/bin/python -m pytest -q
```

Tests use a fresh temporary data directory and real C++ exports. They cover numerical reference values, corrupt input rejection, unit mismatches, stale/duplicate review, code rejection, worker-unavailable blocking, persisted review recovery, plugin enforcement, cancelled jobs, cloud context rejection, model-draft gating, and image-change invalidation. API tests additionally check same-origin protection and capability lifecycle behavior. Refer to `VALIDATION.md` for the verified run and limitations.

## Technical references

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Ollama OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility)
- [Qwen2.5-Coder 7B model card](https://ollama.com/library/qwen2.5-coder:7b)
- The companion Engineering AI Workbench design and investment document describes the broader enterprise target. Features listed as remaining integration above are not silently represented as implemented here.

## Management and design artifacts

- [Management presentation](docs/Engineering_AI_Workbench_Management_Proposal_Evolution.pptx)
- [Design and investment plan](docs/Engineering_AI_Workbench_Design_and_Investment_Plan.docx)
- [Interface concept](docs/Engineering_AI_Workbench_Interface_Concept.png)

These documents describe the broader enterprise target. The implementation and validation sections above identify the smaller working prototype scope. Local conversations, checkpoints, model settings, generated job artifacts and compiled executables are excluded from version control.
