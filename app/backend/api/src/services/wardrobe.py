from typing import Dict, List, Optional

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.api.src.dto.input import wardrobe as dto_in
from app.backend.api.src.repositories import (
    wardrobe as wardrobes_repo,
    user as users_repo,
    item as items_repo
)

OWNER_ONLY = {models.WardrobeRole.OWNER}
EDITORS = {models.WardrobeRole.OWNER, models.WardrobeRole.EDITOR}


def require_role(
        wardrobe: models.Wardrobe,
        user_id: str,
        allowed: set,
        action: str = "do this"
) -> None:
    """Raise 403 unless user_id has one of the allowed roles in the wardrobe"""
    if wardrobe.roles.get(user_id) not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {action} in this wardrobe"
        )


def get_wardrobe_by_id(db: Database, wardrobe_id: str) -> models.Wardrobe:
    """Get wardrobe by ID"""
    try:
        wardrobe_data = wardrobes_repo.find_wardrobe_by_id(db, wardrobe_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error retrieving wardrobe with id {wardrobe_id}: {str(e)}"
        )

    if not wardrobe_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wardrobe with id {wardrobe_id} not found"
        )

    wardrobe = models.Wardrobe(**wardrobe_data)

    return wardrobe


def get_wardrobe_for_member(
        db: Database,
        wardrobe_id: str,
        user_id: str
) -> models.Wardrobe:
    """Get wardrobe by ID if the user has any role in it"""
    wardrobe = get_wardrobe_by_id(db, wardrobe_id)
    if user_id not in wardrobe.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this wardrobe"
        )
    return wardrobe


def get_wardrobes_by_user(
        db: Database,
        user_id: str,
        role: Optional[models.WardrobeRole] = None
) -> List[models.Wardrobe]:
    """Get wardrobes by user, optionally filtered by role"""
    try:
        wardrobes_data = wardrobes_repo.find_wardrobes_by_user(
            db,
            user_id,
            role
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error retrieving wardrobes"
                   f" for user with id {user_id} and role {role}: {str(e)}"
        )

    return [models.Wardrobe(**wardrobe) for wardrobe in wardrobes_data]


def get_item_counts(
        db: Database,
        wardrobes: List[models.Wardrobe]
) -> Dict[str, int]:
    """Number of items per wardrobe.
    ponytail: one count per wardrobe; use an $unwind/$group aggregate
    if users end up with many wardrobes."""
    try:
        return {
            w.id: items_repo.count_items_in_wardrobe(db, w.id)
            for w in wardrobes
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error counting wardrobe items: {str(e)}"
        )


def leave_wardrobe(db: Database, wardrobe_id: str, user_id: str) -> None:
    """Remove the caller's own role. The last owner can't leave, so a
    wardrobe always keeps an owner (they can delete it instead)."""
    wardrobe = get_wardrobe_for_member(db, wardrobe_id, user_id)
    owners = [
        uid for uid, r in wardrobe.roles.items()
        if r == models.WardrobeRole.OWNER
    ]
    if owners == [user_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You're the only owner. Make another member owner"
                   " or delete the wardrobe instead."
        )
    try:
        wardrobes_repo.unset_wardrobe_role(db, wardrobe_id, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error leaving wardrobe {wardrobe_id}: {str(e)}"
        )


def create_wardrobe(
        db: Database,
        user_id: str,
        request: dto_in.CreateWardrobe
) -> models.Wardrobe:
    """Create a new wardrobe"""
    wardrobe_data = request.model_dump()
    wardrobe_data['user_id'] = user_id
    wardrobe_data['roles'] = {user_id: models.WardrobeRole.OWNER}
    wardrobe = models.Wardrobe(**wardrobe_data)

    try:
        wardrobes_repo.insert_wardrobe(db, wardrobe)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error creating wardrobe: {str(e)}"
        )

    return wardrobe


def update_wardrobe(
        db: Database,
        wardrobe_id: str,
        user_id: str,
        request: dto_in.UpdateWardrobe
) -> models.Wardrobe:
    """Update wardrobe information"""
    update_data = request.model_dump(exclude_unset=True)
    existing_wardrobe = get_wardrobe_by_id(db, wardrobe_id)
    if existing_wardrobe.roles.get(user_id) != models.WardrobeRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update the wardrobe"
        )
    try:
        if update_data:  # Mongo rejects an empty $set
            wardrobes_repo.update_wardrobe_by_id(db, wardrobe_id, update_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error updating wardrobe with id {wardrobe_id}: {str(e)}"
        )

    return get_wardrobe_by_id(db, wardrobe_id)


def _set_member_role(
        db: Database,
        wardrobe_id: str,
        requester_id: str,
        member_id: str,
        role: Optional[models.WardrobeRole]
) -> models.Wardrobe:
    """Set (role) or remove (role=None) a member's role. Requester must be OWNER
    and cannot change their own role, so a wardrobe always keeps its owner."""
    require_role(
        get_wardrobe_by_id(db, wardrobe_id), requester_id, OWNER_ONLY,
        "modify roles"
    )
    if member_id == requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner cannot change their own role"
        )
    try:
        if role is None:
            wardrobes_repo.unset_wardrobe_role(db, wardrobe_id, member_id)
        else:
            wardrobes_repo.update_wardrobe_by_id(
                db, wardrobe_id, {f"roles.{member_id}": role}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error updating role for user {member_id}"
                   f" in wardrobe {wardrobe_id}: {str(e)}"
        )
    return get_wardrobe_by_id(db, wardrobe_id)


def add_user_to_wardrobe(
        db: Database,
        wardrobe_id: str,
        user_id: str,
        request: dto_in.AddUserToWardrobe
) -> models.Wardrobe:
    """Add or update a user's role in a wardrobe"""
    if not users_repo.find_user_by_id(db, request.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {request.user_id} not found"
        )
    return _set_member_role(
        db, wardrobe_id, user_id, request.user_id, request.role
    )


def add_user_by_email_to_wardrobe(
        db: Database,
        wardrobe_id: str,
        user_id: str,
        request: dto_in.AddUserByEmailToWardrobe
) -> models.Wardrobe:
    """Add a user to a wardrobe by email with a specific role"""
    target_user = users_repo.find_user_by_email(db, str(request.email))
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {request.email} not found"
        )
    return _set_member_role(
        db, wardrobe_id, user_id, target_user["_id"], request.role
    )


def remove_user_from_wardrobe(
        db: Database,
        wardrobe_id: str,
        user_id: str,
        member_id: str
) -> models.Wardrobe:
    """Remove a user's role from a wardrobe"""
    return _set_member_role(db, wardrobe_id, user_id, member_id, None)


def delete_wardrobe(db: Database, wardrobe_id: str, user_id: str) -> None:
    """Delete a wardrobe by ID"""
    existing_wardrobe = get_wardrobe_by_id(db, wardrobe_id)
    if existing_wardrobe.roles.get(user_id) != models.WardrobeRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete the wardrobe"
        )
    try:
        wardrobes_repo.delete_wardrobe_by_id(db, wardrobe_id)
        # items survive their wardrobe; just drop the reference
        items_repo.pull_wardrobe_from_items(db, wardrobe_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error deleting wardrobe with id {wardrobe_id}: {str(e)}"
        )
