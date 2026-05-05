"""
Test suite for Group and Event Coordination API
"""
import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from main import app

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency with test database"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def test_db():
    """Create a fresh database for each test"""
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after test
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(test_db):
    """Get test client with overridden database"""
    from database import get_db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_user(client):
    """Test that creating a user returns the correct user_id"""
    response = client.post(
        "/users",
        json={
            "name": "Marcus Webb",
            "email": "marcus@example.com",
            "password": "s3cure!"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert data["user_id"] == 1


def test_create_duplicate_user(client):
    """Test that creating a user with duplicate email fails"""
    # Create first user
    client.post(
        "/users",
        json={
            "name": "Marcus Webb",
            "email": "marcus@example.com",
            "password": "s3cure!"
        }
    )
    
    # Try to create duplicate
    response = client.post(
        "/users",
        json={
            "name": "Marcus Webb 2",
            "email": "marcus@example.com",
            "password": "different"
        }
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_group(client):
    """Test that creating a group assigns the creator as owner"""
    # Create user first
    user_response = client.post(
        "/users",
        json={
            "name": "Marcus Webb",
            "email": "marcus@example.com",
            "password": "s3cure!"
        }
    )
    user_id = user_response.json()["user_id"]
    
    # Create group
    response = client.post(
        "/groups",
        json={
            "name": "SLO Hikers",
            "description": "Weekend trails in the Central Coast",
            "created_by": user_id
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["group_id"] == 1
    assert data["owner_id"] == user_id


def test_create_group_nonexistent_user(client):
    """Test that creating a group with non-existent user fails"""
    response = client.post(
        "/groups",
        json={
            "name": "SLO Hikers",
            "description": "Weekend trails",
            "created_by": 999  # User doesn't exist
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_add_member_to_group(client):
    """Test that adding a member to a group works correctly"""
    # Create two users
    marcus = client.post("/users", json={"name": "Marcus Webb", "email": "marcus@example.com", "password": "pass1"})
    priya = client.post("/users", json={"name": "Priya Nair", "email": "priya@example.com", "password": "pass2"})
    
    marcus_id = marcus.json()["user_id"]
    priya_id = priya.json()["user_id"]
    
    # Marcus creates group
    group_response = client.post("/groups", json={"name": "SLO Hikers", "created_by": marcus_id})
    group_id = group_response.json()["group_id"]
    
    # Priya joins
    response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": priya_id}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["group_id"] == group_id
    assert data["user_id"] == priya_id
    assert data["role"] == "member"


def test_add_duplicate_member(client):
    """Test that adding the same member twice fails"""
    # Create user and group
    user = client.post("/users", json={"name": "Marcus", "email": "marcus@example.com", "password": "pass"})
    user_id = user.json()["user_id"]
    
    group = client.post("/groups", json={"name": "Group", "created_by": user_id})
    group_id = group.json()["group_id"]
    
    # Try to add Marcus again (he's already owner)
    response = client.post(
        f"/groups/{group_id}/members",
        json={"user_id": user_id}
    )
    
    assert response.status_code == 409
    assert "already a member" in response.json()["detail"]


def test_promote_member_to_organizer(client):
    """Test that owner can promote member to organizer"""
    # Create users
    marcus = client.post("/users", json={"name": "Marcus", "email": "marcus@example.com", "password": "pass"})
    priya = client.post("/users", json={"name": "Priya", "email": "priya@example.com", "password": "pass"})
    
    marcus_id = marcus.json()["user_id"]
    priya_id = priya.json()["user_id"]
    
    # Create group and add Priya
    group = client.post("/groups", json={"name": "SLO Hikers", "created_by": marcus_id})
    group_id = group.json()["group_id"]
    
    client.post(f"/groups/{group_id}/members", json={"user_id": priya_id})
    
    # Promote Priya
    response = client.patch(
        f"/groups/{group_id}/members/{priya_id}",
        json={"role": "organizer", "requested_by": marcus_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "organizer"
    assert data["user_id"] == priya_id


def test_non_owner_cannot_promote(client):
    """Test that non-owner cannot promote members"""
    # Create users
    marcus = client.post("/users", json={"name": "Marcus", "email": "marcus@example.com", "password": "pass"})
    priya = client.post("/users", json={"name": "Priya", "email": "priya@example.com", "password": "pass"})
    jordan = client.post("/users", json={"name": "Jordan", "email": "jordan@example.com", "password": "pass"})
    
    marcus_id = marcus.json()["user_id"]
    priya_id = priya.json()["user_id"]
    jordan_id = jordan.json()["user_id"]
    
    # Marcus creates group, Priya and Jordan join
    group = client.post("/groups", json={"name": "Group", "created_by": marcus_id})
    group_id = group.json()["group_id"]
    
    client.post(f"/groups/{group_id}/members", json={"user_id": priya_id})
    client.post(f"/groups/{group_id}/members", json={"user_id": jordan_id})
    
    # Priya (member) tries to promote Jordan
    response = client.patch(
        f"/groups/{group_id}/members/{jordan_id}",
        json={"role": "organizer", "requested_by": priya_id}
    )
    
    assert response.status_code == 403
    assert "Only group owners" in response.json()["detail"]


def test_create_event(client):
    """Test that organizer can create an event"""
    # Create user and group
    user = client.post("/users", json={"name": "Priya", "email": "priya@example.com", "password": "pass"})
    user_id = user.json()["user_id"]
    
    group = client.post("/groups", json={"name": "SLO Hikers", "created_by": user_id})
    group_id = group.json()["group_id"]
    
    # Create event
    response = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": user_id,
            "title": "Bishop Peak Morning Hike",
            "location": "Bishop Peak Trailhead, SLO",
            "start_time": "2026-05-10T08:00:00",
            "end_time": "2026-05-10T12:00:00",
            "capacity": 10
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] == 1
    assert data["group_id"] == group_id
    assert data["capacity"] == 10


def test_member_cannot_create_event(client):
    """Test that regular members cannot create events"""
    # Create users
    owner = client.post("/users", json={"name": "Owner", "email": "owner@example.com", "password": "pass"})
    member = client.post("/users", json={"name": "Member", "email": "member@example.com", "password": "pass"})
    
    owner_id = owner.json()["user_id"]
    member_id = member.json()["user_id"]
    
    # Owner creates group, member joins
    group = client.post("/groups", json={"name": "Group", "created_by": owner_id})
    group_id = group.json()["group_id"]
    
    client.post(f"/groups/{group_id}/members", json={"user_id": member_id})
    
    # Member tries to create event
    response = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": member_id,
            "title": "Hike",
            "location": "Trail",
            "start_time": "2026-05-10T08:00:00",
            "end_time": "2026-05-10T12:00:00",
            "capacity": 10
        }
    )
    
    assert response.status_code == 403
    assert "owners and organizers" in response.json()["detail"]


def test_create_rsvp(client):
    """Test that group member can RSVP to event"""
    # Create user, group, and event
    user = client.post("/users", json={"name": "Marcus", "email": "marcus@example.com", "password": "pass"})
    user_id = user.json()["user_id"]
    
    group = client.post("/groups", json={"name": "Group", "created_by": user_id})
    group_id = group.json()["group_id"]
    
    event = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": user_id,
            "title": "Event",
            "location": "Place",
            "start_time": "2026-05-10T08:00:00",
            "end_time": "2026-05-10T12:00:00",
            "capacity": 10
        }
    )
    event_id = event.json()["event_id"]
    
    # RSVP
    response = client.post(
        f"/events/{event_id}/rsvp",
        json={"user_id": user_id, "status": "going"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event_id
    assert data["user_id"] == user_id
    assert data["status"] == "going"


def test_non_member_cannot_rsvp(client):
    """Test that non-members cannot RSVP to events"""
    # Create two users
    owner = client.post("/users", json={"name": "Owner", "email": "owner@example.com", "password": "pass"})
    outsider = client.post("/users", json={"name": "Outsider", "email": "outsider@example.com", "password": "pass"})
    
    owner_id = owner.json()["user_id"]
    outsider_id = outsider.json()["user_id"]
    
    # Owner creates group and event
    group = client.post("/groups", json={"name": "Group", "created_by": owner_id})
    group_id = group.json()["group_id"]
    
    event = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": owner_id,
            "title": "Event",
            "location": "Place",
            "start_time": "2026-05-10T08:00:00",
            "end_time": "2026-05-10T12:00:00",
            "capacity": 10
        }
    )
    event_id = event.json()["event_id"]
    
    # Outsider tries to RSVP
    response = client.post(
        f"/events/{event_id}/rsvp",
        json={"user_id": outsider_id, "status": "going"}
    )
    
    assert response.status_code == 403
    assert "group members" in response.json()["detail"]


def test_update_rsvp(client):
    """Test that user can update their RSVP status"""
    # Create user, group, and event
    user = client.post("/users", json={"name": "User", "email": "user@example.com", "password": "pass"})
    user_id = user.json()["user_id"]
    
    group = client.post("/groups", json={"name": "Group", "created_by": user_id})
    group_id = group.json()["group_id"]
    
    event = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": user_id,
            "title": "Event",
            "location": "Place",
            "start_time": "2026-05-10T08:00:00",
            "end_time": "2026-05-10T12:00:00",
            "capacity": 10
        }
    )
    event_id = event.json()["event_id"]
    
    # Initial RSVP
    client.post(f"/events/{event_id}/rsvp", json={"user_id": user_id, "status": "going"})
    
    # Update RSVP
    response = client.post(
        f"/events/{event_id}/rsvp",
        json={"user_id": user_id, "status": "maybe"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "maybe"


def test_event_invalid_time_range(client):
    """Test that event with end_time before start_time fails"""
    user = client.post("/users", json={"name": "User", "email": "user@example.com", "password": "pass"})
    user_id = user.json()["user_id"]
    
    group = client.post("/groups", json={"name": "Group", "created_by": user_id})
    group_id = group.json()["group_id"]
    
    # Try to create event with invalid times
    response = client.post(
        f"/groups/{group_id}/events",
        json={
            "created_by": user_id,
            "title": "Event",
            "location": "Place",
            "start_time": "2026-05-10T12:00:00",
            "end_time": "2026-05-10T08:00:00",  # Before start time
            "capacity": 10
        }
    )
    
    assert response.status_code == 400
    assert "after start time" in response.json()["detail"]
