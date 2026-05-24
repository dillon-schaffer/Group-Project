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


@router.get("/{group_id}/analytics", response_model=schemas.GroupAnalytics)
def get_group_analytics(group_id: int, requested_by: int):
    """
    Get comprehensive analytics for a group.
    
    Returns:
    - Member statistics by role
    - Event statistics (total, active, cancelled, past, future)
    - Average RSVP rate across all events
    - Most active members (by events created and RSVPs made)
    
    Only accessible by group members.
    """
    with db.engine.begin() as connection:
        # Check if group exists
        group = connection.execute(
            sqlalchemy.text("SELECT group_id, name FROM groups WHERE group_id = :group_id"),
            {"group_id": group_id}
        ).fetchone()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )

        # Verify requester is a member
        membership = connection.execute(
            sqlalchemy.text(
                "SELECT user_id FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": requested_by}
        ).fetchone()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group members can view analytics",
            )

        # Get member counts by role
        member_stats = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    COUNT(*) as total_members,
                    COUNT(CASE WHEN role = 'owner' THEN 1 END) as owners_count,
                    COUNT(CASE WHEN role = 'organizer' THEN 1 END) as organizers_count,
                    COUNT(CASE WHEN role = 'member' THEN 1 END) as members_count
                FROM group_memberships
                WHERE group_id = :group_id
                """
            ),
            {"group_id": group_id}
        ).fetchone()

        # Get event statistics
        event_stats = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_events,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_events,
                    COUNT(CASE WHEN start_time < CURRENT_TIMESTAMP THEN 1 END) as past_events,
                    COUNT(CASE WHEN start_time >= CURRENT_TIMESTAMP THEN 1 END) as future_events
                FROM events
                WHERE group_id = :group_id
                """
            ),
            {"group_id": group_id}
        ).fetchone()

        # Calculate average RSVP rate
        # RSVP rate = (total RSVPs) / (total events * total members)
        rsvp_rate_data = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    COUNT(DISTINCT e.event_id) as event_count,
                    COUNT(DISTINCT gm.user_id) as member_count,
                    COUNT(r.event_id) as total_rsvps
                FROM events e
                CROSS JOIN group_memberships gm
                LEFT JOIN rsvps r ON e.event_id = r.event_id AND r.user_id = gm.user_id
                WHERE e.group_id = :group_id
                  AND gm.group_id = :group_id
                  AND e.status = 'active'
                """
            ),
            {"group_id": group_id}
        ).fetchone()

        # Calculate average RSVP rate (avoid division by zero)
        if rsvp_rate_data.event_count > 0 and rsvp_rate_data.member_count > 0:
            possible_rsvps = rsvp_rate_data.event_count * rsvp_rate_data.member_count
            average_rsvp_rate = (rsvp_rate_data.total_rsvps / possible_rsvps) * 100
        else:
            average_rsvp_rate = 0.0

        # Get most active members
        active_members = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    u.user_id,
                    u.name,
                    gm.role,
                    COUNT(DISTINCT e.event_id) as events_created,
                    COUNT(DISTINCT r.event_id) as rsvps_made
                FROM users u
                JOIN group_memberships gm ON u.user_id = gm.user_id
                LEFT JOIN events e ON u.user_id = e.created_by AND e.group_id = :group_id
                LEFT JOIN rsvps r ON u.user_id = r.user_id 
                    AND r.event_id IN (SELECT event_id FROM events WHERE group_id = :group_id)
                WHERE gm.group_id = :group_id
                GROUP BY u.user_id, u.name, gm.role
                ORDER BY (COUNT(DISTINCT e.event_id) + COUNT(DISTINCT r.event_id)) DESC
                LIMIT 5
                """
            ),
            {"group_id": group_id}
        ).fetchall()

        most_active = [
            schemas.MemberActivityItem(
                user_id=row.user_id,
                name=row.name,
                role=row.role,
                events_created=row.events_created,
                rsvps_made=row.rsvps_made
            )
            for row in active_members
        ]

        return schemas.GroupAnalytics(
            group_id=group_id,
            group_name=group.name,
            total_members=member_stats.total_members,
            owners_count=member_stats.owners_count,
            organizers_count=member_stats.organizers_count,
            members_count=member_stats.members_count,
            total_events=event_stats.total_events,
            active_events=event_stats.active_events,
            cancelled_events=event_stats.cancelled_events,
            past_events=event_stats.past_events,
            future_events=event_stats.future_events,
            average_rsvp_rate=round(average_rsvp_rate, 2),
            most_active_members=most_active
        )
