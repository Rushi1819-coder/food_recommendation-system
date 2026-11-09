# Final Package Checklist

Date: 12 October 2026

## Contents

- Application source for Phases 1–10
- Database base schema and migrations 001–004
- Existing tests and added operational/engagement tests
- README, Phase 5/6/7–10 progress reports, audit and Phase 11 test plan

## Exclusions

- Real `.env` and secrets
- Virtual environments
- Python bytecode and `__pycache__`
- Git metadata and OS/editor temporary files

## Checks run while preparing this archive

- Python syntax compilation for backend and tests: passed.
- JavaScript syntax checks for frontend and frontend test scripts: passed.
- Local HTML `href`/`src` reference and duplicate-ID check: passed for 22 pages and 104 local references.

## Not run / not claimed

- `pytest` execution: not run because Flask, Flask-SQLAlchemy, Flask-Cors and PyMySQL are not installed in this build environment.
- Runtime Flask import/app startup: not verified.
- MySQL migration execution, schema integration, order/offer transaction tests: not run.
- Live browser interaction against Flask + MySQL: not run.

The archive is a source-code delivery and still requires Phase 11 testing in the configured Windows/MySQL environment before claiming end-to-end completion.


## Validation policy follow-up

The package now enforces Unicode letters/spaces only for new account names and requires new account emails to use exactly `@gmail.com`. The frontend rules and messages, backend validation, Python test fixtures, and browser mock assertions were updated to match. Full automated tests and live browser tests must be rerun on the user's Windows/MySQL environment after extracting this package.
