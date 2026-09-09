# Validation — version 0.4

## Automated validation

92 automated tests passed on macOS with Python 3.12 on 8 September 2026. One upstream Starlette/AnyIO deprecation warning remains. Run `python -m pytest -q` in the configured environment after compiling/seeding with `scripts/setup.py`.

Coverage includes:

- Real C++ exports and independent numerical references; corrupt files and unit mismatches.
- LangGraph checkpoint recovery, plan/code/result review, stale and duplicate decisions.
- Agent revisions, disabled agents/plugins, revoked skills and bounded model dispatch.
- Same-origin/token checks and exclusion of engineering context from the frontier route.
- Knowledge approval, source/revision retrieval, retirement, persisted retrieval history and local-only context delivery.
- Replay after original input removal, current-input failure, lineage and fresh agent review.
- Evidence generation before/after review, content hashes, invalid paths and tamper detection.
- Study parameter limits, stale approvals, cancellation, plugin revocation, restart recovery, reference checks and time-budget stopping.

These tests exercise a fixed synthetic reference domain. They are not qualification of arbitrary engineering methods, third-party plugins, or adversarial generated code.

## Earlier live integration validation

Version 0.2 was tested with a local Qwen2.5-Coder 7B model through Ollama and a pinned Python 3.12 Linux Docker image. A reviewed generated moving-average script produced 101 samples matching an independent reference to 1e-10. Retained Docker receipts identify image, script, exit status and cleanup. These were focused model integration checks, not a broad model-quality benchmark.

Expected fixture comparison: RMSE approximately 0.01327444 a.u.; maximum absolute difference approximately 0.02265 a.u.; 101 aligned pairs. No acceptance tolerance is defined.

## Scope and limitations

Windows runtime validation, mounted network-share behavior, cloud document providers, multiple users, SSO/RBAC, arbitrary analyses and live frontier-provider access remain unverified or unimplemented. Model summaries can be wrong; reviewed notes do not fine-tune the model. Historical replay uses current method/runtime versions. Parameter studies use released code in the service and check a cooperative deadline between trials; they are not autonomous code research.

Stop the service and back up the local data directory before upgrades. Version 0.3 adds SQLite tables/columns without deleting existing jobs or notes. Restore requires the database, checkpoint database and associated artifacts together; automatic backup/retention scheduling is not implemented.

## Version 0.3 browser verification

A separate synthetic workspace was exercised through the browser: starter-agent creation, conversation, plan approval, C++ comparison, report acceptance, study proposal, bounded execution, independent-reference results and study acceptance. Knowledge proposal, source display, approval, keyword search and conversation reference display were also checked. JavaScript syntax checks passed for all three application scripts. This browser pass used demo-mode routing; new live-model quality has not been benchmarked.

## Offline hardening checks

Additional tests reject public/link-local model IPs, DNS names, URL credentials and query strings, unapproved private IPs, remote Docker hosts, input symlinks and unapproved external artifact roots. The general-reasoning endpoint and direct frontier model calls are blocked even when configured. These are application-policy tests, not a penetration test, jailbreak-proof guarantee, OS firewall audit, or verification of a local model server's own outbound behavior.

A fresh live Docker execution was attempted during offline hardening but could not run because the local Docker daemon socket was absent. The new local-socket selection is covered by policy tests; live Windows/container revalidation remains required.

## Version 0.4 scheduling verification

Tests cover explicit recipe approval, stale approvals, agent/skill/method revocation, queued-job permission rechecks, once/daily/weekly timing, daylight-saving gaps and folds, timezone package fallback without system timezone files, overlap prevention, missed occurrences, pause/resume/cancel, restart recovery, duplicate prevention, and transactional rollback when enqueue fails.

A real once-only schedule was created and approved through the browser in an isolated synthetic workspace. It dispatched at its scheduled time without a second plan prompt, exported both inputs through the C++ gateway, produced 101 validated comparison samples, and stopped for report review. The report was then accepted. This pass used the released deterministic recipe, without a model or Docker. Unchanged startup was separately verified to preserve the compiled executable's timestamp and hash.

Scheduling requires one running service process. There is no OS wake-up, automatic whole-job retry, or distributed scheduler. Windows execution remains to be validated; timezone fallback is covered by automated tests. Version 0.4 adds scheduling tables and requires the pinned tzdata dependency to be provisioned before offline startup.

## Chart revision follow-up

Request changes opens an inline revision prompt and retains report review. Conversation requests to add axis lines use a bounded, event-persisted display action; tests verify unchanged numerical results, unchanged review fingerprints and status, and no artifact claim without a result. Other chat replies are explicitly labelled as discussion without created artifacts. Axis formatting applies to the main comparison plot in the Workbench, not exported evidence or arbitrary generated charts. JavaScript syntax checks passed; target Windows browser validation remains pending.

## Dynamic Python validation

The runtime task flow replaces the earlier hardcoded axis-line shortcut. Tests cover draft-only behavior, syntax rejection, input retention across revisions, stale approvals, permission revocation, cross-conversation denial, execution failure, duplicate execution prevention, and user-supplied calculations without a preceding result. Tool registrations do not read their referenced paths.

A local Qwen2.5-Coder 7B generated a statistics-and-plot script against synthetic data. After script inspection, browser approval executed it in the pinned Docker image and displayed JSON and PNG outputs. A follow-up generated a separate script revision with dotted mean lines, which also ran in Docker. Both versions matched independent mean and population-standard-deviation calculations to 1e-12. The model initially produced invalid syntax and later imprecise unit labels; syntax checks and human output review remain necessary. This is a focused integration test, not broad qualification of generated scientific code. Windows runtime validation remains pending.
