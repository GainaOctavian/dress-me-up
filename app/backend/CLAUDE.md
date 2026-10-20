# Backend (FastAPI + MongoDB)

## Running

Imports are absolute from the repo root (`from app.backend.common.db import models`), so run from the repo root:

```bash
python -m app.backend.api.src.main
```

Serves on `:8080`, `/` redirects to `/docs`. Docker: `docker compose -f app/infra/compose/compose.yaml up --build`.
`db.py` loads `../../../.env` relative to the CWD; when running locally, export the vars (or rely on the Docker `env_file`).

## Layers (`api/src/`)

One file per resource in each layer; keep the split:

- `routes/` — `APIRouter(prefix="/api/v1/<resource>")`. Parse input, pull the user id via `auth_token.get_user_id_from_token(token)`, call the service, wrap the result in an output DTO. No logic.
- `services/` — business rules and permission checks. Raise `HTTPException` here: 404 for missing, 403 for permission, and wrap repository calls in `try/except Exception` → 424 FAILED_DEPENDENCY.
- `repositories/` — thin pymongo calls, return raw dicts. Services turn them into `models.X(**data)`.
- `dto/input`, `dto/output` — Pydantic request/response bodies. Responses are wrapped: `{"wardrobe": ...}`, `{"wardrobes": [...]}`, `{"user": ...}`.

Auth: `AUTH` (OAuth2 bearer, JWT `sub` = user id) and `DB` are `Annotated` dependencies; add them as route params.

## Models (`common/db/models.py`)

- IDs are uuid4 strings stored as `_id` (`Field(alias="_id")`). Responses serialize by alias, so clients see `_id`.
- `User.hashed_password` is `exclude=True`: it never leaves the API. `insert_user` writes it explicitly; keep it that way.
- `Wardrobe.roles: Dict[user_id, WardrobeRole]` is the source of truth for access (`owner`/`editor`/`viewer`). `Wardrobe.user_id` is just the creator.

## Wardrobe roles: gotchas

- Remove a role with `$unset` (`unset_wardrobe_role`), never `$set` to `None`: a `None` role fails `models.Wardrobe` validation and breaks every read of that wardrobe.
- Role changes go through `_set_member_role` in `services/wardrobe.py` (owner check, plus a guard so the owner can't change their own role and leave the wardrobe without an owner).
- Route order matters in `routes/wardrobe.py`: the `/user/me...` routes have more path segments than `/{wardrobe_id}`, so they don't collide. Keep new single-segment routes above `/{wardrobe_id}`.

## Access

- Every route except `POST /users/` and `POST /auth/token` needs `AUTH`. `GET /wardrobes/{id}` is members-only (`get_wardrobe_for_member`, 403 otherwise); there's no list-all endpoint for users or wardrobes, and users can only modify/delete themselves via `/users/me`.
