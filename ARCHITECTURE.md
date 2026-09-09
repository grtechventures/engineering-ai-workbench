# Architecture and extension guide

Engineering AI Workbench is a reference implementation of a reviewed engineering execution harness. All supplied data is synthetic. No GitHub account, repository, or cloud service is required at runtime.

## Runtime boundaries

Conversation → local model → bounded plan → LangGraph review → C++ export → released calculation / reviewed Docker script → numerical validation → result review.

The model proposes actions; server-owned methods define executable capabilities. New Python remains subject to approval of the exact script, input snapshots and image. MCP is not implemented: the application calls Python functions and the C++ CLI directly. A future MCP wrapper can expose those same reviewed adapters without changing the owning application's binary parser.

Plugins currently provide a bundled capability manifest and enable/disable enforcement. Skills are released workflow recipes, not arbitrary executable packages. Generated extension code requires fresh review when a skill runs.

## Persistence and memory

- **Job state:** local SQLite and LangGraph checkpoints retain messages, plans, exports, code, outputs and review events.
- **Knowledge:** explicitly proposed notes carry a source, revision and optional accepted source job. Approval makes them eligible for keyword retrieval. Retirement removes them from subsequent retrievals.
- **Retrieval history:** each conversation request records the references supplied to the local model. At most five notes are included. Matching is lexical, not semantic, and must not be interpreted as a completeness guarantee.
- **Methods:** accepted workflows can be proposed as candidate skills and separately released or retired.

Notes are treated as reference content, never authorization. Model prompt instructions reduce confusion but do not prove immunity to prompt injection; executable actions remain independently constrained by the server. Past messages may contain retired knowledge. Historical records remain available for audit, so retiring a note is not deletion or a guarantee the model forgets previous conversation content.

Personal/project scopes are labels within one local workspace. They are not multi-user access controls. Multiple users require authenticated ownership, project-scoped authorization on every read/write/retrieval, and database migration before deployment.

## Storage independent of Git

By default, databases, binary fixtures and runtime files live in `data/`. Set `EWB_DATA_DIR` to another **local disk** directory before setup and startup. Existing data is not moved automatically.

Evidence JSON is written automatically when a numerical result reaches review and after its acceptance/rejection. `EWB_ARTIFACT_DIR` can select a separate local directory or an administrator-mounted file share. Each artifact is addressed by its SHA-256, written through a temporary file and checked on read. This detects accidental changes; a machine owner can still alter both state and records. It is not an immutable audit service.

```powershell
$env:EWB_DATA_DIR = 'C:\Workbench\state'
$env:EWB_ARTIFACT_DIR = '\\fileserver\engineering\workbench-evidence'
./start.ps1
```

The process uses the current OS account's file permissions. Setting a share path is an explicit decision to copy evidence—including input exports and code—to that location. Validate permissions, capacity, availability and file semantics before use. A network file share has not been integration-tested in this release. Never place live SQLite databases in a shared/synchronized folder, OneDrive directory, or WAN share. Do not run multiple web workers.

`FileArtifacts.put/get/info` is the provider boundary for future stores. SharePoint, OneDrive and Google Drive adapters, synchronization, credential flows and ACL mirroring are **not implemented**. Cloud storage approval is separate from cloud inference approval. Engineering model calls remain local or explicitly approved on-premises; the frontier route accepts curated public topics only.

## Replay and reproducibility

Evidence → **Replay saved inputs** creates a child job using the parent's persisted C++ exports. **Run with current inputs** re-exports the current binary fixtures. Both preserve the parent and use fresh applicable reviews. Saved agents use their current revision and permissions.

Replay uses current calculation code and worker configuration. It is not an archived executable environment. Generated scripts are drafted/reviewed again; exact historical model output is not promised. Historical evidence includes method identifiers, inputs, hashes, script and image identity where applicable.

## Bounded experimentation

From an accepted released comparison, Evidence → **Explore smoothing parameters** proposes up to eight unique odd window sizes between 1 and 21. Window 1 provides an unsmoothed baseline. A 1–10 second calculation budget is checked between trials; this is not a hard process-level deadline. Each trial operates on 101 synthetic samples and uses released Python code in the trusted service. It does not generate code or use Docker.

Approval covers the input snapshot, method, windows and budget. Results include distortion from the unsmoothed difference, roughness, all sample values and an independent prefix-sum reference check. Neither metric proves physical accuracy. The system selects no winner. Result acceptance is separate from execution approval.

A restart marks running studies interrupted. Explicit reapproval reruns the bounded read-only batch; partial results are not checkpointed per trial. Concurrent approvals are rejected once a study is running. Model-selected hypotheses, recursive code modification and automatic method promotion remain future work.

## Next deployment increments

1. Qualify a real application adapter and numerical reference cases.
2. Add authenticated users/projects, a managed database, durable queue and administrative review roles.
3. Evaluate a replaceable memory provider against known retrieval cases before adding embeddings or a knowledge graph.
4. Add approved document-store connectors with permissions, deletion and retention propagation.
5. Add adaptive experiments only for domain-qualified objectives, independent evaluators and explicit compute budgets.

The current release provides no SSO, signed third-party plugin installation, shared departmental service, automatic fine-tuning, GBrain dependency, or recurring background research.
