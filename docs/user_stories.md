User Stories
1. As a registered user, I want to create a new group with a name and description, so that I can organize a community around a shared interest or activity.
2. As a group owner, I want to assign the organizer role to a trusted member, so that I can delegate event management responsibilities without transferring full ownership.
3. As a registered user, I want to search for and request to join an existing group, so that I can participate in events organized by communities I care about.
4. As a group organizer, I want to create an event within my group by specifying a title, location, start time, end time, and capacity, so that members have all the information they need to attend.
5. As a group member, I want to RSVP to an event with a status of "going," "maybe," or "not going," so that organizers can plan attendance and I can track my own commitments.
6. As a group organizer, I want to view a list of all RSVPs for an event along with each member's status, so that I can gauge turnout and make logistical decisions like venue size or catering.
7. As a registered user, I want to view all upcoming events across every group I belong to, so that I can plan my schedule without checking each group individually.
8. As a group owner, I want to remove a member from my group, so that I can maintain a safe and appropriate community environment.
9. As a group organizer, I want to edit the details of an event I created — including its location, time, or capacity — so that I can keep members informed when plans change.
10. As a group organizer, I want to cancel an event, so that members are notified and no longer see it as an upcoming commitment.
11. As a registered user, I want to update my account information such as my display name or email address, so that my profile stays accurate and up to date.
12. As a group member, I want to leave a group I no longer wish to be part of, so that I stop receiving events and communications from that group.

Exceptions
1. Exception: Email already in use  
If a user attempts to register with an email that already exists, the system will return an error and prompt them to log in instead.
2. Exception: Invalid login credentials  
If a user enters an incorrect email or password, the system will deny access and display an error message.
3. Exception: Unauthorized group access  
If a user tries to view or interact with a group they are not a member of, the system will return an access denied error.
4. Exception: Insufficient permissions for role assignment  
If a non-owner attempts to assign roles, the system will reject the request and notify them they lack permission.
5. Exception: Insufficient permissions for event creation or modification  
If a non-organizer attempts to create, update, or delete an event, the system will deny the request.
6. Exception: Group not found  
If a group ID does not exist, the system will return a "group not found" error.
7. Exception: Event not found  
If a user tries to access or RSVP to a non-existent event, the system will return an error.
8. Exception: Invalid event input data  
If required fields (location, time, capacity) are missing or invalid, the system will reject the request and display validation errors.
9. Exception: Event time conflict  
If an event’s end time is before its start time, the system will reject the event creation or update.
10. Exception: Event capacity exceeded  
If an event has reached its capacity, additional "going" RSVPs will be blocked and the user will be notified.
11. Exception: Duplicate RSVP submission  
If a user submits multiple RSVPs for the same event, the system will update the existing RSVP instead of creating duplicates.
12. Exception: User leaves group with active RSVPs  
If a user leaves a group, all of their RSVPs for that group’s events will be automatically removed.