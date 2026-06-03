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


## Performance Results 
GET /users/{user_id}
TIME_TOTAL_SEC: 0.002989

POST /users
TIME_TOTAL_SEC: 0.171721

GET /users/{user_id}/events
TIME_TOTAL_SEC: 0.024819

GET /users/{user_id}/dashboard
TIME_TOTAL_SEC: 0.037238

POST /groups
TIME_TOTAL_SEC: 0.006794

GET /groups/{group_id}
TIME_TOTAL_SEC: 0.004418

GET /groups/{group_id}/members
TIME_TOTAL_SEC: 0.009613

POST /groups/{group_id}/members
TIME_TOTAL_SEC: 0.007107

PATCH /groups/{group_id}/members/{user_id}
TIME_TOTAL_SEC: 0.004803


DELETE /groups/{group_id}/members/{user_id}
TIME_TOTAL_SEC: 0.000493

POST /groups/{group_id}/events
TIME_TOTAL_SEC: 0.004657

GET /groups/{group_id}/events/{event_id}
TIME_TOTAL_SEC: 0.002848

PATCH /groups/{group_id}/events/{event_id}
TIME_TOTAL_SEC: 0.003544

DELETE /groups/{group_id}/events/{event_id}
TIME_TOTAL_SEC: 0.003269

POST /events/{event_id}/rsvp
TIME_TOTAL_SEC: 0.005730

GET /events/{event_id}/rsvps
TIME_TOTAL_SEC: 0.005286

###SLOWEST
GET /groups/{group_id}/analytics
TIME_TOTAL_SEC: 0.040773



## Performance Tuning 

# Explain result:
                                                     QUERY PLAN                                                      
---------------------------------------------------------------------------------------------------------------------
 Index Scan using groups_pkey on groups  (cost=0.28..8.30 rows=1 width=23) (actual time=0.103..0.104 rows=1 loops=1)
   Index Cond: (group_id = 123)
   Buffers: shared hit=3
 Planning:
   Buffers: shared hit=64
 Planning Time: 0.722 ms
 Execution Time: 0.245 ms
(7 rows)

membership check
                                                                 QUERY PLAN                                                                  
---------------------------------------------------------------------------------------------------------------------------------------------
 Index Only Scan using pk_group_memberships on group_memberships  (cost=0.42..4.44 rows=1 width=4) (actual time=0.061..0.061 rows=0 loops=1)
   Index Cond: ((group_id = 123) AND (user_id = 456))
   Heap Fetches: 0
   Buffers: shared hit=3
 Planning:
   Buffers: shared hit=25
 Planning Time: 0.121 ms
 Execution Time: 0.068 ms
(8 rows)

member stats
                                                                   QUERY PLAN                                                                    
-------------------------------------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=62.01..62.02 rows=1 width=32) (actual time=0.019..0.019 rows=1 loops=1)
   Buffers: shared hit=4
   ->  Index Scan using pk_group_memberships on group_memberships  (cost=0.42..61.46 rows=31 width=7) (actual time=0.010..0.012 rows=20 loops=1)
         Index Cond: (group_id = 123)
         Buffers: shared hit=4
 Planning:
   Buffers: shared hit=12
 Planning Time: 0.067 ms
 Execution Time: 0.046 ms
(9 rows)

event stats
                                                QUERY PLAN                                                 
-----------------------------------------------------------------------------------------------------------
 Aggregate  (cost=1386.37..1386.38 rows=1 width=40) (actual time=5.473..5.474 rows=1 loops=1)
   Buffers: shared hit=753
   ->  Seq Scan on events  (cost=0.00..1386.06 rows=11 width=15) (actual time=0.201..5.466 rows=2 loops=1)
         Filter: (group_id = 123)
         Rows Removed by Filter: 50645
         Buffers: shared hit=753
 Planning:
   Buffers: shared hit=25
 Planning Time: 0.060 ms
 Execution Time: 5.492 ms
(10 rows)

rsvp rate
                                                                                QUERY PLAN                                                                                
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=2915.42..2915.43 rows=1 width=24) (actual time=4.336..4.337 rows=1 loops=1)
   Buffers: shared hit=881
   ->  Sort  (cost=2912.32..2913.09 rows=310 width=12) (actual time=4.303..4.305 rows=40 loops=1)
         Sort Key: e.event_id
         Sort Method: quicksort  Memory: 26kB
         Buffers: shared hit=881
         ->  Nested Loop Left Join  (cost=0.84..2899.49 rows=310 width=12) (actual time=0.183..4.239 rows=40 loops=1)
               Buffers: shared hit=878
               ->  Nested Loop  (cost=0.42..1521.54 rows=310 width=8) (actual time=0.153..4.163 rows=40 loops=1)
                     Buffers: shared hit=757
                     ->  Index Only Scan using pk_group_memberships on group_memberships gm  (cost=0.42..4.96 rows=31 width=4) (actual time=0.035..0.038 rows=20 loops=1)
                           Index Cond: (group_id = 123)
                           Heap Fetches: 0
                           Buffers: shared hit=4
                     ->  Materialize  (cost=0.00..1512.72 rows=10 width=4) (actual time=0.006..0.206 rows=2 loops=20)
                           Buffers: shared hit=753
                           ->  Seq Scan on events e  (cost=0.00..1512.67 rows=10 width=4) (actual time=0.114..4.111 rows=2 loops=1)
                                 Filter: ((group_id = 123) AND (status = 'active'::text))
                                 Rows Removed by Filter: 50645
                                 Buffers: shared hit=753
               ->  Index Only Scan using pk_rsvps on rsvps r  (cost=0.42..4.44 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=40)
                     Index Cond: ((event_id = e.event_id) AND (user_id = gm.user_id))
                     Heap Fetches: 0
                     Buffers: shared hit=121
 Planning:
   Buffers: shared hit=78
 Planning Time: 0.488 ms
 Execution Time: 4.373 ms
(28 rows)

most active members
                                                                                       QUERY PLAN                                                                                        
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Limit  (cost=3148.93..3148.94 rows=5 width=49) (actual time=4.143..4.145 rows=5 loops=1)
   Buffers: shared hit=1580 read=3
   ->  Sort  (cost=3148.93..3149.01 rows=31 width=49) (actual time=4.142..4.144 rows=5 loops=1)
         Sort Key: ((count(DISTINCT e.event_id) + count(DISTINCT r.event_id))) DESC
         Sort Method: top-N heapsort  Memory: 25kB
         Buffers: shared hit=1580 read=3
         ->  GroupAggregate  (cost=1502.68..3148.41 rows=31 width=49) (actual time=4.037..4.047 rows=20 loops=1)
               Group Key: u.user_id, gm.role
               Buffers: shared hit=1577 read=3
               ->  Incremental Sort  (cost=1502.68..3147.72 rows=31 width=33) (actual time=4.025..4.027 rows=24 loops=1)
                     Sort Key: u.user_id, gm.role, e.event_id
                     Presorted Key: u.user_id
                     Full-sort Groups: 1  Sort Method: quicksort  Average Memory: 26kB  Peak Memory: 26kB
                     Buffers: shared hit=1577 read=3
                     ->  Nested Loop Left Join  (cost=1447.88..3146.32 rows=31 width=33) (actual time=3.799..3.983 rows=24 loops=1)
                           Join Filter: (u.user_id = e.created_by)
                           Rows Removed by Join Filter: 46
                           Buffers: shared hit=1574 read=3
                           ->  Merge Left Join  (cost=1447.88..1755.12 rows=31 width=29) (actual time=1.779..1.957 rows=24 loops=1)
                                 Merge Cond: (u.user_id = r.user_id)
                                 Buffers: shared hit=821 read=3
                                 ->  Nested Loop  (cost=0.71..307.00 rows=31 width=25) (actual time=0.097..0.266 rows=20 loops=1)
                                       Buffers: shared hit=61 read=3
                                       ->  Index Scan using pk_group_memberships on group_memberships gm  (cost=0.42..61.46 rows=31 width=11) (actual time=0.007..0.010 rows=20 loops=1)
                                             Index Cond: (group_id = 123)
                                             Buffers: shared hit=4
                                       ->  Index Scan using users_pkey on users u  (cost=0.29..7.92 rows=1 width=18) (actual time=0.012..0.012 rows=1 loops=20)
                                             Index Cond: (user_id = gm.user_id)
                                             Buffers: shared hit=57 read=3
                                 ->  Sort  (cost=1447.17..1447.60 rows=172 width=8) (actual time=1.679..1.681 rows=24 loops=1)
                                       Sort Key: r.user_id
                                       Sort Method: quicksort  Memory: 25kB
                                       Buffers: shared hit=760
                                       ->  Nested Loop  (cost=0.42..1440.79 rows=172 width=8) (actual time=0.091..1.665 rows=24 loops=1)
                                             Buffers: shared hit=760
                                             ->  Seq Scan on events  (cost=0.00..1386.06 rows=11 width=4) (actual time=0.073..1.642 rows=2 loops=1)
                                                   Filter: (group_id = 123)
                                                   Rows Removed by Filter: 50645
                                                   Buffers: shared hit=753
                                             ->  Index Only Scan using pk_rsvps on rsvps r  (cost=0.42..4.78 rows=20 width=8) (actual time=0.009..0.010 rows=12 loops=2)
                                                   Index Cond: (event_id = events.event_id)
                                                   Heap Fetches: 0
                                                   Buffers: shared hit=7
                           ->  Materialize  (cost=0.00..1386.12 rows=11 width=8) (actual time=0.002..0.084 rows=2 loops=24)
                                 Buffers: shared hit=753
                                 ->  Seq Scan on events e  (cost=0.00..1386.06 rows=11 width=8) (actual time=0.029..2.003 rows=2 loops=1)
                                       Filter: (group_id = 123)
                                       Rows Removed by Filter: 50645
                                       Buffers: shared hit=753
 Planning:
   Buffers: shared hit=124
 Planning Time: 0.717 ms
 Execution Time: 4.201 ms
(53 rows)

Most of the analytics endpoint is already pretty fast because the group lookup and membership queries use primary key indexes. The main issue is the events table, where Postgres is doing sequential scans and checking all 50,647 events just to find the 2 events for group_id 123. This happens in multiple parts of the analytics endpoint, so it adds unnecessary work. The RSVP lookups are already using the primary key index, so I would first add an index on events(group_id):

CREATE INDEX idx_events_group_id ON events (group_id);

Explain after adding the index:

                                                     QUERY PLAN                                                      
---------------------------------------------------------------------------------------------------------------------
 Index Scan using groups_pkey on groups  (cost=0.28..8.30 rows=1 width=23) (actual time=0.060..0.061 rows=1 loops=1)
   Index Cond: (group_id = 123)
   Buffers: shared hit=3
 Planning:
   Buffers: shared hit=64
 Planning Time: 0.620 ms
 Execution Time: 0.171 ms
(7 rows)

membership check
                                                                 QUERY PLAN                                                                  
---------------------------------------------------------------------------------------------------------------------------------------------
 Index Only Scan using pk_group_memberships on group_memberships  (cost=0.42..4.44 rows=1 width=4) (actual time=0.047..0.047 rows=0 loops=1)
   Index Cond: ((group_id = 123) AND (user_id = 456))
   Heap Fetches: 0
   Buffers: shared hit=3
 Planning:
   Buffers: shared hit=25
 Planning Time: 0.159 ms
 Execution Time: 0.061 ms
(8 rows)

member stats
                                                                   QUERY PLAN                                                                    
-------------------------------------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=62.01..62.02 rows=1 width=32) (actual time=0.047..0.048 rows=1 loops=1)
   Buffers: shared hit=4
   ->  Index Scan using pk_group_memberships on group_memberships  (cost=0.42..61.46 rows=31 width=7) (actual time=0.027..0.032 rows=20 loops=1)
         Index Cond: (group_id = 123)
         Buffers: shared hit=4
 Planning:
   Buffers: shared hit=12
 Planning Time: 0.081 ms
 Execution Time: 0.087 ms
(9 rows)

event stats
                                                             QUERY PLAN                                                             
------------------------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=8.79..8.80 rows=1 width=40) (actual time=0.057..0.057 rows=1 loops=1)
   Buffers: shared hit=1 read=2
   ->  Index Scan using idx_events_group_id on events  (cost=0.29..8.48 rows=11 width=15) (actual time=0.050..0.051 rows=2 loops=1)
         Index Cond: (group_id = 123)
         Buffers: shared hit=1 read=2
 Planning:
   Buffers: shared hit=36 read=1
 Planning Time: 0.205 ms
 Execution Time: 0.087 ms
(9 rows)

rsvp rate
                                                                                QUERY PLAN                                                                                
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=1411.25..1411.26 rows=1 width=24) (actual time=0.203..0.204 rows=1 loops=1)
   Buffers: shared hit=131
   ->  Sort  (cost=1408.15..1408.93 rows=310 width=12) (actual time=0.182..0.185 rows=40 loops=1)
         Sort Key: e.event_id
         Sort Method: quicksort  Memory: 26kB
         Buffers: shared hit=131
         ->  Nested Loop Left Join  (cost=1.14..1395.32 rows=310 width=12) (actual time=0.068..0.140 rows=40 loops=1)
               Buffers: shared hit=128
               ->  Nested Loop  (cost=0.71..17.37 rows=310 width=8) (actual time=0.024..0.040 rows=40 loops=1)
                     Buffers: shared hit=7
                     ->  Index Only Scan using pk_group_memberships on group_memberships gm  (cost=0.42..4.96 rows=31 width=4) (actual time=0.011..0.014 rows=20 loops=1)
                           Index Cond: (group_id = 123)
                           Heap Fetches: 0
                           Buffers: shared hit=4
                     ->  Materialize  (cost=0.29..8.56 rows=10 width=4) (actual time=0.001..0.001 rows=2 loops=20)
                           Buffers: shared hit=3
                           ->  Index Scan using idx_events_group_id on events e  (cost=0.29..8.51 rows=10 width=4) (actual time=0.009..0.010 rows=2 loops=1)
                                 Index Cond: (group_id = 123)
                                 Filter: (status = 'active'::text)
                                 Buffers: shared hit=3
               ->  Index Only Scan using pk_rsvps on rsvps r  (cost=0.42..4.44 rows=1 width=8) (actual time=0.002..0.002 rows=1 loops=40)
                     Index Cond: ((event_id = e.event_id) AND (user_id = gm.user_id))
                     Heap Fetches: 0
                     Buffers: shared hit=121
 Planning:
   Buffers: shared hit=78
 Planning Time: 0.415 ms
 Execution Time: 0.241 ms
(28 rows)

most active members
                                                                                       QUERY PLAN                                                                                        
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Limit  (cost=383.67..383.68 rows=5 width=49) (actual time=0.346..0.348 rows=5 loops=1)
   Buffers: shared hit=83
   ->  Sort  (cost=383.67..383.75 rows=31 width=49) (actual time=0.345..0.347 rows=5 loops=1)
         Sort Key: ((count(DISTINCT e.event_id) + count(DISTINCT r.event_id))) DESC
         Sort Method: top-N heapsort  Memory: 25kB
         Buffers: shared hit=83
         ->  GroupAggregate  (cost=382.38..383.16 rows=31 width=49) (actual time=0.315..0.332 rows=20 loops=1)
               Group Key: u.user_id, gm.role
               Buffers: shared hit=80
               ->  Sort  (cost=382.38..382.46 rows=31 width=33) (actual time=0.295..0.297 rows=24 loops=1)
                     Sort Key: u.user_id, gm.role, e.event_id
                     Sort Method: quicksort  Memory: 26kB
                     Buffers: shared hit=80
                     ->  Hash Left Join  (cost=74.69..381.61 rows=31 width=33) (actual time=0.075..0.279 rows=24 loops=1)
                           Hash Cond: (u.user_id = e.created_by)
                           Buffers: shared hit=77
                           ->  Hash Left Join  (cost=66.07..372.48 rows=31 width=29) (actual time=0.056..0.255 rows=24 loops=1)
                                 Hash Cond: (u.user_id = r.user_id)
                                 Buffers: shared hit=74
                                 ->  Nested Loop  (cost=0.71..307.00 rows=31 width=25) (actual time=0.020..0.213 rows=20 loops=1)
                                       Buffers: shared hit=64
                                       ->  Index Scan using pk_group_memberships on group_memberships gm  (cost=0.42..61.46 rows=31 width=11) (actual time=0.003..0.006 rows=20 loops=1)
                                             Index Cond: (group_id = 123)
                                             Buffers: shared hit=4
                                       ->  Index Scan using users_pkey on users u  (cost=0.29..7.92 rows=1 width=18) (actual time=0.010..0.010 rows=1 loops=20)
                                             Index Cond: (user_id = gm.user_id)
                                             Buffers: shared hit=60
                                 ->  Hash  (cost=63.21..63.21 rows=172 width=8) (actual time=0.028..0.028 rows=24 loops=1)
                                       Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                       Buffers: shared hit=10
                                       ->  Nested Loop  (cost=0.71..63.21 rows=172 width=8) (actual time=0.008..0.014 rows=24 loops=1)
                                             Buffers: shared hit=10
                                             ->  Index Scan using idx_events_group_id on events  (cost=0.29..8.48 rows=11 width=4) (actual time=0.004..0.005 rows=2 loops=1)
                                                   Index Cond: (group_id = 123)
                                                   Buffers: shared hit=3
                                             ->  Index Only Scan using pk_rsvps on rsvps r  (cost=0.42..4.78 rows=20 width=8) (actual time=0.002..0.003 rows=12 loops=2)
                                                   Index Cond: (event_id = events.event_id)
                                                   Heap Fetches: 0
                                                   Buffers: shared hit=7
                           ->  Hash  (cost=8.48..8.48 rows=11 width=8) (actual time=0.009..0.009 rows=2 loops=1)
                                 Buckets: 1024  Batches: 1  Memory Usage: 9kB
                                 Buffers: shared hit=3
                                 ->  Index Scan using idx_events_group_id on events e  (cost=0.29..8.48 rows=11 width=8) (actual time=0.007..0.008 rows=2 loops=1)
                                       Index Cond: (group_id = 123)
                                       Buffers: shared hit=3
 Planning:
   Buffers: shared hit=124
 Planning Time: 0.544 ms
 Execution Time: 0.396 ms
(49 rows)


Before, the event queries were doing sequential scans over all 50,647 events just to find 2 events for group 123. After adding the index, those switched to Index Scan using idx_events_group_id, so Postgres can jump straight to the matching group’s events.

The main improvements were:

event stats went from 5.492 ms to 0.087 ms

rsvp rate went from 4.373 ms to 0.241 ms

most active members went from 4.201 ms to 0.396 ms
