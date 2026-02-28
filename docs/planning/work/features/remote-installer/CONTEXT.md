# Remote Installer

## Summary

Add a thin bootstrap script (`remote-install.sh`) so other projects can install cnogo with a one-liner without manually cloning the repo first.

## Decisions

- **Distribution**: `remote-install.sh` clones the repo to a temp dir, runs `install.sh`, cleans up. One file, no duplication.
- **Access**: Supports private repos (git clone via SSH) and public (curl from raw.githubusercontent.com). Auto-detects.
- **CLI**: Accepts target dir, `--ref <tag/branch>` for version pinning, passes through `--update`/`--uninstall`/`--force` to install.sh.
- **Cleanup**: Uses `mktemp -d` + `trap EXIT` — temp dir always removed.
- **Location**: `remote-install.sh` at repo root.

## Usage (when public)

```bash
curl -sL https://raw.githubusercontent.com/codenogo/workflowy/main/remote-install.sh | bash -s -- .
```

## Usage (private, with SSH access)

```bash
curl -sL https://raw.githubusercontent.com/codenogo/workflowy/main/remote-install.sh | bash -s -- --ref main .
# or manually:
git clone git@github.com:codenogo/workflowy.git /tmp/cnogo && /tmp/cnogo/install.sh -y . && rm -rf /tmp/cnogo
```

## Validation Cleanup (bundled)

Batch-fix all pre-existing validation errors and warnings before adding new artifacts:
- 14 old REVIEW.json files with schemaVersion < 4 (required by `twoStageReview` policy)
- Ambiguous file paths in historical plan artifacts
- Other minor warnings (summary-outside-plan, word budgets, missing links)

## Constraints

- Bash only, no Python/Node in bootstrap
- macOS + Linux compatible
- install.sh remains the single source of truth
- Validation cleanup must not change semantics of old artifacts
