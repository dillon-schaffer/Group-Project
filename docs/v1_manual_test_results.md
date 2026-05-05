# Example workflow

## Flow 1: Group Owner Creates a Group and Promotes an Organizer

Marcus wants to start a hiking club. He registers, creates the group, and promotes his friend Priya to organizer so she can help manage events.

**Step 1 - Marcus registers an account.**

`POST /users`
```json
{
  "name": "Marcus Webb",
  "email": "marcus@example.com",
  "password": "s3cure!"
}
```
Response: `{ "user_id": 101 }`

**Step 2 - Priya registers separately.**

`POST /users`
```json
{
  "name": "Priya Nair",
  "email": "priya@example.com",
  "password": "hike4ever"
}
```
Response: `{ "user_id": 102 }`

**Step 3 - Marcus creates the group. He is auto-assigned the `owner` role.**

`POST /groups`
```json
{
  "name": "SLO Hikers",
  "description": "Weekend trails in the Central Coast",
  "created_by": 101
}
```
Response: `{ "group_id": 55, "owner_id": 101 }`

**Step 4 - Priya requests to join the group.**

`POST /groups/55/members`
```json
{ "user_id": 102 }
```
Response: `{ "group_id": 55, "user_id": 102, "role": "member" }`

**Step 5 - Marcus promotes Priya to organizer so she can create events.**

`PATCH /groups/55/members/102`
```json
{
  "role": "organizer",
  "requested_by": 101
}
```
Response: `{ "group_id": 55, "user_id": 102, "role": "organizer" }`

Priya is now a trusted organizer and can create and manage events within the SLO Hikers group.

# Testing results

## Step 1 - Marcus registers an account

1. Curl statement called:
```bash
curl -X 'POST' \
  'https://OUR-RENDER-SERVICE.onrender.com/users' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Marcus Webb",
  "email": "marcus@example.com",
  "password": "s3cure!"
}'
```

2. Response received:
```json
TODO: paste actual response here
```

## Step 2 - Priya registers an account

1. Curl statement called:
```bash
curl -X 'POST' \
  'https://OUR-RENDER-SERVICE.onrender.com/users' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Priya Nair",
  "email": "priya@example.com",
  "password": "hike4ever"
}'
```

2. Response received:
```json
TODO: paste actual response here
```

## Step 3 - Marcus creates the group

Use Marcus's actual `user_id` from Step 1 as `created_by`.

1. Curl statement called:
```bash
curl -X 'POST' \
  'https://OUR-RENDER-SERVICE.onrender.com/groups' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "SLO Hikers",
  "description": "Weekend trails in the Central Coast",
  "created_by": 1
}'
```

2. Response received:
```json
TODO: paste actual response here
```

## Step 4 - Priya joins the group

Use the actual `group_id` from Step 3 in the URL and Priya's actual `user_id` from Step 2 in the request body.

1. Curl statement called:
```bash
curl -X 'POST' \
  'https://OUR-RENDER-SERCICE.onrender.com/groups/1/members' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": 2
}'
```

2. Response received:
```json
TODO: paste actual response here
```

## Step 5 - Marcus promotes Priya to organizer

Use the actual `group_id` from Step 3 in the URL, Priya's actual `user_id` from Step 2 in the URL, and Marcus's actual `user_id` from Step 1 as `requested_by`.

1. Curl statement called:
```bash
curl -X 'PATCH' \
  'https://OUR-RENDER-SERVICE.onrender.com/groups/1/members/2' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "role": "organizer",
  "requested_by": 1
}'
```

2. Response received:
```json
TODO: paste actual response here
```
