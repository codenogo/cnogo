# Code Review

Review checklist for code quality, security, and maintainability.

## Checklist

- Code is clear and readable
- Functions and variables are well-named
- No duplicated code or unnecessary complexity
- Proper error handling on all paths
- No exposed secrets or API keys
- Input validation implemented where needed
- Test coverage for new/changed behavior
- Performance considerations addressed
- No OWASP Top 10 vulnerabilities introduced

## Refactor Safety

- Behavior is preserved (no silent regressions)
- Changes are minimal and focused
- No mixed concerns (refactor + feature in same change)
- Deprecation strategy if interfaces change

## Output Format

- **Critical** (must fix before merge)
- **Warning** (should fix, creates tech debt)
- **Suggestion** (consider improving)

Include file:line references and specific fix examples.
