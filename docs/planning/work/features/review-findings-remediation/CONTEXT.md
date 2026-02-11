# Review Findings Remediation - Implementation Context

## Source

Findings from a 3-agent parallel review (code-reviewer, security-scanner, perf-analyzer) of the full codebase. 20 findings total: 6 critical, 8 high, 6 medium.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Scope | All 20 findings | Full remediation — critical, high, and medium |
| Hook strategy | Extract to shell scripts | Move hooks from inline settings.json to `scripts/pre-commit-secrets.sh` etc. Easier to maintain, test, debug |
| Pre-commit tests | Remove entirely | Tests already run during /review and /verify-ci; pre-commit adds 10-120s for marginal value |
| Settings merge | Skip if exists | Same pattern as CODEOWNERS — warn and skip. Users manually merge new settings |
| Agent tools | Remove Bash from review agents | code-reviewer, security-scanner, perf-analyzer, api-reviewer become Read/Grep/Glob only |
| Bash file access | Add deny patterns for sensitive files | Deny `cat .env`, `head .env`, `tail .env`, `grep .env` etc. to close the Read hook bypass |
| Python DRY | Create workflow_utils.py | Shared module with load_json(), repo_root(), write_json(). All scripts import from it |

## Findings to Fix (20)

### Critical (Phase 1)

| # | Finding | Fix |
|---|---------|-----|
| 1 | install.sh doesn't copy scripts/ | Add scripts/ copy section to install.sh |
| 2 | PostToolUse hook path wrong ($HOME/.claude/scripts/) | Fix to project-relative scripts/ path |
| 3 | Shell injection via $CLAUDE_TOOL_INPUT | Extract hooks to scripts, use proper quoting/printf |
| 4 | settings.json overwritten on merge install | Skip if exists, warn user |
| 5 | Pre-commit runs full test suite (10-120s) | Remove test runner hook entirely |
| 6 | Secret scanning duplicated in 3 places | Single source in scripts/pre-commit-secrets.sh, reference from review.md |

### High (Phase 2)

| # | Finding | Fix |
|---|---------|-----|
| 7 | Dangerous command hook trivially bypassed | Expand patterns (split flags, absolute paths, aliases) |
| 8 | rm -rf . / rm -rf .git not denied | Add deny rules for rm -rf ., .., .git |
| 9 | Sensitive file Read hook bypassed via Bash cat | Add Bash deny patterns for cat/head/tail/grep on sensitive files |
| 10 | Review agents have unnecessary Bash access | Remove Bash from 4 sonnet review agents |
| 11 | PostToolUse Python hook 100-500ms per edit | Cache formatter availability, early-exit check |
| 12 | Secret scanner spawns 8 greps per file | Combine into single alternation pattern |
| 13 | Missing secret patterns (Stripe, Twilio, etc.) | Add Stripe, Twilio, SendGrid, DB connection strings, Firebase patterns |
| 14 | curl/wget allowed for data exfiltration | Add deny for curl/wget with POST data flags targeting non-localhost |

### Medium (Phase 3)

| # | Finding | Fix |
|---|---------|-----|
| 15 | repo_root() implemented 3 different ways | Consolidate into workflow_utils.py |
| 16 | shell=True in workflow_checks.py | Document WORKFLOW.json as trusted; add comment |
| 17 | Force push, docker --privileged, terraform destroy not denied | Add deny rules |
| 18 | workflow_validate.py rglob without depth limits | Use WORKFLOW.json packages[] when available |
| 19 | validate_repo() is 233 lines | Split into focused validation functions |
| 20 | Unquoted $(basename $cmd) in install.sh | Quote properly |

## Constraints

- stdlib-only Python (no external deps) — applies to workflow_utils.py
- install.sh must remain a single portable script
- Hook extraction must not change the user-facing behavior (same patterns, same blocking)
- Agent definition changes must not break existing /spawn usage
- Settings.json deny patterns use prefix matching — inherently fragile, document limitations

## Open Questions

- [ ] Should we add a `.gitignore` entry for `*.pem`, `*.key`, etc.? (Security L1)
- [ ] Should WORKFLOW.schema.json be updated to include agentTeams? (Quality #20)
- [ ] Should we add hook timeouts? (Security L8)

## Related Code

- `.claude/settings.json` — hooks, permissions (most findings)
- `install.sh` — installer (findings 1, 4, 20)
- `scripts/*.py` — Python utilities (findings 2, 11, 15, 18, 19)
- `.claude/agents/*.md` — agent definitions (finding 10)
- `.claude/commands/review.md` — duplicated secret scanning (finding 6)
- `.claude/commands/spawn.md` — inline fallback duplication (perf suggestion)

---
*Discussed: 2026-02-10*
