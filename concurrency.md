# Concurrency Problems

## 1. Phantom Read / Write Skew: Too Many People RSVP

An event has a capacity, so we do not want more people marked as `going` than the event allows. Suppose an event has 10 seats and 9 people are already going. If two users RSVP at the same time, both transactions might count 9 people and think there is still one open spot. Then both insert their RSVP, and the event ends up with 11 people going.

```mermaid
sequenceDiagram
    participant UserA
    participant UserB
    participant API
    participant DBMS
    participant Events
    participant RSVPs

    UserA->>API: RSVP going for event 42
    API->>DBMS: Begin T1
    DBMS->>Events: Read capacity = 10
    DBMS->>RSVPs: Count going RSVPs = 9

    UserB->>API: RSVP going for event 42
    API->>DBMS: Begin T2
    DBMS->>Events: Read capacity = 10
    DBMS->>RSVPs: Count going RSVPs = 9

    DBMS->>RSVPs: T1 inserts UserA RSVP
    DBMS-->>API: Commit T1
    API-->>UserA: RSVP accepted

    DBMS->>RSVPs: T2 inserts UserB RSVP
    DBMS-->>API: Commit T2
    API-->>UserB: RSVP accepted

    Note over RSVPs: Event now has 11 going RSVPs even though capacity is 10
```

To prevent this, the RSVP transaction should lock the event row with `SELECT ... FOR UPDATE` before checking capacity and inserting/updating the RSVP. This works because capacity belongs to one event, so locking that one event forces RSVP decisions for that event to happen one at a time.

## 2. Non-Repeatable Read: RSVP During Event Cancellation

The RSVP endpoint checks if an event is active before accepting an RSVP. The cancel event endpoint changes the event status from `active` to `cancelled`. Without isolation, a user could start an RSVP transaction, see that the event is active, and then an owner could cancel the event before the RSVP transaction finishes. The RSVP might still get inserted even though the event is now cancelled.

```mermaid
sequenceDiagram
    participant Member
    participant Owner
    participant API
    participant DBMS
    participant Events
    participant RSVPs

    Member->>API: RSVP going for event 42
    API->>DBMS: Begin T1
    DBMS->>Events: T1 reads status = active

    Owner->>API: Cancel event 42
    API->>DBMS: Begin T2
    DBMS->>Events: T2 reads status = active
    DBMS->>Events: T2 updates status = cancelled
    DBMS-->>API: Commit T2
    API-->>Owner: Event cancelled

    DBMS->>RSVPs: T1 inserts RSVP
    DBMS-->>API: Commit T1
    API-->>Member: RSVP accepted

    Note over Events,RSVPs: A cancelled event received a new RSVP
```

To prevent this, both RSVP and cancellation should lock the same event row with `SELECT ... FOR UPDATE`. Then one transaction has to wait for the other. If the cancellation happens first, the RSVP transaction will see `cancelled` and reject the RSVP. If the RSVP happens first, then the cancellation happens after a valid RSVP update.

## 3. Read Skew / Phantom Read: Weird Analytics Results

The group analytics endpoint runs multiple queries. It counts members, counts events, calculates RSVP rate, and lists active members. If another transaction adds a member or RSVP while the analytics request is running, the report might use data from different moments in time.

For example, the first query might say the group has 10 members. Then another user gets added. A later query in the same analytics request might calculate RSVP rate using 11 members. The final response would not match one real version of the database.

```mermaid
sequenceDiagram
    participant Organizer
    participant NewMember
    participant API
    participant DBMS
    participant Memberships
    participant Events
    participant RSVPs

    Organizer->>API: View group analytics
    API->>DBMS: Begin T1
    DBMS->>Memberships: T1 counts 10 members
    DBMS->>Events: T1 counts events

    NewMember->>API: Join group
    API->>DBMS: Begin T2
    DBMS->>Memberships: T2 inserts new member
    DBMS-->>API: Commit T2
    API-->>NewMember: Member added

    DBMS->>Memberships: T1 counts 11 members for RSVP rate
    DBMS->>RSVPs: T1 reads RSVP totals
    DBMS-->>API: Commit T1
    API-->>Organizer: Analytics response

    Note over API: The response mixes old and new data
```

To prevent this, dashboard and analytics reads should use a `REPEATABLE READ READ ONLY` transaction. That gives the whole report one consistent snapshot of the database. It is a good choice because analytics does not need to block people from creating events or RSVPs; it just needs to show numbers that all come from the same point in time.

## What We Should Use

For RSVP and cancellation transactions, we should use row-level locks with `SELECT ... FOR UPDATE` on the event row. This protects the important event rules without locking the whole database.

For dashboard and analytics transactions, we should use `REPEATABLE READ READ ONLY` so the response is consistent.

We should also keep using database constraints like unique keys and primary keys. For example, `PRIMARY KEY (event_id, user_id)` on RSVPs prevents the same user from having two RSVP rows for the same event.
