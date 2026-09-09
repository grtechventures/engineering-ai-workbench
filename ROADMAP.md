# Engineering AI Workbench roadmap

These are planned increments, not implemented features or committed delivery dates.
Prioritize reliable engineering execution and retain the option to change harnesses.

## 1. Establish the engineering baseline

Qualify one real legacy application adapter, supported file readers, and numerical
reference cases. Improve generated-code reliability and failure-aware revisions.
Validate the Windows workflow and mandatory reviews before expanding use.

**Gate:** repeatable results on representative inputs, clear failure behavior,
access-boundary tests, and recoverable jobs with recorded evidence.

## 2. Make the harness replaceable

Publish versioned tool contracts and extract orchestration-independent job and
artifact APIs. Separate the UI from engine internals. Define versioned export and
import formats for conversations, skills, agent configurations, lineage, and
review evidence. Provide optional MCP adapters over the same authorized tools.

**Gate:** adapter contract tests, record round-trip tests preserving ownership and
lineage, and proof that an alternate client cannot bypass code or data approvals.
Imported skills remain subject to validation and release. No portable live
checkpoint format is assumed.

## 3. Qualify shared enterprise execution

Add authenticated project access, a durable queue, administrative roles,
monitoring, backup, and approved artifact storage. Connect Python and licensed
MATLAB workers behind the execution API. Validate license-aware resource
scheduling and workload concurrency before sizing a departmental rollout.

**Gate:** authorization, resource isolation, recovery and load tests; verified
MATLAB entitlements; agreed support and retention ownership. Live Teams or other
channel adapters require separate approved connectivity and identity mapping.

## 4. Evaluate another enterprise harness

Evaluate a candidate platform or agent framework, including Hermes if appropriate,
against one representative workflow. Reuse engineering adapters and workers;
adapt planning, instructions, and memory integration rather than assuming
behavioral equivalence. No replacement platform is selected by this roadmap.

**Gate:** acceptable numerical correctness, permissions, approval enforcement,
provenance, recovery, latency, cost, offline compatibility, and export capability.
A stronger model or a familiar chat interface alone is insufficient.

## 5. Migrate gradually with rollback

Route a small cohort or workflow to the qualified replacement. Keep existing jobs
in the original engine; retain historical records and evidence. Use idempotent
submission and explicit job ownership to avoid duplicate execution. Expand only
after acceptance tests pass and rollback is demonstrated.

**Gate:** reconciled jobs and records, functioning rollback, retention compliance,
and engineering-owner approval before retiring the previous engine.

See [ARCHITECTURE.md](ARCHITECTURE.md#harness-portability-and-migration) for the
portability boundaries. GitHub is a development/distribution option, not a runtime
requirement. Live SQLite state must remain off shared or synchronized folders.
