"""
State schema for the live interview post-processing subgraph.

Invoked ONCE when the interviewer clicks "End Interview".
Receives the complete transcript and session context, produces
a summary + scores, then persists everything to the DB.

Nodes:
    generate_summary → save_interview → END
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QAPair(BaseModel):
    """A question/answer pair extracted from the interview transcript."""
    question: str
    answer: str
    score: Optional[float] = None     # 0–5, populated for technical interviews
    feedback: Optional[str] = None    # populated for technical interviews


class LiveInterviewState(BaseModel):
    """
    State for the post-interview subgraph.

    ┌──────────────────┬──────────────────────────────────────────────────┐
    │  INPUT           │ session_id, application_id, requisition_id,      │
    │                  │ interview_type, full_transcript,                  │
    │                  │ pre_generated_questions, job_description,         │
    │                  │ candidate_name, followup_questions_log,           │
    │                  │ interview_start_time, interview_end_time          │
    ├──────────────────┼──────────────────────────────────────────────────┤
    │  Node 1 output   │ summary, overall_assessment, key_strengths,      │
    │                  │ key_concerns, recommendation_score,               │
    │                  │ technical_depth_score, qa_pairs                   │
    │  Node 2 output   │ saved (bool)                                      │
    ├──────────────────┼──────────────────────────────────────────────────┤
    │  Error tracking  │ error                                             │
    └──────────────────┴──────────────────────────────────────────────────┘
    """

    # ── INPUT ──────────────────────────────────────────────────────────────────
    session_id: int                    # InterviewSession DB row id
    application_id: int
    requisition_id: int
    interview_type: str                # "hr_screen" | "technical" | "behavioral" | "final"
    full_transcript: str               # Complete accumulated transcript text
    pre_generated_questions: List[str] = Field(default_factory=list)
    job_description: str = ""
    candidate_name: str = ""
    followup_questions_log: List[Dict[str, Any]] = Field(default_factory=list)
    interview_start_time: Optional[str] = None  # ISO string
    interview_end_time: Optional[str] = None    # ISO string

    # ── NODE 1 OUTPUT ──────────────────────────────────────────────────────────
    summary: str = ""
    overall_assessment: str = ""
    key_strengths: List[str] = Field(default_factory=list)
    key_concerns: List[str] = Field(default_factory=list)
    recommendation_score: Optional[float] = None   # 0–10
    technical_depth_score: Optional[float] = None  # 0–10, technical interviews only
    qa_pairs: List[QAPair] = Field(default_factory=list)

    # ── NODE 2 OUTPUT ──────────────────────────────────────────────────────────
    saved: bool = False

    # ── ERROR TRACKING ─────────────────────────────────────────────────────────
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True