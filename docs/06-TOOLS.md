# 06-TOOLS.md

## Smart Agent Tools Reference

This document defines the 13 operational tools exposed to the Smart Agent in Ultra Stack.  
These tools provide controlled access to filesystem, process execution, system services, Docker, package management, Python runtime, logs, and external web search.

The objective is to maximize autonomous capability while preserving safety boundaries, traceability, and recoverability in production environments.

---

## Scope and Operating Model

The Smart Agent uses tools as explicit function calls, not free-form shell authority.  
Each tool has:

- A defined **intent**
- A strict **parameter contract**
- Expected **output semantics**
- A **risk level**
- **Security notes** and guardrails

Tools are designed to work in conjunction with Ultra Stack self-healing components (Monitor, Healer, Learner, Improver), systemd services, and Docker runtime.

---

## Risk Level Legend

- **Low**: Read-only operations, limited side effects.
- **Medium**: Potentially disruptive if abused or mis-scoped.
- **High**: Can alter runtime state, install software, or execute arbitrary logic.
- **Critical**: Capable of broad system impact; requires highest controls and auditing.

---

## General Security Principles

1. **Least privilege**  
   Run the agent with the minimal filesystem, service, and container permissions required.

2. **Path and target validation**  
   Reject unsafe paths (`/`, `/etc`, `/var/lib`, secrets directories) unless explicitly whitelisted.

3. **Command and argument sanitization**  
   Avoid shell interpolation where possible. Prefer argument arrays and strict allowlists.

4. **Timeouts and resource limits**  
   All execution tools should enforce max runtime, output caps, memory/CPU safeguards.

5. **Audit trail**  
   Every tool call should be logged with timestamp, caller, parameters, result code, and truncated output.

6. **Idempotent-first behavior**  
   Favor checks (`status`, `list`, `read`) before mutation (`write`, `restart`, `install`).

7. **Human override readiness**  
   Destructive or persistent operations should be reviewable and reversible.

---

## Tool: `read_file`

### Description

Reads the content of a file from the local filesystem for diagnostics, configuration inspection, or code analysis.  
Intended as a read-only primitive and commonly used before applying `write_file` modifications.

### Parameters

- `path` (string, required): Absolute or workspace-relative path to the target file.
- `encoding` (string, optional, default: `utf-8`): Text encoding.
- `max_bytes` (integer, optional, default: implementation-defined): Output cap to avoid oversized payloads.

### Example Usage

- Read service configuration:
  - `path: /etc/systemd/system/ultra-monitor.service`
- Inspect application source:
  - `path: /opt/ultra-stack/apps/pwa/next.config.js`
- Retrieve recent log snapshot written to file:
  - `path: /var/log/ultra/agent.log`, `max_bytes: 20000`

### Risk Level

**Low**

### Security Notes

- Enforce path allowlists.
- Prevent access to secrets (`.env`, private keys, token stores) unless explicitly authorized.
- Truncate binary or oversized files safely.
- Normalize path to avoid traversal (`../`) bypass.

---

## Tool: `write_file`

### Description

Creates or overwrites file content. Used for patching configs, generating scripts, updating templates, or persisting agent outputs.

### Parameters

- `path` (string, required): Destination file path.
- `content` (string, required): Full content to write.
- `encoding` (string, optional, default: `utf-8`)
- `append` (boolean, optional, default: `false`): Append instead of overwrite.
- `create_dirs` (boolean, optional, default: `false`): Auto-create parent directories.

### Example Usage

- Patch a systemd override:
  - `path: /etc/systemd/system/ultra-healer.service.d/override.conf`
  - `content: [Service] ...`
- Update app runtime flag:
  - `path: /opt/ultra-stack/.runtime/mode`
  - `content: TURBO`
- Append diagnostics:
  - `path: /var/log/ultra/self-heal-actions.log`, `append: true`

### Risk Level

**High**

### Security Notes

- Require backup-before-write for critical files (`.bak` or versioned copy).
- Restrict writable roots to approved directories.
- Validate content for malformed unit files or unsafe shell payloads before deployment.
- Avoid writing secrets in world-readable locations.
- Prefer atomic write pattern (temp file + rename) to prevent partial corruption.

---

## Tool: `list_dir`

### Description

Lists directory entries for discovery of project layout, logs, artifacts, and configuration surfaces.

### Parameters

- `path` (string, required): Directory path.
- `recursive` (boolean, optional, default: `false`)
- `max_depth` (integer, optional): Limits recursion depth.
- `include_hidden` (boolean, optional, default: `false`)
- `pattern` (string, optional): Glob or substring filter.

### Example Usage

- Enumerate Ultra Stack root:
  - `path: /opt/ultra-stack`
- Find service unit definitions:
  - `path: /etc/systemd/system`, `pattern: ultra-*`
- Scan logs directory recursively:
  - `path: /var/log/ultra`, `recursive: true`, `max_depth: 2`

### Risk Level

**Low**

### Security Notes

- Avoid deep unbounded recursion on large filesystems.
- Apply entry count limits to prevent memory spikes.
- Respect denylisted paths (container runtime internals, sensitive system dirs).
- Return metadata only when feasible; avoid unnecessary file content reads.

---

## Tool: `search_files`

### Description

Searches files by name and/or content. Useful for locating config keys, error signatures, TODO markers, imports, and operational references.

### Parameters

- `path` (string, required): Root path for search.
- `query` (string, required): Search expression.
- `mode` (string, optional, default: `content`): `content`, `filename`, or `both`.
- `regex` (boolean, optional, default: `false`)
- `case_sensitive` (boolean, optional, default: `false`)
- `file_glob` (string, optional): Limit search to matching files.
- `max_results` (integer, optional, default: implementation-defined)

### Example Usage

- Locate LLM mode selectors:
  - `path: /opt/ultra-stack`, `query: "MODE="`, `mode: content`
- Find Telegram bot handlers:
  - `path: /opt/ultra-stack`, `query: "*telegram*.py"`, `mode: filename`
- Search error pattern:
  - `path: /var/log/ultra`, `query: "Connection refused"`, `regex: false`

### Risk Level

**Low**

### Security Notes

- Protect against catastrophic regex patterns (ReDoS).
- Limit file size scanned per file and total scan time.
- Skip binary files by default.
- Redact sensitive matches from output where policy requires.

---

## Tool: `shell_execute`

### Description

Executes shell commands for diagnostics, orchestration, repair workflows, and controlled automation tasks.  
This is a high-power tool and should be gated by policy and command allowlists whenever possible.

### Parameters

- `command` (string, required): Command line to execute.
- `cwd` (string, optional): Working directory.
- `timeout_sec` (integer, optional, default: safe platform default)
- `env` (object/map, optional): Environment overrides.
- `capture_stderr` (boolean, optional, default: `true`)

### Example Usage

- Reload systemd daemon:
  - `command: systemctl daemon-reload`
- Check listening ports:
  - `command: ss -tulpen`
- Run health script:
  - `command: ./scripts/healthcheck.sh`, `cwd: /opt/ultra-stack`

### Risk Level

**Critical**

### Security Notes

- Prefer fixed subcommands over unrestricted shell.
- Disallow command chaining/metacharacters unless absolutely required.
- Enforce strict timeout and output limits.
- Drop dangerous commands (`rm -rf /`, user management, raw firewall mutation) unless explicitly authorized.
- Log full invocation metadata for forensic auditing.

---

## Tool: `service_status`

### Description

Retrieves status and health information for systemd services.  
Used by Monitor/Healer loops to detect failures, degraded states, restart storms, and dependency issues.

### Parameters

- `service_name` (string, required): systemd unit name (e.g., `ultra-monitor.service`).
- `verbose` (boolean, optional, default: `false`): Include extended state fields/journal hints.

### Example Usage

- Check primary orchestrator:
  - `service_name: ultra-orchestrator.service`
- Validate bot process:
  - `service_name: ultra-telegram.service`, `verbose: true`
- Inspect dependency service:
  - `service_name: docker.service`

### Risk Level

**Low**

### Security Notes

- Restrict query scope to known service prefixes in hardened mode.
- Normalize service names to prevent command injection in adapters.
- Avoid exposing full environment variables from unit dumps in shared logs.

---

## Tool: `service_control`

### Description

Controls systemd services with lifecycle actions such as start, stop, restart, reload, enable, and disable.  
Primary actuator for self-healing interventions.

### Parameters

- `service_name` (string, required): Target unit.
- `action` (string, required): One of `start`, `stop`, `restart`, `reload`, `enable`, `disable`.
- `force` (boolean, optional, default: `false`): Use only when policy allows.
- `daemon_reload` (boolean, optional, default: `false`): Reload unit definitions before action.

### Example Usage

- Restart failed component:
  - `service_name: ultra-healer.service`, `action: restart`
- Apply updated unit file:
  - `service_name: ultra-monitor.service`, `daemon_reload: true`, `action: restart`
- Enable service on boot:
  - `service_name: ultra-dashboard.service`, `action: enable`

### Risk Level

**High**

### Security Notes

- Prevent broad stop/restart waves without dependency awareness.
- Apply cooldown policy to avoid restart loops.
- Require reason tagging (`incident_id`, `trigger`) in production audit pipelines.
- Guard critical infrastructure services from accidental disable operations.

---

## Tool: `get_logs`

### Description

Fetches logs from journald or file-based sources for troubleshooting and root-cause analysis.  
Supports targeted extraction around service failures and recent incidents.

### Parameters

- `source` (string, required): `journal` or `file`.
- `service_name` (string, required if `source=journal`): systemd unit.
- `file_path` (string, required if `source=file`): Log file path.
- `lines` (integer, optional, default: 200): Tail line count.
- `since` (string, optional): Relative/absolute time filter (e.g., `-30m`).
- `grep` (string, optional): Filter keyword/regex.

### Example Usage

- Journal logs for failed service:
  - `source: journal`, `service_name: ultra-learner.service`, `lines: 300`
- File logs for app:
  - `source: file`, `file_path: /var/log/ultra/pwa.log`, `lines: 150`
- Time-bounded extraction:
  - `source: journal`, `service_name: ultra-monitor.service`, `since: -15m`

### Risk Level

**Medium**

### Security Notes

- Redact secrets/tokens before returning logs to upstream contexts.
- Enforce max line/byte limits.
- Validate file ownership and path permissions for file source.
- Be aware that logs may contain user data and internal topology details.

---

## Tool: `run_python`

### Description

Executes Python code snippets or scripts in a controlled runtime for analysis, transformations, quick diagnostics, and automation tasks.

### Parameters

- `code` (string, optional): Inline Python code.
- `script_path` (string, optional): Path to Python script.
- `args` (array of strings, optional): Script arguments.
- `timeout_sec` (integer, optional, default: safe platform default)
- `venv` (string, optional): Virtual environment path.
- `python_bin` (string, optional): Explicit interpreter path.

### Example Usage

- Inline JSON transform:
  - `code: "import json; ..."`
- Run repository utility:
  - `script_path: /opt/ultra-stack/scripts/check_modes.py`
- Execute with virtual environment:
  - `script_path: tools/diag.py`, `venv: /opt/ultra-stack/.venv`

### Risk Level

**Critical**

### Security Notes

- Treat as arbitrary code execution equivalent.
- Sandbox when possible (containerized runner, restricted filesystem).
- Disable network egress for untrusted executions.
- Cap CPU, memory, wall time, and stdout/stderr size.
- Never execute unreviewed code derived from untrusted web content.

---

## Tool: `pip_install`

### Description

Installs Python packages via pip to satisfy runtime dependencies, hotfix missing modules, or bootstrap tooling.

### Parameters

- `packages` (array of strings, required): Package specifiers (e.g., `requests==2.32.3`).
- `venv` (string, optional): Target virtual environment.
- `index_url` (string, optional): Package index override.
- `upgrade` (boolean, optional, default: `false`)
- `timeout_sec` (integer, optional)

### Example Usage

- Install missing dependency:
  - `packages: ["httpx==0.27.0"]`, `venv: /opt/ultra-stack/.venv`
- Upgrade known package:
  - `packages: ["pydantic"]`, `upgrade: true`
- Install from internal mirror:
  - `packages: ["orjson==3.10.7"]`, `index_url: https://pypi.internal/simple`

### Risk Level

**High**

### Security Notes

- Pin versions whenever possible for reproducibility.
- Prefer trusted indexes and verified hashes in strict environments.
- Avoid global interpreter mutation; use dedicated venv.
- Record dependency changes for rollback and SBOM updates.
- Be cautious of dependency confusion and typosquatting attacks.

---

## Tool: `web_search`

### Description

Performs external web queries for documentation lookup, known issue investigation, API reference checks, and remediation guidance.

### Parameters

- `query` (string, required): Search query.
- `limit` (integer, optional, default: 5): Number of results.
- `lang` (string, optional): Language filter.
- `safe` (boolean, optional, default: `true`): Safe-search mode.

### Example Usage

- Find systemd unit failure reference:
  - `query: "systemd service enters failed state after restart limit hit"`
- Retrieve framework release note:
  - `query: "Next.js 16 breaking changes production build"`
- Investigate Docker log driver issue:
  - `query: "docker json-file log rotation best practices"`

### Risk Level

**Medium**

### Security Notes

- Treat retrieved content as untrusted input.
- Do not execute commands copied directly from search results.
- Prefer official docs and reputable sources.
- Strip tracking parameters and avoid leaking internal identifiers in queries.

---

## Tool: `docker_list`

### Description

Lists Docker containers and optionally images, showing runtime status for services such as Letta, Prometheus, and Grafana.

### Parameters

- `all` (boolean, optional, default: `true`): Include stopped containers.
- `format` (string, optional): Output format profile (`table`, `json`, etc.).
- `include_images` (boolean, optional, default: `false`): Also list images.

### Example Usage

- Check active stack containers:
  - `all: true`
- JSON output for programmatic parsing:
  - `all: true`, `format: json`
- Include image inventory:
  - `all: true`, `include_images: true`

### Risk Level

**Low**

### Security Notes

- Metadata may expose internal port mappings and image tags.
- Restrict exposure in multi-tenant environments.
- Avoid returning sensitive labels or environment snippets without redaction.

---

## Tool: `docker_logs`

### Description

Retrieves logs from Docker containers to diagnose startup failures, crashes, misconfigurations, and runtime exceptions.

### Parameters

- `container` (string, required): Container name or ID.
- `tail` (integer, optional, default: 200): Number of recent lines.
- `since` (string, optional): Time filter.
- `timestamps` (boolean, optional, default: `false`)
- `follow` (boolean, optional, default: `false`): Stream mode (if supported by executor).

### Example Usage

- Prometheus diagnostics:
  - `container: prometheus`, `tail: 300`
- Grafana recent errors:
  - `container: grafana`, `since: 10m`
- Letta startup trace with timestamps:
  - `container: letta`, `tail: 500`, `timestamps: true`

### Risk Level

**Medium**

### Security Notes

- Logs may include credentials or API keys if upstream apps are misconfigured.
- Enforce tail limits and output truncation.
- Prevent continuous follow mode from blocking agent control flow unless explicitly intended.
- Validate container identifiers to avoid command-construction vulnerabilities.

---

## Operational Recommendations

### Sequencing Pattern for Safe Automation

A reliable tool-chain pattern for autonomous remediation:

1. `service_status` / `docker_list` to establish current state.
2. `get_logs` / `docker_logs` for evidence collection.
3. `read_file` / `search_files` to inspect configuration and code.
4. Minimal corrective action (`write_file`, `service_control`, or targeted `shell_execute`).
5. Re-verify via `service_status` and health endpoints.
6. Persist action summary to audit artifacts.

### Retry and Backoff

- Use bounded retries with exponential backoff.
- Do not repeat the same destructive action without new evidence.
- Escalate to human operator after threshold breaches.

### Observability Integration

Tool invocations should emit telemetry:

- Latency per tool call
- Success/failure rate
- Error classes
- Target entities (service/container/path)
- Correlation IDs for incident threading

This enables Prometheus/Grafana dashboards and supports Learner/Improver feedback loops.

---

## Governance and Policy Controls

### Recommended Policy Layers

1. **Tool-level allow/deny** per environment (dev/staging/prod).
2. **Parameter-level constraints** (path prefixes, service prefixes, package source allowlists).
3. **Contextual approvals** for high-impact actions.
4. **Rate limiting** for critical tools (`shell_execute`, `run_python`, `service_control`, `pip_install`).

### Environment Profiles

- **Development**: broader permissions, lower friction.
- **Staging**: near-production constraints, full auditing.
- **Production**: strict gating, mandatory traceability, stronger redaction.

---

## Summary

The Smart Agent’s 13 tools provide a complete operational surface for autonomous diagnosis and remediation across filesystem, services, Python runtime, package dependencies, containers, and external knowledge lookup.

The same power that enables rapid self-healing also introduces operational risk.  
Production readiness depends on clear parameter contracts, strict policy enforcement, robust auditing, and disciplined execution patterns centered on minimal, reversible changes.