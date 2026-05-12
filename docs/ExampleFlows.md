# Example Flows — Event & Group Coordination API

---

## Flow 1: Group Owner Creates a Group and Promotes an Organizer

Marcus wants to start a hiking club. He registers, creates the group, and promotes his friend Priya to organizer so she can help manage events.

**Step 1 — Marcus registers an account.**

`POST /users`
```json
{
  "name": "Marcus Webb",
  "email": "marcus@example.com",
  "password": "s3cure!"
}
```
Response: `{ "user_id": 101 }`

**Step 2 — Priya registers separately.**

`POST /users`
```json
{
  "name": "Priya Nair",
  "email": "priya@example.com",
  "password": "hike4ever"
}
```
Response: `{ "user_id": 102 }`

**Step 3 — Marcus creates the group. He is auto-assigned the `owner` role.**

`POST /groups`
```json
{
  "name": "SLO Hikers",
  "description": "Weekend trails in the Central Coast",
  "created_by": 101
}
```
Response: `{ "group_id": 55, "owner_id": 101 }`

**Step 4 — Priya requests to join the group.**

`POST /groups/55/members`
```json
{ "user_id": 102 }
```
Response: `{ "group_id": 55, "user_id": 102, "role": "member" }`

**Step 5 — Marcus promotes Priya to organizer so she can create events.**

`PATCH /groups/55/members/102`
```json
{
  "role": "organizer",
  "requested_by": 101
}
```
Response: `{ "group_id": 55, "user_id": 102, "role": "organizer" }`

Priya is now a trusted organizer and can create and manage events within the SLO Hikers group.

---
## Flow 2: Organizer Creates an Event, Members RSVP, Organizer Checks Attendance

Priya creates an upcoming hike, three members RSVP, and Priya reviews the attendance list before the event.

**Step 1 — Two more users register and join the group.**

`POST /users`
```json
{
  "name": "Jordan Lee",
  "email": "jordan@example.com",
  "password": "peaks4days"
}
```
Response: `{ "user_id": 103 }`

`POST /users`
```json
{
  "name": "Sam Torres",
  "email": "sam@example.com",
  "password": "trailtime"
}
```
Response: `{ "user_id": 104 }`

`POST /groups/55/members` → `{ "user_id": 103 }` → Jordan joins as `member`  
`POST /groups/55/members` → `{ "user_id": 104 }` → Sam joins as `member`

**Step 2 — Priya creates an event with a capacity of 10.**

`POST /groups/55/events`
```json
{
  "created_by": 102,
  "title": "Bishop Peak Morning Hike",
  "location": "Bishop Peak Trailhead, SLO",
  "start_time": "2026-05-10T08:00:00",
  "end_time": "2026-05-10T12:00:00",
  "capacity": 10
}
```
Response: `{ "event_id": 201, "group_id": 55, "capacity": 10 }`

**Step 3 — Marcus RSVPs as going.**

`POST /events/201/rsvp`
```json
{ "user_id": 101, "status": "going" }
```
Response: `{ "event_id": 201, "user_id": 101, "status": "going" }`

**Step 4 — Jordan RSVPs as maybe.**

`POST /events/201/rsvp`
```json
{ "user_id": 103, "status": "maybe" }
```
Response: `{ "event_id": 201, "user_id": 103, "status": "maybe" }`

**Step 5 — Sam RSVPs as going.**

`POST /events/201/rsvp`
```json
{ "user_id": 104, "status": "going" }
```
Response: `{ "event_id": 201, "user_id": 104, "status": "going" }`

**Step 6 — Priya pulls the RSVP list to plan logistics.**

`GET /events/201/rsvps?requested_by=102`

Response:
```json
{
  "event_id": 201,
  "title": "Bishop Peak Morning Hike",
  "capacity": 10,
  "going_count": 2,
  "maybe_count": 1,
  "not_going_count": 0,
  "rsvps": [
    { "user_id": 101, "name": "Marcus Webb", "status": "going" },
    { "user_id": 103, "name": "Jordan Lee", "status": "maybe" },
    { "user_id": 104, "name": "Sam Torres", "status": "going" }
  ]
}
```

Priya can see 2 confirmed attendees and 1 maybe. She plans for 3 carpools to be safe.

---

## Flow 3: User joins a group, creates an event, is removed from the group and the event is cancelled by the group owner.

Alex wants to host a sunset walk for SLO Hikers. He joins the group, is promoted to organizer, schedules the event, and then Marcus removes him from the group and cancels the walk.

**Step 1: Alex registers an account.**

`POST /users`
```json
{
  "name": "Alex Kim",
  "email": "alex@example.com",
  "password": "trailmix9"
}
```
Response: `{ "user_id": 105 }`

**Step 2: Alex joins SLO Hikers (group 55).**

`POST /groups/55/members`
```json
{ "user_id": 105 }
```
Response: `{ "group_id": 55, "user_id": 105, "role": "member" }`

**Step 3: Alex attempts to create a group event as a member.**

`POST /groups/55/events`
```json
{
  "created_by": 105,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}
```
Response: `{ "detail": "Only group owners and organizers can create events" }`

**Step 3a: Marcus promotes Alex to organizer.**

`PATCH /groups/55/members/105`
```json
{
  "role": "organizer",
  "requested_by": 101
}
```
Response: `{ "group_id": 55, "user_id": 105, "role": "organizer" }`

**Step 3b: Alex creates a group event as organizer.**

`POST /groups/55/events`
```json
{
  "created_by": 105,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}
```
Response: `{ "event_id": 202, "group_id": 55, "capacity": 15 }`

**Step 4: Marcus removes Alex from the group**

`DELETE /groups/55/members/105?requested_by=101`

Response: `{ "group_id": 55, "user_id": 105, "removed": true }`

**Step 5: Marcus cancels the event as group owner.**

`DELETE /groups/55/events/202?requested_by=101`

Response: `{ "event_id": 202, "group_id": 55, "status": "cancelled" }`

### Members who had seen the sunset loop on the calendar are notified by the cancellation and the event no longer appears as active for group 55.
---
