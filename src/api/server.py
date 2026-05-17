from fastapi import FastAPI

from src.api import events, groups, rsvps, users

tags_metadata = [
    {"name": "users", "description": "User account management."},
    {"name": "groups", "description": "Group creation and membership management."},
    {"name": "events", "description": "Event creation and cancellation."},
    {"name": "rsvps", "description": "RSVP management for events."},
]

app = FastAPI(
    title="Event & Group Coordination API",
    description="API for managing groups, events, and RSVPs",
    version="2.0.0",
    openapi_tags=tags_metadata,
)

# Include all routers
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(events.router)
app.include_router(rsvps.router)


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Event & Group Coordination API"}
