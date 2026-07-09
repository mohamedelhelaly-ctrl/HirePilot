# HirePilot Project Specification

This document summarizes the product vision, system structure, and implementation status of the HirePilot repository. It is intended to be a concise, high-level reference for contributors and reviewers.

## 1. Product overview

HirePilot is an AI-assisted recruiting platform for internal HR teams. The system is designed to support:

- requisition management,
- candidate and application tracking,
- AI-assisted CV screening,
- interview preparation and live interview support,
- chat-based querying over candidate data,
- and Google Calendar integration for interview scheduling.

The project is also the implementation basis for the HirePilot thesis work described in [mds/HirePilot_Thesis.md](mds/HirePilot_Thesis.md).

## 2. Roles and user experience

The product is intended for two main roles:

- HR Manager: broader access to requisitions, users, and system-wide workflows.
- Hiring Manager: access to assigned requisitions and related candidate activities.

The current backend includes role-aware authentication dependencies and user-management endpoints, while the frontend provides a web-based experience for these user flows.

## 3. Current implementation status

The repository currently contains a working prototype structure with the following core capabilities:

- FastAPI-based backend service.
- SQLAlchemy models and Alembic migrations.
- Authentication with JWT and Google OAuth.
- Requisition, candidate, application, and interview routers.
- WebSocket-based interview streaming and transcript handling.
- Chat endpoints for retrieval-oriented conversations.
- Google Calendar / Meet integration services.
- LangGraph-based orchestration modules for screening and interview workflows.

Some features are implemented as functional modules, while others are present as structured code paths or partial workflow implementations that are still being refined.

## 4. Architecture at a glance

### Backend
The backend lives in [src/backend](src/backend) and is organized around:

- routers for auth, requisitions, candidates, interviews, chat, and calendar,
- controller and service layers,
- SQLAlchemy models and CRUD modules,
- LangGraph orchestration under [src/backend/graphs](src/backend/graphs),
- storage and AI-related helpers for embeddings, transcription, and model access.

### Frontend
The frontend is a React + Vite application in the frontend workspace. It provides the web interface for the recruiting workflows and integrates with the backend API.

### Data layer
The project uses PostgreSQL as the primary relational database and Alembic for migrations. The data model is centered around users, requisitions, candidates, applications, application details, screening results, interview sessions, and related audit/history structures.

## 5. Key product workflows

### Screening workflow
The system is designed to evaluate applications against requisition requirements using AI-assisted screening. The backend includes orchestration modules and scheduling logic for screening triggers and re-screening workflows.

### Interview workflow
The platform supports interview preparation, live interview transcription, and post-interview summarization. The interview router uses WebSocket communication for real-time interaction.

### Chat and search workflow
The backend exposes chat endpoints for threaded queries over candidate and requisition context, supporting retrieval-oriented assistance for recruiters.

### Scheduling workflow
Google Calendar and Meet-related services are integrated to support interview scheduling and availability checks.

## 6. Technology choices

The implementation uses the following stack:

- Backend: FastAPI, SQLAlchemy, Pydantic, Alembic
- Orchestration: LangGraph
- Frontend: React, Vite, Tailwind-style UI setup
- Authentication: JWT and Google OAuth
- AI components: LLM and embedding-related modules, Whisper-based transcription support
- Integrations: Google Calendar / Meet, external API-oriented services

## 7. Development guidance

When making changes, keep the following in mind:

- keep the product documentation aligned with the actual repository state,
- prefer updating the backend and frontend together when a workflow spans both layers,
- treat the thesis document as the broader narrative reference, not as a substitute for code-level implementation details.

## 8. Current gaps and next focus areas

The repository is already structured as a meaningful prototype, but some areas remain more mature than others. The most obvious next steps are:

- hardening the AI workflow execution and observability,
- expanding test coverage,
- validating the end-to-end user flows in the frontend,
- and refining integrations with external services and runtime configuration.

This spec is intentionally concise and implementation-aware. For detailed product narrative and research context, refer to [mds/HirePilot_Thesis.md](mds/HirePilot_Thesis.md).