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

## Images (plan 03)

- Flow: `POST /images/upload-url {mime_type}` creates an `ImageAsset` (status `pending_upload`, key `originals/<owner>/<asset_id>.<ext>`) and returns a presigned POST. The client uploads straight to S3, then sends `image_asset_id` on item create/update. `services/image.claim_uploaded_asset` checks owner + `pending_upload` + that the object exists (`s3.head`), then marks it `ready`. Each asset can be attached once.
- `common/storage/s3.py` is the only S3 code (shared with the worker). It has two clients: internal for reads/writes, public for signing. The presigned POST pins `Content-Type` and `content-length-range` (10 MB), so S3 enforces both.
- Responses: items go out as `dto_out.ItemOut` with `image_url`, a presigned GET valid 24h (`processed_s3_key` if set, else `s3_key`). Build them with `item_service.to_out(db, items)` (one asset query per list). Never store URLs.
- Replacing an item's image or deleting the item deletes the old asset and its objects (`image_service.delete_asset`, best effort).
- SeaweedFS answers a presigned-POST policy mismatch (wrong content type) with 307 instead of 403, but stores nothing. Too large → 400 `EntityTooLarge`.
- Known orphans: assets uploaded but never attached (user picked a photo, then cancelled) stay `pending_upload`. The worker sweeper (plan 04) deletes those older than 24h.

## Outfits (plan 05)

- `Outfit.items` is embedded (`OutfitItem` + normalized `Transform`). `PUT` replaces the whole list; there are no per-item endpoints.
- Access (`services/outfit.py`): wardrobe outfits are readable by any member and editable by editor+. Personal outfits (`wardrobe_id=None`) belong to their owner only. `GET /outfits/me` = my outfits + outfits of every wardrobe I'm in.
- `_validate_items` on every write: items exist and are unique; in that wardrobe (wardrobe outfit), or owned/visible to the caller (personal).
- Cascades: removing an item from a wardrobe pulls it from that wardrobe's outfits; deleting an item pulls it from all outfits; deleting a wardrobe turns its outfits into personal outfits of their creators (`detach_outfits_from_wardrobe`).
- Responses are `OutfitOut` with `item_refs {item_id: {name, categories, subcategory, image_url, plain_url, image_size, fit}}` and `preview_url`, built by `outfit_service.to_out` (one item query + one asset query per list via `image_service.image_infos`), so clients can draw and dress an outfit without fetching items. `ItemOut` carries the same image fields.
- Dressed outfits (plan 13): `body_id`/`pose_id` set; each `OutfitItem` may carry `fit_adjust {dx, dy, scale, rotation}` (offsets in body heights, so tweaks survive a body switch). `PUT` can't clear `body_id` back to None (`exclude_none`); the app never needs to.

## Layering (plan 11)

- `common/layering.py` is the single source: 52 subcategories (type → category, body slot, layer role, label, CLIP prompt, tucked default) and the draw-order `BANDS`. `draw_order()` / `z_of()` implement the rules (tucked tops under trousers, belt under untucked tops, trousers over shoes unless `into_shoes`, manual `layer_offset` within a band). `warnings()` gives soft outfit checks. Run `python -m app.backend.common.layering` for its self-check.
- Served as `GET /api/v1/meta/layering` (no auth, static). The worker builds its CLIP garment prompts from the same table.
- `Item.subcategory` must belong to one of the item's categories: an empty `categories` is filled from it, a contradiction is 400 (`_consistent_categories` in `services/item.py`). The worker only fills `subcategory` when it agrees with the item's category.
- `OutfitItem` gained `tucked`, `into_shoes`, `open`, `layer_offset` (used by the plan 13 editor).
- Backfill after vocabulary changes: `docker compose -f app/infra/compose/compose.yaml exec worker python -m app.backend.worker.backfill` (suggestions-only pass, fills empty fields only).

## Bodies (plan 12)

- `Body` (collection `bodies`): built-in mannequins have fixed ids (`mannequin_male`, `mannequin_female`, `owner_id` None); user bodies (plan 16) get uuids and an owner. Each pose = transparent PNG (`image_key`, `size`) + `keypoints` normalized 0..1 (x right, y down; `_l`/`_r` = the body's own side, so `_l` is on the image's right).
- API: `GET /bodies/` (mannequins + mine), `GET /bodies/{id}` (someone else's → 404). `services/body.to_out` presigns pose images. Outfits take optional `body_id`/`pose_id`, validated by `_check_body` in `services/outfit.py`.
- Assets are generated offline in `app/infra/body-assets/` (image `dress-me-up-body-assets`, ~5 GB, not in compose):
  - `docker build -t dress-me-up-body-assets app/infra/body-assets`, then `docker run --rm -v <that dir>:/work dress-me-up-body-assets python render_bodies.py` (~1 min). Anny (Apache-2.0, MakeHuman CC0 assets; never the `[smpl]` extra) at phenotype 0.5 with gender 0/1, forearms straightened into the upper-arm line (A-pose), Cycles orthographic front render 1200×1800. Every body uses the same camera (`WORLD_H` 1.85 m, soles at y 0.97), so mannequins share scale and baseline. Keypoints come from Anny joints + torso cross-sections (trimesh); girths in `measurements_cm`.
  - Seed: `docker compose -f app/infra/compose/compose.yaml run --rm --no-deps -v <repo>/app/infra/body-assets:/assets worker python /assets/seed.py`. It uploads WebP q90 (~45 KB vs 1.4 MB PNG; `out/` keeps the PNGs). Keys are `bodies/<id>/<pose>-<sha10>.webp`: clients cache images by key, so a re-render must change it. The seed deletes the previous object.
  - Poses (plan 14): `POSES` = neutral, relaxed, hand_on_hip, walk, built in `make_pose` on top of neutral with `turn(pose, bone, side, axis, deg)` (local rotations; arm/leg: `y` = abduct(-)/adduct(+), `x` = forward(-)/back(+), knee bends on `x`; `.R` mirrors y/z) and `reach()` (coordinate descent bending the forearm so the wrist hits a target). The spine never moves, so the torso outline keypoints are neutral's; joints, `hip_joint_l/r` and each foot's own sole are re-read per pose.
  - Anny: Z up, front = −Y, `.L` = +X. Pose params are per-bone 4×4 in `local-ref`; `return_bone_ends` isn't supported, so read joints from `bone_poses[..., :3, 3]`.

## 3D renderer (plan 19)

- Service `renderer` (`app/backend/renderer/`, image ~4 GB: CPU torch + Anny + bpy 4.2 + common deps; `libgomp1` is needed, and `bpy` must be imported after torch). Consumes `outfit_render` jobs `{outfit_id, version}`; ~20–30 s per render on CPU. CPU is capped (`RENDER_THREADS` for Blender + torch, default 8; compose `cpus: ${RENDERER_CPUS:-8}`): with all 20 cores Cycles starved Docker Desktop's VM until the daemon stopped answering. Prototype `docker run`s get only `RENDER_THREADS`, so add `--cpus 8` to them too.
- Flow: outfit create/update (dressed outfits only) → `services/outfit._queue_render` bumps `Outfit.render.version` (whole subdocument: `render` is null on new outfits), sets `status: queued`, publishes. The renderer stores the WebP at `renders/<outfit>/<pose>-<sha10>.webp` only if `render.version` is still the job's (conditional update), otherwise deletes its upload; the previous image is deleted once replaced. `OutfitOut.render_url` = presigned current image (the old one stays visible while a new version renders). Deleting an outfit deletes its render.
- **How an outfit is dressed (v5, `renderer/outfit3d.py`), like clothes in games:** every item type wears a modelled 3D garment (`MODEL`: MakeHuman CC0 + CC-BY clothes in `app/infra/clothes/`, copied into the image as `/clothes`; male/female variants; shirts wear the collared button-up shirt, blazers and jackets models cut out of the Suits 01 suits (`app/infra/clothes/split_parts.py`: islands by size rank + the small ones sewn on; parts keep every vertex of the suit, so code that looks at a garment's extent must use only vertices in `triangles()`), hoodies the zip hoodie, sweaters the knit, cardigans/coats the long open cardigan; accessories (cap, hat, beanie, glasses, sunglasses, tie, bow tie, gloves, bag/backpack, socks) and per-type shoes have models too). `mhclo.py` binds a garment to Anny's **`topology="anny-full"`** body (MakeHuman hm08, 19158 vertices incl. helpers, posed by the same pose params): each garment vertex = 3 weighted body vertices + scaled offset, so it follows any shape and pose; `delete_verts` hides the skin under it. Not every `.mhclo` in the packs is free (some headers say AGPL): only add garments whose pack catalog says CC0 or CC-BY and list them in `app/infra/clothes/README.md` (CC-BY needs that attribution kept). Newer MakeClothes files scale offsets with `l_shear_x/y/z` or `shear_x/y/z` (`a b x1 x2`) instead of `x/y/z_scale` (`load` reads both; without a scale the offsets stay in reference units and the garment comes out as spikes). Loose parts (buttons, cuffs, pocket flaps: islands under 20% of the biggest piece) are carried along after the sim (`_carry_small_parts`), each in one piece with the displacement of the cloth nearest its centre: per-vertex they fly off, or a button on the overlap of two fronts stretches into a line.
- **Photo in parts, not stretched (`renderer/fabric.py`, self-check `python app/backend/renderer/fabric.py`):** `analyse(cutout)` → base colour (median Lab, lightness counted half so folds/shadows don't count); if ≥ 60% of the cloth is that colour the cloth is plain and whatever differs becomes **decals** (prints, logos, pockets, badges), otherwise it's a **pattern**: a small square (~12% of the garment width, no buttons/deep shadows, colour close to the average) with its low-frequency light flattened and its edges cross-faded → seamless `tile`. Decal components are dropped when they touch the cutout outline (hood, trim, collar: structure) or look like folds (soft edges: rim gradient / ΔL < 0.12, or darker with no hue of their own and < 0.2). No period detection: real photos (folds, perspective) don't repeat exactly. `photo_coords` maps the garment's neutral front projection onto the photo by a **similarity** (collar anchor, scale from collar→hem length: a flat-lay is wider than the same cloth wrapped round a body), so the tile repeats at its real size everywhere (back and sleeves too, UV map "tile") and decals land where they are on the photo, front faces only (UV map "decal", clipped). `mhclo.material` = colour or tile, decals over it, times the MakeHuman texture's luminance (seams/folds, UV map "uv"). UVs are computed once on neutral and reused in every pose. Items without anchors (old ones, shoes) get the colour only.
- **No clipping: physics then snapshot** (`mhclo.settle`): garments go on in plan 11 draw order (shoes rigid and not colliders: trousers are modelled to go into them), each gets 15 frames of Blender cloth **without gravity** (it only pushes the cloth out of the whole body and the layers below, nothing slides) and is frozen as a collider for the next. Duplicate vertices are merged first (`remove_doubles`): springs between coincident vertices made some garments (wool pants) explode. Use Blender's tuned mass/stiffness pair (0.3 / 15); gram-light vertices also exploded. Collision margins 4–5 mm: 3 mm let trousers poke through tops, 6 mm crumpled the hems. Each garment starts inflated `INFLATE` (5 mm) per cloth layer already on, along the body normal: the models are made for bare skin and started deep inside our layers. Tailored types (`HOLD`: blazers, jackets 0.6; trousers 0.4) are softly pinned to their modelled shape (`settle(hold=...)`), or the sim spreads jackets open and bunches waistbands over tucked shirts. After all sims, `_hide_covered` deletes an inner garment's faces whose vertices all have an outer garment within 2 cm toward the camera, or within 3 cm behind them (poking through), like `delete_verts` for skin: trousers under tops, a tee under a jacket, a tie under a sweater. Where nothing is on top (a jacket's V, an open cardigan, below a hem) the inner garment stays whole; whole faces only, so the edge along a lapel stays clean.
- Accessories (plan 15) are rigid (`RIGID` slots: no sim); only the tie and the belt are colliders (`COLLIDE`), so tops settle over them. Belt, watch and bracelet have no model: `Band` builds a ring round a slice of vertices picked on neutral (belt: the trousers 2.5 cm under the waistband top; watch/bracelet: the body 3 cm above `wrist.L`, from Anny's bone heads via `_posed`) and reuses them in every pose. A belt needs trousers and is moved onto their settled surface (`_onto`, + its gap): built on the trousers' unsimulated fit it ended up inside them (they get inflated and pushed out over a tucked shirt) and `_hide_covered` hid it. Accessories get the photo's colour (a tie also its pattern tile), no decals. Not drawn: scarf, necklace (no model). Parkas/coats wear the long cardigan until a closer model exists. The item form asks for tops on a hanger against a plain wall (flat, front on): that's what `fabric` reads best.
- Body data comes from `app/infra/body-assets/out/` baked into the image: `bodies.json` (neutral keypoints) + `<body>/<pose>.pose.npy` (pose params solved by `render_bodies.py`). Rebuild the renderer after regenerating bodies. Camera constants are duplicated from `render_bodies.py` (keep in sync).
- Prototype loop without the queue: `docker run --rm -w /repo -v <repo>:/repo -v <out>:/body-assets -e PYTHONPATH=/repo -e BODY_ASSETS=/body-assets -e CLOTHES=/repo/app/infra/clothes dress-me-up-renderer python <script>` calling `outfit3d.render_outfit(body, pose, garments, png)` (`-w /repo`: with `python -m`, the image's own copy under `/` would win).
- Not used by the 3D render yet: `fit_adjust` (2D tweaks), `open` (jackets render as modelled: blazers closed, cardigans open). Item photo changes don't re-render outfits (only outfit saves do).

## Worker (plan 04)

- Flow: client uploads to S3 → `POST /images/{id}/uploaded` (asset `ready`, job queued via `common/queue.publish`) → worker: `processing` → `processed` (or `failed` after 3 attempts) → client polls `GET /images/{id}` for `status`, the cutout URL and suggestions (`colors`, `tags`, `category`). Item create/update also claims the asset (`attached=True`, once) and queues it if the client skipped `/uploaded`.
- `worker/processing.py` is pure (bytes in → PNG + suggestions out): rembg `isnet-general-use` cutout, cropped, indigo glow (#6366f1) baked into a padded transparent PNG (max 1024px), k-means colors in Lab mapped to `PALETTE` names, CLIP ViT-B-32 zero-shot over `GARMENTS` (→ category + garment tag) and `TAG_GROUPS` (one tag per group above a threshold). Tune vocab/thresholds there.
- Plan 13 additions: `add_glow` also returns the plain cutout on the same padded canvas → `plain_s3_key` (`processed/<owner>/<asset>_plain.png`, drawn on the mannequin; cards keep the glow). `worker/anchors.py` (pure numpy, self-check: `python -m app.backend.worker.anchors`) computes garment anchors on the processed alpha (`alpha > 200` skips the glow) → `metadata.fit = {format, collar, top_l/r, hem_l/r, parts, shoulder_l/r?, sleeve_l/r?}`. Format 2 (plan 14) adds sleeves: torso column = 25th percentile of the run widths around the center in the 55–95% rows; mask outside it above the hem is sleeve, tip = farthest from where it leaves the torso. Symmetry repairs: one side found → mirrored; sides disagree (> 30° or > 1.4× length) → the shorter one, mirrored. Sleeves glued to the torso aren't found (the garment then follows the torso).
- Backfill modes: `python -m app.backend.worker.backfill [suggest|fit|reprocess]` (`reprocess` sets processed assets back to `ready` and re-runs everything; item fields are still only filled when empty).
- `worker/main.py`: writes `processed/<owner>/<asset>.png`, stores suggestions in `asset.metadata`, then `merge_into_item` fills the item: colors/categories only if empty, tags merged. Never overwrites user input.
- Sweeper (every 5 min): re-queues `ready` > 5 min / `processing` > 10 min; deletes un-attached uploads > 24h (S3 + doc, all three keys; `image_service.delete_asset` too).
- The worker image bakes the models (~2.5 GB, CPU torch). First build is slow; code changes rebuild only the last layers. Publishing never fails an API request: if RabbitMQ is down the sweeper catches up.
- Checks: point `RABBITMQ_URL` at a dead port in TestClient scripts so they don't enqueue into the dev stack.

## Access

- Every route except `POST /users/` and `POST /auth/token` needs `AUTH`. `GET /wardrobes/{id}` is members-only (`get_wardrobe_for_member`, 403 otherwise); there's no list-all endpoint for users or wardrobes, and users can only modify/delete themselves via `/users/me`.
