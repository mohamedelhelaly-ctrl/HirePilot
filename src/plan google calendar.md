```
# Plan: Google OAuth Offline Access + Google Calendar Integration
```

## `## TL;DR` 

```
Upgrade from Google ID Token login to Authorization Code Flow to obtain and
store encrypted Google credentials. Build a calendar service layer to query HR
manager availability and schedule/reschedule/cancel interviews with automatic
Meet link generation and attendee notifications.
```

```
---
```

```
## Phase 1: OAuth Upgrade (Weeks 1-2)
```

```
### 1.1 Database Schema
```

```
- **Create** `GoogleOAuthCredential` table (id, user_id, google_account_email,
access_token [encrypted], refresh_token [encrypted], token_expiry)
- **Create** Alembic migration for schema
```

- `**Update** `InterviewSession`: verify google_calendar_event_id, google_meet_link fields exist` 

- `**Add** cryptography library to requirements.txt` 

```
### 1.2 Backend Services
```

- `**Create** `src/backend/controllers/services/google_oauth_service.py`: - `exchange_google_code_for_tokens(auth_code)` — swap code for Google access/refresh tokens` 

- ``get_valid_google_access_token(user_id)` — load stored credentials, autorefresh if expired` 

- ``store_google_oauth_credentials(...)` — encrypt and persist` 

- `**Update** `src/backend/controllers/services/auth_service.py`:` 

- `Replace `google_login(id_token)` → `google_login_code_flow(auth_code)`` 

- `Keep domain validation, user pre-registration check` 

- `**Update** `src/backend/controllers/services/security.py`:` 

- `Add token encryption/decryption with Fernet` 

- `**Create** `src/backend/models/crud/google_oauth_crud.py`:` 

- `CRUD: create, read, update, delete Google credentials` 

- `### 1.3 Frontend Authentication` 

- `**Update** `src/frontend/Incorta-HR-main/hr-ai-agent/src/pages/login.jsx`:` 

- `Switch from ID Token capture to Authorization Code Flow` 

- `Use `useGoogleLogin()` hook or redirect-based flow` 

- `Send auth code instead of ID token` 

## `- **Update**` 

- ``src/frontend/Incorta-HR-main/hr-ai-agent/src/services/authService.js`:` 

- `Change `googleLogin(idToken)` → `googleLogin(authCode)`` 

- `POST body: `{ authorization_code: "..." }`` 

- `### 1.4 API Endpoints` 

- `**Update** `src/backend/routers/auth_router.py`:` 

- `Endpoint `POST /api/auth/google` remains, request body schema changes` 

- `New schema: `AuthorizationCodeRequest` with `authorization_code` field` 

- `**Update** `src/backend/controllers/AuthController.py`:` 

- `Replace `google_auth(GoogleLoginRequest)` →` 

- ``google_auth(AuthorizationCodeRequest)`` 

## `### 1.5 Environment` 

- `**Update** `src/backend/helpers/config.py`:` 

- `Add: GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, ENCRYPTION_KEY` 

## `**Verification**:` 

- `Auth flow: send code → receive JWT → GET /me → confirmed` 

- `DB check: GoogleOAuthCredential created with encrypted tokens` 

- `Logout: POST /logout → tokens deleted` 

```
---
```

```
## Phase 2: Google Calendar Integration (Weeks 3-4)
```

```
### 2.1 Calendar Service Layer
```

```
- **Create** `src/backend/controllers/services/google_calendar_service.py`:
  - `get_availability(user_id, date_from, date_to, interview_type)` — query
Google Calendar, exclude weekends/busy times, return valid slots
  - `create_interview_event(user_id, candidate_email, ...)` — create Calendar
event + Meet link
```

- ``reschedule_event(...)` — update event (Google sends "updated" email)` 

- ``cancel_event(...)` — delete event (Google sends cancellation email)` 

```
- **Create** `src/backend/controllers/services/interview_scheduling_service.py`:
  - Orchestrates scheduling: call Google API, create/update InterviewSession
record
```

```
- **Config constants**:
  ```python
  INTERVIEW_DURATIONS = {"hr_screen": 30, "technical": 60, "behavioral": 45,
"final": 90}
  WORK_DAY_START, WORK_DAY_END = 9, 18
  ```
```

```
### 2.2 Calendar Router & Endpoints
```

- `**Create** `src/backend/routers/calendar_router.py`:` 

- ``GET /api/calendar/availability` — query: date_from, date_to, interview_type → response: [{start, end}, ...]` 

- ``POST /api/calendar/schedule-interview` — body: candidate_email, interview_type, start_time, end_time → creates event + InterviewSession` 

```
  - `PUT /api/calendar/interviews/{id}/reschedule` — reschedule with new times
  - `DELETE /api/calendar/interviews/{id}` — cancel (soft delete in DB, hard
delete in Google)
```

```
- **Create schemas** `src/backend/models/schemas/calendar_schemas.py`:
```

- `CalendarAvailabilityRequest, CalendarSlot, ScheduleInterviewRequest, InterviewSessionResponse` 

```
### 2.3 Database Updates
```

- `**Update** `src/backend/models/tables/interview_session.py`:` 

- `Add fields: `calendar_status` (Enum: PENDING, CONFIRMED, CANCELLED)` 

- `**Update** `src/backend/models/crud/interview_session_crud.py`:` 

- `Add: `update_interview_session_with_google_data()` to store event ID and meet link` 

```
### 2.4 Frontend Calendar UI (Phase 2)
```

- `**Create**` 

- ``src/frontend/Incorta-HR-main/hr-ai-agent/src/components/AvailabilityPicker.jsx` — date range + interview type selector - **Create**` 

- ``src/frontend/Incorta-HR-main/hr-ai-agent/src/components/InterviewScheduler.jsx` — slot list + selection flow` 

```
- **Update** candidate profile page — add "Schedule Interview" button + workflow
- **Update** HR dashboard — show scheduled interviews, reschedule/cancel buttons
```

```
### 2.5 Backend Integration
```

- `**Update** `src/backend/main.py`:` 

- `Import and include calendar_router` 

```
**Verification**:
```

- `Schedule interview → Google Calendar event created → meet link stored in DB - GET /calendar/availability → returns valid slots (no weekends, no conflicts, fits duration)` 

- `Reschedule → Google Calendar updated, candidate receives "updated" email` 

- `Cancel → Google Calendar deleted, candidate receives cancellation email` 

## `---` 

## `## Sequencing & Dependencies` 

```
**Phase 1 can run in parallel tracks**:
```

```
- **Track A** (Database): Alembic migrations (~5 hrs)
- **Track B** (Backend): Services + controllers (*depends on migrations
complete*, ~12 hrs)
```

- `**Track C** (Frontend): Auth flow update (*parallel with B*, ~3-4 hrs) - **Track D** (Testing): End-to-end (*depends on B+C*, ~2 hrs)` 

```
**Phase 2 starts after Phase 1 complete** (~16 hrs total)
```

```
**Total estimate**: ~35-40 hours development + testing
```

```
---
```

## `## Critical Files to Modify` 

## `### Backend` 

- ``src/backend/helpers/config.py` — env vars` 

- ``src/backend/controllers/services/security.py` — encryption` 

- ``src/backend/controllers/services/auth_service.py` — rewrite google_login()` 

- ``src/backend/routers/auth_router.py` — request schema change` 

- ``src/backend/models/schemas/auth_schemas.py` — new schemas` 

- `**CREATE**: google_oauth_service.py, google_oauth_crud.py, google_calendar_service.py (Phase 2), calendar_router.py (Phase 2)` 

## `### Frontend` 

- ``src/frontend/Incorta-HR-main/hr-ai-agent/src/pages/login.jsx` — auth code flow` 

- ``src/frontend/Incorta-HR-main/hr-ai-agent/src/services/authService.js` — API call update` 

```
### Database & Config
```

- ``.env` — add GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, ENCRYPTION_KEY` 

- ``requirements.txt` — add cryptography, google-auth-oauthlib, google-apipython-client` 

- `Alembic migrations — new GoogleOAuthCredential table` 

```
---
```

```
## Security & Decisions
```

- `✅ **Encrypted tokens at rest** — Fernet symmetric encryption` 

- `✅ **Separate GoogleOAuthCredential table** — extensible for future multi-account support` 

- `✅ **Authorization Code Flow** — most secure, prevents token leakage to frontend ✅ **Pre-registration only** — user must exist before OAuth login` 

- `✅ **Domain validation** — @incorta.com, @gmail.com only` 

- `✅ **Automatic token refresh** — transparent to business logic` 

- `✅ **Google handles notifications** — no custom email needed for Calendar invites/updates/cancellations` 

```
---
```

```
## Scope: Included vs. Excluded
```

```
**Included**:
```

- `OAuth code exchange + credential storage` 

- `Automatic Google token refresh` 

- `Calendar availability queries (exclude weekends, respect 9-18 working hours)` 

- `Interview event creation with Meet links` 

- `Reschedule + cancel with notifications` 

- `Role-based auth (HR_MANAGER, HIRING_MANAGER only)` 

```
**Excluded (Future)**:
```

- `Calendar sync (pulling past events into system)` 

- `Timezone handling (assumes single timezone for MVP)` 

- `Multi-account Google support per user` 

- `Candidate-initiated cancellations` 

- `Calendar analytics/reporting` 

```
---
```

```
## Open Questions for Refinement
```

`1. **Google OAuth Consent Screen**: Development or published mode? (Action: Set up Google Cloud project early)` 

`2. **Redirect URI**: Fixed localhost or environment-based? (Recommendation: environment-based via .env)` 

`3. **Interview Cancellation**: HR-only or candidate-initiated? (Current: HRonly)` 

`4. **Error Recovery**: If Google event creation succeeds but DB insert fails, should we rollback? (Recommendation: Yes, wrap in transaction)` 

```
---
```

```
## Detailed Implementation Breakdown
```

```
### Phase 1: Step-by-Step
```

```
#### Step 1.1a: Create Alembic Migration for GoogleOAuthCredential Table
```

```
- File: `alembic/versions/{timestamp}_create_google_oauth_credentials.py`
```

- `Schema:` 

```
  ```sql
  CREATE TABLE google_oauth_credentials (
      id INTEGER PRIMARY KEY,
      user_id INTEGER NOT NULL UNIQUE,
      google_account_email VARCHAR NOT NULL,
      access_token VARCHAR NOT NULL,  -- Encrypted with Fernet
      refresh_token VARCHAR NOT NULL,  -- Encrypted with Fernet
      token_expiry DATETIME NOT NULL,
      created_at DATETIME DEFAULT NOW(),
      updated_at DATETIME DEFAULT NOW(),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
  );
  ```
- Includes: `op.create_index()` on user_id and google_account_email
```

```
#### Step 1.1b: Create GoogleOAuthCredential SQLAlchemy Model
- File: `src/backend/models/tables/google_oauth_credential.py`
- Follows existing pattern (User, RefreshToken models)
- Relationship: `user = relationship("User",
back_populates="google_oauth_credential")`
- Add inverse relationship to User model: `google_oauth_credential =
relationship("GoogleOAuthCredential", back_populates="user", uselist=False)`
#### Step 1.2a: Add Encryption Utilities to security.py
- Import: `from cryptography.fernet import Fernet`
- Functions:
  ```python
```

```
  def encrypt_token(token: str, encryption_key: str) -> str:
      """Encrypt token with Fernet symmetric encryption."""
      f = Fernet(encryption_key.encode())
      return f.encrypt(token.encode()).decode()
```

```
  def decrypt_token(encrypted_token: str, encryption_key: str) -> str:
      """Decrypt token."""
      f = Fernet(encryption_key.encode())
      return f.decrypt(encrypted_token.encode()).decode()
  ```
```

```
- Load ENCRYPTION_KEY from config: `ENCRYPTION_KEY =
os.getenv("ENCRYPTION_KEY")`
```

```
#### Step 1.2b: Create google_oauth_service.py
- Functions:
  ```python
  async def exchange_google_code_for_tokens(auth_code: str) -> dict:
      """Exchange authorization code for Google access/refresh tokens."""
      # Use google-auth-oauthlib
      # 1. Create OAuth2 session
      # 2. POST to Google token endpoint with code
      # 3. Return {'access_token': '...', 'refresh_token': '...', 'expires_in':
3600}
  async def refresh_google_access_token(refresh_token: str) -> dict:
      """Use refresh token to get new access token."""
      # Return {'access_token': '...', 'expires_in': 3600}
```

```
  async def get_valid_google_access_token(db: AsyncSession, user_id: int) ->
str:
```

```
      """Load credentials, check expiry, auto-refresh if needed."""
      # 1. SELECT * FROM google_oauth_credentials WHERE user_id = ?
      # 2. IF token_expiry < now(): call refresh_google_access_token()
      # 3. UPDATE token in DB
      # 4. RETURN access_token
```

```
  async def store_google_oauth_credentials(db: AsyncSession, user_id: int,
email: str, access_token: str, refresh_token: str, expires_in: int) -> None:
      """Encrypt and store Google credentials."""
      # Encrypt tokens using encrypt_token()
      # Create or update GoogleOAuthCredential record
  ```
```

```
#### Step 1.2c: Rewrite google_login in auth_service.py
- Replace entire `google_login()` function
```

```
- New signature: `async def google_login(db: AsyncSession, auth_code: str) ->
Token:`
- Steps:
  1. `exchange_google_code_for_tokens(auth_code)` → get access_token,
refresh_token
  2. `verify_google_token_with_access_token(access_token)` → extract email,
profile
  3. Check domain: `is_email_allowed(email)`
  4. Check user exists: `user = await get_user_by_email(db, email)`
  5. Check active: `ensure_user_active(user)`
  6. Store credentials: `await store_google_oauth_credentials(...)`
  7. Generate JWT: `return await generate_auth_tokens(db, user)`
#### Step 1.3a: Update Frontend login.jsx
- Replace GoogleLogin component logic
- New approach (choose one):
```

```
  **Option A: useGoogleLogin Hook**
  ```jsx
```

```
  const login = useGoogleLogin({
    onSuccess: async (codeResponse) => {
      // codeResponse.code is the authorization code
      await authService.googleLogin(codeResponse.code);
    },
    flow: 'auth-code',
    scope: 'openid email profile https://www.googleapis.com/auth/calendar'
  });
  ```
  **Option B: Redirect Flow**
  - Generate OAuth URL with scopes
  - Redirect to Google consent screen
  - Handle callback in `/auth/callback` route
  - Extract code from query params
  - POST to backend
#### Step 1.3b: Update Frontend authService.js
- Change function: `export const googleLogin = async (authCode) => { ... }`
- Remove: `idToken` parameter
- Update API call: `POST /auth/google` with `{ authorization_code: authCode }`
#### Step 1.4a: Update auth_router.py
- Update schema import: `AuthorizationCodeRequest` instead of
`GoogleLoginRequest`
- Update endpoint docstring
- Update: `async def google_auth(request: AuthorizationCodeRequest, ...)`
#### Step 1.4b: Create auth_schemas.py additions
- New schema:
  ```python
  class AuthorizationCodeRequest(BaseModel):
      authorization_code: str
  ```
```

```
#### Step 1.5: Update config.py
- Add three new config fields:
  ```python
  GOOGLE_CLIENT_SECRET: str = ""
  GOOGLE_REDIRECT_URI: str = ""
  ENCRYPTION_KEY: str = ""
  ```
- Load from environment in Settings class
```

```
#### Step 1.5b: Create google_oauth_crud.py
- Functions:
  ```python
  async def create_google_oauth_credential(db: AsyncSession, user_id: int,
google_account_email: str, access_token: str, refresh_token: str, token_expiry:
datetime) -> GoogleOAuthCredential:
```

```
  async def get_google_oauth_credential(db: AsyncSession, user_id: int) ->
Optional[GoogleOAuthCredential]:
```

```
  async def update_google_oauth_credential(db: AsyncSession, user_id: int,
access_token: str, refresh_token: str, token_expiry: datetime) ->
GoogleOAuthCredential:
```

```
  async def delete_google_oauth_credential(db: AsyncSession, user_id: int) ->
None:
  ```
```

```
---
```

```
### Phase 2: Step-by-Step
#### Step 2.1a: Create google_calendar_service.py
- Functions:
  ```python
  async def get_availability(
      db: AsyncSession,
      user_id: int,
      date_from: str,  # ISO format
      date_to: str,
      interview_type: str  # "hr_screen", "technical", etc.
  ) -> List[dict]:
      """Query Google Calendar and return available interview slots."""
      # 1. Get duration from INTERVIEW_DURATIONS[interview_type]
      # 2. Get valid Google access token
      # 3. Build Google Calendar service
      # 4. Query busyTimes for date range
      # 5. Generate slots:
      #    - For each day (excluding weekends)
      #    - For each hour 9-18
      #    - Check if slot_duration fits without conflicts
      # 6. Return list of {start: ISO, end: ISO}
  async def create_interview_event(
      db: AsyncSession,
      user_id: int,
      candidate_email: str,
      candidate_name: str,
      interview_type: str,
      start_time: str,  # ISO format
      end_time: str,
      requisition_title: str,
      hr_manager_name: str
  ) -> tuple:
      """Create Google Calendar event with Meet link."""
      # 1. Get valid Google access token
      # 2. Build event object:
      #    - summary: "{requisition_title} - {interview_type} -
{candidate_name}"
      #    - description: details
      #    - attendees: [{email: candidate_email}, {email: hr_manager_email}]
      #    - conferenceData: {"entryPoints": [{"entryPointType": "video"}]}
      # 3. CREATE event via Google Calendar API
      # 4. RETURN (google_event_id, meet_link)
  async def reschedule_event(
      db: AsyncSession,
      user_id: int,
      google_event_id: str,
      new_start_time: str,
      new_end_time: str
  ) -> dict:
      """Update Google Calendar event (Google sends "updated" notification)."""
      # 1. Get valid access token
      # 2. UPDATE event with new times
      # 3. RETURN updated event details
  async def cancel_event(
      db: AsyncSession,
      user_id: int,
      google_event_id: str
  ) -> dict:
      """Delete Google Calendar event (Google sends cancellation email)."""
      # 1. Get valid access token
```

```
      # 2. DELETE event from Google Calendar
      # 3. RETURN confirmation
  ```
```

```
#### Step 2.1b: Create interview_scheduling_service.py
- Functions:
  ```python
  async def schedule_interview(
      db: AsyncSession,
      user_id: int,
      candidate_email: str,
      candidate_name: str,
      application_id: int,
      requisition_id: int,
      interview_type: str,
      start_time: str,
      end_time: str
  ) -> InterviewSessionSchema:
      """Orchestrate: create Google event + InterviewSession record."""
      # 1. Get candidate + requisition details (for email/title)
      # 2. CREATE Google Calendar event via google_calendar_service
      # 3. ON SUCCESS: CREATE InterviewSession with google_event_id, meet_link
      # 4. ON FAILURE: ROLLBACK (cancel Google event)
      # 5. RETURN InterviewSession with meet_link
  async def reschedule_interview(
      db: AsyncSession,
      user_id: int,
      interview_session_id: int,
      new_start_time: str,
      new_end_time: str
  ) -> InterviewSessionSchema:
      """Reschedule: update Google event + DB record."""
  async def cancel_interview(
      db: AsyncSession,
      user_id: int,
      interview_session_id: int
  ) -> dict:
      """Cancel: delete Google event + mark InterviewSession as CANCELLED."""
  ```
#### Step 2.2a: Create calendar_router.py
- Endpoints:
  ```python
  @router.get(
      "/availability",
      response_model=List[CalendarSlot],
      status_code=200,
      summary="Get Available Interview Slots",
      description="Query HR manager's Google Calendar for available slots"
  )
  async def get_availability(
      date_from: str,  # Query param: ISO date
      date_to: str,
      interview_type: str,  # "hr_screen", "technical", "behavioral", "final"
      current_user: User = Depends(get_current_user),
      db: AsyncSession = Depends(get_db)
  ) -> List[CalendarSlot]:
      """Get available interview slots based on HR manager's Google Calendar."""
      # Verify user is HR_MANAGER or HIRING_MANAGER
      # Call: await get_availability(db, current_user.id, date_from, date_to,
interview_type)
      # Return slots or error if no Google credentials
```

```
  @router.post(
      "/schedule-interview",
      response_model=InterviewSessionResponse,
      status_code=201,
      summary="Schedule Interview"
  )
  async def schedule_interview(
      request: ScheduleInterviewRequest,
      current_user: User = Depends(get_current_user),
      db: AsyncSession = Depends(get_db)
  ) -> InterviewSessionResponse:
      """Create Google Calendar event + InterviewSession."""
      # Verify user is HR_MANAGER or HIRING_MANAGER
      # Call interview_scheduling_service.schedule_interview()
      # Return InterviewSession with meet_link
  @router.put(
      "/interviews/{interview_id}/reschedule",
      response_model=InterviewSessionResponse,
      status_code=200
  )
  async def reschedule_interview(
      interview_id: int,
      request: RescheduleInterviewRequest,
      current_user: User = Depends(get_current_user),
      db: AsyncSession = Depends(get_db)
  ) -> InterviewSessionResponse:
      """Update Google Calendar event + InterviewSession."""
  @router.delete(
      "/interviews/{interview_id}",
      response_model=dict,
      status_code=200
  )
  async def cancel_interview(
      interview_id: int,
      current_user: User = Depends(get_current_user),
      db: AsyncSession = Depends(get_db)
  ) -> dict:
      """Delete Google Calendar event + mark InterviewSession as CANCELLED."""
  ```
```

```
#### Step 2.2b: Create calendar_schemas.py
- Schemas:
  ```python
  class CalendarSlot(BaseModel):
      start: str  # ISO datetime
      end: str
  class CalendarAvailabilityRequest(BaseModel):
      date_from: str
      date_to: str
      interview_type: str
  class ScheduleInterviewRequest(BaseModel):
      candidate_email: EmailStr
      candidate_name: str
      application_id: int
      requisition_id: int
      interview_type: str
      start_time: str  # ISO datetime
      end_time: str
```

```
  class RescheduleInterviewRequest(BaseModel):
      new_start_time: str
      new_end_time: str
  class InterviewSessionResponse(BaseModel):
      id: int
      google_event_id: str
      google_meet_link: str
      interview_type: str
      calendar_status: str
      scheduled_start_time: str
      scheduled_end_time: str
      # ... other fields
  ```
#### Step 2.3a: Update InterviewSession Model
- Add field: `calendar_status = Column(Enum(CalendarStatus),
default=CalendarStatus.PENDING)`
- Add Enum:
  ```python
  class CalendarStatus(str, Enum):
      PENDING = "pending"
      CONFIRMED = "confirmed"
      CANCELLED = "cancelled"
  ```
#### Step 2.3b: Update interview_session_crud.py
- Add function:
  ```python
  async def update_interview_session_with_google_data(
      db: AsyncSession,
      interview_session_id: int,
      google_event_id: str,
      google_meet_link: str,
      calendar_status: str
  ) -> InterviewSession:
      """Update InterviewSession with Google Calendar data."""
      # UPDATE interview_sessions SET google_calendar_event_id = ?,
google_meet_link = ?, calendar_status = ? WHERE id = ?
  ```
#### Step 2.4a: Create Frontend Components
- **AvailabilityPicker.jsx**:
  - Date range input (from/to)
  - Dropdown: interview type selector
  - Button: "Check Availability"
  - Calls: `GET /api/calendar/availability`
- **InterviewScheduler.jsx**:
  - Displays list of available slots
  - Each slot clickable
  - On select: calls `POST /api/calendar/schedule-interview`
  - Shows confirmation + Meet link
#### Step 2.5: Update main.py
- Add import: `from routers import calendar_router`
- Add: `app.include_router(calendar_router.router)`
---
## Testing Checklist
### Phase 1 Verification
```

- `[ ] Alembic migration runs successfully: `alembic upgrade head`` 

- `[ ] GoogleOAuthCredential table created with all fields` 

- `[ ] Backend startup successful with new env vars` 

- `[ ] POST /auth/google with valid auth code → 200 OK, returns JWT tokens` 

- `[ ] GoogleOAuthCredential record created with encrypted tokens` 

- `[ ] Verify tokens are encrypted: `SELECT access_token FROM google_oauth_credentials LIMIT 1` → garbled output` 

- `[ ] GET /auth/me with JWT token → 200 OK, returns user profile` 

- `[ ] POST /auth/refresh with refresh token → 200 OK, returns new JWT` 

- `[ ] POST /auth/logout → 200 OK, revokes tokens` 

- `[ ] POST /auth/logout then GET /auth/me → 401 Unauthorized` 

- `[ ] Frontend: Login flow → redirects to Google consent screen` 

- `[ ] Frontend: Capture auth code → POST to backend → receive tokens → redirect to /hr` 

## `### Phase 2 Verification` 

- `[ ] GET /api/calendar/availability with valid HR manager → 200 OK, returns slots` 

- `[ ] Available slots exclude weekends (no Saturday/Sunday)` 

- `[ ] Available slots within 9-18 working hours` 

- `[ ] Slot duration matches interview type (e.g., technical = 60 min)` 

- `[ ] POST /api/calendar/schedule-interview → 201 Created, event appears in HR's Google Calendar` 

- `[ ] Candidate receives email invitation with Meet link` 

- `[ ] InterviewSession record created with google_event_id + google_meet_link` 

- `[ ] PUT /api/calendar/interviews/{id}/reschedule → event updated in Google Calendar` 

- `[ ] Candidate receives "updated" email with new time` 

- `[ ] DELETE /api/calendar/interviews/{id} → event deleted from Google Calendar` 

- `[ ] Candidate receives cancellation email` 

- `[ ] Frontend: Schedule Interview button → availability picker → slot selection → confirmation` 

- `[ ] Frontend: Reschedule button → update times → confirmation` 

- `[ ] Frontend: Cancel button → confirmation → deleted from calendar` 

```
---
```

## `## Security Checklist` 

- `[ ] ENCRYPTION_KEY never logged or exposed` 

- `[ ] Google tokens encrypted at rest in DB` 

- `[ ] Google Client Secret never exposed to frontend` 

- `[ ] Authorization Code Flow prevents token leakage` 

- `[ ] Domain validation enforced (@incorta.com, @gmail.com)` 

- `[ ] Pre-registration required (no auto-create during OAuth)` 

- `[ ] Role-based access control: only HR_MANAGER/HIRING_MANAGER can access calendar endpoints` 

- `[ ] Token expiry checked before API calls (auto-refresh)` 

- `[ ] Refresh tokens hashed in DB (existing pattern)` 

- `[ ] HTTPS enforced in production` 

- `[ ] OAuth redirect URI must match frontend deployment URL` 

