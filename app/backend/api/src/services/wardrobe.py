from typing import List, Optional

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.api.src.dto.input import wardrobe as dto_in
from app.backend.api.src.repositories import (
    wardrobe as wardrobes_repo,
    user as users_repo
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


def get_owned_wardrobes_by_user_id(
        db: Database,
        user_id: str
) -> List[models.Wardrobe]:
    """Get owned wardrobes by user ID"""
    try:
        wardrobes_data = wardrobes_repo.find_wardrobes_by_user_id(db, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error retrieving wardrobes"
                   f" for user with id {user_id}: {str(e)}"
        )

    wardrobes = [models.Wardrobe(**wardrobe) for wardrobe in wardrobes_data]

    return wardrobes


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
    if 'roles' in update_data:
        requested_roles = update_data.pop('roles') or {}

        validated_roles = {}
        for uid, r in requested_roles.items():
            # Accept either enum member or raw value; validate against enum
            try:
                validated_role = r if isinstance(r, models.WardrobeRole) else models.WardrobeRole(r)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role '{r}' for user '{uid}'"
                )

            # Prevent owner from removing/demoting their own OWNER role
            if uid == user_id and validated_role != models.WardrobeRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Owner cannot remove their OWNER role"
                )

            validated_roles[uid] = validated_role

        update_data['roles'] = validated_roles
    try:
        wardrobes_repo.update_wardrobe_by_id(db, wardrobe_id, update_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error updating wardrobe with id {wardrobe_id}: {str(e)}"
        )

    return get_wardrobe_by_id(db, wardrobe_id)


def _require_owner(wardrobe: models.Wardrobe, user_id: str) -> None:
    """Raise 403 unless user_id is an OWNER of the wardrobe"""
    if wardrobe.roles.get(user_id) != models.WardrobeRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can modify roles"
        )


def _set_member_role(
        db: Database,
        wardrobe_id: str,
        requester_id: str,
        member_id: str,
        role: Optional[models.WardrobeRole]
) -> models.Wardrobe:
    """Set (role) or remove (role=None) a member's role. Requester must be OWNER
    and cannot change their own role, so a wardrobe always keeps its owner."""
    _require_owner(get_wardrobe_by_id(db, wardrobe_id), requester_id)
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error deleting wardrobe with id {wardrobe_id}: {str(e)}"
        )
