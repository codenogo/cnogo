# CLAUDE.md

Agent instructions for this project. Claude reads this automatically.

## Project Overview

[One paragraph: what this project is, who it's for, what it does]

## Quick Reference

```bash
# Build
[build command]

# Test
[test command]

# Run locally
[run command]

# Lint/format
[lint command]
```

## Code Organisation

```
src/
├── [layer or feature]/     # [Purpose]
├── [layer or feature]/     # [Purpose]
└── [layer or feature]/     # [Purpose]

tests/
├── unit/                   # Unit tests
└── integration/            # Integration tests
```

## Conventions

### Naming
- Files: `kebab-case.ts` or `PascalCase.java`
- Classes: `PascalCase`
- Functions: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE`

### Code Style
- [Max line length]
- [Import ordering]
- [Any other conventions]

### Git
- Branch naming: `feature/description`, `fix/description`
- Commit format: `type(scope): description`
- PR: Squash and merge

## Architecture Rules

### Do
- [Pattern to follow]
- [Pattern to follow]

### Don't
- [Anti-pattern to avoid]
- [Anti-pattern to avoid]

## Key Files

| File | Purpose | Notes |
|------|---------|-------|
| `src/config/` | Configuration | Don't hardcode values |
| `src/types/` | Type definitions | Keep in sync with API |

## Common Tasks

### Adding a new API endpoint
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Adding a new database table
1. [Step 1]
2. [Step 2]

## Testing Requirements

- Unit tests required for: [what]
- Integration tests required for: [what]
- Minimum coverage: [X%]

## Security

- Never commit: secrets, keys, credentials
- Always validate: [inputs]
- Always sanitize: [outputs]

## Dependencies

Before adding dependencies:
1. Check if existing dep solves problem
2. Evaluate security (last update, maintainers, CVEs)
3. Consider bundle size impact

## Troubleshooting

### [Common Issue 1]
```bash
[Solution]
```

### [Common Issue 2]
```bash
[Solution]
```

---

## Planning Docs

- Project vision: `docs/planning/PROJECT.md`
- Current state: `docs/planning/STATE.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`

## Skills Library

Reusable playbooks/checklists Claude should apply:

- `docs/skills.md`

## Karpathy-Inspired Operating Principles

Adopt these principles for non-trivial work (especially when making code changes). Inspired by [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills).

1. **Think Before Coding**: don’t assume; surface confusion/tradeoffs; ask when ambiguous.
2. **Simplicity First**: minimum code that solves the problem; no speculative abstractions.
3. **Surgical Changes**: touch only what’s needed; don’t refactor unrelated areas.
4. **Goal-Driven Execution**: define success criteria; verify with commands/tests; loop until proven.
