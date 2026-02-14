# Plan 02: Resolver Agent, Exports, and Validation

## Goal
Create the opus-powered resolver agent, export worktree functions from the memory API, and add validation for the worktree session schema.

## Prerequisites
- [ ] Plan 01 complete (worktree.py exists with all primitives)

## Tasks

### Task 1: Create Resolver Agent Definition
**Files:** `.claude/agents/resolver.md`
**Action:**
Create the resolver agent with YAML frontmatter and instructions:

Frontmatter:
- `name: resolver`
- `description: Resolves git merge conflicts using both task descriptions for intent context. Teams only.`
- `tools: Read, Edit, Write, Bash, Grep, Glob`
- `model: opus` (per CONTEXT.md — best reasoning for conflict resolution)
- `maxTurns: 15`

Add HTML comment: `<!-- Model: opus — conflict resolution requires understanding both sides' intent -->`

Instructions:
- **Context section**: "You resolve merge conflicts between two agent branches. You receive: the conflicted files (with git markers), the task description for the conflicting branch (what it intended), and the already-merged state (what was integrated before this branch)."
- **Cycle**:
  1. Read each conflicted file to understand both sides
  2. Read the task descriptions to understand intent
  3. Edit files to resolve conflicts — preserve both intents where possible
  4. Run verify commands from BOTH the conflicting task AND previously merged tasks
  5. Stage resolved files: `git add <file>` for each resolved file
  6. Complete the merge: `git commit --no-edit`
  7. Report resolution to team lead via SendMessage
- **Rules**:
  - Preserve intent of BOTH sides — don't silently drop changes
  - If intents are truly contradictory, prefer the later task's intent (higher index = more specific)
  - If stuck after 2 attempts, message the team lead for manual resolution
  - NEVER use `git merge --abort` — that's the team lead's decision

**Verify:**
```bash
grep 'model: opus' .claude/agents/resolver.md && grep 'conflict' .claude/agents/resolver.md && echo 'PASS'
```

**Done when:** `.claude/agents/resolver.md` exists with opus model and conflict resolution instructions.

### Task 2: Export Worktree Functions from Memory API
**Files:** `scripts/memory/__init__.py`
**Action:**
Add worktree function exports following the existing bridge pattern:

1. Add to `__all__` list:
   - `"create_session"`, `"merge_session"`, `"cleanup_session"`
   - `"get_conflict_context"`, `"load_session"`, `"save_session"`

2. Add a new section `# Worktree (parallel agent isolation)` after the Bridge section, with lazy imports:
```python
def create_session(plan_json_path: Path, root: Path, task_descriptions: list[dict]) -> Any:
    from .worktree import create_session as _create
    return _create(plan_json_path, root, task_descriptions)

def merge_session(session: Any, root: Path) -> Any:
    from .worktree import merge_session as _merge
    return _merge(session, root)

def cleanup_session(session: Any, root: Path) -> None:
    from .worktree import cleanup_session as _cleanup
    _cleanup(session, root)

def get_conflict_context(session: Any, task_index: int, plan_json_path: Path, root: Path) -> dict:
    from .worktree import get_conflict_context as _ctx
    return _ctx(session, task_index, plan_json_path, root)

def load_session(root: Path) -> Any:
    from .worktree import load_session as _load
    return _load(root)

def save_session(session: Any, root: Path) -> None:
    from .worktree import save_session as _save
    _save(session, root)
```

**Verify:**
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import create_session, merge_session, cleanup_session, load_session; print('PASS')"
```

**Done when:** All worktree functions are importable from `scripts.memory`.

### Task 3: Validation + WORKFLOW.json Config
**Files:** `scripts/workflow_validate.py`, `docs/planning/WORKFLOW.json`
**Action:**

**workflow_validate.py** — Add worktree-session.json validation in the WORKFLOW.json validation section:

After the existing `agentTeams` validation block, add validation for worktree config:
```python
wt = agent_teams.get("worktreeMode")
if wt is not None:
    if isinstance(wt, bool) or not isinstance(wt, str) or wt not in ("always", "off"):
        findings.append(Finding("WARN", "WORKFLOW.json: agentTeams.worktreeMode should be 'always' or 'off'.", str(cfg_path)))
```

Also add a standalone function `_validate_worktree_session(root, findings)` that:
- Checks if `.cnogo/worktree-session.json` exists
- If it does, validates: `schemaVersion` (int), `feature` (str), `planNumber` (str), `baseCommit` (str), `baseBranch` (str), `phase` (str, one of known phases), `worktrees` (list), `mergeOrder` (list), `mergedSoFar` (list)
- Call this from the main validation function

**WORKFLOW.json** — Add `"worktreeMode": "always"` inside the `agentTeams` object (after `staleIndicatorMinutes`). Per CONTEXT.md decision: replace shared-dir entirely.

**Verify:**
```bash
python3 -c "compile(open('scripts/workflow_validate.py').read(), 'w.py', 'exec'); print('PASS')"
```
```bash
python3 scripts/workflow_validate.py
```
```bash
python3 -c "import json; wf=json.loads(open('docs/planning/WORKFLOW.json').read()); assert wf['agentTeams']['worktreeMode'] == 'always'; print('PASS')"
```

**Done when:** Validation covers worktree session schema, WORKFLOW.json has worktreeMode config.

## Verification

After all tasks:
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import create_session, merge_session, cleanup_session; print('PASS')"
grep 'model: opus' .claude/agents/resolver.md
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(worktree-parallel-agents): resolver agent, API exports, and validation

- Add .claude/agents/resolver.md (opus model for conflict resolution)
- Export worktree functions from scripts/memory/__init__.py
- Add worktree session schema validation to workflow_validate.py
- Add worktreeMode config to WORKFLOW.json
```

---
*Planned: 2026-02-14*
