# Performance Analysis

Profiling and optimization checklist.

## Checklist

- Identify hotspot (profile or log timings)
- Complexity check (watch for O(n^2) or worse)
- IO patterns (DB queries, network calls, file reads)
- N+1 query detection
- Caching opportunities (memoization, HTTP cache, query cache)
- Backpressure, retries, and timeout configuration
- Large payload handling (pagination, streaming, compression)
- Connection pooling and resource lifecycle

## Process

1. Measure before optimizing (baseline)
2. Identify the bottleneck (don't guess)
3. Fix the bottleneck
4. Measure after (confirm improvement)
5. Check for regressions
