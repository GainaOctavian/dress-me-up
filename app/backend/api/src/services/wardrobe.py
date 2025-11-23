from typing import List

from starlette import status
from fastapi.exceptions import HTTPException
from pymongo.synchronous.database import Database

from app.backend.common.db import models
from app.backend.api.src.dto.input import wardrobe as dto_in
from app.backend.api.src.repositories import (
    wardrobe as wardrobes_repo,
)


def get_wardrobes(db: Database) -> List[models.Wardrobe]:
    """Get all wardrobes"""
    try:
        wardrobes_data = wardrobes_repo.find_all_wardrobes(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"Error retrieving wardrobes: {str(e)}"
        )

    wardrobes = [models.Wardrobe(**wardrobe) for wardrobe in wardrobes_data]

    return wardrobes


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


def get_wardrobes_by_user_id(
        db: Database,
        user_id: str
) -> List[models.Wardrobe]:
    """Get wardrobes by user ID"""
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


def get_wardrobes_by_user_role(
        db: Database,
        user_id: str,
        role: str
) -> List[models.Wardrobe]:
    """Get wardrobes by user role"""
    try:
        models.WardrobeRole(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role}."
                   f" Must be one of {[r.value for r in models.WardrobeRole]}"
        )
    try:
        wardrobes_data = wardrobes_repo.find_wardrobes_by_user_role(
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

    wardrobes = [models.Wardrobe(**wardrobe) for wardrobe in wardrobes_data]

    return wardrobes


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

        # Ensure requester is OWNER in current roles mapping
        if existing_wardrobe.roles.get(user_id) != models.WardrobeRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an OWNER can modify roles"
            )

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
