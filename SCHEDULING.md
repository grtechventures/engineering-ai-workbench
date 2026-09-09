# Scheduling released workflows

The local service includes a persistent, single-process scheduler. It does not require cron, GitHub, cloud services or internet access. Only released comparison recipes without generated Python can be scheduled in this release.

## Create and approve

Start from an accepted baseline comparison. Select an enabled agent, a released comparison skill assigned to that agent, a future local start date/time, an IANA timezone, and Once, Daily or Weekly. Weekly repeats on the start date's weekday; Daily/Weekly retain that local clock time.

Saving creates a proposal. Approval covers timing, the agent revision, skill/version, current input scope, source-code/executable hashes and configured storage roots. It grants permission to run that fixed released recipe unattended. Each occurrence reads the current two configured binary fixtures through the C++ gateway. Model re-planning is bypassed; result acceptance is not. Generated-code workflows are rejected rather than receiving blanket script approval.

Permission checks run at dispatch and again at export, preparation and calculation. Agent, skill, method code or storage changes put future dispatch into needs_review. Cancel the old schedule and create/approve a replacement. A disabled plugin or revoked skill also blocks dispatch. Local single-user approval is not independent enterprise authorization.

## Clock semantics

- Starts have minute precision and an explicit IANA timezone; UTC is the default UI timezone.
- The service checks for work about once per second. Dispatch up to 60 seconds after due time is allowed to absorb normal clock/tick latency.
- An occurrence older than that grace period is recorded as missed and skipped. Extended downtime is summarized by a missed record, not expanded into hundreds of historical jobs. No catch-up burst runs.
- Spring-forward local times that do not exist are skipped for recurring schedules. A first start in that gap is rejected. Fall-back repeated times use the first occurrence only.
- Changing timezone rules may change future calendar calculations; provision reviewed tzdata updates and recheck schedules after such changes.

## Overlap, limits and failures

Only one nonterminal analysis per schedule is permitted. Running, queued, blocked, interrupted and review-pending jobs all prevent another occurrence. Accept, reject or cancel the prior job to clear it. Skipped overlaps appear in history. Up to 100 proposed/active/paused schedules are supported; the application still uses one calculation worker.

A run is limited to the fixed released comparison, two fixed C++ exports with ten-second per-export timeouts, and bounded synthetic input size. No model or Docker job is invoked. There are zero automatic whole-job retries: numerical, permission and integration failures remain visible for inspection and manual resume. The service does not classify failures well enough to safely select transient retry cases yet.

Occurrence reservation, initial job state and advancing next_due are committed in one local SQLite transaction. A unique schedule/occurrence key prevents duplicate dispatch. If the process stops after queuing a job, restart marks that job interrupted. Resume it through Job history; the scheduler will not create a duplicate. This does not provide distributed exactly-once execution or support multiple service processes.

## Pause, cancel and shutdown

Pause stops future dispatch and lets an already-dispatched job proceed. Resume checks the original approval and skips overdue occurrences. Cancel prevents future work and rejects an already-dispatched job at its next scheduled-authority check; it cannot undo completed calculations or interrupt an in-progress C++ process. Individual job controls remain available.

Once-only schedules become complete after their occurrence is dispatched or skipped. Complete describes the schedule, not acceptance of its result. Inspect the linked job for execution/review status. Schedule definitions and review events persist; the UI shows the latest 50 occurrence records without deleting older records.

The scheduler starts/stops with FastAPI's service lifecycle. No Windows Task Scheduler entry, autostart service, wake timer, email or external notification is installed. The Schedules page refreshes while open. Operating-system startup and multi-user service management are separate deployment work.

Setup caches the C++ build using a hash of its source and build script, avoiding needless recompilation and schedule invalidation on an ordinary restart. Genuine changes to approved code/executable hashes still require a replacement schedule.
