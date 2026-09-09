# Prototype release

This release is for evaluation and adaptation. It is a single-user local application, not a production multi-user enterprise service. It is provided AS IS under Apache 2.0; license warranty and liability provisions are subject to applicable law.

## Known limitations

- Generated Python can fail or produce incorrect calculations, units and geometry. Syntax/schema checks and human approval do not prove correctness. The local-model pipe-generation example remains unreliable and was not accepted as a working engineering result.
- Three.js renders valid bounded static scenes; it is not a CAD, meshing or simulation solver. No animated fluid physics is implemented.
- 132 automated checks passed on the development environment. A synthetic scene rendered after Docker execution, and a live worker failure returned its Python diagnostic. These checks do not establish general model reliability. Windows runtime validation remains pending.
- MATLAB and Channels are configuration/preview only. Live MATLAB, Teams and Slack execution/messaging are not connected. Tools registration does not install adapters; most database readers remain integration work. MCP is planned, not implemented.
- Security controls are prototype controls, not certification or a jailbreak-proof guarantee. Keep the service on loopback. Do not expose it as a shared service without authentication, authorization and deployment hardening. Validate analyses independently before engineering use.

## Distribution

Use GitHub's Code → Download ZIP, or clone the repository. Local runtime data, uploaded files, conversations and credentials are not part of the source distribution. Provision dependencies separately using the README and PLOTTING guide. See LICENSE, NOTICE and THIRD_PARTY_NOTICES.md before redistributing.
