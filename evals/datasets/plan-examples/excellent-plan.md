# CSV Export Feature Implementation Plan

## Context
Add CSV export capability to the user management API. Users should be able to export filtered user lists as CSV files via a new API endpoint.

**Scope**: This plan covers only the CSV export endpoint. Email delivery of exports and scheduled exports are explicitly excluded.

**Existing patterns**: The API uses Express routes in `src/routes/`, service layer in `src/services/`, and validation middleware in `src/middleware/`.

## Tasks

- [ ] **Task 1**: Create `src/services/csvExportService.ts` with a `generateUserCsv(filters)` method
  - Accept filter params (role, status, createdAfter)
  - Use existing `UserRepository.findWithFilters()` (already supports these filters)
  - Stream rows to avoid memory issues on large datasets
  - Return a `ReadableStream` of CSV content

- [ ] **Task 2**: Add `GET /api/users/export/csv` endpoint in `src/routes/users.ts`
  - Reuse existing `authMiddleware` and `requireRole('admin')` from `src/middleware/auth.ts`
  - Parse query params for filters
  - Set `Content-Type: text/csv` and `Content-Disposition: attachment`
  - Pipe the stream from csvExportService to response

- [ ] **Task 3**: Add input validation for export filters
  - Add validation schema in `src/validators/exportValidator.ts`
  - Reuse existing `validateRequest` middleware pattern from `src/middleware/validate.ts`
  - Validate: role is enum, status is enum, createdAfter is ISO date

- [ ] **Task 4**: Write unit tests in `tests/unit/csvExportService.test.ts`
  - Test CSV header generation
  - Test with empty results
  - Test with special characters in user data (commas, quotes, newlines)
  - Test filter passthrough to repository

- [ ] **Task 5**: Write integration tests in `tests/integration/csvExport.test.ts`
  - Test endpoint authentication (401 without token, 403 without admin role)
  - Test successful export with mock data
  - Test filter combinations
  - Test large dataset streaming (1000+ rows)

## Verification

```bash
npm test -- --grep "csv"           # Unit + integration tests
npx tsc --noEmit                    # Type checking
npm run lint                        # Lint check
curl -H "Authorization: Bearer $TOKEN" localhost:3000/api/users/export/csv  # Manual smoke test
```
