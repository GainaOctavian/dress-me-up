from typing import List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.api.src.dto.input import item as dto_in
from app.backend.api.src.repositories import (
    item as items_repo,
    wardrobe as wardrobes_repo,
)
from app.backend.api.src.services import wardrobe as wardrobe_service
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
    item = models.Item(
        **request.model_dump(exclude={"wardrobe_ids"}),
        owner_id=user_id,
        wardrobe_ids=wardrobe_ids,
    )
    _db("Error creating item", items_repo.insert_item, db, item)
    return item


def update_item(
        db: Database,
        item_id: str,
        user_id: str,
        request: dto_in.UpdateItem
) -> models.Item:
    """Update an item (owner only)"""
    _require_item_owner(_get_item(db, item_id), user_id)
    update_data = request.model_dump(exclude_unset=True, exclude_none=True)
    if update_data:
        _db(
            f"Error updating item with id {item_id}",
            items_repo.update_item_by_id, db, item_id, update_data
        )
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
    return _get_item(db, item_id)


def delete_item(db: Database, item_id: str, user_id: str) -> None:
    """Delete an item (owner only)"""
    _require_item_owner(_get_item(db, item_id), user_id)
    _db(
        f"Error deleting item with id {item_id}",
        items_repo.delete_item_by_id, db, item_id
    )
