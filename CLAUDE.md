# dress-me-up

Wardrobe / outfit app: FastAPI + MongoDB backend, Expo (React Native) mobile client.

## Layout

- `app/backend/api/` — the FastAPI service (the only backend that does anything today). See `app/backend/CLAUDE.md`.
- `app/backend/common/` — code shared across backend services: Mongo models (`db/models.py`), DB dependency (`db/db.py`), id/password helpers (`stringproc/`).
- `app/backend/worker/`, `app/backend/file-service/` — placeholders, empty `main.py`.
- `app/mobile/` — Expo app. See `app/mobile/CLAUDE.md`.
- `app/infra/compose/` — local stack: `compose.yaml` runs the API, SeaweedFS (S3-compatible, port 8333; MinIO stopped publishing images) and RabbitMQ (5672, UI on 15672 guest/guest). MongoDB is Atlas via `MONGODB_URI` in `app/.env` (gitignored; also `DB_NAME`, `SECRET_KEY`); add `-f compose.local-db.yaml` for a local Mongo instead. Host-specific values go in `app/infra/compose/.env` (gitignored): `API_PORT` (the user's 8080 is taken, they use 8000) and `S3_PUBLIC_ENDPOINT_URL` (LAN IP, so presigned URLs work from the phone).
- Run everything: `docker compose -f app/infra/compose/compose.yaml up -d --build`.
- `docs/` — diagrams (class diagram, sequence diagram). `docs/claude-plans/` (gitignored) holds per-feature implementation plans derived from them; start from `00-overview.md`.

## Conventions

- Branches: `api/<feature>`, `ui/<feature>`; PRs into `main`.
- Commit messages: `feat(api): ...`, `feat(ui): ...`, `fix(api): ...`.
- Everything user-facing is English (UI copy, API messages). Some older code comments are Romanian; new ones in English.
- Never commit without the user's explicit OK, and never add `Co-Authored-By` trailers.
- Before handing a UI feature over for testing, run it end-to-end in Expo web (see `app/mobile/CLAUDE.md` → E2E testing), not just `tsc`.
- No test suite yet. For backend changes, a quick check with FastAPI `TestClient` + `mongomock` (override `get_db`) works well — keep it in a scratch dir unless asked to add tests.
