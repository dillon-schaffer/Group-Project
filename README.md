# Group-Project

Our idea is an Event and Group Coordination API. The main ideas is that it will let users create groups, manage membership, and organize events within those groups. On the user side, we store basic account information like name, email, and a password hash. Groups have an owner and support multiple members, each with a role of either member or organizer. Events belong to a group and track the details that actually matter, like location, start and end times, and capacity. The last piece is RSVPs, which let users respond to events with a status of going, maybe, or not going, and give organizers a way to track attendance. Together, these tables give our API a clean foundation for handling the full lifecycle of group coordination, from creating a group to filling seats at an event.

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
- `POSTGRES_URI` - Your Supabase/PostgreSQL connection string

## API Documentation

Once running, visit:
- `/docs` - Interactive Swagger UI
- `/openapi.json` - OpenAPI specification

All endpoints (except `/`) require the `X-API-Key` header with your API key.
