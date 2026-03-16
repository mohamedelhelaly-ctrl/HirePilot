# Incorta-HR: Project Specification
> Living context document for AI coding assistants. Describes scope, architecture, and behavior — not implementation details.

---

## 1. What This System Does

Incorta-HR is an AI-powered recruitment assistant built for Incorta's internal HR team. It automates candidate screening, assessment dispatch, interview scheduling, live interview support, and candidate ranking — all integrated with Lever (ATS), HackerRank (assessments), and Google Calendar.

The system has two user-facing roles:
- **HR Manager** — full access to all requisitions, candidates, and actions
- **Hiring Manager** — scoped access to their assigned requisitions; can conduct technical interviews and query the RAG chatbot

---

## 2. Tech Stack (High-Level)

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Orchestration | LangGraph |
| Primary Database | PostgreSQL |
| Vector Database | Chroma |
| Cache / Sessions | Redis |
| LLM | Claude or Gemini (configurable) |
| Embeddings | Sentence-BERT |
| Speech-to-Text | Whisper |
| ATS | Lever (API + Webhooks) |
| Assessment | HackerRank API |
| Calendar | Google Calendar API + Google Meet |
| Frontend | React + TypeScript + TailwindCSS |
| Auth | JWT (access + refresh tokens) |
| Real-time | WebSockets |
| Background Jobs | APScheduler |

---

## 3. Repository Structure

```
incorta-hr/
├── backend/
│   ├── app/
│   │   ├── api/          # REST + WebSocket endpoint routers
│   │   ├── db/           # ORM models + CRUD modules
│   │   ├── graphs/       # LangGraph orchestrator + all subgraphs
│   │   ├── services/     # Clients for Lever, HackerRank, Google Calendar, Whisper, LLM, Chroma
│   │   ├── schemas/      # Pydantic request/response models
│   │   └── utils/        # Auth helpers, scheduler, webhook validation
│   ├── alembic/          # Database migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/   # UI components
│       ├── pages/        # Route-level pages
│       ├── hooks/        # Custom hooks (WebSocket, auth, data fetching)
│       └── services/     # API client wrappers
└── docker-compose.yml
```

---

## 4. Database — PostgreSQL

All data is stored in PostgreSQL. Migrations are managed with Alembic.

### Tables Overview

| Table | Purpose |
|---|---|
| `users` | HR Managers and Hiring Managers with roles |
| `requisitions` | Job openings synced from Lever, includes batch processing counters and thresholds |
| `candidates` | Immutable personal profile (one per individual, reused across applications) |
| `applications` | Links a candidate to a requisition; holds all mutable state — status, scores, assessment data, interview data |
| `application_details` | Normalized CV fields extracted by AI (skills, experience, education) for fast filtering |
| `screening_results` | Detailed AI screening breakdown per application (technical score, behavioral score, justifications) |
| `interview_sessions` | Scheduled and completed interviews; stores pre-generated questions, transcript, summary, and scores |
| `transcript_chunks` | Real-time transcript pieces stored as they arrive during a live interview |
| `status_history` | Immutable audit trail of every status change per application |
| `webhook_events` | Log of all incoming Lever webhooks for idempotency and debugging |
| `refresh_tokens` | Active JWT refresh tokens |

### Key Relationships
- A `requisition` has many `applications`
- A `candidate` has many `applications` (one per requisition they applied to)
- An `application` has one `screening_result`, many `application_details`, many `interview_sessions`, many `status_history` records
- An `interview_session` has many `transcript_chunks`

### Batch Processing Counters
The `requisitions` table tracks three counters that drive automated re-screening:
- `new_candidate_counter` — increments on each new application
- `new_assessment_counter` — increments when an assessment is completed
- `new_interview_counter` — increments when an interview is completed

Each counter has a configurable threshold. When a counter hits its threshold, it triggers the appropriate batch re-screening workflow and then resets.

---

## 5. Vector Database — Chroma

Chroma stores CV embeddings and interview transcript embeddings. It enables semantic search across all candidate data — used by both the batch screening pipeline and the RAG chatbot.

- CVs are chunked and embedded, stored with metadata linking back to the application
- Transcripts are embedded after interview completion
- Similarity search is performed against a job description embedding to find the most relevant candidates

---

## 6. External Service Integrations

### Lever (ATS)
Two-way integration. The system receives webhook events from Lever and writes data back.

**Webhooks received:**
- New requisition created
- New candidate application
- Candidate stage changed
- Assessment completed
- Note added

**Data written back to Lever:**
- AI screening scores (as tags)
- Candidate stage updates (when sending assessments or scheduling interviews)
- Interview notes (post-interview summary)

### HackerRank
Used to create and send technical assessments. When HR dispatches an assessment, the system creates a test via the HackerRank API and stores the test link. Results flow back through a Lever webhook.

### Google Calendar
Used for interview scheduling. The system checks the interviewer's calendar for free slots, presents them to HR, and upon selection creates a Google Meet event and sends invites to both the candidate and interviewer.

### Whisper (STT)
Used during live interviews. Audio streamed from the browser over a WebSocket is transcribed in near-real-time and stored as transcript chunks.

---

## 7. API Layer — FastAPI

The API has three types of endpoints:

**REST endpoints** handle standard CRUD and action requests:
- Auth (login, logout, token refresh)
- Requisitions (list, get, trigger manual screening)
- Candidates/Applications (list ranked, get detail, update status)
- Assessments (send assessment, get result)
- Interviews (get availability, schedule, start, end, get summary)
- RAG Chat (submit query, receive answer with citations)
- Webhooks (Lever event receiver)

**WebSocket endpoints** handle real-time communication:
- `/ws/requisitions/{req_id}` — pushes live candidate table updates when a batch screening completes
- `/ws/interview/{session_id}` — bidirectional; receives audio chunks from the browser, pushes back transcript text and follow-up questions

All endpoints are protected by JWT authentication. Role-based access control is enforced per endpoint.

---

## 8. LangGraph Orchestration

All AI-driven workflows run through LangGraph. The architecture consists of one main orchestrator graph and six specialized subgraphs.

LangGraph is chosen because the workflows require conditional routing, loops, human-in-the-loop pauses, and long-running background processes — none of which work well in simple linear chains.

### State Management
Each graph and subgraph has its own typed state schema. State is passed between nodes and subgraphs explicitly. Redis is used to hold transient runtime state (e.g., whether an interview is still active).

---

### 8.1 Main Orchestrator Graph

The single entry point for all requests. It receives an intent — from a user action, an incoming webhook, or a scheduled background job — and routes it to the correct subgraph.

**Routing paths:**
- `background_job` → Batch Screening Subgraph
- `webhook_event` → webhook handler node, which fans out to:
  - New application → increment counter, check threshold, optionally trigger batch screening
  - Assessment result → store score, increment counter, check threshold, optionally trigger re-ranking
  - Stage change → update application status in DB
  - Other → log event
- `live_interview` → Live Interview Subgraph
- `schedule_interview` → Interview Scheduling Subgraph
- `send_assessment` → Assessment Dispatch Subgraph
- `rag_query` → RAG Query Subgraph
- `view_candidates` → simple DB read node (no LLM involved; data is pre-computed)

After any subgraph completes, the orchestrator handles syncing results to Lever and/or pushing updates to the frontend where applicable, then terminates.

---

### 8.2 Batch Screening Subgraph

**What it does:** Scores and ranks all candidates for a requisition in a single batch operation.

**Triggered by:** A counter hitting its threshold, a 24-hour scheduled run, a new requisition being created, or a manual HR trigger.

**Flow:**
1. Check whether the batch threshold is met. If not, exit early and queue for later.
2. Fetch the job description from Lever.
3. Fetch all candidate profiles and download their CVs from Lever.
4. Extract text from CV files (PDF/DOCX/TXT) in parallel.
5. Generate embeddings for each CV and store them in Chroma.
6. Perform a similarity search between all CV embeddings and the job description embedding to find the top candidates by cosine similarity.
7. Send the top candidates to the LLM in a single batch call. The LLM scores each one and produces a justification, a technical score, and a behavioral/cultural score.
8. Compute a combined score from cosine similarity, technical score, and behavioral score.
9. Store all results in the database.
10. Reset the candidate counter.
11. Sync updated scores back to Lever.
12. If any HR user is currently viewing this requisition's pipeline, push a live update over WebSocket.

**Key design decisions:**
- CV downloads and text extraction are parallelized.
- All top candidates are sent to the LLM in a single batch call to minimize API costs.
- A Redis lock prevents two concurrent batch runs for the same requisition.
- If the LLM fails for any candidate, their cosine score is used as a fallback.

---

### 8.3 Assessment Dispatch Subgraph

**What it does:** Validates a candidate's eligibility, creates a HackerRank test, and triggers delivery via Lever.

**Triggered by:** HR Manager clicking "Send Assessment" for a specific candidate.

**Flow:**
1. Validate that the candidate is in a valid stage to receive an assessment (not already sent, not at a later stage).
2. If invalid, return an error immediately.
3. Fetch the candidate's full profile from the database.
4. Create a test via the HackerRank API and receive a test link.
5. In parallel:
   - Update the candidate's stage in Lever to "Assessment Sent" — this triggers Lever's built-in email automation which delivers the HackerRank link to the candidate.
   - Set up a webhook listener to watch for the assessment completion event.
   - Update the candidate's status in the database to `assessment_sent`.
6. Wait for all parallel updates to complete.
7. Return success confirmation to the HR Manager.

Assessment results arrive later via a Lever webhook, which flows through the orchestrator and into a re-ranking batch check.

---

### 8.4 Interview Scheduling Subgraph

**What it does:** Finds available time slots, pauses for HR approval, then creates a calendar event and generates interview questions.

**Triggered by:** HR Manager clicking "Schedule Interview" for a candidate.

**Human-in-the-loop:** This subgraph uses LangGraph's `interrupt()` to pause execution and wait for HR to select a time slot before continuing.

**Flow:**
1. Fetch the candidate's stated availability from the database.
2. Check the assigned interviewer's Google Calendar for free slots.
3. Find overlapping time slots.
4. If no slots exist, suggest alternative dates/times and interrupt — wait for HR input.
5. If slots are found, present them to HR and interrupt — wait for HR to select one.
6. Graph resumes when HR submits their selection.
7. Fetch the candidate's CV and assessment data, plus the job description.
8. Generate tailored interview questions using the LLM, based on the candidate's CV, assessment results, job description, and interview type (HR screen vs. technical).
9. In parallel:
   - Create a Google Calendar event with a Meet link; include the interview questions and candidate CV link in the event description.
   - Update the database (create an `interview_session` record, store the questions and calendar event ID).
   - Update the candidate's stage in Lever.
10. Send calendar invites to both the candidate and the interviewer.
11. Return meeting details and confirmation to HR.

---

### 8.5 Live Interview Subgraph

**What it does:** Provides a real-time interview copilot — transcribing audio, periodically generating follow-up questions, and producing a summary when the interview ends.

**Triggered by:** HR or Hiring Manager clicking "Start Interview" in their dashboard.

**Design:** This is a **cyclic graph**. The transcription loop repeats continuously until the interviewer ends the session.

**Flow:**
1. Fetch the interview context from the database (candidate CV, assessment score, job description, pre-generated questions).
2. Initialize the WebSocket session and create a session record in the database with status `in_progress`.
3. Display the pre-generated questions to the interviewer.
4. **Enter the transcription loop:**
   - Receive an audio chunk from the browser over WebSocket.
   - Send it to Whisper for transcription.
   - Append the resulting text chunk to the database.
   - Check whether 30 seconds have elapsed since the last analysis.
   - If not, continue receiving audio (loop back).
   - If yes:
     - Send the transcript so far to the LLM. It analyzes topic coverage, answer quality, and gaps, then generates one contextual follow-up question.
     - Push the follow-up question to the interviewer's screen via WebSocket.
     - Store it in the session record.
     - Reset the analysis timer and continue the loop.
5. When the interviewer clicks "End Interview" (received as a WebSocket message), the loop exits.
6. Retrieve the full transcript from the database.
7. Send the full transcript, pre-generated questions, and job description to the LLM to generate a post-interview summary. The summary includes: overall assessment, key strengths, key concerns, a recommendation score, and (for technical interviews) a technical depth score.
8. Store the summary and final score in the database; update the candidate's application record.
9. Increment the interview counter on the requisition.
10. Post the interview summary as a note in Lever.
11. Push the summary to the interviewer's screen.
12. If the interview counter now meets the re-ranking threshold, trigger the Re-ranking Subgraph.

---

### 8.6 RAG Query Subgraph

**What it does:** Answers natural-language questions about candidates by retrieving relevant data from the vector store and generating a sourced response.

**Triggered by:** HR or Hiring Manager submitting a query in the chat panel.

**Flow:**
1. Parse the user's query to understand intent (single candidate lookup, comparison, general search).
2. Embed the query using the same model used for CVs.
3. Search Chroma for the most semantically similar CV chunks and interview transcript chunks. Filter by requisition if one is in context.
4. Retrieve the full profiles (from PostgreSQL) for the top matching candidates, including CV text, assessment scores, interview summaries, and Lever notes.
5. Assemble the full context and send it to the LLM with the original query.
6. The LLM returns a natural-language answer with citations — each citation pointing to the specific candidate and excerpt it drew from.
7. Return the answer and citations to the frontend. Citations are rendered as clickable links to the candidate's detail page.

**Target response time:** 5–10 seconds depending on query complexity.

---

### 8.7 Re-ranking Subgraph

**What it does:** Re-scores and re-ranks all candidates for a requisition when new data (assessments or interviews) has come in.

**Triggered by:** An assessment counter or interview counter hitting its threshold, a 24-hour scheduled run, or a manual HR request.

**Flow:**
1. Fetch all candidates for the requisition from the database.
2. Check whether any new assessment or interview data exists since the last re-ranking. If not, exit without doing anything.
3. Merge all available data per candidate: CV text + prior cosine score + assessment score (if any) + interview summary (if any).
4. Send all candidates to the LLM in a single call. The LLM re-scores each one considering all available signals and returns an updated ranked list with justifications.
5. In parallel:
   - Save the new scores and justifications to the database.
   - Sync updated rankings back to Lever.
6. Check whether any HR user is currently viewing this requisition's pipeline in Redis.
   - If yes, push the updated candidate table to their screen via WebSocket.
   - If no, skip the notification.
7. Reset the relevant counters.

---

### 8.8 Scheduled Background Jobs

Three scheduled jobs run independently of user actions:

| Job | Frequency | Purpose |
|---|---|---|
| Time-based re-screening | Every 24 hours | Finds all active requisitions that have received new candidates, assessments, or interviews since their last screening, and triggers batch re-screening for each |
| Lever sync fallback | Every 2 hours | If webhook delivery failures are detected, re-syncs active requisitions directly from the Lever API |
| Token cleanup | Every 1 hour | Deletes expired refresh tokens from the database |

---

## 9. Frontend Pages

| Route | Page | Who |
|---|---|---|
| `/login` | Login | Both |
| `/dashboard` | All requisitions overview with screening status | HR |
| `/requisition/:id` | Ranked candidate pipeline + RAG chat sidebar | Both |
| `/requisition/:id/candidate/:appId` | Full candidate detail (scores, CV, assessment, interview) | Both |
| `/hiring-manager` | Scoped requisitions + candidate list | HM |
| `/interview/:sessionId/prepare` | Pre-generated questions before the interview | Both |
| `/interview/:sessionId/live` | Live copilot: transcript + follow-up questions | Both |
| `/interview/:sessionId/summary` | Post-interview summary and scores | Both |

---

## 10. Authentication & Authorization

- JWT-based: short-lived access tokens + long-lived refresh tokens stored hashed in the database
- All API endpoints require authentication
- HR Managers have full system access
- Hiring Managers are scoped to their assigned requisitions and cannot send assessments, schedule interviews, or trigger screening manually
- WebSocket connections are authenticated via token query parameter on connection

---

## 11. Error Handling Principles

- Webhook processing always returns HTTP 200 immediately; failures are logged and retried asynchronously
- LLM failures during batch screening fall back to cosine similarity scores only
- If a batch screening is already running for a requisition (Redis lock held), new triggers are silently dropped and will be picked up by the next scheduled run
- WebSocket disconnects during live interviews are handled gracefully — transcript chunks are already persisted, and reconnection resumes the session
- LLM failures during follow-up question generation are skipped silently; transcription continues normally

---

*End of Incorta-HR Project Specification*