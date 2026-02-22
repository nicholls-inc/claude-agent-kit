# Add Rate Limiting

## Context
API needs rate limiting to prevent abuse. Currently no rate limiting exists.

## Tasks

- [ ] Install and configure `express-rate-limit` package
- [ ] Create rate limit middleware with configurable limits per endpoint
- [ ] Add stricter limits for auth endpoints (login, register)
- [ ] Add default limit for all other endpoints
- [ ] Add rate limit headers to responses (X-RateLimit-Remaining etc.)
- [ ] Write tests for rate limiting behavior

## Verification
- `npm test` passes
- Manual test: send 100+ requests rapidly, verify 429 response after limit
