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
