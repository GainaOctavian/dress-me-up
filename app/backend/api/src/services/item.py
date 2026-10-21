from typing import List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common import layering
from app.backend.common.db import models
from app.backend.api.src.dto.input import item as dto_in
from app.backend.api.src.repositories import (
    item as items_repo,
    wardrobe as wardrobes_repo,
    outfit as outfits_repo,
)
from app.backend.api.src.services import wardrobe as wardrobe_service
from app.backend.api.src.services import image as image_service
from app.backend.api.src.dto.output import item as dto_out
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


def _get_item(db: Database, item_id: str) -> models.Item:
    data = _db(
        f"Error retrieving item with id {item_id}",
        items_repo.find_item_by_id, db, item_id
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    return models.Item(**data)


def _require_item_owner(item: models.Item, user_id: str) -> None:
    if item.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the item's owner can do this"
        )


def to_out(db: Database, items: List[models.Item]) -> List[dto_out.ItemOut]:
    """Attach presigned image URLs (one asset lookup for the whole list)"""
    asset_ids = [i.image_asset_id for i in items if i.image_asset_id]
    urls = image_service.image_urls(db, asset_ids)
    statuses = image_service.image_statuses(db, asset_ids)
    return [
        dto_out.ItemOut(
            **i.model_dump(),
            image_url=urls.get(i.image_asset_id),
            image_status=statuses.get(i.image_asset_id),
        )
        for i in items
    ]


def get_item(db: Database, item_id: str, user_id: str) -> models.Item:
    """Get an item if the user owns it or is a member of one of its wardrobes"""
    item = _get_item(db, item_id)
    if item.owner_id != user_id and not _db(
        "Error checking item access",
        wardrobes_repo.count_wardrobes_with_member,
        db, item.wardrobe_ids, user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this item"
        )
    return item


def get_items_by_owner(db: Database, user_id: str) -> List[models.Item]:
    """Get all items owned by the user"""
    data = _db(
        f"Error retrieving items for user {user_id}",
        items_repo.find_items_by_owner, db, user_id
    )
    return [models.Item(**item) for item in data]


def get_wardrobe_items(
        db: Database,
        wardrobe_id: str,
        user_id: str
) -> List[models.Item]:
    """Get items in a wardrobe (any member)"""
    wardrobe_service.get_wardrobe_for_member(db, wardrobe_id, user_id)
    data = _db(
        f"Error retrieving items for wardrobe {wardrobe_id}",
        items_repo.find_items_by_wardrobe, db, wardrobe_id
    )
    return [models.Item(**item) for item in data]


def _consistent_categories(subcategory, categories: list) -> list:
    """A subcategory belongs to one category: fill it in when the item has
    none, reject a contradiction (e.g. "blazer" on a "bottom")."""
    if not subcategory:
        return categories
    category = layering.SUBCATEGORIES[subcategory].category
    if not categories:
        return [category]
    if category not in categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type '{subcategory}' belongs to category '{category}'"
        )
    return categories


def create_item(
        db: Database,
        user_id: str,
        request: dto_in.CreateItem
) -> models.Item:
    """Create an item owned by the user, optionally in wardrobes they can edit"""
    wardrobe_ids = list(dict.fromkeys(request.wardrobe_ids))  # dedupe, keep order
    for wardrobe_id in wardrobe_ids:
        wardrobe_service.require_role(
            wardrobe_service.get_wardrobe_by_id(db, wardrobe_id),
            user_id, EDITORS, "add items"
        )
    if request.image_asset_id:
        image_service.claim_uploaded_asset(db, request.image_asset_id, user_id)
    data = request.model_dump(exclude={"wardrobe_ids"})
    data["categories"] = _consistent_categories(request.subcategory, data["categories"])
    item = models.Item(**data, owner_id=user_id, wardrobe_ids=wardrobe_ids)
    _db("Error creating item", items_repo.insert_item, db, item)
    return item


def update_item(
        db: Database,
        item_id: str,
        user_id: str,
        request: dto_in.UpdateItem
) -> models.Item:
    """Update an item (owner only). A new image_asset_id replaces the old
    image, which is then deleted."""
    item = _get_item(db, item_id)
    _require_item_owner(item, user_id)
    update_data = request.model_dump(exclude_unset=True, exclude_none=True)
    if "subcategory" in update_data or "categories" in update_data:
        cats = _consistent_categories(
            update_data.get("subcategory", item.subcategory),
            update_data.get("categories", item.categories or []),
        )
        if cats != (item.categories or []) or "categories" in update_data:
            update_data["categories"] = cats
    new_image = update_data.get("image_asset_id")
    if new_image and new_image != item.image_asset_id:
        image_service.claim_uploaded_asset(db, new_image, user_id)
    if update_data:
        _db(
            f"Error updating item with id {item_id}",
            items_repo.update_item_by_id, db, item_id, update_data
        )
    if new_image and new_image != item.image_asset_id:
        image_service.delete_asset(db, item.image_asset_id)
    return _get_item(db, item_id)


def add_item_to_wardrobe(
        db: Database,
        wardrobe_id: str,
        item_id: str,
        user_id: str
) -> models.Item:
    """Put one of the user's items into a wardrobe they can edit"""
    wardrobe_service.require_role(
        wardrobe_service.get_wardrobe_by_id(db, wardrobe_id),
        user_id, EDITORS, "add items"
    )
    # owner only: otherwise an editor could expose someone else's item
    # to a wardrobe its owner never shared it with
    _require_item_owner(_get_item(db, item_id), user_id)
    _db(
        f"Error adding item {item_id} to wardrobe {wardrobe_id}",
        items_repo.add_item_to_wardrobe, db, item_id, wardrobe_id
    )
    return _get_item(db, item_id)


def remove_item_from_wardrobe(
        db: Database,
        wardrobe_id: str,
        item_id: str,
        user_id: str
) -> models.Item:
    """Take an item out of a wardrobe (wardrobe editors or the item's owner).
    The item itself is kept."""
    wardrobe = wardrobe_service.get_wardrobe_by_id(db, wardrobe_id)
    item = _get_item(db, item_id)
    if item.owner_id != user_id:
        wardrobe_service.require_role(wardrobe, user_id, EDITORS, "remove items")
    _db(
        f"Error removing item {item_id} from wardrobe {wardrobe_id}",
        items_repo.remove_item_from_wardrobe, db, item_id, wardrobe_id
    )
    # that wardrobe's outfits can't use it anymore
    _db(
        "Error updating outfits",
        outfits_repo.pull_item_from_outfits, db, item_id, wardrobe_id
    )
    return _get_item(db, item_id)


def delete_item(db: Database, item_id: str, user_id: str) -> None:
    """Delete an item (owner only), and its image"""
    item = _get_item(db, item_id)
    _require_item_owner(item, user_id)
    _db(
        f"Error deleting item with id {item_id}",
        items_repo.delete_item_by_id, db, item_id
    )
    _db("Error updating outfits", outfits_repo.pull_item_from_outfits, db, item_id)
    image_service.delete_asset(db, item.image_asset_id)
