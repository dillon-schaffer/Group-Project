import bcrypt
import sqlalchemy
from fastapi import FastAPI, HTTPException, status

import schemas
from database import engine

app = FastAPI(
    title="Event & Group Coordination API",
    description="API for managing groups, events, and RSVPs",
    version="1.0.0",
)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Event & Group Coordination API"}


@app.post("/users", response_model=schemas.UserCreated, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate):
    """
    Create a new user account.
    
    The password will be securely hashed before storage.
    """
    # Hash the password
    password_hash = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    with engine.begin() as connection:
        # Check if email already exists
        existing_user = connection.execute(
            sqlalchemy.text(
                """
                SELECT user_id
                FROM users
                WHERE email = :email
                """
            ),
            {"email": user.email}
        ).fetchone()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        
        # Insert new user
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
    """
    Create a new group.
    
    The creator is automatically assigned the 'owner' role.
    """
    with engine.begin() as connection:
        # Verify the creator exists
        creator = connection.execute(
            sqlalchemy.text(
                """
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": group.created_by}
        ).fetchone()
        
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {group.created_by} not found",
            )
        
        # Insert new group
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
        
        # Add creator as owner
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO group_memberships (group_id, user_id, role, joined_at)
                VALUES (:group_id, :user_id, 'owner', CURRENT_TIMESTAMP)
                """
            ),
            {"group_id": group_id, "user_id": group.created_by}
        )
        
        return schemas.GroupCreated(
            group_id=group_id,
            owner_id=group.created_by,
        )


@app.post("/groups/{group_id}/members", response_model=schemas.MembershipOut, status_code=status.HTTP_201_CREATED)
def add_group_member(group_id: int, member: schemas.MemberCreate):
    """
    Add a member to a group.
    
    New members are assigned the 'member' role by default.
    """
    with engine.begin() as connection:
        # Verify the group exists
        group = connection.execute(
            sqlalchemy.text(
                """
                SELECT group_id
                FROM groups
                WHERE group_id = :group_id
                """
            ),
            {"group_id": group_id}
        ).fetchone()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )
        
        # Verify the user exists
        user = connection.execute(
            sqlalchemy.text(
                """
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": member.user_id}
        ).fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {member.user_id} not found",
            )
        
        # Check if already a member
        existing = connection.execute(
            sqlalchemy.text(
                """
                SELECT group_id
                FROM group_memberships
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"group_id": group_id, "user_id": member.user_id}
        ).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {member.user_id} is already a member of group {group_id}",
            )
        
        # Add membership
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO group_memberships (group_id, user_id, role, joined_at)
                VALUES (:group_id, :user_id, 'member', CURRENT_TIMESTAMP)
                """
            ),
            {"group_id": group_id, "user_id": member.user_id}
        )
        
        return schemas.MembershipOut(
            group_id=group_id,
            user_id=member.user_id,
            role="member",
        )


@app.patch("/groups/{group_id}/members/{user_id}", response_model=schemas.MembershipOut)
def update_member_role(group_id: int, user_id: int, update: schemas.MemberRoleUpdate):
    """
    Update a member's role within a group.
    
    Only owners can promote members to organizer or demote organizers.
    """
    with engine.begin() as connection:
        # Verify the requester is an owner
        requester_membership = connection.execute(
            sqlalchemy.text(
                """
                SELECT role
                FROM group_memberships
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"group_id": group_id, "user_id": update.requested_by}
        ).fetchone()
        
        if not requester_membership or requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners can change member roles",
            )
        
        # Get the target membership
        membership = connection.execute(
            sqlalchemy.text(
                """
                SELECT role
                FROM group_memberships
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"group_id": group_id, "user_id": user_id}
        ).fetchone()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} is not a member of group {group_id}",
            )
        
        # Prevent changing owner role
        if membership.role == "owner" or update.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change owner role",
            )
        
        # Update the role
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
        
        return schemas.MembershipOut(
            group_id=group_id,
            user_id=user_id,
            role=update.role,
        )


@app.post("/groups/{group_id}/events", response_model=schemas.EventCreated, status_code=status.HTTP_201_CREATED)
def create_event(group_id: int, event: schemas.EventCreate):
    """
    Create a new event within a group.
    
    Only group owners and organizers can create events.
    """
    with engine.begin() as connection:
        # Verify the group exists
        group = connection.execute(
            sqlalchemy.text(
                """
                SELECT group_id
                FROM groups
                WHERE group_id = :group_id
                """
            ),
            {"group_id": group_id}
        ).fetchone()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )
        
        # Verify the creator is an owner or organizer
        membership = connection.execute(
            sqlalchemy.text(
                """
                SELECT role
                FROM group_memberships
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"group_id": group_id, "user_id": event.created_by}
        ).fetchone()
        
        if not membership or membership.role not in ("owner", "organizer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners and organizers can create events",
            )
        
        # Validate time range
        if event.end_time <= event.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time must be after start time",
            )
        
        # Create the event
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
                "capacity": event.capacity
            }
        ).scalar_one()
        
        return schemas.EventCreated(
            event_id=event_id,
            group_id=group_id,
            capacity=event.capacity,
        )


@app.post("/events/{event_id}/rsvp", response_model=schemas.RsvpOut)
def create_or_update_rsvp(event_id: int, rsvp: schemas.RsvpCreate):
    """
    RSVP to an event or update an existing RSVP.
    
    Users can only RSVP if they are members of the event's group.
    """
    with engine.begin() as connection:
        # Verify the event exists and get group_id
        event = connection.execute(
            sqlalchemy.text(
                """
                SELECT group_id, status
                FROM events
                WHERE event_id = :event_id
                """
            ),
            {"event_id": event_id}
        ).fetchone()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found",
            )
        
        # Verify user is a member of the group
        membership = connection.execute(
            sqlalchemy.text(
                """
                SELECT user_id
                FROM group_memberships
                WHERE group_id = :group_id AND user_id = :user_id
                """
            ),
            {"group_id": event.group_id, "user_id": rsvp.user_id}
        ).fetchone()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group members can RSVP to events",
            )
        
        # Check if event is active
        if event.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot RSVP to a cancelled event",
            )
        
        # Check if RSVP already exists
        existing_rsvp = connection.execute(
            sqlalchemy.text(
                """
                SELECT event_id
                FROM rsvps
                WHERE event_id = :event_id AND user_id = :user_id
                """
            ),
            {"event_id": event_id, "user_id": rsvp.user_id}
        ).fetchone()
        
        if existing_rsvp:
            # Update existing RSVP
            connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE rsvps
                    SET status = :status, rsvp_at = CURRENT_TIMESTAMP
                    WHERE event_id = :event_id AND user_id = :user_id
                    """
                ),
                {"status": rsvp.status, "event_id": event_id, "user_id": rsvp.user_id}
            )
        else:
            # Create new RSVP
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO rsvps (event_id, user_id, status, rsvp_at)
                    VALUES (:event_id, :user_id, :status, CURRENT_TIMESTAMP)
                    """
                ),
                {"event_id": event_id, "user_id": rsvp.user_id, "status": rsvp.status}
            )
        
        return schemas.RsvpOut(
            event_id=event_id,
            user_id=rsvp.user_id,
            status=rsvp.status,
        )
