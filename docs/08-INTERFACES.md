# 08-INTERFACES.md

## Overview

Ultra Stack exposes five primary user interfaces designed for different operational contexts: web-based command and control, conversational operations, terminal-native workflows, observability dashboards, and metrics visualization. Together, these interfaces provide overlapping access patterns so operators can choose the most effective tool for each task without losing consistency in behavior, state, or control boundaries.

The five interfaces are:

1. **PWA Command Center (Next.js 16)** on port **3100**
2. **Telegram Bot** `@Ultra_Erik_Bot` with inline button workflows
3. **Global CLI** command `ultra`
4. **Streamlit Dashboard** on port **8501**
5. **Grafana** on port **3000**

This document defines architecture, access patterns, usage flows, and operational recommendations for each interface.

---

## Interface Topology

### Unified Control Plane

All interfaces connect to the same Ultra Stack runtime and are expected to operate against the same canonical state:

- Agent state and mode selection (FREE, NORMAL, KIMI, BOOST, TURBO, BLACKBOX, CODE)
- Approval queues and human-in-the-loop checkpoints
- Service health status and self-healing telemetry
- Tool invocation outcomes and execution traces
- Persistent logs and metrics feeds

### Interface Responsibility Model

Each interface is optimized for specific operational goals:

- **PWA Command Center**: primary control surface for day-to-day operations.
- **Telegram Bot**: remote, low-latency operational control from mobile chat.
- **CLI**: scripting, automation, and power-user workflows.
- **Streamlit Dashboard**: system-level status review and guided diagnostics.
- **Grafana**: deep metrics analysis, alerting, and trend inspection.

---

## 1) PWA Command Center (Next.js 16, Port 3100)

### Purpose

The PWA Command Center is the main operator interface. It combines chat-driven control, approvals, and system introspection in a web app installable as a Progressive Web App (PWA). It is designed for both desktop and mobile browsers, with responsive behavior for operational continuity.

### Access

Default URL:

- `http://<host>:3100`

Local development/common setup:

- `http://localhost:3100`

If deployed behind reverse proxy, ensure forwarding for WebSocket/SSE channels used by live updates.

### Core Views

The Command Center contains four primary views:

1. **Home**
2. **Chat**
3. **Approvals**
4. **System**

#### Home View

The Home view is a high-level operational summary. It should be used at session start to validate platform status before sending complex commands.

Typical widgets:

- Service status aggregate (healthy/degraded/down)
- Current active LLM mode
- Pending approvals count
- Recent events (healing actions, escalations, failures)
- Quick actions (switch mode, open chat, inspect approvals)

Recommended workflow:

1. Open Home.
2. Confirm core services are healthy.
3. Verify active mode aligns with workload.
4. Check whether approvals are blocked.
5. Continue to Chat or System as needed.

#### Chat View

The Chat view is the primary human-agent interaction channel. It supports natural language control of Ultra Stack and can invoke Smart Agent tools indirectly through interpreted instructions.

Supported interaction patterns:

- Intent execution (“deploy diagnostics on service X”)
- Investigation (“why did healer restart Y?”)
- Coordination (“summarize incidents in last 2 hours”)
- Mode-sensitive tasks (e.g., CODE mode for coding-oriented output)

Operational best practices:

- Keep prompts explicit about scope and target service.
- Include timeframe for logs/diagnostics requests.
- Confirm high-impact actions through approval flow where configured.
- Use mode selection intentionally (e.g., TURBO for speed, CODE for technical detail).

#### Approvals View

The Approvals view provides human-in-the-loop governance for controlled actions. Actions requiring approval are queued and displayed with context.

Each approval item should include:

- Request origin (agent/tool/interface)
- Requested action
- Target resources
- Risk metadata (if available)
- Timestamp and timeout window

Operator actions:

- Approve
- Reject
- Inspect details/logs/context chain

Usage guidance:

- Approve only after validating intent and target.
- Reject ambiguous or stale requests.
- Use comments/reason fields if available to improve Learner/Improver feedback loops.
- Monitor queue depth to avoid operational deadlocks.

#### System View

System is the technical status panel for services, runtime, and coordination loops (Monitor/Healer/Learner/Improver).

Common capabilities:

- Service health per systemd unit
- Container status snapshots
- Event stream and recent corrective actions
- Runtime metadata (uptime, last restart, error counts)
- Self-healing loop visibility

Use this view when:

- Chat responses suggest instability.
- Approvals accumulate unexpectedly.
- Telegram/CLI report inconsistent state.
- Preparing for maintenance windows.

### PWA Operational Notes

- Designed for installability as PWA for app-like mobile behavior.
- If offline behavior is enabled, treat cached data as potentially stale until sync completes.
- Browser session authentication should follow deployment security policy.
- For production, terminate TLS at ingress/proxy and enforce secure cookies.

### Typical PWA Session

1. Enter Home and validate stack health.
2. Switch to Chat for active task execution.
3. Open Approvals for any blocked actions.
4. Verify outcomes in System.
5. Return to Home for overall green-state confirmation.

---

## 2) Telegram Bot (`@Ultra_Erik_Bot`)

### Purpose

The Telegram bot enables remote operation with minimal latency and low interface overhead. It is ideal for quick checks, acknowledgements, and lightweight control when operators are away from desktop environments.

### Access

Bot handle:

- `@Ultra_Erik_Bot`

Prerequisites:

- Authorized Telegram account (depending on bot access control policy)
- Network connectivity from bot host to Ultra backend APIs
- Webhook or long polling process active in runtime

### Interaction Model

The bot supports command and button-driven interactions with **inline keyboard buttons** for structured actions.

Common patterns:

- Request status snapshot
- Trigger safe pre-defined operations
- Review and respond to approvals
- Navigate context-specific options via buttons

Inline buttons reduce ambiguity by constraining possible actions and can encode contextual payloads (e.g., approval ID, service name, action type).

### Recommended Command Classes

Depending on implementation, bot flows typically include:

- **Status**: health summaries, service states, mode
- **Approvals**: list pending and act on selected item
- **Control**: start/stop/restart selected service (if authorized)
- **Mode**: switch LLM mode quickly
- **Diagnostics**: recent errors, last healing action, queue depth

### Approval Handling in Telegram

Approval workflows through Telegram should include safeguards:

- Show complete action summary before buttons appear.
- Include “Approve” and “Reject” inline buttons with unique request context.
- Confirm final action in follow-up message.
- Prevent double-processing by invalidating buttons after decision.

### Operational Best Practices

- Use Telegram for fast triage, not full forensic analysis.
- Escalate to PWA System view or Grafana for deep diagnostics.
- Avoid high-risk multi-step operations from chat-only context unless policy allows.
- Ensure notifications are not muted for critical alerts.

### Security Considerations

- Restrict bot access to approved user IDs/chats.
- Validate callback query payload integrity.
- Rate-limit sensitive operations.
- Log every decision event (especially approvals).
- Avoid exposing secrets in chat responses.

### Example Remote Workflow

1. Receive alert notification in Telegram.
2. Open inline status action.
3. Check pending approvals and resolve urgent item.
4. Trigger diagnostic summary.
5. Escalate to PWA or CLI for follow-up remediation.

---

## 3) Global CLI (`ultra`)

### Purpose

The `ultra` CLI is the automation-first interface. It is intended for operators, SRE workflows, shell scripting, CI/CD hooks, and reproducible incident procedures.

### Access

Command:

- `ultra`

Verify installation:

- `ultra --help`
- `ultra version` (if implemented)

CLI should be available globally in `$PATH`.

### Why Use CLI

- Scriptable and deterministic
- Fast interaction for experienced operators
- Easy integration with Unix tools (`grep`, `jq`, `xargs`)
- Suitable for cron jobs and runbooks
- Supports non-interactive operational pipelines

### Common Capability Areas

Typical CLI command domains include:

- Stack/service status inspection
- Mode management (set/get mode)
- Approval queue interactions
- Agent prompt submission
- Self-healing subsystem controls
- Logs/events retrieval

### Usage Style

Two broad usage modes are expected:

1. **Interactive**: human at terminal, quick commands and checks.
2. **Non-interactive**: scripts invoking `ultra` with structured output.

For automation, prefer machine-readable output options if provided (JSON/YAML).

### Example Operational Flows

#### Health Check Loop

- Poll status periodically.
- Detect degraded units.
- Trigger report generation.
- Notify via external channel.

#### Approval Automation Guardrail

- Pull pending approvals.
- Apply policy-based filtering.
- Route only compliant items for auto-approval (if policy permits).
- Escalate unresolved high-risk items to humans.

#### Mode Switching for Task Classes

- Set CODE mode before generation-heavy technical workflows.
- Revert to NORMAL/FREE for routine conversational operations.
- Reserve TURBO/BLACKBOX for specific latency/performance requirements.

### CLI Best Practices

- Always inspect target before restart or destructive action.
- Use explicit flags over implicit defaults in scripts.
- Capture command output and exit codes.
- Build idempotent scripts to reduce failure amplification.
- Version-lock critical automation if command surface changes over time.

### Production Safety

- Use least-privilege execution context.
- Separate read-only and write-capable workflows.
- Audit command history for high-impact actions.
- Add confirmation flags for destructive commands in manual sessions.

---

## 4) Streamlit Dashboard (Port 8501)

### Purpose

The Streamlit Dashboard provides a guided operational UI focused on visibility and decision support. It is particularly useful for quick diagnosis, non-terminal users, and compact cross-section views of service state.

### Access

Default URL:

- `http://<host>:8501`
- Local: `http://localhost:8501`

### Functional Focus

Compared to the PWA, Streamlit typically emphasizes visualization and inspection over command orchestration. It is often used as a “status wall” or operator side panel.

Common panel types:

- Service table with health markers
- Event timeline
- Error/restart counters
- Current mode and agent activity summary
- Self-healing action logs

### When to Use Streamlit

Use Streamlit when you need:

- Quick visual status without entering full command workflow
- A secondary operational screen during incidents
- A concise summary for handoff discussions
- Lightweight exploration before deep dive in Grafana

### Workflow Pattern

1. Open dashboard during startup checks.
2. Identify anomalies in service or healing indicators.
3. Cross-check affected components in PWA System view.
4. Move to Grafana for metric-level root cause if needed.
5. Execute remediations via CLI/PWA/Telegram per policy.

### Operational Notes

- Streamlit refresh behavior depends on app configuration; confirm update interval.
- For production use behind reverse proxy, configure base path and headers correctly.
- Protect dashboard exposure in public networks (auth + network ACLs).
- Use it as a visualization surface; keep control actions in audited channels if required.

---

## 5) Grafana (Port 3000)

### Purpose

Grafana is the primary metrics observability interface. In Ultra Stack, it complements operational interfaces by providing time-series analysis, dashboards, and alerting integrations based on Prometheus data.

### Access

Default URL:

- `http://<host>:3000`
- Local: `http://localhost:3000`

Data source integration is typically Prometheus (containerized in stack topology).

### Core Use Cases

- Service performance trends
- Resource usage (CPU, memory, disk, network)
- Error and restart correlation
- SLA/SLO tracking
- Alert inspection and tuning

### Dashboard Strategy

Recommended dashboard layers:

1. **Executive Health Dashboard**  
   High-level KPIs and fleet status.

2. **Runtime Services Dashboard**  
   systemd units + container metrics with per-service drill-down.

3. **Self-Healing Dashboard**  
   Monitor/Healer/Learner/Improver cycles, action counts, success/failure ratios.

4. **Interface Activity Dashboard**  
   Request volumes and error rates by PWA/Telegram/CLI entrypoints (if instrumented).

### Incident Investigation Flow in Grafana

1. Select incident time window.
2. Identify first anomalous metric deviation.
3. Correlate with service restarts/healing actions.
4. Check saturation signals (CPU/memory/IO/network).
5. Validate post-remediation recovery slope.
6. Export/share panel links for incident report.

### Alerting Considerations

- Define alerts for both hard failures and degradation trends.
- Include cooldown and deduplication policies to reduce noise.
- Route critical alerts to Telegram/on-call channels.
- Review false positives weekly and tune thresholds.

### Security and Operations

- Enforce authentication and role-based access.
- Restrict admin credentials and rotate secrets.
- Use HTTPS in production.
- Back up dashboards and provisioning configs.
- Track config changes in version control.

---

## Cross-Interface Usage Matrix

## Choosing the Right Interface

### Fast Decision Guide

- Need full control + approvals + chat context: **PWA**
- Mobile quick action or alert response: **Telegram**
- Automation or scripting: **CLI**
- Visual quick health snapshot: **Streamlit**
- Deep metrics and trend analysis: **Grafana**

### Complementary Usage Pattern

A mature operational flow usually combines interfaces:

1. **Alert received** via Telegram/Grafana
2. **Health validated** in Streamlit/PWA Home
3. **Root cause explored** in Grafana + PWA System
4. **Action executed** via CLI or PWA Approvals
5. **Post-fix confirmation** across Home + Grafana trends

---

## Operational Playbooks by Interface

### Daily Operations

- Start with **PWA Home** or **Streamlit** for morning health check.
- Use **CLI** for routine scripted validations.
- Keep **Telegram** available for asynchronous interventions.
- Review **Grafana** trend dashboards at least once per shift.

### Incident Response

- Acknowledge alert in **Telegram**.
- Open **Grafana** for signal timeline.
- Validate component state in **PWA System**.
- Execute remediation in **CLI** or through approved **PWA** action.
- Resolve queued risks in **Approvals**.
- Confirm stabilization in **Grafana** and **Home**.

### Change Windows

- Pre-check baseline metrics in **Grafana**.
- Validate zero pending approvals/conflicts in **PWA**.
- Run scripted actions via **CLI** for repeatability.
- Monitor live status in **Streamlit** during rollout.
- Keep **Telegram** open for instant rollback triggers.

---

## Reliability and Consistency Guidelines

### State Consistency

Because all interfaces point to shared backend state, operators should avoid conflicting simultaneous actions. Recommended controls:

- Prefer one “active controller” per incident.
- Use approval locks where possible.
- Confirm action completion before issuing new high-impact commands.
- Rely on timestamps and request IDs for reconciliation.

### Auditability

For production operations, ensure every interface contributes to centralized audit trails:

- Who triggered action
- From which interface
- Which resource changed
- Whether approval was required/granted
- Result and error context

Audit logs should be immutable and exportable for post-incident analysis.

### Failure Modes

Common cross-interface failure patterns:

- UI reachable but backend API degraded
- Telegram responsive but approval callbacks failing
- CLI command success with delayed state propagation
- Grafana data lag due to metrics pipeline disruption

Mitigation:

- Cross-check at least two interfaces before concluding system state.
- Use direct service health probes from CLI when UI inconsistencies occur.
- Validate metrics ingestion path if dashboards flatten unexpectedly.

---

## Access, Networking, and Ports

Default exposed ports in this interface layer:

- **3100**: PWA Command Center (Next.js 16)
- **8501**: Streamlit Dashboard
- **3000**: Grafana

Telegram Bot is externally accessed through Telegram network; locally it depends on bot runtime process and backend API connectivity.

Recommendations:

- Place interfaces behind reverse proxy in production.
- Enforce TLS termination and secure headers.
- Restrict network exposure by role and environment.
- Apply firewall rules and IP allowlists where feasible.

---

## Practical “How To Use” Summary

### PWA (3100)

1. Open `/` and review Home.
2. Use Chat for directed tasks.
3. Approve/reject pending operations in Approvals.
4. Validate low-level runtime condition in System.

### Telegram Bot (`@Ultra_Erik_Bot`)

1. Open chat with bot.
2. Use inline buttons for status/approvals/control.
3. Confirm decisions from callback responses.
4. Escalate complex diagnostics to PWA/CLI/Grafana.

### CLI (`ultra`)

1. Run `ultra --help` to inspect command surface.
2. Execute status/operation commands explicitly.
3. Use structured output for scripts.
4. Capture exit codes and logs for automation safety.

### Streamlit (8501)

1. Open dashboard.
2. Inspect service and event panels.
3. Detect anomalies quickly.
4. Use as visual companion during incidents and rollouts.

### Grafana (3000)

1. Open metrics dashboards.
2. Select relevant time range and services.
3. Correlate symptoms with resource and error signals.
4. Validate remediation impact over time.

---

## Final Recommendations

- Treat **PWA** as the primary operator console.
- Keep **Telegram** for immediate remote response.
- Standardize critical procedures in **CLI** scripts.
- Use **Streamlit** for at-a-glance monitoring.
- Use **Grafana** for evidence-based diagnosis and continuous reliability improvement.

When used together, these five interfaces form a robust, redundant operational surface for Ultra Stack, enabling fast control, transparent governance, and measurable system reliability across development and production environments.