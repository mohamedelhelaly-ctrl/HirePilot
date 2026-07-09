# Incorta-HR Thesis — Document Outline

> **Context for the agent generating this document:** This is a final-stage thesis (60–100+ pages) for "Incorta-HR," an AI-powered internal recruitment assistant. It covers requisition management, candidate lifecycle handling, automated batch screening, live AI-assisted interviews, and RAG-based conversational candidate insights. Backend: Python/FastAPI, PostgreSQL, Alembic, Redis (planned). AI stack: Whisper (speech-to-text), sentence-transformer embeddings (semantic search), LangGraph (workflow orchestration). Frontend: React/Vite. Use the repository contents to fill in real, accurate technical details for every section below — do not invent architecture, schemas, or code that isn't reflected in the actual codebase.

---

## 1. Introduction
- **1.1 Motivation** — Why this project exists: the recruiting pain points at Incorta that motivated building an AI-assisted HR system.
- **1.2 Problem Definition** — The specific gaps in manual/existing recruiting workflows that Incorta-HR is designed to solve.
- **1.3 Aims and Objectives** — The concrete goals the system sets out to achieve, stated as measurable objectives.
- **1.4 Scope and Limitations** — What the system covers (screening, interviews, RAG insights) and explicitly what it does not (e.g., payroll, onboarding, offer management).
- **1.5 Time Plan** — Planned project timeline/milestones, shown against what was actually delivered.
- **1.6 Thesis Organization** — A roadmap of what each subsequent chapter covers.

## 2. Background & Literature Review
- **2.1 Field of the Project** — Overview of AI-assisted recruitment/HR-tech as a domain.
- **2.2 State-of-the-Art Techniques** — Current techniques used in ATS systems, LLM-based candidate screening, and speech-to-text for interviews.
- **2.3 Market Analysis and Competitive Landscape** — Comparison against existing recruiting platforms (e.g., Greenhouse, Lever, HireVue) and where they fall short.
- **2.4 Gap Analysis** — Explicit statement of what existing tools don't do that Incorta-HR does.

## 3. System Requirements
- **3.1 Functional Requirements** — What the system must do, organized by feature area (requisitions, candidates, screening, interviews, chat/RAG).
- **3.2 Non-Functional Requirements** — Performance, security, scalability, usability, and reliability requirements.
- **3.3 Constraints and Assumptions** — Technical/business constraints (e.g., Google Workspace dependency, language limitations of Whisper) and assumptions made during design.

## 4. System Analysis & Diagrams
- **4.1 Use Case Diagram** — Actors (HR Manager, Hiring Manager) and their interactions with system functions.
- **4.2 Entity-Relationship Diagram** — The PostgreSQL schema: core entities (requisitions, candidates, applications, interviews, users) and their relationships.
- **4.3 Sequence Diagrams** — Step-by-step interaction flows for batch screening, live interview assistance, and RAG query handling.
- **4.4 Activity/State Diagram — Candidate Lifecycle** — The candidate's journey from application through screening, interviewing, to final decision.
- **4.5 Component Diagram** — How FastAPI, PostgreSQL, Redis, Whisper, the embedding model, and LangGraph connect as system components.

## 5. System Architecture
- **5.1 System Overview** — High-level architecture diagram and narrative of how all subsystems fit together.
- **5.2 Backend Architecture** — The FastAPI structure: routers, controllers, services, and CRUD layering.
- **5.3 PostgreSQL Database Architecture** — Schema design, migrations via Alembic, and data modeling decisions.
- **5.4 AI/ML Stack Architecture** — How Whisper, the embedding model, and the ranking/screening logic fit together as a stack.
- **5.5 LangGraph Orchestration** — How LangGraph coordinates batch screening, live interview assistance, and RAG workflows as graphs/nodes.
- **5.6 Authentication & Authorization Architecture** — How user roles (HR Manager vs Hiring Manager) are authenticated and access-controlled.
- **5.7 Third-Party Integrations** — Google Calendar/Meet integration for scheduling, and WebSocket-based audio streaming for live interviews.

## 6. Implementation
- **6.1 Technology Stack Justification** — Why each major technology (FastAPI, PostgreSQL, LangGraph, Whisper, React/Vite, etc.) was chosen.
- **6.2 Backend Implementation Highlights** — Key modules, design patterns, and notable implementation decisions in the backend.
- **6.3 AI Workflow Implementation** — How the batch screening pipeline, live interview assistant, and RAG flow were actually built.
- **6.4 Frontend Implementation** — The React/Vite frontend structure and how it connects to backend APIs.
- **6.5 Challenges and Solutions** — Technical obstacles encountered during implementation and how they were resolved.

## 7. Prototype / UI Design
- **7.1 Login Page** — Walkthrough of the authentication screen and its design rationale.
- **7.2 HR Dashboard** — Walkthrough of the HR Manager's main dashboard view.
- **7.3 Specific Job Pipeline** — Walkthrough of the per-requisition candidate pipeline view.
- **7.4 Candidate Details Interface** — Walkthrough of the individual candidate profile/detail screen.
- **7.5 Hiring Manager Dashboard** — Walkthrough of the Hiring Manager's dedicated dashboard view.
- **7.6 AI Copilot Interface** — Walkthrough of the live-interview AI assistant interface.

## 8. Testing & Evaluation
- **8.1 Testing Strategy** — Overall approach: unit, integration, and system-level testing methodology.
- **8.2 AI Model Evaluation** — Measured performance of the screening ranking model and Whisper (e.g., word error rate, latency).
- **8.3 Usability Testing** — Findings from any usability testing conducted with HR/hiring manager users.
- **8.4 Performance & Load Testing** — System behavior under load, including API response times and concurrency handling.

## 9. Conclusion & Future Work
- **9.1 Summary of Contributions** — Recap of what the thesis/project delivered.
- **9.2 Limitations** — Honest assessment of current shortcomings.
- **9.3 Future Work** — Planned or recommended next steps (e.g., Redis caching, additional language support).

## References
- Full citation list for all sources referenced throughout the thesis.

## Appendices
- Supplementary material: full API documentation, complete ERD, survey instruments (if usability testing was conducted), and any additional supporting artifacts.