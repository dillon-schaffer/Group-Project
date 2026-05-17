import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status

from src import database as db
from src import schemas
from src.api import auth

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("", response_model=schemas.GroupCreated, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate):
    """Create a new group."""
    with db.engine.begin() as connection:
        creator = connection.execute(
            sqlalchemy.text("SELECT user_id FROM users WHERE user_id = :user_id"),
            {"user_id": group.created_by}
        ).fetchone()

        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {group.created_by} not found",
            )

        group_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO groups (name, description, created_by, created_at)
                VALUES (:name, :description, :created_by, CURRENT_TIMESTAMP)
                RETURNING group_id
                """
            ),
            {"name": group.name, "description": group.description, "created_by": group.created_by}
        ).scalar_one()

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO group_memberships (group_id, user_id, role, joined_at)
                VALUES (:group_id, :user_id, 'owner', CURRENT_TIMESTAMP)
                """
            ),
            {"group_id": group_id, "user_id": group.created_by}
        )

        return schemas.GroupCreated(group_id=group_id, owner_id=group.created_by)


@router.post("/{group_id}/members", response_model=schemas.MembershipOut, status_code=status.HTTP_201_CREATED)
def add_group_member(group_id: int, member: schemas.MemberCreate):
    """Add a member to a group."""
    with db.engine.begin() as connection:
        group = connection.execute(
            sqlalchemy.text("SELECT group_id FROM groups WHERE group_id = :group_id"),
            {"group_id": group_id}
        ).fetchone()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )

        user = connection.execute(
            sqlalchemy.text("SELECT user_id FROM users WHERE user_id = :user_id"),
            {"user_id": member.user_id}
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {member.user_id} not found",
            )

        existing = connection.execute(
            sqlalchemy.text(
                "SELECT group_id FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": member.user_id}
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {member.user_id} is already a member of group {group_id}",
            )

        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO group_memberships (group_id, user_id, role, joined_at)
                VALUES (:group_id, :user_id, 'member', CURRENT_TIMESTAMP)
                """
            ),
            {"group_id": group_id, "user_id": member.user_id}
        )

        return schemas.MembershipOut(group_id=group_id, user_id=member.user_id, role="member")


@router.patch("/{group_id}/members/{user_id}", response_model=schemas.MembershipOut)
def update_member_role(group_id: int, user_id: int, update: schemas.MemberRoleUpdate):
    """Update a group member's role."""
    with db.engine.begin() as connection:
        requester_membership = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": update.requested_by}
        ).fetchone()

        if not requester_membership or requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners can change member roles",
            )

        membership = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": user_id}
        ).fetchone()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} is not a member of group {group_id}",
            )

        if membership.role == "owner" or update.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change owner role",
            )

        connection.execute(
            sqlalchemy.text(
                """
                UPDATE group_memberships
                SET role = :role
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"role": update.role, "group_id": group_id, "user_id": user_id}
        )

        return schemas.MembershipOut(group_id=group_id, user_id=user_id, role=update.role)


@router.delete("/{group_id}/members/{user_id}", response_model=schemas.MemberRemoved)
def remove_group_member(group_id: int, user_id: int, requested_by: int):
    """Remove a member from a group."""
    with db.engine.begin() as connection:
        requester = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": requested_by}
        ).fetchone()

        if not requester or requester.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners can remove members",
            )

        target = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": user_id}
        ).fetchone()

        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} is not a member of group {group_id}",
            )

        if target.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the group owner",
            )

        connection.execute(
            sqlalchemy.text(
                "DELETE FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": user_id}
        )

        return schemas.MemberRemoved(group_id=group_id, user_id=user_id, removed=True)
