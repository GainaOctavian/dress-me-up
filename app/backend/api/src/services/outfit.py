from typing import List, Optional

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common import queue
from app.backend.common.db import models
from app.backend.common.storage import s3
from app.backend.api.src.dto.input import outfit as dto_in
from app.backend.api.src.dto.output import outfit as dto_out
from app.backend.api.src.repositories import (
    outfit as outfits_repo,
    item as items_repo,
    wardrobe as wardrobes_repo,
    user as users_repo,
)
from app.backend.api.src.services import wardrobe as wardrobe_service
from app.backend.api.src.services import image as image_service
from app.backend.api.src.services import body as body_service
from app.backend.api.src.services.wardrobe import EDITORS


def _db(error: str, fn, *args):
    """Run a repository call, mapping driver errors to 424"""
    try:
        return fn(*args)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"{error}: {str(e)}"
        )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _get_outfit(db: Database, outfit_id: str) -> models.Outfit:
    data = _db(
        f"Error retrieving outfit {outfit_id}",
        outfits_repo.find_outfit_by_id, db, outfit_id
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outfit with id {outfit_id} not found"
        )
    return models.Outfit(**data)


def _require_edit(db: Database, outfit: models.Outfit, user_id: str) -> None:
    """Wardrobe outfits: editors and owners of the wardrobe.
    Personal outfits: their owner."""
    if outfit.wardrobe_id:
        wardrobe_service.require_role(
            wardrobe_service.get_wardrobe_by_id(db, outfit.wardrobe_id),
            user_id, EDITORS, "edit outfits"
        )
    elif outfit.owner_id != user_id:
        raise _forbidden("Only the outfit's owner can do this")


def _validate_items(
        db: Database,
        user_id: str,
        wardrobe_id: Optional[str],
        outfit_items: List[models.OutfitItem]
) -> None:
    """Every referenced item must exist, appear once, and be usable here:
    in that wardrobe for wardrobe outfits, or visible to the user
    (owned / in one of their wardrobes) for personal ones."""
    ids = [oi.item_id for oi in outfit_items]
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An item can appear only once in an outfit"
        )
    found = {
        i["_id"]: models.Item(**i)
        for i in _db("Error retrieving items", items_repo.find_items_by_ids, db, ids)
    }
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Items not found: {', '.join(missing)}"
        )
    for item in found.values():
        if wardrobe_id:
            if wardrobe_id not in item.wardrobe_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item '{item.name}' is not in this wardrobe"
                )
        elif item.owner_id != user_id and not _db(
            "Error checking item access",
            wardrobes_repo.count_wardrobes_with_member,
            db, item.wardrobe_ids, user_id
        ):
            raise _forbidden(f"You don't have access to item '{item.name}'")


def _check_body(db: Database, user_id: str, body_id, pose_id) -> None:
    """The body must be visible to the user and have that pose"""
    if not body_id:
        return
    body = body_service.get_body(db, body_id, user_id)
    if pose_id and pose_id not in body.poses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Body {body_id} has no pose '{pose_id}'"
        )


def _queue_render(db: Database, outfit: models.Outfit) -> None:
    """Dressed outfits: bump the render version and queue a 3D render
    (plan 19). The previous image stays until the new one replaces it.
    Never fails the request: a lost job just leaves the old render."""
    if not outfit.body_id:
        return
    render = outfit.render or models.OutfitRender()
    version = render.version + 1
    # the whole subdocument: `render` is null on new outfits ($set on
    # render.status would fail there)
    _db(
        f"Error queueing render for outfit {outfit.id}",
        outfits_repo.update_outfit_by_id, db, outfit.id,
        {"render": render.model_copy(update={"status": "queued", "version": version, "error": None}).model_dump()}
    )
    try:
        queue.publish(queue.RENDER_QUEUE, {"outfit_id": outfit.id, "version": version})
    except Exception:
        pass


def to_out(db: Database, outfits: List[models.Outfit]) -> List[dto_out.OutfitOut]:
    """Attach item summaries (name, categories, image URL) and the preview
    URL, with one item query and one image query for the whole list."""
    item_ids = list({oi.item_id for o in outfits for oi in o.items})
    items = [
        models.Item(**i)
        for i in _db("Error retrieving items", items_repo.find_items_by_ids, db, item_ids)
    ] if item_ids else []
    infos = image_service.image_infos(
        db,
        [i.image_asset_id for i in items if i.image_asset_id]
        + [o.image_asset_id for o in outfits if o.image_asset_id]
    )
    none = {"url": None, "plain_url": None, "size": None, "fit": None}
    refs = {
        i.id: dto_out.OutfitItemRef(
            name=i.name,
            categories=i.categories or [],
            subcategory=i.subcategory,
            image_url=infos.get(i.image_asset_id, none)["url"],
            image_size=infos.get(i.image_asset_id, none)["size"],
            fit=infos.get(i.image_asset_id, none)["fit"],
            plain_url=infos.get(i.image_asset_id, none)["plain_url"],
        )
        for i in items
    }
    return [
        dto_out.OutfitOut(
            **o.model_dump(),
            preview_url=infos.get(o.image_asset_id, none)["url"],
            render_url=s3.presigned_get(o.render.image_key) if o.render and o.render.image_key else None,
            model_url=s3.presigned_get(o.render.model_key) if o.render and o.render.model_key else None,
            item_refs={oi.item_id: refs[oi.item_id] for oi in o.items if oi.item_id in refs},
        )
        for o in outfits
    ]


def get_outfit(db: Database, outfit_id: str, user_id: str) -> models.Outfit:
    """Readable by its owner, or by any member of its wardrobe"""
    outfit = _get_outfit(db, outfit_id)
    if outfit.owner_id == user_id:
        return outfit
    if outfit.wardrobe_id:
        wardrobe_service.get_wardrobe_for_member(db, outfit.wardrobe_id, user_id)
        return outfit
    raise _forbidden("You don't have access to this outfit")


def get_visible_outfits(db: Database, user_id: str) -> List[models.Outfit]:
    """My outfits plus all outfits of wardrobes I'm a member of"""
    wardrobe_ids = [w.id for w in wardrobe_service.get_wardrobes_by_user(db, user_id)]
    data = _db(
        "Error retrieving outfits",
        outfits_repo.find_visible_outfits, db, user_id, wardrobe_ids
    )
    return [models.Outfit(**o) for o in data]


def get_feed(db: Database, user_id: str, before, limit: int) -> List[models.Outfit]:
    """Plan 08: what my friends shared (by its owner: only the owner can
    share, so it reaches the owner's friends whatever wardrobe it's in)"""
    friends = _db("Error retrieving user", users_repo.find_user_by_id, db, user_id) or {}
    data = _db(
        "Error retrieving feed",
        outfits_repo.find_shared_by, db, friends.get("friend_ids") or [], before, limit
    )
    return [models.Outfit(**o) for o in data]


def get_wardrobe_outfits(
        db: Database,
        wardrobe_id: str,
        user_id: str
) -> List[models.Outfit]:
    wardrobe_service.get_wardrobe_for_member(db, wardrobe_id, user_id)
    data = _db(
        f"Error retrieving outfits for wardrobe {wardrobe_id}",
        outfits_repo.find_outfits_by_wardrobe, db, wardrobe_id
    )
    return [models.Outfit(**o) for o in data]


def create_outfit(
        db: Database,
        user_id: str,
        request: dto_in.CreateOutfit
) -> models.Outfit:
    if request.wardrobe_id:
        wardrobe_service.require_role(
            wardrobe_service.get_wardrobe_by_id(db, request.wardrobe_id),
            user_id, EDITORS, "create outfits"
        )
    _validate_items(db, user_id, request.wardrobe_id, request.items)
    _check_body(db, user_id, request.body_id, request.pose_id)
    outfit = models.Outfit(**request.model_dump(), owner_id=user_id)
    _db("Error creating outfit", outfits_repo.insert_outfit, db, outfit)
    _queue_render(db, outfit)
    return _get_outfit(db, outfit.id)


def update_outfit(
        db: Database,
        outfit_id: str,
        user_id: str,
        request: dto_in.UpdateOutfit
) -> models.Outfit:
    outfit = _get_outfit(db, outfit_id)
    _require_edit(db, outfit, user_id)
    if request.shared is not None and request.shared != outfit.shared and outfit.owner_id != user_id:
        raise _forbidden("Only the outfit's owner can share it")
    if request.items is not None:
        _validate_items(db, user_id, outfit.wardrobe_id, request.items)
    if request.body_id or request.pose_id:
        _check_body(db, user_id, request.body_id or outfit.body_id,
                    request.pose_id or outfit.pose_id)
    update_data = request.model_dump(exclude_unset=True, exclude_none=True)
    if update_data:
        _db(
            f"Error updating outfit {outfit_id}",
            outfits_repo.update_outfit_by_id, db, outfit_id, update_data
        )
    if update_data.keys() & {"items", "body_id", "pose_id"}:  # not for a rename or (un)share
        _queue_render(db, _get_outfit(db, outfit_id))
    return _get_outfit(db, outfit_id)


def delete_outfit(db: Database, outfit_id: str, user_id: str) -> None:
    outfit = _get_outfit(db, outfit_id)
    _require_edit(db, outfit, user_id)
    _db(
        f"Error deleting outfit {outfit_id}",
        outfits_repo.delete_outfit_by_id, db, outfit_id
    )
    image_service.delete_asset(db, outfit.image_asset_id)
    for key in (outfit.render.image_key, outfit.render.model_key) if outfit.render else ():
        if key:
            try:
                s3.delete(key)
            except Exception:
                pass  # best effort, like delete_asset
