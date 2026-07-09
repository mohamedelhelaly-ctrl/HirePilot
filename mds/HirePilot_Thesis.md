# HirePilot: An AI-Powered Internal Recruitment Assistant

> **Document purpose.** This Markdown file is a complete technical and narrative source document for a final-stage thesis on HirePilot. It follows the outline in `mds/outlines.md` section by section. All technical claims are grounded in the actual codebase (`src/backend/`, `src/frontend/`) as it exists on the `phase5` branch. Diagram sections include ready-to-use LaTeX/TikZ source so the document can be transcribed directly into a LaTeX thesis template. Where a required `\usetikzlibrary` is needed, it is noted directly above the snippet.

---

# 1. Introduction

## 1.1 Motivation

Internal recruitment teams at fast-growing technology organizations face a structural bottleneck: the volume of inbound applications per requisition scales far faster than the number of people available to read CVs, schedule interviews, and synthesize structured feedback into a hiring decision. In a typical internal hiring pipeline, a hiring manager opens a requisition, an HR coordinator collects dozens to hundreds of CVs, and the same handful of recruiters must independently re-derive a candidate's relevant experience, compare it against the job description, generate interview questions, run and score interviews, and keep a defensible audit trail of every status change — all while doing this in parallel across many open requisitions.

This manual process has three structural failure points that motivated HirePilot:

1. **Screening is slow and inconsistent.** Two recruiters reading the same stack of CVs against the same job description will produce different shortlists, because there is no consistent, repeatable scoring rubric applied at scale, and reading 50+ CVs in detail is fatiguing.
2. **Interview quality depends on the individual interviewer's preparation.** Without a structured set of tailored technical and behavioral questions per candidate, interviews drift toward generic, low-signal conversations, and follow-up questions are improvised rather than informed by what the candidate has already said earlier in the conversation.
3. **Institutional knowledge about a candidate is scattered.** A candidate's CV, screening justification, interview transcript, and evaluation live in different systems (or different people's heads), making it hard to ask a simple natural-language question like *"which of our shortlisted candidates has production Kubernetes experience?"* without manually re-reading every file.

HirePilot was built to attack all three problems with the same underlying technology stack: large language models (LLMs) for judgment-heavy tasks (extraction, scoring, question generation, summarization), semantic search over CV embeddings for retrieval, and a speech-to-text pipeline for turning live interview audio into a structured, queryable artifact.

## 1.2 Problem Definition

Concretely, the gaps in a manual or lightly-tooled recruiting workflow that HirePilot is designed to close are:

- **No consistent, auditable scoring mechanism.** Traditional applicant tracking systems (ATS) store candidate metadata and let a human read attached files; they do not natively rank candidates against a job description with a documented numeric score and justification (see [2.4](#24-gap-analysis)).
- **No automatic linkage between screening and interviewing.** Even where ATS tooling provides scoring (e.g., via a third-party assessment add-on), the same system rarely also generates tailored interview questions from the specific CV content and job description, or treats the interview as feedback that re-ranks the candidate pool.
- **No live, real-time interviewer support.** Conventional video interview tools record audio/video for later review; they do not transcribe and analyze the conversation *while it is happening* to suggest follow-up questions grounded in what the candidate just said.
- **No conversational access to the candidate pool.** Finding "everyone with 5+ years of backend experience who has already completed a technical interview" today requires either a saved filter (if the ATS happens to support it) or manually reading files.
- **Fragmented scheduling.** Coordinating interview slots against interviewer and candidate availability, generating a video-call link, and keeping the database in sync with the calendar event is typically a separate, manual step bolted onto the ATS.

HirePilot's working hypothesis is that an LLM-orchestrated backend, with a vector store for semantic CV retrieval and a real-time speech pipeline for interviews, can collapse these gaps into a single coherent system without requiring the recruiting team to operate multiple disconnected tools.

## 1.3 Aims and Objectives

The system sets out to achieve the following measurable objectives:

1. **Automate CV-to-requisition matching.** Given a batch of uploaded CVs and a requisition's job description, automatically extract structured candidate data (skills, experience, education, roles) and produce a comparative 0–1 score with a written justification for every candidate, without per-candidate manual review.
2. **Trigger screening automatically at scale, not on-demand only.** Batch screening should run on a threshold/interval basis (new CVs accumulate, then are screened together) so that recruiters are not the bottleneck for *triggering* the AI pipeline.
3. **Generate tailored interview material per candidate.** For every candidate that reaches the interview stage, automatically generate technical questions derived from their specific CV and the job description, plus a fixed competency-based interview (CBI) question set using the STAR method.
4. **Provide a live, AI-assisted interview experience.** Stream interview audio over a WebSocket connection, transcribe it in near real time using a self-hosted Whisper model, and generate contextual follow-up questions during the conversation — then produce a structured post-interview summary (strengths, concerns, recommendation score) automatically.
5. **Support natural-language search over the candidate pool.** Let a hiring manager or HR manager ask free-text questions about candidates within a requisition (e.g., comparisons, qualifications) and receive an answer synthesized via retrieval-augmented generation (RAG) over CV embeddings and interview data, with persistent, multi-turn chat threads.
6. **Integrate scheduling end-to-end.** Let HR/hiring managers query interviewer availability, schedule a Google Calendar event with an auto-generated Google Meet link, and keep `InterviewSession` records synchronized with reschedules/cancellations.
7. **Enforce role-appropriate access.** Distinguish HR Managers (who manage users, requisitions, and have system-wide visibility) from Hiring Managers (scoped to their own assigned requisitions), enforced both in the API layer (JWT + role dependency injection) and in the frontend (protected routes).

## 1.4 Scope and Limitations

**In scope:**
- Requisition lifecycle management (create, edit, assign hiring manager, deactivate).
- Candidate and application lifecycle management, including an immutable global candidate directory that survives across multiple applications to different requisitions.
- CV ingestion (PDF/DOCX), text extraction, embedding, and vector storage.
- LLM-driven batch screening (extraction, enrichment, comparative scoring) as a multi-node LangGraph workflow, runnable both on a scheduled interval and on demand.
- Tailored technical question generation and static STAR-method behavioral question generation.
- Live, WebSocket-based AI-assisted interviewing with real-time transcription and follow-up question generation.
- Post-interview automatic summarization and re-scoring of the candidate (interview re-screening).
- RAG-based conversational search over the candidate pool, scoped per requisition, with persisted multi-thread chat history.
- Google Calendar/Google Meet integration for interview scheduling, rescheduling, and cancellation.
- JWT-based authentication with Google OAuth (ID-token and authorization-code flows), refresh-token rotation, and role-based authorization.
- A React/Vite single-page frontend covering login, HR dashboard, requisition detail/pipeline, candidate directory, user management, and the live-interview "AI Copilot" interface.

**Explicitly out of scope:**
- **Payroll, compensation, and benefits administration.**
- **Onboarding** of hired candidates (no post-offer workflow beyond marking an application `HIRED`).
- **Offer management** (e-signature, offer letter generation, negotiation tracking) beyond the `OFFER_EXTENDED` status flag.
- **External candidate-facing portal** — candidates do not log into HirePilot; they interact only via the Google Meet link and (implicitly) the CV they submit.
- **Multi-tenant / multi-organization support** — the system is designed for a single internal organization's recruiting team.
- **Caching layer (Redis)** — referenced in the original technology plan for session/result caching and rate limiting, but not yet implemented in the current codebase; all state is held in PostgreSQL or short-lived in-process memory (see [9.3 Future Work](#93-future-work)).

**Known limitations:**
- Whisper's transcription accuracy depends heavily on audio conditions (background noise, multiple overlapping speakers, accents) — a limitation inherited from the underlying speech model rather than something HirePilot's interview pipeline can fully compensate for (see [2.2](#22-state-of-the-art-techniques) and [8.2](#82-ai-model-evaluation)).
- LLM-based scoring inherits the well-documented risk of bias present in foundation models trained on uncurated web-scale text (see [2.2](#22-state-of-the-art-techniques)); HirePilot does not currently implement a dedicated fairness-auditing layer.
- The batch screening pipeline currently processes requisitions strictly sequentially (no concurrent LLM calls across requisitions), trading throughput for simplicity and to avoid rate-limit contention on the underlying LLM provider.

## 1.5 Time Plan

The project timeline below is reconstructed directly from the Git commit history of the repository, which spans from the initial commit to the current `phase5` branch.

| Phase | Window | Branch | Delivered |
|---|---|---|---|
| **Phase 0 — Concept demo** | Oct 2025 – Jan 2026 | `demo` | Initial proof-of-concept: candidate matching against a job description, an early conversational filter over chat history, first React pages (login, HR home page, jobs pipeline, candidate modal). |
| **Phase 1 — Frontend skeleton** | Nov 2025 | `hrHomePage`, `jobs-pipeline-page`, `cadidate-modal-pop-up`, `dummy-login`, `hr-manager-home-page` | Page-level UI scaffolding for the HR dashboard, job pipeline table, and candidate detail modal; dummy/local login flow. |
| **Phase 2 — Backend foundations** | Feb 2026 – Mar 2026 | `Phase2` | LangGraph subgraph skeletons; first working batch-screening flow; modularized `models`/`crud` packages (split from a single monolithic file into per-entity modules). |
| **Phase 3 — Auth & RAG** | Mar 2026 – May 2026 | `Phase3` | JWT authentication service, Google OAuth integration, refresh-token rotation, role-based access dependencies; application-detail extraction; RAG query subgraph; live-interview copilot (first version); switch of CV/extraction scoring from a single combined field to a single score + justification. |
| **Phase 4 — Integration & local inference** | May 2026 | `phase4` | Switch of the LLM/embedding stack to a self-hostable/local-model configuration; hardened screening flow; WebSocket interview test harness; frontend/backend URL wiring for cross-origin development. |
| **Phase 5 — Calendar, assignment, polish (current)** | Jun 2026 (ongoing) | `phase5` | Google Calendar/Meet scheduling integration; assigning requisitions to hiring managers; interview history view; requisition-filtering scoped to the logged-in hiring manager; UI enhancements; interview rescreening (re-ranking candidates after interviews complete). |

This phased delivery — frontend-first prototyping, then backend orchestration, then authentication/RAG, then integration, then scheduling — reflects an iterative approach where each phase de-risked one subsystem (UI feel, AI workflow correctness, security, real-time inference, third-party integration) before layering on the next.

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning}
\begin{tikzpicture}[x=2.3cm, y=1cm]
  % Timeline axis
  \draw[-{Latex[length=2mm]}] (0,0) -- (6.6,0);
  \foreach \x/\lbl in {0/Oct 2025, 1/Jan 2026, 2/Feb 2026, 3/Mar 2026, 4/May 2026, 5/Jun 2026, 6/Today} {
    \draw (\x,0.08) -- (\x,-0.08);
    \node[below, font=\scriptsize] at (\x,-0.1) {\lbl};
  }
  % Phase bars
  \draw[fill=blue!20] (0,0.3) rectangle (1,0.9) node[midway]{\scriptsize Phase 0: Demo};
  \draw[fill=green!20] (1,0.3) rectangle (2,0.9) node[midway]{\scriptsize Phase 1: UI};
  \draw[fill=orange!20] (2,0.3) rectangle (3,0.9) node[midway]{\scriptsize Phase 2: Backend};
  \draw[fill=red!20] (3,0.3) rectangle (4,0.9) node[midway]{\scriptsize Phase 3: Auth/RAG};
  \draw[fill=purple!20] (4,0.3) rectangle (5,0.9) node[midway]{\scriptsize Phase 4: Integration};
  \draw[fill=yellow!30] (5,0.3) rectangle (6,0.9) node[midway]{\scriptsize Phase 5: Calendar};
\end{tikzpicture}
```

## 1.6 Thesis Organization

The remainder of this document is organized as follows. **Chapter 2** situates HirePilot within the broader AI-recruitment-technology landscape, surveys state-of-the-art techniques in ATS scoring, LLM-based screening, and speech-to-text, and positions HirePilot against existing commercial platforms. **Chapter 3** specifies the system's functional and non-functional requirements. **Chapter 4** presents the system analysis through use-case, entity-relationship, sequence, activity/state, and component diagrams (with accompanying TikZ source). **Chapter 5** describes the system architecture layer by layer: backend, database, AI/ML stack, LangGraph orchestration, authentication, and third-party integrations. **Chapter 6** documents the implementation in depth, including technology justification and the concrete engineering of the screening, interview, and RAG workflows. **Chapter 7** walks through the prototype's user interface screen by screen. **Chapter 8** covers the testing and evaluation strategy. **Chapter 9** concludes with a summary of contributions, honest limitations, and future work.

---

# 2. Background & Literature Review

## 2.1 Field of the Project

HirePilot sits at the intersection of three established research and product areas: **applicant tracking systems (ATS)**, **conversational/generative AI applied to human resources**, and **automatic speech recognition (ASR) for structured conversation analysis**. Recruitment technology has gone through three broad waves. The first wave (1990s–2000s) digitized paperwork: keyword-matching resume databases and workflow tracking. The second wave (2010s) added structured collaboration — interview kits, scorecards, pipeline analytics, and a recruiting CRM layer for proactive sourcing. The third wave, underway since approximately 2023 with the mainstreaming of large language models, is replacing keyword matching and rigid scorecards with models that read CVs and job descriptions the way a human reviewer would, at a fraction of the time cost. By 2026, AI-powered ATS platforms are described in industry literature as having evolved "far beyond simple resume filters" into "intelligent hiring ecosystems integrating predictive analytics, natural language understanding, and automated workflows" [TheUndercoverRecruiter, 2026]. HirePilot is best understood as a from-scratch implementation of this third wave, purpose-built for an internal recruiting team rather than retrofitted onto a legacy ATS.

## 2.2 State-of-the-Art Techniques

**LLM-based candidate screening.** Industry surveys of 2026-era screening tools note that LLMs are used to "understand context, evaluate career consistency, and detect nuances that old ATS filters miss," generating "personalized interview questions, executive summaries, and CV/LinkedIn cross-validation — all in under 30 seconds" [PeopleManagingPeople, 2026]. This is architecturally close to HirePilot's batch-screening subgraph, which performs LLM-based structured extraction followed by a single comparative-scoring LLM call across the whole candidate cohort (Chapter 6). The literature also documents a specific failure mode relevant to HirePilot's design choices: a 2026 academic study found that "AI-powered ATS systems actually prefer AI-written resumes over human-written ones," and industry estimates suggest 88% of employers believe they lose qualified candidates to ATS systems that are not resume-format-tolerant [ResumeRank.io, 2026]. This motivates HirePilot's use of a general-purpose extraction prompt over raw extracted CV text (rather than rigid field-position parsing), which is comparatively more tolerant of varied resume formats and writing styles, though it does not eliminate model-side biases (below).

**Fairness and bias in AI-driven hiring.** A substantial and growing body of peer-reviewed work documents bias in LLM-based resume screening. Studies report that LLM-based screening "disadvantage[s] Black and female-associated names, even when all other resume content was identical," and that running thousands of simulated applications through a general-purpose chat model surfaces "emergent patterns of discrimination, such as preference for elite education or positional bias in response order" [arXiv:2407.20371; arXiv:2503.19182]. More recent work (2025–2026) finds that while explicit gender/race bias has been reduced in newer model generations, "implicit biases concerning educational background remain significant," with candidates from prestigious institutions receiving preferential treatment [arXiv:2508.16673]. Perhaps most relevant to a system like HirePilot, where humans review AI output rather than letting the AI decide outright, a University of Washington study found that human reviewers' own decisions shift to mirror a biased AI assistant's preferences — when the AI favored non-white candidates participants did too, and vice versa for white candidates [University of Washington, 2025]. This is a direct argument for two design decisions already present in HirePilot: (1) every AI score is paired with a stored, human-readable justification rather than presented as a bare number, and (2) the AI score is explicitly a recommendation that a human still approves/rejects via the application status workflow, not an autonomous accept/reject action.

**Speech-to-text for interview transcription.** OpenAI's Whisper family is the most widely benchmarked open-source ASR model as of 2026. Reported word-error rates (WER) vary drastically by acoustic condition: under controlled conditions (e.g., the LibriSpeech benchmark), Whisper large-v3 reaches roughly 97.9% word accuracy, and in clean daily-dialogue datasets it can reach as low as ~1.7% WER [ArtificialAnalysis.ai, 2026]. Performance degrades substantially in realistic multi-speaker, noisy settings — small-group classroom discourse studies report WER as high as ~84.7%, and post-processed real-world meeting audio is more realistically expected to fall in the 10–20% WER range [ACM, 2023; University Transcription Services, 2026]. Whisper is also documented to "hallucinate" — emit fluent but unsupported text — more than some commercial alternatives [AssemblyAI, 2026]. This directly informs HirePilot's interview pipeline design: rather than batch-transcribing a full recording after the fact, the system transcribes in short overlapping chunks (Chapter 6) specifically to bound the audio context per inference call and to allow deduplication across chunk boundaries, which mitigates (without eliminating) the kind of long-context drift and hallucination documented in the literature.

**Retrieval-augmented generation (RAG) in recruiting.** RAG combines a retrieval step (semantic search over an embedded corpus) with a generative step (an LLM that synthesizes an answer from retrieved context), and is reported in both industry and academic sources as a fit for recruiting use cases: "RAG automates resume screening through context-aware extraction, evaluation, summarization, and scoring, closely aligning with HR assessments" [ResearchGate, 2025], and is also described as useful for interview preparation — gathering "context like the time an interview is slated to take place, the job the candidate is interviewing for, a brief description of the candidate's background" for an interviewer [Merge.dev, 2026]. HirePilot's RAG subgraph (Chapter 6, [8.3](#83-usability-testing)) implements exactly this pattern: a tool-calling LLM agent retrieves candidate data from a Chroma vector index and the relational database, then synthesizes a natural-language answer, persisted as a chat thread scoped to a single requisition.

**Workflow orchestration for multi-step LLM applications.** As LLM applications move beyond single-call prompting toward multi-step pipelines with conditional branching (e.g., "extract, then enrich, then score, then persist"), graph-based orchestration frameworks have emerged as the dominant pattern for making such pipelines observable, debuggable, and resumable. HirePilot adopts LangGraph for exactly this reason: every multi-step AI workflow in the system (batch screening, live-interview summarization, RAG querying) is expressed as an explicit graph of typed nodes over a shared state object, rather than as an ad hoc chain of function calls (Chapter 5, Chapter 6).

## 2.3 Market Analysis and Competitive Landscape

Three platforms are commonly used as reference points for "what a modern ATS looks like" and are compared against HirePilot below.

| Platform | Core focus | AI screening | Live interview AI | RAG/chat over candidates | Pricing model |
|---|---|---|---|---|---|
| **Greenhouse** | Structured hiring process discipline — interview kits, scorecards | None natively; relies on third-party add-ons for AI scoring [HireTruffle, 2026] | None | None | Per-seat/annual contract |
| **Lever** | ATS + recruiting CRM bundle for proactive sourcing | None natively; no built-in AI match score [HireTruffle, 2026] | None | None | Per-seat/annual contract |
| **HireVue** | Video-interview assessment platform | AI-generated scores, but only for candidates who complete a separate video-assessment step; does not auto-triage resumes [HireAuto.ai comparison notes, 2026] | Asynchronous pre-recorded video assessment with AI scoring, not a live, two-way, real-time copilot | None | High floor — "Essential" tier reported around \$35,000/year, "Premium" around \$75,000/year [GoMokka, 2026] |
| **HirePilot (this project)** | End-to-end internal pipeline: screening → interview → decision, single system | Native LLM-based comparative scoring with stored justification, triggered automatically by volume threshold or on demand | Live, real-time WebSocket-based transcription with in-conversation follow-up question generation and automatic post-interview summarization | Native RAG chat over CVs + interview transcripts, scoped per requisition, multi-turn and persisted | Self-hosted; no licensing fee — cost is infrastructure + LLM API usage |

The general pattern in the competitive landscape is that **ATS-of-record platforms (Greenhouse, Lever) intentionally stay thin on AI scoring and delegate it to point solutions**, while **assessment platforms (HireVue) are deep on AI but only within their own narrow assessment step**, and **none of the three couple screening, live-interview assistance, and conversational candidate search into one system with a shared data model.** A recruiter using Greenhouse + a screening add-on + HireVue today is stitching together three vendor relationships, three data models, and three places candidate signal can go stale or fall out of sync. HirePilot's architectural bet is that owning the full pipeline — from CV upload through final hiring decision — in a single PostgreSQL-backed system lets every stage feed the next one directly (e.g., the interview transcript directly informs re-scoring; the original CV text is what the RAG chat retrieves against) rather than passing data across vendor boundaries.

## 2.4 Gap Analysis

Synthesizing the literature and competitive review against HirePilot's actual capabilities (Chapters 5–6), the explicit gaps closed are:

1. **Unified data model across the funnel.** Existing ATS platforms treat screening, assessment, and interviewing as separate stages, often handled by separate vendors; HirePilot persists CV-derived data (`ApplicationDetail`), the screening verdict (`ScreeningResult`), and interview outcomes (`InterviewSession`, `TranscriptChunk`) against the same `Application` row, so a single comparative score genuinely reflects the candidate's *entire* journey, not just the resume.
2. **Threshold-triggered batch automation, not purely on-demand.** Where third-party AI screening add-ons typically score a candidate the moment they apply (one-at-a-time), HirePilot's scheduler-driven batch screening explicitly waits for a configurable volume of new candidates per requisition (`new_candidate_threshold`) before running a *comparative* scoring pass across the whole new cohort at once — closer to how a human panel would rank a stack of CVs against each other, not just against a fixed rubric in isolation.
3. **Live, real-time interview assistance, not post-hoc video review.** HireVue-style platforms record and later score a video; HirePilot transcribes audio while the interview is happening and surfaces follow-up question suggestions inside the same conversation, then immediately produces structured scoring on interview end.
4. **Conversational retrieval over the candidate pool.** No reference platform in the comparison offers a chat interface for asking free-text questions about an evolving candidate pool with retrieval grounded in the actual CV/interview text; HirePilot's chat-thread + RAG-subgraph design fills this gap directly.
5. **Self-hosted, ownership-first deployment model.** HireVue's published pricing floor (tens of thousands of dollars annually) puts AI-assisted interviewing out of reach for smaller internal recruiting teams; HirePilot's stack (self-hostable embedding model, self-hostable Whisper, swappable LLM provider via GROQ/Ollama/Watsonx) is designed to run without recurring per-seat licensing.

---

# 3. System Requirements

## 3.1 Functional Requirements

### Requisitions
- **FR-1.** An HR Manager can create a requisition with a title, description (job description text), department, location, and an assigned hiring manager.
- **FR-2.** Each requisition is auto-assigned a unique `lever_id` (UUID) on creation.
- **FR-3.** An HR Manager can update or soft-delete (deactivate, `is_active = false`) a requisition; deactivated requisitions are excluded from default list views.
- **FR-4.** A Hiring Manager can view only the requisitions for which they are the assigned `hiring_manager_id`; an HR Manager can view all requisitions.
- **FR-5.** Each requisition tracks rolling counters (`new_candidate_counter`, `new_assessment_counter`, `new_interview_counter`) against configurable thresholds, used to trigger automated batch processing.
- **FR-6.** A requisition exposes a `screening_in_progress` flag so the UI can show a live "screening in progress" banner and so the scheduler will not double-trigger a screening run on the same requisition.

### Candidates & Applications
- **FR-7.** A user can upload one or more CV files (PDF/DOCX) against a specific requisition via multipart upload; the system extracts text, generates embeddings, and stores them in the vector index tagged with the requisition ID.
- **FR-8.** The system maintains a global, immutable **Candidate** identity (name, email, phone, LinkedIn URL) that is distinct from a per-requisition **Application**; the same person applying to two requisitions produces one `Candidate` row and two `Application` rows.
- **FR-9.** The system deduplicates repeat CV uploads for the same candidate/requisition pair by matching on email.
- **FR-10.** Every application has a status drawn from a fixed lifecycle (`new → screening_pending → screening_passed/screening_rejected → interview_scheduled → interview_completed → offer_extended → hired/rejected/withdrawn`), and every status transition is recorded in an append-only `StatusHistory` table with who changed it and an optional reason.
- **FR-11.** A user can view a global **Candidate Directory** listing every candidate and their full cross-requisition application history, restricted to applications on requisitions the viewing user has access to.

### Batch Screening
- **FR-12.** The system can run an automated, multi-stage screening pipeline for a requisition that: (a) retrieves the top-K semantically similar CVs from the vector index against the job description, (b) extracts structured candidate data via LLM, (c) computes total years of experience deterministically from extracted role date ranges, (d) generates a single comparative LLM score (0–1) and justification across the full candidate cohort, and (e) persists the results.
- **FR-13.** Batch screening can be triggered either automatically (scheduler polls every N minutes and fires when a requisition's new-candidate counter crosses its threshold) or manually (via an API call with `manual_trigger = true`).
- **FR-14.** The system supports an **interview re-screening mode** that re-runs comparative scoring once enough candidates on a requisition have completed interviews, incorporating interview performance into an updated ranking.
- **FR-15.** The system must not run two screening passes concurrently against the same requisition (enforced via the `screening_in_progress` lock).

### Interview Question Generation
- **FR-16.** For a given application, the system can generate a set of technical interview questions tailored to that candidate's specific CV content and the requisition's job description.
- **FR-17.** For a given application, the system can generate (or load) a static set of competency-based interview (CBI) questions following the STAR (Situation, Task, Action, Result) method.

### Live AI-Assisted Interview
- **FR-18.** A user can open a live interview session over a WebSocket connection, specifying the application, requisition, and interview type (`hr_screen`, `technical`, `behavioral`, `final`).
- **FR-19.** The system streams short audio chunks from the client, transcribes them via a self-hosted Whisper model, and returns transcript text to the client in near real time.
- **FR-20.** The system periodically (approximately every 30 seconds, once sufficient new transcript content has accumulated) generates a contextual follow-up question via LLM and pushes it to the client during the live session.
- **FR-21.** On interview end, the system generates a structured summary (overall assessment, key strengths, key concerns, a recommendation score, and — for technical interviews — a technical-depth score) and persists it against the `InterviewSession` and the parent `Application`.
- **FR-22.** All transcript text is persisted incrementally as ordered `TranscriptChunk` rows, not only as a final concatenated blob, so a session can be replayed/audited chunk by chunk.

### Conversational Candidate Search (RAG)
- **FR-23.** A user can create one or more named chat threads scoped to a specific requisition and ask free-text questions about the candidates in that requisition's pipeline.
- **FR-24.** The system answers using retrieval-augmented generation: an LLM agent with tool-calling access to CV semantic search and candidate/requisition lookups retrieves relevant context before answering.
- **FR-25.** Chat threads and their message history persist across sessions and can be renamed or deleted.

### Scheduling
- **FR-26.** A user can query available interview time slots for a given date range and interview type, with type-specific duration (HR screen: 30 min, technical: 60 min, behavioral: 45 min, final: 90 min) and working-hours/weekend exclusions applied.
- **FR-27.** A user can schedule an interview, which creates a Google Calendar event with an auto-generated Google Meet link, sends an invitation, and creates a corresponding `InterviewSession` row.
- **FR-28.** The interviewer who owns a scheduled interview can reschedule or cancel it; rescheduling updates the Google Calendar event and the stored session times, and cancellation deletes the calendar event and marks the session `CANCELLED`.

### Identity, Access, and User Management
- **FR-29.** Users authenticate via Google OAuth (either ID-token or authorization-code flow); there is no independent password-based account creation by end users.
- **FR-30.** An HR Manager can pre-register a user (email, name, role) before that person ever logs in; the user's first Google login then matches against the pre-registered email.
- **FR-31.** A one-time bootstrap endpoint allows creation of the first HR Manager account when no admin exists yet.
- **FR-32.** An HR Manager can list, update, deactivate, and reactivate users; a user cannot deactivate their own account.
- **FR-33.** Access tokens expire after 30 minutes; refresh tokens are valid for 7 days, are stored hashed (not in plaintext), and can be individually or wholesale revoked on logout.

## 3.2 Non-Functional Requirements

- **NFR-1 (Performance).** Batch screening for a single requisition must complete its LLM-bound stages (extraction, enrichment, scoring) without blocking the API process — the workflow runs asynchronously and is observable via the `screening_in_progress` flag and `last_screening_at` timestamp, with the frontend polling for completion rather than blocking on a synchronous HTTP call.
- **NFR-2 (Real-time responsiveness).** Live interview transcription must return transcript text to the client within a few seconds of receiving an audio chunk, so the on-screen transcript feels "live" rather than batched.
- **NFR-3 (Security).** All inter-service secrets (Google OAuth tokens, refresh-token hashes) must be stored encrypted or hashed at rest — Google OAuth credentials are Fernet-encrypted; refresh tokens are stored as SHA-256 hashes, never as raw JWTs.
- **NFR-4 (Authorization).** Every state-changing endpoint must enforce role checks server-side via FastAPI dependency injection (`get_current_user`, `require_hr_manager`), not merely hide UI affordances client-side.
- **NFR-5 (Scalability — data layer).** The relational schema must support a candidate applying to multiple requisitions without duplicating their core identity, and must support arbitrarily many structured CV-derived fields per application without a schema migration per new field (`ApplicationDetail` is a flexible key/JSON-value table for this reason).
- **NFR-6 (Reliability — partial failure).** A failure in one stage of a multi-node AI workflow (e.g., an LLM call timing out during extraction) must not corrupt previously-committed state; LangGraph nodes check an `error` field on entry and short-circuit cleanly rather than continuing to operate on partial/invalid state.
- **NFR-7 (Usability).** The frontend must surface background AI work (screening in progress, interview processing) as visible status rather than leaving the user staring at a static screen with no feedback, via polling-driven banners and toast notifications.
- **NFR-8 (Auditability).** Every application status transition, every transcript chunk, and every generated follow-up question must be individually persisted with a timestamp, so a hiring decision can be reconstructed and justified after the fact.
- **NFR-9 (Portability of the AI stack).** The LLM provider must be swappable (GROQ-hosted, local Ollama, or Watsonx) via configuration rather than code changes, to avoid hard vendor lock-in on inference.

## 3.3 Constraints and Assumptions

**Constraints:**
- **Google Workspace dependency.** Authentication and calendar scheduling both depend on Google APIs (OAuth 2.0, Calendar API, Meet link generation); an organization without Google Workspace/Google accounts cannot use HirePilot's login or scheduling features as implemented.
- **Whisper's language/accuracy envelope.** The deployed Whisper configuration is run in "translate" mode (any source language transcribed into English), which is appropriate for the target organization's primarily English-language interviews but means non-English interview answers are translated rather than transcribed verbatim, and accuracy is subject to the acoustic-condition sensitivity discussed in [2.2](#22-state-of-the-art-techniques).
- **Sequential batch screening.** Only one requisition's screening pipeline runs at a time system-wide (by design, to bound concurrent LLM call volume), which bounds throughput under heavy simultaneous hiring activity.
- **Single-organization deployment model.** The schema and authorization model assume one organization's users and roles; there is no tenant/organization partitioning.

**Assumptions:**
- CVs are submitted as machine-readable PDF or DOCX (not scanned image-only PDFs requiring OCR).
- Interviewers and candidates both have functioning microphones and a stable connection sufficient for near-real-time audio streaming.
- The organization is comfortable with an LLM-generated score being a *recommendation* surfaced to a human decision-maker, not an autonomous accept/reject gate (consistent with the bias-mitigation rationale in [2.2](#22-state-of-the-art-techniques)).
- The two-role model (HR Manager, Hiring Manager) is sufficient to express the organization's access-control needs; no need for finer-grained per-requisition collaborator permissions was identified.

---

# 4. System Analysis & Diagrams

> All TikZ snippets in this chapter assume the following preamble is available in the surrounding LaTeX document: `\usepackage{tikz}` and `\usetikzlibrary{positioning, arrows.meta, shapes.geometric}`. Each snippet is a self-contained `tikzpicture` that can be dropped inside a `figure` environment.

## 4.1 Use Case Diagram

**Actors:** HR Manager (full system access — users, all requisitions, batch screening triggers) and Hiring Manager (scoped to their own assigned requisitions). Both actors share most use cases; "Manage Users" is exclusive to the HR Manager role.

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[font=\small, >={Latex[length=2mm]}]
  % --- Actors (simple stick figures) ---
  \newcommand{\stickactor}[3]{
    \draw[thick] (#1,#2+0.55) circle (0.18);
    \draw[thick] (#1,#2+0.37) -- (#1,#2-0.25);
    \draw[thick] (#1-0.22,#2+0.15) -- (#1+0.22,#2+0.15);
    \draw[thick] (#1,#2-0.25) -- (#1-0.18,#2-0.65);
    \draw[thick] (#1,#2-0.25) -- (#1+0.18,#2-0.65);
    \node[below, align=center] at (#1,#2-0.7) {#3};
  }
  \stickactor{0}{2.6}{HR\\Manager}
  \stickactor{0}{-2.6}{Hiring\\Manager}

  % --- System boundary ---
  \draw (2.2,-4.2) rectangle (11.5,4.2);
  \node[above] at (6.85,4.2) {\textbf{HirePilot}};

  % --- Use case anchor coordinates ---
  \coordinate (uc1) at (4.6,3.3);
  \coordinate (uc2) at (9.4,3.3);
  \coordinate (uc3) at (4.6,1.6);
  \coordinate (uc4) at (9.4,1.6);
  \coordinate (uc5) at (4.6,0);
  \coordinate (uc6) at (9.4,0);
  \coordinate (uc7) at (4.6,-1.6);
  \coordinate (uc8) at (9.4,-1.6);
  \coordinate (uc9) at (7,-3.3);

  % --- Connectors (drawn first so node fill covers the stub) ---
  \draw (0,2.6) -- (uc1);
  \draw (0,2.6) -- (uc2);
  \draw (0,2.6) -- (uc3);
  \draw (0,2.6) -- (uc5);
  \draw (0,2.6) -- (uc7);
  \draw (0,2.6) -- (uc9);
  \draw (0,-2.6) -- (uc3);
  \draw (0,-2.6) -- (uc4);
  \draw (0,-2.6) -- (uc5);
  \draw (0,-2.6) -- (uc6);
  \draw (0,-2.6) -- (uc7);
  \draw (0,-2.6) -- (uc8);
  \draw (0,-2.6) -- (uc9);

  % --- Use cases (ellipses) ---
  \node[draw, ellipse, fill=white, minimum width=3.4cm, minimum height=0.9cm] at (uc1) {Manage Requisitions};
  \node[draw, ellipse, fill=white, minimum width=3.4cm, minimum height=0.9cm] at (uc2) {Manage Users};
  \node[draw, ellipse, fill=white, minimum width=3.6cm, minimum height=0.9cm] at (uc3) {Upload \& Screen CVs};
  \node[draw, ellipse, fill=white, minimum width=3.6cm, minimum height=0.9cm] at (uc4) {Generate Interview Questions};
  \node[draw, ellipse, fill=white, minimum width=3.4cm, minimum height=0.9cm] at (uc5) {Schedule Interview};
  \node[draw, ellipse, fill=white, minimum width=3.6cm, minimum height=0.9cm] at (uc6) {Conduct Live AI Interview};
  \node[draw, ellipse, fill=white, minimum width=3.8cm, minimum height=0.9cm] at (uc7) {Ask Recruiting Copilot (RAG Chat)};
  \node[draw, ellipse, fill=white, minimum width=3.6cm, minimum height=0.9cm] at (uc8) {View Candidate Directory};
  \node[draw, ellipse, fill=white, minimum width=3.8cm, minimum height=0.9cm] at (uc9) {Update Application Status};
\end{tikzpicture}
```

## 4.2 Entity-Relationship Diagram

The relational schema below reflects the SQLAlchemy ORM models under `src/backend/models/tables/` (PostgreSQL, accessed asynchronously via SQLAlchemy 2.0 + `asyncpg`). Only the columns most relevant to the entity's identity and its relationships are shown in each box for readability; the full column lists are documented in [5.3](#53-postgresql-database-architecture).

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[
  font=\scriptsize,
  >={Latex[length=2mm]},
  entity/.style={draw, rectangle, align=left, fill=blue!4, minimum width=3.2cm, inner sep=4pt}
]
  % --- Row 1: core identity / ownership entities ---
  \node[entity] (user) {\textbf{User}\\id (PK)\\email\\role\\is\_active};
  \node[entity, right=3.4cm of user] (req) {\textbf{Requisition}\\id (PK)\\lever\_id\\hiring\_manager\_id (FK)\\screening\_in\_progress};
  \node[entity, right=3.4cm of req] (cand) {\textbf{Candidate}\\id (PK)\\lever\_id\\email\\full\_name};

  % --- Row 2: User's owned auxiliary entities ---
  \node[entity, below=1.6cm of user, xshift=-1.4cm] (refresh) {\textbf{RefreshToken}\\id (PK)\\user\_id (FK)\\token\_hash\\expires\_at};
  \node[entity, below=1.6cm of user, xshift=1.6cm] (oauth) {\textbf{GoogleOAuthCredential}\\id (PK)\\user\_id (FK, unique)\\access\_token (enc)\\refresh\_token (enc)};

  % --- Row 2/3: Application, the central join entity ---
  \node[entity, below=3.0cm of req] (app) {\textbf{Application}\\id (PK)\\candidate\_id (FK)\\requisition\_id (FK)\\status\\combined\_score};

  % --- Row 3: Application's children ---
  \node[entity, below=1.6cm of app, xshift=-4.6cm] (detail) {\textbf{ApplicationDetail}\\id (PK)\\application\_id (FK)\\key\\value (JSON)};
  \node[entity, below=1.6cm of app, xshift=-1.6cm] (screen) {\textbf{ScreeningResult}\\id (PK)\\application\_id (FK, unique)\\score\\justification};
  \node[entity, below=1.6cm of app, xshift=1.6cm] (hist) {\textbf{StatusHistory}\\id (PK)\\application\_id (FK)\\from\_status\\to\_status};
  \node[entity, below=1.6cm of app, xshift=4.8cm] (sess) {\textbf{InterviewSession}\\id (PK)\\application\_id (FK)\\interviewer\_id (FK)\\interview\_type\\status};

  % --- Row 4 ---
  \node[entity, below=1.6cm of sess] (chunk) {\textbf{TranscriptChunk}\\id (PK)\\session\_id (FK)\\text\\sequence\_number};

  % --- Requisition's chat entities ---
  \node[entity, above right=0.3cm and 2.0cm of cand] (thread) {\textbf{ChatThread}\\id (PK)\\external\_id\\requisition\_id (FK)\\user\_id (FK, nullable)};
  \node[entity, below=1.6cm of thread, xshift=2.2cm] (msg) {\textbf{ChatMessage}\\id (PK)\\thread\_id (FK)\\role\\content};

  % --- Relationships with cardinality labels ---
  \draw (user) -- (refresh) node[midway, fill=white] {1:N};
  \draw (user) -- (oauth) node[midway, fill=white] {1:1};
  \draw (user) -- (req) node[midway, fill=white] {1:N};
  \draw (user) -- (sess) node[midway, sloped, fill=white] {1:N};
  \draw (user) -- (thread) node[midway, sloped, fill=white] {1:N};
  \draw (req) -- (app) node[midway, fill=white] {1:N};
  \draw (req) -- (thread) node[midway, sloped, fill=white] {1:N};
  \draw (cand) -- (app) node[midway, sloped, fill=white] {1:N};
  \draw (app) -- (detail) node[midway, sloped, fill=white] {1:N};
  \draw (app) -- (screen) node[midway, fill=white] {1:1};
  \draw (app) -- (hist) node[midway, sloped, fill=white] {1:N};
  \draw (app) -- (sess) node[midway, sloped, fill=white] {1:N};
  \draw (sess) -- (chunk) node[midway, fill=white] {1:N};
  \draw (thread) -- (msg) node[midway, fill=white] {1:N};
\end{tikzpicture}
```

## 4.3 Sequence Diagrams

### 4.3.1 Batch Screening Flow

This corresponds to the five-node `batchScreening` LangGraph subgraph ([6.3](#63-ai-workflow-implementation)): similarity search → CV extraction → interview enrichment → comparative scoring → save results.

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[font=\scriptsize, >={Latex[length=2mm]}]
  % Lifeline headers
  \foreach \x/\name in {0/Scheduler, 3.2/Batch Screening\\Subgraph, 6.6/Vector Store\\(Chroma), 9.8/LLM Provider\\(GROQ), 13.0/PostgreSQL} {
    \node[draw, fill=gray!10, align=center, minimum width=2.6cm] (h-\x) at (\x,0) {\name};
    \draw[dashed] (\x,0) -- (\x,-11);
  }
  % Messages (decreasing y = time moving down)
  \draw[->] (0,-0.8) -- (3.2,-0.8) node[midway, above] {poll: counter \(\geq\) threshold};
  \draw[->] (3.2,-1.6) -- (6.6,-1.6) node[midway, above] {similarity\_search(job\_description)};
  \draw[->, dashed] (6.6,-2.3) -- (3.2,-2.3) node[midway, above] {top-K CandidateDoc[]};
  \draw[->] (3.2,-3.1) -- (9.8,-3.1) node[midway, above] {extract CV fields (per new CV)};
  \draw[->, dashed] (9.8,-3.8) -- (3.2,-3.8) node[midway, above] {ExtractedCV (skills, roles, dates)};
  \draw[->] (3.2,-4.6) -- (3.2,-4.6) ;
  \node at (3.2,-5.0) {\scriptsize Python: total\_years\_experience};
  \draw[->] (3.2,-5.6) -- (9.8,-5.6) node[midway, above] {generate tech/CBI question context};
  \draw[->, dashed] (9.8,-6.3) -- (3.2,-6.3) node[midway, above] {question set};
  \draw[->] (3.2,-7.1) -- (9.8,-7.1) node[midway, above] {comparative\_score(all candidates, JD)};
  \draw[->, dashed] (9.8,-7.8) -- (3.2,-7.8) node[midway, above] {ScoredCandidate[] (0--1 + justification)};
  \draw[->] (3.2,-8.6) -- (13.0,-8.6) node[midway, above, align=center] {upsert Application,\\ScreeningResult, ApplicationDetail};
  \draw[->, dashed] (13.0,-9.3) -- (3.2,-9.3) node[midway, above] {ack};
  \draw[->, dashed] (3.2,-10.1) -- (0,-10.1) node[midway, above] {saved\_count, updated\_count};
\end{tikzpicture}
```

### 4.3.2 Live Interview Assistance Flow

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[font=\scriptsize, >={Latex[length=2mm]}]
  \foreach \x/\name in {0/Browser\\(Interviewer), 3.4/WebSocket\\Server, 7.0/Whisper\\(ASR), 10.4/LLM\\(Follow-up), 13.6/PostgreSQL} {
    \node[draw, fill=gray!10, align=center, minimum width=2.6cm] at (\x,0) {\name};
    \draw[dashed] (\x,0) -- (\x,-11.5);
  }
  \draw[->] (0,-0.8) -- (3.4,-0.8) node[midway, above] {ws connect + \{type: init, session\_id, ...\}};
  \draw[->, dashed] (3.4,-1.5) -- (0,-1.5) node[midway, above] {init\_ok: questions, candidate\_name};
  \draw[->] (0,-2.3) -- (3.4,-2.3) node[midway, above] {\{type: audio\_chunk, audio\_data (base64)\}};
  \draw[->] (3.4,-3.0) -- (7.0,-3.0) node[midway, above] {transcribe\_chunk(bytes)};
  \draw[->, dashed] (7.0,-3.7) -- (3.4,-3.7) node[midway, above] {text};
  \draw[->, dashed] (3.4,-4.4) -- (0,-4.4) node[midway, above] {\{type: transcript, sequence\}};
  \node[align=center] at (6.8,-5.0) {\scriptsize (audio\_chunk loop repeats every \(\sim\)5s)};
  \draw[->] (3.4,-5.8) -- (10.4,-5.8) node[midway, above, align=center] {every \(\sim\)30s if \(\geq\)150 new chars:\\generate\_followup(transcript)};
  \draw[->, dashed] (10.4,-6.6) -- (3.4,-6.6) node[midway, above] {follow-up question};
  \draw[->, dashed] (3.4,-7.3) -- (0,-7.3) node[midway, above] {\{type: followup\_question\}};
  \draw[->] (3.4,-8.0) -- (13.6,-8.0) node[midway, above] {async save TranscriptChunk};
  \draw[->] (0,-8.8) -- (3.4,-8.8) node[midway, above] {\{type: end\_interview\}};
  \draw[->] (3.4,-9.5) -- (10.4,-9.5) node[midway, above, align=center] {invoke live\_interview\_subgraph\\(generate\_summary)};
  \draw[->, dashed] (10.4,-10.2) -- (3.4,-10.2) node[midway, above] {summary, scores, qa\_pairs};
  \draw[->] (3.4,-10.7) -- (13.6,-10.7) node[midway, above] {save\_interview: update Session + Application};
  \draw[->, dashed] (3.4,-11.3) -- (0,-11.3) node[midway, above] {\{type: summary, data\}};
\end{tikzpicture}
```

### 4.3.3 RAG Query (Recruiting Copilot Chat) Flow

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[font=\scriptsize, >={Latex[length=2mm]}]
  \foreach \x/\name in {0/HR / Hiring\\Manager (UI), 3.4/Chat \&\\Graph Router, 7.0/RAG Subgraph\\(LLM Agent), 10.4/Vector Store\\(Chroma), 13.6/PostgreSQL} {
    \node[draw, fill=gray!10, align=center, minimum width=2.6cm] at (\x,0) {\name};
    \draw[dashed] (\x,0) -- (\x,-8.5);
  }
  \draw[->] (0,-0.8) -- (3.4,-0.8) node[midway, above, align=center] {POST /api/execute\\\{intent: rag\_query, query, requisition\_id, chat\_thread\_id\}};
  \draw[->] (3.4,-1.6) -- (7.0,-1.6) node[midway, above] {invoke(RAGQueryState)};
  \draw[->] (7.0,-2.4) -- (10.4,-2.4) node[midway, above] {tool call: search\_candidates(query)};
  \draw[->, dashed] (10.4,-3.1) -- (7.0,-3.1) node[midway, above] {top-K CV chunks + metadata};
  \draw[->] (7.0,-3.9) -- (13.6,-3.9) node[midway, above] {tool call: get\_candidate\_details(id)};
  \draw[->, dashed] (13.6,-4.6) -- (7.0,-4.6) node[midway, above] {candidate / application rows};
  \node[align=center] at (7.0,-5.2) {\scriptsize LLM agent loop: synthesize grounded answer};
  \draw[->, dashed] (7.0,-5.9) -- (3.4,-5.9) node[midway, above] {answer text};
  \draw[->] (3.4,-6.7) -- (13.6,-6.7) node[midway, above] {persist ChatMessage (user + assistant)};
  \draw[->, dashed] (3.4,-7.4) -- (0,-7.4) node[midway, above] {\{answer, thread\_id\}};
\end{tikzpicture}
```

## 4.4 Activity/State Diagram — Candidate Lifecycle

States below mirror the `ApplicationStatus` enum (`src/backend/models/tables_enums.py`); every transition is additionally recorded as a row in `StatusHistory`.

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta}
\begin{tikzpicture}[
  font=\small, >={Latex[length=2mm]},
  state/.style={draw, rounded corners, fill=blue!6, align=center, minimum width=3.0cm, minimum height=0.9cm}
]
  \node[state] (new) {NEW\\(CV uploaded)};
  \node[state, below=1.2cm of new] (pending) {SCREENING\_PENDING};
  \node[state, below left=1.4cm and 2.0cm of pending] (rejected1) {SCREENING\_REJECTED};
  \node[state, below right=1.4cm and 2.0cm of pending] (passed) {SCREENING\_PASSED};
  \node[state, below=1.4cm of passed] (scheduled) {INTERVIEW\_SCHEDULED};
  \node[state, below=1.4cm of scheduled] (completed) {INTERVIEW\_COMPLETED};
  \node[state, below=1.4cm of completed] (offer) {OFFER\_EXTENDED};
  \node[state, below left=1.4cm and 1.6cm of offer] (hired) {HIRED};
  \node[state, below right=1.4cm and 1.6cm of offer] (rejected2) {REJECTED};
  \node[state, right=2.6cm of completed] (withdrawn) {WITHDRAWN};

  \draw[->] (new) -- (pending) node[midway, right] {batch screening triggered};
  \draw[->] (pending) -- (rejected1) node[midway, left, align=center] {comparative\\score below bar};
  \draw[->] (pending) -- (passed) node[midway, right, align=center] {comparative\\score meets bar};
  \draw[->] (passed) -- (scheduled) node[midway, right] {calendar event created};
  \draw[->] (scheduled) -- (completed) node[midway, right] {WebSocket session ends};
  \draw[->] (completed) -- (offer) node[midway, right] {HR/Hiring Manager decision};
  \draw[->] (offer) -- (hired) node[midway, left] {accepted};
  \draw[->] (offer) -- (rejected2) node[midway, right] {declined / not selected};
  \draw[->] (completed.east) to[bend left=15] (withdrawn.north) node[midway, above] {candidate withdraws};
  \draw[->] (scheduled.east) to[bend left=25] (withdrawn.west) node[near start, above] {};
  \draw[->] (passed.east) to[bend left=35] (withdrawn.west) node[near start, above] {};
\end{tikzpicture}
```

## 4.5 Component Diagram

```latex
% Requires: \usepackage{tikz} \usetikzlibrary{positioning, arrows.meta, shapes.geometric}
\begin{tikzpicture}[
  font=\small, >={Latex[length=2mm]},
  comp/.style={draw, rectangle, rounded corners, align=center, minimum width=3.0cm, minimum height=1.0cm, fill=gray!8}
]
  \node[comp, fill=orange!15] (frontend) {React / Vite\\SPA Frontend};
  \node[comp, below=1.4cm of frontend, fill=blue!12] (api) {FastAPI Backend\\(routers / controllers / services)};
  \node[comp, below=1.4cm of api, fill=green!12] (orchestrator) {LangGraph Orchestrator\\(main graph + 3 subgraphs)};

  \node[comp, left=2.2cm of orchestrator, fill=yellow!15] (scheduler) {APScheduler\\(batch screening poll)};
  \node[comp, right=2.2cm of orchestrator, fill=purple!12] (ws) {WebSocket Channel\\(/interview/stream)};

  \node[comp, below=1.4cm of orchestrator, fill=red!10] (db) {PostgreSQL\\(SQLAlchemy async)};
  \node[comp, left=1.6cm of db, fill=red!10] (vector) {ChromaDB\\Vector Store};
  \node[comp, right=1.6cm of db, fill=red!10] (whisper) {Whisper ASR\\(self-hosted)};

  \node[comp, below=1.4cm of vector, fill=teal!12] (embed) {Sentence-Transformer\\(BAAI/bge-m3)};
  \node[comp, below=1.4cm of db, fill=teal!12] (llm) {LLM Provider\\(GROQ / Ollama / Watsonx)};
  \node[comp, below=1.4cm of whisper, fill=gray!20] (gcal) {Google Calendar /\\Meet API};

  \draw[<->] (frontend) -- (api) node[midway, right] {REST + WS};
  \draw[<->] (api) -- (orchestrator);
  \draw[->] (scheduler) -- (orchestrator) node[midway, above] {interval trigger};
  \draw[<->] (orchestrator) -- (ws);
  \draw[<->] (orchestrator) -- (db);
  \draw[<->] (orchestrator) -- (vector);
  \draw[<->] (orchestrator) -- (whisper);
  \draw[<->] (vector) -- (embed);
  \draw[<->] (db) -- (llm);
  \draw[<->] (orchestrator) -- (llm);
  \draw[<->] (api) -- (gcal);
  \draw[<->] (whisper) -- (gcal) [draw=none];
\end{tikzpicture}
```

---

# 5. System Architecture

## 5.1 System Overview

HirePilot is a single-organization web application composed of four cooperating layers: a React/Vite single-page frontend; a FastAPI backend exposing both REST and a WebSocket endpoint; a PostgreSQL relational store accessed asynchronously via SQLAlchemy 2.0; and an AI subsystem comprising a local sentence-embedding model, a ChromaDB vector index, a self-hosted Whisper speech-to-text model, and a pluggable LLM provider (GROQ-hosted by default, with Ollama and IBM Watsonx as alternates). All multi-step AI workflows — batch screening, live-interview summarization, and RAG querying — are expressed as LangGraph graphs rather than ad hoc function chains, giving the system one consistent mental model ("nodes mutate a typed state object, conditional edges route between them") for every place an LLM is involved in a decision.

Two entry points drive work into the backend: synchronous HTTP/WebSocket requests from the frontend, and an in-process APScheduler job that polls the database on an interval and triggers batch screening automatically once a requisition crosses its configured candidate-volume threshold. Both entry points converge on the same `main_graph` orchestrator, so there is exactly one code path for "run batch screening," whether it was triggered by a human clicking a button or by the scheduler.

## 5.2 Backend Architecture

The backend (`src/backend/`) follows a layered structure:

```
main.py              FastAPI app, lifespan startup/shutdown, router registration
scheduler.py         APScheduler job definition and interval trigger
routers/             HTTP/WebSocket route declarations — thin, delegate to controllers
controllers/         Business-logic orchestration per domain entity
controllers/services/  Cross-cutting services: auth, security, Google Calendar/OAuth,
                        question generation, screening-run wiring
models/tables/       SQLAlchemy ORM models (one file per entity)
models/schemas/      Pydantic request/response models
models/crud/         Thin async CRUD functions per entity, used by controllers
graphs/               LangGraph main orchestrator + per-workflow subgraphs/nodes
stores/llm/          LLM client configuration + Whisper service
stores/vectordb/     Embedding model singleton + Chroma vector store + CV text extraction
helpers/             Settings/config loading and shared utilities
assets/cvs/          Local storage for uploaded CV source files
scripts/             One-off/maintenance and manual test scripts (e.g., WebSocket interview tester)
```

This is a fairly conventional **router → controller → service/CRUD** layering, chosen specifically to keep FastAPI route functions thin (parsing the request, calling a controller method, returning the response) while pushing all business logic — validation, multi-step orchestration, calling out to LangGraph — into controllers and the services beneath them. The `BaseController` base class gives every controller access to cached application settings (`get_settings()`) without each controller re-reading environment variables.

**Application startup (`main.py`)** uses FastAPI's `@asynccontextmanager` lifespan pattern to perform three blocking initialization steps exactly once, off the request path: lazily downloading/loading the sentence-embedding model, loading the Whisper ASR model onto the configured device (CPU/CUDA), and starting the APScheduler instance. Both model-loading calls are dispatched via `asyncio.to_thread()` so they do not block the event loop during startup. CORS middleware is configured permissively for local development (allowing the Vite dev server's default ports). Eight routers are registered, each scoped to a path prefix (`/api/auth`, `/api/users`, `/api` for requisitions, `/api/candidates`, `/api/interview`, `/api/chat`, `/api/calendar`, plus the graph-execution endpoint also under `/api`). Two unauthenticated health-check endpoints (`/`, `/health`) report service and database connectivity status.

**Routers** are deliberately narrow. For example, `requisition_router.py` exposes five endpoints (create, list, get-by-id, patch, soft-delete) and defers all logic to `RequisitonController`; `candidate_router.py` similarly exposes candidate CRUD, the cross-requisition candidate directory, application CRUD, status updates, question-generation triggers, and the multipart CV-upload endpoint. The one router that is not purely CRUD-shaped is `interview_router.py`, which hosts the stateful WebSocket endpoint described in [5.5](#55-langgraph-orchestration) and [6.3](#63-ai-workflow-implementation).

**Controllers** map roughly one-to-one onto the schema's aggregate roots: `AuthController`, `CandidateController`, `ApplicationController`, `RequisitonController`, `InterviewController`, `ChatController`. Each holds the orchestration logic for its entity — e.g., `ApplicationController` resolves a status update into both an `Application.status` write and a `StatusHistory` insert in the same operation, so the audit trail can never silently desynchronize from the live status field.

**Services** (`controllers/services/`) hold logic that does not belong to any single entity: `auth_service.py` and `security.py` implement the OAuth/JWT machinery (see [5.6](#56-authentication--authorization-architecture)); `google_calendar_service.py` and `google_oauth_service.py` wrap the Google Calendar API and OAuth credential lifecycle; `generate_questions.py`, `cbi_questions.py`, and `question_context.py` implement interview-question generation; `screening_runner.py` is the single call-site that wires a manual or scheduled trigger into `main_graph.ainvoke(...)`.

## 5.3 PostgreSQL Database Architecture

The database is PostgreSQL, accessed through SQLAlchemy 2.0's async ORM (`asyncpg` driver), with schema evolution managed by Alembic (autogenerated revisions against `SQLAlchemyBase.metadata`, per `mds/ALEMBIC.md`). Thirteen tables exist:

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | HR Manager / Hiring Manager accounts | 1→N `requisitions` (as hiring manager), 1→N `interview_sessions` (as interviewer), 1→N `refresh_tokens`, 1→1 `google_oauth_credentials`, 1→N `chat_threads` |
| `requisitions` | Open job requisitions | 1→N `applications`, 1→N `chat_threads`; N→1 `users` (hiring manager) |
| `candidates` | Immutable global candidate identity | 1→N `applications` |
| `applications` | A candidate's pipeline state for one requisition | N→1 `candidates`, N→1 `requisitions`; 1→N `application_details`; 1→1 `screening_results`; 1→N `interview_sessions`; 1→N `status_history` |
| `application_details` | Flexible key/JSON-value store for extracted CV fields (`technical_skills`, `total_years_experience`, `education`, `previous_roles`, `certifications`, `projects`, `profile_summary`, `contact_info`) | N→1 `applications` |
| `screening_results` | One row per application: numeric score (0–1) + justification text | 1→1 `applications` |
| `interview_sessions` | One scheduled/conducted interview | N→1 `applications`, N→1 `users` (interviewer, nullable); 1→N `transcript_chunks` |
| `transcript_chunks` | Ordered, timestamped slices of interview transcript | N→1 `interview_sessions` |
| `status_history` | Append-only audit trail of `Application.status` transitions | N→1 `applications`; optional N→1 `users` (changed_by) |
| `chat_threads` | A named RAG conversation scoped to one requisition | N→1 `requisitions`; optional N→1 `users`; 1→N `chat_messages` |
| `chat_messages` | Ordered messages within a chat thread | N→1 `chat_threads` |
| `refresh_tokens` | Hashed (SHA-256) refresh tokens with expiry, for rotation/revocation | N→1 `users` |
| `google_oauth_credentials` | Fernet-encrypted Google access/refresh tokens for calendar access | 1→1 `users` |

Three design decisions are worth calling out:

1. **Candidate vs. Application separation.** A `Candidate` row represents a real person's durable identity (name, email, phone, LinkedIn) and is created once; an `Application` row represents that person's pipeline state *for one specific requisition* (status, score, interview history). This is what makes the cross-requisition Candidate Directory ([7.4](#74-candidate-details-interface)) possible without duplicating identity data, and what lets HirePilot deduplicate repeat CV uploads by email.
2. **`ApplicationDetail` as an EAV-style extension table.** Rather than adding a new column to `applications` every time the extraction prompt is asked to pull out one more CV field, structured CV data is stored as `(application_id, key, value: JSON)` rows. This trades a small query-time join cost for schema flexibility — the LLM extraction prompt can evolve without a migration.
3. **Concurrency control via a boolean flag, not a queue.** `Requisition.screening_in_progress` is a simple boolean lock checked by both the scheduler and the manual-trigger endpoint before invoking the batch-screening subgraph, and is always reset on completion (success or failure). This is a deliberately lightweight alternative to a distributed task queue, appropriate at the system's current scale (see [9.3](#93-future-work) for where a real queue would be introduced).

## 5.4 AI/ML Stack Architecture

HirePilot's AI subsystem is composed of four independently swappable pieces, unified behind small wrapper modules in `stores/`:

- **Embedding model** (`stores/vectordb/embedding_model.py`): a `sentence-transformers` model (`BAAI/bge-m3` by default, multilingual), loaded once as a process-wide singleton, with a `SentenceTransformerEmbeddingWrapper` adapting it to LangChain's `Embeddings` interface (`embed_documents`, `embed_query`).
- **Vector store** (`stores/vectordb/load_vectordb.py`): a Chroma collection (`cv_embeddings`) persisted to disk, queried via `similarity_search_with_score(query, k=20, filter={"requisition_id": ...})`. CV text is extracted from uploaded PDFs (via `pymupdf`/`fitz`) or DOCX files before embedding, and each vector is tagged with `{source: filename, requisition_id}` metadata so retrieval is always scoped to the right job.
- **Speech-to-text** (`stores/llm/whisper_service.py`): a self-hosted Hugging Face Whisper model (`openai/whisper-small` by default), run in *translate* mode (any input language → English text), on CPU or CUDA depending on configuration. Audio bytes are decoded via `ffmpeg` (stdin-pipe strategy, with a tempfile fallback) into 16 kHz mono PCM, then chunked into 25-second windows with a 2-second overlap stride before inference, and a small per-session ring buffer of the last two chunks plus an MD5 hash check prevents the same audio from being transcribed twice across chunk boundaries.
- **LLM provider** (`stores/llm/llm_config.py`): a `UnifiedLLM` wrapper class abstracts over three interchangeable backends — GROQ's OpenAI-compatible API (default, `llama-3.3-70b-versatile`), a local Ollama server (`qwen2.5:3b-instruct` default), or IBM Watsonx — selected by an environment variable, with built-in retry (3 attempts, 2-second backoff). Five differently-tuned LLM instances are kept for different jobs: `llm_routing` (temperature 0.1, deterministic intent classification), `llm_extraction` (temperature 0.3, structured CV-field extraction), `llm_generic` (temperature 0.7, reasoning/follow-up generation), `llm_rag` (temperature 0.7, larger-context RAG synthesis), and `llm_sql` (temperature 0.1, precision-oriented).

This separation means the embedding model, the ASR model, and the LLM can each be swapped (e.g., GROQ → Ollama for a fully offline deployment) by changing configuration, without touching the LangGraph workflow code that calls them.

## 5.5 LangGraph Orchestration

A single **main graph** (`graphs/maingraph.py`) is the only entry point for AI-driven work. Its state object, `OrchestratorState`, carries every field any subgraph might need (intent, requisition/application/session IDs, screening mode, query text, chat-thread ID, transcript and follow-up data, and output fields `result`/`error`). A `router` node inspects `state.intent` and conditionally routes to exactly one of three subgraphs — `batch_screening`, `live_interview`, or `rag_query` — or to `END` if the intent is unrecognized. This router-plus-subgraphs shape means new AI capabilities are added by writing a new subgraph and one new branch in the router, not by modifying existing subgraphs.

- **Batch screening subgraph** (`graphs/subgraphs/batchScreening/`) is a strict five-node pipeline (`similarity_search → cv_extraction → interview_enrichment → comparative_scoring → save_results`), with each node checking `state.error` on entry and short-circuiting if a prior node already failed. Its full mechanics are detailed in [6.3](#63-ai-workflow-implementation).
- **Live interview subgraph** (`graphs/subgraphs/liveInterview/`) is a two-node pipeline (`generate_summary → save_interview`) invoked once, at the end of a live WebSocket interview session, to turn an accumulated transcript into a structured, persisted evaluation.
- **RAG query subgraph** (`graphs/subgraphs/ragQuery/`) is a single tool-calling agent node (not a fixed pipeline): an LLM is given access to retrieval tools (`rag_tools.py` — semantic CV search, candidate lookup, requisition-context lookup) and loops, calling tools as needed, until it can produce a grounded final answer.

Every subgraph has its own typed state class (`BatchScreeningState`, `LiveInterviewState`, `RAGQueryState`) distinct from `OrchestratorState`; the main graph's batch/live/RAG nodes are responsible for projecting the orchestrator state into the appropriate subgraph state before invoking it, and projecting the result back out.

## 5.6 Authentication & Authorization Architecture

Authentication is Google-OAuth-only — there is no independently-set password for end users. Two OAuth flows are supported: an **ID-token flow** (`POST /api/auth/google`, for clients that already hold a Google ID token) and an **authorization-code flow** (`POST /api/auth/google/callback`, used by the frontend's `@react-oauth/google` Authorization Code Flow integration, which additionally captures a Google refresh token so the backend can call the Calendar API on the user's behalf later, without another interactive consent step). Both flows converge on the same outcome: verify the Google identity, look up (never auto-create) a `User` row by email, and issue HirePilot's own JWT pair.

- **Access tokens** are HS256 JWTs with a 30-minute expiry and claims `{user_id, email, role, type: "access"}`.
- **Refresh tokens** are HS256 JWTs with a 7-day expiry; the backend never stores the raw refresh token — only its SHA-256 hash, in the `refresh_tokens` table, alongside its expiry. `POST /api/auth/refresh` validates the incoming token's signature *and* checks that its hash still exists (i.e., has not been revoked) before minting a new access token.
- **Logout** deletes the corresponding `refresh_tokens` row, which immediately invalidates that refresh token for future renewal (the still-live 30-minute access token is the only residual window, by design — short enough to be an acceptable trade-off).
- **Pre-registration model.** An HR Manager creates a `User` row (email, name, role) with an empty `hashed_password` via `POST /api/auth/admin/users`; that person's *first* Google login then matches by email and activates the account. A one-time `POST /api/auth/setup` endpoint bootstraps the very first HR Manager when none exists yet, and permanently returns 403 afterward.
- **Authorization** is role-based with exactly two roles, `HR_MANAGER` and `HIRING_MANAGER`, enforced via FastAPI dependency injection — `get_current_user` resolves and validates the bearer JWT into a `User` object for any protected route, and `require_hr_manager()` is layered on top for HR-Manager-only routes (user management, in particular). Authorization is enforced server-side on every state-changing endpoint; the frontend's route guards ([6.4](#64-frontend-implementation)) are a UX convenience, not the security boundary.
- **Secrets at rest.** Google OAuth credentials (used for calendar access) are encrypted with Fernet symmetric encryption before being stored in `google_oauth_credentials`; refresh tokens are stored hashed, never in plaintext.

## 5.7 Third-Party Integrations

**Google Calendar / Google Meet.** The calendar router (`routers/calendar_router.py`) and `google_calendar_service.py` implement: availability querying (excluding weekends, respecting a 9 AM–6 PM UTC working-hours window, with interview-type-specific durations — 30 min HR screen, 60 min technical, 45 min behavioral, 90 min final), interview scheduling (creates a Calendar event with an auto-generated Meet conference link and emails an invitation to the candidate), rescheduling (updates the existing Calendar event and the stored `InterviewSession` times), and cancellation (deletes the Calendar event and marks the session `CANCELLED`). All four operations require the caller to be either an HR Manager or the Hiring Manager who owns the interview.

**WebSocket-based audio streaming.** The live-interview feature ([5.5](#55-langgraph-orchestration), [6.3](#63-ai-workflow-implementation)) is the system's only persistent, stateful connection: the frontend opens a WebSocket to `/api/interview/stream`, sends an `init` handshake, then streams base64-encoded audio chunks for the duration of the interview, receiving transcript and follow-up-question messages back on the same connection until an `end_interview` message triggers final summarization.

---

# 6. Implementation

## 6.1 Technology Stack Justification

| Technology | Role | Why chosen |
|---|---|---|
| **FastAPI** | Backend HTTP + WebSocket framework | Native `async`/`await` support is required for a system that spends most of its time waiting on LLM/ASR inference and database I/O; FastAPI's dependency-injection system (`Depends(get_current_user)`, `Depends(get_db)`) gives clean, testable separation between auth, DB sessions, and route logic; built-in Pydantic request/response validation removes a whole class of manual parsing code. |
| **SQLAlchemy 2.0 (async) + PostgreSQL** | Relational persistence | The domain is fundamentally relational (candidates, applications, status history, interview sessions are all foreign-keyed to each other); PostgreSQL's JSON column type is used deliberately for the few genuinely semi-structured fields (`ApplicationDetail.value`, `tech_questions`, `key_strengths`) without giving up relational integrity everywhere else. |
| **Alembic** | Schema migrations | Autogenerates revisions directly from the SQLAlchemy metadata, keeping the migration history and the ORM model definitions from drifting apart as the schema evolved across five project phases ([1.5](#15-time-plan)). |
| **LangGraph** | AI workflow orchestration | Once a workflow has more than one LLM call with conditional branching and shared state (extract → enrich → score → save), expressing it as explicit nodes and typed state is far more debuggable and resumable than a chain of nested function calls; it also gives every workflow a uniform invocation contract (`graph.ainvoke(state)`) regardless of how different the batch-screening, live-interview, and RAG workflows are internally. |
| **ChromaDB** | Vector store for CV embeddings | A lightweight, embeddable vector database that persists to local disk with no separate server process to operate — appropriate for a single-organization deployment where running a dedicated vector-database cluster would be disproportionate infrastructure. |
| **Sentence-Transformers (BAAI/bge-m3)** | CV embedding model | A strong general-purpose, multilingual embedding model that can be self-hosted (no per-call API cost or external data exposure for sensitive candidate CV text), consistent with the project's preference for self-hostable AI components ([2.4](#24-gap-analysis)). |
| **Whisper (self-hosted, Hugging Face `transformers`)** | Interview speech-to-text | Open-weight, runs locally (no candidate audio leaves the organization's infrastructure), and is the most extensively benchmarked open ASR model, which made it possible to design the chunking/deduplication strategy in [6.3](#63-ai-workflow-implementation) around well-documented accuracy characteristics ([2.2](#22-state-of-the-art-techniques)). |
| **GROQ (default LLM provider), with Ollama/Watsonx as alternates** | LLM inference for extraction, scoring, question generation, RAG, follow-ups | GROQ's hosted inference is fast enough to keep the live-interview follow-up loop and batch-screening pipeline responsive; the provider abstraction (`UnifiedLLM`) means the same code can fall back to a fully local Ollama model if data-residency requirements tighten, without rewriting the graphs. |
| **APScheduler** | Background batch-screening polling | An in-process interval scheduler is sufficient at the system's current scale and avoids standing up a separate task-queue service (Celery/RQ + broker) purely to run one polling job every 15 minutes. |
| **React 19 + Vite** | Frontend SPA | Vite's fast dev-server iteration loop and React's component model fit a UI with many distinct, stateful screens (dashboard, pipeline table, live-interview modal, chat drawer); React 19's stable feature set was already mainstream by the time frontend work began. |
| **Tailwind CSS** | Styling | Utility-first styling let a small frontend team iterate on layout-heavy screens (dense candidate tables, multi-pane interview modal) without maintaining a large separate CSS/SCSS codebase. |
| **`@react-oauth/google`** | Frontend OAuth | Implements the Authorization Code Flow against Google directly in the browser, which is what allows the backend to obtain a Google refresh token for later, offline Calendar API access. |

## 6.2 Backend Implementation Highlights

**Async-first throughout.** Every database access uses an `AsyncSession` from `AsyncSessionLocal`, and every route handler, controller method, and CRUD function is declared `async def`. This was a deliberate choice given how much of the request lifecycle in this system is I/O-bound (waiting on PostgreSQL, on the LLM provider, or on the Whisper model running off the main thread).

**Thin CRUD layer.** Each entity has a small, uniform set of async functions (`create_X`, `get_X_by_id`, `get_Xs`, `update_X`, `delete_X`) in `models/crud/`, plus a handful of entity-specific query helpers where the generic pattern doesn't fit — e.g., `requisition_crud.get_requisitions_ready_for_screening()` and `get_requisitions_ready_for_interview_rescreen()` encapsulate the exact threshold/lock conditions the scheduler needs, so that logic lives in one place rather than being re-derived in both the scheduler and any future manual-trigger code path.

**Status changes are never a bare field write.** `application_crud.update_application_status()` is the single function responsible for changing `Application.status`; it always also inserts a `StatusHistory` row recording `from_status`, `to_status`, who made the change, and an optional reason, in the same logical operation. This guarantees the audit trail (NFR-8) can never fall out of sync with the live status field, because there is no other code path that writes `Application.status`.

**Configuration via a single cached `Settings` object.** `helpers/config.py` defines a Pydantic `BaseSettings` subclass loaded from environment variables / `.env`, wrapped in `@lru_cache` so the whole process shares one settings instance. This is what makes the embedding model, the Whisper model, the LLM provider, and the screening thresholds all independently configurable per deployment without code changes.

**CV upload pipeline.** `POST /api/candidates/upload` accepts a `requisition_id` and a list of files (PDF/DOCX). For each file: text is extracted (`pymupdf`/`fitz` for PDF), the text is embedded via the sentence-transformer, and the resulting vector is written into the Chroma collection tagged with `{source: filename, requisition_id}`. The requisition's `new_candidate_counter` is incremented, which is what eventually causes the scheduler to fire a batch-screening pass once the configured threshold is crossed — CV upload itself does **not** trigger an immediate per-candidate scoring call, by design (see [2.4](#24-gap-analysis) on threshold-triggered batch automation vs. one-at-a-time scoring).

## 6.3 AI Workflow Implementation

### Batch Screening

The `batchScreening` subgraph is implemented as five sequential nodes, each guarded by an `if state.error:` short-circuit so a failure partway through never corrupts already-committed state:

1. **`similarity_search`** loads the requisition's job description from PostgreSQL and runs a Chroma cosine-similarity search (`k=20`, filtered to that requisition's vectors), returning a ranked `List[CandidateDoc]` (source filename, raw CV text, cosine score). In **interview re-screening mode**, this node instead loads the already-screened candidates whose interviews have since completed.
2. **`cv_extraction`** partitions the candidate set into **Bucket A** (candidates who already have an `Application` on this requisition — typically the re-screening case) and **Bucket B** (genuinely new candidates). Bucket A's structured data is *reconstructed from the already-stored `ApplicationDetail` rows*, skipping a redundant LLM call entirely. Bucket B candidates get two concurrent LLM calls per CV: one extracting identity/skills/education/certifications/summary, and a second extracting a strict, dated list of previous roles (`MM/YYYY` start/end), which a pure-Python `ExperienceCalculator` then turns into `total_years_experience` deterministically — total experience is **computed, not LLM-estimated**, specifically because date arithmetic is a place LLMs are unreliable and a calculator is not. Email-based deduplication here also prevents the same person's repeat CV upload from creating a duplicate `Candidate` row.
3. **`interview_enrichment`** generates technical/behavioral question context for Bucket B candidates ahead of time, so that by the time a candidate reaches the interview stage, tailored questions are already available rather than generated on-demand under interview-scheduling time pressure.
4. **`comparative_scoring`** makes a *single* LLM call containing the job description and **every** candidate's extracted summary simultaneously, asking the model to score the whole cohort comparatively (0–1) with a justification each — deliberately not one independent LLM call per candidate, so that the resulting scores are normalized against each other rather than each being an isolated absolute judgment.
5. **`save_results`** upserts: for Bucket A, updates the existing `Application.combined_score` and `ScreeningResult`; for Bucket B, gets-or-creates the `Candidate`, inserts a new `Application`, a new `ScreeningResult`, and the full set of `ApplicationDetail` rows; and finally updates the requisition's counters.

This subgraph is invoked identically whether triggered by `scheduler.py`'s 15-minute interval poll (checking `new_candidate_counter >= new_candidate_threshold` across all active, unlocked requisitions) or by a manual `POST /api/execute` call with `intent: "batch_screening"` — both paths build an `OrchestratorState` and call `main_graph.ainvoke(state)`.

### Live Interview Assistance

The WebSocket handler in `interview_router.py` keeps an in-memory `_Session` object per connection (candidate name, job description, pre-generated questions, accumulated transcript chunks, follow-up log, timing state) — this is intentionally *not* persisted to the database on every message, to keep the per-chunk hot path fast; persistence happens asynchronously via fire-and-forget tasks (`pending_db_tasks`) that save each `TranscriptChunk` without blocking the next audio chunk's processing.

On each `audio_chunk` message, the base64 payload is decoded and handed to `transcribe_chunk()`, which checks an MD5-hash-keyed session buffer (holding the last two chunks) before running Whisper inference, specifically to avoid re-transcribing audio that overlaps a previous chunk's tail. Every ~30 seconds, *if* at least 150 new transcript characters have accumulated since the last follow-up, a separate async LLM call generates a contextual follow-up question grounded in the transcript so far — this threshold exists so the follow-up generator doesn't fire on near-empty silence or repeat itself on unchanged content. When the client sends `end_interview`, the handler waits for any in-flight transcript-chunk saves, then invokes the `liveInterview` subgraph: `generate_summary` (one LLM call producing `key_strengths`, `key_concerns`, `overall_assessment`, a `recommendation_score`, a `technical_depth_score` for technical interviews, and per-question `qa_pairs`) followed by `save_interview` (writing all of that onto the `InterviewSession` row and propagating `overall_interview_score` onto the parent `Application`).

### RAG Query (Recruiting Copilot)

Unlike the two pipeline-shaped subgraphs above, `ragQuery` is a single **agent node** running a tool-calling loop. `RAGQueryState` carries the user's query, the requisition scope, and the running list of agent messages. The LLM is given tools (`rag_tools.py`) for semantic CV search (querying the same Chroma index used by batch screening, scoped to the requisition) and for direct candidate/application/requisition lookups, and loops — call a tool, read its result, decide whether more retrieval is needed, eventually emit a final answer — rather than following a fixed sequence of steps. This is the architecturally correct shape for "answer an open-ended question about an evolving candidate pool," where the right retrieval calls depend entirely on what the user actually asked, unlike the batch-screening pipeline where the steps are always the same five.

## 6.4 Frontend Implementation

The frontend (`hr-ai-agent/`) is a React 19 + Vite single-page application with **no global state management library** — each page owns its own data fetching and local UI state via `useState`/`useEffect`, and only authentication state (`access_token`, `refresh_token`, `user`) is shared globally, via `localStorage`. Routing is handled by `react-router-dom`, with a `ProtectedRoute` wrapper enforcing both "is authenticated" and, where specified, "has the required role" (`hr_manager` vs. `hiring_manager`) before rendering a route.

**Folder structure:**
```
src/
  pages/        One file per screen: login, hrHomePage, jobPipeline, requisitionDetail,
                 candidatesPage, usersPage
  components/   Reusable UI: Button, Card, Modal, Badge, InputField, Toast,
                 ListPagination, ProtectedRoute, and feature components
                 (interviewModal, chatDrawer, requisitionModal, scheduleInterviewModal, ...)
  layouts/      AuthLayout (centered, for login) and hrShellLayout (sidebar + navbar shell)
  services/     One module per backend domain — authService, requisitionService,
                 candidateService, interviewService, chatService, graphService,
                 calendarService, userService — each wrapping `fetch` calls
  data/         Mock data used by not-yet-wired prototype pages (jobPipeline)
```

**API layer.** There is no axios dependency; all HTTP calls go through a shared `apiCall()` helper built on the native `fetch` API, which attaches a `Authorization: Bearer <access_token>` header from `localStorage`, and — critically — on receiving a `401`, transparently calls the refresh endpoint once and retries the original request before giving up and redirecting to `/login`. CV uploads use a parallel helper that omits the `Content-Type` header so the browser can set the correct multipart boundary itself.

**Live interview UI.** `interviewModal.jsx` is the most complex frontend component: a setup panel (choose interview type and audio source), a recording panel (timer, waveform animation, live transcript), a two-pane "guide" column (pre-generated questions alongside AI-generated follow-ups as they arrive over the WebSocket), and a results panel (score, strengths, concerns, full transcript) once the session ends. Audio is captured via the browser's media APIs, chunked roughly every five seconds, base64-encoded, and sent over the same WebSocket protocol documented in [5.5](#55-langgraph-orchestration).

**Recruiting Copilot chat.** `chatDrawer.jsx` implements a multi-thread chat UI (thread list sidebar + message pane) against the chat-thread endpoints and `POST /api/execute` with `intent: "rag_query"`. Bot responses are rendered through a small custom Markdown-block parser (tables, lists, bold/italic) rather than a full Markdown library, since the LLM's RAG answers only ever need that limited subset of formatting.

**Polling for asynchronous backend work.** Because batch screening and live-interview summarization both happen outside the request/response cycle (scheduler-triggered or WebSocket-driven respectively), `requisitionDetail.jsx` polls `GET /api/{requisition_id}` every 5 seconds whenever `screening_in_progress` or an interview-rescreen condition is active, and stops once the backend reports completion — this is the frontend's way of making asynchronous backend state visible without requiring a push channel for every kind of update (NFR-7).

## 6.5 Challenges and Solutions

- **Challenge: distinguishing "new" from "already-seen" candidates during re-screening.** Running comparative scoring again after interviews complete risks either re-extracting CV data the system already has (wasteful, and risks the LLM extracting slightly different values the second time) or silently double-counting candidates. **Solution:** the `cv_extraction` node's Bucket A/Bucket B split explicitly reconstructs already-known candidates from stored `ApplicationDetail` rows instead of re-running extraction, while still feeding both buckets into the same `comparative_scoring` call so old and new candidates are ranked on equal footing.
- **Challenge: LLMs are unreliable at date arithmetic.** Asking a model to directly output "total years of experience" produces inconsistent results across otherwise-identical CVs. **Solution:** the extraction prompt is scoped to *only* extracting structured role/date data (a much narrower, more reliable task for an LLM), and a deterministic Python `ExperienceCalculator` computes the actual duration, explicitly excluding internships/part-time/volunteer roles by rule rather than by asking the model to judge it.
- **Challenge: Whisper transcription quality on live, multi-speaker, possibly noisy audio.** As documented in [2.2](#22-state-of-the-art-techniques), Whisper's error rate rises sharply outside clean, single-speaker conditions, and naively re-running Whisper on overlapping audio windows produces duplicated text at chunk boundaries. **Solution:** audio is chunked with a fixed overlap (25-second windows, 2-second stride) and an MD5-hash-keyed buffer of the previous two chunks is checked before transcribing, so identical overlapping audio is not transcribed (and therefore not duplicated in the persisted transcript) twice.
- **Challenge: keeping the live-interview WebSocket responsive while still persisting every transcript chunk.** Awaiting a database write on every single audio chunk would add latency directly into the user-visible transcript loop. **Solution:** chunk persistence is dispatched as a fire-and-forget `asyncio.Task` tracked in the session's `pending_db_tasks` list, which the handler only awaits at the very end of the interview (before generating the summary), decoupling "show the transcript live" from "guarantee it's durably saved" without losing data.
- **Challenge: generating useful follow-up questions without spamming the interviewer.** Naively calling the LLM on every transcript update either produces too many follow-ups (distracting) or repeats the same suggestion. **Solution:** a follow-up is only generated if at least 150 new characters of transcript have accumulated since the last one and at least ~30 seconds have passed, bounding both the frequency and the LLM cost.
- **Challenge: avoiding vendor lock-in on LLM inference for a project still iterating on model choice.** Different project phases (per [1.5](#15-time-plan)) switched between hosted and local LLM configurations. **Solution:** the `UnifiedLLM` abstraction in `stores/llm/llm_config.py` exposes a single `generate()` interface regardless of whether the underlying call goes to GROQ's hosted API, a local Ollama server, or Watsonx, so graph/node code never references a specific provider's SDK directly.

---

# 7. Prototype / UI Design

> **Note for the LaTeX author:** every subsection below should be paired with an actual screenshot of the running application (`npm run dev` inside the `hr-ai-agent/` frontend directory, against a live backend). Screenshots could not be captured as part of producing this Markdown source; insert a `\begin{figure}` placeholder per screen and replace with a real capture before final submission.

## 7.1 Login Page

`pages/login.jsx`, wrapped in the centered `AuthLayout`. On desktop, the screen splits into two columns: a left-hand sign-in panel and a right-hand gradient hero panel carrying the product name and a one-line description of the platform. There is deliberately no username/password form — the only call to action is a single "Sign in with Google" button. The design rationale follows directly from the authentication architecture in [5.6](#56-authentication--authorization-architecture): because every account is pre-registered by an HR Manager and authenticated purely via Google identity, presenting any other login affordance (password field, "forgot password" link, self-service signup) would be both unnecessary and misleading. An inline "Need an account?" notice tells first-time users that access must be provisioned by HR before their Google sign-in will succeed, since the backend looks up — and never auto-creates — a `User` row by email. On click, `useGoogleLogin()` (Authorization Code Flow) hands an authorization code to `authService.googleLogin()`, which exchanges it via `POST /auth/google/callback`, stores the returned JWT pair, fetches the profile via `GET /auth/me`, and routes the user into `/hr`.

## 7.2 HR Dashboard

`pages/hrHomePage.jsx`, rendered inside the shared application shell (`hrShellLayout.jsx`: a persistent sidebar + top navbar around a scrollable content area). The dashboard's job is purely **requisition triage**: a toolbar (free-text search, a department filter, a "New Requisition" button) sits above a responsive card grid, one card per requisition, showing title, department, location, and status. Below the grid, pagination controls page through the result set. Creating or editing a requisition opens `requisitionModal.jsx`, a three-step wizard (Details → Job Description → Assign Hiring Manager) rather than one long form, which keeps each step's validation scope small and mirrors how a recruiter actually fills the information out in practice (decide the basics, write/paste the JD, then decide who owns it). Deleting a requisition routes through a confirmation modal before issuing the soft-delete (`is_active = false`) call, since a requisition with live applications attached should never disappear silently.

## 7.3 Specific Job Pipeline

Two pages exist for "the pipeline view of one requisition," reflecting the project's iterative history ([1.5](#15-time-plan)):

- **`pages/jobPipeline.jsx`** is the original UI prototype from the early frontend-first phase: a static layout with a hardcoded title and mock candidate rows from `data/candidates.js`, built to validate the look and feel of a two-column "candidate table + AI chat sidebar" layout before any backend existed to drive it.
- **`pages/requisitionDetail.jsx`** (`/requisition/:id`) is the page that superseded it and is the system's actual, fully-wired pipeline view, and the most complex screen in the application. Its header shows the requisition title, department/location, assigned hiring manager, and rollup stat badges (candidate count, average score, status breakdown). Directly below, status banners surface background AI work in progress — "screening N new CVs," "re-ranking after recent interviews" — driven by the 5-second poll described in [6.4](#64-frontend-implementation), so the page never looks frozen while the LangGraph batch-screening subgraph is running server-side. The centerpiece is a dense candidate table: rank, name, a visual score bar (the LLM's comparative 0–1 score), a status dropdown (constrained to valid forward transitions of the `ApplicationStatus` lifecycle, [4.4](#44-activitystate-diagram--candidate-lifecycle)), approve/reject actions, buttons to generate or view tech/CBI interview questions, a button to launch the live AI interview, and a button to schedule/manage the Google Calendar interview. A floating "AI Copilot" action button opens the RAG chat drawer ([7.6](#76-ai-copilot-interface)) without leaving the pipeline view, so a hiring manager can ask "who's our strongest candidate so far" without losing their place in the table.

## 7.4 Candidate Details Interface

Candidate detail is presented as a slide-over panel (`components/candidateDetailsModal.jsx`), not a separate page, so it can be invoked consistently from both the per-requisition pipeline ([7.3](#73-specific-job-pipeline)) and the global Candidate Directory (`pages/candidatesPage.jsx`). The panel header shows the candidate's durable identity (name, email with a `mailto:` link, phone, LinkedIn). Below that, every application this candidate has ever submitted is listed as its own card: requisition title, department/location, a color-coded status badge, the screening score percentage, the interview score (once available), and — when the viewing user lacks access to that particular requisition — a "Restricted" indicator instead of the score, which is the UI-level expression of the role-scoped access control described in [5.6](#56-authentication--authorization-architecture). Clicking an application card navigates straight into that requisition's pipeline view. This single reusable component is what makes the **Candidate vs. Application** data-model split ([5.3](#53-postgresql-database-architecture)) visible to the end user: one identity, many application cards underneath it.

## 7.5 Hiring Manager Dashboard

HirePilot does not implement a structurally separate "Hiring Manager Dashboard" screen; instead, the **same** `hrHomePage.jsx` dashboard ([7.2](#72-hr-dashboard)) and `requisitionDetail.jsx` pipeline view ([7.3](#73-specific-job-pipeline)) are reused for both roles, with the data — not the UI — scoped by role: a Hiring Manager's requisition list is filtered server-side to `hiring_manager_id = <their user id>`, while an HR Manager sees every active requisition. Two pages are gated out entirely for Hiring Managers via `ProtectedRoute`'s `requiredRole` prop: `/candidates` (the global directory) and `/users` (user administration), both HR-Manager-only. A `layouts/HiringManagerLayout.jsx` file exists in the codebase as a placeholder for a visually distinct hiring-manager shell, but is not currently wired into the router — at present, role differentiation is purely a filtering and route-gating concern, not a separate visual experience. This is a deliberate (if modest) simplification: a hiring manager's job — review and decide on candidates for *their own* open roles — is a strict subset of an HR manager's job, so one dashboard with scoped data was judged sufficient rather than maintaining two parallel UIs.

## 7.6 AI Copilot Interface

The live-interview assistant (`components/interviewModal.jsx`) is the system's most interactive screen, structured as a phase machine — **Setup → Recording → Evaluating → Results** — rather than a single static form:

1. **Setup panel:** choose the interview type (HR Screen / Technical / Behavioral / Final, which determines duration and question set) and the audio source (microphone only, or microphone + system/mixed audio for remote calls).
2. **Recording panel:** once started, a live timer and an animated waveform/recording indicator confirm capture is active, while a transcript pane fills in near real time as `transcript` messages arrive over the WebSocket ([4.3.2](#432-live-interview-assistance-flow)).
3. **Guide column (running alongside recording):** a two-section sidebar — pre-generated questions (from the batch-screening enrichment step, [6.3](#63-ai-workflow-implementation)) in one collapsible card, and AI-generated follow-up questions in another, appended live as `followup_question` messages arrive, each tagged with the moment it was suggested.
4. **Results panel:** once the interviewer ends the session, the UI shows the LLM-generated overall score, a list of strengths and concerns, and a scrollable, timestamped review of the full transcript — the human-readable rendering of the `generate_summary` node's output ([6.3](#63-ai-workflow-implementation)).

The same "Copilot" branding also labels the floating chat-drawer entry point on the requisition pipeline page ([7.3](#73-specific-job-pipeline)); together, the live-interview assistant and the RAG chat drawer are the two faces of "AI Copilot" presented to the user — one active *during* a candidate conversation, one available *between* conversations for free-text questions over the whole candidate pool.

---

# 8. Testing & Evaluation

> **Note on scope.** This chapter reports honestly on what testing was actually performed during development, rather than presenting fabricated benchmark figures. Where no formal measurement exists yet, this is stated explicitly and a concrete evaluation methodology is proposed for future work ([9.3](#93-future-work)).

## 8.1 Testing Strategy

Verification during development was predominantly **manual and exploratory**, exercised through the running React frontend against a live backend, rather than through an automated test suite. The codebase contains one purpose-built test harness, `src/backend/scripts/test_interview_live.py`, which exercises the live-interview pipeline end-to-end outside the browser: it resolves or creates a real `InterviewSession` via the REST API, opens a WebSocket connection to `/api/interview/stream`, captures real microphone audio in fixed-length chunks (via `sounddevice`), streams it exactly as the frontend would, and prints incoming transcript and follow-up-question messages to the console as they arrive, ending with the generated summary on `end_interview`. This script was used throughout Phases 3–5 ([1.5](#15-time-plan)) to validate the WebSocket protocol, the Whisper chunking/deduplication logic, and the follow-up-generation timing logic independent of frontend UI bugs. A separate `lever/` directory in the repository root holds standalone, ad hoc scripts written earlier in the project to explore the Lever ATS's public API (postings, opportunities) as a candidate data source before the team committed to a fully native data model — these are exploratory scripts, not part of the application or its test suite, and explain the `lever_id` / `lever_opportunity_id` naming convention retained in the current schema ([5.3](#53-postgresql-database-architecture)) as a naming legacy rather than an active integration.

There is currently **no automated unit or integration test suite** (no `pytest` test directory with assertions against the FastAPI routes, CRUD layer, or LangGraph nodes; no frontend test files using a runner such as Vitest or Jest). This is an explicit, acknowledged gap rather than an oversight, and is carried forward as a limitation ([9.2](#92-limitations)) and a concrete future-work item ([9.3](#93-future-work)): the highest-value targets for a first automated suite would be (a) the deterministic, non-LLM logic that is cheapest and most valuable to pin down — `ExperienceCalculator`'s date-range arithmetic, the `ApplicationStatus` transition rules, the Bucket A/Bucket B partitioning logic in `cv_extraction` — and (b) the JWT/refresh-token lifecycle in `security.py`, since an authentication regression is high-impact and easy to catch with a small, fast test set that requires no LLM calls at all.

## 8.2 AI Model Evaluation

No in-house, measured benchmark of the screening model's ranking quality or the Whisper deployment's word error rate has been conducted against a held-out labeled dataset; this section therefore reports the relevant evaluation *methodology* and situates HirePilot's expected behavior against the published literature figures from [2.2](#22-state-of-the-art-techniques), rather than reporting numbers that were not actually measured.

**Recommended methodology for comparative-scoring quality:** assemble a held-out set of CVs for one or more past (already-decided) requisitions, run them through the unmodified `batchScreening` subgraph, and compute rank correlation (Spearman's ρ or Kendall's τ) between the LLM's comparative ranking and the actual historical hiring-panel ranking for the same candidates. A secondary metric — top-K overlap (e.g., "did the model's top 5 match the panel's top 5") — would be more directly actionable for a recruiting team than the score's absolute value, since the system is explicitly designed to *recommend*, not autonomously decide ([1.4](#14-scope-and-limitations), [2.4](#24-gap-analysis)).

**Recommended methodology for Whisper transcription accuracy:** record a small set of mock interviews under the actual deployment conditions (laptop microphone, typical home/office background noise, two speakers), produce a manually-transcribed gold-standard transcript for each, and compute word error rate (WER) of the system's persisted, de-duplicated transcript against that gold standard. Based on the published literature ([2.2](#22-state-of-the-art-techniques)), a reasonable *a priori* expectation for this deployment is double-digit WER (roughly the 10–20% range reported for real-world meeting audio) rather than the sub-2% figures Whisper achieves on clean, single-speaker benchmark datasets — live two-person interview audio with normal conversational overlap is a meaningfully harder acoustic condition than the curated benchmarks those low figures come from.

**Recommended methodology for follow-up-question quality:** since "is this a good follow-up question" is inherently subjective, an LLM-as-judge or small human-rater panel scoring relevance/specificity of generated follow-ups against the preceding transcript chunk (blind, on a 1–5 scale) would be more tractable than any fully automated metric.

## 8.3 Usability Testing

No formal, structured usability study (e.g., moderated task-based sessions with a System Usability Scale questionnaire) was conducted with HR or hiring-manager users during this project. UI decisions instead evolved through the iterative phase structure documented in [1.5](#15-time-plan) — each phase's frontend work (dashboard, pipeline table, candidate modal, interview modal, chat drawer) was reviewed and adjusted informally against the workflow the system was meant to support, but not measured against a usability instrument with external participants. This is flagged as a limitation in [9.2](#92-limitations); a recommended first usability study would task a small group of real HR/hiring-manager users with: triaging a requisition's candidate list, generating and reviewing interview questions for one candidate, running a short mock live interview through the AI Copilot interface, and asking the Recruiting Copilot chat a comparative question across candidates — followed by a structured questionnaire and a think-aloud debrief.

## 8.4 Performance & Load Testing

No formal load testing (e.g., simulated concurrent users via a tool such as Locust or k6) has been performed against the API. Based on the architecture documented in Chapter 5, the system's known throughput-limiting design choices — which would be the natural starting points for a load-testing exercise — are:

- **Sequential batch screening across requisitions.** Only one requisition's screening pipeline runs at a time system-wide ([3.3](#33-constraints-and-assumptions)), so organizations triggering many simultaneous large hiring pushes would see screening completion times for later requisitions queue up behind earlier ones rather than running in parallel.
- **In-process scheduler and in-memory WebSocket session state.** APScheduler and the live-interview `_Session` objects both live inside the single FastAPI process; horizontally scaling the backend to multiple processes/instances would currently risk either duplicate scheduled-job firing or a WebSocket session being unreachable from a different instance than the one that initialized it — both are addressed by the Redis-backed approach proposed in [9.3](#93-future-work).
- **Synchronous-feeling model loading at startup.** The embedding model and Whisper model are loaded once at process startup (via `asyncio.to_thread`), which is a one-time cost per process start, not a per-request cost, but does mean a multi-instance horizontal scale-out multiplies that one-time memory/load cost by the number of instances.

A recommended first load test would measure: (1) REST API p50/p95 latency for the CRUD-heavy endpoints (requisition/candidate listing, application status updates) under concurrent load, which are not LLM-bound and should scale cleanly with the async FastAPI + PostgreSQL stack; and (2) the maximum number of concurrent live-interview WebSocket sessions the Whisper model (on its configured device) can transcribe without the per-chunk transcription latency exceeding the real-time chunk-arrival rate, which is the most likely actual bottleneck given that ASR inference, unlike most of the REST API, is CPU/GPU-bound rather than I/O-bound.

---

# 9. Conclusion & Future Work

## 9.1 Summary of Contributions

This project delivered a single, internally-owned recruiting system, HirePilot, that unifies four stages of internal hiring — CV intake, AI-assisted screening, AI-assisted interviewing, and conversational candidate search — behind one data model and one orchestration layer, where the competitive landscape ([2.3](#23-market-analysis-and-competitive-landscape)) shows these stages are typically split across separate vendor products. Concretely, the system delivers:

1. A **threshold-triggered, multi-node batch-screening pipeline** (LangGraph: similarity search → CV extraction → interview enrichment → comparative scoring → persistence) that produces a comparative, justified 0–1 score per candidate per requisition, with deterministic (non-LLM) experience calculation and re-screening support that incorporates interview outcomes into an updated ranking.
2. **Automatic, CV- and job-description-specific interview question generation**, paired with a fixed STAR-method behavioral question set, available before a candidate is even scheduled for interview.
3. A **real-time, WebSocket-driven live-interview assistant** that transcribes audio via a self-hosted Whisper model with overlap-aware deduplication, suggests contextual follow-up questions during the conversation, and automatically produces a structured post-interview evaluation.
4. A **retrieval-augmented, multi-turn conversational interface** over the candidate pool, scoped per requisition and backed by the same CV vector index the screening pipeline uses, with persisted chat history.
5. **End-to-end Google Calendar/Meet scheduling integration**, and a **JWT + Google OAuth authentication and role-based authorization layer** distinguishing HR Managers from Hiring Managers, enforced server-side.
6. A **React/Vite frontend** covering the full workflow — requisition management, the per-requisition pipeline, a cross-requisition candidate directory, user administration, and the AI Copilot interfaces — built to make asynchronous backend AI work (screening, interview processing) visibly trackable rather than opaque.

## 9.2 Limitations

- **No dedicated fairness-auditing layer.** As discussed in [2.2](#22-state-of-the-art-techniques), LLM-based screening carries documented bias risk; HirePilot mitigates this only by design convention (every score carries a justification and remains a human-reviewed recommendation, never an autonomous reject), not through an active bias-measurement or de-biasing mechanism.
- **No automated test suite.** As documented in [8.1](#81-testing-strategy), verification has been manual/exploratory plus one scripted WebSocket harness; there is no `pytest`/frontend-test-runner coverage protecting against regressions in the CRUD layer, the LangGraph nodes, or the authentication flow.
- **No measured AI-quality or load benchmarks.** [8.2](#82-ai-model-evaluation) and [8.4](#84-performance--load-testing) propose methodologies but report no executed results; the system's actual screening-ranking quality, transcription word error rate, and concurrent-session capacity are currently unknown quantities rather than measured ones.
- **No formal usability study.** UI iteration was informal ([8.3](#83-usability-testing)); the interface has not been validated against real HR/hiring-manager users under a structured usability protocol.
- **Single-organization, no horizontal scale-out yet.** The in-process scheduler and in-memory WebSocket session state ([8.4](#84-performance--load-testing)) work correctly for a single backend instance but would need the Redis-backed changes proposed below before the backend could run as more than one process.
- **Google Workspace dependency.** Both login and scheduling are unusable for an organization not on Google Workspace ([3.3](#33-constraints-and-assumptions)).

## 9.3 Future Work

- **Introduce Redis** for: (a) a shared job lock / distributed scheduler coordination, replacing the single boolean `screening_in_progress` column so multiple backend instances can safely share scheduling responsibility; (b) externalizing live-interview `_Session` state out of in-process memory, so a WebSocket session is not pinned to the specific backend instance that accepted the initial connection; and (c) a response cache for repeat RAG queries within a short window.
- **Add an automated test suite**, prioritized as described in [8.1](#81-testing-strategy): deterministic logic first (experience calculation, status-transition rules, CV-extraction bucket partitioning, JWT/refresh-token lifecycle), then integration tests against a test database for the CRUD and controller layers, then (lower priority, given cost/non-determinism) golden-output regression tests for the LangGraph nodes using recorded LLM responses.
- **Run the proposed AI evaluation methodology** from [8.2](#82-ai-model-evaluation) against real historical hiring decisions and real interview audio, to replace the literature-derived expectations in this thesis with measured numbers for this specific deployment.
- **Conduct a structured usability study** per the protocol proposed in [8.3](#83-usability-testing), with real HR/hiring-manager participants.
- **Broaden language support beyond Whisper's translate-to-English mode**, for organizations that need verbatim non-English transcription rather than translation, and for direct multilingual support in the comparative-scoring and RAG prompts.
- **Add a lightweight bias-auditing pass** to the comparative-scoring node — for example, periodically re-running scoring with candidate names/identifying details redacted and flagging large score deltas — as a concrete, low-cost mitigation building on the fairness literature in [2.2](#22-state-of-the-art-techniques).
- **Expand role granularity** if/when the organization needs finer-grained collaboration (e.g., interview panelists who are neither the HR Manager nor the requisition's Hiring Manager but need limited, scoped access to one requisition's pipeline).

---

# References

1. The Undercover Recruiter. *Choosing the Best AI Applicant Tracking Systems 2026.* https://theundercoverrecruiter.com/choosing-the-best-ai-applicant-tracking-systems-2026/
2. People Managing People. *30 Best AI ATS Software of 2026: Reviewed & Compared.* https://peoplemanagingpeople.com/tools/best-ai-ats/
3. ResumeRank.io. *Top 5 AI Resume Screening Tools (LLM-Powered) for Recruiters in 2026.* https://www.resumerank.io/en/blog/top-5-resume-screening-tools-independent-recruiters-agencies-2026
4. Truffle. *Greenhouse vs Lever (2026 comparison).* https://www.hiretruffle.com/compare/greenhouse-vs-lever
5. HireAuto.ai. *Compare AI Hiring Platforms — HireAuto vs HireVue, Greenhouse, Workable.* https://hireauto.ai/compare
6. GoMokka. *12 Best AI Screening Tools (2026): Compared, Priced, Rated.* https://www.gomokka.com/resources/12-best-ai-screening-tools-for-recruiters-in-2026.html
7. Artificial Analysis. *Whisper — Word Error Rate Index, Speed & Price Analysis.* https://artificialanalysis.ai/speech-to-text/models/whisper
8. ACM Digital Library. *A Comparative Analysis of Automatic Speech Recognition Errors in Small Group Classroom Discourse.* https://dl.acm.org/doi/fullHtml/10.1145/3565472.3595606
9. University Transcription Services. *Word Error Rates (WER) for AI Transcription: What Do They Tell Us?* https://universitytranscriptions.co.uk/word-error-rates-wer-for-ai-transcription-what-do-they-tell-us/
10. AssemblyAI. *Universal-2 vs OpenAI's Whisper: Comparing Speech-to-Text Models in Real-World Use Cases.* https://www.assemblyai.com/blog/comparing-universal-2-and-openai-whisper
11. ResearchGate. *Application of RAG (Retrieval-Augmented Generation) in AI-Driven Resume Analysis and Job Matching.* https://www.researchgate.net/publication/390752902_Application_of_RAG_Retrieval-Augmented_Generation_in_AI-Driven_Resume_Analysis_and_Job_Matching
12. Merge.dev. *12 Powerful Examples of Retrieval-Augmented Generation (RAG).* https://www.merge.dev/blog/rag-examples
13. Robbins, B. *RAG in Recruitment in AI-Powered Recruitment.* Medium. https://medium.com/@brucerobbins/rag-in-recruitment-7c15d6d24b20
14. arXiv:2407.20371. *Gender, Race, and Intersectional Bias in Resume Screening via Language Model Retrieval.* https://arxiv.org/html/2407.20371v1
15. arXiv:2503.19182. *Evaluating Bias in LLMs for Job-Resume Matching: Gender, Race, and Education.* https://arxiv.org/pdf/2503.19182
16. arXiv:2508.16673. *Invisible Filters: Cultural Bias in Hiring Evaluations Using Large Language Models.* https://arxiv.org/html/2508.16673v1
17. arXiv:2504.01420. *FAIRE: Assessing Racial and Gender Bias in AI-Driven Resume Evaluations.* https://arxiv.org/pdf/2504.01420
18. arXiv:2405.19699. *Fairness in AI-Driven Recruitment: Challenges, Metrics, Methods, and Future Directions.* https://arxiv.org/html/2405.19699v3
19. arXiv:2507.11548. *Fairness Is Not Enough: Auditing Competence and Intersectional Bias in AI-Powered Resume Screening.* https://arxiv.org/pdf/2507.11548
20. University of Washington News. *People Mirror AI Systems' Hiring Biases, Study Finds.* (2025). https://washington.edu/news/2025/11/10/people-mirror-ai-systems-hiring-biases-study-finds

---

# Appendices

## Appendix A — Full API Endpoint Reference

A consolidated list of every backend route, grouped by router, suitable for expansion into a full OpenAPI-style appendix table (method, path, auth requirement, request/response schema):

- **Auth** (`/api/auth`): `POST /google`, `POST /google/callback`, `POST /refresh`, `GET /me`, `POST /logout`, `POST /admin/users`, `POST /setup`
- **Users** (`/api/users`): `GET /`, `GET /{user_id}`, `PUT /{user_id}`, `PATCH /{user_id}/deactivate`, `PATCH /{user_id}/activate`
- **Requisitions** (`/api`): `POST /`, `GET /`, `GET /{requisition_id}`, `PATCH /{requisition_id}`, `DELETE /{requisition_id}`
- **Candidates & Applications** (`/api/candidates`): `POST /`, `GET /directory`, `GET /{candidate_id}`, `PATCH /{candidate_id}`, `GET /by-requisition/{requisition_id}`, `POST /applications/`, `GET /applications/{application_id}`, `PATCH /applications/{application_id}`, `POST /applications/{application_id}/tech-questions`, `POST /applications/{application_id}/cbi-questions`, `PATCH /applications/{application_id}/status`, `GET /applicationDetail/{application_id}`, `POST /upload`
- **Interviews** (`/api/interview`): `WS /stream`, `GET /sessions/{session_id}/detail`, `GET /sessions/{application_id}`, `POST /sessions`
- **Chat** (`/api/chat`): `GET /threads`, `POST /threads`, `GET /threads/{external_id}/messages`, `PATCH /threads/{external_id}`, `DELETE /threads/{external_id}`
- **Graph execution** (`/api`): `POST /execute`
- **Calendar** (`/api/calendar`): `GET /availability`, `POST /schedule-interview`, `PUT /interviews/{interview_id}/reschedule`, `DELETE /interviews/{interview_id}`

## Appendix B — Complete Entity-Relationship Reference

Full column-level listings for all thirteen tables (`users`, `requisitions`, `candidates`, `applications`, `application_details`, `screening_results`, `interview_sessions`, `transcript_chunks`, `status_history`, `chat_threads`, `chat_messages`, `refresh_tokens`, `google_oauth_credentials`) are documented in [5.3](#53-postgresql-database-architecture); the simplified visual ER diagram is in [4.2](#42-entity-relationship-diagram). A full appendix table should reproduce every column, type, nullability, and default directly from `src/backend/models/tables/*.py` for the final submission.

## Appendix C — Survey Instruments

No usability survey instrument was administered during this project ([8.3](#83-usability-testing)); this appendix is reserved for the structured questionnaire/task script recommended in [9.3](#93-future-work), to be added once that study is conducted.

## Appendix D — Environment & Configuration Reference

Key environment variables consumed by `helpers/config.py` and the AI/store modules: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `ENCRYPTION_KEY`, `SCREENING_POLL_INTERVAL_MINUTES`, `NEW_CANDIDATE_THRESHOLD`, `NEW_ASSESSMENT_THRESHOLD`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_DEVICE`, `WHISPER_MODEL_NAME`, `WHISPER_DEVICE`, `FFMPEG_PATH`, `GROQ_API_KEY`, `GROQ_MODEL`, `OLLAMA_BASE_URL`, `BASE_MODEL`, `LLM_PROVIDER`. Frontend build-time variables (`hr-ai-agent/.env`): `VITE_GOOGLE_CLIENT_ID`, `VITE_API_BASE_URL`.
