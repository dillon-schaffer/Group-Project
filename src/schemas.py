from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


MembershipRole = Literal["owner", "organizer", "member"]
RsvpStatus = Literal["going", "maybe", "not going"]


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)


class UserCreated(BaseModel):
    user_id: int


class GroupCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    created_by: int


class GroupCreated(BaseModel):
    group_id: int
    owner_id: int


class MemberCreate(BaseModel):
    user_id: int


class MemberRoleUpdate(BaseModel):
    role: MembershipRole
    requested_by: int


class MembershipOut(BaseModel):
    group_id: int
    user_id: int
    role: MembershipRole


class MemberRemoved(BaseModel):
    group_id: int
    user_id: int
    removed: bool


class EventCreate(BaseModel):
    created_by: int
    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0)


class EventCreated(BaseModel):
    event_id: int
    group_id: int
    capacity: int


class EventCancelled(BaseModel):
    event_id: int
    group_id: int
    status: str


class RsvpCreate(BaseModel):
    user_id: int
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
