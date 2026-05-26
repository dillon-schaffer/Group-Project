# Group-Project

Our idea is an Event and Group Coordination API. The main ideas is that it will let users create groups, manage membership, and organize events within those groups. On the user side, we store basic account information like name, email, and a password hash. Groups have an owner and support multiple members, each with a role of either member or organizer. Events belong to a group and track the details that actually matter, like location, start and end times, and capacity. The last piece is RSVPs, which let users respond to events with a status of going, maybe, or not going, and give organizers a way to track attendance. Together, these tables give our API a clean foundation for handling the full lifecycle of group coordination, from creating a group to filling seats at an event.

## Complex Endpoints

This project includes two complex endpoints that go beyond simple CRUD operations:

### 1. **GET /users/{user_id}/dashboard**
A comprehensive user dashboard that aggregates data across multiple tables:
- Fetches all groups with roles and member counts
- Shows upcoming events user is attending (RSVP = 'going')
- Lists events from user's groups they haven't RSVP'd to yet
- **Complexity**: Multiple JOINs across 5 tables (users, groups, group_memberships, events, rsvps), aggregations, date filtering, subqueries with NOT EXISTS

### 2. **GET /groups/{group_id}/analytics**
Sophisticated group analytics with business intelligence:
- Member statistics broken down by role (owner/organizer/member)
- Event statistics (total, active, cancelled, past, future)
- Calculates average RSVP rate: (total RSVPs / (events × members)) × 100
- Identifies top 5 most active members by events created + RSVPs
- **Complexity**: Multiple aggregations with conditional counting (COUNT CASE WHEN), cross joins, complex calculations, division by zero handling, date-based categorization

See [docs/APISpec.md](docs/APISpec.md) for complete documentation.

## Improvements from Peer Review

Based on feedback from peer reviews, we made the following improvements:

### Round 1: Schema & Validation
- Strengthened password requirements: 8-128 characters with uppercase, number, and special character  
- Added max_length constraints: All string fields now have reasonable upper bounds  
- Capacity upper bound: Events limited to 10,000 capacity  
- Event Update endpoint: PATCH /groups/{group_id}/events/{event_id} for modifying event details  
- RSVP pagination: GET /events/{event_id}/rsvps now supports limit/offset parameters  
- Removed duplicate files: Cleaned up root-level database.py and schemas.py  

### Round 2: Bug Fixes & New Endpoints
- Organizers can cancel events: Fixed permission check (previously only owners)  
- Capacity enforcement: Cannot RSVP "going" if event is at full capacity  
- Improved error messages: No longer exposes membership information  
- GET /users/{user_id}: Retrieve user profile  
- GET /users/{user_id}/events: Get all events user has RSVP'd to  
- GET /groups/{group_id}: Get group details and member count  
- GET /groups/{group_id}/members: List all group members with roles  
- GET /groups/{group_id}/events/{event_id}: Get single event details  

### Round 3: Testing & Code Quality
- Fixed test suite: Added X-API-Key header to test client - all 14 tests now pass  
- RSVP cleanup on member removal: RSVPs now deleted when user leaves group (per user story #12)  
- Self-removal capability: Members can now remove themselves from groups  
- Logging improvements: Replaced print() statements with proper logging  
- Sensitive data protection: Database credentials no longer logged in production  
- Test database exclusion: Added *.db to .gitignore  
- Complete API documentation: Fixed formatting and added all endpoints to APISpec.md  

### Already Implemented Correctly
- Group membership validation for RSVPs  
- Owner role protection (cannot be changed via API)  
- RSVP status validation using Literal types  
- Duplicate membership prevention  
- Capacity validation (rejects zero/negative values)  
- Event description field (optional, max 1000 chars)  

See [peer_review_response.md](peer_review_response.md) for detailed analysis of all feedback from 3 rounds of peer review.

## Setup

1. **Environment Variables**: Copy `.env.example` to `.env` and fill in your values:
   ```env
   API_KEY=your-secret-api-key
   POSTGRES_URI=postgresql://user:password@host:port/database
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Run Locally**:
   ```bash
   python main.py
   ```
   The API will be available at http://localhost:8000

## Deployment

### Render

**Start Command**:
```bash
uvicorn src.api.server:app --host 0.0.0.0 --port $PORT
```

**Environment Variables** (set in Render dashboard):
- `API_KEY` - Your secret API key for authentication
- `POSTGRES_URL` or `POSTGRES_URI` or `DATABASE_URL` - Your Supabase/PostgreSQL connection string

## API Documentation

Once running, visit:
- `/docs` - Interactive Swagger UI
- `/openapi.json` - OpenAPI specification

All endpoints (except `/`) require the `X-API-Key` header with your API key.
