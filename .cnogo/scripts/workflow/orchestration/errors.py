"""Classified dispatch exceptions.

Inspired by Erlang/OTP supervisor child restart types:
- TransientDispatchError ≈ :transient — retryable via circuit breaker backoff
- SystemicDispatchError ≈ :permanent — immediate permanent hold, needs manual fix
"""

from __future__ import annotations


class TransientDispatchError(Exception):
    """Retryable: network timeouts, temporary file locks, git conflicts, rate limits."""
    pass


class SystemicDispatchError(Exception):
    """Non-retryable: missing schemas, permission denied, corrupt state, bad config."""
    pass
