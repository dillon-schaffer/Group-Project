import os
import random
from datetime import timedelta

import dotenv
import numpy as np
import sqlalchemy
from faker import Faker


def database_connection_url():
    dotenv.load_dotenv()
    # point this at a LOCAL postgres, not the hosted one
    uri = os.environ.get("POSTGRES_URI", "postgresql://postgres:postgres@localhost:5432/group_project")
    # we have psycopg v3 installed, so use the +psycopg driver
    if uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://"):]
    return uri


engine = sqlalchemy.create_engine(database_connection_url())
fake = Faker()
rng = np.random.default_rng()

DUMMY_HASH = "$2b$12$abcdefghijklmnopqrstuv"  # one fake hash for passwords, don't bcrypt 50k times
NUM_USERS = 50_000
NUM_GROUPS = 5_000

# skewed counts so a few groups are big/active and most are small
group_sizes = rng.negative_binomial(3, 0.09, NUM_GROUPS) + 1   # ~30 members each
events_per_group = rng.negative_binomial(1, 0.09, NUM_GROUPS)  # ~10 events each

with engine.begin() as conn:
    # wipe old data but keep the schema and its constraints
    conn.execute(sqlalchemy.text(
        "TRUNCATE rsvps, events, group_memberships, groups, users RESTART IDENTITY CASCADE"
    ))

    # Users
    print("creating users...")
    user_ids = []
    for i in range(NUM_USERS):
        if i % 5000 == 0:
            print(i)
        user_id = conn.execute(sqlalchemy.text(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (:name, :email, :hash, :created_at) RETURNING user_id"
        ), {
            "name": fake.name(),
            "email": fake.unique.email(),
            "hash": DUMMY_HASH,
            "created_at": fake.date_time_between(start_date="-3y"),
        }).scalar_one()
        user_ids.append(user_id)

    # Groups and their memberships (creator is the owner)
    print("creating groups and memberships...")
    group_members = {}
    for g in range(NUM_GROUPS):
        creator = random.choice(user_ids)
        group_id = conn.execute(sqlalchemy.text(
            "INSERT INTO groups (name, description, created_by, created_at) "
            "VALUES (:name, :description, :created_by, :created_at) RETURNING group_id"
        ), {
            "name": f"{fake.word().title()} {fake.word().title()} Group",
            "description": fake.sentence(),
            "created_by": creator,
            "created_at": fake.date_time_between(start_date="-3y"),
        }).scalar_one()

        members = {creator}
        while len(members) < group_sizes[g]:
            members.add(random.choice(user_ids))
        group_members[group_id] = list(members)

        memberships = [{
            "group_id": group_id,
            "user_id": uid,
            "role": "owner" if uid == creator else random.choice(["organizer", "member", "member", "member"]),
            "joined_at": fake.date_time_between(start_date="-3y"),
        } for uid in members]
        conn.execute(sqlalchemy.text(
            "INSERT INTO group_memberships (group_id, user_id, role, joined_at) "
            "VALUES (:group_id, :user_id, :role, :joined_at)"
        ), memberships)

    # Events (start times span past and future)
    print("creating events...")
    event_members = {}
    for group_id, members in group_members.items():
        for _ in range(int(events_per_group[group_id - 1])):
            start = fake.date_time_between(start_date="-6M", end_date="+6M")
            event_id = conn.execute(sqlalchemy.text(
                "INSERT INTO events (group_id, created_by, title, location, start_time, "
                "end_time, capacity, status, created_at) "
                "VALUES (:group_id, :created_by, :title, :location, :start_time, "
                ":end_time, :capacity, :status, :created_at) RETURNING event_id"
            ), {
                "group_id": group_id,
                "created_by": random.choice(members),
                "title": fake.sentence(nb_words=4),
                "location": fake.city(),
                "start_time": start,
                "end_time": start + timedelta(hours=random.randint(1, 5)),
                "capacity": random.randint(5, 500),
                "status": random.choices(["active", "cancelled"], [0.9, 0.1])[0],
                "created_at": fake.date_time_between(start_date="-1y"),
            }).scalar_one()
            event_members[event_id] = members

    # RSVPs (members of an event's group respond), bulk inserted at the end
    print("creating rsvps...")
    rsvp_counts = rng.negative_binomial(2, 0.09, len(event_members))  # ~20 per event
    rsvps = []
    for count, (event_id, members) in zip(rsvp_counts, event_members.items()):
        for uid in random.sample(members, min(len(members), int(count))):
            rsvps.append({
                "event_id": event_id,
                "user_id": uid,
                "status": random.choices(["going", "maybe", "not going"], [0.6, 0.25, 0.15])[0],
                "updated_at": fake.date_time_between(start_date="-6M"),
            })
    conn.execute(sqlalchemy.text(
        "INSERT INTO rsvps (event_id, user_id, status, updated_at) "
        "VALUES (:event_id, :user_id, :status, :updated_at)"
    ), rsvps)

total = NUM_USERS + NUM_GROUPS + sum(len(m) for m in group_members.values()) + len(event_members) + len(rsvps)
print("\ndone.")
print("users:", NUM_USERS)
print("groups:", NUM_GROUPS)
print("memberships:", sum(len(m) for m in group_members.values()))
print("events:", len(event_members))
print("rsvps:", len(rsvps))
print("total:", total)
