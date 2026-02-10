# Context: $ARGUMENTS
<!-- effort: low -->

Load relevant files for a feature or area of the codebase.

## Your Task

Build a context pack for "$ARGUMENTS".

### Step 1: Search for Related Code

```bash
# Keyword search
rg -l "$ARGUMENTS" --type-add 'code:*.{java,ts,tsx,js,jsx,py,go,rs,kt}' -t code

# Find by naming convention
find . -type f \( -name "*$ARGUMENTS*" -o -name "*[related-term]*" \) | grep -v node_modules | grep -v target | grep -v build

# Check imports/dependencies
rg "import.*$ARGUMENTS" --type-add 'code:*.{java,ts,tsx,js,jsx,py,go}' -t code
```

### Step 2: Identify Hotspots

Files with high churn are dragons:

```bash
# Most changed files (last 3 months)
git log --since="3 months ago" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -20
```

Cross-reference with search results—churny + related = extra caution.

### Step 3: Find Tests

```bash
# Related test files
find . -type f \( -name "*$ARGUMENTS*test*" -o -name "*$ARGUMENTS*spec*" -o -name "*Test$ARGUMENTS*" \) | grep -v node_modules
```

### Step 4: Check Configs

```bash
# Config files that might be relevant
rg -l "$ARGUMENTS" -g "*.{yml,yaml,json,properties,toml,xml}" | head -10
```

### Step 5: Read Planning Docs

```bash
# Check if feature has existing docs
ls docs/planning/work/features/*$ARGUMENTS*/ 2>/dev/null
cat docs/planning/work/features/*$ARGUMENTS*/CONTEXT.md 2>/dev/null
```

### Step 6: Generate Context Pack

Output:

```markdown
## Context Pack: $ARGUMENTS

### Core Files (read these first)
| File | Relevance |
|------|-----------|
| `src/services/[feature].ts` | Main implementation |
| `src/controllers/[feature].ts` | API layer |

### Tests
| File | Coverage |
|------|----------|
| `tests/[feature].test.ts` | Unit tests |

### Configs
| File | Purpose |
|------|---------|
| `config/[feature].yml` | Feature config |

### Hotspots ⚠️
| File | Churn | Risk |
|------|-------|------|
| `src/utils/helpers.ts` | 47 changes | High - many dependencies |

### Dependencies
| This feature uses | Used by |
|-------------------|---------|
| `AuthService` | `UserController` |

### Related Docs
- `docs/planning/work/features/[feature]/CONTEXT.md`
- `docs/adr/003-[related-decision].md`

### Don't Break
- [ ] `src/api/contracts/[feature].ts` - Public API
- [ ] `src/db/migrations/` - Schema changes need migration
```

### Step 7: Load Key Files

Read the top 3-5 most relevant files to have them in context.

## Output

Structured context pack with files loaded and ready for work.
