# dress-me-up

Wardrobe / outfit app: FastAPI + MongoDB backend, Expo (React Native) mobile client.

## Layout

- `app/backend/api/` — the FastAPI service (the only backend that does anything today). See `app/backend/CLAUDE.md`.
- `app/backend/common/` — code shared across backend services: Mongo models (`db/models.py`), DB dependency (`db/db.py`), id/password helpers (`stringproc/`).
- `app/backend/worker/` — image worker (RabbitMQ consumer): background removal + indigo glow, color/tag/category suggestions (CLIP). See `app/backend/CLAUDE.md` → Worker.
- `app/backend/renderer/` — 3D renderer (RabbitMQ consumer, plan 19): dresses the Anny mannequin with 3D garments and accessories (MakeHuman CC0/CC-BY, `app/infra/clothes/`, suits split into jackets/ties by `split_parts.py`) textured from the item photos taken apart into colour / seamless pattern tile / print decals (`fabric.py`), short gravity-free cloth sim against clipping, Blender render per outfit/pose. See `app/backend/CLAUDE.md` → 3D renderer.
- `app/backend/file-service/` — placeholder, empty `main.py`.
- `app/infra/body-assets/` — offline mannequin pipeline (Anny + Blender `bpy` in Docker): `render_bodies.py` → `out/` (committed renders + keypoints), `seed.py` uploads them. See `app/backend/CLAUDE.md` → Bodies.
- `app/mobile/` — Expo app. See `app/mobile/CLAUDE.md`.
- `app/infra/compose/` — local stack: `compose.yaml` runs the API, the image worker, the 3D renderer, SeaweedFS (S3-compatible, port 8333; MinIO stopped publishing images) and RabbitMQ (5672, UI on 15672 guest/guest). MongoDB is Atlas via `MONGODB_URI` in `app/.env` (gitignored; also `DB_NAME`, `SECRET_KEY`); add `-f compose.local-db.yaml` for a local Mongo instead. Host-specific values go in `app/infra/compose/.env` (gitignored): `API_PORT` (the user's 8080 is taken, they use 8000), `S3_PUBLIC_ENDPOINT_URL` (LAN IP, so presigned URLs work from the phone) and `CORS_ORIGINS` (Expo web dev servers, e.g. `http://localhost:8090,http://localhost:8091`; unset = no CORS).
- Test data: account `admin@test.io` (password given by the user) has "Test wardrobe" with 18 seeded items (Wikimedia Commons photos, processed by the worker) and a "Smart casual" outfit. Attribution: `docs/claude-plans/seed-attribution.md`.
- Run everything: `docker compose -f app/infra/compose/compose.yaml up -d --build`.
- `docs/` — diagrams (class diagram, sequence diagram). `docs/claude-plans/` (gitignored) holds per-feature implementation plans derived from them; start from `00-overview.md`.

## Conventions

- Branches: `api/<feature>`, `ui/<feature>`; PRs into `main`.
- Commit messages: `feat(api): ...`, `feat(ui): ...`, `fix(api): ...`.
- Everything user-facing is English (UI copy, API messages). Some older code comments are Romanian; new ones in English.
- Never commit without the user's explicit OK, and never add `Co-Authored-By` trailers.
- Before handing a UI feature over for testing, run it end-to-end in Expo web (see `app/mobile/CLAUDE.md` → E2E testing), not just `tsc`.
- No test suite yet. For backend changes, a quick check with FastAPI `TestClient` + `mongomock` (override `get_db`) works well — keep it in a scratch dir unless asked to add tests.
