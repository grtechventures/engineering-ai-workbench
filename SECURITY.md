# Security boundary and offline deployment

This single-user prototype provides application-level restrictions. It is not certified, penetration-tested, or guaranteed immune to jailbreaks, prompt injection, sandbox vulnerabilities or malicious local administrators.

## Model output cannot grant authority

The model can choose only bounded server-defined actions. It cannot install tools, select arbitrary filesystem paths, change network configuration, grant permissions, remove review gates, or run generated code on the host. Source and notes are reference content. An accepted model plan is still checked against current agent permissions. Exact generated code, input snapshots and worker image require review.

## Network enforcement in the application

- All frontier inference is disabled in both the HTTP API and the model gateway, even if old frontier environment variables are present.
- Model URLs accept literal loopback IPs. localhost is rewritten to 127.0.0.1 to avoid name resolution.
- LAN models require an exact private literal IP in EWB_APPROVED_MODEL_IPS and EWB_APPROVED_ONPREM=1. No user/model prompt can set these variables.
- Public/link-local model destinations, DNS names, embedded credentials, queries, fragments, redirects and environment HTTP proxies are rejected.
- Generated Python runs in a pinned local Docker image with no network, read-only inputs, no Docker socket, no credentials supplied by the application, dropped capabilities and resource limits. Images must be reviewed: a locally available image is not inherently trustworthy.
- The worker validates the configured Docker endpoint and explicitly pins a local Unix socket or local Windows named pipe. TCP/SSH/remote named-pipe endpoints are refused. Images are never pulled during analysis.

## Files and LAN storage

The runtime does not expose an arbitrary file browser/read tool to the model. The C++ adapter reads two fixed workspace fixtures; input symlinks and paths escaping the workspace are rejected. Generated code sees only its mounted input snapshot, script and job output directory, plus its container image filesystem.

Evidence outside the state directory requires an exact EWB_APPROVED_FILE_ROOTS entry, configured by an administrator before startup. A configured share grants access only through the fixed evidence writer, not unrestricted model browsing. The artifact reader validates identifiers and content hashes. Changes to root configuration require a service restart.

UNC paths are refused for database state. The application cannot reliably identify every mapped drive, mounted filesystem or synchronized folder. Administrators must keep state local and enforce OS filesystem permissions. Local users able to replace executables, modify databases or alter environment variables are outside this prototype's trust boundary. Symlink checks are not a defense against a hostile local user racing filesystem operations.

## Required for an enforced offline installation

Use a dedicated restricted OS account and filesystem ACLs. Apply default-deny outbound firewall rules to the Workbench service, model server and container/VM networking, allowing only necessary loopback and specifically approved LAN endpoints. Deny general access to LAN shares under that account. Validate the rules on the target Windows host.

A loopback HTTP endpoint can proxy requests elsewhere. Some model services may offer cloud-backed models. The Workbench cannot verify that a service behind an approved address keeps processing local. Disable cloud models, web tools, remote integrations and automatic update/download activity in the model service, and enforce egress externally.

Installation is separate from runtime: dependency installation, model downloads and image downloads can require internet access. For an offline environment, stage vetted dependencies, model weights and images through an approved internal channel. The Workbench launchers do not install missing Python dependencies. They stop with a provisioning message instead. Provision the environment in advance using approved offline wheels.

Do not expose this service on a network interface. Authentication, multi-user project authorization, protected audit storage, retention/deletion controls and independent release review remain deployment work. Server-configured allowlists are not organizational approval workflows.

## Scheduled authority

Only explicitly approved released comparisons can execute on a timer. Timing, current fixed-input scope, agent/skill revision, code hashes and storage roots are captured at approval. The scheduler rechecks this authority at dispatch and execution; it does not grant new model tools or network access. Generated-code skills are rejected. Scheduled results still require review. The scheduler is single-process and local; it is not a multi-user approval or distributed execution system.
