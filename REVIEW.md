# Security Audit Report: Merkle-CFI Agent Harness
**Date:** February 19, 2026
**Lead Auditor:** Lead AI Security Architect & Red Teamer
**Status:** DRAFT / READ-ONLY ANALYSIS COMPLETE

---

## 1. Executive Summary

### Risk Score: **CRITICAL (8.9/10)**

The Merkle-CFI architecture introduces a novel and highly effective method for ensuring **Control Flow Integrity (CFI)** in agentic workflows. By committing an execution plan to a Merkle tree and enforcing cryptographic leaf verification at each step, the system effectively mitigates "In-Flight Plan Mutation"—a common vector where an agent deviates from its original intent due to mid-session prompt injection.

However, the current implementation suffers from **Critical-level vulnerabilities** in the tool registry and lacks robust "Hard Gates" for dangerous actions. The "Secure" variants of tools exist but are not active, and the "Safety Gate" relies entirely on an LLM-based inspector which is susceptible to the same injection techniques it is meant to detect.

---

## 2. Detailed Vulnerability Findings

### [CRITICAL] C1: Path Traversal & Arbitrary File Write
*   **Location:** `src/tool_monitor/tools.py:L43` (`_tool_file_write`)
*   **Description:** The active `file_write` tool uses `os.path.abspath(path)` without verifying if the resulting path resides within a safe sandbox. 
*   **Exploit Vector:** An attacker (via Prompt Injection) can trick the user model into generating a plan with a path like `../../../../etc/cron.d/malicious_job`. 
*   **Risk:** Full system compromise, persistence, and data destruction.
*   **Note:** A secure implementation exists (`_secure_tool_file_write`) but is **not wired** to the `TOOLS` registry.

### [CRITICAL] C2: Unrestricted Egress & SSRF
*   **Location:** `src/tool_monitor/tools.py:L86` (`_tool_http_post`)
*   **Description:** The `http_post` tool allows the agent to send arbitrary JSON payloads to any URL. 
*   **Exploit Vector:** 
    1.  **Data Exfiltration:** Sending sensitive local data (e.g., `.env` contents) to a C2 server.
    2.  **SSRF:** Probing internal network metadata services (e.g., `http://169.254.169.254/latest/meta-data/`).
*   **Risk:** Information disclosure and lateral movement.

### [HIGH] H1: LLM-on-LLM "Soft Gate" Bypass
*   **Location:** `src/tool_monitor/harness.py:L193` (`inspect_plan`)
*   **Description:** The "Safety Gate" is a second LLM (`TOOL_MODEL`) prompted to be a security architect. While it uses "Theory of Mind" analysis, it is a probabilistic defense.
*   **Exploit Vector:** Indirect Prompt Injection. A payload in a `search` result could contain instructions that later trick the `TOOL_MODEL` during synthesis or subsequent steps if the state is reused.
*   **Risk:** Circumvention of all safety policies.

### [HIGH] H2: Data-to-Control Plane Leakage (Dynamic Variables)
*   **Location:** `src/tool_monitor/harness.py:L248` (`_execute_step`)
*   **Description:** The harness allows arguments marked `<DYNAMIC>` to be mutated during execution. While intended for data flow (e.g., summary text), there is no structural enforcement to prevent "Control Variables" (URLs, Paths) from being marked as `<DYNAMIC>`.
*   **Exploit Vector:** An injection payload can force the User Model to emit a plan where the `url` of an `http_post` is `<DYNAMIC>`, effectively bypassing the Merkle-CFI's static argument check.
*   **Risk:** Complete CFI bypass.

---

## 3. Threat Modeling Evaluation

### Recursive Loop Hijacking
**Assessment:** **LOW RISK.** The harness uses a finite `for` loop over a pre-committed Merkle tree of steps. The agent cannot autonomously append new steps to its current execution cycle. This is a best-in-class defense against infinite loops.

### Prompt Injection (Direct & Indirect)
**Assessment:** **HIGH RISK.** The `prior_observation` from `search` tools is fed raw into the ReACT prompt. Malicious search results can hijack the `TOOL_MODEL`'s "Thought" process, potentially leading it to use `<DYNAMIC>` arguments maliciously.

### Tool-to-Tool Contamination
**Assessment:** **CRITICAL.** The current flow allows: `search (untrusted data) -> summarize -> http_post (exfiltration)`. Without a "Privacy Wall" between tools, sensitive data retrieved in one step is easily moved to a high-risk egress tool.

---

## 4. Hardening & Defensive Patterns

### 1. The "Dual-LLM" Privilege Separation
*   **Pattern:** The `User Model` (Planning) should never see the raw output of high-risk tools.
*   **Implementation:** Introduce a `Data Scrubbing Model` that sanitizes tool observations before they are returned to the harness state, specifically redacting PII or potential injection strings.

### 2. Ephemeral Execution (Micro-Sandboxing)
*   **Pattern:** Tools must not run in the host OS context.
*   **Implementation:** Wrap `tools.py` in a Docker container or Firecracker MicroVM. The `workspace/` directory should be a temporary mount destroyed after each `run()`.

### 3. Zero-Trust Egress Policy
*   **Pattern:** Hard-code an allowlist for `http_post`.
*   **Implementation:**
    ```python
    ALLOWED_DOMAINS = ["api.trusted-service.com", "backup.internal"]
    if urlparse(url).netloc not in ALLOWED_DOMAINS:
        return "ERROR: Unauthorized egress."
    ```

### 4. Merkle-Enforced Control/Data Separation
*   **Pattern:** Programmatic enforcement of dynamic constraints.
*   **Implementation:** Modify `Step` model to distinguish between `control_args` (Fixed) and `data_args` (Dynamic). The `Scaffold` must reject any plan where a `path` or `url` is placed in the `data_args` bucket.

---

## 5. Operational Monitoring

### Agentic Anomaly Detection
*   **Token Spikes:** Monitor for sudden increases in `TOOL_MODEL` output length, which may indicate a "Refusal-Bypass" or "Jailbreak" attempt.
*   **Hash Mismatches:** Log all `IntegrityError` events as high-priority security alerts. A hash mismatch in production is a smoking gun for an attempted system-level exploit.
*   **Tool Failures:** Repeated "Tool Not Found" errors suggest the agent is trying to "hallucinate" capabilities (e.g., `bash`, `python_exec`) to escape the scaffold.

---
**Audit Complete.**
*Recommendation: Immediate migration to `_secure_tool_file_write` and implementation of Egress Filtering.*
