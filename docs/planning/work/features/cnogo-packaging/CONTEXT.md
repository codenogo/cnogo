# cnogo Packaging & Lifecycle — Context

## Problem

cnogo is a workflow toolkit installed into other projects. This repo is both cnogo's source code AND a project that uses cnogo (self-hosting). Currently:

- `install.sh` copies files but there's no uninstall, update, or version tracking
- `scripts/context/` (context graph, 22 files) is not distributed
- cnogo files are scattered across `scripts/`, `.claude/`, `docs/` with no ownership markers
- No way to look at a repo and know "this file is cnogo" vs "this is my project"
- The installed layout should be identical to the source repo layout

## Core Principle

**The git repo IS the package.** The layout in git = the layout in every project. `install.sh` copies files as-is — no transformation. This repo gets cnogo installed into itself via the same mechanism as any other project.

## Decisions

### 1. Self-Hosting Identity

This repo is cnogo's source AND a cnogo-managed project. After packaging, cnogo is installed here the same way it's installed anywhere else. Development-only files (tests/, install.sh, docs/templates/) sit outside cnogo's installed scope.

### 2. All Runtime in .cnogo/scripts/

Scripts, memory engine, context graph, hooks — all under `.cnogo/`. Claude Code integration stays in `.claude/` (fixed paths). If it's in `.cnogo/`, it's cnogo. No ambiguity with project `scripts/` directories.

### 3. Git-Based Distribution

`install.sh` clones/pulls from the cnogo git repo. Also supports local path for offline/dev use. No separate build or archive step needed.

### 4. Five File Ownership Categories

| Category | Owned By | On Update | On Uninstall | Examples |
|----------|----------|-----------|--------------|----------|
| **managed** | cnogo | Always overwrite | Remove | scripts, commands, skills, agents, hooks |
| **seeded** | User (after creation) | Never overwrite | Leave | CLAUDE.md, PROJECT.md, WORKFLOW.json |
| **merged** | Shared | Merge cnogo parts only | Remove cnogo parts | settings.json, .gitignore |
| **runtime** | cnogo (at runtime) | Recreate if missing | Remove | memory.db, graph.db |
| **scaffold** | cnogo (structure) | Add new dirs only | Leave | docs/planning/work/*, .gitkeep files |

### 5. Manifest with Content Hashes

`.cnogo/manifest.json` is the single source of truth. Each file entry has category and sha256 hash at install time. Hash comparison detects user modifications — backup before overwriting on update.

### 6. Settings.json Merge via Markers

cnogo hook entries carry `"_cnogo": true`. Install adds hooks with marker. Update replaces hooks with marker. Uninstall removes hooks with marker. User hooks (no marker) are never touched.

### 7. .gitignore Merge via Comment Blocks

cnogo entries wrapped in `# >>> cnogo` / `# <<< cnogo`. Install adds block, update replaces block, uninstall removes block.

### 8. Context Graph Always Ships

`scripts/context/` (22 files) is core, not optional. Every install includes it.

### 9. Single install.sh for All Operations

`install.sh [--update|--uninstall|--force] [--from <git-url>] <project-dir>`. One script, manifest-based operations.

### 10. Import Path Resolution

`_bootstrap.py` in `.cnogo/scripts/` adds `.cnogo/` to `sys.path`. Entry-point scripts import it first. All `from scripts.memory import ...` patterns work unchanged.

## Target Directory Layout

```
project/
├── .cnogo/                              # cnogo runtime + state
│   ├── manifest.json                    # tracks ALL cnogo files + hashes
│   ├── version.json                     # version, source, commit
│   ├── scripts/
│   │   ├── _bootstrap.py               # sys.path resolution
│   │   ├── workflow_memory.py           # memory engine CLI
│   │   ├── workflow_checks.py           # review/verify
│   │   ├── workflow_validate.py         # contract validation
│   │   ├── workflow_hooks.py            # formatting/telemetry
│   │   ├── workflow_render.py           # JSON → markdown
│   │   ├── workflow_detect.py           # stack detection
│   │   ├── workflow_utils.py            # shared utilities
│   │   ├── memory/                      # 13 modules
│   │   └── context/                     # 22 modules (incl. phases/)
│   ├── hooks/
│   │   ├── hook-dangerous-cmd.sh
│   │   ├── hook-pre-commit-secrets.sh
│   │   ├── hook-sensitive-file.sh
│   │   ├── hook-commit-confirm.sh
│   │   ├── hook-post-commit-graph.sh
│   │   ├── hook-subagent-stop.py
│   │   ├── hook-pre-compact.py
│   │   └── install-githooks.sh
│   ├── templates/                       # language-specific CLAUDE templates
│   ├── issues.jsonl                     # git-tracked memory sync
│   ├── memory.db                        # runtime (gitignored)
│   └── graph.db                         # runtime (gitignored)
├── .claude/                             # Claude Code integration (fixed paths)
│   ├── commands/                        # 30 slash commands (managed)
│   ├── agents/                          # 3 agent definitions (managed)
│   ├── skills/                          # 16 skill files (managed)
│   ├── settings.json                    # merged (cnogo hooks + user hooks)
│   └── CLAUDE.md                        # managed (workflow docs)
├── docs/planning/
│   ├── PROJECT.md                       # seeded (user-owned)
│   ├── ROADMAP.md                       # seeded (user-owned)
│   ├── WORKFLOW.json                    # seeded (user-owned)
│   ├── WORKFLOW.schema.json             # managed
│   └── work/                            # scaffold + user artifacts
├── CLAUDE.md                            # seeded (user-owned)
└── [project files]
```

## Lifecycle Operations

**Install:** Clone/fetch source → copy managed files → seed templates → create scaffold → merge settings.json + .gitignore → init runtime → write manifest

**Update:** Read manifest → fetch new version → hash-compare managed files → backup user-modified → overwrite → remove deleted files → add new files → re-merge → re-index → update manifest

**Uninstall:** Read manifest → remove managed files → clean settings.json hooks → clean .gitignore block → leave seeded files + scaffold → remove .cnogo/

**Reinstall:** Uninstall + fresh install (`--force`). Seeded files left in place.

## Constraints

- Python stdlib only
- `.claude/` paths fixed by Claude Code
- `.cnogo/` needs `_bootstrap.py` for Python imports
- Single bash script installer (no build tools)
- Same layout in source repo and all installed repos
- settings.json and .gitignore are shared ownership (marker-based merge)

## Resolved Questions

1. **Python imports** → `_bootstrap.py` adds `.cnogo/` to `sys.path`
2. **Reference paths** → all commands/skills/hooks reference `.cnogo/scripts/` and `.cnogo/hooks/`
3. **.gitignore** → comment block markers (`# >>> cnogo` / `# <<< cnogo`)

## Next Steps

Ready for `/plan cnogo-packaging` — plans should be re-created from scratch based on this updated design.
