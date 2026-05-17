import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status

from src import database as db
from src import schemas
from src.api import auth

router = APIRouter(
    prefix="/groups",
    tags=["events"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/{group_id}/events", response_model=schemas.EventCreated, status_code=status.HTTP_201_CREATED)
def create_event(group_id: int, event: schemas.EventCreate):
    """Create a new event in a group."""
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


@router.delete("/{group_id}/events/{event_id}", response_model=schemas.EventCancelled)
def cancel_event(group_id: int, event_id: int, requested_by: int):
    """Cancel an event."""
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
