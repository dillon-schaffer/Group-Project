import bcrypt
from fastapi import FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import models
import schemas
from database import get_db

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
    
    db = next(get_db())
    try:
        new_user = models.User(
            name=user.name,
            email=user.email,
            password_hash=password_hash,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return schemas.UserCreated(user_id=new_user.user_id)
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    finally:
        db.close()


@app.post("/groups", response_model=schemas.GroupCreated, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate):
    """
    Create a new group.
    
    The creator is automatically assigned the 'owner' role.
    """
    db = next(get_db())
    try:
        # Verify the creator exists
        creator = db.scalar(select(models.User).where(models.User.user_id == group.created_by))
        if not creator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {group.created_by} not found",
            )
        
        # Create the group
        new_group = models.Group(
            name=group.name,
            description=group.description,
            created_by=group.created_by,
        )
        db.add(new_group)
        db.flush()  # Get the group_id without committing
        
        # Add creator as owner
        membership = models.GroupMembership(
            group_id=new_group.group_id,
            user_id=group.created_by,
            role="owner",
        )
        db.add(membership)
        db.commit()
        
        return schemas.GroupCreated(
            group_id=new_group.group_id,
            owner_id=group.created_by,
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create group: {str(e)}",
        )
    finally:
        db.close()


@app.post("/groups/{group_id}/members", response_model=schemas.MembershipOut, status_code=status.HTTP_201_CREATED)
def add_group_member(group_id: int, member: schemas.MemberCreate):
    """
    Add a member to a group.
    
    New members are assigned the 'member' role by default.
    """
    db = next(get_db())
    try:
        # Verify the group exists
        group = db.scalar(select(models.Group).where(models.Group.group_id == group_id))
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )
        
        # Verify the user exists
        user = db.scalar(select(models.User).where(models.User.user_id == member.user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {member.user_id} not found",
            )
        
        # Check if already a member
        existing = db.scalar(
            select(models.GroupMembership).where(
                models.GroupMembership.group_id == group_id,
                models.GroupMembership.user_id == member.user_id,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {member.user_id} is already a member of group {group_id}",
            )
        
        # Add membership
        membership = models.GroupMembership(
            group_id=group_id,
            user_id=member.user_id,
            role="member",
        )
        db.add(membership)
        db.commit()
        
        return schemas.MembershipOut(
            group_id=group_id,
            user_id=member.user_id,
            role="member",
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member: {str(e)}",
        )
    finally:
        db.close()


@app.patch("/groups/{group_id}/members/{user_id}", response_model=schemas.MembershipOut)
def update_member_role(group_id: int, user_id: int, update: schemas.MemberRoleUpdate):
    """
    Update a member's role within a group.
    
    Only owners can promote members to organizer or demote organizers.
    """
    db = next(get_db())
    try:
        # Verify the requester is an owner
        requester_membership = db.scalar(
            select(models.GroupMembership).where(
                models.GroupMembership.group_id == group_id,
                models.GroupMembership.user_id == update.requested_by,
            )
        )
        if not requester_membership or requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group owners can change member roles",
            )
        
        # Get the target membership
        membership = db.scalar(
            select(models.GroupMembership).where(
                models.GroupMembership.group_id == group_id,
                models.GroupMembership.user_id == user_id,
            )
        )
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
        membership.role = update.role
        db.commit()
        
        return schemas.MembershipOut(
            group_id=group_id,
            user_id=user_id,
            role=update.role,
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}",
        )
    finally:
        db.close()


@app.post("/groups/{group_id}/events", response_model=schemas.EventCreated, status_code=status.HTTP_201_CREATED)
def create_event(group_id: int, event: schemas.EventCreate):
    """
    Create a new event within a group.
    
    Only group owners and organizers can create events.
    """
    db = next(get_db())
    try:
        # Verify the group exists
        group = db.scalar(select(models.Group).where(models.Group.group_id == group_id))
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found",
            )
        
        # Verify the creator is an owner or organizer
        membership = db.scalar(
            select(models.GroupMembership).where(
                models.GroupMembership.group_id == group_id,
                models.GroupMembership.user_id == event.created_by,
            )
        )
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
        new_event = models.Event(
            group_id=group_id,
            created_by=event.created_by,
            title=event.title,
            location=event.location,
            start_time=event.start_time,
            end_time=event.end_time,
            capacity=event.capacity,
            status="active",
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        
        return schemas.EventCreated(
            event_id=new_event.event_id,
            group_id=group_id,
            capacity=new_event.capacity,
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}",
        )
    finally:
        db.close()


@app.post("/events/{event_id}/rsvp", response_model=schemas.RsvpOut)
def create_or_update_rsvp(event_id: int, rsvp: schemas.RsvpCreate):
    """
    RSVP to an event or update an existing RSVP.
    
    Users can only RSVP if they are members of the event's group.
    """
    db = next(get_db())
    try:
        # Verify the event exists
        event = db.scalar(select(models.Event).where(models.Event.event_id == event_id))
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found",
            )
        
        # Verify user is a member of the group
        membership = db.scalar(
            select(models.GroupMembership).where(
                models.GroupMembership.group_id == event.group_id,
                models.GroupMembership.user_id == rsvp.user_id,
            )
        )
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
        
        # Create or update RSVP
        existing_rsvp = db.scalar(
            select(models.Rsvp).where(
                models.Rsvp.event_id == event_id,
                models.Rsvp.user_id == rsvp.user_id,
            )
        )
        
        if existing_rsvp:
            existing_rsvp.status = rsvp.status
        else:
            new_rsvp = models.Rsvp(
                event_id=event_id,
                user_id=rsvp.user_id,
                status=rsvp.status,
            )
            db.add(new_rsvp)
        
        db.commit()
        
        return schemas.RsvpOut(
            event_id=event_id,
            user_id=rsvp.user_id,
            status=rsvp.status,
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to RSVP: {str(e)}",
        )
    finally:
        db.close()
