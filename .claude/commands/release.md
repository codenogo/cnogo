# Release: $ARGUMENTS
<!-- effort: max -->

Create a release with notes, tag, and optional SBOM.

## Arguments

- `/release patch` — Bump patch version (1.0.0 → 1.0.1)
- `/release minor` — Bump minor version (1.0.0 → 1.1.0)  
- `/release major` — Bump major version (1.0.0 → 2.0.0)
- `/release v1.2.3` — Explicit version

## Your Task

Create a release for "$ARGUMENTS".

### Step 1: Determine Version

```bash
# Get current version from tag
CURRENT=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
CURRENT=${CURRENT#v}  # Remove 'v' prefix

# Parse semver
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
```

Calculate new version based on argument:
- `patch` → `$MAJOR.$MINOR.$((PATCH+1))`
- `minor` → `$MAJOR.$((MINOR+1)).0`
- `major` → `$((MAJOR+1)).0.0`
- Explicit → Use as provided

### Step 2: Generate Release Notes

```bash
# Get commits since last tag
git log $CURRENT..HEAD --pretty=format:"- %s (%h)" --no-merges
```

Create release notes structure:

```markdown
# Release v[VERSION]

**Release Date:** [date]
**Previous Version:** v[previous]

## Highlights

[2-3 sentence summary of the most important changes]

## What's Changed

### ✨ New Features

- [Feature description] (#PR)

### 🐛 Bug Fixes

- [Fix description] (#PR)

### ⚠️ Breaking Changes

- [Breaking change and migration path]

### 📝 Documentation

- [Doc changes]

### 🔧 Maintenance

- [Maintenance items]

## Upgrade Guide

[Steps to upgrade from previous version]

```bash
# Example upgrade commands
npm install package@[VERSION]
```

## Contributors

@contributor1, @contributor2

## Full Changelog

https://github.com/owner/repo/compare/v[previous]...v[VERSION]
```

### Step 3: Update Version Files (if applicable)

```bash
# package.json
if [ -f package.json ]; then
    npm version $VERSION --no-git-tag-version
fi

# pom.xml
if [ -f pom.xml ]; then
    mvn versions:set -DnewVersion=$VERSION -DgenerateBackupPoms=false
fi

# pyproject.toml
if [ -f pyproject.toml ]; then
    export VERSION
    python3 - << 'PY'
from pathlib import Path
import os
import re

path = Path("pyproject.toml")
version = os.environ.get("VERSION", "")
if not version:
    raise SystemExit("VERSION env var not set")
text = path.read_text(encoding="utf-8")
text2, n = re.subn(r'(?m)^version\s*=\s*".*"$', f'version = "{version}"', text)
if n == 0:
    raise SystemExit("Could not find version = \"...\" line in pyproject.toml")
path.write_text(text2, encoding="utf-8")
PY
fi
```

### Step 4: Update CHANGELOG.md

Replace `[Unreleased]` with version and date:

```markdown
## [VERSION] - YYYY-MM-DD
```

Add new `[Unreleased]` section at top.

### Step 5: Generate SBOM (Optional)

If user confirms or compliance requires:

```bash
# For npm projects
npx @cyclonedx/cyclonedx-npm --output-file sbom.json

# For Maven projects  
mvn org.cyclonedx:cyclonedx-maven-plugin:makeAggregateBom

# For Python projects
pip install cyclonedx-bom
cyclonedx-py -o sbom.json
```

### Step 6: Create Commit and Tag

```bash
git add -A
git commit -m "chore(release): v$VERSION

- Update version to $VERSION
- Update CHANGELOG.md
- Generate release notes"

git tag -a "v$VERSION" -m "Release v$VERSION"
```

### Step 7: Preview and Confirm

Show user:

```markdown
## Release Preview

**Version:** v[VERSION]
**Commits included:** [N]
**Files changed:** [list]

### Release Notes Preview

[Show generated notes]

### Actions

- [ ] Commit version bump
- [ ] Create tag v[VERSION]
- [ ] Push tag to origin
- [ ] Create GitHub release

Proceed? (y/n)
```

### Step 8: Push and Create Release

```bash
git push origin main
git push origin v$VERSION

# Create GitHub release
gh release create v$VERSION \
    --title "v$VERSION" \
    --notes-file RELEASE_NOTES.md \
    --latest
```

If SBOM was generated:
```bash
gh release upload v$VERSION sbom.json
```

### Step 9: Update State

```markdown
## Latest Release

- **Version:** v[VERSION]
- **Date:** [date]
- **Tag:** v[VERSION]
- **Release:** https://github.com/owner/repo/releases/tag/v[VERSION]
```

## Output

- Release notes generated
- Version bumped in relevant files
- CHANGELOG.md updated
- Tag created and pushed
- GitHub release created
- SBOM attached (if generated)
