# CLAUDE.md — Rust

Agent instructions for this project. Claude reads this automatically.

## Project Overview

[One paragraph: what this project is, who it's for, what it does]

## Quick Reference

```bash
# Build
cargo build

# Build release
cargo build --release

# Test
cargo test

# Run locally
cargo run

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt

# Check
cargo check

# Documentation
cargo doc --open

# Audit dependencies
cargo audit
```

## Code Organisation

```
src/
├── main.rs           # Binary entry point
├── lib.rs            # Library root
├── api/              # HTTP handlers (Actix/Axum)
│   └── mod.rs
├── services/         # Business logic
│   └── mod.rs
├── repositories/     # Data access
│   └── mod.rs
├── models/           # Domain types
│   └── mod.rs
├── errors/           # Error types
│   └── mod.rs
└── config/           # Configuration
    └── mod.rs

tests/
├── common/           # Shared test utilities
│   └── mod.rs
└── integration/      # Integration tests
```

## Conventions

### Naming
- Files: `snake_case.rs`
- Modules: `snake_case`
- Types/Traits: `PascalCase`
- Functions/Methods: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Lifetimes: short lowercase (`'a`, `'de`)

### Code Style
- Max line length: 100 characters
- Use `rustfmt` for formatting
- Use `clippy` for linting
- Follow Rust API Guidelines

### Git
- Branch naming: `feature/description`, `fix/description`
- Commit format: `feat(scope): description` or `fix(scope): description`
- PR: Squash and merge

## Architecture Rules

### Do
- Use `Result<T, E>` for fallible operations
- Prefer `&str` over `String` in function parameters
- Use `thiserror` for library errors, `anyhow` for applications
- Use `serde` for serialization
- Write doc comments for public APIs

### Don't
- Don't use `unwrap()` or `expect()` in library code
- Don't use `unsafe` without clear justification
- Don't ignore clippy warnings
- Don't use `clone()` without considering alternatives
- Don't panic in library code

## Key Patterns

### Error Handling
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Not found: {0}")]
    NotFound(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Database error")]
    Database(#[from] sqlx::Error),
}
```

### Response Format
```rust
use serde::Serialize;

#[derive(Serialize)]
pub struct ApiResponse<T> {
    pub data: Option<T>,
    pub message: Option<String>,
    pub errors: Option<Vec<String>>,
}
```

### Testing
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_example() {
        // Arrange
        // Act
        // Assert
    }
}
```

### Async Patterns (Tokio)
```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ...
}
```

## Security

- Never commit: `.env`, secrets, `*.pem`, `*.key`
- Always: Use parameterized queries (sqlx)
- Audit: Run `cargo audit` regularly
- Use `secrecy` crate for sensitive values

## Dependencies

Before adding dependencies:
1. Check if std library suffices
2. Prefer crates with minimal dependencies
3. Check maintenance status on crates.io
4. Run `cargo audit` after adding
5. Verify MSRV compatibility

---

## Planning Docs

- Project vision: `docs/planning/PROJECT.md`
- Current state: `docs/planning/STATE.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`
