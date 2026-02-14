# Init
<!-- effort: medium -->

Auto-populate project templates by detecting the tech stack and gathering project information.

## Your Task

Scan the project, detect the tech stack, and populate the template files with sensible defaults.

### Step 1: Detect Tech Stack

```bash
echo "=== Detecting Tech Stack ==="

# Build system
if [ -f pom.xml ]; then
    echo "Build: Maven"
    STACK="java-maven"
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
    echo "Build: Gradle"
    STACK="java-gradle"
elif [ -f package.json ]; then
    echo "Build: npm"
    if grep -q "typescript" package.json 2>/dev/null; then
        STACK="typescript"
    else
        STACK="javascript"
    fi
elif [ -f pyproject.toml ]; then
    echo "Build: Python (pyproject.toml)"
    STACK="python"
elif [ -f setup.py ]; then
    echo "Build: Python (setup.py)"
    STACK="python"
elif [ -f go.mod ]; then
    echo "Build: Go"
    STACK="go"
elif [ -f Cargo.toml ]; then
    echo "Build: Rust"
    STACK="rust"
else
    echo "Build: Unknown"
    STACK="unknown"
fi

# Framework detection
echo ""
echo "=== Detecting Framework ==="

if [ -f package.json ]; then
    grep -E '"(react|vue|angular|next|nuxt|express|fastify|nestjs)"' package.json | head -5
fi

if [ -f pom.xml ]; then
    grep -E "(spring-boot|quarkus|micronaut)" pom.xml | head -5
fi

if [ -f pyproject.toml ]; then
    grep -E "(django|flask|fastapi)" pyproject.toml | head -5
fi

# Database detection
echo ""
echo "=== Detecting Database ==="

if [ -f docker-compose.yml ] || [ -f docker-compose.yaml ]; then
    grep -E "(postgres|mysql|mongodb|redis)" docker-compose.yml docker-compose.yaml 2>/dev/null | head -5
fi

# Test framework
echo ""
echo "=== Detecting Test Framework ==="

if [ -f package.json ]; then
    grep -E '"(jest|mocha|vitest|cypress|playwright)"' package.json | head -5
fi
```

#### Monorepo / Polyglot Detection (Required)

Also detect multi-package and polyglot layouts:

```bash
echo ""
echo "=== Detecting Repo Shape ==="

echo "package.json count:"
find . -name package.json -not -path "*/node_modules/*" -print | wc -l

echo "pyproject.toml count:"
find . -name pyproject.toml -print | wc -l

echo "pom.xml count:"
find . -name pom.xml -print | wc -l

echo "go.mod count:"
find . -name go.mod -print | wc -l

echo "Cargo.toml count:"
find . -name Cargo.toml -print | wc -l
```

If there are multiple manifests, treat this as a **monorepo/polyglot**. Do not assume one global build command; instead enumerate per-package commands in `CLAUDE.md`.

### Step 1b: Auto-Detect Packages (Recommended)

Run the detector to generate package list + commands, and write them into `WORKFLOW.json`:

```bash
python3 scripts/workflow_detect.py --write-workflow
```

This fills `docs/planning/WORKFLOW.json` → `packages[]` (paths, kinds, and suggested commands), which improves:

- monorepo verify scoping warnings
- `/verify-ci` and `/review` package-aware guidance

### Step 2: Gather Information

Ask the user for:

1. **Project name** (suggest from directory name or package.json/pom.xml)
2. **One-line description**
3. **Team/owner** (for CODEOWNERS)

### Step 3: Copy Stack-Specific CLAUDE.md Template

Based on detected stack, copy the appropriate template:

```bash
TEMPLATE_DIR="docs/templates"

case "$STACK" in
    java-maven|java-gradle)
        TEMPLATE="$TEMPLATE_DIR/CLAUDE-java.md"
        ;;
    typescript|javascript)
        TEMPLATE="$TEMPLATE_DIR/CLAUDE-typescript.md"
        ;;
    python)
        TEMPLATE="$TEMPLATE_DIR/CLAUDE-python.md"
        ;;
    go)
        TEMPLATE="$TEMPLATE_DIR/CLAUDE-go.md"
        ;;
    rust)
        TEMPLATE="$TEMPLATE_DIR/CLAUDE-rust.md"
        ;;
    *)
        TEMPLATE="docs/templates/CLAUDE-generic.md"  # Use generic template
        ;;
esac

if [ -f "$TEMPLATE" ]; then
    echo "Using template: $TEMPLATE"
    if [ -f "CLAUDE.md" ]; then
        # Check if CLAUDE.md has custom content (differs from generic template)
        GENERIC="docs/templates/CLAUDE-generic.md"
        if [ -f "$GENERIC" ] && ! diff -q "CLAUDE.md" "$GENERIC" > /dev/null 2>&1; then
            echo ""
            echo -e "${YELLOW}Your CLAUDE.md has custom content.${NC}"
            echo "The stack template ($STACK) would replace it."
            echo ""
            read -p "Replace CLAUDE.md with $STACK template? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "⏭️  Kept existing CLAUDE.md"
            else
                cp "$TEMPLATE" CLAUDE.md
                echo "✅ CLAUDE.md replaced with $STACK defaults"
            fi
        else
            cp "$TEMPLATE" CLAUDE.md
            echo "✅ CLAUDE.md populated with $STACK defaults"
        fi
    else
        cp "$TEMPLATE" CLAUDE.md
        echo "✅ CLAUDE.md populated with $STACK defaults"
    fi
else
    echo "⚠️ No template found for $STACK, using generic template"
fi
```

#### Step 3b: Populate “Quick Reference” for Monorepos

If multiple manifests were detected, update `CLAUDE.md` to include:

- A **Repo Shape** section (monorepo/polyglot)
- A **Per-Package Quick Reference** table listing:
  - package path
  - build/test/run/lint commands (best-effort)

Example discovery:

```bash
find . -maxdepth 4 -name package.json -not -path "*/node_modules/*" -print | head -20
find . -maxdepth 4 -name pom.xml -print | head -20
find . -maxdepth 4 -name pyproject.toml -print | head -20
```

You can also copy/paste the detector output into `CLAUDE.md`:

```bash
python3 scripts/workflow_detect.py
```

**Available Templates:**

| Stack | Template |
|-------|----------|
| Java/Spring | `docs/templates/CLAUDE-java.md` |
| TypeScript/Node | `docs/templates/CLAUDE-typescript.md` |
| Python | `docs/templates/CLAUDE-python.md` |
| Go | `docs/templates/CLAUDE-go.md` |
| Rust | `docs/templates/CLAUDE-rust.md` |

Each template includes:
- Stack-specific build/test/run commands
- Code organisation patterns
- Naming conventions
- Architecture rules
- Testing patterns
- Security guidelines

### Step 4: Populate PROJECT.md

Fill in:
- Project name and description from user input
- Tech stack table from detection
- Architecture diagram placeholder

### Step 5: Populate CODEOWNERS

```bash
# Detect code structure
echo "=== Directory Structure ==="
find . -type d -maxdepth 2 | grep -v node_modules | grep -v .git | grep -v target | head -20
```

Create CODEOWNERS based on:
- Detected service boundaries
- User-provided team information

### Step 6: Memory Engine Setup (Optional)

Ask the user if they want to enable the **memory engine** for structured task tracking.

If yes:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import init
from pathlib import Path
init(Path('.'))
print('Memory engine initialized at .cnogo/')
"
```

Then verify the `.gitignore` includes memory runtime exclusions:

```
.cnogo/memory.db
.cnogo/memory.db-wal
.cnogo/memory.db-shm
```

If these lines are missing, append them to `.gitignore`.

**What memory engine provides:**
- Structured issue tracking across sessions (persists to `.cnogo/issues.jsonl`)
- Dependency graphs with blocked/ready state detection
- Atomic task claiming for parallel agent coordination
- Token-efficient context summaries via `memory.prime()`

If the user declines, all commands continue to work exactly as before (markdown-only mode).

### Step 7: Verify

Show the user what was populated:

```markdown
## Init Complete

### Files Updated

| File | Status |
|------|--------|
| `CLAUDE.md` | Populated with [stack] commands |
| `docs/planning/PROJECT.md` | Tech stack detected |
| `.github/CODEOWNERS` | Default owner set |
| `.cnogo/memory.db` | Memory engine initialized (if enabled) |

### Next Steps

1. Review and customise `CLAUDE.md` with project-specific patterns
2. Add architecture details to `docs/planning/PROJECT.md`
3. Update team structure in `.github/CODEOWNERS`
4. Run `/status` to verify setup
```

## Output

- Detected tech stack summary
- Files that were updated
- Recommended next steps for customisation
