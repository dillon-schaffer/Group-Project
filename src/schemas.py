from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# Note: 'owner' is included for internal representation but cannot be assigned via update endpoints
MembershipRole = Literal["owner", "organizer", "member"]
RsvpStatus = Literal["going", "maybe", "not going"]


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserCreated(BaseModel):
    user_id: int


class UserProfile(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    created_at: datetime



class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    created_by: int = Field(gt=0)


class GroupCreated(BaseModel):
    group_id: int
    owner_id: int


class GroupDetails(BaseModel):
    group_id: int
    name: str
    description: str | None
    created_by: int
    owner_name: str
    member_count: int
    created_at: datetime


class MemberCreate(BaseModel):
    user_id: int = Field(gt=0)


class MemberRoleUpdate(BaseModel):
    role: MembershipRole
    requested_by: int = Field(gt=0)


class MembershipOut(BaseModel):
    group_id: int
    user_id: int
    role: MembershipRole


class MemberListItem(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: MembershipRole
    joined_at: datetime


class MemberRemoved(BaseModel):
    group_id: int
    user_id: int
    removed: bool



class EventCreate(BaseModel):
    created_by: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=300)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0, le=10000)


class EventCreated(BaseModel):
    event_id: int
    group_id: int
    capacity: int


class EventUpdate(BaseModel):
    requested_by: int = Field(gt=0)
    title: str | None = Field(None, min_length=1, max_length=200)
    location: str | None = Field(None, min_length=1, max_length=300)
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(None, gt=0, le=10000)


class EventDetails(BaseModel):
    event_id: int
    group_id: int
    group_name: str
    title: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    status: str
    created_by: int
    creator_name: str
    going_count: int
    created_at: datetime


class EventUpdated(BaseModel):
    event_id: int
    group_id: int
    message: str


class EventCancelled(BaseModel):
    event_id: int
    group_id: int
    status: str



class RsvpCreate(BaseModel):
    user_id: int = Field(gt=0)
    status: RsvpStatus


class RsvpOut(BaseModel):
    event_id: int
    user_id: int
    status: RsvpStatus


class UserEventOut(BaseModel):
    event_id: int
    group_id: int
    group_name: str
    title: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    status: str
    rsvp_status: RsvpStatus | None = None


class RsvpListItem(BaseModel):
    user_id: int
    name: str
    status: RsvpStatus


class EventRsvpSummary(BaseModel):
    event_id: int
    title: str
    capacity: int
    going_count: int
    maybe_count: int
    not_going_count: int
    rsvps: list[RsvpListItem]


# Complex endpoint schemas

class DashboardGroupItem(BaseModel):
    group_id: int
    name: str
    role: MembershipRole
    member_count: int


class DashboardEventItem(BaseModel):
    event_id: int
    group_id: int
    group_name: str
    title: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    going_count: int
    rsvp_status: RsvpStatus | None = None


class UserDashboard(BaseModel):
    user_id: int
    user_name: str
    groups: list[DashboardGroupItem]
    attending_events: list[DashboardEventItem]
    pending_rsvps: list[DashboardEventItem]
    total_groups: int
    total_attending: int
    total_pending: int


class MemberActivityItem(BaseModel):
    user_id: int
    name: str
    role: MembershipRole
    events_created: int
    rsvps_made: int


class GroupAnalytics(BaseModel):
    group_id: int
    group_name: str
    total_members: int
    owners_count: int
    organizers_count: int
    members_count: int
    total_events: int
    active_events: int
    cancelled_events: int
    past_events: int
    future_events: int
    average_rsvp_rate: float
    most_active_members: list[MemberActivityItem]
