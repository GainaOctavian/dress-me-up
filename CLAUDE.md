# dress-me-up

Wardrobe / outfit app: FastAPI + MongoDB backend, Expo (React Native) mobile client.

## Layout

- `app/backend/api/` — the FastAPI service (the only backend that does anything today). See `app/backend/CLAUDE.md`.
- `app/backend/common/` — code shared across backend services: Mongo models (`db/models.py`), DB dependency (`db/db.py`), id/password helpers (`stringproc/`).
- `app/backend/worker/`, `app/backend/file-service/` — placeholders, empty `main.py`.
- `app/mobile/` — Expo app. See `app/mobile/CLAUDE.md`.
- `app/infra/compose/compose.yaml` — runs the API only; reads env from `app/.env` (gitignored; needs `MONGODB_URI`, `DB_NAME`, `SECRET_KEY`).
- `docs/` — diagrams (class diagram, sequence diagram). `docs/claude-plans/` (gitignored) holds per-feature implementation plans derived from them; start from `00-overview.md`.

## Conventions

- Branches: `api/<feature>`, `ui/<feature>`; PRs into `main`.
- Commit messages: `feat(api): ...`, `feat(ui): ...`, `fix(api): ...`.
- Everything user-facing is English (UI copy, API messages). Some older code comments are Romanian; new ones in English.
- Never commit without the user's explicit OK, and never add `Co-Authored-By` trailers.
- No test suite yet. For backend changes, a quick check with FastAPI `TestClient` + `mongomock` (override `get_db`) works well — keep it in a scratch dir unless asked to add tests.
