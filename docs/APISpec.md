# Event & Group Coordination API Specification

## Authentication
All endpoints require API key authentication via the `X-API-Key` header.

---

## Users

### POST /users
Registers a new user (creates a new user_id)

**Request Body:**
- `name`: User's full name (1-100 characters)
- `email`: User's email address
- `password`: User's password (8-128 characters, must include uppercase, number, and special character)

**Response:** `{ user_id: int }`

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

---

### GET /users/{user_id}
Get a user's profile information

**Response:**
- `user_id`: User ID
- `name`: User's name
- `email`: User's email
- `created_at`: Account creation timestamp

---

### GET /users/{user_id}/events
Get all events a user has RSVP'd to

**Response:** Array of events with:
- `event_id`: Event ID
- `group_id`: Group ID
- `group_name`: Group name
- `title`: Event title
- `location`: Event location
- `start_time`: Event start time
- `end_time`: Event end time
- `capacity`: Event capacity
- `status`: Event status
- `rsvp_status`: User's RSVP status for this event

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
- `name`: Group name (1-200 characters)
- `description`: Optional group description (max 1000 characters)
- `created_by`: User ID of creator

**Response:** `{ group_id: int, owner_id: int }`

---
### GET /groups/{group_id}/events/{event_id}
Get details for a specific event

**Response:**
- `event_id`: Event ID
- `group_id`: Group ID
- `group_name`: Group name
- `title`: Event title
- `location`: Event location
- `start_time`: Event start time
- `end_time`: Event end time
- `capacity`: Maximum attendees
- `status`: Event status (active/cancelled)
- `created_by`: Creator user ID
- `creator_name`: Creator's name
- `going_count`: Number of "going" RSVPs
- `created_at`: Creation timestamp

---
### GET /groups/{group_id}
Get group details

**Response:**
- `group_id`: Group ID
- `name`: Group name
- `description`: Group description
- `created_by`: Owner user ID
- `owner_name`: Owner's name
- `member_count`: Number of members
- `created_at`: Creation timestamp

---

### GET /groups/{group_id}/members
Get all members of a group

**Response:** Array of members with:
- `user_id`: User ID
- `name`: User's name
- `email`: User's email
- `role`: Member's role
- `joined_at`: When they joined

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
- `title`: Event title (1-200 characters)
- `location`: Event location (1-300 characters)
- `start_time`: Event start datetime
- `end_time`: Event end datetime
- `capacity`: Maximum attendees (1-10000)

**Response:** `{ event_id: int, group_id: int, capacity: int }`

**Validation:**
- End time must be after start time
- Only owners and organizers can create events

---

### PATCH /groups/{group_id}/events/{event_id}
Update an event's details (owner and organizer only)

**Request Body:**
- `requested_by`: User ID making the request
- `title`: Optional, new event title (1-200 characters)
- `location`: Optional, new location (1-300 characters)
- `start_time`: Optional, new start datetime
- `end_time`: Optional, new end datetime
- `capacity`: Optional, new capacity (1-10000)

**Response:** `{ event_id: int, group_id: int, message: string }`

**Validation:**
- At least one field must be provided
- End time must be after start time (if either is updated)
- Cannot update cancelled events
- Only owners and organizers can update events

---

### DELETE /groups/{group_id}/events/{event_id}
Cancel an event (owner and organizer only - UPDATED)

**Query Parameters:**
- `requested_by`: User ID making the request

**Response:** `{ event_id: int, group_id: int, status: string }`

**Note:** Both owners and organizers can now cancel events.

---

## RSVPs

### POST /events/{event_id}/rsvp
Create or update an RSVP for an event (upsert operation)

**Request Body:**
- `user_id`: User ID making the RSVP
- `status`: RSVP status ("going", "maybe", "not going")

**Response:** `{ event_id: int, user_id: int, status: string }`

**Validation:**
- User must be a group member
- Event must be active (not cancelled)
- **NEW:** Capacity check - cannot RSVP "going" if event is at full capacity

---

### GET /events/{event_id}/rsvps
Get all RSVPs for an event with summary statistics (with pagination)

**Query Parameters:**
- `requested_by`: User ID making the request
- `limit`: Optional, max number of RSVPs to return (1-1000, default 100)
- `offset`: Optional, number of RSVPs to skip (default 0)

**Response:**
- `event_id`: Event ID
- `title`: Event title
- `capacity`: Event capacity
- `going_count`: Number of 'going' RSVPs (total, not paginated)
- `maybe_count`: Number of 'maybe' RSVPs (total, not paginated)
- `not_going_count`: Number of 'not going' RSVPs (total, not paginated)
- `rsvps`: Array of RSVPs with user details (paginated)

**Note:** Counts represent all RSVPs, but the `rsvps` array is paginated based on limit/offset parameters.

---

## Recent Improvements

### Round 1: Schema & Validation
✅ **Strengthened password requirements**: 8-128 characters with uppercase, number, and special character  
✅ **Added max_length constraints**: All string fields now have reasonable upper bounds  
✅ **Capacity upper bound**: Events limited to 10,000 capacity  
✅ **Event Update endpoint**: PATCH /groups/{group_id}/events/{event_id} for modifying event details  
✅ **RSVP pagination**: GET /events/{event_id}/rsvps now supports limit/offset parameters  
✅ **Removed duplicate files**: Cleaned up root-level database.py and schemas.py  

### Round 2: Bug Fixes & New Endpoints
✅ **Organizers can cancel events**: Fixed permission check (previously only owners)  
✅ **Capacity enforcement**: Cannot RSVP "going" if event is at full capacity  
✅ **Improved error messages**: No longer exposes membership information  
✅ **GET /users/{user_id}**: Retrieve user profile  
✅ **GET /users/{user_id}/events**: Get all events user has RSVP'd to  
✅ **GET /groups/{group_id}**: Get group details and member count  
✅ **GET /groups/{group_id}/members**: List all group members with roles  
✅ **GET /groups/{group_id}/events/{event_id}**: Get single event details  

### Round 3: Testing & Code Quality
✅ **Fixed test suite**: Added X-API-Key header to test client  
✅ **RSVP cleanup on member removal**: RSVPs now deleted when user leaves group  
✅ **Self-removal capability**: Members can now remove themselves from groups  
✅ **Logging improvements**: Replaced print() with proper logging  
✅ **Sensitive data protection**: Database credentials no longer logged  
✅ **Test database exclusion**: Added *.db to .gitignore

---

## Complex Endpoints Summary

This API includes **two complex endpoints** that go beyond simple CRUD operations:

1. **GET /users/{user_id}/dashboard** - Aggregates user data across multiple tables with joins, date filtering, and nested queries
2. **GET /groups/{group_id}/analytics** - Performs sophisticated analytics with multiple aggregations, calculations, and conditional counting
