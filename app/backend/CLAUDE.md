# Backend (FastAPI + MongoDB)

## Running

Imports are absolute from the repo root (`from app.backend.common.db import models`), so run from the repo root:

```bash
python -m app.backend.api.src.main
```

Serves on `:8080` inside Docker (host port from `API_PORT`), `/` redirects to `/docs`. Docker: `docker compose -f app/infra/compose/compose.yaml up --build`.
`db.py` loads `app/.env` relative to its own file, so running from any directory works.

## Layers (`api/src/`)

One file per resource in each layer; keep the split:

- `routes/` — `APIRouter(prefix="/api/v1/<resource>")`. Parse input, pull the user id via `auth_token.get_user_id_from_token(token)`, call the service, wrap the result in an output DTO. No logic.
- `services/` — business rules and permission checks. Raise `HTTPException` here: 404 for missing, 403 for permission, and wrap repository calls in `try/except Exception` → 424 FAILED_DEPENDENCY.
- `repositories/` — thin pymongo calls, return raw dicts. Services turn them into `models.X(**data)`.
- `dto/input`, `dto/output` — Pydantic request/response bodies. Responses are wrapped: `{"wardrobe": ...}`, `{"wardrobes": [...]}`, `{"user": ...}`.

Auth: `AUTH` (OAuth2 bearer, JWT `sub` = user id) and `DB` are `Annotated` dependencies; add them as route params.

## Infra hooks

- `common/db/db.py`: one cached `MongoClient` per process (`get_client`); `get_db` returns the database. TLS CA bundle only for `mongodb+srv://` (Atlas), so a plain local Mongo works too.
- `main.py` lifespan creates indexes (`INDEXES`: items.wardrobe_ids, items.owner_id, wardrobes `roles.$**`, unique users.email). It uses `app.dependency_overrides[get_db]` when set, so tests index their fake DB. Add an entry there for every new query path.
- Env the API gets from compose (used from plan 03/04 on): `S3_ENDPOINT_URL` (internal, `http://seaweedfs:8333`), `S3_PUBLIC_ENDPOINT_URL` (sign presigned URLs with this one), `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `RABBITMQ_URL`. Use `signature_version="s3v4"` and region `us-east-1` with boto3.
- SeaweedFS quirk: `list_buckets` doesn't show the bucket created by `seaweedfs-init`, but reads/writes to it work. Don't rely on `list_buckets`/`head_bucket` checks.

## Models (`common/db/models.py`)

- IDs are uuid4 strings stored as `_id` (`Field(alias="_id")`). Responses serialize by alias, so clients see `_id`.
- Datetime fields use `UtcDatetime`: pymongo returns naive datetimes, which serialize without an offset and clients read as local time (was 3h off in Romania). Use it for every new `*_at` field.
- `User.hashed_password` is `exclude=True`: it never leaves the API. `insert_user` writes it explicitly; keep it that way.
- `Wardrobe.roles: Dict[user_id, WardrobeRole]` is the source of truth for access (`owner`/`editor`/`viewer`). `Wardrobe.user_id` is just the creator.

## Wardrobe roles: gotchas

- Remove a role with `$unset` (`unset_wardrobe_role`), never `$set` to `None`: a `None` role fails `models.Wardrobe` validation and breaks every read of that wardrobe.
- `PUT /wardrobes/{id}` only edits name/description; roles change only via the `/roles` endpoints (it used to replace the whole `roles` map and could drop the owner).
- "My wardrobes" (`GET /user/me`) = wardrobes where the caller has the OWNER role, not `user_id == caller`.
- `POST /{id}/leave`: any member removes their own role; the last owner gets 400 (a wardrobe never loses its last owner).
- List responses (`GetAllWardrobesByUser`) also carry `item_counts: {wardrobe_id: n}`, built by `_list_response` in `routes/wardrobe.py`.
- Role changes go through `_set_member_role` in `services/wardrobe.py` (owner check, plus a guard so the owner can't change their own role and leave the wardrobe without an owner).
- Route order matters in `routes/wardrobe.py`: the `/user/me...` routes have more path segments than `/{wardrobe_id}`, so they don't collide. Keep new single-segment routes above `/{wardrobe_id}`.

## Items

- `Item.wardrobe_ids` is many-to-many: an item can be in several wardrobes. Deleting a wardrobe `$pull`s its id from items (`pull_wardrobe_from_items`); it never deletes items.
- Rules in `services/item.py`: read = item owner or member of any of its wardrobes. Update/delete = item owner. Add to wardrobe = editor+ **and** item owner. Remove from wardrobe = editor+ or item owner.
- Role checks use `require_role(wardrobe, user_id, EDITORS | OWNER_ONLY, action)` from `services/wardrobe.py`; reuse it for outfits.
- `services/item.py` wraps repository calls with `_db(error, fn, *args)` (→ 424) instead of repeating try/except.

## Access

- Every route except `POST /users/` and `POST /auth/token` needs `AUTH`. `GET /wardrobes/{id}` is members-only (`get_wardrobe_for_member`, 403 otherwise); there's no list-all endpoint for users or wardrobes, and users can only modify/delete themselves via `/users/me`.
