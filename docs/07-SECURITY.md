# 07 - Security Layer

The Ultra Stack security layer is designed as a defense-in-depth system for autonomous and semi-autonomous agent workflows. It combines static controls (pattern blocklists, path policies), dynamic controls (risk scoring, approval queue), runtime throttling (rate limiting per tool), and operational controls (audit trails, PANIC mode, fail2ban integration). This document specifies the implementation model, enforcement order, and operational procedures used to protect host integrity, data confidentiality, and service availability.

## 1. Security Objectives

### 1.1 Primary Goals

- Prevent destructive or irreversible actions from autonomous tools.
- Contain high-risk operations behind explicit human approval.
- Ensure full action traceability via structured JSONL audit records.
- Mitigate abuse patterns (prompt abuse, shell abuse, API spam, brute-force attempts).
- Allow low-risk, high-frequency workflows with minimal friction.

### 1.2 Security Model

Ultra Stack applies a layered model:

1. **Input and intent validation**  
   Detect dangerous patterns before command/tool execution.
2. **Risk classification**  
   Assign operation risk level (`LOW`, `MEDIUM`, `HIGH`) based on tool, arguments, and target.
3. **Policy gating**  
   Auto-approve safe actions only in approved paths and risk envelope.
4. **Rate limiting per tool**  
   Enforce request budgets to prevent runaway loops and abuse.
5. **Approval queue**  
   Hold risky operations until explicit human decision (Telegram inline controls).
6. **Emergency controls**  
   PANIC mode to halt sensitive execution globally.
7. **Auditing and ban controls**  
   JSONL logs + fail2ban for repeated malicious patterns.

## 2. Threat Model Summary

### 2.1 In-Scope Threats

- Prompt-injected command execution attempts.
- Unsafe shell or filesystem operations.
- Data exfiltration via network tools.
- Agent loops producing abusive request volumes.
- Unauthorized privileged command usage.
- Repeated failed approval manipulation attempts.

### 2.2 Out-of-Scope (for this layer)

- Kernel-level exploits.
- Hardware attacks.
- Full endpoint EDR replacement.
- Supply-chain security of external model providers.

## 3. Enforcement Pipeline

All actionable tool calls follow this sequence:

1. **Request received** from PWA/CLI/Telegram/API agent runtime.
2. **Tool adapter normalization** (structured arguments).
3. **Blocklist scan** against command text, payload, and path targets.
4. **Risk scoring** into `LOW`, `MEDIUM`, or `HIGH`.
5. **Path trust evaluation** for auto-approve allowlist.
6. **Rate limit check** for calling principal + tool.
7. **Decision phase**:
   - Permit directly,
   - Queue for approval,
   - Deny hard.
8. **Execution wrapper** applies timeout, output caps, and return sanitization.
9. **Audit emit** to JSONL with decision and metadata.
10. **Optional fail2ban feed** on repeated deny signatures.

If any layer returns `DENY`, execution is aborted and logged.

## 4. Dangerous Pattern Blocklist (22 Patterns)

The blocklist is implemented as case-insensitive regular expressions and token signatures evaluated on raw command text, arguments, and expanded shell payloads. Matches result in immediate deny unless an explicit internal override exists (reserved for controlled maintenance mode).

### 4.1 Pattern List

1. `rm\s+-rf\s+/($|\s)`  
2. `:\(\)\s*\{\s*:\|:&\s*\};:` (fork bomb)
3. `mkfs(\.\w+)?\s+`  
4. `dd\s+if=.*\s+of=/dev/`  
5. `shutdown\s+-h\s+now|reboot`  
6. `chmod\s+-R\s+777\s+/`  
7. `chown\s+-R\s+\w+:\w+\s+/`  
8. `>\s*/etc/(passwd|shadow|sudoers)`  
9. `curl\s+.*\|\s*(bash|sh)`  
10. `wget\s+.*\|\s*(bash|sh)`  
11. `nc\s+-e\s+|ncat\s+--exec`  
12. `python\s+-c\s+.*(pty|subprocess|socket).*` (reverse-shell indicators)
13. `bash\s+-i\s+>&\s*/dev/tcp/`  
14. `ssh\s+.*StrictHostKeyChecking=no.*`  
15. `iptables\s+(-F|--flush)`  
16. `ufw\s+disable`  
17. `systemctl\s+(stop|disable)\s+(docker|prometheus|grafana|ultra-)`  
18. `kill\s+-9\s+1`  
19. `useradd\s+|adduser\s+|passwd\s+` (identity mutation)
20. `sudo\s+su\b|su\s+-\b`  
21. `/etc/cron\.(d|daily|hourly)|crontab\s+-e` (persistence vector)
22. `(base64\s+-d|openssl\s+enc).*(\|\s*(bash|sh))` (obfuscated execution)

### 4.2 Notes

- Pattern matching runs before shell interpolation.
- Encoded payload heuristics are intentionally strict.
- False positives can be mitigated only via controlled policy exception files, never via runtime prompt text.

## 5. Risk Levels

Ultra Stack uses three risk levels that influence approval and execution paths.

### 5.1 LOW

Typical characteristics:

- Read-only operations.
- Safe metadata retrieval.
- File reads in trusted paths.
- Non-destructive diagnostics.

Default policy:

- Auto-approved if within global and tool-specific limits.
- Fully audited.

Examples:

- Read markdown docs.
- List files under `/opt/ultra/docs/`.
- Query service status (read-only wrappers).

### 5.2 MEDIUM

Typical characteristics:

- Writes to non-critical paths.
- Controlled code generation.
- Non-privileged process interactions.
- External API calls without credential mutation.

Default policy:

- Auto-approve only if target path is in trusted auto-approve paths and no dangerous patterns are matched.
- Otherwise route to approval queue.

Examples:

- Write generated example files in `/tmp/ultra/`.
- Refactor local sandbox script in `/opt/ultra/examples/`.

### 5.3 HIGH

Typical characteristics:

- Privileged operations.
- Service lifecycle mutation.
- Network/security config changes.
- File writes outside trusted paths.
- Any blocklist-near behavior.

Default policy:

- Requires explicit human approval.
- Denied automatically in PANIC mode.
- Elevated logging with full context.

Examples:

- Restarting core services.
- Modifying `/etc/*`, `/var/lib/*`, or systemd units.
- Executing shell with escalated privileges.

## 6. Auto-Approve Trusted Paths

The following paths are considered trusted for limited auto-approval of `LOW` and constrained `MEDIUM` operations:

- `/opt/ultra/docs/`
- `/opt/ultra/examples/`
- `/tmp/ultra/`

### 6.1 Path Rules

- Path must resolve to canonical realpath.
- Symlink traversal outside allowed roots is denied.
- Relative segments (`..`) are normalized and revalidated.
- Hidden override files are ignored by default.
- Executable bit changes are treated as `HIGH`, even inside trusted paths.

### 6.2 Why These Paths

- `docs`: documentation generation and reading.
- `examples`: safe sample artifacts and prototypes.
- `tmp/ultra`: disposable runtime artifacts.

No other path is implicitly trusted.

## 7. Rate Limiting Per Tool

Each Smart Agent tool has independent quotas. Limits are applied per identity tuple:

`(agent_id, user_id, tool_name, time_window)`

### 7.1 Limit Dimensions

- Requests per minute (RPM).
- Burst capacity.
- Concurrent executions.
- Daily ceiling (optional for expensive/network tools).

### 7.2 Reference Policy

- Read-only tools: high RPM, moderate burst.
- Write tools: medium RPM, low burst.
- Shell/system tools: low RPM, strict concurrency (often 1).
- External network tools: medium RPM with daily caps.

### 7.3 Enforcement Behavior

- On limit hit, request is rejected with `429_TOOL_RATE_LIMIT`.
- Consecutive violations increase temporary cooldown.
- Cooldown events are logged and can feed fail2ban if abuse is sustained.

### 7.4 Anti-Loop Protection

- Detect repetitive identical tool invocation signatures.
- Decay window resets only after quiet period.
- Optional circuit breaker can disable specific tool for an agent session.

## 8. Approval Queue (Telegram Inline Buttons)

High-risk and policy-gated medium-risk operations are sent to a central approval queue with Telegram notification and inline actions.

### 8.1 Queue Lifecycle

1. Request classified as requiring approval.
2. Ticket generated with immutable ID and hash.
3. Notification sent to authorized approvers via Telegram bot.
4. Approver chooses one action:
   - `Approve Once`
   - `Deny`
   - `Approve + TTL` (time-limited rule)
   - `Panic` (activate emergency mode)
5. Decision recorded to audit log.
6. Request executed or rejected accordingly.

### 8.2 Telegram Inline Controls

Minimum inline keyboard layout:

- Row 1: `✅ Approve Once` | `❌ Deny`
- Row 2: `⏱ Approve 10m` | `⏱ Approve 1h`
- Row 3: `🛑 PANIC`

Only pre-authorized Telegram user IDs can act on approval messages. Unauthorized button presses are rejected and logged.

### 8.3 Decision Integrity

- Callback payload includes ticket ID + integrity token.
- Expired tickets cannot be approved.
- Replayed callbacks are rejected.
- Last decision wins only if prior state is `PENDING`; terminal states are immutable.

### 8.4 Timeout Policy

- Default pending timeout: 5 minutes.
- On timeout: action denied (`DENY_TIMEOUT`).
- For critical workflows, timeout can be shortened to 60 seconds.

## 9. PANIC Mode

PANIC mode is a global emergency switch for immediate containment.

### 9.1 Activation Sources

- Telegram inline `PANIC` button.
- CLI admin command.
- Policy engine trigger (e.g., repeated high-risk anomalies).
- Manual file/flag toggle by operator.

### 9.2 Behavior in PANIC

- Deny all `HIGH` risk actions.
- Deny all shell/system mutation tools.
- Disable auto-approve for `MEDIUM`.
- Keep `LOW` read-only tools operational unless explicitly disabled.
- Raise alert events to monitoring channels.

### 9.3 Deactivation

- Requires explicit admin command and reason.
- Captured as audited event with operator identity.
- Optional grace period applies before normal policy resumes.

## 10. Audit Log (JSONL)

All security-relevant events are written as newline-delimited JSON (`.jsonl`) for machine parsing and retention workflows.

### 10.1 Log Scope

- Allow/deny decisions.
- Risk classifications.
- Blocklist hits.
- Approval queue lifecycle events.
- PANIC mode transitions.
- Rate limit and cooldown events.
- Authz failures in Telegram callbacks.

### 10.2 Canonical Record Fields

```json
{
  "ts": "2026-04-24T18:45:12.481Z",
  "event": "policy_decision",
  "request_id": "req_01HT...",
  "ticket_id": "appr_01HT...",
  "agent_id": "smart-agent",
  "user_id": "telegram:12345678",
  "tool": "shell_exec",
  "risk": "HIGH",
  "decision": "DENY",
  "reason": "blocklist_match",
  "pattern_id": 9,
  "target_path": "/etc/systemd/system/",
  "panic_mode": false,
  "rate_limit": {
    "window": "60s",
    "remaining": 0
  },
  "hash": "sha256:..."
}
```

### 10.3 Logging Requirements

- UTC timestamps in RFC3339 format.
- One event per line, no multiline payloads.
- Sensitive payloads redacted (tokens, secrets, private keys).
- Append-only semantics.
- Daily rotation with retention policy (recommended: 30-90 days hot, archived cold).

## 11. fail2ban Integration

fail2ban provides host-level response to repeated malicious interaction patterns surfaced by Ultra logs.

### 11.1 Integration Strategy

- Emit security denials to dedicated log file or tagged stream.
- fail2ban jail reads deny patterns (e.g., repeated blocked commands, unauthorized Telegram callbacks, brute-force endpoints).
- Ban source IP for configured durations.

### 11.2 Example Jail (Reference)

```ini
[ultra-security]
enabled  = true
port     = http,https,ssh
filter   = ultra-security
logpath  = /var/log/ultra/security.log
findtime = 600
maxretry = 8
bantime  = 3600
backend  = auto
action   = %(action_mwl)s
```

### 11.3 Example Filter (Reference)

```ini
[Definition]
failregex = .*"decision":"DENY".*"reason":"blocklist_match".*"source_ip":"<HOST>".*
            .*"event":"telegram_authz_fail".*"source_ip":"<HOST>".*
            .*"event":"rate_limit_abuse".*"source_ip":"<HOST>".*
ignoreregex =
```

### 11.4 Operational Notes

- Use conservative `maxretry` to reduce false positives.
- Ensure internal network probes are allowlisted where needed.
- Review bans via scheduled reports.

## 12. Tool Security Profiles

Each of the 13 Smart Agent tools should declare:

- Default risk level.
- Allowed operations and argument schema.
- Path constraints.
- Rate limits.
- Whether approval is mandatory.
- Timeout and max output size.

### 12.1 Recommended Baseline

- File read tools: `LOW`.
- File write tools: `MEDIUM` (or `HIGH` outside trusted paths).
- Shell/system tools: `HIGH`.
- Network fetch tools: `MEDIUM` with egress controls.
- Service control tools: `HIGH` always.

## 13. Interaction with LLM Modes

Ultra Stack supports seven LLM modes (`FREE`, `NORMAL`, `KIMI`, `BOOST`, `TURBO`, `BLACKBOX`, `CODE`). Security policy is mode-aware but enforcement remains server-side and non-bypassable.

### 13.1 Mode-Specific Guardrails

- `FREE`: strictest rate and approval defaults.
- `NORMAL`: balanced limits.
- `CODE`: higher write throughput in trusted paths only.
- `TURBO/BOOST`: stricter anti-loop controls due to high task velocity.
- `BLACKBOX`: mandatory expanded auditing and conservative execution policy.

No mode can disable blocklist, audit logging, or PANIC enforcement.

## 14. Self-Healing and Security Controls

Monitor/Healer/Learner/Improver components integrate with security signals:

- **Monitor** detects spikes in denies, approval backlog growth, or abnormal tool call rates.
- **Healer** can temporarily disable misbehaving tool routes.
- **Learner** analyzes false-positive rates and proposes policy tuning.
- **Improver** applies reviewed non-breaking policy updates.

Autonomous remediation never bypasses approval requirements for `HIGH` risk operations.

## 15. Operational Runbook

### 15.1 Daily Checks

- Review deny and high-risk allow events from JSONL.
- Inspect pending approval queue latency.
- Verify PANIC mode is off unless expected.
- Check fail2ban active bans for anomalies.

### 15.2 Incident Workflow

1. Activate PANIC if destructive behavior suspected.
2. Freeze approvals except trusted responders.
3. Export and snapshot last 24h audit logs.
4. Identify triggering agent/user/tool signatures.
5. Patch policy and blocklist rules.
6. Gradually restore from PANIC with monitoring.

### 15.3 Change Management

- Security policy changes must be versioned.
- Require peer review for blocklist/risk rule edits.
- Test in staging with synthetic workloads.
- Maintain rollback artifacts for last known good policy.

## 16. Hardening Recommendations

- Run services as non-root wherever feasible.
- Use systemd sandbox directives (`NoNewPrivileges`, `ProtectSystem`, `PrivateTmp`).
- Restrict outbound network for tools that do not require egress.
- Store secrets in dedicated vault/backends, never in prompts.
- Enforce TLS for dashboards and bot webhooks.
- Rotate bot/API tokens periodically.
- Enable immutable logs or remote forwarding for tamper resistance.

## 17. Validation and Test Cases

Minimum validation suite should include:

1. Blocklist deny for each of 22 patterns.
2. Path traversal denial (`../`) outside trusted roots.
3. Auto-approve success in `/opt/ultra/docs/`.
4. Medium-risk queue routing outside trusted paths.
5. High-risk approval requirement.
6. Telegram callback replay rejection.
7. Unauthorized approver rejection.
8. PANIC mode deny verification.
9. Rate limit exhaustion behavior.
10. JSONL schema validation.
11. fail2ban trigger simulation.
12. Recovery from queue timeout.

## 18. Compliance-Oriented Logging Guidance

For environments requiring stronger governance:

- Add actor metadata (`role`, `session_id`, `origin`).
- Hash command payloads for integrity while redacting secrets.
- Digitally sign rotated log files.
- Forward logs to centralized SIEM (Loki/Elastic/Splunk).
- Set retention based on legal/policy obligations.

## 19. Known Limitations

- Regex blocklists cannot guarantee perfect semantic detection.
- Very novel obfuscation may evade static signatures.
- Human approval can become bottleneck under sustained high-risk load.
- False positives may occur in security research or low-level debugging tasks.

Mitigations include anomaly detection, reviewed exceptions, and continuous rule updates.

## 20. Security Posture Summary

The Ultra Stack security layer provides practical, production-oriented safeguards for autonomous agent execution:

- 22-pattern dangerous action blocklist.
- Per-tool rate limiting with anti-loop behavior.
- Human-in-the-loop approval queue via Telegram inline controls.
- Emergency PANIC mode for immediate containment.
- Structured JSONL auditing for complete traceability.
- Trusted auto-approve paths for controlled productivity.
- fail2ban host-level response for repeated abuse.
- Clear risk model (`LOW` / `MEDIUM` / `HIGH`) aligned to operational impact.

This design enables fast iteration without sacrificing control boundaries, and it is intended to evolve as usage patterns, threat intelligence, and operational maturity increase.