# Performance Testing Writeup

## Fake Data Modeling

(setup commands)
python3 -m venv .venv
source .venv/bin/activate   
pip install -r requirements.txt
cp .env.example .env

(edit env)
API_KEY=local-dev-key
POSTGRES_URI=postgresql://postgres:postgres@localhost:5432/group_project

(start a local postgres in Docker)
docker run --name csc365-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=group_project \
  -p 5432:5432 -d postgres:16

alembic upgrade head

python fakedata.py

(For running the API)
uvicorn main:app --reload


The script we wrote to build the data is [fakedata.py](fakedata.py). It connects
to a local postgres, truncates the five tables, and then fills them back up using
Faker for the text fields and numpy distributions for the counts, so the data
comes out skewed in a realistic way instead of every group/event being the same
size. Users, groups, and events get inserted one at a time with RETURNING so we
can hang onto their ids for the foreign keys, and the two big tables
(group_memberships and rsvps) get collected into lists and bulk inserted.

Here's what we ended up with in each table:

users - 50,000
groups - 5,000 
group_memberships ~ 157,000 
events  ~ 50,000 
rsvps  ~ 797,000 
total ~ 1,059,000

(the membership/event/rsvp counts move around a little every run since they come
from random distributions, these are the numbers from our run. you can check your
own with `SELECT count(*) FROM rsvps;` etc.)

Our app is an event and group coordination service.
There are only so many actual users and groups, but each user
joins several groups and each event collects a whole pile of RSVPs, so those two
join tables are where almost all the rows live. We set it up so the average user
is in about 3 groups (groups average ~30 members) which gives ~157k memberships,
and each event pulls RSVPs from its group's members which gives ~797k rsvps.
Together memberships and rsvps are about 90% of the database, which feels right
for this kind of app.

users and groups grow roughly linearly with how popular
the app is, but memberships grow like users times groups per user, and rsvps grow
like events times attendees per event, so those two grow way faster than
everything else. RSVPs end up being the single biggest table because every active
member of a group can RSVP to every event that group puts on, and that's a
multiplying effect. So if our service blew up, the RSVP table is the one that
would balloon first, which makes it the realistic thing to stress test against.

A few details we made sure stayed realistic instead of totally random: RSVPs only
come from people who are actually members of that event's group, events are only
created by members of the group they belong to, and event start times are spread
across both the past and the future (the future ones matter because some of our
endpoints only care about upcoming events).
