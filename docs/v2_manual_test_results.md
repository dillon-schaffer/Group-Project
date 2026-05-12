# Example workflow

## Flow 2: Organizer Creates an Event, Members RSVP, Organizer Checks Attendance

Priya creates an upcoming hike, three members RSVP, and Priya reviews the attendance list before the event.

**Precondition:** Flow 1 setup is already complete.
- Marcus user_id = 1 (owner)
- Priya user_id = 2 (organizer)
- SLO Hikers group_id = 1

**Step 1 - Two more members join the group.**

`POST /groups/1/members` -> `{ "user_id": 3 }` -> Jordan joins as `member`

`POST /groups/1/members` -> `{ "user_id": 4 }` -> Sam joins as `member`

**Step 2 - Priya creates an event with a capacity of 10.**

`POST /groups/1/events`
```json
{
  "created_by": 2,
  "title": "Bishop Peak Morning Hike",
  "location": "Bishop Peak Trailhead, SLO",
  "start_time": "2026-05-10T08:00:00",
  "end_time": "2026-05-10T12:00:00",
  "capacity": 10
}
```

**Step 3 - Marcus RSVPs as going.**

`POST /events/1/rsvp`
```json
{ "user_id": 1, "status": "going" }
```

**Step 4 - Jordan RSVPs as maybe.**

`POST /events/1/rsvp`
```json
{ "user_id": 3, "status": "maybe" }
```

**Step 5 - Sam RSVPs as going.**

`POST /events/1/rsvp`
```json
{ "user_id": 4, "status": "going" }
```

**Step 6 - Priya pulls the RSVP list to plan logistics.**

`GET /events/1/rsvps?requested_by=2`

---

## Flow 3: User joins a group, creates an event, is removed from the group and the event is cancelled by the group owner.

Alex wants to host a sunset walk for SLO Hikers. He joins the group, is promoted to organizer (required by API permissions), schedules the event, and then Marcus removes him from the group and cancels the walk.

**Step 1 - Alex registers an account.**

`POST /users`
```json
{
  "name": "Alex Kim",
  "email": "alex@example.com",
  "password": "trailmix9"
}
```

**Step 2 - Alex joins SLO Hikers (group 1).**

`POST /groups/1/members`
```json
{ "user_id": 5 }
```

**Step 3 - Alex attempts to create an event as member (expected to fail with 403).**

`POST /groups/1/events`
```json
{
  "created_by": 5,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}
```

**Step 3a - Marcus promotes Alex to organizer.**

`PATCH /groups/1/members/5`
```json
{
  "role": "organizer",
  "requested_by": 1
}
```

**Step 3b - Alex creates the event as organizer.**

`POST /groups/1/events`
```json
{
  "created_by": 5,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}
```

**Step 4 - Marcus removes Alex from the group.**

`DELETE /groups/1/members/5?requested_by=1`

**Step 5 - Marcus cancels the event as group owner.**

`DELETE /groups/1/events/2?requested_by=1`

---

# Testing results

## Flow 2 - Step 1 - Jordan joins the group

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/members' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 3
}'
```

2. Response received:
```json
{
  "group_id": 1,
  "user_id": 3,
  "role": "member"
}
```

## Flow 2 - Step 1 - Sam joins the group

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/members' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 4
}'
```

2. Response received:
```json
{
  "group_id": 1,
  "user_id": 4,
  "role": "member"
}
```

## Flow 2 - Step 2 - Priya creates event

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/events' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "created_by": 2,
  "title": "Bishop Peak Morning Hike",
  "location": "Bishop Peak Trailhead, SLO",
  "start_time": "2026-05-10T08:00:00",
  "end_time": "2026-05-10T12:00:00",
  "capacity": 10
}'
```

2. Response received:
```json
{
  "event_id": 1,
  "group_id": 1,
  "capacity": 10
}
```

## Flow 2 - Step 3 - Marcus RSVPs going

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/events/1/rsvp' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 1,
  "status": "going"
}'
```

2. Response received:
```json
{
  "event_id": 1,
  "user_id": 1,
  "status": "going"
}
```

## Flow 2 - Step 4 - Jordan RSVPs maybe

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/events/1/rsvp' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 3,
  "status": "maybe"
}'
```

2. Response received:
```json
{
  "event_id": 1,
  "user_id": 3,
  "status": "maybe"
}
```

## Flow 2 - Step 5 - Sam RSVPs going

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/events/1/rsvp' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 4,
  "status": "going"
}'
```

2. Response received:
```json
{
  "event_id": 1,
  "user_id": 4,
  "status": "going"
}
```

## Flow 2 - Step 6 - Priya views RSVP summary

1. Curl statement called:
```bash
curl -X 'GET' \
  'http://localhost:8000/events/1/rsvps?requested_by=2' \
  -H 'accept: application/json'
```

2. Response received:
```json
{
  "event_id": 1,
  "title": "Bishop Peak Morning Hike",
  "capacity": 10,
  "going_count": 2,
  "maybe_count": 1,
  "not_going_count": 0,
  "rsvps": [
    {
      "user_id": 1,
      "name": "Marcus Webb",
      "status": "going"
    },
    {
      "user_id": 3,
      "name": "Jordan Lee",
      "status": "maybe"
    },
    {
      "user_id": 4,
      "name": "Sam Torres",
      "status": "going"
    }
  ]
}
```

## Flow 3 - Step 1 - Alex registers

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/users' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Alex Kim",
  "email": "alex@example.com",
  "password": "trailmix9"
}'
```

2. Response received:
```json
{
  "user_id": 5
}
```

## Flow 3 - Step 2 - Alex joins group

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/members' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 5
}'
```

2. Response received:
```json
{
  "group_id": 1,
  "user_id": 5,
  "role": "member"
}
```

## Flow 3 - Step 3 - Alex attempts event creation as member (expected permission error)

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/events' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "created_by": 5,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}'
```

2. Response received:
```json
{
  "detail": "Only group owners and organizers can create events"
}
```

## Flow 3 - Step 3a - Marcus promotes Alex to organizer

1. Curl statement called:
```bash
curl -X 'PATCH' \
  'http://localhost:8000/groups/1/members/5' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "role": "organizer",
  "requested_by": 1
}'
```

2. Response received:
```json
{
  "group_id": 1,
  "user_id": 5,
  "role": "organizer"
}
```

## Flow 3 - Step 3b - Alex creates event as organizer

1. Curl statement called:
```bash
curl -X 'POST' \
  'http://localhost:8000/groups/1/events' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "created_by": 5,
  "title": "Laguna Lake Sunset Loop",
  "location": "Laguna Lake Park, SLO",
  "start_time": "2026-05-17T18:30:00",
  "end_time": "2026-05-17T20:00:00",
  "capacity": 15
}'
```

2. Response received:
```json
{
  "event_id": 2,
  "group_id": 1,
  "capacity": 15
}
```

## Flow 3 - Step 4 - Marcus removes Alex

1. Curl statement called:
```bash
curl -X 'DELETE' \
  'http://localhost:8000/groups/1/members/5?requested_by=1' \
  -H 'accept: application/json'
```

2. Response received:
```json
{
  "group_id": 1,
  "user_id": 5,
  "removed": true
}
```

## Flow 3 - Step 5 - Marcus cancels Alex's event

1. Curl statement called:
```bash
curl -X 'DELETE' \
  'http://localhost:8000/groups/1/events/2?requested_by=1' \
  -H 'accept: application/json'
```

2. Response received:
```json
{
  "event_id": 2,
  "group_id": 1,
  "status": "cancelled"
}
```

---

# V2 verification notes

- Automated tests: 14 passed (`python -m pytest -q`)
- Alembic migrations are in use via `alembic/versions/546d0e45e534_create_initial_schema.py`, so no standalone `schema.sql` is required for this submission.

# Online submission

GitHub project link: https://github.com/dillon-schaffer/Group-Project
