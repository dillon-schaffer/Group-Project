"""create initial schema

Revision ID: 546d0e45e534
Revises: 
Create Date: 2026-05-04 15:29:46.768628

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '546d0e45e534'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            user_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_users_email UNIQUE (email)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE groups (
            group_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_groups_created_by_users
                FOREIGN KEY (created_by)
                REFERENCES users (user_id)
                ON DELETE RESTRICT
        );
        """
    )

    op.execute(
        """
        CREATE TABLE group_memberships (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_group_memberships PRIMARY KEY (group_id, user_id),
            CONSTRAINT fk_group_memberships_group_id_groups
                FOREIGN KEY (group_id)
                REFERENCES groups (group_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_group_memberships_user_id_users
                FOREIGN KEY (user_id)
                REFERENCES users (user_id)
                ON DELETE CASCADE,
            CONSTRAINT ck_group_memberships_role
                CHECK (role IN ('owner', 'organizer', 'member'))
        );
        """
    )

    op.execute(
        """
        CREATE TABLE events (
            event_id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            start_time TIMESTAMPTZ NOT NULL,
            end_time TIMESTAMPTZ NOT NULL,
            capacity INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_events_group_id_groups
                FOREIGN KEY (group_id)
                REFERENCES groups (group_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_events_created_by_users
                FOREIGN KEY (created_by)
                REFERENCES users (user_id)
                ON DELETE RESTRICT,
            CONSTRAINT ck_events_capacity_positive CHECK (capacity > 0),
            CONSTRAINT ck_events_time_range CHECK (end_time > start_time),
            CONSTRAINT ck_events_status CHECK (status IN ('active', 'cancelled'))
        );
        """
    )

    op.execute(
        """
        CREATE TABLE rsvps (
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_rsvps PRIMARY KEY (event_id, user_id),
            CONSTRAINT fk_rsvps_event_id_events
                FOREIGN KEY (event_id)
                REFERENCES events (event_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_rsvps_user_id_users
                FOREIGN KEY (user_id)
                REFERENCES users (user_id)
                ON DELETE CASCADE,
            CONSTRAINT ck_rsvps_status
                CHECK (status IN ('going', 'maybe', 'not going'))
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rsvps")
    op.execute("DROP TABLE IF EXISTS events")
    op.execute("DROP TABLE IF EXISTS group_memberships")
    op.execute("DROP TABLE IF EXISTS groups")
    op.execute("DROP TABLE IF EXISTS users")