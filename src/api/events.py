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


@router.get("/{group_id}/events/{event_id}", response_model=schemas.EventDetails)
def get_event(group_id: int, event_id: int):
    """Get details for a specific event."""
    with db.engine.begin() as connection:
        event = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    e.event_id,
                    e.group_id,
                    g.name as group_name,
                    e.title,
                    e.location,
                    e.start_time,
                    e.end_time,
                    e.capacity,
                    e.status,
                    e.created_by,
                    u.name as creator_name,
                    e.created_at,
                    COUNT(CASE WHEN r.status = 'going' THEN 1 END) as going_count
                FROM events e
                JOIN groups g ON e.group_id = g.group_id
                JOIN users u ON e.created_by = u.user_id
                LEFT JOIN rsvps r ON e.event_id = r.event_id
                WHERE e.event_id = :event_id AND e.group_id = :group_id
                GROUP BY e.event_id, e.group_id, g.name, e.title, e.location,
                         e.start_time, e.end_time, e.capacity, e.status, 
                         e.created_by, u.name, e.created_at
                """
            ),
            {"event_id": event_id, "group_id": group_id}
        ).fetchone()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found in group {group_id}",
            )

        return schemas.EventDetails(
            event_id=event.event_id,
            group_id=event.group_id,
            group_name=event.group_name,
            title=event.title,
            location=event.location,
            start_time=event.start_time,
            end_time=event.end_time,
            capacity=event.capacity,
            status=event.status,
            created_by=event.created_by,
            creator_name=event.creator_name,
            going_count=event.going_count,
            created_at=event.created_at
        )


@router.patch("/{group_id}/events/{event_id}", response_model=schemas.EventUpdated)
def update_event(group_id: int, event_id: int, update: schemas.EventUpdate):
    """Update an event's details (owner and organizer only)."""
    with db.engine.begin() as connection:
        # Check if requester has permission
        membership = connection.execute(
            sqlalchemy.text(
                "SELECT role FROM group_memberships WHERE group_id = :group_id AND user_id = :user_id"
            ),
            {"group_id": group_id, "user_id": update.requested_by}
        ).fetchone()

        if not membership or membership.role not in ("owner", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners and organizers can update events",
            )

        # Check if event exists
        event = connection.execute(
            sqlalchemy.text(
                "SELECT event_id, title, location, start_time, end_time, capacity, status FROM events WHERE event_id = :event_id AND group_id = :group_id"
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
                detail="Cannot update a cancelled event",
            )

        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"event_id": event_id}
        
        if update.title is not None:
            update_fields.append("title = :title")
            params["title"] = update.title
        
        if update.location is not None:
            update_fields.append("location = :location")
            params["location"] = update.location
        
        if update.start_time is not None:
            update_fields.append("start_time = :start_time")
            params["start_time"] = update.start_time
        
        if update.end_time is not None:
            update_fields.append("end_time = :end_time")
            params["end_time"] = update.end_time
        
        if update.capacity is not None:
            update_fields.append("capacity = :capacity")
            params["capacity"] = update.capacity

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        # Validate times if either is being updated
        final_start = update.start_time if update.start_time is not None else event.start_time
        final_end = update.end_time if update.end_time is not None else event.end_time
        
        if final_end <= final_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after start time",
            )

        # Execute update
        connection.execute(
            sqlalchemy.text(f"UPDATE events SET {', '.join(update_fields)} WHERE event_id = :event_id"),
            params
        )

        return schemas.EventUpdated(
            event_id=event_id,
            group_id=group_id,
            message="Event updated successfully"
        )


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

        if not requester or requester.role not in ("owner", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners and organizers can cancel events",
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
