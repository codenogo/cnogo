# Research: Programmatic Tool Calling

**Date:** 2026-02-22 | **Mode:** auto | **Sources:** 12

## Context

cnogo is a Python stdlib-only workflow engine that orchestrates Claude Code Agent Teams for multi-agent plan execution. This research examines "programmatic tool calling" — both the general concept and Anthropic's specific PTC feature — to identify what's relevant, what's new, and what cnogo should consider.

## Key Findings

### 1. Two Meanings of "Programmatic Tool Calling"

**Standard Tool Use** is the baseline API contract: you define tools via JSON Schema, Claude returns `tool_use` blocks, you execute them client-side and send `tool_result` blocks back. This requires one model inference pass per tool call.

**Programmatic Tool Calling (PTC)** is a specific advanced feature (GA Feb 2026) where Claude writes async Python code inside a sandboxed container that calls your tools directly. One inference pass can orchestrate N tool calls via loops, conditionals, and aggregation.

### 2. PTC Architecture and Token Impact

Standard flow: `inference -> tool call -> execute -> inference -> tool call -> ...` (N passes).
PTC flow: `inference -> Python script -> N tool calls in sandbox -> final output` (1-2 passes).

Benchmark result: **85.6% token reduction** (110K to 16K tokens) on a team expense analysis task. Tool results stay in-sandbox and never enter model context.

**How to enable:**
- Add `code_execution_20260120` tool to the tools array
- Set `allowed_callers: ["code_execution_20260120"]` on tools that should be callable from code
- Container persists ~4.5 min idle; reuse via `container` parameter

**Constraints:** No structured outputs (`strict: true`), no `tool_choice` forcing, no MCP tools (yet).

### 3. Complementary Features (All GA Feb 2026)

| Feature | What | Impact |
|---------|------|--------|
| Tool Search Tool | `defer_loading: true` defers tool definitions until Claude searches for them | 85% definition token reduction for large toolsets |
| Tool Use Examples | `input_examples` array on tool definitions | Accuracy 72% -> 90% on complex params |
| Fine-Grained Streaming | `eager_input_streaming: true` per tool | Latency from 15s to 3s for large params |

### 4. tool_choice Control

| Value | Behavior |
|-------|----------|
| `auto` | Claude decides (default) |
| `any` | Must call a tool, Claude picks |
| `tool` | Must call named tool |
| `none` | No tool use |

Additional: `disable_parallel_tool_use: true` limits to one tool per response.

### 5. SDK and Tool Runner

The `anthropic` Python SDK provides a Tool Runner (beta) that automates the tool call loop via `@beta_tool` decorator. The Claude Agent SDK provides full agent infrastructure. Both require non-stdlib dependencies (`httpx`, `pydantic`).

**Stdlib-only alternative:** `urllib.request` against `https://api.anthropic.com/v1/messages` with manual JSON serialization. Loses streaming, retries, and type safety.

### 6. MCP Relationship

MCP standardizes tool discovery (`list_tools()`) and execution (`call_tool()`) across providers. Schema translation is trivial (`inputSchema` -> `input_schema`). MCP tools **cannot** be called via PTC yet. cnogo already has MCP server management.

### 7. cnogo's Current Position

cnogo uses Claude Code's built-in tool infrastructure extensively:
- Agent Teams with Task/TaskCreate/SendMessage tools
- TaskDescV2 schema via `bridge.py` for plan-to-task translation
- File scope validation and conflict detection before spawning
- Token budgeting in WORKFLOW.json

This is **indirect** tool calling — cnogo doesn't call the Claude API itself but leverages Claude Code as the runtime. The patterns are mature and well-documented in prior research (`opus-46-multi-agent`, `subagent-context-patterns`).

## Options and Fit Criteria

| Option | Fit | Risk |
|--------|-----|------|
| **Stay on Claude Code Agent Teams** | High — already working, no code needed | Locked to Claude Code runtime |
| **Add stdlib urllib API integration** | Medium — enables standalone execution | Manual tool loop, no streaming, fragile |
| **Add anthropic SDK (break stdlib rule)** | High capability — Tool Runner, PTC, streaming | Breaks project constraint |
| **Wait for MCP + PTC convergence** | Future value — MCP tools callable from PTC | Timeline unknown |

## Risks and Failure Modes

1. **PTC container expiry** — 4.5 min idle timeout; long-running tools can cause silent failures
2. **stdlib urllib fragility** — no retries, no streaming, manual error handling
3. **Token budget mismatch** — PTC savings (85%) are API-level; Claude Code Agent Teams have their own token dynamics not directly controlled by cnogo
4. **MCP + PTC gap** — MCP tools can't use PTC today; limits orchestration optimization

## Recommendation

**No immediate action needed.** cnogo's tool-calling patterns via Claude Code Agent Teams are mature and effective. The stdlib-only constraint makes direct API integration costly for limited benefit.

**If direct API integration becomes necessary:**
1. Start with stdlib `urllib.request` + standard tool use for simple cases
2. Consider relaxing the stdlib constraint for `anthropic` SDK if PTC token savings justify it
3. Track PTC + MCP convergence — when MCP tools become PTC-callable, cnogo's MCP-connected workflows could see 85% token reductions

## Open Questions

- Will Anthropic expose PTC without the full SDK (e.g., via MCP or Claude Code native)?
- Can Claude Code Agent Teams leverage PTC internally for multi-tool agent turns?
- What's the timeline for MCP tools becoming PTC-callable?
- Should cnogo's token budgets account for PTC-level savings in future planning?
