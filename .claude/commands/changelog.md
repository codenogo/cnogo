# Changelog
<!-- effort: low -->

Generate or update CHANGELOG.md from git history.

## Arguments

- `/changelog` — Generate since last tag
- `/changelog v1.0.0..v1.1.0` — Generate for specific range
- `/changelog --full` — Regenerate entire changelog

## Your Task

Generate a changelog following [Keep a Changelog](https://keepachangelog.com/) format.

### Step 1: Determine Range

```bash
# Get last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

# Get commits since last tag (or all if no tag)
if [ -n "$LAST_TAG" ]; then
    COMMITS=$(git log $LAST_TAG..HEAD --oneline)
    RANGE="$LAST_TAG..HEAD"
else
    COMMITS=$(git log --oneline)
    RANGE="(all commits)"
fi

echo "Generating changelog for: $RANGE"
```

### Step 2: Categorise Commits

Parse commit messages and categorise by type:

```bash
# Get commits with full message
git log $LAST_TAG..HEAD --pretty=format:"%h|%s|%b" --no-merges
```

Map commit prefixes to changelog sections:

| Prefix | Changelog Section |
|--------|------------------|
| `feat:` | Added |
| `fix:` | Fixed |
| `docs:` | Documentation |
| `refactor:` | Changed |
| `perf:` | Changed (Performance) |
| `test:` | (skip - internal) |
| `chore:` | (skip - internal) |
| `BREAKING CHANGE:` | ⚠️ Breaking Changes |
| `deprecate:` | Deprecated |
| `security:` | Security |
| `remove:` | Removed |

### Step 3: Extract Details

For each commit:
1. Parse the type from prefix
2. Extract scope if present: `feat(auth): message` → scope: auth
3. Extract description
4. Look for BREAKING CHANGE in body
5. Look for issue references: `#123`, `JIRA-456`

### Step 4: Generate Changelog Entry

```markdown
## [Unreleased]

### ⚠️ Breaking Changes

- **scope:** Description ([#123](link)) - @author

### Added

- **scope:** Description ([commit](link))

### Changed

- **scope:** Description

### Fixed

- **scope:** Description

### Security

- **scope:** Description

### Deprecated

- **scope:** Description

### Removed

- **scope:** Description
```

### Step 5: Update CHANGELOG.md

If CHANGELOG.md exists:
1. Read existing content
2. Insert new entry after `# Changelog` header
3. Update `[Unreleased]` link

If CHANGELOG.md doesn't exist:
1. Create with header
2. Add entry

### Template

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

[Generated entries here]

## [1.0.0] - YYYY-MM-DD

### Added

- Initial release

[Unreleased]: https://github.com/owner/repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/owner/repo/releases/tag/v1.0.0
```

### Step 6: Show Preview

Before writing, show the user what will be added:

```markdown
## Preview

The following will be added to CHANGELOG.md:

---
[preview of entry]
---

Write to CHANGELOG.md? (y/n)
```

## Output

- Preview of changelog entry
- Written to CHANGELOG.md (after confirmation)
- Summary of changes by category
