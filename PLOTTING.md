# Dynamic Python tasks

Conversations can draft Python for calculations, JSON tables and PNG plots using the selected numerical analysis snapshot. Existing released comparisons remain available; other runtime tasks use generated code. A local model is required. There is no fixed list of supported chart edits. The model's ability and installed numerical libraries limit what it can produce correctly.

## Provision the worker

On an approved provisioning machine with Docker in Linux-container mode:

```powershell
docker build -f docker/Dockerfile.python-tasks -t ewb-python-tasks:local .
docker image inspect --format '{{.Id}}' ewb-python-tasks:local | Set-Content data/python-task-image.txt
```

Restart the service. The launcher reads the pinned local image ID from that file, or use EWB_PLOT_IMAGE. Building may download dependencies; runtime never pulls images or installs packages. Offline deployments should transfer the vetted image through approved internal distribution. The Dockerfile pins direct dependencies; transitive dependencies are resolved at build time. Record and deploy the resulting image ID.

## Workflow

1. Open a numerical result in a conversation using an agent with reviewed Python permission.
2. Request a calculation or plot. The local model drafts a complete script using an immutable copy of the analysis JSON.
3. Inspect the actual Python script, input scope and image. Approve and run in Docker, or reject.
4. Inspect the output JSON and optional PNG. Successful execution is not scientific validation; accept the output only after reviewing the method and results.
5. With the task selected, send a follow-up. A new version retains the original data snapshot and receives the parent script and available outputs as context. It requires fresh approval. Previous versions remain accessible below the conversation.

A failed or interrupted execution can be explicitly retried with the same approved artifact or revised into a new proposal. No automatic retries or automatic code approvals occur. A clarification job does not erase earlier numerical results: drafting falls back to the latest result within that conversation. Selecting a parent artifact fixes its input snapshot.

## Runtime contract and limits

Generated Python reads `/inputs/data.json` and writes `/outputs/result.json` (a finite JSON object, up to 1 MB). Plot-only scripts may omit result.json; the Workbench then labels the output as plot-only without inventing numerical results. A plot is optional at `/outputs/plot.png`, at most 4 MB and 2000 by 1600 pixels. Tables can be arrays of objects in the JSON output. Only these outputs are displayed; HTML, arbitrary scripts, SVG and file links are not executed in the browser.

Docker runs a pinned local image, no network, non-root, read-only root filesystem and inputs, dropped capabilities, 512 MB memory, one CPU, process limits, and a 60-second timeout. It receives no Docker socket or application credentials. The writable output directory belongs to this task. Additional disk quotas and stronger sandbox isolation remain production deployment work. Input/output checks do not establish numerical correctness or guarantee protection against vulnerabilities in the container runtime or image libraries.

Receipts retain image, script and output hashes and execution times in local task storage. Python task tables, files and proposal versions must be included in workspace backups. Original comparison evidence exports do not bundle these newer task artifacts. The tasks are separate persisted records, not new LangGraph nodes, and are not eligible for unattended scheduling.

## Tools and source references

The Tools page registers an application/module location and optional source-folder reference. These are metadata, not executable tools or file access grants. The bundled adapter remains the only released application integration. Source-folder indexing, executable adapter onboarding and arbitrary installed-application discovery are not implemented. Additional integrations must preserve the administrator-approved file and network boundaries.

## Interactive 3D results

Describe geometry, dimensions and units in a conversation using an agent with
reviewed Python enabled. Python returns a `scene3d` field in `result.json`, after
exact-script approval and isolated Docker execution. The analysis panel renders
that scene interactively using locally bundled Three.js 0.180.0. Follow-up requests
create new reviewed script versions. The **Tools** page contains an expandable
sample; 3D is a result type, not a separate workflow or top-level navigation item.

The bounded schema supports boxes, spheres, cylinders, polylines, and indexed
triangle meshes. It rejects unknown fields, external assets, scripts, invalid
indices and nonfinite coordinates. Limits: 100 objects, 5,000 total mesh/line
vertices, 10,000 triangles, and the existing 1 MiB JSON output limit. Browser GPU
support is required. Rotation, zoom, pan, reset and PNG export are available.
Animation, CAD solids, manufacturing tolerances, external model import, and
physics solvers are not provided. Engineering correctness remains subject to
review; successful rendering is not physical validation. Model drafting can fail.

The schema is defined in `backend/scenes.py`. Three.js and OrbitControls are
vendored with the upstream MIT license and package integrity metadata in
`frontend/vendor/three/`. OrbitControls' import is changed to a local module.
No npm installation or CDN access is required at runtime.
