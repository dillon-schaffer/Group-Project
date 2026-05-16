import os

import bcrypt
import sqlalchemy
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader

import schemas
from database import engine

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Verify the API key from the X-API-Key header."""
    server_api_key = os.getenv("API_KEY")
    
    if not server_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY is not configured",
        )
    
    if not api_key or api_key != server_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    
    return api_key


app = FastAPI(
    title="Event & Group Coordination API",
    description="API for managing groups, events, and RSVPs",
    version="2.0.0",
    dependencies=[Security(verify_api_key)],
)


@app.get("/", dependencies=[])
def root():
    return {"status": "healthy", "message": "Event & Group Coordination API"}


@app.post("/users", response_model=schemas.UserCreated, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate):
    password_hash = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with engine.begin() as connection:
        existing_user = connection.execute(
            sqlalchemy.text("SELECT user_id FROM users WHERE email = :email"),
            {"email": user.email}
        ).fetchone()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        user_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO users (name, email, password_hash, created_at)
                VALUES (:name, :email, :password_hash, CURRENT_TIMESTAMP)
                RETURNING user_id
                """
            ),
            {"name": user.name, "email": user.email, "password_hash": password_hash}
        ).scalar_one()

        return schemas.UserCreated(user_id=user_id)


@app.post("/groups", response_model=schemas.GroupCreated, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate):
    with engine.begin() as connection:
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


@app.post("/groups/{group_id}/members", response_model=schemas.MembershipOut, status_code=status.HTTP_201_CREATED)
def add_group_member(group_id: int, member: schemas.MemberCreate):
    with engine.begin() as connection:
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


@app.patch("/groups/{group_id}/members/{user_id}", response_model=schemas.MembershipOut)
def update_member_role(group_id: int, user_id: int, update: schemas.MemberRoleUpdate):
    with engine.begin() as connection:
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


@app.delete("/groups/{group_id}/members/{user_id}", response_model=schemas.MemberRemoved)
def remove_group_member(group_id: int, user_id: int, requested_by: int):
    with engine.begin() as connection:
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


@app.post("/groups/{group_id}/events", response_model=schemas.EventCreated, status_code=status.HTTP_201_CREATED)
def create_event(group_id: int, event: schemas.EventCreate):
    with engine.begin() as connection:
        group = connection.execute(
            sqlalchemy.text("SELECT group_id FROM groups WHERE group_id = :group_id"),
            {"group_id": group_id}
        ).fetchone()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )

        membership = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": event.created_by}
        ).fetchone()

        if not membership or membership.role not in ("owner", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners and organizers can create events",
            )

        if event.end_time <= event.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after start time",
            )

        event_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO events (
                    group_id, created_by, title, location,
                    start_time, end_time, capacity, status, created_at
                )
                VALUES (
                    :group_id, :created_by, :title, :location,
                    :start_time, :end_time, :capacity, 'active', CURRENT_TIMESTAMP
                )
                RETURNING event_id
                """
            ),
            {
                "group_id": group_id,
                "created_by": event.created_by,
                "title": event.title,
                "location": event.location,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "capacity": event.capacity,
            }
        ).scalar_one()

        return schemas.EventCreated(event_id=event_id, group_id=group_id, capacity=event.capacity)


@app.delete("/groups/{group_id}/events/{event_id}", response_model=schemas.EventCancelled)
def cancel_event(group_id: int, event_id: int, requested_by: int):
    with engine.begin() as connection:
        requester = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": requested_by}
        ).fetchone()

        if not requester or requester.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners can cancel events",
            )

        event = connection.execute(
            sqlalchemy.text(
                "SELECT event_id, status FROM events WHERE event_id = :event_id AND group_id = :group_id"
            ),
            {"event_id": event_id, "group_id": group_id}
        ).fetchone()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found in group {group_id}",
            )

        if event.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is already cancelled",
            )

        connection.execute(
            sqlalchemy.text(
                "UPDATE events SET status = 'cancelled' WHERE event_id = :event_id"
            ),
            {"event_id": event_id}
        )

        return schemas.EventCancelled(event_id=event_id, group_id=group_id, status="cancelled")


@app.post("/events/{event_id}/rsvp", response_model=schemas.RsvpOut)
def create_or_update_rsvp(event_id: int, rsvp: schemas.RsvpCreate):
    with engine.begin() as connection:
        event = connection.execute(
            sqlalchemy.text("SELECT group_id, status FROM events WHERE event_id = :event_id"),
            {"event_id": event_id}
        ).fetchone()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found",
            )

        if event.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot RSVP to a cancelled event",
            )

        membership = connection.execute(
            sqlalchemy.text(
                "SELECT user_id FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": event.group_id, "user_id": rsvp.user_id}
        ).fetchone()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group members can RSVP to events",
            )

        existing_rsvp = connection.execute(
            sqlalchemy.text(
                "SELECT event_id FROM rsvps WHERE event_id = :event_id AND user_id = :user_id"
            ),
            {"event_id": event_id, "user_id": rsvp.user_id}
        ).fetchone()

        if existing_rsvp:
            connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE rsvps
                    SET status = :status, updated_at = CURRENT_TIMESTAMP
                    WHERE event_id = :event_id AND user_id = :user_id
                    """
                ),
                {"status": rsvp.status, "event_id": event_id, "user_id": rsvp.user_id}
            )
        else:
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO rsvps (event_id, user_id, status, updated_at)
                    VALUES (:event_id, :user_id, :status, CURRENT_TIMESTAMP)
                    """
                ),
                {"event_id": event_id, "user_id": rsvp.user_id, "status": rsvp.status}
            )

        return schemas.RsvpOut(event_id=event_id, user_id=rsvp.user_id, status=rsvp.status)


@app.get("/events/{event_id}/rsvps", response_model=schemas.EventRsvpSummary)
def get_event_rsvps(event_id: int, requested_by: int):
    with engine.begin() as connection:
        event = connection.execute(
            sqlalchemy.text(
                "SELECT event_id, group_id, title, capacity, status FROM events WHERE event_id = :event_id"
            ),
            {"event_id": event_id}
        ).fetchone()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found",
            )

        membership = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": event.group_id, "user_id": requested_by}
        ).fetchone()

        if not membership or membership.role not in ("owner", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners and organizers can view the RSVP list",
            )

        rsvp_rows = connection.execute(
            sqlalchemy.text(
                """
                SELECT r.user_id, u.name, r.status
                FROM rsvps r
                JOIN users u ON u.user_id = r.user_id
                WHERE r.event_id = :event_id
                ORDER BY r.updated_at
                """
            ),
            {"event_id": event_id}
        ).fetchall()

        rsvps = [
            schemas.RsvpListItem(user_id=row.user_id, name=row.name, status=row.status)
            for row in rsvp_rows
        ]

        going_count = sum(1 for r in rsvps if r.status == "going")
        maybe_count = sum(1 for r in rsvps if r.status == "maybe")
        not_going_count = sum(1 for r in rsvps if r.status == "not going")

        return schemas.EventRsvpSummary(
            event_id=event_id,
            title=event.title,
            capacity=event.capacity,
            going_count=going_count,
            maybe_count=maybe_count,
            not_going_count=not_going_count,
            rsvps=rsvps,
        )