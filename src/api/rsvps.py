import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status

from src import database as db
from src import schemas
from src.api import auth

router = APIRouter(
    prefix="/events",
    tags=["rsvps"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/{event_id}/rsvp", response_model=schemas.RsvpOut)
def create_or_update_rsvp(event_id: int, rsvp: schemas.RsvpCreate):
    """Create or update an RSVP for an event."""
    with db.engine.begin() as connection:
        # Lock the event row to prevent race conditions in capacity checking
        event = connection.execute(
            sqlalchemy.text("SELECT event_id, group_id, status, capacity FROM events WHERE event_id = :event_id FOR UPDATE"),
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
                "SELECT event_id, status FROM rsvps WHERE event_id = :event_id AND user_id = :user_id"
            ),
            {"event_id": event_id, "user_id": rsvp.user_id}
        ).fetchone()

        # Only block transitions that would add one more attendee.
        if rsvp.status == "going" and (not existing_rsvp or existing_rsvp.status != "going"):
            going_count = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT COUNT(*)
                    FROM rsvps
                    WHERE event_id = :event_id
                      AND status = 'going'
                    """
                ),
                {"event_id": event_id}
            ).scalar_one()

            if going_count >= event.capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Event is at full capacity ({event.capacity} attendees)",
                )

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


@router.get("/{event_id}/rsvps", response_model=schemas.EventRsvpSummary)
def get_event_rsvps(event_id: int, requested_by: int, limit: int = 100, offset: int = 0):
    """Get all RSVPs for an event (owners and organizers only)."""
    # Validate pagination parameters
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative",
        )
    
    with db.engine.begin() as connection:
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

        # Get aggregate RSVP counts in SQL (unpaginated)
        counts_row = connection.execute(
            sqlalchemy.text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE r.status = 'going') AS going_count,
                    COUNT(*) FILTER (WHERE r.status = 'maybe') AS maybe_count,
                    COUNT(*) FILTER (WHERE r.status = 'not going') AS not_going_count
                FROM rsvps r
                WHERE r.event_id = :event_id
                """
            ),
            {"event_id": event_id}
        ).fetchone()

        going_count = counts_row.going_count or 0
        maybe_count = counts_row.maybe_count or 0
        not_going_count = counts_row.not_going_count or 0

        # Get paginated RSVP details
        rsvp_rows = connection.execute(
            sqlalchemy.text(
                """
                SELECT r.user_id, u.name, r.status
                FROM rsvps r
                JOIN users u ON u.user_id = r.user_id
                WHERE r.event_id = :event_id
                ORDER BY r.updated_at
                LIMIT :limit OFFSET :offset
                """
            ),
            {"event_id": event_id, "limit": limit, "offset": offset}
        ).fetchall()

        rsvps = [
            schemas.RsvpListItem(user_id=row.user_id, name=row.name, status=row.status)
            for row in rsvp_rows
        ]

        return schemas.EventRsvpSummary(
            event_id=event_id,
            title=event.title,
            capacity=event.capacity,
            going_count=going_count,
            maybe_count=maybe_count,
            not_going_count=not_going_count,
            rsvps=rsvps,
        )
