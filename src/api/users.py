import bcrypt
import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, status

from src import database as db
from src import schemas
from src.api import auth

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("", response_model=schemas.UserCreated, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate):
    """
    Create a new user account.
    
    The password will be securely hashed before storage.
    """
    password_hash = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with db.engine.begin() as connection:
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

@router.get("/{user_id}", response_model=schemas.UserProfile)
def get_user(user_id: int):
    """Get a user's profile information."""
    with db.engine.begin() as connection:
        user = connection.execute(
            sqlalchemy.text(
                """
                SELECT user_id, name, email, created_at
                FROM users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id}
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        return schemas.UserProfile(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            created_at=user.created_at
        )


@router.get("/{user_id}/events", response_model=list[schemas.UserEventOut])
def get_user_events(user_id: int):
    """Get all events a user has RSVP'd to."""
    with db.engine.begin() as connection:
        # Check if user exists
        user = connection.execute(
            sqlalchemy.text("SELECT user_id FROM users WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        # Get all events user has RSVP'd to
        events = connection.execute(
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
                    r.status as rsvp_status
                FROM events e
                JOIN groups g ON e.group_id = g.group_id
                JOIN rsvps r ON e.event_id = r.event_id
                WHERE r.user_id = :user_id
                ORDER BY e.start_time DESC
                """
            ),
            {"user_id": user_id}
        ).fetchall()

        return [
            schemas.UserEventOut(
                event_id=row.event_id,
                group_id=row.group_id,
                group_name=row.group_name,
                title=row.title,
                location=row.location,
                start_time=row.start_time,
                end_time=row.end_time,
                capacity=row.capacity,
                status=row.status,
                rsvp_status=row.rsvp_status
            )
            for row in events
        ]

@router.get("/{user_id}/dashboard", response_model=schemas.UserDashboard)
def get_user_dashboard(user_id: int):
    """
    Get comprehensive dashboard for a user.
    
    Returns:
    - All groups the user is a member of with their roles
    - Upcoming events they're attending (RSVP = 'going')
    - Events from their groups they haven't RSVP'd to yet
    - Summary statistics
    """
    with db.engine.begin() as connection:
        # Check if user exists
        user = connection.execute(
            sqlalchemy.text("SELECT user_id, name FROM users WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        # Get all groups user is a member of
        groups_rows = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    g.group_id,
                    g.name,
                    gm.role,
                    COUNT(DISTINCT gm2.user_id) as member_count
                FROM groups g
                JOIN group_memberships gm ON g.group_id = gm.group_id
                LEFT JOIN group_memberships gm2 ON g.group_id = gm2.group_id
                WHERE gm.user_id = :user_id
                GROUP BY g.group_id, g.name, gm.role
                ORDER BY g.name
                """
            ),
            {"user_id": user_id}
        ).fetchall()

        groups = [
            schemas.DashboardGroupItem(
                group_id=row.group_id,
                name=row.name,
                role=row.role,
                member_count=row.member_count
            )
            for row in groups_rows
        ]

        # Get upcoming events user is attending (RSVP = 'going')
        attending_rows = connection.execute(
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
                    r.status as rsvp_status,
                    COUNT(CASE WHEN r2.status = 'going' THEN 1 END) as going_count
                FROM events e
                JOIN groups g ON e.group_id = g.group_id
                JOIN rsvps r ON e.event_id = r.event_id
                LEFT JOIN rsvps r2 ON e.event_id = r2.event_id
                WHERE r.user_id = :user_id
                  AND r.status = 'going'
                  AND e.status = 'active'
                  AND e.start_time > CURRENT_TIMESTAMP
                GROUP BY e.event_id, e.group_id, g.name, e.title, e.location, 
                         e.start_time, e.end_time, e.capacity, r.status
                ORDER BY e.start_time
                """
            ),
            {"user_id": user_id}
        ).fetchall()

        attending_events = [
            schemas.DashboardEventItem(
                event_id=row.event_id,
                group_id=row.group_id,
                group_name=row.group_name,
                title=row.title,
                location=row.location,
                start_time=row.start_time,
                end_time=row.end_time,
                capacity=row.capacity,
                going_count=row.going_count,
                rsvp_status=row.rsvp_status
            )
            for row in attending_rows
        ]

        # Get upcoming events from user's groups they haven't RSVP'd to
        pending_rows = connection.execute(
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
                    COUNT(CASE WHEN r.status = 'going' THEN 1 END) as going_count
                FROM events e
                JOIN groups g ON e.group_id = g.group_id
                JOIN group_memberships gm ON e.group_id = gm.group_id
                LEFT JOIN rsvps r ON e.event_id = r.event_id
                WHERE gm.user_id = :user_id
                  AND e.status = 'active'
                  AND e.start_time > CURRENT_TIMESTAMP
                  AND NOT EXISTS (
                      SELECT 1 FROM rsvps r2 
                      WHERE r2.event_id = e.event_id 
                      AND r2.user_id = :user_id
                  )
                GROUP BY e.event_id, e.group_id, g.name, e.title, e.location,
                         e.start_time, e.end_time, e.capacity
                ORDER BY e.start_time
                LIMIT 10
                """
            ),
            {"user_id": user_id}
        ).fetchall()

        pending_rsvps = [
            schemas.DashboardEventItem(
                event_id=row.event_id,
                group_id=row.group_id,
                group_name=row.group_name,
                title=row.title,
                location=row.location,
                start_time=row.start_time,
                end_time=row.end_time,
                capacity=row.capacity,
                going_count=row.going_count,
                rsvp_status=None
            )
            for row in pending_rows
        ]

        return schemas.UserDashboard(
            user_id=user_id,
            user_name=user.name,
            groups=groups,
            attending_events=attending_events,
            pending_rsvps=pending_rsvps,
            total_groups=len(groups),
            total_attending=len(attending_events),
            total_pending=len(pending_rsvps)
        )
