POST /users - Registers a new user (creates a new user_id)

GET /users/{user_id}/events

POST /groups - Create a new group (creator is auto assigned owner)

POST /groups/{group_id}/members - Request to join a group

DELETE /groups/{group_id}/members/{user_id} - Removes a member from a group

POST /groups/{group_id}/events - Creates an event within a group

DELETE /groups/{group_id}/events/{event_id} - Cancel an event

POST /events/{event_id}/rsvp - Submit or update an RVSP
