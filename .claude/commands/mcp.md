# MCP: $ARGUMENTS
<!-- effort: medium -->

Manage Model Context Protocol connections for external integrations.

## Arguments

`/mcp` — List all configured MCP servers
`/mcp list` — List available MCP servers
`/mcp add <server>` — Add an MCP server
`/mcp remove <server>` — Remove an MCP server
`/mcp status` — Check connection health

## Available MCP Servers

| Server | Purpose | Setup |
|--------|---------|-------|
| `github` | Code reviews, PRs, issues | Requires GitHub token |
| `postgres` | Database queries | Requires connection string |
| `jira` | Project management | Requires Jira API token |
| `sentry` | Error monitoring | Requires Sentry DSN |
| `figma` | Design system access | Requires Figma token |
| `notion` | Documentation | Requires Notion API key |
| `linear` | Issue tracking | Requires Linear API key |
| `slack` | Team communication | Requires Slack bot token |

## Your Task

### If no argument or `list`:

```bash
echo "=== Configured MCP Servers ==="
claude mcp list 2>/dev/null || echo "No MCP servers configured"

echo ""
echo "=== Available Servers ==="
echo "  github   - GitHub integration (PRs, issues, code review)"
echo "  postgres - PostgreSQL database queries"
echo "  jira     - Jira project management"
echo "  sentry   - Error monitoring and debugging"
echo "  figma    - Design system access"
echo "  notion   - Documentation and wikis"
echo "  linear   - Issue tracking"
echo "  slack    - Team notifications"
echo ""
echo "Add with: /mcp add <server>"
```

### If `add <server>`:

Guide the user through setup:

#### GitHub
```bash
echo "📦 Setting up GitHub MCP server..."
echo ""
echo "Requirements:"
echo "  1. GitHub Personal Access Token with repo scope"
echo "  2. Set GITHUB_TOKEN environment variable"
echo ""
echo "Run:"
echo "  export GITHUB_TOKEN=ghp_your_token_here"
echo "  claude mcp add github"
```

#### PostgreSQL
```bash
echo "📦 Setting up PostgreSQL MCP server..."
echo ""
echo "Requirements:"
echo "  1. PostgreSQL connection string"
echo "  2. Set DATABASE_URL environment variable"
echo ""
echo "Run:"
echo "  export DATABASE_URL=postgres://user:pass@host:5432/db"
echo "  claude mcp add postgres"
```

#### Jira
```bash
echo "📦 Setting up Jira MCP server..."
echo ""
echo "Requirements:"
echo "  1. Jira API token from https://id.atlassian.com/manage-profile/security/api-tokens"
echo "  2. Set JIRA_TOKEN and JIRA_URL environment variables"
echo ""
echo "Run:"
echo "  export JIRA_URL=https://your-domain.atlassian.net"
echo "  export JIRA_TOKEN=your_api_token"
echo "  claude mcp add jira"
```

#### Sentry
```bash
echo "📦 Setting up Sentry MCP server..."
echo ""
echo "Requirements:"
echo "  1. Sentry Auth Token from https://sentry.io/settings/account/api/auth-tokens/"
echo "  2. Set SENTRY_AUTH_TOKEN environment variable"
echo ""
echo "Run:"
echo "  export SENTRY_AUTH_TOKEN=your_token"
echo "  claude mcp add sentry"
```

#### Figma
```bash
echo "📦 Setting up Figma MCP server..."
echo ""
echo "Requirements:"
echo "  1. Figma Personal Access Token from https://www.figma.com/developers/api#access-tokens"
echo "  2. Set FIGMA_TOKEN environment variable"
echo ""
echo "Run:"
echo "  export FIGMA_TOKEN=your_token"
echo "  claude mcp add figma"
```

### If `status`:

```bash
echo "=== MCP Server Health ==="
claude mcp list 2>/dev/null | while read server; do
    echo "Checking $server..."
    claude mcp test "$server" 2>/dev/null && echo "  ✅ $server connected" || echo "  ❌ $server failed"
done
```

### If `remove <server>`:

```bash
echo "Removing MCP server: $ARGUMENTS..."
claude mcp remove "$ARGUMENTS"
echo "✅ Server removed"
```

## Integration with Workflow

Once MCP servers are configured, they enhance other commands:

| Command | Enhancement |
|---------|-------------|
| `/review` | Can fetch Sentry errors for context |
| `/ship` | Can create GitHub PR directly |
| `/debug` | Can query production logs via MCP |
| `/plan` | Can pull Jira tickets for context |
| `/discuss` | Can reference Figma designs |

## Output

- List of available/configured servers
- Setup instructions for requested server
- Connection status if checking health
