# Engineering AI Workbench

A local engineering analysis workspace with conversational agents, reviewed tools, persistent evidence, and reusable methods. The reference implementation uses synthetic data and a small C++ application to demonstrate integration with application-owned binary formats.

**Version 0.4** adds persistent once/daily/weekly scheduling of approved released comparisons, alongside reviewed knowledge, evidence storage, replay, and bounded studies. Engineers can use an installed copy or a source archive without a GitHub account. This is a single-user prototype; it is not a production shared service.

- Ask questions and review a proposed analysis plan.
- Execute released calculations or inspect generated Python before isolated execution.
- Retrieve approved project notes with provenance; retire outdated knowledge.
- Revisit results, replay saved inputs, and compare bounded parameter trials.
- Propose accepted workflows as reusable skills, with a separate release review.

See [the walkthrough](DEMO_GUIDE.md), [architecture and storage](ARCHITECTURE.md), and [validation](VALIDATION.md).

## Windows 11 setup

The application runs in a local browser on Windows 11. Install Python 3.12 and a C++17 toolchain (Visual Studio Build Tools with the C++ workload and Windows SDK). Use **Developer PowerShell for Visual Studio** so the Microsoft `cl` compiler is available.

For the conversational and generated-Python demonstration, also install [Ollama for Windows](https://docs.ollama.com/windows) and [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Run Docker in **Linux-container mode**, for example with its WSL 2 backend. The C++ gateway runs natively on Windows; the approved Python extension runs inside a Linux container.

Clone or download this repository and provision Python dependencies using the manual setup below (or an approved offline wheel bundle). Open Developer PowerShell in its root directory, start Ollama and Docker Desktop, then run the following one-time provisioning commands only where downloads are permitted:

```powershell
# Download the demo model and Python worker image once.
ollama pull qwen2.5-coder:7b
docker pull python:3.12-slim

# Configure this PowerShell session before starting the Workbench.
$env:EWB_LOCAL_MODEL_URL = 'http://127.0.0.1:11434/v1'
$env:EWB_LOCAL_MODEL = 'qwen2.5-coder:7b'
$env:EWB_WORKER_IMAGE = (docker image inspect --format '{{.Id}}' python:3.12-slim).Trim()

./start.ps1
```

Open **http://127.0.0.1:8765** in the Windows browser and keep the PowerShell window open. Provision the Python environment first. The launcher compiles the dummy C++ application, creates synthetic inputs and starts the service; it never downloads dependencies. If the server is already running, use that instance rather than starting a second server on the same port. Stop it with **Ctrl+C**.

The environment variables above last for the current PowerShell session. Set them again in a new session, or save the non-secret model and image settings using the files described below. On a fresh checkout, create an agent in **Agents**; agents and conversations from the development machine are not included.

**Windows validation remains pending.** The existing automated and live integration checks were performed on macOS; the presence of a Windows launcher does not imply those checks have passed on Windows. Run the validation command below and rehearse both the comparison and Docker extension before using the Windows installation.

Manual Windows setup, if you need to run the launcher steps individually:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe scripts/setup.py
./.venv/Scripts/python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

For offline dependency provisioning, prepare a vetted wheel directory on a separate approved build machine, then install locally:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install --no-index --find-links C:/approved-wheels -r requirements.txt
```

For optional macOS/Linux development, `bash start.command` remains available with Python 3.11+ and a C++17 compiler. Windows 11 is the primary setup documented here.

The C++ build script seeds `data/run-a.ewb` and `data/run-b.ewb` only if either file is missing. The `.ewb` format is a deliberately simple, native-endian binary fixture owned by the C++ application. It is neither an existing proprietary format nor a cross-platform archival standard. Regenerate fixture files on a different architecture.

## Conversational demonstration

1. Open **Agents** to create or edit an assistant. Set its name, purpose, local-model/demo mode, permitted tools and assigned released skills. Data scope and all three review gates are fixed for this prototype.
2. Choose **Start conversation**. Ask what it can do, then request “Compare Run A against Run B and explain the differences.” The local model proposes a supported method. The server checks permissions and pauses at **Plan review** before reading the binary inputs.
3. Approve the plan. The C++ executable exports the two synthetic runs; the released Python calculation produces a chart and numerical metrics. Ask follow-up questions in the conversation, inspect evidence, then accept or request changes to the report.
4. Ask “Now smooth the difference using a five-sample moving average.” Review the new plan, then inspect the exact model-drafted Python. Code approval covers its input snapshots and pinned worker image. Docker executes it; an independent reference checks all 101 output samples.
5. Open **Evidence** to see the Docker execution receipt. Completed containers are removed automatically and Docker logs are disabled; the Workbench retains results and provenance.
6. Propose an accepted workflow as a reusable skill and separately approve its release. Add reviewed notes, inspect the curated source catalog, and inspect or disable the bundled plugin.

**Guided workflows** preserves the original explicit workflow picker. **Demo-mode agents** use deterministic routing and canned explanations; the interface labels them as having no model. **Local-mode agents** actually call the configured Ollama/OpenAI-compatible model for conversation, bounded planning and script proposals. There is no silent fallback to demo mode or cloud inference.

The conversation can discuss and refine requests, but execution currently supports two methods only: comparing the fixed synthetic Run A/Run B and their centered five-sample moving-average difference. A separate reviewed parameter-study flow explores smoothing windows using released code. It cannot run arbitrary engineering analyses, accept new project files, install arbitrary tools or create unrestricted autonomous agents. Unsupported plans ask for clarification without executing tools.

## Implemented versus integration work

| Area | Working now | Remaining integration |
|---|---|---|
| Interface | Persistent conversations, agent editor, chart, metrics, history, evidence downloads | Desktop packaging, broader accessibility and user research |
| Orchestration | Actual LangGraph StateGraph, saved agent revisions, SQLite persistence, plan/code/result interrupts, retry/resume | Department queue, HA, richer cancellation and reconciliation |
| C++ gateway | Compiled dummy app, binary input validation, CLI export, source viewer | Real Windows apps, DLL/COM/IPC adapters and app ownership |
| Analysis | Real deterministic comparison and independent fixture tests | Additional engineering methods and acceptance criteria |
| Generated Python | Structured script proposals, syntax checks, exact-artifact approval, Docker-only runner, reference validation and receipts | Production sandbox hardening, new-method qualification |
| Local models | Configured local adapter for conversation, structured planning, drafting and explanations | Broader task benchmarks and model-profile selection per agent |
| Internet inference | Disabled at API and model client, even with frontier configuration | Any future cloud mode requires a separate policy change and review |
| Skills | Candidate, release, reuse, retirement of bundled workflow recipes | General packaging, automated qualification, release signatures |
| Plugins | Bundled manifest and enable/disable enforcement | Signed distribution, compatibility upgrades/rollback, third-party extension isolation |
| Knowledge | Sourced notes, revision-checked review, keyword retrieval into local conversation, retrieval history, retirement | Multiple projects, identity-backed access controls, semantic retrieval, retention automation |
| Evidence and replay | Content-addressed JSON artifacts, saved input snapshots, linked replay with fresh reviews | Historical executable/runtime retention for exact environment reproduction |
| Experiments | Reviewed smoothing-window sweep, trial/time bounds, independent numerical reference, result review | Adaptive hypothesis selection and domain-qualified experiment methods |
| Storage | Local SQLite; configurable local or mounted-filesystem evidence folder; no Git requirement | Shared database/service, SharePoint, OneDrive, Google Drive providers |
| Governance | Same-origin request checks, per-process request token, local bind, no remote tracing | Corporate SSO/RBAC, independent reviewers, immutable audit, retention enforcement |
| MCP | Stable tool boundary demonstrated directly | No MCP server is implemented; add a wrapper after the real adapter is stable |
| Scheduling | Persistent once/daily/weekly schedules, explicit recipe approval, permission rechecks, overlap prevention, missed-run records, pause/resume/cancel | Shared departmental runner, OS startup/wake integration, adaptive workflows |
| Data sources | Synthetic C++ binary application | SQLite/SQL Server enterprise adapters and file authorization |

The application never automatically installs model weights or Docker. They are configured separately. The initial development validation includes local model and real Docker integration checks; see VALIDATION.md for the platform and results. A frontier provider is not configured or tested live.

## Connect a local or approved on-premises model

Set environment variables **before starting the server**. `.env.example` is a reference, not an automatically loaded secrets file. The base URL must expose OpenAI-compatible `POST /chat/completions` and normally ends in `/v1`.

```powershell
$env:EWB_LOCAL_MODEL_URL = 'http://127.0.0.1:11434/v1'
$env:EWB_LOCAL_MODEL = 'qwen2.5-coder:7b'
# Optional when your approved server requires authentication:
# $env:EWB_LOCAL_API_KEY = '...'
./start.ps1
```

A non-loopback engineering endpoint requires a literal private LAN IP, `EWB_APPROVED_ONPREM=1`, and that exact IP in `EWB_APPROVED_MODEL_IPS`. This is an administrator-configured allowlist; it does not establish that the destination model server is itself offline.

The local model must support JSON-schema structured chat responses for conversation, plans and script proposals. The launchers can also read non-secret settings from `data/local-model.json` with `url` and `model` keys; explicit environment variables take priority. Model credentials belong only in environment variables.

With a local-mode agent, each conversation request includes up to eight recent messages (each capped at 1,200 characters), the current job status and metrics, and the agent purpose/tool list. Complete conversation history is retained locally for the UI; older turns are not all supplied to the model. This is context retention, not fine-tuning. Up to five approved keyword-matched notes are also supplied to the local conversation model, with source and revision metadata. Retrievals are recorded separately from chat history. These notes are context, not execution authority. Retired notes are excluded from new retrievals; past conversations and audit records retain their historical content.

With a local model configured, the moving-average workflow obtains a draft script from it, validates its JSON envelope and Python syntax, then pauses for human approval. Syntax validation does not prove correctness or safety. The exact code is displayed, fingerprinted with the input snapshots and worker image, and independently checked against the supported moving-average method after execution. For a completed comparison, **Draft local-model explanation** calls the local endpoint with computed metrics only. The returned prose does not alter the numerical result or acceptance record.

A configured but unreachable model results in a visible error; it never silently switches an engineering request to a cloud model. Generation is currently restricted to the supported extension, not arbitrary new engineering methods.

## Offline security policy

Internet inference is disabled, including the general-reasoning API. Configuring a frontier URL or key does not enable it. Local model requests accept literal loopback addresses (localhost is converted to 127.0.0.1). No model destination is accepted from conversation text.

An approved LAN model requires a literal private IP plus both `EWB_APPROVED_ONPREM=1` and an exact entry in the comma-separated `EWB_APPROVED_MODEL_IPS` allowlist. Public and link-local addresses, DNS hostnames, URL credentials, queries and fragments are rejected. Prefer HTTPS for LAN connections. Redirects and environment proxies are disabled.

See [SECURITY.md](SECURITY.md) for enforcement and remaining OS-level requirements. This policy intentionally disables the earlier optional frontier route.

## Enable reviewed Python execution

Install an approved Docker distribution separately. Obtain a reviewed Python runtime image through your normal process. It needs Python 3 and only the standard library for this demo. Record its **local image ID**:

```powershell
$env:EWB_WORKER_IMAGE = (docker image inspect --format '{{.Id}}' YOUR_REVIEWED_IMAGE).Trim()
```

For persistent non-secret worker configuration, create the `data` directory if needed and save the image ID in `data/worker-image.txt` (plain UTF-8 text). The Windows launcher reads it when the environment variable is unset. Obtain the image ID on the target Windows machine; do not copy a development machine's image ID.

Restart the server, then create a **new** extension job so approval includes that image. A job approved against another image must not be reused; create a fresh request. The runner does not pull images during execution.

Each job runs in a fresh container with no network, a read-only root and inputs, a dedicated output folder, a non-root user, dropped capabilities, no new privileges, PID/CPU/memory/file limits, and a 30-second timeout. Neither model nor generated code can access the Docker socket. The trusted server launches Docker and validates the bounded result artifact. It refuses symlinked output and non-finite or misaligned values, and compares the supported extension against an independent reference calculation.

Production needs an approved security profile, aggregate output/disk quotas, stronger worker isolation where policy requires it, dependency governance, malware review, job identity enforcement, and robust crash cleanup. Do not use the prototype runner for untrusted external workloads or real sensitive engineering data.

## Layout

```text
backend/app.py       Local API, request boundary, capability lifecycle
backend/engine.py    LangGraph state machine and SQLite-backed jobs
backend/agents.py    Saved revisions, plan selection and capability checks
backend/conversations.py Persistent messages and bounded local-model actions
backend/analysis.py  Released calculations, bounded study and draft fixture
backend/workspace.py Knowledge retrieval, evidence provider, replay and studies
backend/schedules.py Persistent scheduler, calendar policy, atomic dispatch and authority checks
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

```powershell
./.venv/Scripts/python.exe -m pytest -q
```

Tests use a fresh temporary data directory and real C++ exports. They cover numerical reference values, corrupt input rejection, unit mismatches, stale/duplicate review, code rejection, worker-unavailable blocking, persisted review recovery, plugin enforcement, cancelled jobs, cloud context rejection, model-draft gating, and image-change invalidation. API tests additionally check same-origin protection and capability lifecycle behavior. Refer to `VALIDATION.md` for the verified run and limitations.

## Technical references

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Ollama OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility)
- [Qwen2.5-Coder 7B model card](https://ollama.com/library/qwen2.5-coder:7b)
- The architecture guide describes extension boundaries. Features listed as remaining integration are not implemented in this release.

## Reference documents

The optional presentation and design files in `docs/` describe earlier deployment proposals, not the current runtime contract. [ARCHITECTURE.md](ARCHITECTURE.md) and this README describe the implemented release. Review historical presentation/document contents separately before redistributing them.

## Distribution

GitHub is a source distribution option, not an application dependency. A maintainer can supply a ZIP through an approved internal software channel. The runtime never pushes conversations, knowledge, databases, or reports to a repository. Keep generated data and local credentials outside distributed packages.

Repository visibility and team access are managed separately from the application. No public release or open-source license is introduced by this update; select licensing terms before advertising reuse rights for an eventual public release.

## Schedule a released workflow

Open an accepted comparison without generated Python, then **Evidence → Schedule this workflow**. Select an agent and an assigned released comparison skill, a local start date/time, an IANA timezone, and once/daily/weekly frequency. Save the proposal, then **Approve schedule and recipe**. Approval authorizes that fixed recipe and current workspace inputs; the model cannot re-plan scheduled work.

**Schedules** shows the next occurrence, status and latest 50 run records. Open a run to review its result. Pause stops future dispatch. Resume skips missed occurrences; cancellation prevents further dispatch and blocks queued jobs at their next authority check. Already-completed results are retained. Cancel an individual analysis through its job controls when needed.

The scheduler starts with the web service and uses no internet or operating-system cron. The machine must be awake and the service running. It does not install a Windows service or wake the computer. Timezone data is provisioned through the pinned tzdata dependency; offline installations need its wheel in their approved bundle.

See [SCHEDULING.md](SCHEDULING.md) for timing, approval and recovery semantics.

## Runtime Python and tool registration

Generate reviewed Python tasks for calculations, tables and plots, then revise their scripts in the conversation. Each version runs only after approval in a pinned local Docker image. See [Dynamic Python tasks](PLOTTING.md) for setup, artifact review and scope limits. The Tools page records application and optional source-folder references for future reviewed adapter integration; registration does not enable execution or source access.

## Create or import skills and packages

Skills library supports direct drafts and Markdown/JSON import without an accepted analysis. Plugins supports declarative multi-skill packages. See [Skill authoring](SKILL_AUTHORING.md) for formats, release and agent assignment, and current limitations. Multiple tool registrations are supported.

## Source and data locations

Source discovery accepts registered code folders/files. Data sources records dataset locations, formats and reader references, with bounded CSV preview. Access is denied unless an administrator configures approved roots. See [Source and data locations](DATA_SOURCES.md) for limits and setup. These registrations do not yet attach inputs or source context to model tasks.

## Models, runtime and security settings

Models & runtime supports saved Ollama, LM Studio and other OpenAI-compatible profiles: add/edit, test, and activate. All local-mode agents share the active connection; separate per-agent endpoints are not implemented. Editing a profile requires activating it again. Profile settings persist in SQLite. Endpoint validation still blocks public internet destinations; LAN model IPs require server-side approval. API credentials remain server-managed and are not stored in profiles.

Docker settings verify and save full local image IDs for comparison and dynamic Python workers. The diagnostic checks the local daemon, not analysis correctness. Images are never downloaded and remote Docker contexts are rejected. Changes can invalidate pending approvals. The Security & permissions page links to operational permission controls and can persistently disable resource inspection. An administrator can restore inspection by removing the `discovery_disabled` setting from the workspace database while the service is stopped; approved filesystem roots are still required. Enterprise positioning belongs in deployment documentation rather than these settings.

## Conversation attachments

Use Attach files or Choose folder in Conversations, then ask a question or request a Python calculation. Explicitly selected files are copied into that conversation, not read through arbitrary server paths. Supported UTF-8 text formats are CSV, TXT, Markdown, JSON, and selected source extensions. Limits: 8 KB per file, ten files and 32 KB per conversation. Unsupported or oversized selections are rejected; a partially completed batch may leave earlier files attached. Clear attachments removes them from future questions, but prior generated task snapshots retain their reviewed inputs.

A local-mode agent is required for open-ended questions and generated calculations. New Python tasks use attached text snapshots instead of synthetic run data. Revisions retain the original task snapshot. PDFs, Office documents, images, binary formats, live folder monitoring and large datasets are not supported by this uploader. Uploading files is an explicit data selection, not an expansion of server filesystem permissions. Files are untrusted context and cannot grant tool authority.
