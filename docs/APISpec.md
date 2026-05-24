# Event & Group Coordination API Specification

## Authentication
All endpoints require API key authentication via the `X-API-Key` header.

---

## Users

### POST /users
Registers a new user (creates a new user_id)

**Request Body:**
- `name`: User's full name
- `email`: User's email address
- `password`: User's password (will be hashed)

**Response:** `{ user_id: int }`

---

### GET /users/{user_id}/dashboard ⭐ COMPLEX ENDPOINT
Get comprehensive dashboard for a user including all groups, attending events, and pending RSVPs.

**Query Parameters:**
- None (user_id in path)

**Response:**
- `user_id`: User ID
- `user_name`: User's name
- `groups`: Array of groups user belongs to with role and member count
- `attending_events`: Array of upcoming events user is attending (RSVP = 'going')
- `pending_rsvps`: Array of upcoming events from user's groups they haven't RSVP'd to
- `total_groups`: Count of groups
- `total_attending`: Count of events attending
- `total_pending`: Count of pending RSVPs

**Complexity:**
- Multiple JOINs across users, groups, group_memberships, events, and rsvps tables
- Aggregations (member counts, RSVP counts)
- Date filtering (upcoming events only)
- Subquery for pending RSVPs (NOT EXISTS clause)
- Grouped data presentation

---

### GET /users/{user_id}/events
Get all events for a specific user.

---

## Groups

### POST /groups
Create a new group (creator is auto-assigned owner role)

**Request Body:**
- `name`: Group name
- `description`: Optional group description
- `created_by`: User ID of creator

**Response:** `{ group_id: int, owner_id: int }`

---

### POST /groups/{group_id}/members
Add a member to a group

**Request Body:**
- `user_id`: ID of user to add

**Response:** `{ group_id: int, user_id: int, role: string }`

---

### PATCH /groups/{group_id}/members/{user_id}
Update a group member's role (owner only)

**Request Body:**
- `role`: New role (organizer or member)
- `requested_by`: User ID making the request

**Response:** `{ group_id: int, user_id: int, role: string }`

---

### DELETE /groups/{group_id}/members/{user_id}
Remove a member from a group (owner only)

**Query Parameters:**
- `requested_by`: User ID making the request

**Response:** `{ group_id: int, user_id: int, removed: bool }`

---

### GET /groups/{group_id}/analytics ⭐ COMPLEX ENDPOINT
Get comprehensive analytics for a group including member statistics, event metrics, and activity data.

**Query Parameters:**
- `requested_by`: User ID making the request (must be a group member)

**Response:**
- `group_id`: Group ID
- `group_name`: Group name
- `total_members`: Total member count
- `owners_count`: Number of owners
- `organizers_count`: Number of organizers
- `members_count`: Number of regular members
- `total_events`: Total events created
- `active_events`: Number of active events
- `cancelled_events`: Number of cancelled events
- `past_events`: Number of past events
- `future_events`: Number of future events
- `average_rsvp_rate`: Percentage of possible RSVPs that were made
- `most_active_members`: Top 5 members by activity (events created + RSVPs)

**Complexity:**
- Multiple aggregations with conditional counting (COUNT CASE WHEN)
- JOINs across group_memberships, events, rsvps, and users tables
- Complex RSVP rate calculation (total RSVPs / (events × members))
- Date-based filtering (past vs future events)
- Sorting by computed activity score
- Division by zero handling

---

## Events

### POST /groups/{group_id}/events
Create an event within a group (owner and organizer only)

**Request Body:**
- `created_by`: User ID of creator
- `title`: Event title
- `location`: Event location
- `start_time`: Event start datetime
- `end_time`: Event end datetime
- `capacity`: Maximum attendees

**Response:** `{ event_id: int, group_id: int, capacity: int }`

**Validation:**
- End time must be after start time
- Only owners and organizers can create events

---

### DELETE /groups/{group_id}/events/{event_id}
Cancel an event (owner only)

**Query Parameters:**
- `requested_by`: User ID making the request

**Response:** `{ event_id: int, group_id: int, status: string }`

---

## RSVPs

### POST /events/{event_id}/rsvp
Submit or update an RSVP for an event (group members only)

**Request Body:**
- `user_id`: User ID
- `status`: RSVP status ('going', 'maybe', 'not going')

**Response:** `{ event_id: int, user_id: int, status: string }`

**Validation:**
- User must be a group member
- Event must be active (not cancelled)

---

### GET /events/{event_id}/rsvps
Get all RSVPs for an event with summary statistics (owner and organizer only)

**Query Parameters:**
- `requested_by`: User ID making the request

**Response:**
- `event_id`: Event ID
- `title`: Event title
- `capacity`: Event capacity
- `going_count`: Number of 'going' RSVPs
- `maybe_count`: Number of 'maybe' RSVPs
- `not_going_count`: Number of 'not going' RSVPs
- `rsvps`: Array of all RSVPs with user details

---

## Complex Endpoints Summary

This API includes **two complex endpoints** that go beyond simple CRUD operations:

1. **GET /users/{user_id}/dashboard** - Aggregates user data across multiple tables with joins, date filtering, and nested queries
2. **GET /groups/{group_id}/analytics** - Performs sophisticated analytics with multiple aggregations, calculations, and conditional counting
